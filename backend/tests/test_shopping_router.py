"""API tests for routers/shopping.py. Own tiny FastAPI app + in-memory SQLite,
so teammates' routers and MySQL are not involved."""
from datetime import date
from decimal import Decimal as D

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.logic import scaling
from app.models import Ingredient, MealPlan, Recipe
from app.routers import shopping as shopping_router


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as s:
        s.add_all([
            Ingredient(id=1, name="toor dal", base_unit="g"),
            Ingredient(id=2, name="onion", base_unit="count"),
            Recipe(id=1, name="dal", meal_type="lunch", base_servings=4),
            MealPlan(date=date.today(), meal_type="lunch", recipe_id=1, servings=4),
        ])
        s.commit()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(shopping_router.router)
    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(scaling, "get_scaled_ingredients",
                        lambda rid, servings: [(1, D(450)), (2, D(3))])
    return TestClient(app)


def test_list_is_empty_before_generate(client):
    assert client.get("/shopping").json()["items"] == []


def test_generate_then_list(client):
    body = client.post("/shopping/generate").json()
    names = {i["name"]: i for i in body["items"]}
    assert names["toor dal"]["quantity"] == 450.0
    assert names["onion"]["quantity_text"] == "3"
    assert len(client.get("/shopping").json()["items"]) == 2


def test_generate_twice_does_not_duplicate(client):
    client.post("/shopping/generate")
    client.post("/shopping/generate")
    assert len(client.get("/shopping").json()["items"]) == 2


def test_patch_checked_and_handoff_skips_it(client):
    items = client.post("/shopping/generate").json()["items"]
    onion = next(i for i in items if i["name"] == "onion")
    r = client.patch(f"/shopping/{onion['id']}", json={"checked": True})
    assert r.status_code == 200 and r.json()["checked"] is True
    hand = client.get("/shopping/handoff").json()
    assert [i["name"] for i in hand["items"]] == ["toor dal"]


def test_patch_unknown_item_is_404(client):
    assert client.patch("/shopping/999", json={"checked": True}).status_code == 404


def test_patch_bad_body_is_422(client):
    assert client.patch("/shopping/1", json={"checked": "maybe"}).status_code == 422


def test_handoff_shape(client):
    client.post("/shopping/generate")
    hand = client.get("/shopping/handoff").json()
    assert hand["count"] == 2
    assert hand["whatsapp_link"].startswith("https://wa.me/?text=")
    assert set(hand["items"][0]["links"]) == {"blinkit", "zepto", "instamart", "bigbasket"}
    assert "no public ordering api" in hand["note"].lower()


def test_handoff_empty(client):
    hand = client.get("/shopping/handoff").json()
    assert hand["count"] == 0 and hand["whatsapp_link"] is None


def test_bad_week_start_is_422(client):
    assert client.get("/shopping?week_start=not-a-date").status_code == 422
