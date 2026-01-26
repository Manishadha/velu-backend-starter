from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping

from services.pipelines.catalog import select_pipeline
from services.queue import get_queue

logger = logging.getLogger(__name__)


def _extract_product_spec(payload: Mapping[str, Any]) -> dict[str, Any]:
    spec = payload.get("product_spec")
    if isinstance(spec, dict):
        out = dict(spec)
    else:
        out = {"version": 1}

    kind = str(payload.get("kind") or "").strip().lower()
    if "product_type" not in out or not str(out.get("product_type") or "").strip():
        if kind in {"marketplace"}:
            out["product_type"] = "marketplace"
        elif kind in {"chat", "messaging"}:
            out["product_type"] = "chat"
        elif kind in {"dashboard", "admin", "console"}:
            out["product_type"] = "dashboard"
        elif kind in {"api", "api_only"}:
            out["product_type"] = "api_only"
        elif kind in {"mobile_app", "mobile"}:
            out["product_type"] = "mobile_app"
        else:
            out["product_type"] = "web_app"

    if "platforms" not in out or not isinstance(out.get("platforms"), list) or not out.get("platforms"):
        out["platforms"] = ["web", "api", "admin"]

    if "lane" not in out or not str(out.get("lane") or "").strip():
        out["lane"] = "py_fastapi_next_postgres"

    if "locales" not in out or not isinstance(out.get("locales"), list) or not out.get("locales"):
        raw_locales = payload.get("locales")
        if isinstance(raw_locales, list) and [str(x).strip() for x in raw_locales if str(x).strip()]:
            out["locales"] = [str(x).strip() for x in raw_locales if str(x).strip()]
        else:
            out["locales"] = ["en"]

    if "security_level" not in out or not str(out.get("security_level") or "").strip():
        out["security_level"] = "standard"

    if "features" not in out or not isinstance(out.get("features"), list):
        out["features"] = []

    if "release" not in out or not isinstance(out.get("release"), dict):
        out["release"] = {
            "format": "zip",
            "layout": ["backend", "frontend", "infra", "docs", "artifacts/manifest.json"],
        }

    out["version"] = int(out.get("version") or 1)
    return out


def _env_name() -> str:
    return (os.getenv("ENV") or "local").strip().lower() or "local"


def _workspace_base() -> Path:
    v = (os.getenv("WORKSPACE_BASE") or "").strip()
    if v:
        return Path(v)
    velu_tmp = (os.getenv("VELU_TMP") or "").strip()
    if velu_tmp:
        return Path(velu_tmp)
    return Path(tempfile.gettempdir())


def handle(task_or_payload: Any, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(task_or_payload, dict) and payload is None:
        payload = task_or_payload
    payload = dict(payload or {})

    q = get_queue()

    idea = str(payload.get("idea") or "demo").strip() or "demo"
    module = str(payload.get("module") or "app_mod").strip() or "app_mod"
    session_id = payload.get("session_id")

    run_id = str(payload.get("run_id") or "").strip() or uuid.uuid4().hex[:16]
    env_name = _env_name()
    base = _workspace_base()
    workspace = (base / "velu-workspace" / env_name / run_id).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    product_spec = _extract_product_spec(payload)

    pipe = select_pipeline(product_spec)
    pipeline_name = pipe["name"]
    stage_names = list(pipe["stages"])
    gates = dict(pipe["gates"])

    incoming_velu = payload.get("_velu") if isinstance(payload.get("_velu"), dict) else {}
    velu_meta = dict(incoming_velu)
    velu_meta.setdefault("run_id", run_id)
    velu_meta.setdefault("workspace", str(workspace))

    stage_payload: Dict[str, Any] = {
        "idea": idea,
        "module": module,
        "kind": payload.get("kind") or "web_app",
        "frontend": payload.get("frontend") or "nextjs",
        "backend": payload.get("backend") or "fastapi",
        "database": payload.get("database") or "sqlite",
        "schema": payload.get("schema") or {},
        "product_spec": product_spec,
        "locales": product_spec.get("locales") or ["en"],
        "ui_languages": payload.get("ui_languages") or product_spec.get("locales") or ["en"],
        "_velu": velu_meta,
    }

    if isinstance(session_id, str) and session_id.strip():
        stage_payload["session_id"] = session_id.strip()
    if "user_language" in payload:
        stage_payload["user_language"] = payload.get("user_language")
    if "original_text_language" in payload:
        stage_payload["original_text_language"] = payload.get("original_text_language")

    stage_priority: dict[str, int] = {
        "execute": 30,
        "test": 20,
        "packager": 10,
        "security_scan": 5,
        "pipeline_waiter": 0,
    }

    stages_out: list[dict[str, Any]] = []
    subjobs: dict[str, Any] = {}

    for st in stage_names:
        p = dict(stage_payload)
        p["_velu"] = dict(stage_payload.get("_velu") or {})
        meta = p.get("_velu") if isinstance(p.get("_velu"), dict) else {}

        jid = q.enqueue(
            task=st,
            payload=p,
            priority=int(stage_priority.get(st, 0)),
            org_id=str(meta.get("org_id")) if meta.get("org_id") else None,
            project_id=str(meta.get("project_id")) if meta.get("project_id") else None,
            actor_type=str(meta.get("actor_type") or "api_key"),
            actor_id=str(meta.get("actor_id")) if meta.get("actor_id") else None,
        )
        subjobs[st] = jid
        stages_out.append({"name": st, "job_id": jid, "status": "queued"})

    waiter_payload: Dict[str, Any] = {
        "pipeline_name": pipeline_name,
        "stage_jobs": dict(subjobs),
        "gates": dict(gates),
        "idea": idea,
        "module": module,
        "_velu": dict(velu_meta),
    }

    waiter_id = q.enqueue(
        task="pipeline_waiter",
        payload=waiter_payload,
        priority=int(stage_priority.get("pipeline_waiter", 0)),
        org_id=str(velu_meta.get("org_id")) if velu_meta.get("org_id") else None,
        project_id=str(velu_meta.get("project_id")) if velu_meta.get("project_id") else None,
        actor_type=str(velu_meta.get("actor_type") or "api_key"),
        actor_id=str(velu_meta.get("actor_id")) if velu_meta.get("actor_id") else None,
    )
    subjobs["pipeline_waiter"] = waiter_id

    result: Dict[str, Any] = {
        "ok": True,
        "agent": "pipeline",
        "pipeline_mode": "catalog",
        "payload": {
            "idea": idea,
            "module": module,
            "session_id": session_id if isinstance(session_id, str) else None,
            "product_spec": product_spec,
            "run_id": run_id,
            "workspace": str(workspace),
        },
        "subjobs": subjobs,
        "pipeline": {
            "name": pipeline_name,
            "stages": stages_out,
            "gates": gates,
            "waiter_job_id": waiter_id,
            "run_id": run_id,
            "workspace": str(workspace),
        },
        "plan": f"{idea} via {module}: {pipeline_name}",
    }
    return result
