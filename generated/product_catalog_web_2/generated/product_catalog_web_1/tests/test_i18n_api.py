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
