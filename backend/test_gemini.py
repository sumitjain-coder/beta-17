from dotenv import load_dotenv
from app.llm.recipe_estimator import generate_recipe_draft

# Load API key from the project's root .env file
load_dotenv("../.env")

try:
    recipe = generate_recipe_draft(
        dish_name="Mushroom Masala",
        servings=3,
        meal_type="dinner"
    )

    print("\nGemini API working successfully!")
    print("\nGenerated recipe:")
    print(recipe)

except Exception as error:
    print("\nGemini API test failed:")
    print(error)