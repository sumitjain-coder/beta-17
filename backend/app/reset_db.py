from app.db import Base, engine, SessionLocal
from app import models  # noqa: F401  (registers tables)
from app.models import Household, Ingredient

# (name, base_unit, aliases)
SEED_INGREDIENTS = [
    ("toor dal", "g", ["arhar dal", "tur dal"]),
    ("moong dal", "g", ["mung dal"]),
    ("rice", "g", ["chawal"]),
    ("atta", "g", ["wheat flour", "gehun atta"]),
    ("poha", "g", ["flattened rice"]),
    ("sugar", "g", ["cheeni"]),
    ("salt", "g", ["namak"]),
    ("onion", "g", ["pyaaz"]),
    ("tomato", "g", ["tamatar"]),
    ("potato", "g", ["aloo"]),
    ("oil", "ml", ["tel", "cooking oil"]),
    ("milk", "ml", ["doodh"]),
    ("ghee", "g", []),
    ("egg", "count", ["anda", "eggs"]),
    ("turmeric", "g", ["haldi"]),
]


def reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(Household(name="Demo Household", size=4))
        for name, unit, aliases in SEED_INGREDIENTS:
            db.add(Ingredient(name=name, base_unit=unit, aliases=aliases))
        db.commit()
    print("Database reset and seeded.")


if __name__ == "__main__":
    reset()
