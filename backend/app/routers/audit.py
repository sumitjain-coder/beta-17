"""Audit router (owner: Role 4). Real version - replaces the Phase 1 stub.

  GET  /audit/pick      up to 5 items to check this week, each with a reason
  POST /audit/submit    body {"items":[{"ingredient_id":1,"quantity":380,"unit":"g"}]}
  GET  /audit/history   past audits + per-ingredient drift ranking
Percentages are returned as plain numbers (12.5 means 12.5%).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.logic import audit

router = APIRouter(tags=["audit"])


class AuditEntry(BaseModel):
    ingredient_id: int
    quantity: float = Field(ge=0)
    unit: str = Field(min_length=1)


class AuditIn(BaseModel):
    items: list[AuditEntry] = Field(min_length=1)


def _pct(ratio) -> Optional[float]:
    return None if ratio is None else round(float(ratio) * 100, 1)


def _item(i: dict) -> dict:
    return {"ingredient_id": i["ingredient_id"], "name": i["name"], "unit": i["unit"],
            "expected": float(i["expected"]), "actual": float(i["actual"]),
            "gap_before": float(i["gap"]), "gap_after": 0.0,
            "pct_error": _pct(i["pct_error"]), "matched": i["matched"],
            "stock_after": float(i["actual"])}


def _summary(ev: dict) -> dict:
    return {"total": ev["total"], "matched": ev["matched"],
            "accuracy_pct": _pct(ev["accuracy"]),
            "avg_error_pct_before": _pct(ev["avg_error_before"]),
            "avg_error_pct_after": _pct(ev["avg_error_after"]),
            "items": [_item(i) for i in ev["items"]]}


@router.get("/audit/pick")
def pick(db: Session = Depends(get_db)):
    items = audit.pick_items(db)
    message = None
    if not items:
        message = "No stock to audit yet. Add some items first."
    elif len(items) < audit.PICK_COUNT:
        message = f"Only {len(items)} item(s) in stock, so this audit is shorter than {audit.PICK_COUNT}."
    return {"items": [{"ingredient_id": i["ingredient_id"], "name": i["name"],
                       "unit": i["unit"], "expected": float(i["expected"]),
                       "reason": i["reason"]} for i in items],
            "tolerance_note": audit.TOLERANCE_NOTE, "message": message}


@router.post("/audit/submit", status_code=201)
def submit(body: AuditIn, db: Session = Depends(get_db)):
    entries = [e.model_dump() for e in body.items]
    try:
        ev = audit.submit_audit(db, entries)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:            # also covers UnknownConversion (e.g. 'a handful')
        raise HTTPException(422, str(e))
    return {"audit_id": ev["audit_id"], "audit_date": ev["audit_date"],
            "tolerance_note": audit.TOLERANCE_NOTE, **_summary(ev)}


@router.get("/audit/history")
def get_history(db: Session = Depends(get_db)):
    h = audit.history(db)
    return {"audits": [{"audit_id": a["audit_id"], "audit_date": a["audit_date"],
                        **_summary(a)} for a in h["audits"]],
            "drift_ranking": [{"ingredient_id": d["ingredient_id"], "name": d["name"],
                               "unit": d["unit"], "audits": d["audits"],
                               "avg_error_pct": _pct(d["avg_error"]),
                               "avg_gap": float(d["avg_gap"]),
                               "direction": d["direction"]} for d in h["drift_ranking"]]}
