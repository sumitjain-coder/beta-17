import datetime as dt
from decimal import Decimal
from typing import Optional
from sqlalchemy import (String, Integer, Numeric, Date, DateTime, ForeignKey,
                        Boolean, JSON, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

QTY = Numeric(12, 3)


class Household(Base):
    __tablename__ = "households"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer, default=4)


class Ingredient(Base):
    __tablename__ = "ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # canonical, lowercase
    base_unit: Mapped[str] = mapped_column(String(10))           # g / ml / count
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class StockItem(Base):
    __tablename__ = "stock_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    # one row per ingredient: entering the same item twice merges
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), unique=True)
    quantity: Mapped[Decimal] = mapped_column(QTY, default=0)    # base unit
    expiry_date: Mapped[Optional[dt.date]] = mapped_column(Date, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now())
    ingredient: Mapped[Ingredient] = relationship()


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    delta: Mapped[Decimal] = mapped_column(QTY)
    reason: Mapped[str] = mapped_column(String(20))              # manual / meal_done / audit
    meal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("meal_plan.id"), nullable=True)
    time: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class Recipe(Base):
    __tablename__ = "recipes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    meal_type: Mapped[str] = mapped_column(String(20))
    base_servings: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(20), default="seed")  # seed/user/llm_draft


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    quantity: Mapped[Decimal] = mapped_column(QTY)
    unit: Mapped[str] = mapped_column(String(20))


class MealPlan(Base):
    __tablename__ = "meal_plan"
    __table_args__ = (UniqueConstraint("date", "meal_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(20))
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    servings: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="planned")  # planned/done


class ShoppingItem(Base):
    __tablename__ = "shopping_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    quantity: Mapped[Decimal] = mapped_column(QTY)
    checked: Mapped[bool] = mapped_column(Boolean, default=False)
    for_week_start: Mapped[dt.date] = mapped_column(Date)


class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    audit_date: Mapped[dt.date] = mapped_column(Date)


class AuditItem(Base):
    __tablename__ = "audit_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    expected: Mapped[Decimal] = mapped_column(QTY)
    actual: Mapped[Decimal] = mapped_column(QTY)
