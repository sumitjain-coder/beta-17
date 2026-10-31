from datetime import date
from decimal import Decimal as D
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Ingredient, StockItem, StockMovement
from app.logic import stock as stock_logic
from app.logic.units import to_base, UnknownConversion

router = APIRouter(tags=["stock"])


class StockIn(BaseModel):
    ingredient: str = Field(min_length=1)       # name or alias
    quantity: float = Field(gt=0)
    unit: str
    expiry_date: Optional[date] = None


class StockPatch(BaseModel):
    quantity: float = Field(ge=0)
    unit: str
    expiry_date: Optional[date] = None


def find_ingredient(db: Session, text: str) -> Ingredient:
    """Match canonical name OR alias, case-insensitive (handles two spellings)."""
    t = text.strip().lower()
    for ing in db.scalars(select(Ingredient)):
        if ing.name == t or t in [a.lower() for a in (ing.aliases or [])]:
            return ing
    raise HTTPException(404, f"Unknown ingredient '{text}'. Create it first.")


def _row(s: StockItem) -> dict:
    return {"id": s.id, "ingredient_id": s.ingredient_id, "name": s.ingredient.name,
            "quantity": s.quantity, "unit": s.ingredient.base_unit,
            "expiry_date": s.expiry_date}


@router.get("/stock")
def list_stock(db: Session = Depends(get_db)):
    return [_row(s) for s in db.scalars(select(StockItem))]


@router.post("/stock", status_code=201)
def add_stock(body: StockIn, db: Session = Depends(get_db)):
    ing = find_ingredient(db, body.ingredient)
    try:
        qty = to_base(body.quantity, body.unit, ing.name, ing.base_unit)
    except UnknownConversion as e:
        raise HTTPException(422, str(e))
    return _row(stock_logic.add_stock(db, ing.id, qty, expiry=body.expiry_date))


@router.patch("/stock/{item_id}")
def patch_stock(item_id: int, body: StockPatch, db: Session = Depends(get_db)):
    item = db.get(StockItem, item_id)
    if not item:
        raise HTTPException(404, "Stock item not found")
    ing = item.ingredient
    try:
        qty = to_base(body.quantity, body.unit, ing.name, ing.base_unit)
    except UnknownConversion as e:
        raise HTTPException(422, str(e))
    if body.expiry_date:
        item.expiry_date = body.expiry_date
    return _row(stock_logic.set_stock(db, item_id, qty))


@router.delete("/stock/{item_id}", status_code=204)
def delete_stock(item_id: int, db: Session = Depends(get_db)):
    item = db.get(StockItem, item_id)
    if not item:
        raise HTTPException(404, "Stock item not found")
    stock_logic.set_stock(db, item_id, D(0))   # records a movement
    db.delete(item)
    db.commit()


@router.get("/plan/check")
def plan_check(scope: str = Query("today", pattern="^(today|week)$"),
               db: Session = Depends(get_db)):
    return stock_logic.check_scope(db, scope)


@router.post("/meals/{meal_id}/done")
def meal_done(meal_id: int, db: Session = Depends(get_db)):
    try:
        return stock_logic.mark_done(db, meal_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@router.get("/stock/movements")
def stock_movements(db: Session = Depends(get_db)):

    movements = db.execute(
        select(
            StockMovement.id,
            StockMovement.ingredient_id,
            Ingredient.name.label("ingredient_name"),
            Ingredient.base_unit.label("unit"),
            StockMovement.delta,
            StockMovement.reason,
            StockMovement.meal_id,
            StockMovement.time
        )
        .join(
            Ingredient,
            StockMovement.ingredient_id == Ingredient.id
        )
        .order_by(StockMovement.time.desc(), StockMovement.id.desc())
    ).all()

    return [
        {
            "id": movement.id,
            "ingredient_id": movement.ingredient_id,
            "ingredient_name": movement.ingredient_name,
            "delta": float(movement.delta),
            "unit": movement.unit,
            "reason": movement.reason,
            "meal_id": movement.meal_id,
            "time": movement.time
        }
        for movement in movements
    ]
