
import re
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Recipe, RecipeIngredient, Ingredient
from app.logic.units import to_base, UnknownConversion

from app.llm.recipe_estimator import (
    generate_recipe_draft,
    RecipeGenerationError
)

def normalize_ingredient_name(name: str) -> str:
    """
    Normalize ingredient names for consistent matching.
    """
    name = name.strip().lower()

    # Treat hyphens and underscores as spaces.
    name = re.sub(r"[-_]", " ", name)

    # Remove unnecessary punctuation.
    name = re.sub(r"[^\w\s]", "", name)

    # Collapse multiple spaces.
    name = re.sub(r"\s+", " ", name)

    return name

router = APIRouter(tags=["recipes"])


# -----------------------------
# Request schemas
# -----------------------------

class RecipeIngredientIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    ingredient: str = Field(min_length=1)
    quantity: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(min_length=1)


class RecipeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    meal_type: Literal["breakfast", "lunch", "dinner"]
    base_servings: int = Field(gt=0)
    ingredients: list[RecipeIngredientIn] = Field(min_length=1)

    @field_validator("meal_type", mode="before")
    @classmethod
    def normalize_meal_type(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

class RecipeEstimateIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    dish_name: str = Field(min_length=1)
    servings: int = Field(default=2, gt=0)
    meal_type: Literal["breakfast", "lunch", "dinner"] | None = None

class RecipeDraftIngredientIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    quantity: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(min_length=1)


class RecipeDraftSaveIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    meal_type: Literal["breakfast", "lunch", "dinner"]
    base_servings: int = Field(gt=0)
    ingredients: list[RecipeDraftIngredientIn] = Field(min_length=1)

    @field_validator("meal_type", mode="before")
    @classmethod
    def normalize_meal_type(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

# -----------------------------
# Ingredient lookup helpers
# -----------------------------

def build_ingredient_lookup(db: Session):
    """
    Load ingredients once and create a lookup dictionary
    using normalized canonical names and aliases.
    """
    ingredients = db.scalars(select(Ingredient)).all()

    lookup = {}

    for ingredient in ingredients:

        canonical_name = normalize_ingredient_name(
            ingredient.name
        )

        lookup[canonical_name] = ingredient

        for alias in ingredient.aliases or []:
            normalized_alias = normalize_ingredient_name(alias)

            if normalized_alias:
                lookup.setdefault(normalized_alias, ingredient)

    return lookup


def find_ingredient(name: str, ingredient_lookup: dict):
    search_name = normalize_ingredient_name(name)

    ingredient = ingredient_lookup.get(search_name)

    return ingredient

# -----------------------------
# Create recipe
# -----------------------------

@router.post("/recipes", status_code=201)
def create_recipe(
    body: RecipeIn,
    db: Session = Depends(get_db)
):

    try:
        # Load ingredients only once.
        ingredient_lookup = build_ingredient_lookup(db)

        # Create the recipe.
        recipe = Recipe(
            name=body.name,
            meal_type=body.meal_type,
            base_servings=body.base_servings,
            source="user"
        )

        db.add(recipe)
        db.flush()

        # Prevent the same canonical ingredient from
        # being added multiple times to one recipe.
        used_ingredient_ids = set()

        for item in body.ingredients:

            ingredient = find_ingredient(
                item.ingredient,
                ingredient_lookup
            )

            if ingredient.id in used_ingredient_ids:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Duplicate ingredient '{ingredient.name}' "
                        "in the recipe"
                    )
                )

            used_ingredient_ids.add(ingredient.id)

            # Convert the supplied quantity to the
            # ingredient's canonical base unit.
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

    except UnknownConversion as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception:
        db.rollback()
        raise


# -----------------------------
# List all recipes
# -----------------------------

@router.get("/recipes")
def list_recipes(db: Session = Depends(get_db)):

    recipes = db.scalars(select(Recipe)).all()

    if not recipes:
        return []

    recipe_ids = [recipe.id for recipe in recipes]

    # Fetch all recipe ingredients in one query
    # instead of querying separately for every recipe.
    rows = db.execute(
        select(RecipeIngredient).where(
            RecipeIngredient.recipe_id.in_(recipe_ids)
        )
    ).scalars().all()

    ingredients_by_recipe = {
        recipe_id: [] for recipe_id in recipe_ids
    }

    for item in rows:
        ingredients_by_recipe[item.recipe_id].append({
            "ingredient_id": item.ingredient_id,
            "quantity": float(item.quantity),
            "unit": item.unit
        })

    result = []

    for recipe in recipes:
        result.append({
            "id": recipe.id,
            "name": recipe.name,
            "meal_type": recipe.meal_type,
            "base_servings": recipe.base_servings,
            "ingredients": ingredients_by_recipe[recipe.id]
        })

    return result


@router.post("/recipes/estimate")
def estimate_recipe(body: RecipeEstimateIn):

    try:
        draft = generate_recipe_draft(
            dish_name=body.dish_name,
            servings=body.servings,
            meal_type=body.meal_type
        )

        return {
            "status": "draft",
            "message": "Recipe generated successfully. Review before saving.",
            "recipe": draft
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except RecipeGenerationError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        )

@router.post("/recipes/estimate/save", status_code=201)
def save_estimated_recipe(
    body: RecipeDraftSaveIn,
    db: Session = Depends(get_db)
):
    try:
        # Check for duplicate recipe names.
        existing_recipe = db.scalars(
            select(Recipe).where(
                Recipe.name.ilike(body.name.strip())
            )
        ).first()

        if existing_recipe:
            raise HTTPException(
                status_code=409,
                detail="A recipe with this name already exists."
            )

        # Load canonical ingredients and aliases.
        ingredient_lookup = build_ingredient_lookup(db)

        prepared_ingredients = []
        used_ingredient_ids = set()
        missing_ingredients = []

        # First pass: identify all missing ingredients.
        for item in body.ingredients:

            ingredient = find_ingredient(
                item.name,
                ingredient_lookup
            )

            if ingredient is None:
                missing_ingredients.append(item.name)
                continue

            if ingredient.id in used_ingredient_ids:
                raise HTTPException(
                    status_code=422,
                    detail=f"Duplicate ingredient: '{ingredient.name}'"
                )

            used_ingredient_ids.add(ingredient.id)

            # Convert to the canonical base unit.
            quantity = to_base(
                item.quantity,
                item.unit,
                ingredient.name,
                ingredient.base_unit
            )

            prepared_ingredients.append({
                "ingredient_id": ingredient.id,
                "quantity": Decimal(str(quantity)),
                "unit": ingredient.base_unit
            })

        # Report all missing ingredients together.
        if missing_ingredients:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Some ingredients are not present in the database.",
                    "missing_ingredients": missing_ingredients
                }
            )

        # Create recipe only after all validation succeeds.
        recipe = Recipe(
            name=body.name.strip(),
            meal_type=body.meal_type,
            base_servings=body.base_servings,
            source="llm_draft"
        )

        db.add(recipe)
        db.flush()

        # Insert recipe ingredients.
        for item in prepared_ingredients:
            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=item["ingredient_id"],
                    quantity=item["quantity"],
                    unit=item["unit"]
                )
            )

        db.commit()
        db.refresh(recipe)

        return {
            "status": "saved",
            "message": "Gemini recipe saved successfully.",
            "recipe": {
                "id": recipe.id,
                "name": recipe.name,
                "meal_type": recipe.meal_type,
                "base_servings": recipe.base_servings,
                "source": recipe.source
            }
        }

    except HTTPException:
        db.rollback()
        raise

    except UnknownConversion as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception:
        db.rollback()
        raise        
# -----------------------------
# Get one recipe with scaling
# -----------------------------

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

    requested_servings = (
        servings if servings is not None
        else recipe.base_servings
    )

    factor = (
        Decimal(requested_servings)
        / Decimal(recipe.base_servings)
    )

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

        scaled_quantity = (
            Decimal(str(item.quantity)) * factor
        )

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
