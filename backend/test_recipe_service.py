from app.logic.recipe_service import get_or_generate_recipe


# Test an existing recipe
result1 = get_or_generate_recipe(
    dish_name="Dal Tadka",
    servings=2
)

print("Existing recipe:")
print(result1)


# Test a new recipe (calls Gemini)
result2 = get_or_generate_recipe(
    dish_name="Mushroom Masala",
    servings=3,
    meal_type="dinner"
)

print("\nGenerated recipe:")
print(result2)