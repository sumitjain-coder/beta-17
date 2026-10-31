
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
from app.db import Base, get_db
from app import models
from app.models import Ingredient, Recipe
from main import app



@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    s = Session()

    s.add_all([
        Ingredient(
            id=1,
            name="toor dal",
            base_unit="g",
            aliases=["arhar dal"]
        ),
        Ingredient(
            id=2,
            name="onion",
            base_unit="g",
            aliases=[]
        ),
        Recipe(
            id=1,
            name="dal",
            meal_type="lunch",
            base_servings=1
        ),
        Recipe(
            id=2,
            name="sabzi",
            meal_type="dinner",
            base_servings=1
        ),
    ])

    s.commit()

    yield s

    s.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()



@pytest.fixture(autouse=True)
def fake_scaling(monkeypatch):
    """Recipe 1: 90 g dal per serving.
    Recipe 2: 200 g onion per serving.
    """
    from app.logic import scaling

    def fake(recipe_id, servings):
        return (
            [(1, 90 * servings)]
            if recipe_id == 1
            else [(2, 200 * servings)]
        )

    monkeypatch.setattr(
        scaling,
        "get_scaled_ingredients",
        fake,
        raising=False
    )


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
