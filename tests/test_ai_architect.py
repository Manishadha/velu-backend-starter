# tests/test_ai_architect.py
from __future__ import annotations

from services.agents import ai_architect
from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintFrontend,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintLocalization,
)


def _simple_blueprint_web_fastapi() -> Blueprint:
    frontend = BlueprintFrontend(
        framework="nextjs",
        language="typescript",
        targets=["web"],
    )
    backend = BlueprintBackend(
        framework="fastapi",
        language="python",
        style="rest",
    )
    database = BlueprintDatabase(
        engine="sqlite",
        mode="single_node",
    )
    localization = BlueprintLocalization(
        default_language="en",
        supported_languages=["en", "fr"],
    )
    return Blueprint(
        id="demo_app",
        name="Demo App",
        kind="web_app",
        frontend=frontend,
        backend=backend,
        database=database,
        localization=localization,
    )


def _simple_blueprint_mobile_react_native() -> Blueprint:
    frontend = BlueprintFrontend(
        framework="react_native",
        language="typescript",
        targets=["android", "ios"],
    )
    backend = BlueprintBackend(
        framework="fastapi",
        language="python",
        style="rest",
    )
    database = BlueprintDatabase(
        engine="postgres",
        mode="single_node",
    )
    localization = BlueprintLocalization(
        default_language="en",
        supported_languages=["en"],
    )
    return Blueprint(
        id="mobile_app",
        name="Mobile App",
        kind="mobile_app",
        frontend=frontend,
        backend=backend,
        database=database,
        localization=localization,
    )


def test_ai_architect_basic_web_fastapi():
    bp = _simple_blueprint_web_fastapi()
    res = ai_architect.handle({"blueprint": bp})
    assert res["ok"] is True
    assert res["agent"] == "ai_architect"
    assert res["kind"] == "web_app"

    services = res["services"]
    names = {s["name"] for s in services}
    assert "web" in names
    assert "api" in names

    web_service = [s for s in services if s["name"] == "web"][0]
    api_service = [s for s in services if s["name"] == "api"][0]

    assert web_service["kind"] == "frontend"
    assert web_service["framework"] == "nextjs"
    assert "web" in web_service["targets"]

    assert api_service["kind"] == "backend"
    assert api_service["framework"] == "fastapi"
    assert api_service["style"] == "rest"

    db = res["database"]
    assert db["engine"] == "sqlite"
    assert db["mode"] == "single_node"


def test_ai_architect_mobile_react_native():
    bp = _simple_blueprint_mobile_react_native()
    res = ai_architect.handle({"blueprint": bp})
    assert res["ok"] is True
    assert res["kind"] == "mobile_app"

    services = res["services"]
    web_service = [s for s in services if s["kind"] == "frontend"][0]
    assert web_service["framework"] == "react_native"
    assert "android" in web_service["targets"]
    assert "ios" in web_service["targets"]

    db = res["database"]
    assert db["engine"] == "postgres"
