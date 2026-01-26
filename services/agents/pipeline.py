# services/agents/pipeline.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Mapping

from services.queue import get_queue

q = get_queue()
logger = logging.getLogger(__name__)

PLAN_STR = (
    "requirements → architecture → datamodel → api_design → "
    "ui_scaffold → backend_scaffold → ai_features → "
    "security_hardening → testgen"
)


def _extract_locales(payload: Mapping[str, Any]) -> list[str]:
    direct = payload.get("locales")
    if isinstance(direct, list):
        vals = [str(v).strip() for v in direct if str(v).strip()]
        if vals:
            return vals

    product = payload.get("product")
    if isinstance(product, Mapping):
        vals = product.get("locales")
        if isinstance(vals, list):
            clean = [str(v).strip() for v in vals if str(v).strip()]
            if clean:
                return clean

    spec = payload.get("localization")
    if isinstance(spec, Mapping):
        vals = spec.get("supported_languages")
        if isinstance(vals, list):
            clean = [str(v).strip() for v in vals if str(v).strip()]
            if clean:
                return clean

    return ["en"]


def handle(task_or_payload: Any, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(task_or_payload, dict) and payload is None:
        payload = dict(task_or_payload)
    else:
        payload = dict(payload or {})

    idea = str(payload.get("idea", "")).strip() or "demo"
    module = str(payload.get("module", "")).strip() or "hello_mod"

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

    frontend = payload.get("frontend") or "nextjs"
    backend = payload.get("backend") or "fastapi"
    database = payload.get("database") or "sqlite"
    kind = payload.get("kind") or "web_app"
    schema = payload.get("schema") or {}
    locales = _extract_locales(payload)

    # ui_languages defaults to locales
    raw_ui_langs = payload.get("ui_languages")
    ui_languages: list[str] | None = None
    if isinstance(raw_ui_langs, list):
        vals = [str(v).strip() for v in raw_ui_langs if str(v).strip()]
        if vals:
            ui_languages = vals
    elif isinstance(raw_ui_langs, str):
        parts = [s.strip() for s in raw_ui_langs.split(",") if s.strip()]
        if parts:
            ui_languages = parts
    if ui_languages is None:
        ui_languages = list(locales)

    plan_title = f"{idea} via {module}"
    plan_text = f"{plan_title}: {PLAN_STR}"

    # Base payload shared by stages
    base_payload: Dict[str, Any] = {
        "idea": idea,
        "module": module,
        "frontend": frontend,
        "backend": backend,
        "database": database,
        "kind": kind,
        "schema": schema,
        "locales": locales,
        "ui_languages": ui_languages,
    }
    if session_id:
        base_payload["session_id"] = session_id
    if user_language:
        base_payload["user_language"] = user_language
    if original_text_language:
        base_payload["original_text_language"] = original_text_language

    # -------------------------
    # Stage 1: execute
    # IMPORTANT: executor allows ONLY src/ and tests/
    # So we MUST write tests under tests/ (not tests_app) and skip pytest.ini.
    # -------------------------
    files = [
        {
            "path": f"src/{module}.py",
            "content": (
                "def greet(name: str) -> str:\n"
                '    """Simple greeter used by pipeline smoke tests."""\n'
                '    return f"Hello, {name}!"\n'
            ),
        },
        {
            "path": f"tests/test_{module}.py",
            "content": (
                f"from {module} import greet\n\n"
                "def test_greet_pipeline():\n"
                '    assert greet("Velu") == "Hello, Velu!"\n'
            ),
        },
    ]

    # Add files_json fallback in case any layer strips list/dict payload values
    execute_payload: Dict[str, Any] = {
        **base_payload,
        "rootdir": ".",
        "files": files,
        "files_json": json.dumps(files),
    }
    execute_id = q.enqueue(task="execute", payload=execute_payload, priority=0)

    # -------------------------
    # Stage 2: test
    # Run the explicit test file we created.
    # -------------------------
    test_payload: Dict[str, Any] = {
        **base_payload,
        "rootdir": ".",
        "tests_path": f"tests/test_{module}.py",
        "depends_on": [execute_id],
        "args": ["-q", "--maxfail=1", "--disable-warnings", "--basetemp=/tmp/pytest"],
    }
    test_id = q.enqueue(task="test", payload=test_payload, priority=0)

    # -------------------------
    # Stage 3: packager
    # -------------------------
    packager_payload: Dict[str, Any] = {
        **base_payload,
        "rootdir": ".",
        "depends_on": [execute_id, test_id],
    }
    packager_id = q.enqueue(task="packager", payload=packager_payload, priority=0)

    # Optional: multi-step agent pipeline
    pipeline_mode = os.getenv("VELU_PIPELINE_MODE", "simple").strip().lower()
    pipeline_subjobs: Dict[str, int] = {}

    if pipeline_mode == "multi":
        logger.info("pipeline: multi-step mode enabled for module=%s", module)

        agent_payload: Dict[str, Any] = dict(base_payload)

        steps = [
            "requirements",
            "architecture",
            "datamodel",
            "api_design",
            "ui_scaffold",
            "backend_scaffold",
            "ai_features",
            "security_hardening",
            "testgen",
        ]

        for step in steps:
            try:
                jid = q.enqueue(task=step, payload=agent_payload, priority=0)
                pipeline_subjobs[step] = jid
                logger.info("pipeline: enqueued step=%s job_id=%s", step, jid)
            except Exception as e:
                logger.warning("pipeline: failed to enqueue step=%s for module=%s: %s", step, module, e)

    result: Dict[str, Any] = {
        "ok": True,
        "agent": "pipeline",
        "plan": plan_text,
        "subjobs": {
            "execute": execute_id,
            "test": test_id,
            "packager": packager_id,
        },
        "payload": base_payload,
        "pipeline_mode": pipeline_mode,
        "pipeline": {
            "name": "simple_pipeline",
            "stages": [
                {"name": "execute", "job_id": execute_id, "status": "queued"},
                {"name": "test", "job_id": test_id, "status": "queued"},
                {"name": "packager", "job_id": packager_id, "status": "queued"},
            ],
            "gates": {
                "unit_tests": "pending",
                "build": "pending",
                "security": "pending",
            },
        },
    }

    if pipeline_subjobs:
        result["pipeline_subjobs"] = pipeline_subjobs

    return result
