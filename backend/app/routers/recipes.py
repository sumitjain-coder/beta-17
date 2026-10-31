
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Recipe, RecipeIngredient, Ingredient
from app.logic.units import to_base, UnknownConversion

router = APIRouter(tags=["recipes"])


class RecipeIngredientIn(BaseModel):
    ingredient: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str


class RecipeIn(BaseModel):
    name: str = Field(min_length=1)
    meal_type: str
    base_servings: int = Field(gt=0)
    ingredients: list[RecipeIngredientIn]


def find_ingredient(db: Session, name: str):
    search_name = name.strip().lower()

    for ingredient in db.scalars(select(Ingredient)):
        if (
            ingredient.name.lower() == search_name
            or search_name in [
                alias.lower() for alias in (ingredient.aliases or [])
            ]
        ):
            return ingredient

    raise HTTPException(
        status_code=404,
        detail=f"Ingredient '{name}' not found"
    )


@router.post("/recipes", status_code=201)
def create_recipe(body: RecipeIn, db: Session = Depends(get_db)):

    if not body.ingredients:
        raise HTTPException(400, "Recipe must contain ingredients")

    recipe = Recipe(
        name=body.name,
        meal_type=body.meal_type.lower(),
        base_servings=body.base_servings,
        source="user"
    )

    db.add(recipe)
    db.flush()

    try:
        for item in body.ingredients:
            ingredient = find_ingredient(db, item.ingredient)

            quantity = to_base(
                item.quantity,
                item.unit,
                ingredient.name,
                ingredient.base_unit
            )

            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=Decimal(str(quantity)),
                    unit=ingredient.base_unit
                )
            )

        db.commit()
        db.refresh(recipe)

        return {
            "id": recipe.id,
            "name": recipe.name,
            "meal_type": recipe.meal_type,
            "base_servings": recipe.base_servings,
            "message": "Recipe created successfully"
        }

    except Exception as e:
        db.rollback()

        if isinstance(e, HTTPException):
            raise e

        if isinstance(e, UnknownConversion):
            raise HTTPException(422, str(e))

        raise


@router.get("/recipes")
def list_recipes(db: Session = Depends(get_db)):
    recipes = db.scalars(select(Recipe)).all()

    result = []

    for recipe in recipes:
        ingredients = db.scalars(
            select(RecipeIngredient).where(
                RecipeIngredient.recipe_id == recipe.id
            )
        ).all()

        result.append({
            "id": recipe.id,
            "name": recipe.name,
            "meal_type": recipe.meal_type,
            "base_servings": recipe.base_servings,
            "ingredients": [
                {
                    "ingredient_id": item.ingredient_id,
                    "quantity": float(item.quantity),
                    "unit": item.unit
                }
                for item in ingredients
            ]
        })

    return result
@router.get("/recipes/{recipe_id}")
def get_recipe(
    recipe_id: int,
    servings: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db)
):
    recipe = db.get(Recipe, recipe_id)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found"
        )

    requested_servings = servings or recipe.base_servings

    factor = Decimal(requested_servings) / Decimal(recipe.base_servings)

    rows = db.execute(
        select(RecipeIngredient, Ingredient)
        .join(
            Ingredient,
            RecipeIngredient.ingredient_id == Ingredient.id
        )
        .where(RecipeIngredient.recipe_id == recipe_id)
    ).all()

    ingredients = []

    for item, ingredient in rows:
        scaled_quantity = Decimal(str(item.quantity)) * factor

        ingredients.append({
            "ingredient_id": ingredient.id,
            "name": ingredient.name,
            "quantity": float(scaled_quantity),
            "unit": item.unit
        })

    return {
        "id": recipe.id,
        "name": recipe.name,
        "meal_type": recipe.meal_type,
        "base_servings": recipe.base_servings,
        "servings": requested_servings,
        "ingredients": ingredients
    }