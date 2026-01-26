# services/app_server/routes/jobs.py
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request

from services.app_server.dependencies.scopes import require_scopes
from services.app_server.task_policy import allowed_tasks_for_claims
from services.contracts.jobs import JobCreate
from services.queue import using_postgres_jobs
from services.queue.jobs import enqueue_job, get_job, project_belongs_to_org
from services.queue.worker_entry import HANDLERS as WORKER_HANDLERS

router = APIRouter()
ALLOWED_TASKS: set[str] = set(WORKER_HANDLERS.keys())


def _truthy(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _claims_actor(claims: dict) -> tuple[str, str]:
    """
    Phase 2.1: enforce attribution invariant for Postgres jobs mode.
    We accept a few common claim key names to avoid breaking older token layouts.
    """
    actor_type = str(claims.get("actor_type") or "api_key").strip() or "api_key"

    actor_id = (
        claims.get("actor_id")
        or claims.get("api_key_id")
        or claims.get("key_id")
        or claims.get("sub")
    )
    actor_id = str(actor_id).strip() if actor_id is not None else ""

    if not actor_id:
        # In postgres mode we refuse to enqueue unattributed jobs.
        raise HTTPException(status_code=401, detail="invalid_actor")

    return actor_type, actor_id


@router.post(
    "/orgs/{org_id}/projects/{project_id}/jobs",
    dependencies=[Depends(require_scopes({"jobs:submit"}))],
)
def create_job(org_id: str, project_id: str, body: JobCreate, request: Request):
    if not using_postgres_jobs():
        raise HTTPException(status_code=400, detail="jobs api requires postgres backend")

    claims = getattr(request.state, "claims", None) or {}
    claims_org = claims.get("org_id")
    if not claims_org:
        raise HTTPException(status_code=401, detail="invalid_api_key_or_org_not_found")

    if str(claims_org) != str(org_id):
        raise HTTPException(status_code=404, detail="not_found_org_mismatch")

    if not project_belongs_to_org(project_id, org_id):
        raise HTTPException(status_code=404, detail="not_found_project_not_in_org")

    task_name = (body.task or "").strip()
    if task_name not in ALLOWED_TASKS:
        raise HTTPException(status_code=400, detail="task_not_allowed")

    env = (os.getenv("ENV") or "local").strip().lower()
    enforce_tiers = _truthy("ENFORCE_TIERS") or _truthy("VELU_ENFORCE_TIERS")
    if not (env in {"local", "test"} and not enforce_tiers):
        allowed = allowed_tasks_for_claims(claims)
        if task_name not in allowed:
            raise HTTPException(status_code=403, detail="upgrade_required")

    # Phase 2.1: actor attribution is mandatory in Postgres mode
    actor_type, actor_id = _claims_actor(claims)

    payload = body.payload if isinstance(body.payload, dict) else {}
    job_id = enqueue_job(
        {
            "task": task_name,
            "payload": payload,
            "actor_type": actor_type,
            "actor_id": actor_id,
        },
        org_id=str(org_id),
        project_id=str(project_id),
        actor_type=actor_type,
        actor_id=actor_id,
    )

    return {"ok": True, "job_id": str(job_id)}


@router.get(
    "/orgs/{org_id}/jobs/{job_id}",
    dependencies=[Depends(require_scopes({"jobs:read"}))],
)
def read_job(org_id: str, job_id: str, request: Request):
    if not using_postgres_jobs():
        raise HTTPException(status_code=400, detail="jobs api requires postgres backend")

    claims = getattr(request.state, "claims", None) or {}
    claims_org = claims.get("org_id")
    if not claims_org:
        raise HTTPException(status_code=401, detail="invalid_api_key_or_org_not_found")

    if str(claims_org) != str(org_id):
        raise HTTPException(status_code=404, detail="not_found")

    row = get_job(job_id)
    if not row or str(row.get("org_id")) != str(org_id):
        raise HTTPException(status_code=404, detail="not_found")

    if "id" in row:
        row["id"] = str(row["id"])

    return {"ok": True, "item": row}
