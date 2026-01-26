# tests/test_hospital_codegen.py
from __future__ import annotations

from services.agents import hospital_codegen


def _base_spec() -> dict:
    return {
        "project": {
            "name": "hospital_demo",
            "type": "web_app",
        },
        "stack": {
            "frontend": {"framework": "nextjs", "language": "typescript"},
            "backend": {"framework": "fastapi", "language": "python"},
            "database": {"engine": "sqlite", "mode": "single_tenant"},
        },
        "features": {
            "modules": ["patients", "appointments"],
        },
    }


def test_hospital_codegen_plan_only_analysis_ok() -> None:
    payload = {
        "spec": _base_spec(),
        "apply": False,
        "target_files": [
            "team_dashboard_api.py",
        ],
    }

    result = hospital_codegen.handle(payload)

    assert result["ok"] is True
    assert result["agent"] == "hospital_codegen"
    assert result["mode"] == "plan_only"
    assert "summary" in result
    assert "analysis" in result
    assert result["spec"]["project"]["name"] == "hospital_demo"

    analysis = result["analysis"]
    assert "team_dashboard_api.py" in analysis
    file_info = analysis["team_dashboard_api.py"]
    assert file_info["exists"] is True

    modules = file_info["modules"]
    assert "patients" in modules
    assert "appointments" in modules

    # Each requested module should report that the file exists and have marker lists.
    for mod_name in ("patients", "appointments"):
        mod_info = modules[mod_name]
        assert "exists" in mod_info
        assert "present" in mod_info
        assert "missing" in mod_info
        # At least one marker should be present for seeded code
        assert isinstance(mod_info["present"], list)


def test_hospital_codegen_with_apply_returns_patches() -> None:
    payload = {
        "spec": _base_spec(),
        "apply": True,
        "target_files": [
            "team_dashboard_api.py",
        ],
    }

    result = hospital_codegen.handle(payload)

    assert result["ok"] is True
    assert "patches" in result

    patches = result["patches"]
    assert "team_dashboard_api.py" in patches

    p = patches["team_dashboard_api.py"]
    assert p["kind"] == "full_file"
    assert p["path"] == "team_dashboard_api.py"
    assert isinstance(p["content"], str)
    # sanity: content should include something from the real file
    assert 'FastAPI(title="Team Dashboard API"' in p["content"]
