# services/app_server/admin.py
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from services.app_server.auth import using_postgres_api_keys
from services.auth.api_keys import create_api_key, list_api_keys, revoke_api_key, rotate_api_key
from services.queue import get_queue

q = get_queue()
router = APIRouter()


def admin_enabled() -> bool:
    return os.getenv("ADMIN_ROUTES", "0").lower() not in {"0", "", "false", "no"}


def _require_admin_ctx(request: Request) -> str | None:
    if not admin_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    if not using_postgres_api_keys():
        raise HTTPException(status_code=400, detail="admin api keys require postgres backend")

    claims = getattr(request.state, "claims", None) or {}
    org_id = claims.get("org_id")
    return str(org_id) if org_id else None


class ApiKeyCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    scopes: list[str] = Field(default_factory=list)


@router.get("/jobs")
def list_jobs(request: Request, limit: int = Query(50, ge=1, le=500)):
    if not admin_enabled():
        raise HTTPException(status_code=404, detail="Not Found")

    org_id = _require_admin_ctx(request)
    if not org_id:
        raise HTTPException(status_code=401, detail="invalid api key or org not found")
    return {"items": q.list_recent_for_org(org_id=org_id, limit=limit)}


@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    if not admin_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
    item = q.load(job_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"item": item}


@router.post("/api-keys")
def admin_create_api_key(body: ApiKeyCreateIn, request: Request):
    org_id = _require_admin_ctx(request)
    if not org_id:
        raise HTTPException(status_code=401, detail="invalid api key or org not found")
    try:
        rec = create_api_key(org_id=org_id, name=body.name, scopes=body.scopes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "item": rec}


@router.get("/api-keys")
def admin_list_api_keys(request: Request):
    org_id = _require_admin_ctx(request)
    if not org_id:
        raise HTTPException(status_code=401, detail="invalid api key or org not found")
    return {"ok": True, "items": list_api_keys(org_id=org_id)}


@router.post("/api-keys/{key_id}/revoke")
def admin_revoke_api_key(key_id: str, request: Request):
    org_id = _require_admin_ctx(request)
    try:
        revoke_api_key(org_id=org_id, key_id=key_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="not_found") from None
    return {"ok": True}


@router.post("/api-keys/{key_id}/rotate")
def admin_rotate_api_key(key_id: str, request: Request):
    org_id = _require_admin_ctx(request)
    try:
        rec = rotate_api_key(org_id=org_id, key_id=key_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="not_found") from None
    return {"ok": True, "item": rec}
