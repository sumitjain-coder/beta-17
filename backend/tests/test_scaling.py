
import json
import pytest

from app.logic.scaling import scale_recipe


@pytest.fixture
def dal_recipe():
    return {
        "name": "Dal Tadka",
        "base_servings": 2,
        "ingredients": [
            {"name": "toor dal", "quantity": 120, "unit": "g"},
            {"name": "onion", "quantity": 60, "unit": "g"},
            {"name": "oil", "quantity": 15, "unit": "ml"}
        ]
    }


def test_scale_recipe_to_double_servings(dal_recipe):

    result = scale_recipe(dal_recipe, 4)

    assert result[0]["quantity"] == 240
    assert result[1]["quantity"] == 120
    assert result[2]["quantity"] == 30


def test_scale_recipe_with_decimal_quantities(dal_recipe):

    result = scale_recipe(dal_recipe, 5)

    assert result[0]["quantity"] == 300
    assert result[1]["quantity"] == 150
    assert result[2]["quantity"] == 37.5


def test_zero_servings_rejected(dal_recipe):

    with pytest.raises(ValueError):
        scale_recipe(dal_recipe, 0)


def test_negative_servings_rejected(dal_recipe):

    with pytest.raises(ValueError):
        scale_recipe(dal_recipe, -2)


def test_invalid_base_servings_rejected(dal_recipe):

    dal_recipe["base_servings"] = 0

    with pytest.raises(ValueError):
        scale_recipe(dal_recipe, 4)
