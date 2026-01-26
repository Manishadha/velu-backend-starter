from __future__ import annotations

from typing import Any, Dict, List

from services.app_server.schemas.runtime import RuntimeDescriptor, RuntimeProcess  # type: ignore


def _extract_blueprint_fields(payload: Dict[str, Any]) -> Dict[str, str]:
    bp = payload.get("blueprint")
    kind = "web_app"
    frontend_fw = "nextjs"
    backend_fw = "fastapi"

    if bp is None:
        return {
            "kind": kind,
            "frontend_framework": frontend_fw,
            "backend_framework": backend_fw,
        }

    if isinstance(bp, dict):
        kind_raw = bp.get("kind")
        if isinstance(kind_raw, str) and kind_raw.strip():
            kind = kind_raw.strip()
        f_stack = bp.get("frontend") or {}
        if isinstance(f_stack, dict):
            fw = f_stack.get("framework")
            if isinstance(fw, str) and fw.strip():
                frontend_fw = fw.strip().lower()
        b_stack = bp.get("backend") or {}
        if isinstance(b_stack, dict):
            fw = b_stack.get("framework")
            if isinstance(fw, str) and fw.strip():
                backend_fw = fw.strip().lower()
        return {
            "kind": kind,
            "frontend_framework": frontend_fw,
            "backend_framework": backend_fw,
        }

    kind_attr = getattr(bp, "kind", None)
    if isinstance(kind_attr, str) and kind_attr.strip():
        kind = kind_attr.strip()

    frontend = getattr(bp, "frontend", None)
    if frontend is not None:
        fw = getattr(frontend, "framework", None)
        if isinstance(fw, str) and fw.strip():
            frontend_fw = fw.strip().lower()

    backend = getattr(bp, "backend", None)
    if backend is not None:
        fw = getattr(backend, "framework", None)
        if isinstance(fw, str) and fw.strip():
            backend_fw = fw.strip().lower()

    return {
        "kind": kind,
        "frontend_framework": frontend_fw,
        "backend_framework": backend_fw,
    }


def _project_id_from_payload(payload: Dict[str, Any]) -> str:
    explicit = payload.get("project_id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    bp = payload.get("blueprint")
    if bp is None:
        return "project"

    if isinstance(bp, dict):
        bid = bp.get("id")
        name = bp.get("name")
        if isinstance(bid, str) and bid.strip():
            return bid.strip()
        if isinstance(name, str) and name.strip():
            return name.strip().lower().replace(" ", "_")
        return "project"

    bid = getattr(bp, "id", None)
    if isinstance(bid, str) and bid.strip():
        return bid.strip()

    name = getattr(bp, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip().lower().replace(" ", "_")

    return "project"


def _api_service(backend_fw: str) -> RuntimeProcess:
    if backend_fw in {"fastapi", "django"}:
        cmd = ["python", "-m", "generated.services.api.app"]
    elif backend_fw in {"express", "node", "nestjs"}:
        cmd = ["node", "generated/services/node/app.js"]
    else:
        cmd = ["python", "-m", "generated.services.api.app"]
    return RuntimeProcess(
        id="api",
        kind="api",
        command=cmd,
        cwd=None,
        env={},
    )


def _web_service(frontend_fw: str) -> RuntimeProcess | None:
    fw = frontend_fw.lower()
    if fw == "nextjs":
        return RuntimeProcess(
            id="web",
            kind="web",
            command=["npm", "run", "dev", "--", "--port", "3001"],
            cwd="generated/web",
            env={},
        )
    if fw == "react":
        return RuntimeProcess(
            id="web",
            kind="web",
            command=["npm", "run", "dev"],
            cwd="generated/react_spa",
            env={},
        )
    return None


def _mobile_service(frontend_fw: str) -> RuntimeProcess | None:
    fw = frontend_fw.lower()
    if fw in {"react_native", "expo"}:
        return RuntimeProcess(
            id="mobile",
            kind="web",
            command=["npm", "run", "start"],
            cwd="mobile/react_native",
            env={},
        )
    if fw == "flutter":
        return RuntimeProcess(
            id="mobile",
            kind="web",
            command=["flutter", "run"],
            cwd="mobile/flutter",
            env={},
        )
    return None


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    fields = _extract_blueprint_fields(payload)
    project_id = _project_id_from_payload(payload)

    backend_fw = fields["backend_framework"]
    frontend_fw = fields["frontend_framework"]

    services: List[RuntimeProcess] = []
    services.append(_api_service(backend_fw))

    web = _web_service(frontend_fw)
    if web is not None:
        services.append(web)

    mobile = _mobile_service(frontend_fw)
    if mobile is not None:
        services.append(mobile)

    descriptor = RuntimeDescriptor(project_id=project_id, services=services)

    return {
        "ok": True,
        "agent": "runtime_planner",
        "runtime": descriptor.model_dump(),
    }
