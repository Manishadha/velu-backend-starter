from __future__ import annotations

from services.agents import runtime_recipe


def test_runtime_recipe_fastapi_nextjs_linux() -> None:
    runtime = {
        "project_id": "demo_project",
        "services": [
            {"id": "api", "kind": "fastapi_api", "language": "python"},
            {"id": "web", "kind": "nextjs_web", "language": "node"},
        ],
    }

    res = runtime_recipe.handle({"runtime": runtime, "os": "linux"})

    assert res["ok"] is True
    assert res["os"] == "linux"
    assert res["project_id"] == "demo_project"

    services = res["services"]
    ids = {s["id"] for s in services}
    assert ids == {"api", "web"}

    script = res["script"]
    assert "#!/usr/bin/env bash" in script
    assert "uvicorn generated.services.api.app:app" in script
    assert "cd generated/web" in script
    assert "npm run dev" in script
    assert 'PROJECT_ID="demo_project"' in script


def test_runtime_recipe_node_react_windows() -> None:
    runtime = {
        "project_id": "node_demo",
        "services": [
            {"id": "api", "kind": "node_api", "language": "node"},
            {"id": "web", "kind": "react_spa", "language": "node"},
        ],
    }

    res = runtime_recipe.handle({"runtime": runtime, "os": "windows"})

    assert res["ok"] is True
    assert res["os"] == "windows"
    assert res["project_id"] == "node_demo"

    services = res["services"]
    ids = {s["id"] for s in services}
    assert ids == {"api", "web"}

    script = res["script"]
    assert "@echo off" in script
    assert "set PROJECT_ID=node_demo" in script
    assert "generated/services/node" in script
    assert "npm run dev" in script
    assert "react_spa" in script
