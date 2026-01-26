from __future__ import annotations

from services.agents import runtime_command_planner


def test_runtime_command_planner_fastapi_nextjs_linux() -> None:
    runtime = {
        "project_id": "demo",
        "services": [
            {"id": "api", "kind": "fastapi_api", "language": "python"},
            {"id": "web", "kind": "nextjs_web", "language": "node"},
        ],
    }

    res = runtime_command_planner.handle({"runtime": runtime, "os": "linux"})
    assert res["ok"] is True
    assert res["os"] == "linux"

    cmds = {s["id"]: s["command"] for s in res["services"]}
    assert "api" in cmds
    assert "web" in cmds
    assert "uvicorn" in cmds["api"]
    assert "npm" in cmds["web"]
    assert "generated/web" in cmds["web"]


def test_runtime_command_planner_node_react_linux() -> None:
    runtime = {
        "project_id": "demo_node",
        "services": [
            {"id": "api", "kind": "node_api", "language": "node"},
            {"id": "web", "kind": "react_spa", "language": "node"},
        ],
    }

    res = runtime_command_planner.handle({"runtime": runtime, "os": "linux"})
    assert res["ok"] is True
    cmds = {s["id"]: s["command"] for s in res["services"]}

    assert "api" in cmds
    assert "web" in cmds

    assert "npm run dev" in cmds["api"]
    assert "generated/services/node" in cmds["api"]

    assert "npm run dev" in cmds["web"]
    assert "react_spa" in cmds["web"]
