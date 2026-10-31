
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import MealPlan, Recipe

router = APIRouter(tags=["meals"])


class MealIn(BaseModel):
    date: date
    meal_type: str = Field(min_length=1)
    recipe_id: int = Field(gt=0)
    servings: int = Field(gt=0)


@router.post("/meals", status_code=201)
def create_meal(body: MealIn, db: Session = Depends(get_db)):

    recipe = db.get(Recipe, body.recipe_id)

    if not recipe:
        raise HTTPException(404, "Recipe not found")

    meal_type = body.meal_type.strip().lower()

    existing = db.scalar(
        select(MealPlan).where(
            MealPlan.date == body.date,
            MealPlan.meal_type == meal_type
        )
    )

    if existing:
        raise HTTPException(
            409,
            "A meal is already planned for this date and meal type"
        )

    meal = MealPlan(
        date=body.date,
        meal_type=meal_type,
        recipe_id=body.recipe_id,
        servings=body.servings,
        status="planned"
    )

    db.add(meal)
    db.commit()
    db.refresh(meal)

    return {
        "id": meal.id,
        "date": str(meal.date),
        "meal_type": meal.meal_type,
        "recipe_id": meal.recipe_id,
        "servings": meal.servings,
        "status": meal.status,
        "message": "Meal scheduled successfully"
    }


@router.get("/meals")
def list_meals(db: Session = Depends(get_db)):

    meals = db.scalars(
        select(MealPlan).order_by(MealPlan.date, MealPlan.meal_type)
    ).all()

    return [
        {
            "id": meal.id,
            "date": str(meal.date),
            "meal_type": meal.meal_type,
            "recipe_id": meal.recipe_id,
            "servings": meal.servings,
            "status": meal.status
        }
        for meal in meals
    ]
