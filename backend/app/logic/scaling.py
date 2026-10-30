
from decimal import Decimal, InvalidOperation


def scale_recipe(recipe: dict, servings: int) -> list[dict]:
    """
    Scale a recipe's ingredient quantities for the requested servings.

    Args:
        recipe: Recipe dictionary loaded from recipes.json.
        servings: Number of people to cook for.

    Returns:
        List of ingredients with scaled quantities.
    """

    if not isinstance(servings, int) or isinstance(servings, bool) or servings <= 0:
        raise ValueError("Servings must be a positive integer.")

    base_servings = recipe.get("base_servings")

    if not isinstance(base_servings, int) or isinstance(base_servings, bool) or base_servings <= 0:
        raise ValueError("Recipe must have a valid positive base_servings.")

    ingredients = recipe.get("ingredients")

    if not isinstance(ingredients, list) or not ingredients:
        raise ValueError("Recipe must contain at least one ingredient.")

    scaling_factor = Decimal(servings) / Decimal(base_servings)

    scaled_ingredients = []

    for ingredient in ingredients:

        try:
            original_quantity = Decimal(str(ingredient["quantity"]))
        except (KeyError, InvalidOperation, ValueError):
            raise ValueError("Every ingredient must have a valid quantity.")

        if not original_quantity.is_finite() or original_quantity < 0:
            raise ValueError("Ingredient quantity cannot be negative or invalid.")

        scaled_quantity = original_quantity * scaling_factor

        # Convert to int when the result is a whole number.
        if scaled_quantity == scaled_quantity.to_integral_value():
            scaled_quantity = int(scaled_quantity)
        else:
            scaled_quantity = float(scaled_quantity)

        scaled_ingredients.append({
            "name": ingredient["name"],
            "quantity": scaled_quantity,
            "unit": ingredient["unit"]
        })

    return scaled_ingredients
