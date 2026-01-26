# services/agents/testgen.py
from __future__ import annotations

from typing import Any, Dict, List  # noqa: F401


def _has_plugin(payload: Dict[str, Any], name: str) -> bool:
    plugins = payload.get("plugins") or []
    if isinstance(plugins, (list, tuple, set)):
        return name.lower() in {str(p).strip().lower() for p in plugins}
    return False


def _is_blueprint_app(payload: Dict[str, Any]) -> bool:
    return bool(payload.get("blueprint_id")) or str(payload.get("kind") or "").lower() in {
        "web_app",
        "dashboard",
        "api_only",
    }


def _module(payload: Dict[str, Any]) -> str:
    return str(payload.get("module") or "hello_mod").strip() or "hello_mod"


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    module = _module(payload)
    idea = str(payload.get("idea") or "demo")

    # If this looks like a generated web/api blueprint, generate API smoke tests
    if (
        _is_blueprint_app(payload)
        or _has_plugin(payload, "ecommerce")
        or _has_plugin(payload, "auth")
    ):
        test_code = """from __future__ import annotations

def test_app_imports() -> None:
    # Blueprint-style FastAPI app
    from services.api.app import app
    assert app is not None


def test_routes_present() -> None:
    from services.api.app import app
    paths = {getattr(r, "path", None) for r in app.router.routes}
    assert "/health" in paths

    # Optional features: don't fail if absent
    # (these are common for shop blueprints)
    # If present, they should be mounted correctly.
    for p in ["/products", "/auth/login", "/i18n/locales"]:
        # some are router prefixes; may not appear exactly
        # so we just ensure app has *some* route starting with the prefix
        if p.startswith("/auth") or p.startswith("/i18n"):
            prefix = p.split("/", 2)[1]
            assert any(str(x or "").startswith(f"/{prefix}") for x in paths)
        elif p == "/products":
            assert any(str(x or "").startswith("/products") for x in paths)
"""
        files = [{"path": "tests/test_generated_app_smoke.py", "content": test_code}]
        return {"ok": True, "agent": "testgen", "idea": idea, "module": module, "files": files}

    # Otherwise keep legacy greet-style tests for CLI/module demos
    test_code = f"""from __future__ import annotations

from {module} import greet


def test_greet_pipeline_extra() -> None:
    out = greet("Velu")
    assert isinstance(out, str)
    assert "Velu" in out
""".lstrip()

    files = [{"path": f"tests/test_{module}_pipeline_extra.py", "content": test_code}]

    return {"ok": True, "agent": "testgen", "idea": idea, "module": module, "files": files}
