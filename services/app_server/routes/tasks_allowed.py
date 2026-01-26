from __future__ import annotations

from fastapi import APIRouter, Request
from services.app_server.task_policy import tasks_allowed_response

router = APIRouter()

@router.get("/tasks/allowed")
def tasks_allowed(request: Request):
    claims = getattr(request.state, "claims", None) or {}
    return tasks_allowed_response(claims)
