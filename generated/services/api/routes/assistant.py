from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from services.agents import assistant_intake
from services.queue import get_queue

q = get_queue()


router = APIRouter(prefix="/v1/assistant", tags=["assistant"])


class AssistantIntakeRequest(BaseModel):
    company: Dict[str, Any]
    product: Dict[str, Any]
    idea: str
    run_pipeline: bool = False


class AssistantIntakeResponse(BaseModel):
    ok: bool
    language: str
    intake: Dict[str, Any]
    blueprint: Dict[str, Any]
    i18n: Dict[str, Any]
    pipeline_job_id: int | None = None
    pipeline_module: str | None = None


def _slug(value: str) -> str:
    s = (value or "").strip().lower()
    if not s:
        return "assistant_app"
    buf: list[str] = []
    last_us = False
    for ch in s:
        if ch.isalnum():
            buf.append(ch)
            last_us = False
        else:
            if not last_us:
                buf.append("_")
                last_us = True
    out = "".join(buf).strip("_")
    return out or "assistant_app"


@router.post("/intake", response_model=AssistantIntakeResponse)
async def assistant_intake_endpoint(req: AssistantIntakeRequest) -> AssistantIntakeResponse:
    payload: Dict[str, Any] = {
        "company": req.company,
        "product": req.product,
        "idea": req.idea,
    }

    res = assistant_intake.handle(payload) or {}
    ok = bool(res.get("ok", False))
    language = str(res.get("language") or "")
    intake = res.get("intake") or {}
    blueprint = res.get("blueprint") or {}
    i18n = res.get("i18n") or {}

    pipeline_job_id: int | None = None
    pipeline_module: str | None = None

    if req.run_pipeline and ok:
        company = intake.get("company") or {}
        product = intake.get("product") or {}
        localization = blueprint.get("localization") or {}

        module_source = (
            product.get("slug") or product.get("name") or company.get("name") or "assistant_app"
        )
        module = _slug(str(module_source))
        pipeline_module = module

        locales = localization.get("supported_languages") or product.get("locales") or ["en"]
        kind = blueprint.get("kind") or "web_app"

        pipe_payload: Dict[str, Any] = {
            "idea": req.idea,
            "module": module,
            "frontend": "nextjs",
            "backend": "fastapi",
            "database": "sqlite",
            "kind": kind,
            "schema": {},
            "locales": locales,
        }

        pipeline_job_id = q.enqueue(task="pipeline", payload=pipe_payload, priority=0)

    return AssistantIntakeResponse(
        ok=ok,
        language=language,
        intake=intake,
        blueprint=blueprint,
        i18n=i18n,
        pipeline_job_id=pipeline_job_id,
        pipeline_module=pipeline_module,
    )
