"""Tests for seed_data/demo_seed.py on in-memory SQLite. The base ingredient list is
imported from Role 1's reset_db, so these tests mirror the real starting point."""
from datetime import date, datetime, timedelta
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.logic import audit, scaling, shopping, stock
from app.models import (Audit, Household, Ingredient, MealPlan, Recipe,
                        RecipeIngredient, StockItem)
from app.reset_db import SEED_INGREDIENTS
from app.seed_data import demo_seed

TODAY = date(2026, 11, 2)
NOW = datetime(2026, 11, 2, 9, 0)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False)() as s:
        s.add(Household(name="Demo Household", size=4))
        for name, unit, aliases in SEED_INGREDIENTS:
            s.add(Ingredient(name=name, base_unit=unit, aliases=aliases))
        s.commit()
        yield s


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_every_recipe_loads_and_every_ingredient_resolves(db):
    recipes = demo_seed._load_recipe_file()
    summary = demo_seed.seed_demo(db, today=TODAY, now=NOW)
    assert summary["recipes_loaded"] == len(recipes) == _count(db, Recipe)
    assert _count(db, RecipeIngredient) == sum(len(r["ingredients"]) for r in recipes)


def test_missing_ingredients_created_with_base_units(db):
    before = _count(db, Ingredient)
    summary = demo_seed.seed_demo(db, today=TODAY, now=NOW)
    assert _count(db, Ingredient) == before + len(summary["ingredients_created"])
    names = {i.name: i for i in db.scalars(select(Ingredient))}
    assert names["paneer"].base_unit == "g"
    assert names["cream"].base_unit == "ml"
    assert names["bread"].base_unit == "count"


def test_aliases_do_not_create_duplicates(db):
    demo_seed.seed_demo(db, today=TODAY, now=NOW)
    names = {i.name: i for i in db.scalars(select(Ingredient))}
    assert "turmeric powder" not in names and "wheat flour" not in names
    assert "turmeric powder" in names["turmeric"].aliases
    assert "haldi" in names["turmeric"].aliases          # Role 1's alias kept


def test_seeding_twice_changes_nothing(db):
    demo_seed.seed_demo(db, today=TODAY, now=NOW)
    counts = [_count(db, m) for m in (Ingredient, Recipe, StockItem, MealPlan, Audit)]
    again = demo_seed.seed_demo(db, today=TODAY, now=NOW)
    assert again == {"ingredients_created": [], "recipes_loaded": 0, "stock_items": 0,
                     "meals_planned": 0, "past_audits": 0}
    assert counts == [_count(db, m) for m in (Ingredient, Recipe, StockItem, MealPlan, Audit)]


@pytest.mark.parametrize("today", [date(2026, 11, 2), date(2031, 2, 28), date.today()])
def test_plan_is_relative_to_today(db, today):
    demo_seed.seed_demo(db, today=today, now=NOW)
    dates = sorted({m.date for m in db.scalars(select(MealPlan))})
    assert dates[0] == today and dates[-1] == today + timedelta(days=3)
    assert _count(db, MealPlan) == len(demo_seed.DEMO_PLAN)
    assert all(m.servings == 4 and m.status == "planned" for m in db.scalars(select(MealPlan)))


def test_stock_has_near_expiry_and_almost_empty_items(db):
    demo_seed.seed_demo(db, today=TODAY, now=NOW)
    items = {s.ingredient.name: s for s in db.scalars(select(StockItem))}
    assert items["milk"].expiry_date == TODAY + timedelta(days=1)
    assert items["tomato"].expiry_date == TODAY + timedelta(days=2)
    assert items["sugar"].quantity == D(30) and items["oil"].quantity == D(60)
    assert "besan" not in items and "cream" not in items          # genuinely missing


def test_stock_check_shows_the_designed_shortages(db, monkeypatch):
    demo_seed.seed_demo(db, today=TODAY, now=NOW)

    def fake_scaled(recipe_id, servings):                         # same maths as Role 2's
        rec = db.get(Recipe, recipe_id)
        f = D(servings) / D(rec.base_servings)
        rows = db.scalars(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id))
        return [(r.ingredient_id, r.quantity * f) for r in rows]

    monkeypatch.setattr(scaling, "get_scaled_ingredients", fake_scaled)

    today = stock.check_scope(db, "today", today=TODAY)
    ok = [m["ok"] for m in today["meals"]]
    assert ok == [True, False, False]          # Poha ok; Dal short; Khichdi short on peas
    t = {r["name"]: r for r in today["summary"]}
    assert t["toor dal"]["missing"] == D(40)   # need 240, have 200
    assert t["peas"]["missing"] == D(60)       # need 160, have 100

    week = {r["name"]: r for r in stock.check_scope(db, "week", today=TODAY)["summary"]}
    assert week["onion"]["missing"] == D(400)  # need 1100, have 700 (shared across meals)
    assert week["oil"]["missing"] == D(218)
    assert week["besan"]["missing"] == D(200)  # not in stock at all
    assert week["paneer"]["missing"] == D(110)

    items = {i["name"] for i in shopping.generate_shopping_list(db, TODAY, today=TODAY)}
    assert {"besan", "onion", "oil", "paneer", "toor dal"} <= items


def test_audit_has_something_to_find_at_the_start(db):
    demo_seed.seed_demo(db, today=TODAY, now=NOW)
    picks = audit.pick_items(db, now=NOW)
    assert len(picks) == 5
    reasons = {p["name"]: p["reason"] for p in picks}
    assert "past audits" in reasons["atta"] and "past audits" in reasons["sugar"]
    hist = audit.history(db)
    assert len(hist["audits"]) == 2
    assert hist["drift_ranking"][0]["name"] == "sugar"
    assert hist["drift_ranking"][0]["direction"] == "list too high"


def test_audit_history_can_be_skipped(db):
    summary = demo_seed.seed_demo(db, today=TODAY, now=NOW, with_audit_history=False)
    assert summary["past_audits"] == 0 and _count(db, Audit) == 0
