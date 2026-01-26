from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app


client = TestClient(app)


def test_assistant_intake_endpoint_basic() -> None:
    body = {
        "company": {"name": "Acme Travel"},
        "product": {
            "type": "saas",
            "goal": "internal_tool",
            "locales": ["en", "fr"],
        },
        "idea": "tableau de bord pour mon équipe",
    }

    r = client.post("/v1/assistant/intake", json=body)
    assert r.status_code == 200

    data = r.json()
    assert data["ok"] is True
    assert isinstance(data["language"], str) and data["language"] != ""

    assert isinstance(data["intake"], dict)
    assert isinstance(data["blueprint"], dict)
    assert isinstance(data["i18n"], dict)

    assert data["intake"]["product"]["locales"] == ["en", "fr"]
    assert data["blueprint"]["localization"]["supported_languages"] == ["en", "fr"]

    i18n = data["i18n"]
    assert isinstance(i18n.get("locales"), list)
    assert len(i18n["locales"]) >= 1
    assert isinstance(i18n.get("messages"), dict)


def test_assistant_intake_infers_language_and_locales_from_idea() -> None:
    body = {
        "company": {"name": "Acme Travel"},
        "product": {
            "type": "saas",
            "goal": "internal_tool",
        },
        "idea": "tableau de bord pour mon équipe en français",
    }

    r = client.post("/v1/assistant/intake", json=body)
    assert r.status_code == 200

    data = r.json()
    assert data["ok"] is True

    lang = data["language"]
    assert isinstance(lang, str) and lang != ""
    assert lang.startswith("fr")

    intake = data["intake"]
    assert isinstance(intake, dict)

    intake_lang = intake.get("user_language")
    assert isinstance(intake_lang, str) and intake_lang.startswith("fr")

    product = intake["product"]
    locales = product.get("locales") or []
    assert isinstance(locales, list)
    assert "fr" in locales

    blueprint = data["blueprint"]
    localization = blueprint["localization"]
    assert localization["default_language"].startswith("fr")
    assert "fr" in localization["supported_languages"]

    i18n = data["i18n"]
    i18n_locales = i18n.get("locales") or []
    assert "fr" in i18n_locales
    messages = i18n.get("messages") or {}
    assert "fr" in messages
