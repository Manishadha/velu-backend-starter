from __future__ import annotations

from services.agents import assistant_intake


def test_assistant_intake_basic_multilingual_flow() -> None:
    payload = {
        "company": {"name": "Acme Travel"},
        "product": {
            "type": "saas",
            "goal": "internal_tool",
            "locales": ["en", "fr"],
        },
        "idea": "tableau de bord pour mon équipe",
    }

    res = assistant_intake.handle(payload)

    assert res["ok"] is True

    language = res.get("language")
    assert isinstance(language, str)
    assert language != ""

    intake = res.get("intake") or {}
    product = intake.get("product") or {}
    assert product.get("locales") == ["en", "fr"]

    blueprint = res.get("blueprint") or {}
    localization = blueprint.get("localization") or {}
    assert localization.get("supported_languages") == ["en", "fr"]

    i18n = res.get("i18n") or {}
    locales = i18n.get("locales") or []
    assert isinstance(locales, list)
    assert len(locales) >= 1

    messages = i18n.get("messages") or {}
    assert isinstance(messages, dict)
    assert len(messages) >= 1

    summary = i18n.get("summary") or {}
    assert summary.get("name") == "Acme Travel"
    assert "kind" in summary
