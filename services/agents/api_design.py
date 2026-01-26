from __future__ import annotations

from typing import Any, Dict, List


def _default_openapi() -> Dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Velu API", "version": "v1"},
        "paths": {
            "/v1/health": {"get": {"responses": {"200": {"description": "ok"}}}},
            "/v1/auth/login": {"post": {"responses": {"200": {"description": "logged in"}}}},
        },
        "components": {},
    }


def _to_list(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    if val is None:
        return []
    return [val]


def _architecture_from_blueprint(bp: Dict[str, Any]) -> Dict[str, Any]:
    pid = str(bp.get("id") or "project")
    name = str(bp.get("name") or "Untitled Project")
    kind = str(bp.get("kind") or "web_app")

    frontend = bp.get("frontend") or {}
    backend = bp.get("backend") or {}
    database = bp.get("database") or {}
    localization = bp.get("localization") or {}

    summary = "\n".join(
        [
            f"Architecture for {name} ({kind})",
            "",
            "Frontend:",
            f"  - Framework: {frontend.get('framework')}",
            f"  - Language: {frontend.get('language')}",
            f"  - Targets: {_to_list(frontend.get('targets'))}",
            "",
            "Backend:",
            f"  - Framework: {backend.get('framework')}",
            f"  - Language: {backend.get('language')}",
            f"  - Style: {backend.get('style')}",
            "",
            "Database:",
            f"  - Engine: {database.get('engine')}",
            f"  - Mode: {database.get('mode')}",
            "",
            "Localization:",
            f"  - Default: {localization.get('default_language')}",
            f"  - Supported: {_to_list(localization.get('supported_languages'))}",
            "",
            "High-Level Components:",
            "  - API layer",
            "  - Business logic layer",
            "  - Data layer",
            "  - Auth module",
            "  - Localization middleware",
            "",
            "Suggested Deployment:",
            "  - Docker compose (web + api + db)",
            "  - Alternative: serverless (Vercel + managed DB)",
        ]
    )

    return {
        "id": pid,
        "name": name,
        "kind": kind,
        "frontend": frontend,
        "backend": backend,
        "database": database,
        "localization": localization,
        "summary": summary,
    }


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    bp = payload.get("blueprint")
    if isinstance(bp, dict):
        arch = _architecture_from_blueprint(bp)
        return {
            "ok": True,
            "agent": "api_design",
            "architecture": arch,
            "blueprint": bp,
        }

    openapi = _default_openapi()
    return {"ok": True, "agent": "api_design", "openapi": openapi}
