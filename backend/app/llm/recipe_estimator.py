
import os
from pathlib import Path
from dotenv import load_dotenv

from app.llm.schemas import RecipeDraft


# Load .env from the project root
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(ENV_FILE)


class RecipeGenerationError(Exception):
    """Raised when an AI recipe cannot be generated or validated."""


def generate_recipe_draft(
    dish_name: str,
    servings: int = 2,
    meal_type: str | None = None
) -> dict:
    """
    Generate a vegetarian recipe using Gemini.

    Returns a Pydantic-validated recipe dictionary.
    """

    dish_name = dish_name.strip()

    if not dish_name:
        raise ValueError("Dish name cannot be empty.")

    if not isinstance(servings, int) or isinstance(servings, bool) or servings <= 0:
        raise ValueError("Servings must be a positive integer.")

    if meal_type is not None and meal_type not in {
        "breakfast", "lunch", "dinner"
    }:
        raise ValueError("Invalid meal type.")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RecipeGenerationError(
            "Gemini API key is not configured."
        )

    try:
        from google import genai
        from google.genai import types

        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""
        Create a practical Indian vegetarian recipe.

        Dish name: {dish_name}
        Number of servings: {servings}
        Requested meal type: {meal_type or "Choose an appropriate meal type"}

        Requirements:
        1. The recipe must be vegetarian.
        2. Include realistic ingredient quantities for the requested servings.
        3. Use grams (g), millilitres (ml), or count for units.
        4. Do not include cooking instructions or extra fields.
        5. Return the recipe name, meal type, base servings and ingredients.
        6. Do not invent stock availability.
        """

        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "name": types.Schema(type=types.Type.STRING),
            "meal_type": types.Schema(
                type=types.Type.STRING,
                enum=["breakfast", "lunch", "dinner"]
            ),
            "base_servings": types.Schema(type=types.Type.INTEGER),
            "ingredients": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(type=types.Type.STRING),
                        "quantity": types.Schema(type=types.Type.NUMBER),
                        "unit": types.Schema(
                            type=types.Type.STRING,
                            enum=["g", "ml", "count"]
                        )
                    },
                    required=["name", "quantity", "unit"]
                )
            )
        },
        required=[
            "name",
            "meal_type",
            "base_servings",
            "ingredients"
        ]
    )
)
        )

        if not response.text:
            raise RecipeGenerationError(
                "Gemini returned an empty response."
            )

        # Validate Gemini's response using Pydantic.
        recipe = RecipeDraft.model_validate_json(response.text)

        # Add the source expected by our database design.
        result = recipe.model_dump()
        result["source"] = "llm_draft"

        return result

    except RecipeGenerationError:
        raise

    except Exception as error:
        print("Gemini API error:", repr(error))
        raise RecipeGenerationError(
            "Failed to generate recipe."
        ) from error
