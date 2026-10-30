"""Audit router - STUB (Role 4). Returns contract-shaped fake data.
Replaced by real logic in Phase 4."""
from fastapi import APIRouter

router = APIRouter(tags=["audit"])


@router.get("/audit/pick")
def pick():
    return {"items": [{"ingredient_id": 10, "name": "toor dal", "expected": 400, "unit": "g"}], "stub": True}


@router.post("/audit/submit")
def submit():
    return {"matched": 4, "total": 5, "avg_error": 12.5, "stub": True}


@router.get("/audit/history")
def history():
    return {"audits": [], "stub": True}
