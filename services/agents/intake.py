from __future__ import annotations

import logging
from typing import Any, Dict

from services.queue import get_queue

logger = logging.getLogger(__name__)


def _norm_str(v: Any, default: str = "") -> str:
    if isinstance(v, (str, bytes)):
        s = str(v).strip()
        return s if s else default
    return default


def _norm_list_str(v: Any) -> list[str] | None:
    if isinstance(v, list):
        out: list[str] = []
        for x in v:
            s = str(x).strip()
            if s:
                out.append(s)
        return out or None
    if isinstance(v, str):
        parts = [p.strip() for p in v.split(",") if p.strip()]
        return parts or None
    return None


def _infer_product_type(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k in {"marketplace"}:
        return "marketplace"
    if k in {"chat", "messaging"}:
        return "chat"
    if k in {"dashboard", "admin", "console"}:
        return "dashboard"
    if k in {"api", "api_only"}:
        return "api_only"
    if k in {"mobile_app", "mobile"}:
        return "mobile_app"
    return "web_app"


def _infer_platforms(product_type: str, payload: dict[str, Any]) -> list[str]:
    explicit = _norm_list_str(payload.get("platforms"))
    if explicit:
        return explicit
    if product_type == "api_only":
        return ["api"]
    if product_type == "mobile_app":
        return ["mobile", "api"]
    if product_type == "dashboard":
        return ["web", "api", "admin"]
    if product_type in {"marketplace", "web_app", "chat"}:
        return ["web", "api", "admin"]
    return ["web", "api"]


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    kind = _norm_str(payload.get("kind"), "app").lower()
    idea = _norm_str(payload.get("idea"), "New Velu app")
    module = _norm_str(payload.get("module"), "app_mod")

    frontend = _norm_str(payload.get("frontend"), "nextjs").lower()
    backend = _norm_str(payload.get("backend"), "fastapi").lower()
    database = _norm_str(payload.get("database"), "sqlite").lower()

    schema = payload.get("schema") or {}

    raw_session_id = payload.get("session_id")
    session_id = raw_session_id.strip() if isinstance(raw_session_id, str) and raw_session_id.strip() else None

    raw_user_language = payload.get("user_language")
    user_language = raw_user_language.strip() if isinstance(raw_user_language, str) and raw_user_language.strip() else None

    raw_original_text_language = payload.get("original_text_language")
    original_text_language = (
        raw_original_text_language.strip()
        if isinstance(raw_original_text_language, str) and raw_original_text_language.strip()
        else None
    )

    ui_languages = _norm_list_str(payload.get("ui_languages"))
    locales = _norm_list_str(payload.get("locales")) or ui_languages or ["en"]

    product_type = _infer_product_type(kind)
    platforms = _infer_platforms(product_type, payload)

    lane = _norm_str(payload.get("lane"), "py_fastapi_next_postgres")
    security_level = _norm_str(payload.get("security_level"), "standard").lower() or "standard"

    features = payload.get("features")
    if not isinstance(features, list):
        features = []

    product_spec: dict[str, Any] = {
        "version": 1,
        "product_type": product_type,
        "platforms": platforms,
        "lane": lane,
        "locales": locales,
        "security_level": security_level,
        "features": features,
        "release": {
            "format": "zip",
            "layout": ["backend", "frontend", "infra", "docs", "artifacts/manifest.json"],
        },
    }

    norm: dict[str, Any] = {
        "kind": kind,
        "idea": idea,
        "module": module,
        "frontend": frontend,
        "backend": backend,
        "database": database,
        "schema": schema,
        "session_id": session_id,
        "product_spec": product_spec,
    }

    if user_language is not None:
        norm["user_language"] = user_language
    if original_text_language is not None:
        norm["original_text_language"] = original_text_language
    if ui_languages is not None:
        norm["ui_languages"] = ui_languages

    return norm


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        norm = _normalize(payload or {})
    except Exception as e:
        err = f"normalize-failed: {type(e).__name__}: {e}"
        logger.exception("intake._normalize failed")
        return {"ok": False, "agent": "intake", "error": err}

    q = get_queue()
    session_id = norm.get("session_id")

    pipe_payload: Dict[str, Any] = {
        "idea": norm["idea"],
        "module": norm["module"],
        "schema": norm["schema"],
        "kind": norm["kind"],
        "frontend": norm["frontend"],
        "backend": norm["backend"],
        "database": norm["database"],
        "product_spec": norm["product_spec"],
    }

    if session_id:
        pipe_payload["session_id"] = session_id
    if "user_language" in norm:
        pipe_payload["user_language"] = norm["user_language"]
    if "original_text_language" in norm:
        pipe_payload["original_text_language"] = norm["original_text_language"]
    if "ui_languages" in norm:
        pipe_payload["ui_languages"] = norm["ui_languages"]

    jid = q.enqueue(task="pipeline", payload=pipe_payload, priority=0)

    if session_id:
        try:
            from src import landing_sync

            logger.info("intake: syncing frontend for session_id=%s", session_id)
            landing_sync.sync_frontend(session_id)
        except Exception as e:
            logger.warning("intake: landing_sync failed for session_id=%s: %s", session_id, e)

    result: Dict[str, Any] = {
        "ok": True,
        "agent": "intake",
        "msg": "intake accepted; pipeline enqueued",
        "pipeline_job_id": jid,
        "normalized": norm,
    }
    if session_id:
        result["session_id"] = session_id
    return result
