from __future__ import annotations

from services.agents import runtime_script_writer


def test_runtime_script_writer_fastapi_nextjs_linux() -> None:
    runtime = {
        "project_id": "demo_project",
        "services": [
            {"id": "api", "kind": "fastapi_api", "language": "python"},
            {"id": "web", "kind": "nextjs_web", "language": "node"},
        ],
    }

    res = runtime_script_writer.handle(
        {"runtime": runtime, "os": "linux", "output_dir": "generated"}
    )

    assert res["ok"] is True
    assert res["os"] == "linux"
    assert res["project_id"] == "demo_project"
    assert res["script_path"] == "generated/run_all.sh"

    files = res.get("files") or []
    assert len(files) == 1
    f = files[0]
    assert f["path"] == "generated/run_all.sh"

    script = f["content"]
    assert "#!/usr/bin/env bash" in script
    assert 'PROJECT_ID="demo_project"' in script
    assert "uvicorn generated.services.api.app:app" in script
    assert "cd generated/web" in script
    assert "npm run dev" in script


def test_runtime_script_writer_node_react_windows() -> None:
    runtime = {
        "project_id": "node_demo",
        "services": [
            {"id": "api", "kind": "node_api", "language": "node"},
            {"id": "web", "kind": "react_spa", "language": "node"},
        ],
    }

    res = runtime_script_writer.handle(
        {"runtime": runtime, "os": "windows", "output_dir": "generated"}
    )

    assert res["ok"] is True
    assert res["os"] == "windows"
    assert res["project_id"] == "node_demo"
    assert res["script_path"] == "generated/run_all.bat"

    files = res.get("files") or []
    assert len(files) == 1
    f = files[0]
    assert f["path"] == "generated/run_all.bat"

    script = f["content"]
    assert "@echo off" in script
    assert "set PROJECT_ID=node_demo" in script
    assert "generated/services/node" in script or "generated\\services\\node" in script
    assert "npm run dev" in script
    assert "react_spa" in script
