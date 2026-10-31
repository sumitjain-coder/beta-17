
import json
from pathlib import Path
from decimal import Decimal

from app.db import SessionLocal
from app.models import Ingredient, Recipe, RecipeIngredient
from app.logic.units import to_base


DATA_FILE = Path(__file__).parent / "seed_data" / "recipes.json"


def seed_recipes():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        recipes_data = json.load(file)

    db = SessionLocal()

    try:
        # Load existing ingredients
        ingredients = db.query(Ingredient).all()

        # Build lookup using canonical names and aliases
        ingredient_lookup = {}

        for ingredient in ingredients:
            ingredient_lookup[ingredient.name.lower()] = ingredient

            for alias in (ingredient.aliases or []):
                ingredient_lookup[alias.lower()] = ingredient

        # Add missing ingredients and recipes
        added_ingredients = 0
        added_recipes = 0
        skipped_recipes = 0

        for recipe_data in recipes_data:

            # Skip recipes that already exist
            existing_recipe = (
                db.query(Recipe)
                .filter(Recipe.name == recipe_data["name"])
                .first()
            )

            if existing_recipe:
                skipped_recipes += 1
                continue

            recipe = Recipe(
                name=recipe_data["name"],
                meal_type=recipe_data["meal_type"],
                base_servings=recipe_data["base_servings"],
                source="seed",
            )

            db.add(recipe)
            db.flush()

            for item in recipe_data["ingredients"]:
                name = item["name"].strip().lower()
                unit = item["unit"].strip().lower()

                ingredient = ingredient_lookup.get(name)

                # Create missing ingredient
                if ingredient is None:
                    ingredient = Ingredient(
                        name=name,
                        base_unit=unit,
                        aliases=[],
                    )

                    db.add(ingredient)
                    db.flush()

                    ingredient_lookup[name] = ingredient
                    added_ingredients += 1

                # Convert quantity into the ingredient's base unit
                quantity = to_base(
                    item["quantity"],
                    unit,
                    ingredient.name,
                    ingredient.base_unit,
                )

                db.add(
                    RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=ingredient.id,
                        quantity=quantity,
                        unit=ingredient.base_unit,
                    )
                )

            added_recipes += 1

        db.commit()

        print("\nRecipe seeding completed!")
        print(f"Recipes added: {added_recipes}")
        print(f"Recipes skipped: {skipped_recipes}")
        print(f"New ingredients added: {added_ingredients}")

        print(
            "Total recipes in database:",
            db.query(Recipe).count()
        )
        print(
            "Total ingredients in database:",
            db.query(Ingredient).count()
        )
        print(
            "Total recipe ingredients:",
            db.query(RecipeIngredient).count()
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_recipes()
