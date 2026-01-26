from __future__ import annotations

from services.agents import runtime_planner, runtime_recipe


def _react_native_blueprint() -> dict:
    return {
        "id": "shopping_app",
        "name": "Shopping App",
        "kind": "mobile_app",
        "frontend": {"framework": "react_native"},
        "backend": {"framework": "fastapi"},
    }


def _flutter_blueprint() -> dict:
    return {
        "id": "flutter_app",
        "name": "Flutter App",
        "kind": "mobile_app",
        "frontend": {"framework": "flutter"},
        "backend": {"framework": "fastapi"},
    }


def test_runtime_planner_adds_mobile_service_for_react_native() -> None:
    bp = _react_native_blueprint()
    res = runtime_planner.handle({"blueprint": bp})
    assert res["ok"] is True

    runtime = res["runtime"]
    services = runtime.get("services") or []
    ids = {s["id"] for s in services}

    assert "api" in ids
    assert "mobile" in ids

    mobile = next(s for s in services if s["id"] == "mobile")
    cwd = str(mobile.get("cwd") or "")
    assert "mobile/react_native" in cwd.replace("\\", "/")


def test_runtime_recipe_emits_expo_command_for_react_native() -> None:
    bp = _react_native_blueprint()
    plan = runtime_planner.handle({"blueprint": bp})
    runtime = plan["runtime"]

    res = runtime_recipe.handle({"runtime": runtime, "os": "linux"})
    assert res["ok"] is True

    script = res["script"]
    assert "mobile/react_native" in script
    assert "expo start" in script


def test_runtime_recipe_emits_flutter_command_for_flutter_mobile() -> None:
    bp = _flutter_blueprint()
    plan = runtime_planner.handle({"blueprint": bp})
    runtime = plan["runtime"]

    res = runtime_recipe.handle({"runtime": runtime, "os": "linux"})
    assert res["ok"] is True

    script = res["script"]
    assert "mobile/flutter" in script
    assert "flutter run" in script
