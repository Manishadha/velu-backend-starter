from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app


client = TestClient(app)


def test_i18n_locales_endpoint() -> None:
    resp = client.get("/v1/i18n/locales")
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, dict)
    assert "locales" in data

    locales = data["locales"]
    assert isinstance(locales, list)
    assert "en" in locales
    assert "fr" in locales
    assert "ar" in locales


def test_i18n_messages_endpoint_from_product() -> None:
    body = {
        "product": {
            "name": "Inventory Manager",
            "locales": ["de", "ar"],
        }
    }

    resp = client.post("/v1/i18n/messages", json=body)
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, dict)
    assert "locales" in data
    assert "messages" in data

    locales = data["locales"]
    assert sorted(locales) == sorted(["de", "ar"])

    messages = data["messages"]
    assert set(messages.keys()) == set(["de", "ar"])

    for loc, payload in messages.items():
        hero = payload.get("hero") or {}
        title = hero.get("title", "")
        assert "Inventory Manager" in title
        assert isinstance(hero.get("primary_cta", ""), str)
        assert hero["primary_cta"] != ""
