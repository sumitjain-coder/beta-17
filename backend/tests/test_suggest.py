
from datetime import date

from app.logic.suggest import suggest_recipes


def test_recipe_with_more_available_ingredients_ranks_higher():

    recipes = [
        {
            "name": "Dal Tadka",
            "ingredients": [
                {"name": "toor dal", "quantity": 100, "unit": "g"},
                {"name": "onion", "quantity": 50, "unit": "g"},
                {"name": "tomato", "quantity": 50, "unit": "g"}
            ]
        },
        {
            "name": "Aloo Gobi",
            "ingredients": [
                {"name": "potato", "quantity": 100, "unit": "g"},
                {"name": "cauliflower", "quantity": 100, "unit": "g"}
            ]
        }
    ]

    stock = [
        {"name": "toor dal", "quantity": 200},
        {"name": "onion", "quantity": 100},
        {"name": "tomato", "quantity": 100}
    ]

    result = suggest_recipes(recipes, stock, today=date(2026, 10, 30))

    assert result[0]["recipe_name"] == "Dal Tadka"


def test_expiring_ingredients_get_bonus():

    recipes = [
        {
            "name": "Dal Tadka",
            "ingredients": [
                {"name": "toor dal", "quantity": 100, "unit": "g"}
            ]
        },
        {
            "name": "Rice",
            "ingredients": [
                {"name": "rice", "quantity": 100, "unit": "g"}
            ]
        }
    ]

    stock = [
        {
            "name": "toor dal",
            "quantity": 200,
            "expiry_date": "2026-10-31"
        },
        {
            "name": "rice",
            "quantity": 200,
            "expiry_date": "2026-11-20"
        }
    ]

    result = suggest_recipes(recipes, stock, today=date(2026, 10, 30))

    assert result[0]["recipe_name"] == "Dal Tadka"


def test_recently_cooked_recipe_gets_penalty():

    recipes = [
        {
            "name": "Dal Tadka",
            "ingredients": [
                {"name": "toor dal", "quantity": 100, "unit": "g"}
            ]
        },
        {
            "name": "Rice",
            "ingredients": [
                {"name": "rice", "quantity": 100, "unit": "g"}
            ]
        }
    ]

    stock = [
        {"name": "toor dal", "quantity": 200},
        {"name": "rice", "quantity": 200}
    ]

    result = suggest_recipes(
        recipes,
        stock,
        recently_cooked=["Dal Tadka"],
        today=date(2026, 10, 30)
    )

    assert result[0]["recipe_name"] == "Rice"


def test_insufficient_quantity_is_marked_missing():

    recipes = [
        {
            "name": "Dal Tadka",
            "ingredients": [
                {"name": "toor dal", "quantity": 500, "unit": "g"}
            ]
        }
    ]

    stock = [
        {"name": "toor dal", "quantity": 100}
    ]

    result = suggest_recipes(
        recipes,
        stock,
        today=date(2026, 10, 30)
    )

    assert result[0]["available_ingredients"] == []
    assert result[0]["missing_ingredients"][0]["missing"] == 400


def test_multiple_stock_batches_are_combined():

    recipes = [
        {
            "name": "Dal Tadka",
            "ingredients": [
                {"name": "toor dal", "quantity": 500, "unit": "g"}
            ]
        }
    ]

    stock = [
        {"name": "toor dal", "quantity": 200},
        {"name": "toor dal", "quantity": 300}
    ]

    result = suggest_recipes(
        recipes,
        stock,
        today=date(2026, 10, 30)
    )

    assert result[0]["available_ingredients"] == ["toor dal"]
    assert result[0]["missing_ingredients"] == []
