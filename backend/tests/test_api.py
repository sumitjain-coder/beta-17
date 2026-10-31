def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "KitchenSync Backend Running"
    }


def test_get_stock(client):
    response = client.get("/stock")

    assert response.status_code == 200


def test_get_recipes(client):
    response = client.get("/recipes")

    assert response.status_code == 200


def test_get_meals(client):
    response = client.get("/meals")

    assert response.status_code == 200

def test_add_stock(client):
    response = client.post(
        "/stock",
        json={
            "ingredient": "toor dal",
            "quantity": 1.5,
            "unit": "kg"
        }
    )

def test_create_recipe(client):
    response = client.post(
        "/recipes",
        json={
            "name": "Dal",
            "meal_type": "lunch",
            "base_servings": 2,
            "ingredients": [
                {
                    "ingredient": "toor dal",
                    "quantity": 150,
                    "unit": "g"
                },
                {
                    "ingredient": "onion",
                    "quantity": 100,
                    "unit": "g"
                }
            ]
        }
    )


def test_create_meal(client):
    recipe_response = client.post(
        "/recipes",
        json={
            "name": "Dal",
            "meal_type": "lunch",
            "base_servings": 2,
            "ingredients": [
                {
                    "ingredient": "toor dal",
                    "quantity": 150,
                    "unit": "g"
                }
            ]
        }
    )

    assert recipe_response.status_code == 201
    recipe_id = recipe_response.json()["id"]

    response = client.post(
        "/meals",
        json={
            "date": "2026-11-05",
            "meal_type": "lunch",
            "recipe_id": recipe_id,
            "servings": 4
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["date"] == "2026-11-05"
    assert data["meal_type"] == "lunch"
    assert data["recipe_id"] == recipe_id
    assert data["servings"] == 4
    assert data["status"] == "planned"
    assert data["message"] == "Meal scheduled successfully"
    assert "id" in data

def test_duplicate_meal_not_allowed(client):
    # Create a recipe
    recipe_response = client.post(
        "/recipes",
        json={
            "name": "Dal",
            "meal_type": "lunch",
            "base_servings": 2,
            "ingredients": [
                {
                    "ingredient": "toor dal",
                    "quantity": 150,
                    "unit": "g"
                }
            ]
        }
    )

    recipe_id = recipe_response.json()["id"]

    meal_data = {
        "date": "2026-11-06",
        "meal_type": "lunch",
        "recipe_id": recipe_id,
        "servings": 2
    }

    # First meal should be created
    first_response = client.post("/meals", json=meal_data)
    assert first_response.status_code == 201

    # Second meal on the same date and meal type should fail
    second_response = client.post("/meals", json=meal_data)
    assert second_response.status_code == 409

    assert second_response.json()["detail"] == (
        "A meal is already planned for this date and meal type"
    )


def test_meal_with_invalid_recipe_id(client):
    response = client.post(
        "/meals",
        json={
            "date": "2026-11-07",
            "meal_type": "lunch",
            "recipe_id": 999999,
            "servings": 2
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recipe not found"


def test_add_stock_zero_quantity_rejected(client):
    response = client.post(
        "/stock",
        json={
            "ingredient": "toor dal",
            "quantity": 0,
            "unit": "g"
        }
    )

    assert response.status_code == 422


def test_add_stock_unknown_ingredient(client):
    response = client.post(
        "/stock",
        json={
            "ingredient": "unknown ingredient",
            "quantity": 100,
            "unit": "g"
        }
    )

    assert response.status_code == 404
    assert "Unknown ingredient" in response.json()["detail"]


def test_complete_meal_deducts_stock_once(client):
    # 1. Add 500 g of toor dal
    stock_response = client.post(
        "/stock",
        json={
            "ingredient": "toor dal",
            "quantity": 500,
            "unit": "g"
        }
    )
    assert stock_response.status_code == 201

    # 2. Schedule a meal using the existing test recipe (ID 1)
    meal_response = client.post(
        "/meals",
        json={
            "date": "2026-11-08",
            "meal_type": "lunch",
            "recipe_id": 1,
            "servings": 2
        }
    )
    assert meal_response.status_code == 201

    meal_id = meal_response.json()["id"]

    # 3. Complete the meal
    done_response = client.post(f"/meals/{meal_id}/done")

    assert done_response.status_code == 200
    assert done_response.json()["already_done"] is False

    # 4. Check that 180 g was deducted (90 g per serving)
    stock_after = client.get("/stock")
    dal = next(
        item for item in stock_after.json()
        if item["name"] == "toor dal"
    )
    assert float(dal["quantity"]) == 320

    # 5. Complete the same meal again
    second_response = client.post(f"/meals/{meal_id}/done")

    assert second_response.status_code == 200
    assert second_response.json()["already_done"] is True

    # 6. Verify stock was not deducted again
    stock_final = client.get("/stock")
    dal_final = next(
        item for item in stock_final.json()
        if item["name"] == "toor dal"
    )
    assert float(dal_final["quantity"]) == 320
