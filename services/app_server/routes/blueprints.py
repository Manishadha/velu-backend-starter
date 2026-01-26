# services/app_server/routes/blueprints.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.app_server.schemas.blueprint import Blueprint
from services.app_server.schemas.blueprint_factory import (
    blueprint_from_intake,
    blueprint_from_hospital_spec,
)
from services.app_server.schemas.intake import Intake
from services.app_server.blueprints_sqlite import (
    save_blueprint,
    get_blueprint,
    list_blueprints,
)
from services.agents import api_design

router = APIRouter(prefix="/v1/blueprints", tags=["blueprints"])


class BlueprintSave(BaseModel):
    id: str
    name: str
    kind: str
    frontend: dict[str, Any]
    backend: dict[str, Any]
    database: dict[str, Any]
    localization: dict[str, Any]


@router.post("/from-intake")
def from_intake_endpoint(body: dict[str, Any]) -> dict[str, Any]:
    """
    Endpoint used in tests:

    - body is the raw Intake JSON (tests send `intake.model_dump()`).
    - Response is a dict that includes:
        * company  (echoed from intake)
        * product  (echoed from intake)
        * blueprint (normalized Blueprint, serialized to dict)
    """
    intake = Intake(**body)
    bp: Blueprint = blueprint_from_intake(intake)

    company = body.get("company") or {}
    product = body.get("product") or {}

    return {
        "company": company,
        "product": product,
        "blueprint": bp.model_dump(),
    }


@router.post("/from-hospital")
def from_hospital_endpoint(body: dict[str, Any]) -> dict[str, Any]:
    """
    Endpoint used in tests:

    - body is the raw hospital spec JSON.
    - Response includes:
        * product   (derived from spec.project + localization)
        * stack     (echoed from spec.stack)
        * blueprint (normalized Blueprint, serialized to dict)
    """
    bp: Blueprint = blueprint_from_hospital_spec(body)

    project = body.get("project") or {}
    loc = body.get("localization") or {}
    stack = body.get("stack") or {}

    product = {
        "id": project.get("id"),
        "name": project.get("name"),
        "type": project.get("type"),
        "description": project.get("description"),
        "locales": loc.get("supported_languages") or [],
    }

    return {
        "product": product,
        "stack": stack,
        "blueprint": bp.model_dump(),
    }


@router.post("/design")
def design_blueprint(bp: Blueprint) -> dict[str, Any]:
    """
    Take a Blueprint and return an architecture summary via api_design.
    """
    res = api_design.handle({"blueprint": bp.model_dump()})
    arch = res.get("architecture") or {}
    return {
        "blueprint": bp.model_dump(),
        "architecture": arch,
    }


@router.post("/save")
def save_endpoint(bp: Blueprint) -> dict[str, Any]:
    """
    Save a blueprint to SQLite and return its id.
    """
    save_blueprint(bp.id, bp.model_dump())
    return {"ok": True, "id": bp.id}


@router.get("/{bp_id}")
def get_endpoint(bp_id: str) -> Blueprint:
    """
    Load a blueprint by id, or 404 if missing.
    """
    data = get_blueprint(bp_id)
    if not data:
        raise HTTPException(status_code=404, detail="blueprint not found")
    return Blueprint(**data)


@router.get("")
def list_blueprints_api(limit: int = 20) -> dict[str, Any]:
    """
    List recent blueprints.
    """
    items = list_blueprints(limit=max(1, min(200, int(limit))))
    return {"ok": True, "items": items}
