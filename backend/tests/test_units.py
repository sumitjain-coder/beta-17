import pytest
from decimal import Decimal as D
from app.logic.units import convert, UnknownConversion


def test_kg_to_g():
    assert convert(1.5, "kg", "g") == D(1500)


def test_katori_to_ml():
    assert convert(2, "katori", "ml") == D(300)


def test_cup_rice_to_grams_uses_density():
    assert convert(1, "cup", "g", "rice") == D("192.00")


def test_unknown_unit_raises():
    with pytest.raises(UnknownConversion):
        convert(1, "handful", "g", "rice")


def test_unknown_density_raises_not_guesses():
    with pytest.raises(UnknownConversion):
        convert(1, "cup", "g", "mystery spice")
