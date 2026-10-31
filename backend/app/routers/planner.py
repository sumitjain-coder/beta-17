
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MealPlan, Recipe

router = APIRouter(tags=["planner"])


class PlanMealIn(BaseModel):
    recipe_id: int = Field(gt=0)
    servings: int = Field(gt=0)


@router.get("/plan")
def get_plan(
    start: date,
    db: Session = Depends(get_db)
):
    """Return a 7-day meal plan starting from the given date."""

    end = start + timedelta(days=6)

    rows = db.execute(
        select(MealPlan, Recipe)
        .join(Recipe, MealPlan.recipe_id == Recipe.id)
        .where(
            MealPlan.date >= start,
            MealPlan.date <= end
        )
        .order_by(MealPlan.date, MealPlan.meal_type)
    ).all()

    return {
        "start_date": str(start),
        "end_date": str(end),
        "meals": [
            {
                "id": meal.id,
                "date": str(meal.date),
                "meal_type": meal.meal_type,
                "recipe_id": meal.recipe_id,
                "recipe_name": recipe.name,
                "servings": meal.servings,
                "status": meal.status
            }
            for meal, recipe in rows
        ]
    }


@router.put("/plan/{plan_date}/{meal_type}")
def update_plan(
    plan_date: date,
    meal_type: str,
    body: PlanMealIn,
    db: Session = Depends(get_db)
):
    """Create or update a meal for a particular date and meal type."""

    meal_type = meal_type.strip().lower()

    if not meal_type:
        raise HTTPException(400, "Meal type cannot be empty")

    recipe = db.get(Recipe, body.recipe_id)

    if recipe is None:
        raise HTTPException(404, "Recipe not found")

    meal = db.scalar(
        select(MealPlan).where(
            MealPlan.date == plan_date,
            MealPlan.meal_type == meal_type
        )
    )

    if meal:
        meal.recipe_id = body.recipe_id
        meal.servings = body.servings
        meal.status = "planned"
        message = "Meal plan updated successfully"
    else:
        meal = MealPlan(
            date=plan_date,
            meal_type=meal_type,
            recipe_id=body.recipe_id,
            servings=body.servings,
            status="planned"
        )
        db.add(meal)
        message = "Meal planned successfully"

    db.commit()
    db.refresh(meal)

    return {
        "id": meal.id,
        "date": str(meal.date),
        "meal_type": meal.meal_type,
        "recipe_id": meal.recipe_id,
        "recipe_name": recipe.name,
        "servings": meal.servings,
        "status": meal.status,
        "message": message
    }
