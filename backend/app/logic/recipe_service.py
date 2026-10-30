from app.logic.recipes import get_recipe_by_name
from app.llm.recipe_estimator import (
    generate_recipe_draft,
    RecipeGenerationError
)


def get_or_generate_recipe(
    dish_name: str,
    servings: int = 2,
    meal_type: str | None = None
) -> dict:

    if not dish_name or not dish_name.strip():
        raise ValueError("Dish name cannot be empty.")

    if not isinstance(servings, int) or isinstance(servings, bool) or servings <= 0:
        raise ValueError("Servings must be a positive integer.")

    # Check predefined recipes first.
    existing_recipe = get_recipe_by_name(dish_name)

    if existing_recipe:
        return {
            "source": "seed",
            "requires_review": False,
            "recipe": existing_recipe
        }

    # Generate a new recipe using Gemini.
    try:
        generated_recipe = generate_recipe_draft(
            dish_name=dish_name,
            servings=servings,
            meal_type=meal_type
        )

        return {
            "source": "llm_draft",
            "requires_review": True,
            "recipe": generated_recipe,
            "message": "Please review this AI-generated recipe."
        }

    except RecipeGenerationError as error:
        return {
            "source": "llm_unavailable",
            "requires_review": False,
            "recipe": None,
            "message": (
                "AI recipe generation is temporarily unavailable. "
                "Please try again later."
            )
        }