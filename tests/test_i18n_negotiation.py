from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app


client = TestClient(app)


def _get_locale(resp_json: dict) -> str:
    assert isinstance(resp_json, dict)
    assert "locale" in resp_json
    return str(resp_json["locale"])


def test_i18n_messages_explicit_locale_param_wins() -> None:
    resp = client.get("/v1/i18n/messages", params={"locale": "fr"})
    assert resp.status_code == 200

    data = resp.json()
    locale = _get_locale(data)
    assert locale == "fr"


def test_i18n_messages_uses_accept_language_when_no_param() -> None:
    headers = {"Accept-Language": "fr, en;q=0.8"}
    resp = client.get("/v1/i18n/messages", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    locale = _get_locale(data)
    # With Phase 3, we expect negotiation to pick "fr"
    assert locale == "fr"


def test_i18n_messages_header_with_unsupported_primary_falls_back_to_supported() -> None:
    # es-MX not in our default list, but fr is, so we should pick fr
    headers = {"Accept-Language": "es-MX, fr;q=0.7"}
    resp = client.get("/v1/i18n/messages", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    locale = _get_locale(data)
    assert locale == "fr"


def test_i18n_messages_unsupported_header_falls_back_to_en() -> None:
    headers = {"Accept-Language": "zz, yy;q=0.5"}
    resp = client.get("/v1/i18n/messages", headers=headers)
    assert resp.status_code == 200

    data = resp.json()
    locale = _get_locale(data)

    assert locale == "en"


def test_i18n_messages_no_header_no_param_defaults_to_en() -> None:
    resp = client.get("/v1/i18n/messages")
    assert resp.status_code == 200

    data = resp.json()
    locale = _get_locale(data)

    assert locale == "en"
