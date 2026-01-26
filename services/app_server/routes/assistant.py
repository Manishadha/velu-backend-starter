from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request
from pydantic import BaseModel

from services.agents import language_detector
from services.app_server.schemas.intake import Company, Intake, Product
from services.app_server.schemas import blueprint_factory
from services.app_server.routes.i18n import _build_messages
from services.app_server.auth import claims_from_request
from services.app_server.task_policy import allowed_tasks_for_claims
from services.queue.jobs import enqueue_job



router = APIRouter()


class AssistantIntakeBody(BaseModel):
    company: Dict[str, Any]
    product: Dict[str, Any]
    idea: str | None = None
    run_pipeline: bool = False


@router.post("/v1/assistant/intake")
def assistant_intake(body: AssistantIntakeBody, request: Request) -> Dict[str, Any]:
    company = Company(**body.company)
    product = Product(**body.product)

    intake = Intake(company=company, product=product)

    detected_lang: str | None = None
    if body.idea:
        try:
            det = language_detector.handle({"text": body.idea})
            detected_lang = str(det.get("language") or "").strip() or None
        except Exception:
            detected_lang = None

    if not intake.user_language and detected_lang:
        intake.user_language = detected_lang
    if not intake.original_text_language and detected_lang:
        intake.original_text_language = detected_lang

    blueprint = blueprint_factory.blueprint_from_intake(intake)
    locales = blueprint.localization.supported_languages
    messages = _build_messages(blueprint.name, locales)

    claims = claims_from_request(request) or {}
    org_id = claims.get("org_id")
    project_id = claims.get("project_id")

    pipeline_job_id = None
    pipeline_module = None

    if body.run_pipeline:
        allowed = allowed_tasks_for_claims(claims)
        if "pipeline" not in allowed:
            return {
                "ok": True,
                "language": intake.user_language or detected_lang or blueprint.localization.default_language,
                "intake": intake.to_pipeline_payload(),
                "blueprint": blueprint,
                "i18n": {
                    "locales": locales,
                    "messages": messages,
                    "summary": {"locales": locales, "kind": blueprint.kind, "name": blueprint.name},
                },
                "pipeline_job_id": None,
                "pipeline_module": None,
                "warning": "pipeline_not_allowed_for_tier",
            }

        payload = {
            "intake": intake.to_pipeline_payload(),
            "blueprint": getattr(blueprint, "model_dump", lambda: blueprint)(),
            "_velu": {"source": "assistant_intake"},
        }

        pipeline_job_id = enqueue_job(
            {"task": "pipeline", "payload": payload},
            org_id=org_id,
            project_id=project_id,
            actor_type=claims.get("actor_type", "api_key"),
            actor_id=claims.get("actor_id"),
        )
        pipeline_module = "pipeline"

    return {
        "ok": True,
        "language": intake.user_language or detected_lang or blueprint.localization.default_language,
        "intake": intake.to_pipeline_payload(),
        "blueprint": blueprint,
        "i18n": {
            "locales": locales,
            "messages": messages,
            "summary": {"locales": locales, "kind": blueprint.kind, "name": blueprint.name},
        },
        "pipeline_job_id": pipeline_job_id,
        "pipeline_module": pipeline_module,
    }
