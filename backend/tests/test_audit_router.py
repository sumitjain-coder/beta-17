"""API tests for routers/audit.py. Own tiny FastAPI app + in-memory SQLite."""
from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.models import Audit, Ingredient, StockItem, StockMovement
from app.routers import audit as audit_router

NOW = datetime.now()
# name, base unit, qty, days since last change
SEED = [("toor dal", "g", 400, 20), ("onion", "count", 5, 10), ("sugar", "g", 500, 5),
        ("oil", "ml", 1000, 3), ("salt", "g", 800, 2), ("rice", "g", 2000, 1)]


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as s:
        for i, (name, unit, qty, days) in enumerate(SEED, start=1):
            s.add(Ingredient(id=i, name=name, base_unit=unit))
            s.add(StockItem(ingredient_id=i, quantity=D(qty),
                            updated_at=NOW - timedelta(days=days)))
        s.commit()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(audit_router.router)
    app.dependency_overrides[get_db] = override
    return TestClient(app), Session


ID = {name: i for i, (name, *_rest) in enumerate(SEED, start=1)}


def _stock(Session, name):
    with Session() as s:
        return s.scalar(select(StockItem).where(StockItem.ingredient_id == ID[name])).quantity


def test_pick_returns_five_stalest_with_reasons(env):
    client, _ = env
    body = client.get("/audit/pick").json()
    names = [i["name"] for i in body["items"]]
    assert len(names) == 5 and "rice" not in names and names[0] == "toor dal"
    assert "not changed for 20 days" in body["items"][0]["reason"]
    assert body["message"] is None and body["tolerance_note"]


def test_pick_with_empty_stock(env):
    client, Session = env
    with Session() as s:
        s.query(StockItem).delete()
        s.commit()
    body = client.get("/audit/pick").json()
    assert body["items"] == [] and "No stock" in body["message"]


def test_pick_with_fewer_than_five(env):
    client, Session = env
    with Session() as s:
        s.query(StockItem).filter(StockItem.ingredient_id > 2).delete()
        s.commit()
    body = client.get("/audit/pick").json()
    assert len(body["items"]) == 2 and "Only 2" in body["message"]


def test_submit_counts_matches_corrects_stock_and_logs_movements(env):
    client, Session = env
    r = client.post("/audit/submit", json={"items": [
        {"ingredient_id": ID["toor dal"], "quantity": 380, "unit": "g"},      # within 10%
        {"ingredient_id": ID["onion"], "quantity": 3, "unit": "count"},       # off by 2
        {"ingredient_id": ID["sugar"], "quantity": 100, "unit": "g"},         # way off
    ]})
    assert r.status_code == 201
    body = r.json()
    assert body["total"] == 3 and body["matched"] == 1
    assert body["accuracy_pct"] == 33.3
    assert body["avg_error_pct_before"] == round((0.05 + 0.4 + 0.8) / 3 * 100, 1)
    assert body["avg_error_pct_after"] == 0.0
    sugar = next(i for i in body["items"] if i["name"] == "sugar")
    assert sugar["gap_before"] == -400.0 and sugar["gap_after"] == 0.0
    assert _stock(Session, "toor dal") == D(380) and _stock(Session, "sugar") == D(100)
    with Session() as s:
        moves = s.scalars(select(StockMovement).where(StockMovement.reason == "audit")).all()
        assert len(moves) == 3
        assert sum(m.delta for m in moves) == D(-20) + D(-2) + D(-400)


def test_submit_accepts_household_units(env):
    client, Session = env
    r = client.post("/audit/submit", json={"items": [
        {"ingredient_id": ID["rice"], "quantity": 2, "unit": "katori"}]})
    assert r.status_code == 201
    assert _stock(Session, "rice") == D(240)          # 2 x 150 ml x 0.80 g/ml


def test_unknown_unit_rejects_whole_audit_and_changes_nothing(env):
    client, Session = env
    r = client.post("/audit/submit", json={"items": [
        {"ingredient_id": ID["sugar"], "quantity": 100, "unit": "g"},
        {"ingredient_id": ID["salt"], "quantity": 1, "unit": "handful"}]})
    assert r.status_code == 422
    assert _stock(Session, "sugar") == D(500)
    with Session() as s:
        assert s.query(Audit).count() == 0


def test_duplicate_ingredient_is_422(env):
    client, _ = env
    e = {"ingredient_id": ID["sugar"], "quantity": 1, "unit": "g"}
    assert client.post("/audit/submit", json={"items": [e, e]}).status_code == 422


def test_unknown_ingredient_is_404(env):
    client, _ = env
    r = client.post("/audit/submit", json={"items": [{"ingredient_id": 999, "quantity": 1, "unit": "g"}]})
    assert r.status_code == 404


def test_bad_bodies_are_422(env):
    client, _ = env
    assert client.post("/audit/submit", json={"items": []}).status_code == 422
    assert client.post("/audit/submit", json={"items": [
        {"ingredient_id": 1, "quantity": -5, "unit": "g"}]}).status_code == 422


def test_item_without_stock_row_is_created_by_audit(env):
    client, Session = env
    with Session() as s:
        s.add(Ingredient(id=50, name="jeera", base_unit="g"))
        s.commit()
    r = client.post("/audit/submit", json={"items": [{"ingredient_id": 50, "quantity": 100, "unit": "g"}]})
    assert r.status_code == 201 and r.json()["items"][0]["pct_error"] == 100.0
    with Session() as s:
        assert s.scalar(select(StockItem).where(StockItem.ingredient_id == 50)).quantity == D(100)


def test_history_and_drift_ranking(env):
    client, _ = env
    client.post("/audit/submit", json={"items": [
        {"ingredient_id": ID["sugar"], "quantity": 100, "unit": "g"},
        {"ingredient_id": ID["rice"], "quantity": 2000, "unit": "g"}]})
    h = client.get("/audit/history").json()
    assert len(h["audits"]) == 1 and h["audits"][0]["matched"] == 1
    assert h["drift_ranking"][0]["name"] == "sugar"
    assert h["drift_ranking"][0]["direction"] == "list too high"


def test_history_empty(env):
    client, _ = env
    assert client.get("/audit/history").json() == {"audits": [], "drift_ranking": []}


def test_audited_drifty_item_is_picked_again(env):
    client, _ = env
    client.post("/audit/submit", json={"items": [{"ingredient_id": ID["sugar"], "quantity": 100, "unit": "g"}]})
    items = client.get("/audit/pick").json()["items"]
    sugar = next(i for i in items if i["name"] == "sugar")
    assert "past audits" in sugar["reason"]
