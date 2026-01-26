from __future__ import annotations

from services.agents import content_generator
from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)
from services.app_server.schemas.blueprint_factory import blueprint_from_hospital_spec


def test_content_generator_with_blueprint_object_and_locales():
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

    locales = res.get("locales") or []
    assert locales == ["en", "fr"]

    content = res.get("content") or {}
    assert set(content.keys()) == {"en", "fr"}

    en = content["en"]
    assert "Team Dashboard" in en["title"]
    hero = next(s for s in en["sections"] if s["id"] == "hero")
    assert "Team Dashboard" in hero["heading"]
    assert isinstance(hero["primary_cta"], str) and hero["primary_cta"] != ""


def test_content_generator_with_hospital_spec_dict_blueprint():
    spec = {
        "project": {
            "id": "team_dashboard",
            "name": "Team Dashboard",
            "type": "dashboard",
        },
        "stack": {
            "frontend": {
                "framework": "react",
                "language": "typescript",
            },
            "backend": {
                "framework": "fastapi",
                "style": "rest",
            },
            "database": {
                "engine": "postgres",
                "mode": "single_node",
            },
        },
        "localization": {
            "default_language": "en",
            "supported_languages": ["en", "fr", "nl"],
        },
    }

    bp = blueprint_from_hospital_spec(spec)
    bp_dict = bp.model_dump()

    res = content_generator.handle({"blueprint": bp_dict})
    assert res["ok"] is True

    locales = res.get("locales") or []
    assert locales == ["en", "fr", "nl"]

    content = res.get("content") or {}
    assert set(content.keys()) == {"en", "fr", "nl"}


def test_content_generator_fallback_locales_when_no_blueprint():
    payload = {
        "product": {
            "name": "Inventory Manager",
            "locales": ["de", "ar"],
        }
    }
    res = content_generator.handle(payload)
    assert res["ok"] is True

    locales = res.get("locales") or []
    assert locales == ["ar", "de"] or locales == ["de", "ar"]

    content = res.get("content") or {}
    for loc, data in content.items():
        assert "Inventory Manager" in data["title"]
        assert any(s["id"] == "hero" for s in data.get("sections") or [])
