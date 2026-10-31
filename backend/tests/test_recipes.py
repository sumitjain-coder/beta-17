
import pytest

from app.logic.recipes import (
    load_recipes,
    get_recipe_by_name,
    get_recipes_by_meal_type,
    search_recipes,
    get_scaled_recipe
)


def test_load_all_recipes():
    recipes = load_recipes()

    assert len(recipes) == 31


def test_get_recipe_by_name():
    recipe = get_recipe_by_name("Dal Tadka")

    assert recipe is not None
    assert recipe["name"] == "Dal Tadka"


def test_get_recipe_case_insensitive():
    recipe = get_recipe_by_name("dal tadka")

    assert recipe is not None


def test_get_nonexistent_recipe():
    recipe = get_recipe_by_name("Unknown Dish")

    assert recipe is None


def test_filter_breakfast_recipes():
    recipes = get_recipes_by_meal_type("breakfast")

    assert len(recipes) > 0
    assert all(r["meal_type"] == "breakfast" for r in recipes)


def test_search_recipes():
    recipes = search_recipes("paneer")

    assert len(recipes) > 0
    assert all("paneer" in r["name"].lower() for r in recipes)


def test_scaled_recipe():
    result = get_scaled_recipe("Dal Tadka", 4)

    assert result[0]["quantity"] == 240
