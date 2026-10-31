"""Shopping list logic (owner: Role 4).

Golden rule: code does the math. Nothing here uses the LLM.

How it works
1. Role 1's stock.check_scope() already SUMS needs across all planned meals in
   the window and compares the total against stock (so two meals that both need
   onions are not each told 'available').
2. We take its `summary` rows, keep only those with missing > 0, and save them
   to shopping_items.
3. Regenerating never duplicates: it updates quantities in place, keeps ticked
   items, and removes unticked items that are no longer missing.

All quantities are base units (g / ml / count).
"""
from datetime import date, timedelta
from decimal import Decimal as D

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logic import stock
from app.models import Ingredient, ShoppingItem


def week_start_of(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


# ---------- pure function (no database) ----------
def missing_to_shopping_rows(summary: list) -> list:
    """Keep only rows with something missing; quantity to buy = missing.
    Sorted by name so the list is stable on screen."""
    rows = []
    for r in summary:
        missing = D(str(r["missing"]))
        if missing > 0:
            rows.append({
                "ingredient_id": r["ingredient_id"],
                "name": r["name"],
                "unit": r["unit"],
                "quantity": missing,
            })
    rows.sort(key=lambda r: r["name"])
    return rows


# ---------- database functions ----------
def list_shopping(db: Session, week_start: date) -> list:
    q = (select(ShoppingItem, Ingredient)
         .join(Ingredient, Ingredient.id == ShoppingItem.ingredient_id)
         .where(ShoppingItem.for_week_start == week_start)
         .order_by(Ingredient.name))
    return [{
        "id": item.id,
        "ingredient_id": item.ingredient_id,
        "name": ing.name,
        "unit": ing.base_unit,
        "quantity": item.quantity,
        "checked": item.checked,
        "for_week_start": item.for_week_start,
    } for item, ing in db.execute(q)]


def generate_shopping_list(db: Session, week_start: date | None = None,
                           today: date | None = None) -> list:
    """Build (or refresh) the shopping list for the week and return it.

    Window = 7 days starting from max(week_start, today). Meals already in the
    past are not shopped for. The rows are tagged with week_start.
    """
    today = today or date.today()
    week_start = week_start or week_start_of(today)
    window_start = max(week_start, today)

    result = stock.check_scope(db, "week", today=window_start)
    rows = missing_to_shopping_rows(result["summary"])

    existing = {i.ingredient_id: i for i in db.scalars(
        select(ShoppingItem).where(ShoppingItem.for_week_start == week_start))}

    needed_ids = set()
    for row in rows:
        needed_ids.add(row["ingredient_id"])
        item = existing.get(row["ingredient_id"])
        if item:
            item.quantity = row["quantity"]          # keep 'checked' as the user left it
        else:
            db.add(ShoppingItem(ingredient_id=row["ingredient_id"],
                                quantity=row["quantity"], checked=False,
                                for_week_start=week_start))

    for ing_id, item in existing.items():            # no longer missing and not ticked
        if ing_id not in needed_ids and not item.checked:
            db.delete(item)

    db.commit()
    return list_shopping(db, week_start)


def set_checked(db: Session, item_id: int, checked: bool) -> ShoppingItem:
    item = db.get(ShoppingItem, item_id)
    if item is None:
        raise LookupError("Shopping item not found")
    item.checked = checked
    db.commit()
    return item
