from math import isfinite

VALID_UNITS = {"g", "ml", "count"}
VALID_MEAL_TYPES = {"breakfast", "lunch", "dinner"}


def validate_recipe_data(recipes: list) -> bool:
    if not isinstance(recipes, list) or not recipes:
        raise ValueError("Recipe data must be a non-empty list.")

    recipe_names = set()

    for recipe in recipes:
        if not isinstance(recipe, dict):
            raise ValueError("Every recipe must be an object.")

        name = recipe.get("name")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every recipe must have a name.")

        normalized_name = name.strip().lower()

        if normalized_name in recipe_names:
            raise ValueError(f"Duplicate recipe name: {name}")

        recipe_names.add(normalized_name)

        if recipe.get("meal_type") not in VALID_MEAL_TYPES:
            raise ValueError(f"Invalid meal type in {name}.")

        servings = recipe.get("base_servings")

        if (
            not isinstance(servings, int)
            or isinstance(servings, bool)
            or servings <= 0
        ):
            raise ValueError(f"Invalid base servings in {name}.")

        ingredients = recipe.get("ingredients")

        if not isinstance(ingredients, list) or not ingredients:
            raise ValueError(f"{name} must have ingredients.")

        ingredient_names = set()

        for ingredient in ingredients:
            if not isinstance(ingredient, dict):
                raise ValueError(f"Invalid ingredient in {name}.")

            ingredient_name = ingredient.get("name")

            if (
                not isinstance(ingredient_name, str)
                or not ingredient_name.strip()
            ):
                raise ValueError(f"Invalid ingredient name in {name}.")

            normalized_ingredient = ingredient_name.strip().lower()

            if normalized_ingredient in ingredient_names:
                raise ValueError(
                    f"Duplicate ingredient '{ingredient_name}' in {name}."
                )

            ingredient_names.add(normalized_ingredient)

            quantity = ingredient.get("quantity")

            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, (int, float))
                or not isfinite(quantity)
                or quantity <= 0
            ):
                raise ValueError(
                    f"Invalid quantity for {ingredient_name} in {name}."
                )

            if ingredient.get("unit") not in VALID_UNITS:
                raise ValueError(
                    f"Invalid unit for {ingredient_name} in {name}."
                )

    return True