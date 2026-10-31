from datetime import date
from math import isfinite

COVERAGE_WEIGHT = 70
EXPIRY_BONUS = 20
RECENTLY_COOKED_PENALTY = 15
EXPIRY_THRESHOLD_DAYS = 3


def suggest_recipes(
    recipes: list,
    stock: list,
    recently_cooked: list = None,
    today: date = None
) -> list:

    today = today or date.today()
    recently_cooked = recently_cooked or []

    recently_cooked = {
        name.strip().lower()
        for name in recently_cooked
    }

    stock_lookup = {}

    # Build a combined stock lookup.
    for item in stock:
        name = item["name"].strip().lower()
        quantity = float(item["quantity"])

        if not isfinite(quantity) or quantity < 0:
            raise ValueError(f"Invalid stock quantity for {name}")

        expiry = item.get("expiry_date")

        if expiry and isinstance(expiry, str):
            expiry = date.fromisoformat(expiry)

        # Ignore expired stock.
        if expiry and expiry < today:
            continue

        if name not in stock_lookup:
            stock_lookup[name] = {
                "quantity": 0.0,
                "expiring_quantity": 0.0
            }

        stock_lookup[name]["quantity"] += quantity

        if expiry:
            days_left = (expiry - today).days

            if 0 <= days_left <= EXPIRY_THRESHOLD_DAYS:
                stock_lookup[name]["expiring_quantity"] += quantity

    suggestions = []

    for recipe in recipes:
        ingredients = recipe.get("ingredients", [])

        if not ingredients:
            continue

        total_ingredients = len(ingredients)
        available_count = 0

        available_ingredients = []
        missing_ingredients = []
        expiring_ingredients = []

        expiry_utilization = 0.0

        for ingredient in ingredients:
            name = ingredient["name"].strip().lower()
            required_quantity = float(ingredient["quantity"])

            if not isfinite(required_quantity) or required_quantity <= 0:
                raise ValueError(
                    f"Invalid recipe quantity for {name}"
                )

            stock_item = stock_lookup.get(name, {
                "quantity": 0.0,
                "expiring_quantity": 0.0
            })

            available_quantity = stock_item["quantity"]
            expiring_quantity = stock_item["expiring_quantity"]

            if available_quantity >= required_quantity:
                available_count += 1
                available_ingredients.append(name)
            else:
                missing_ingredients.append({
                    "name": name,
                    "required": required_quantity,
                    "available": available_quantity,
                    "missing": required_quantity - available_quantity,
                    "unit": ingredient["unit"]
                })

            # Reward only the expiring quantity this recipe can use.
            usable_expiring = min(
                expiring_quantity,
                required_quantity
            )

            expiry_utilization += (
                usable_expiring / required_quantity
            )

            if usable_expiring > 0:
                expiring_ingredients.append(name)

        # Main score: percentage of ingredients fully available.
        coverage = available_count / total_ingredients
        score = coverage * COVERAGE_WEIGHT

        # Expiry bonus: proportional to usable expiring quantities.
        expiry_ratio = expiry_utilization / total_ingredients
        score += expiry_ratio * EXPIRY_BONUS

        was_recently_cooked = (
            recipe["name"].strip().lower() in recently_cooked
        )

        if was_recently_cooked:
            score -= RECENTLY_COOKED_PENALTY

        reasons = [
            f"You have enough stock for {available_count} "
            f"out of {total_ingredients} ingredients."
        ]

        if missing_ingredients:
            reasons.append("Some ingredients are insufficient.")

        if expiring_ingredients:
            reasons.append(
                "Uses ingredients nearing expiry: "
                + ", ".join(expiring_ingredients)
            )

        if was_recently_cooked:
            reasons.append("Recently cooked meal.")

        suggestions.append({
            "recipe_name": recipe["name"],
            "score": round(max(0, score), 2),
            "available_ingredients": available_ingredients,
            "missing_ingredients": missing_ingredients,
            "expiring_ingredients": expiring_ingredients,
            "reasons": reasons
        })

    suggestions.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return suggestions