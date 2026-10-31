from datetime import date, timedelta

import pytest

from app.logic.suggest import suggest_recipes


TODAY = date(2026, 10, 31)


def test_expiry_bonus_is_proportional():
    recipes = [{
        "name": "Tomato Dal",
        "ingredients": [
            {"name": "tomato", "quantity": 100, "unit": "g"},
            {"name": "onion", "quantity": 100, "unit": "g"}
        ]
    }]

    stock = [
        {
            "name": "tomato",
            "quantity": 20,
            "expiry_date": TODAY + timedelta(days=1)
        },
        {
            "name": "onion",
            "quantity": 100,
            "expiry_date": TODAY + timedelta(days=10)
        }
    ]

    result = suggest_recipes(recipes, stock, today=TODAY)

    # Coverage = 35; expiry bonus = 2.
    assert result[0]["score"] == 37


def test_expired_stock_is_ignored():
    recipes = [{
        "name": "Simple Dal",
        "ingredients": [
            {"name": "toor dal", "quantity": 100, "unit": "g"}
        ]
    }]

    stock = [{
        "name": "toor dal",
        "quantity": 500,
        "expiry_date": TODAY - timedelta(days=1)
    }]

    result = suggest_recipes(recipes, stock, today=TODAY)

    assert result[0]["score"] == 0
    assert result[0]["missing_ingredients"][0]["missing"] == 100


def test_duplicate_stock_entries_are_combined():
    recipes = [{
        "name": "Simple Dal",
        "ingredients": [
            {"name": "toor dal", "quantity": 100, "unit": "g"}
        ]
    }]

    stock = [
        {"name": "toor dal", "quantity": 40},
        {"name": "Toor Dal", "quantity": 60}
    ]

    result = suggest_recipes(recipes, stock, today=TODAY)

    assert result[0]["score"] == 70
    assert result[0]["missing_ingredients"] == []


def test_invalid_stock_quantity():
    recipes = [{
        "name": "Simple Dal",
        "ingredients": [
            {"name": "toor dal", "quantity": 100, "unit": "g"}
        ]
    }]

    stock = [{
        "name": "toor dal",
        "quantity": -50
    }]

    with pytest.raises(ValueError):
        suggest_recipes(recipes, stock, today=TODAY)