from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app

client = TestClient(app)


def test_create_location_valid_coordinates() -> None:
    payload = {
        "name": "HQ",
        "latitude": 50.0,
        "longitude": 4.0,
    }
    response = client.post("/v1/locations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "HQ"
    assert data["latitude"] == 50.0
    assert data["longitude"] == 4.0
    assert isinstance(data["id"], int)


def test_create_location_rejects_invalid_coordinates() -> None:
    payload = {
        "name": "Nowhere",
        "latitude": 999.0,
        "longitude": 4.0,
    }
    response = client.post("/v1/locations", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "invalid_coordinates"


def test_list_locations_returns_geo_fields() -> None:
    payload = {
        "name": "Office",
        "latitude": 51.0,
        "longitude": 3.0,
    }
    create_response = client.post("/v1/locations", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()

    response = client.get("/v1/locations")
    assert response.status_code == 200
    items = response.json()
    assert any(item["id"] == created["id"] for item in items)

    for item in items:
        assert "id" in item
        assert "name" in item
        assert isinstance(item["latitude"], float)
        assert isinstance(item["longitude"], float)
