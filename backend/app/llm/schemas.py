from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecipeIngredient(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    name: str = Field(min_length=1)
    quantity: float
    unit: Literal["g", "ml", "count"]

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value):
        if value <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return value


class RecipeDraft(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True
    )

    name: str = Field(min_length=1)
    meal_type: Literal["breakfast", "lunch", "dinner"]
    base_servings: int
    ingredients: list[RecipeIngredient] = Field(min_length=1)

    @field_validator("base_servings")
    @classmethod
    def validate_servings(cls, value):
        if value <= 0:
            raise ValueError("Base servings must be positive.")
        return value