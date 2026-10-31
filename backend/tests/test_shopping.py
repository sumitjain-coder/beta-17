"""Tests for logic/shopping.py. Uses an in-memory SQLite database and a fake
get_scaled_ingredients, so no MySQL and no Role 2 data are needed."""
from datetime import date
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.logic import scaling, shopping
from app.models import (Ingredient, MealPlan, Recipe, ShoppingItem, StockItem)

MON = date(2026, 11, 2)   # a Monday


# ---------- pure function ----------
def test_pure_keeps_only_missing_and_sorts():
    summary = [
        {"ingredient_id": 2, "name": "tomato", "unit": "count", "missing": D(0)},
        {"ingredient_id": 3, "name": "onion", "unit": "count", "missing": D(2)},
        {"ingredient_id": 1, "name": "atta", "unit": "g", "missing": D("50.5")},
    ]
    rows = shopping.missing_to_shopping_rows(summary)
    assert [r["name"] for r in rows] == ["atta", "onion"]
    assert rows[0]["quantity"] == D("50.5")


def test_pure_empty():
    assert shopping.missing_to_shopping_rows([]) == []


def test_week_start_of():
    assert shopping.week_start_of(date(2026, 11, 5)) == MON   # Thursday -> Monday
    assert shopping.week_start_of(MON) == MON


# ---------- database ----------
@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        s.add_all([
            Ingredient(id=1, name="toor dal", base_unit="g"),
            Ingredient(id=2, name="onion", base_unit="count"),
            Recipe(id=1, name="dal", meal_type="lunch", base_servings=4),
            Recipe(id=2, name="sabzi", meal_type="dinner", base_servings=4),
        ])
        s.commit()
        yield s


@pytest.fixture(autouse=True)
def fake_scaling(monkeypatch):
    # recipe 1 (dal): 450 g dal + 3 onion; recipe 2 (sabzi): 3 onion
    table = {1: [(1, D(450)), (2, D(3))], 2: [(2, D(3))]}
    monkeypatch.setattr(scaling, "get_scaled_ingredients",
                        lambda recipe_id, servings: table[recipe_id])


def _plan(s, day, mtype, recipe_id, status="planned"):
    s.add(MealPlan(date=day, meal_type=mtype, recipe_id=recipe_id,
                   servings=4, status=status))
    s.commit()


def _stock(s, ing_id, qty):
    s.add(StockItem(ingredient_id=ing_id, quantity=D(qty)))
    s.commit()


def _by_name(items):
    return {i["name"]: i for i in items}


def test_week_aggregation_two_meals_share_onions(session):
    _plan(session, MON, "lunch", 1)
    _plan(session, MON, "dinner", 2)
    _stock(session, 1, 400)      # dal: need 450, have 400 -> short 50
    _stock(session, 2, 4)        # onion: need 3+3=6, have 4 -> short 2
    items = _by_name(shopping.generate_shopping_list(session, MON, today=MON))
    assert items["toor dal"]["quantity"] == D(50)
    assert items["onion"]["quantity"] == D(2)


def test_empty_stock_everything_is_missing(session):
    _plan(session, MON, "lunch", 1)
    items = _by_name(shopping.generate_shopping_list(session, MON, today=MON))
    assert items["toor dal"]["quantity"] == D(450)
    assert items["onion"]["quantity"] == D(3)


def test_nothing_planned_gives_empty_list(session):
    assert shopping.generate_shopping_list(session, MON, today=MON) == []


def test_everything_in_stock_gives_empty_list(session):
    _plan(session, MON, "lunch", 1)
    _stock(session, 1, 1000)
    _stock(session, 2, 10)
    assert shopping.generate_shopping_list(session, MON, today=MON) == []


def test_done_meals_are_not_shopped_for(session):
    _plan(session, MON, "lunch", 1, status="done")
    assert shopping.generate_shopping_list(session, MON, today=MON) == []


def test_regenerate_does_not_duplicate(session):
    _plan(session, MON, "lunch", 1)
    shopping.generate_shopping_list(session, MON, today=MON)
    shopping.generate_shopping_list(session, MON, today=MON)
    assert session.query(ShoppingItem).count() == 2


def test_regenerate_updates_quantity_and_keeps_checked(session):
    _plan(session, MON, "lunch", 1)
    items = _by_name(shopping.generate_shopping_list(session, MON, today=MON))
    shopping.set_checked(session, items["toor dal"]["id"], True)
    _stock(session, 1, 100)                     # stock changed: now short 350
    items = _by_name(shopping.generate_shopping_list(session, MON, today=MON))
    assert items["toor dal"]["quantity"] == D(350)
    assert items["toor dal"]["checked"] is True


def test_regenerate_removes_unticked_items_no_longer_missing(session):
    _plan(session, MON, "lunch", 1)
    shopping.generate_shopping_list(session, MON, today=MON)
    _stock(session, 1, 1000)
    _stock(session, 2, 10)
    assert shopping.generate_shopping_list(session, MON, today=MON) == []


def test_past_meals_are_skipped(session):
    _plan(session, MON, "lunch", 1)             # Monday, but today is Wednesday
    wed = date(2026, 11, 4)
    assert shopping.generate_shopping_list(session, MON, today=wed) == []


def test_set_checked_unknown_id_raises(session):
    with pytest.raises(LookupError):
        shopping.set_checked(session, 999, True)
