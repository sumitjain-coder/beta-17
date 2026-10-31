
from decimal import Decimal
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Recipe, RecipeIngredient


def get_scaled_ingredients(recipe_id: int, servings: int):
    """Return (ingredient_id, required_quantity_in_base_unit) pairs."""

    if servings <= 0:
        raise ValueError("Servings must be greater than zero.")

    with SessionLocal() as db:
        recipe = db.get(Recipe, recipe_id)

        if recipe is None:
            raise LookupError(f"Recipe {recipe_id} not found.")

        ingredients = db.scalars(
            select(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe_id
            )
        ).all()

        factor = Decimal(servings) / Decimal(recipe.base_servings)

        return [
            (item.ingredient_id, item.quantity * factor)
            for item in ingredients
        ]
