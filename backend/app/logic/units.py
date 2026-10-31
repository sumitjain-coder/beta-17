"""Unit conversion. Base units: g, ml, count. Raises UnknownConversion
instead of guessing."""
from decimal import Decimal as D
from typing import Optional


class UnknownConversion(ValueError):
    pass


UNIT_ALIASES = {
    "g": "g", "gm": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg", "mg": "mg",
    "ml": "ml", "millilitre": "ml", "milliliter": "ml",
    "l": "l", "litre": "l", "liter": "l", "litres": "l", "liters": "l",
    "tsp": "tsp", "teaspoon": "tsp", "tbsp": "tbsp", "tablespoon": "tbsp",
    "cup": "cup", "cups": "cup", "katori": "katori", "katoris": "katori",
    "pinch": "pinch",
    "count": "count", "piece": "count", "pieces": "count", "pc": "count",
    "nos": "count", "no": "count",
}

# unit -> (dimension, factor to canonical: g / ml / count)
TO_CANON = {
    "g": ("g", D(1)), "kg": ("g", D(1000)), "mg": ("g", D("0.001")),
    "ml": ("ml", D(1)), "l": ("ml", D(1000)),
    "tsp": ("ml", D(5)), "tbsp": ("ml", D(15)),
    "cup": ("ml", D(240)), "katori": ("ml", D(150)), "pinch": ("ml", D("0.3")),
    "count": ("count", D(1)),
}

# grams per ml (needed for volume <-> weight). Tune these.
DENSITY_G_PER_ML = {
    "rice": D("0.80"), "toor dal": D("0.85"), "moong dal": D("0.85"),
    "atta": D("0.55"), "poha": D("0.35"), "sugar": D("0.85"),
    "salt": D("1.20"), "oil": D("0.92"), "milk": D("1.03"),
    "ghee": D("0.91"), "turmeric": D("0.60"), "water": D(1),
}

# grams per piece (needed for count <-> weight)
PIECE_WEIGHT_G = {
    "onion": D(100), "tomato": D(80), "potato": D(150), "egg": D(50),
}


def normalize_unit(unit: str) -> str:
    key = unit.strip().lower()
    if key not in UNIT_ALIASES:
        raise UnknownConversion(f"Unknown unit '{unit}'. Please ask the user.")
    return UNIT_ALIASES[key]


def _to_grams(qty: D, dim: str, name: Optional[str]) -> D:
    if dim == "g":
        return qty
    if dim == "ml":
        if name not in DENSITY_G_PER_ML:
            raise UnknownConversion(f"No ml-to-gram density known for '{name}'.")
        return qty * DENSITY_G_PER_ML[name]
    if name not in PIECE_WEIGHT_G:
        raise UnknownConversion(f"No per-piece weight known for '{name}'.")
    return qty * PIECE_WEIGHT_G[name]


def _from_grams(grams: D, dim: str, name: Optional[str]) -> D:
    if dim == "g":
        return grams
    if dim == "ml":
        if name not in DENSITY_G_PER_ML:
            raise UnknownConversion(f"No gram-to-ml density known for '{name}'.")
        return grams / DENSITY_G_PER_ML[name]
    if name not in PIECE_WEIGHT_G:
        raise UnknownConversion(f"No per-piece weight known for '{name}'.")
    return grams / PIECE_WEIGHT_G[name]


def convert(quantity, from_unit: str, to_unit: str,
            ingredient: Optional[str] = None) -> D:
    """Convert quantity between units. `ingredient` is the canonical name."""
    q = D(str(quantity))
    name = ingredient.strip().lower() if ingredient else None
    f, t = normalize_unit(from_unit), normalize_unit(to_unit)
    if f == t:
        return q
    fdim, ffac = TO_CANON[f]
    tdim, tfac = TO_CANON[t]
    canon = q * ffac
    if fdim != tdim:
        canon = _from_grams(_to_grams(canon, fdim, name), tdim, name)
    return canon / tfac


def to_base(quantity, unit: str, ingredient_name: str, base_unit: str) -> D:
    return convert(quantity, unit, base_unit, ingredient_name)


def friendly(quantity, base_unit: str) -> str:
    """Display helper: 1500 g -> '1.5 kg'."""
    q = D(str(quantity))
    if base_unit == "g" and q >= 1000:
        return f"{(q / 1000).normalize():f} kg"
    if base_unit == "ml" and q >= 1000:
        return f"{(q / 1000).normalize():f} L"
    return f"{q.normalize():f} {base_unit}"
