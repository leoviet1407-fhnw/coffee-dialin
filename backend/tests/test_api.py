"""HTTP tests: success and error cases through the whole stack, on a temporary data file."""
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from coffee_api.api import create_app

PHIN = {"method": "phin", "dose_g": 18, "water_ml": 140, "water_temp_c": 94, "drip_time_s": 190,
        "grind_setting": "7", "taste": "sour"}
ESPRESSO = {"method": "espresso", "dose_g": 18, "yield_g": 36, "shot_time_s": 27, "taste": "balanced"}
SAIGON = {"product_id": "saigon-drip", "roast_date": "2026-10-10", "bag_size_g": 250}

@pytest.fixture
def data_file(tmp_path):
    return tmp_path / "data.json"

@pytest.fixture
def client(data_file):
    return TestClient(create_app(data_file))

def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json().keys() == {"code", "message"}
    assert response.json()["code"] == code

def test_products_come_from_seed(client):
    products = client.get("/api/products").json()
    assert [p["id"] for p in products] == ["hanoi-haze", "da-lat-dawn", "saigon-drip"]

def test_coffee_lifecycle(client):
    created = client.post("/api/coffees", json={"product_id": "hanoi-haze", "roast_date": "2026-10-15"})
    assert created.status_code == 201
    coffee = created.json()
    assert created.headers["Location"] == f"/api/coffees/{coffee['id']}"
    assert (coffee["name"], coffee["grams_left"], coffee["bag_size_g"]) == ("Hanoi Haze", 250, 250)
    assert client.get(created.headers["Location"]).json() == coffee

    update = {"product_id": "hanoi-haze", "roast_date": "2026-10-20", "bag_size_g": 250, "grams_left": 120}
    replaced = client.put(f"/api/coffees/{coffee['id']}", json=update)
    assert replaced.status_code == 200 and replaced.json()["grams_left"] == 120
    assert [c["id"] for c in client.get("/api/coffees").json()] == [1, coffee["id"]]

    assert client.delete(f"/api/coffees/{coffee['id']}").status_code == 204
    assert_error(client.get(f"/api/coffees/{coffee['id']}"), 404, "not_found")

def test_coffee_without_product_needs_name_and_bag_size(client):
    assert_error(client.post("/api/coffees", json={"roast_date": "2026-10-15"}), 422, "invalid_input")
    assert_error(client.post("/api/coffees", json={"product_id": "nope", "roast_date": "2026-10-15"}),
                 422, "invalid_input")
    other = client.post("/api/coffees", json={"name": "Local roaster", "bag_size_g": 500, "roast_date": "2026-10-15"})
    assert other.status_code == 201 and other.json()["reorder_url"] is None

def test_future_roast_date_is_refused_and_nothing_changes(client, data_file):
    before = data_file.read_bytes()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = client.post("/api/coffees", json={"product_id": "saigon-drip", "roast_date": tomorrow})
    assert_error(response, 422, "invalid_input")
    assert response.json()["message"] == "roast_date cannot be in the future."
    assert data_file.read_bytes() == before

def test_demo_workflow_log_phin_brew(client, data_file):
    response = client.post("/api/coffees/1/brews", json=PHIN)
    assert response.status_code == 201
    brew = response.json()
    assert response.headers["Location"] == f"/api/brews/{brew['id']}"
    assert brew["ratio"] == 7.8
    assert brew["advice"]["action"] == "grind_finer"
    assert brew["advice"]["message"] == "Sour and fast (3:10). Grind finer or press the screen a little firmer."
    assert brew["grams_left"] == 232 - 18
    assert client.get("/api/coffees/1").json()["grams_left"] == 214

    # Persistence: a new app on the same file still sees the brew.
    restarted = TestClient(create_app(data_file))
    assert restarted.get("/api/coffees/1/brews").json()[0]["id"] == brew["id"]

@pytest.mark.parametrize("body", [
    {**PHIN, "water_temp_c": 110},
    {key: value for key, value in PHIN.items() if key != "taste"},
    {**PHIN, "method": "moka"},
    {**PHIN, "grams_left": 5},
])
def test_demo_workflow_invalid_brew_changes_nothing(client, data_file, body):
    before = data_file.read_bytes()
    assert_error(client.post("/api/coffees/1/brews", json=body), 422, "invalid_input")
    assert data_file.read_bytes() == before

def test_not_enough_coffee_is_a_conflict(client, data_file):
    client.put("/api/coffees/1", json={**SAIGON, "grams_left": 6})
    before = data_file.read_bytes()
    response = client.post("/api/coffees/1/brews", json=PHIN)
    assert_error(response, 409, "conflict")
    assert response.json()["message"] == "Only 6 g left. Add a new bag first."
    assert data_file.read_bytes() == before

def test_brew_for_unknown_coffee(client, data_file):
    before = data_file.read_bytes()
    response = client.post("/api/coffees/999/brews", json=PHIN)
    assert_error(response, 404, "not_found")
    assert response.json()["message"] == "Coffee 999 was not found."
    assert data_file.read_bytes() == before

def test_espresso_brew(client):
    brew = client.post("/api/coffees/1/brews", json=ESPRESSO).json()
    assert brew["ratio"] == 2.0
    assert brew["advice"]["action"] == "save_recipe"
    assert [b["method"] for b in client.get("/api/coffees/1/brews?method=espresso").json()] == ["espresso"]
    assert_error(client.get("/api/coffees/1/brews?method=moka"), 422, "invalid_input")

def test_low_stock(client):
    client.put("/api/coffees/1", json={**SAIGON, "grams_left": 40})
    client.post("/api/coffees/1/brews", json=PHIN)
    coffee = client.get("/api/coffees/1").json()
    assert (coffee["grams_left"], coffee["low_stock"], coffee["brews_left"]) == (22, True, 1)
    assert coffee["reorder_url"] == "https://phinkafi.ch"

def test_delete_brew_returns_dose(client):
    brew = client.post("/api/coffees/1/brews", json=PHIN).json()
    assert client.delete(f"/api/brews/{brew['id']}").status_code == 204
    assert client.get("/api/coffees/1").json()["grams_left"] == 232
    assert_error(client.delete(f"/api/brews/{brew['id']}"), 404, "not_found")

def test_delete_coffee_removes_its_brews(client):
    assert client.delete("/api/coffees/1").status_code == 204
    assert_error(client.delete("/api/brews/1"), 404, "not_found")

def test_recipes(client):
    balanced = client.post("/api/coffees/1/brews", json=ESPRESSO).json()
    saved = client.put("/api/coffees/1/recipes/espresso", json={"brew_id": balanced["id"]})
    assert saved.status_code == 200 and saved.json()["brew"]["id"] == balanced["id"]
    assert_error(client.put("/api/coffees/1/recipes/phin", json={"brew_id": 1}), 422, "invalid_input")
    assert_error(client.put("/api/coffees/1/recipes/phin", json={"brew_id": balanced["id"]}), 422, "invalid_input")
    assert_error(client.put("/api/coffees/1/recipes/phin", json={"brew_id": 999}), 404, "not_found")
    assert [r["method"] for r in client.get("/api/coffees/1/recipes").json()] == ["espresso"]

    # Deleting the brew removes the recipe built on it.
    client.delete(f"/api/brews/{balanced['id']}")
    assert client.get("/api/coffees/1/recipes").json() == []

def test_malformed_requests_use_error_shape(client):
    response = client.post("/api/coffees/1/brews", content="{not json", headers={"Content-Type": "application/json"})
    assert_error(response, 422, "invalid_input")
    assert_error(client.get("/api/coffees/abc"), 422, "invalid_input")
    assert_error(client.get("/api/nothing-here"), 404, "not_found")
