from __future__ import annotations

import json

from services.agents import chatbot_embed
from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)
from services.app_server.schemas.blueprint_factory import blueprint_from_hospital_spec


def _paths(res) -> set[str]:
    files = res.get("files") or []
    return {f["path"] for f in files if "path" in f}


def _get_file(res, path: str) -> str:
    for f in res.get("files") or []:
        if f.get("path") == path:
            return str(f.get("content") or "")
    raise KeyError(path)


def test_chatbot_embed_basic_paths():
    res = chatbot_embed.handle({})
    assert res["ok"] is True

    p = _paths(res)
    assert "web/components/VeluChatWidget.tsx" in p
    assert "web/chatbot.config.json" in p

    cfg_raw = _get_file(res, "web/chatbot.config.json")
    cfg = json.loads(cfg_raw)
    assert cfg["api_path"] == "/v1/ai/chat"
    assert cfg["default_language"] == "en"
    assert cfg["bot_name"] == "Product"


def test_chatbot_embed_with_blueprint_object_locales():
    bp = Blueprint(
        id="team_dashboard",
        name="Team Dashboard",
        kind="dashboard",
        frontend=BlueprintFrontend(framework="nextjs", language="typescript", targets=["web"]),
        backend=BlueprintBackend(framework="fastapi", language="python", style="rest"),
        database=BlueprintDatabase(engine="postgres", mode="single_node"),
        localization=BlueprintLocalization(
            default_language="en",
            supported_languages=["en", "fr", "nl"],
        ),
    )

    res = chatbot_embed.handle({"blueprint": bp})
    assert res["ok"] is True

    p = _paths(res)
    assert "web/components/VeluChatWidget.tsx" in p
    assert "web/chatbot.config.json" in p

    cfg_raw = _get_file(res, "web/chatbot.config.json")
    cfg = json.loads(cfg_raw)
    assert cfg["locales"] == ["en", "fr", "nl"]
    assert cfg["bot_name"] == "Team Dashboard"
    assert cfg["kind"] == "dashboard"


def test_chatbot_embed_with_hospital_spec_dict_blueprint():
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
            "supported_languages": ["en", "fr"],
        },
    }

    bp = blueprint_from_hospital_spec(spec)
    bp_dict = bp.model_dump()

    res = chatbot_embed.handle({"blueprint": bp_dict})
    assert res["ok"] is True

    cfg_raw = _get_file(res, "web/chatbot.config.json")
    cfg = json.loads(cfg_raw)
    assert cfg["locales"] == ["en", "fr"]
    assert cfg["bot_name"] == "Team Dashboard"
