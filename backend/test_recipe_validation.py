import pytest

from app.logic.recipe_validation import validate_recipe_data


def valid_recipe():
    return [{
        "name": "Dal Tadka",
        "meal_type": "lunch",
        "base_servings": 2,
        "ingredients": [
            {"name": "toor dal", "quantity": 100, "unit": "g"},
            {"name": "onion", "quantity": 50, "unit": "g"}
        ]
    }]


def test_valid_recipe_data():
    assert validate_recipe_data(valid_recipe()) is True


def test_duplicate_recipe_names():
    recipes = valid_recipe() * 2

    with pytest.raises(ValueError, match="Duplicate recipe name"):
        validate_recipe_data(recipes)


def test_duplicate_ingredients():
    recipes = valid_recipe()
    recipes[0]["ingredients"].append({
        "name": "Toor Dal",
        "quantity": 50,
        "unit": "g"
    })

    with pytest.raises(ValueError, match="Duplicate ingredient"):
        validate_recipe_data(recipes)


def test_invalid_unit():
    recipes = valid_recipe()
    recipes[0]["ingredients"][0]["unit"] = "kg"

    with pytest.raises(ValueError, match="Invalid unit"):
        validate_recipe_data(recipes)


def test_invalid_quantity():
    recipes = valid_recipe()
    recipes[0]["ingredients"][0]["quantity"] = -10

    with pytest.raises(ValueError, match="Invalid quantity"):
        validate_recipe_data(recipes)


def test_empty_recipe_list():
    with pytest.raises(ValueError):
        validate_recipe_data([])