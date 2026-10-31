from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal as D
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import StockItem, StockMovement, MealPlan, Ingredient


def _needs_for_meal(meal) -> dict:
    # Imported lazily so tests can monkeypatch Role 2's function.
    from app.logic import scaling
    needs = defaultdict(D)
    for ing_id, qty in scaling.get_scaled_ingredients(meal.recipe_id, meal.servings):
        needs[ing_id] += D(str(qty))
    return needs


def _stock_map(db: Session) -> dict:
    return {s.ingredient_id: s.quantity for s in db.scalars(select(StockItem))}


def _ingredients(db: Session, ids) -> dict:
    ids = list(ids)
    if not ids:
        return {}
    rows = db.scalars(select(Ingredient).where(Ingredient.id.in_(ids))).all()
    return {i.id: i for i in rows}


def _build_rows(db, needs: dict, available: dict) -> list:
    ings = _ingredients(db, needs.keys())
    rows = []
    for ing_id, needed in needs.items():
        have = available.get(ing_id, D(0))
        rows.append({
            "ingredient_id": ing_id,
            "name": ings[ing_id].name,
            "unit": ings[ing_id].base_unit,
            "needed": needed,
            "available": min(have, needed),
            "missing": max(needed - have, D(0)),
        })
    return rows


# ---------- stock changes ----------
def add_stock(db: Session, ingredient_id: int, qty_base: D, reason="manual",
              expiry=None, commit=True) -> StockItem:
    """Add (or subtract, if negative) quantity. Same ingredient always merges."""
    item = db.scalar(select(StockItem).where(StockItem.ingredient_id == ingredient_id)
                     .with_for_update())
    if item is None:
        item = StockItem(ingredient_id=ingredient_id, quantity=D(0))
        db.add(item)
    new_qty = item.quantity + qty_base
    if new_qty < 0:
        raise ValueError("Stock cannot go below zero.")
    item.quantity = new_qty
    if expiry:
        item.expiry_date = expiry
    db.add(StockMovement(ingredient_id=ingredient_id, delta=qty_base, reason=reason))
    if commit:
        db.commit()
    return item


def set_stock(db: Session, item_id: int, new_qty: D, reason="manual") -> StockItem:
    item = db.get(StockItem, item_id)
    if item is None:
        raise LookupError("Stock item not found")
    if new_qty < 0:
        raise ValueError("Stock cannot be negative.")
    delta = new_qty - item.quantity
    item.quantity = new_qty
    if delta != 0:
        db.add(StockMovement(ingredient_id=item.ingredient_id, delta=delta, reason=reason))
    db.commit()
    return item


# ---------- checks ----------
def check_meal(db: Session, meal_id: int) -> list:
    meal = db.get(MealPlan, meal_id)
    if meal is None:
        raise LookupError("Meal not found")
    return _build_rows(db, _needs_for_meal(meal), _stock_map(db))


def check_scope(db: Session, scope: str, today: date | None = None) -> dict:
    """scope = 'today' or 'week'. Needs are SUMMED across meals before comparing
    to stock; stock is allocated meal by meal in date order."""
    if scope not in ("today", "week"):
        raise ValueError("Scope must be today or week.")

    today = today or date.today()
    end = today if scope == "today" else today + timedelta(days=6)
    meals = db.scalars(
        select(MealPlan)
        .where(MealPlan.date >= today, MealPlan.date <= end, MealPlan.status == "planned")
        .order_by(MealPlan.date, MealPlan.id)
    ).all()

    remaining = dict(_stock_map(db))
    total_needs = defaultdict(D)
    per_meal = []
    for meal in meals:
        needs = _needs_for_meal(meal)
        rows = _build_rows(db, needs, remaining)
        for ing_id, needed in needs.items():          # consume stock for next meal
            remaining[ing_id] = max(remaining.get(ing_id, D(0)) - needed, D(0))
            total_needs[ing_id] += needed
        per_meal.append({
            "meal_id": meal.id, "date": meal.date.isoformat(),
            "meal_type": meal.meal_type,
            "ok": all(r["missing"] == 0 for r in rows), "items": rows,
        })

    summary = _build_rows(db, total_needs, _stock_map(db)) if total_needs else []
    return {"scope": scope, "meals": per_meal, "summary": summary,
            "all_available": all(r["missing"] == 0 for r in summary)}


# ---------- mark done ----------
def mark_done(db: Session, meal_id: int) -> dict:
    """Deduct stock for a meal in ONE transaction. Safe to call twice."""
    try:
        meal = db.scalar(select(MealPlan).where(MealPlan.id == meal_id).with_for_update())
        if meal is None:
            raise LookupError("Meal not found")
        if meal.status == "done":
            return {"meal_id": meal_id, "already_done": True,
                    "deducted": [], "shortfalls": []}

        needs = _needs_for_meal(meal)
        ings = _ingredients(db, needs.keys())
        deducted, shortfalls = [], []
        for ing_id, needed in needs.items():
            item = db.scalar(select(StockItem).where(StockItem.ingredient_id == ing_id)
                             .with_for_update())
            have = item.quantity if item else D(0)
            take = min(have, needed)
            name, unit = ings[ing_id].name, ings[ing_id].base_unit
            if take > 0:
                item.quantity = have - take
                db.add(StockMovement(ingredient_id=ing_id, delta=-take,
                                     reason="meal_done", meal_id=meal.id))
                deducted.append({"name": name, "unit": unit, "quantity": take})
            if needed > have:
                shortfalls.append({"name": name, "unit": unit, "short_by": needed - have})

        meal.status = "done"
        db.commit()
        return {"meal_id": meal_id, "already_done": False,
                "deducted": deducted, "shortfalls": shortfalls}
    except Exception:
        db.rollback()
        raise
