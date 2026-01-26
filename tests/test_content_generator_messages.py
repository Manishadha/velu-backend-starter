# tests/test_content_generator_messages.py
from __future__ import annotations

from services.agents import content_generator
from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)


def test_content_generator_messages_from_blueprint_object() -> None:
    bp = Blueprint(
        id="team_dashboard",
        name="Team Dashboard",
        kind="dashboard",
        frontend=BlueprintFrontend(framework="nextjs", language="typescript", targets=["web"]),
        backend=BlueprintBackend(framework="fastapi", language="python", style="rest"),
        database=BlueprintDatabase(engine="postgres", mode="single_node"),
        localization=BlueprintLocalization(
            default_language="en",
            supported_languages=["en", "fr"],
        ),
    )

    res = content_generator.handle({"blueprint": bp})
    assert res["ok"] is True

    messages = res.get("messages") or {}
    assert set(messages.keys()) == {"en", "fr"}

    en_msg = messages["en"]
    assert en_msg["locale"] == "en"

    hero = en_msg["hero"]
    assert "Team Dashboard" in hero["title"]
    assert isinstance(hero["primary_cta"], str)
    assert hero["primary_cta"] != ""


def test_content_generator_messages_follows_product_locales() -> None:
    payload = {
        "product": {
            "name": "Inventory Manager",
            "locales": ["de", "ar"],
        }
    }

    res = content_generator.handle(payload)
    assert res["ok"] is True

    messages = res.get("messages") or {}
    assert isinstance(messages, dict)
    locales = sorted(messages.keys())

    expected = sorted(res.get("locales") or [])
    assert locales == expected
    assert set(locales) == {"de", "ar"}

    for loc, data in messages.items():
        hero = data.get("hero") or {}
        assert "Inventory Manager" in hero.get("title", "")
        assert isinstance(hero.get("primary_cta", ""), str)
