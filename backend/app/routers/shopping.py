"""Shopping router - STUB (Role 4). Returns contract-shaped fake data.
Replaced by real logic in Phase 3."""
from fastapi import APIRouter

router = APIRouter(tags=["shopping"])

_SAMPLE = [
    {"id": 1, "ingredient_id": 10, "name": "toor dal", "quantity": 50, "unit": "g", "checked": False, "for_week_start": "2026-11-02"},
    {"id": 2, "ingredient_id": 11, "name": "onion", "quantity": 3, "unit": "count", "checked": False, "for_week_start": "2026-11-02"},
]


@router.post("/shopping/generate")
def generate():
    return {"items": _SAMPLE, "stub": True}


@router.get("/shopping/handoff")
def handoff():
    return {"text": "toor dal - 50 g\nonion - 3", "whatsapp_link": "https://wa.me/?text=toor%20dal%2050%20g", "stub": True}


@router.get("/shopping")
def list_items():
    return {"items": _SAMPLE, "stub": True}


@router.patch("/shopping/{item_id}")
def update_item(item_id: int, checked: bool = True):
    return {"id": item_id, "checked": checked, "stub": True}
