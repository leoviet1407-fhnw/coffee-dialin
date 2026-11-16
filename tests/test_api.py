"""End-to-end checks through HTTP. Each test gets a fresh SQLite file in a temp folder."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from dialin_api.main import create_app

TODAY = date(2026, 11, 11)
PHIN = {"method": "phin", "dose_g": 18, "water_ml": 130, "water_temp_c": 93, "drip_time_s": 290,
        "grind_setting": "6", "taste": "balanced"}
ESPRESSO = {"method": "espresso", "dose_g": 18, "yield_g": 36, "shot_time_s": 28, "grind_setting": "2.4",
            "taste": "balanced"}


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}", demo_data=False, today=lambda: TODAY)
    return TestClient(app)


def add_coffee(client, **extra) -> dict:
    body = {"product_id": "saigon-drip", "roast_date": "2026-11-01", **extra}
    res = client.post("/api/coffees", json=body)
    assert res.status_code == 201, res.text
    return res.json()


# ---- products and coffees -----------------------------------------------------------


def test_products_are_seeded(client):
    ids = {p["id"] for p in client.get("/api/products").json()}
    assert ids == {"hanoi-haze", "da-lat-dawn", "saigon-drip"}


def test_create_coffee_from_phin_product(client):
    res = client.post("/api/coffees", json={"product_id": "saigon-drip", "roast_date": "2026-11-01"})
    assert res.status_code == 201
    coffee = res.json()
    assert coffee["name"] == "Saigon Drip"
    assert coffee["grams_left"] == 250  # defaults to the bag size
    assert coffee["days_off_roast"] == 10
    assert coffee["shop_url"] == "https://phinkafi.ch"
    assert res.headers["Location"] == f"/api/coffees/{coffee['id']}"


def test_create_other_coffee_needs_all_fields(client):
    res = client.post("/api/coffees", json={"name": "Kenya AA", "roast_date": "2026-11-01"})
    assert res.status_code == 422
    assert "origin" in res.json()["detail"]
    ok = client.post("/api/coffees", json={"name": "Kenya AA", "origin": "Kenya", "roast_level": "light",
                                           "bag_size_g": 500, "roast_date": "2026-11-01"})
    assert ok.status_code == 201
    assert ok.json()["shop_url"] is None


def test_roast_date_in_the_future_is_refused(client):
    res = client.post("/api/coffees", json={"product_id": "saigon-drip", "roast_date": "2026-12-01"})
    assert res.status_code == 422
    assert "future" in res.json()["detail"]


def test_unknown_product_is_refused(client):
    assert client.post("/api/coffees", json={"product_id": "nope", "roast_date": "2026-11-01"}).status_code == 422


def test_new_bag_via_put(client):
    coffee = add_coffee(client, grams_left=10)
    body = {k: coffee[k] for k in ("name", "origin", "roast_level", "bag_size_g")}
    res = client.put(f"/api/coffees/{coffee['id']}", json={**body, "roast_date": "2026-11-10", "grams_left": 260})
    assert res.status_code == 200
    assert res.json()["grams_left"] == 260


def test_missing_coffee_is_404(client):
    res = client.get("/api/coffees/999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Coffee 999 was not found."}


# ---- brews, stock and advice ------------------------------------------------------------


def test_brew_subtracts_dose_and_gives_advice(client):
    coffee = add_coffee(client)
    res = client.post(f"/api/coffees/{coffee['id']}/brews",
                      json={**PHIN, "water_ml": 140, "water_temp_c": 94, "drip_time_s": 190, "taste": "sour"})
    assert res.status_code == 201
    brew = res.json()
    assert brew["grams_left"] == 232
    assert brew["ratio"] == 7.78
    assert brew["advice"]["action"] == "grind_finer"
    assert brew["advice"]["time_status"] == "fast"
    assert res.headers["Location"] == f"/api/brews/{brew['id']}"


def test_ranges_depend_on_the_method(client):
    coffee = add_coffee(client)
    url = f"/api/coffees/{coffee['id']}/brews"
    assert client.post(url, json={**PHIN, "water_temp_c": 110}).status_code == 422
    assert client.post(url, json={**PHIN, "dose_g": 5}).status_code == 422  # too little for a Phin
    assert client.post(url, json={**ESPRESSO, "dose_g": 5}).status_code == 201  # fine for espresso
    assert client.post(url, json={**ESPRESSO, "water_ml": 140}).status_code == 201  # extra fields ignored
    res = client.post(url, json={k: v for k, v in PHIN.items() if k != "taste"})
    assert res.status_code == 422
    assert any(err["loc"][-1] == "taste" for err in res.json()["detail"])


def test_not_enough_coffee_is_409_and_changes_nothing(client):
    coffee = add_coffee(client, grams_left=6)
    res = client.post(f"/api/coffees/{coffee['id']}/brews", json=PHIN)
    assert res.status_code == 409
    assert res.json() == {"detail": "Only 6 g left. Add a new bag first."}
    assert client.get(f"/api/coffees/{coffee['id']}").json()["grams_left"] == 6
    assert client.get(f"/api/coffees/{coffee['id']}/brews").json() == []


def test_low_stock_flag(client):
    coffee = add_coffee(client, grams_left=60)
    client.post(f"/api/coffees/{coffee['id']}/brews", json=PHIN)  # 42 g left < 3 × 18 g
    after = client.get(f"/api/coffees/{coffee['id']}").json()
    assert after["low_stock"] is True
    assert after["brews_left"] == 2


def test_delete_brew_returns_the_dose(client):
    coffee = add_coffee(client)
    brew = client.post(f"/api/coffees/{coffee['id']}/brews", json=PHIN).json()
    assert client.delete(f"/api/brews/{brew['id']}").status_code == 204
    assert client.get(f"/api/coffees/{coffee['id']}").json()["grams_left"] == 250
    assert client.get(f"/api/brews/{brew['id']}").status_code == 404


def test_filter_brews_by_method(client):
    coffee = add_coffee(client)
    url = f"/api/coffees/{coffee['id']}/brews"
    client.post(url, json=PHIN)
    client.post(url, json=ESPRESSO)
    assert [b["method"] for b in client.get(url, params={"method": "espresso"}).json()] == ["espresso"]
    assert len(client.get(url).json()) == 2


# ---- recipes -------------------------------------------------------------------------------


def test_save_recipe_and_replace_it(client):
    coffee = add_coffee(client)
    url = f"/api/coffees/{coffee['id']}"
    first = client.post(f"{url}/brews", json=PHIN).json()
    second = client.post(f"{url}/brews", json={**PHIN, "drip_time_s": 300}).json()

    res = client.put(f"{url}/recipes/phin", json={"brew_id": first["id"]})
    assert res.status_code == 200
    client.put(f"{url}/recipes/phin", json={"brew_id": second["id"]})
    recipes = client.get(f"{url}/recipes").json()
    assert [(r["method"], r["brew"]["id"]) for r in recipes] == [("phin", second["id"])]


def test_recipe_rules(client):
    coffee = add_coffee(client)
    other = add_coffee(client)
    url = f"/api/coffees/{coffee['id']}"
    sour = client.post(f"{url}/brews", json={**PHIN, "taste": "sour"}).json()
    shot = client.post(f"{url}/brews", json=ESPRESSO).json()
    elsewhere = client.post(f"/api/coffees/{other['id']}/brews", json=PHIN).json()

    assert client.put(f"{url}/recipes/phin", json={"brew_id": sour["id"]}).status_code == 422  # not balanced
    assert client.put(f"{url}/recipes/phin", json={"brew_id": shot["id"]}).status_code == 422  # wrong method
    assert client.put(f"{url}/recipes/phin", json={"brew_id": elsewhere["id"]}).status_code == 422  # other coffee
    assert client.put(f"{url}/recipes/phin", json={"brew_id": 999}).status_code == 404
    assert client.put(f"{url}/recipes/moka", json={"brew_id": shot["id"]}).status_code == 422  # unknown method


def test_deleting_the_recipe_brew_removes_the_recipe(client):
    coffee = add_coffee(client)
    brew = client.post(f"/api/coffees/{coffee['id']}/brews", json=PHIN).json()
    client.put(f"/api/coffees/{coffee['id']}/recipes/phin", json={"brew_id": brew["id"]})
    client.delete(f"/api/brews/{brew['id']}")
    assert client.get(f"/api/coffees/{coffee['id']}/recipes").json() == []


def test_delete_coffee_cascades(client):
    coffee = add_coffee(client)
    brew = client.post(f"/api/coffees/{coffee['id']}/brews", json=PHIN).json()
    assert client.delete(f"/api/coffees/{coffee['id']}").status_code == 204
    assert client.get(f"/api/coffees/{coffee['id']}").status_code == 404
    assert client.get(f"/api/brews/{brew['id']}").status_code == 404


# ---- persistence and demo data ---------------------------------------------------------------


def test_data_survives_a_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'restart.db'}"
    first = TestClient(create_app(url, demo_data=False, today=lambda: TODAY))
    coffee = first.post("/api/coffees", json={"product_id": "hanoi-haze", "roast_date": "2026-11-01"}).json()
    second = TestClient(create_app(url, demo_data=False, today=lambda: TODAY))
    assert second.get(f"/api/coffees/{coffee['id']}").json()["name"] == "Hanoi Haze"


def test_demo_data_only_fills_an_empty_database(tmp_path):
    url = f"sqlite:///{tmp_path / 'demo.db'}"
    client = TestClient(create_app(url, demo_data=True, today=lambda: TODAY))
    assert len(client.get("/api/coffees").json()) == 2
    client = TestClient(create_app(url, demo_data=True, today=lambda: TODAY))
    assert len(client.get("/api/coffees").json()) == 2


def test_frontend_is_served(client):
    assert client.get("/").status_code == 200
