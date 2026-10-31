"""Shopping router (owner: Role 4). Real version - replaces the Phase 1 stub.

Endpoints (from the shared contract):
  POST  /shopping/generate   build/refresh this week's list from missing items
  GET   /shopping            the saved list
  PATCH /shopping/{id}       tick / untick an item   body: {"checked": true}
  GET   /shopping/handoff    text, WhatsApp link, quick-commerce search links
All accept ?week_start=YYYY-MM-DD (any date; snapped to that week's Monday).
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.logic import handoff, shopping

router = APIRouter(tags=["shopping"])


class CheckedIn(BaseModel):
    checked: bool


def _week(week_start: Optional[date]) -> date:
    return shopping.week_start_of(week_start or date.today())


def _row(i: dict) -> dict:
    return {**i,
            "quantity": float(i["quantity"]),
            "quantity_text": handoff.format_quantity(i["quantity"], i["unit"])}


@router.post("/shopping/generate")
def generate(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    ws = _week(week_start)
    try:
        items = shopping.generate_shopping_list(db, ws)
    except LookupError as e:          # e.g. a planned meal points to a missing recipe
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"week_start": ws, "items": [_row(i) for i in items]}


@router.get("/shopping/handoff")
def get_handoff(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    ws = _week(week_start)
    return handoff.build_handoff(shopping.list_shopping(db, ws), ws)


@router.get("/shopping")
def list_items(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    ws = _week(week_start)
    return {"week_start": ws, "items": [_row(i) for i in shopping.list_shopping(db, ws)]}


@router.patch("/shopping/{item_id}")
def update_item(item_id: int, body: CheckedIn, db: Session = Depends(get_db)):
    try:
        item = shopping.set_checked(db, item_id, body.checked)
    except LookupError as e:
        raise HTTPException(404, str(e))
    for row in shopping.list_shopping(db, item.for_week_start):
        if row["id"] == item.id:
            return _row(row)
    raise HTTPException(404, "Shopping item not found")
