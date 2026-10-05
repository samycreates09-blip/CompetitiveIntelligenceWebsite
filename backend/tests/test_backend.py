import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "boost_competitive_intelligence")
os.environ.setdefault("POSTGRES_USER", os.environ.get("USER", "postgres"))
os.environ.setdefault("POSTGRES_PASSWORD", "")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_competitors():
    response = client.get("/api/v1/competitors")
    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload] == ["Boost Mobile", "T-Mobile", "Verizon"]


def test_get_competitor_by_id():
    response = client.get("/api/v1/competitors/2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "T-Mobile"
    assert payload["short_name"] == "T-Mobile"


def test_current_plan_prices():
    response = client.get("/api/v1/plans/current")
    assert response.status_code == 200
    payload = response.json()
    prices = {item["competitor_name"]: item["price_usd"] for item in payload}
    assert prices["Boost Mobile"] == 50.0
    assert prices["T-Mobile"] == 65.0
    assert prices["Verizon"] == 70.0


def test_t_mobile_history_values():
    response = client.get("/api/v1/plans/201/history")
    assert response.status_code == 200
    payload = response.json()
    assert [item["price_usd"] for item in payload] == [60.0, 60.0, 65.0]


def test_verizon_device_history_values():
    response = client.get("/api/v1/devices/7001/history")
    assert response.status_code == 200
    payload = response.json()
    assert [item["promo_price_usd"] for item in payload] == [899.0, 849.0]


def test_promotions_filtered_by_competitor():
    response = client.get("/api/v1/promotions?competitor_id=3")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1
    assert all(item["competitor_id"] == 3 for item in payload)


def test_changes_endpoint():
    response = client.get("/api/v1/changes")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert payload[0]["competitor_name"] in {"Boost Mobile", "T-Mobile", "Verizon"}


def test_nonexistent_resource_404():
    response = client.get("/api/v1/competitors/999")
    assert response.status_code == 404


def test_invalid_semantic_date_range_400():
    response = client.get("/api/v1/plans/201/history?from_date=2026-09-20&to_date=2026-09-01")
    assert response.status_code == 400


def test_invalid_date_type_422():
    response = client.get("/api/v1/plans/201/history?from_date=not-a-date")
    assert response.status_code == 422
