"""Demo seed (owner: Role 4). Makes the app start in a believable, interesting state.

ONE call does everything, and it is safe to run twice (it skips what exists):
    from app.seed_data.demo_seed import seed_demo
    seed_demo(db)          # after households + base ingredients are committed

What it does
1. ensure_ingredients : recipes.json uses names that are not in reset_db's ingredient
                        list (paneer, curd, garlic ...). Missing ones are CREATED here,
                        with the base unit taken from recipes.json (g / ml / count).
                        'turmeric powder' is added as an alias of 'turmeric'.
2. load_recipes       : loads recipes.json (source = 'seed').
3. seed_stock         : a realistic kitchen, with awkward cases on purpose.
4. seed_plan          : 12 meals over the next 4 days, dated RELATIVE TO TODAY, so the
                        demo works on any day.
5. seed_audit_history : two past audits (DEMO DATA) so the drift ranking and the
                        'off by X% in past audits' reasons are visible at the start.
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logic import stock, units
from app.models import (Audit, AuditItem, Household, Ingredient, MealPlan, Recipe,
                        RecipeIngredient, StockItem)

HERE = Path(__file__).resolve().parent
RECIPE_FILE_CANDIDATES = [HERE / "recipes.json", HERE.parent / "recipes.json",
                          HERE.parent.parent / "recipes.json"]

ALIAS_ADDITIONS = {"turmeric": ["turmeric powder"]}

NEW_INGREDIENT_ALIASES = {
    "besan": ["gram flour", "chickpea flour"], "chickpeas": ["chole", "kabuli chana"],
    "coriander leaves": ["dhania", "cilantro"], "curd": ["dahi", "yogurt"],
    "cumin seeds": ["jeera"], "mustard seeds": ["rai", "sarson"],
    "garlic": ["lehsun"], "ginger": ["adrak"], "peas": ["matar", "green peas"],
    "rajma": ["kidney beans"], "semolina": ["suji", "rava"], "spinach": ["palak"],
    "cauliflower": ["gobi"], "carrot": ["gajar"], "paneer": ["cottage cheese"],
    "masoor dal": ["red lentils"], "okra": ["bhindi"], "lemon": ["nimbu"],
    "capsicum": ["bell pepper", "shimla mirch"], "cream": ["malai"],
    "butter": ["makhan"], "broken wheat": ["daliya", "dalia"],
    "peanuts": ["moongfali"], "cabbage": ["patta gobi"],
    "fenugreek leaves": ["methi"], "soya chunks": ["soya nuggets"],
    "spring onion": ["green onion"], "cucumber": ["kheera"],
}

# name, quantity (g / ml / count), days since last change, expiry in N days (or None)
# Deliberately NOT in stock: besan, cauliflower, spinach, coriander leaves, cream.
DEMO_STOCK = [
    ("poha", 500, 6, None),
    ("onion", 700, 3, None),         # week needs 1100 -> short for the week, fine today
    ("potato", 700, 2, None),
    ("peas", 100, 4, None),          # today needs 160 -> second meal runs short
    ("oil", 60, 8, None),            # almost empty
    ("mustard seeds", 50, 9, None),
    ("toor dal", 200, 12, None),     # Dal Tadka for 4 needs 240 -> missing 40 g
    ("tomato", 500, 1, 2),           # near expiry
    ("turmeric", 100, 11, None),
    ("rice", 1500, 5, None),
    ("moong dal", 300, 10, None),
    ("carrot", 150, 2, 1),           # near expiry
    ("milk", 1000, 0, 1),            # near expiry
    ("sugar", 30, 11, None),         # almost empty
    ("salt", 800, 10, None),
    ("ghee", 200, 5, None),
    ("atta", 2000, 18, None),
    ("paneer", 250, 3, 3),           # week needs 360 -> short
    ("semolina", 500, 7, None),
    ("rajma", 500, 6, None),
    ("garlic", 40, 6, None),
    ("ginger", 20, 6, None),         # week needs 36 -> short
    ("cumin seeds", 50, 8, None),
]

# day offset from today, meal type, recipe name (exactly as in recipes.json)
DEMO_PLAN = [
    (0, "breakfast", "Poha"), (0, "lunch", "Dal Tadka"), (0, "dinner", "Vegetable Khichdi"),
    (1, "breakfast", "Besan Chilla"), (1, "lunch", "Aloo Gobi"), (1, "dinner", "Palak Dal"),
    (2, "breakfast", "Aloo Paratha"), (2, "lunch", "Rajma Masala"), (2, "dinner", "Jeera Rice"),
    (3, "breakfast", "Upma"), (3, "lunch", "Vegetable Pulao"), (3, "dinner", "Paneer Curry"),
]

# DEMO DATA: days ago, [(ingredient, expected, actual)]. The list ran HIGH: people cooked
# without pressing 'Mark done'.
DEMO_AUDITS = [
    (14, [("sugar", 500, 380), ("atta", 3000, 2400), ("ghee", 300, 290)]),
    (7, [("sugar", 450, 300), ("toor dal", 600, 570), ("oil", 500, 420)]),
]


# ------------------------------------------------------------------ helpers
def _load_recipe_file() -> list:
    for path in RECIPE_FILE_CANDIDATES:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("recipes.json not found. Looked in: "
                            + ", ".join(str(p) for p in RECIPE_FILE_CANDIDATES))


def _lookup(db: Session) -> dict:
    """lowercase canonical name OR alias -> Ingredient."""
    table = {}
    for ing in db.scalars(select(Ingredient)):
        table[ing.name.strip().lower()] = ing
        for alias in (ing.aliases or []):
            table.setdefault(alias.strip().lower(), ing)
    return table


def _resolve(lookup: dict, name: str) -> Ingredient:
    ing = lookup.get(name.strip().lower())
    if ing is None:
        raise LookupError(f"Ingredient '{name}' is not in the ingredients table.")
    return ing


# ------------------------------------------------------------------ steps
def ensure_ingredients(db: Session, recipes: list) -> list:
    """Create ingredients that recipes use but the table lacks. Returns created names."""
    lookup = _lookup(db)
    for canon, extra in ALIAS_ADDITIONS.items():
        ing = lookup.get(canon)
        if ing is None:
            continue
        merged = list(ing.aliases or [])
        for a in extra:
            if a.lower() not in [m.lower() for m in merged]:
                merged.append(a)
            lookup[a.lower()] = ing
        if merged != list(ing.aliases or []):
            ing.aliases = merged                     # new list so SQLAlchemy sees it

    units_used = {}
    for r in recipes:
        for it in r["ingredients"]:
            units_used.setdefault(it["name"].strip().lower(), set()).add(it["unit"])

    created = []
    for key in sorted(units_used):
        if key in lookup:
            continue
        used = units_used[key]
        base = units.normalize_unit(next(iter(used))) if len(used) == 1 else None
        if base not in ("g", "ml", "count"):
            raise ValueError(f"Cannot choose a base unit for '{key}' (recipes use {sorted(used)}).")
        ing = Ingredient(name=key, base_unit=base, aliases=NEW_INGREDIENT_ALIASES.get(key, []))
        db.add(ing)
        db.flush()
        lookup[key] = ing
        for a in ing.aliases:
            lookup.setdefault(a.lower(), ing)
        created.append(key)
    return created


def load_recipes(db: Session, recipes: list) -> int:
    lookup = _lookup(db)
    existing = set(db.scalars(select(Recipe.name)))
    added = 0
    for r in recipes:
        if r["name"] in existing:
            continue
        rec = Recipe(name=r["name"], meal_type=r["meal_type"].lower(),
                     base_servings=r["base_servings"], source="seed")
        db.add(rec)
        db.flush()
        for it in r["ingredients"]:
            ing = _resolve(lookup, it["name"])
            qty = units.to_base(it["quantity"], it["unit"], ing.name, ing.base_unit)
            db.add(RecipeIngredient(recipe_id=rec.id, ingredient_id=ing.id,
                                    quantity=qty, unit=ing.base_unit))
        added += 1
    return added


def seed_stock(db: Session, today: date, now: datetime) -> int:
    lookup = _lookup(db)
    added = 0
    for name, qty, days_ago, expiry_in in DEMO_STOCK:
        ing = _resolve(lookup, name)
        if db.scalar(select(StockItem).where(StockItem.ingredient_id == ing.id)):
            continue
        expiry = today + timedelta(days=expiry_in) if expiry_in is not None else None
        item = stock.add_stock(db, ing.id, D(qty), reason="manual", expiry=expiry, commit=False)
        item.updated_at = now - timedelta(days=days_ago)   # explicit -> staleness varies
        added += 1
    return added


def seed_plan(db: Session, today: date) -> int:
    size = db.scalar(select(Household.size)) or 4
    by_name = {r.name: r for r in db.scalars(select(Recipe))}
    added = 0
    for offset, meal_type, recipe_name in DEMO_PLAN:
        day = today + timedelta(days=offset)
        if db.scalar(select(MealPlan).where(MealPlan.date == day, MealPlan.meal_type == meal_type)):
            continue
        rec = by_name.get(recipe_name)
        if rec is None:
            raise LookupError(f"Recipe '{recipe_name}' not found for the demo plan.")
        db.add(MealPlan(date=day, meal_type=meal_type, recipe_id=rec.id,
                        servings=size, status="planned"))
        added += 1
    return added


def seed_audit_history(db: Session, today: date) -> int:
    if db.scalar(select(Audit.id).limit(1)) is not None:
        return 0
    lookup = _lookup(db)
    for days_ago, rows in DEMO_AUDITS:
        audit = Audit(audit_date=today - timedelta(days=days_ago))
        db.add(audit)
        db.flush()
        for name, expected, actual in rows:
            db.add(AuditItem(audit_id=audit.id, ingredient_id=_resolve(lookup, name).id,
                             expected=D(expected), actual=D(actual)))
    return len(DEMO_AUDITS)


# ------------------------------------------------------------------ entry point
def seed_demo(db: Session, today: date | None = None, now: datetime | None = None,
              with_audit_history: bool = True) -> dict:
    today = today or date.today()
    now = now or datetime.now()
    try:
        recipes = _load_recipe_file()
        summary = {"ingredients_created": ensure_ingredients(db, recipes)}
        summary["recipes_loaded"] = load_recipes(db, recipes)
        summary["stock_items"] = seed_stock(db, today, now)
        summary["meals_planned"] = seed_plan(db, today)
        summary["past_audits"] = seed_audit_history(db, today) if with_audit_history else 0
        db.commit()
    except Exception:
        db.rollback()
        raise
    return summary


if __name__ == "__main__":      # python -m app.seed_data.demo_seed
    from app.db import SessionLocal
    with SessionLocal() as session:
        print(seed_demo(session))
