from __future__ import annotations

from typing import Any, Dict, List


def _plan_command_for_service(service: Dict[str, Any], os_name: str) -> str | None:
    service_id = str(service.get("id") or "service")
    kind = str(service.get("kind") or "").lower()
    language = str(service.get("language") or "").lower()
    cwd = str(service.get("cwd") or "")
    cwd_norm = cwd.replace("\\", "/")

    os_name = os_name.lower()
    if os_name not in ("linux", "darwin", "mac", "macos", "windows"):
        os_name = "linux"

    is_unix = os_name in ("linux", "darwin", "mac", "macos")

    # Mobile
    if service_id == "mobile":
        if "mobile/react_native" in cwd_norm:
            return "cd mobile/react_native && npm install && npx expo start"
        if "mobile/flutter" in cwd_norm:
            return "cd mobile/flutter && flutter run"
        return None

    # FastAPI (IMPORTANT: tests expect `generated.services.api.app:app`)
    if "fastapi" in kind or (service_id == "api" and language == "python"):
        if is_unix:
            return (
                "PYTHONPATH=src:generated "
                "uvicorn generated.services.api.app:app --reload --port 8000"
            )
        # windows: user can set env separately; keep command simple
        return "uvicorn generated.services.api.app:app --reload --port 8000"

    # Node API
    if "node_api" in kind or (
        service_id == "api" and language in ("node", "javascript", "typescript")
    ):
        return "cd generated/services/node && npm install && npm run dev"

    # Next.js
    if "nextjs" in kind or ("next" in kind and service_id == "web"):
        return "cd generated/web && npm install && npm run dev -- --port 3000"

    # React SPA
    if "react_spa" in kind or ("react" in kind and service_id == "web"):
        return "cd generated/react_spa && npm install && npm run dev"

    return None


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime = payload.get("runtime") or {}
    os_name = str(payload.get("os") or "linux").lower()

    services: List[Dict[str, Any]] = []
    raw_services = runtime.get("services") or []

    for service in raw_services:
        if not isinstance(service, dict):
            continue
        cmd = _plan_command_for_service(service, os_name)
        if cmd is None:
            continue
        service_id = str(service.get("id") or "service")
        services.append({"id": service_id, "command": cmd, "os": os_name})

    return {
        "ok": True,
        "agent": "runtime_command_planner",
        "os": os_name,
        "services": services,
    }
