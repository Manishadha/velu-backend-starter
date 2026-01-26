from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app


client = TestClient(app)


def test_translate_explicit_source_locale() -> None:
    body = {
        "text": "Hello world",
        "source_locale": "en",
        "target_locale": "fr",
    }
    resp = client.post("/v1/i18n/translate", json=body)
    assert resp.status_code == 200

    data = resp.json()
    assert data["text"] == "Hello world"
    assert data["source_locale"] == "en"
    assert data["target_locale"] == "fr"
    assert isinstance(data["translated_text"], str)
    assert data["translated_text"] != ""
    assert data["backend"] == "stub"


def test_translate_detects_source_when_missing(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_detect_language(text: str) -> str:
        calls["text"] = text
        return "fr"

    monkeypatch.setattr(
        "services.agents.language_detector.detect_language",
        fake_detect_language,
    )

    body = {
        "text": "Bonjour le monde",
        "target_locale": "en",
    }
    resp = client.post("/v1/i18n/translate", json=body)
    assert resp.status_code == 200

    data = resp.json()
    assert data["text"] == "Bonjour le monde"
    assert data["source_locale"] == "fr"
    assert data["target_locale"] == "en"
    assert isinstance(data["translated_text"], str)
    assert data["translated_text"] != ""
    assert data["backend"] == "stub"
    assert calls["text"] == "Bonjour le monde"
