
from app.logic.recipe_validation import validate_recipe_data
import json
from pathlib import Path

# Locate recipes.json relative to this Python file.
RECIPE_FILE = (
    Path(__file__).resolve().parent.parent
    / "seed_data"
    / "recipes.json"
)


def load_recipes() -> list:
    with open(RECIPE_FILE, "r", encoding="utf-8") as file:
        recipes = json.load(file)

    validate_recipe_data(recipes)

    return recipes


def get_recipe_by_name(name: str):
    """Find a recipe using its name (case-insensitive)."""

    recipes = load_recipes()

    for recipe in recipes:
        if recipe["name"].strip().lower() == name.strip().lower():
            return recipe

    return None


def get_recipes_by_meal_type(meal_type: str) -> list:
    """Return recipes belonging to breakfast, lunch or dinner."""

    recipes = load_recipes()

    return [
        recipe for recipe in recipes
        if recipe["meal_type"].lower() == meal_type.strip().lower()
    ]


def search_recipes(keyword: str) -> list:
    """Search recipes by partial name."""

    recipes = load_recipes()
    keyword = keyword.strip().lower()

    if not keyword:
        return []

    return [
        recipe for recipe in recipes
        if keyword in recipe["name"].lower()
    ]


def get_scaled_recipe(name: str, servings: int):
    """Find a recipe and return its scaled ingredients."""

    from app.logic.scaling import scale_recipe

    recipe = get_recipe_by_name(name)

    if recipe is None:
        raise ValueError(f"Recipe '{name}' not found.")

    return scale_recipe(recipe, servings)
