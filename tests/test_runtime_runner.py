from __future__ import annotations

from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)
from services.console import runtime_runner


def make_blueprint(frontend_fw: str, backend_fw: str) -> Blueprint:
    return Blueprint(
        id="runtime_demo",
        name="Runtime Demo",
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


def test_runtime_runner_plan_from_payload_fastapi_nextjs() -> None:
    bp = make_blueprint("nextjs", "fastapi")

    runtime = runtime_runner.plan_from_payload({"blueprint": bp, "project_id": "runtime_demo_app"})

    assert runtime["project_id"] == "runtime_demo_app"
    service_ids = runtime_runner.list_service_ids(runtime)
    assert "api" in service_ids
    assert "web" in service_ids

    api = runtime_runner.find_service(runtime, "api")
    assert api is not None
    assert api["kind"] == "api"
    cmd = " ".join(api["command"])
    assert "generated.services.api.app" in cmd

    web = runtime_runner.find_service(runtime, "web")
    assert web is not None
    assert web["kind"] == "web"
    assert web["cwd"] == "generated/web"


def test_runtime_runner_plan_from_payload_node_react() -> None:
    bp = make_blueprint("react", "express")

    runtime = runtime_runner.plan_from_payload({"blueprint": bp, "project_id": "runtime_node_demo"})

    assert runtime["project_id"] == "runtime_node_demo"
    service_ids = runtime_runner.list_service_ids(runtime)
    assert "api" in service_ids
    assert "web" in service_ids

    api = runtime_runner.find_service(runtime, "api")
    assert api is not None
    cmd = " ".join(api["command"])
    assert api["command"][0] == "node"
    assert "generated/services/node/app.js" in cmd

    web = runtime_runner.find_service(runtime, "web")
    assert web is not None
    assert web["cwd"] == "generated/react_spa"
