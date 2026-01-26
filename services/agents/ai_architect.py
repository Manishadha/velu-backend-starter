# services/agents/ai_architect.py
from __future__ import annotations

from typing import Any, Dict, List

try:
    from services.app_server.schemas.blueprint import (
        Blueprint,
        BlueprintFrontend,
        BlueprintBackend,
        BlueprintDatabase,
        BlueprintLocalization,
    )
except Exception:
    Blueprint = Any  # type: ignore
    BlueprintFrontend = Any  # type: ignore
    BlueprintBackend = Any  # type: ignore
    BlueprintDatabase = Any  # type: ignore
    BlueprintLocalization = Any  # type: ignore


def _blueprint_to_dict(bp: Any) -> Dict[str, Any]:
    if bp is None:
        return {}
    if isinstance(bp, dict):
        return bp
    model_dump = getattr(bp, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    as_dict = getattr(bp, "dict", None)
    if callable(as_dict):
        return as_dict()
    return {}


def _extract_frontend(bp: Any) -> Dict[str, Any]:
    if bp is None:
        return {}
    if isinstance(bp, dict):
        f = bp.get("frontend") or {}
        if isinstance(f, dict):
            return {
                "framework": str(f.get("framework") or "nextjs"),
                "language": str(f.get("language") or "typescript"),
                "targets": list(f.get("targets") or ["web"]),
            }
        return {}
    frontend = getattr(bp, "frontend", None)
    if frontend is None:
        return {}
    framework = getattr(frontend, "framework", "nextjs")
    language = getattr(frontend, "language", "typescript")
    targets = getattr(frontend, "targets", ["web"])
    return {
        "framework": str(framework or "nextjs"),
        "language": str(language or "typescript"),
        "targets": list(targets or ["web"]),
    }


def _extract_backend(bp: Any) -> Dict[str, Any]:
    if bp is None:
        return {}
    if isinstance(bp, dict):
        b = bp.get("backend") or {}
        if isinstance(b, dict):
            framework = str(b.get("framework") or "fastapi")
            language = str(b.get("language") or "python")
            style_raw = str(b.get("style") or "rest").lower()
            style = style_raw if style_raw in ("rest", "graphql", "rpc") else "rest"
            return {
                "framework": framework,
                "language": language,
                "style": style,
            }
        return {}
    backend = getattr(bp, "backend", None)
    if backend is None:
        return {}
    framework = getattr(backend, "framework", "fastapi")
    language = getattr(backend, "language", "python")
    style_raw = str(getattr(backend, "style", "rest")).lower()
    style = style_raw if style_raw in ("rest", "graphql", "rpc") else "rest"
    return {
        "framework": str(framework or "fastapi"),
        "language": str(language or "python"),
        "style": style,
    }


def _extract_database(bp: Any) -> Dict[str, Any]:
    if bp is None:
        return {}
    if isinstance(bp, dict):
        d = bp.get("database") or {}
        if isinstance(d, dict):
            engine = str(d.get("engine") or "sqlite")
            mode_raw = str(d.get("mode") or "single_node").lower()
            mode = mode_raw if mode_raw in ("single_node", "clustered") else "single_node"
            return {
                "engine": engine,
                "mode": mode,
            }
        return {}
    database = getattr(bp, "database", None)
    if database is None:
        return {}
    engine = getattr(database, "engine", "sqlite")
    mode_raw = str(getattr(database, "mode", "single_node")).lower()
    mode = mode_raw if mode_raw in ("single_node", "clustered") else "single_node"
    return {
        "engine": str(engine or "sqlite"),
        "mode": mode,
    }


def _extract_kind(bp: Any) -> str:
    if bp is None:
        return "web_app"
    if isinstance(bp, dict):
        raw = str(bp.get("kind") or "web_app").strip().lower()
    else:
        raw = str(getattr(bp, "kind", "web_app")).strip().lower()
    allowed = {
        "website",
        "web_app",
        "mobile_app",
        "dashboard",
        "api_only",
        "cli",
        "service",
    }
    if raw in allowed:
        return raw
    return "web_app"


def _suggest_services(
    kind: str, frontend: Dict[str, Any], backend: Dict[str, Any]
) -> List[Dict[str, Any]]:
    services: List[Dict[str, Any]] = []

    frontend_service = {
        "name": "web",
        "kind": "frontend",
        "framework": frontend.get("framework") or "nextjs",
        "language": frontend.get("language") or "typescript",
        "targets": frontend.get("targets") or ["web"],
    }
    services.append(frontend_service)

    backend_service = {
        "name": "api",
        "kind": "backend",
        "framework": backend.get("framework") or "fastapi",
        "language": backend.get("language") or "python",
        "style": backend.get("style") or "rest",
    }
    services.append(backend_service)

    if kind in ("service", "api_only"):
        worker_service = {
            "name": "worker",
            "kind": "worker",
            "framework": backend.get("framework") or "fastapi",
            "language": backend.get("language") or "python",
        }
        services.append(worker_service)

    return services


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    bp = payload.get("blueprint")
    kind = _extract_kind(bp)
    frontend = _extract_frontend(bp)
    backend = _extract_backend(bp)
    database = _extract_database(bp)
    services = _suggest_services(kind, frontend, backend)
    bp_snapshot = _blueprint_to_dict(bp)

    notes: List[str] = []
    notes.append("kind=" + kind)
    notes.append("frontend=" + frontend.get("framework", "nextjs"))
    notes.append("backend=" + backend.get("framework", "fastapi"))
    notes.append("db=" + database.get("engine", "sqlite"))

    return {
        "ok": True,
        "agent": "ai_architect",
        "kind": kind,
        "services": services,
        "database": database,
        "blueprint": bp_snapshot,
        "notes": notes,
    }
