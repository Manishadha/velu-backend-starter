from __future__ import annotations

from services.agents import runtime_planner
from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)


def make_blueprint(frontend_fw: str, backend_fw: str) -> Blueprint:
    return Blueprint(
        id="demo",
        name="Demo",
        kind="web_app",
        frontend=BlueprintFrontend(
            framework=frontend_fw,
            language="typescript",
            targets=["web"],
        ),
        backend=BlueprintBackend(
            framework=backend_fw,
            language="python",
            style="rest",
        ),
        database=BlueprintDatabase(
            engine="sqlite",
            mode="single_node",
        ),
        localization=BlueprintLocalization(
            default_language="en",
            supported_languages=["en"],
        ),
    )


def test_runtime_planner_fastapi_nextjs() -> None:
    bp = make_blueprint("nextjs", "fastapi")
    res = runtime_planner.handle({"blueprint": bp, "project_id": "demo_app"})
    assert res["ok"] is True

    runtime = res["runtime"]
    assert runtime["project_id"] == "demo_app"

    services = runtime["services"]
    kinds = {s["kind"] for s in services}
    assert "api" in kinds
    assert "web" in kinds

    api = next(s for s in services if s["kind"] == "api")
    web = next(s for s in services if s["kind"] == "web")

    assert api["command"][0] == "python"
    assert "generated.services.api.app" in " ".join(api["command"])
    assert web["cwd"] == "generated/web"
    assert web["command"][0] == "npm"


def test_runtime_planner_node_react() -> None:
    bp = make_blueprint("react", "express")
    res = runtime_planner.handle({"blueprint": bp, "project_id": "demo_node"})
    assert res["ok"] is True

    runtime = res["runtime"]
    assert runtime["project_id"] == "demo_node"

    services = runtime["services"]
    kinds = {s["kind"] for s in services}
    assert "api" in kinds
    assert "web" in kinds

    api = next(s for s in services if s["kind"] == "api")
    web = next(s for s in services if s["kind"] == "web")

    cmd = " ".join(api["command"])
    assert api["command"][0] == "node"
    assert "generated/services/node/app.js" in cmd

    assert web["cwd"] == "generated/react_spa"
    assert web["command"][0] == "npm"
