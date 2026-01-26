from __future__ import annotations

from services.agents import runtime_planner, runtime_recipe, runtime_script_writer


def _blueprint_fastapi_nextjs() -> dict:
    return {
        "id": "demo_project",
        "name": "Demo Project",
        "kind": "web_app",
        "frontend": {
            "framework": "nextjs",
            "language": "typescript",
            "targets": ["web"],
        },
        "backend": {
            "framework": "fastapi",
            "language": "python",
            "style": "rest",
        },
        "database": {
            "engine": "sqlite",
            "mode": "single_node",
        },
        "localization": {
            "default_language": "en",
            "supported_languages": ["en", "fr"],
        },
    }


def test_runtime_end_to_end_fastapi_nextjs_linux() -> None:
    bp = _blueprint_fastapi_nextjs()

    # 1) plan runtime from blueprint
    plan_res = runtime_planner.handle({"blueprint": bp, "os": "linux"})
    assert plan_res["ok"] is True
    runtime = plan_res["runtime"]

    # 2) build a recipe script for the chosen runtime
    recipe_res = runtime_recipe.handle({"runtime": runtime, "os": "linux"})
    assert recipe_res["ok"] is True
    assert recipe_res["project_id"] == "demo_project"

    script_text = recipe_res.get("script") or ""
    # minimal invariants that current implementation guarantees
    assert "#!/usr/bin/env bash" in script_text
    assert "set -euo pipefail" in script_text
    assert 'PROJECT_ID="demo_project"' in script_text
    assert "export PROJECT_ID" in script_text

    # 3) write script to files via script writer
    script_res = runtime_script_writer.handle(
        {"runtime": runtime, "os": "linux", "output_dir": "generated"}
    )
    assert script_res["ok"] is True
    assert script_res["os"] == "linux"
    assert script_res["project_id"] == "demo_project"
    assert script_res["script_path"] == "generated/run_all.sh"

    files = script_res.get("files") or []
    assert len(files) == 1
    f = files[0]
    assert f["path"] == "generated/run_all.sh"

    script = f["content"]
    # same minimal invariants for the written script
    assert "#!/usr/bin/env bash" in script
    assert "set -euo pipefail" in script
    assert 'PROJECT_ID="demo_project"' in script
    assert "export PROJECT_ID" in script
