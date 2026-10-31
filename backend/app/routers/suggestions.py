
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Recipe, RecipeIngredient, Ingredient, StockItem, MealPlan
from app.logic.suggest import suggest_recipes

router = APIRouter(tags=["suggestions"])


@router.get("/suggestions")
def get_suggestions(
    date_for: date = Query(default=None, alias="date"),
    meal_type: str = Query(default=None),
    db: Session = Depends(get_db)
):
    target_date = date_for or date.today()

    if meal_type:
        meal_type = meal_type.strip().lower()
        if meal_type not in {"breakfast", "lunch", "dinner"}:
            raise HTTPException(
                status_code=422,
                detail="Meal type must be breakfast, lunch or dinner."
            )

    # Fetch recipes and their ingredients.
    recipes = db.scalars(select(Recipe)).all()

    recipe_data = []

    for recipe in recipes:
        if meal_type and recipe.meal_type != meal_type:
            continue

        items = db.scalars(
            select(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe.id
            )
        ).all()

        ingredients = []

        for item in items:
            ingredient = db.get(Ingredient, item.ingredient_id)

            ingredients.append({
                "name": ingredient.name,
                "quantity": float(item.quantity),
                "unit": ingredient.base_unit
            })

        recipe_data.append({
            "id": recipe.id,
            "name": recipe.name,
            "meal_type": recipe.meal_type,
            "base_servings": recipe.base_servings,
            "ingredients": ingredients
        })

    # Fetch current stock.
    stock_items = db.scalars(select(StockItem)).all()

    stock_data = [
        {
            "name": item.ingredient.name,
            "quantity": float(item.quantity),
            "expiry_date": item.expiry_date
        }
        for item in stock_items
    ]

    # Recipes cooked during the previous seven days.
    recent_meals = db.scalars(
        select(MealPlan).where(
            MealPlan.status == "done",
            MealPlan.date >= target_date - timedelta(days=7),
            MealPlan.date < target_date
        )
    ).all()

    recently_cooked = []

    for meal in recent_meals:
        recipe = db.get(Recipe, meal.recipe_id)
        if recipe:
            recently_cooked.append(recipe.name)

    try:
        results = suggest_recipes(
            recipes=recipe_data,
            stock=stock_data,
            recently_cooked=recently_cooked,
            today=target_date
        )
    except (ValueError, TypeError) as error:
        raise HTTPException(422, str(error))

    # Include database IDs and serving information.
    recipe_lookup = {
        recipe["name"]: recipe for recipe in recipe_data
    }

    for result in results:
        recipe = recipe_lookup[result["recipe_name"]]
        result["recipe_id"] = recipe["id"]
        result["meal_type"] = recipe["meal_type"]
        result["base_servings"] = recipe["base_servings"]

    return {
        "date": str(target_date),
        "meal_type": meal_type,
        "suggestions": results
    }
