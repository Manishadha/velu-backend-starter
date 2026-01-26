from __future__ import annotations

import os
import time
import uuid
from contextlib import closing
from typing import Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from services.app_server.dependencies.scopes import require_scopes
from services.auth.api_keys import create_api_key

router = APIRouter()


def _env() -> str:
    return (os.getenv("ENV") or "local").strip().lower()


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _test_db_lookup_enabled() -> bool:
    return _truthy("VELU_TEST_DB_LOOKUP")


def _allow_raw_keys() -> bool:
    if _truthy("ORG_BOOTSTRAP_RETURN_RAW"):
        return True
    env = (os.getenv("ENV") or "local").strip().lower()
    return env in {"local", "test", "dev"}




def _strip_raw_key(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item or {})
    out.pop("raw_key", None)
    return out


def _mask_key(raw_key: str) -> str:
    rk = (raw_key or "").strip()
    if not rk:
        return ""
    if len(rk) <= 8:
        return "****"
    return rk[:4] + "..." + rk[-4:]


def _db_url_optional() -> str | None:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        return None
    if raw.lower().startswith("postgresql+psycopg://"):
        return "postgresql://" + raw.split("://", 1)[1]
    if raw.lower().startswith("postgres://"):
        return "postgresql://" + raw.split("://", 1)[1]
    return raw


def _db_url_required() -> str:
    url = _db_url_optional()
    if url:
        return url
    if _env() in {"local", "test", "dev"}:
        return ""
    raise RuntimeError("DATABASE_URL is required")


def _pg_connect() -> psycopg.Connection:
    url = _db_url_optional()
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return psycopg.connect(url, autocommit=False)


def _require_platform_admin(request: Request) -> None:
    claims = getattr(request.state, "claims", None) or {}
    if claims.get("is_platform_admin"):
        return
    raise HTTPException(status_code=401, detail="invalid api key or org not found")



class OrgCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=80)
    plan: str = Field(default="base", min_length=1, max_length=32)


class OrgUpdatePlanIn(BaseModel):
    plan: str = Field(min_length=1, max_length=32)


class OrgBootstrapIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=80)
    plan: str = Field(default="base", min_length=1, max_length=32)


def _norm_slug(s: str) -> str:
    s = (s or "").strip().lower()
    out: list[str] = []
    for ch in s:
        if ch.isalnum() or ch in {"-", "_"}:
            out.append(ch)
    return "".join(out)

def _norm_project_slug(name: str) -> str:
    s = (name or "").strip().lower()
    out: list[str] = []
    for ch in s:
        if ch.isalnum() or ch in {"-", "_"}:
            out.append(ch)
        elif ch.isspace():
            out.append("-")
    slug = "".join(out).strip("-")
    return slug or "default"

def _norm_plan(p: str) -> str:
    p = (p or "").strip().lower()
    if p not in {"base", "hero", "superhero"}:
        return "base"
    return p


_MEM_ORGS: dict[str, dict[str, Any]] = {}

def _ensure_project(org_id: str, name: str = "default") -> dict[str, Any]:
    """
    Ensure a default project exists for this org. Returns the project record.
    - In memory mode: stored in a local dict
    - In Postgres mode: stored in projects table
    """
    oid = (org_id or "").strip()
    if not oid:
        raise HTTPException(status_code=400, detail="invalid_org_id")

    url = _db_url_optional()
    if not url and (_env() in {"local", "test", "dev"} or _test_db_lookup_enabled()):
        # simple in-memory project store (keyed by org_id)
        key = f"{oid}:{name.strip().lower()}"
        proj = _MEM_ORGS.get(key)
        if proj:
            return proj
        now = int(time.time())
        proj = {
            "id": str(uuid.uuid4()),
            "org_id": oid,
            "name": name.strip(),
            "slug": _norm_project_slug(name),
            "created_at": now,
            "updated_at": now,
            "_mem": True,
        }
        _MEM_ORGS[key] = proj
        return proj

    with closing(_pg_connect()) as conn:
        with conn:
            row = conn.execute(
                """
                SELECT id::text, org_id::text, name, slug, created_at
                  FROM projects
                 WHERE org_id=%s::uuid
                 ORDER BY created_at ASC
                 LIMIT 1
                """,
                (oid,),
            ).fetchone()

            if row:
                return {
                    "id": row[0],
                    "org_id": row[1],
                    "name": row[2],
                    "slug": row[3],
                    "created_at": row[4],
                }

            slug = _norm_project_slug(name)

            row2 = conn.execute(
                """
                INSERT INTO projects (org_id, name, slug)
                VALUES (%s::uuid, %s, %s)
                RETURNING id::text, org_id::text, name, slug, created_at
                """,
                (oid, name.strip(), slug),
            ).fetchone()

            return {
                "id": row2[0],
                "org_id": row2[1],
                "name": row2[2],
                "slug": row2[3],
                "created_at": row2[4],
            }



def _ensure_org(slug: str, name: str, plan: str) -> dict[str, Any]:
    slug_n = _norm_slug(slug)
    if not slug_n:
        raise HTTPException(status_code=400, detail="invalid_slug")
    plan_n = _norm_plan(plan)

    url = _db_url_optional()
    if not url and (_env() in {"local", "test", "dev"} or _test_db_lookup_enabled()):
        existing = _MEM_ORGS.get(slug_n)
        if existing:
            return existing
        now = int(time.time())
        org = {
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "slug": slug_n,
            "plan": plan_n,
            "created_at": now,
            "updated_at": now,
            "_mem": True,
        }
        _MEM_ORGS[slug_n] = org
        return org

    with closing(_pg_connect()) as conn:
        with conn:
            row = conn.execute(
                "SELECT id::text, name, slug, plan FROM organizations WHERE slug=%s LIMIT 1",
                (slug_n,),
            ).fetchone()
            if row:
                return {"id": row[0], "name": row[1], "slug": row[2], "plan": _norm_plan(row[3])}

            row2 = conn.execute(
                """
                INSERT INTO organizations (name, slug, plan)
                VALUES (%s, %s, %s)
                RETURNING id::text, name, slug, plan, created_at, updated_at
                """,
                (name.strip(), slug_n, plan_n),
            ).fetchone()
            return {
                "id": row2[0],
                "name": row2[1],
                "slug": row2[2],
                "plan": _norm_plan(row2[3]),
                "created_at": row2[4],
                "updated_at": row2[5],
            }


def _dummy_key(org_id: str, name: str, scopes: list[str]) -> dict[str, Any]:
    raw = f"velu_test_{name}_{uuid.uuid4().hex}"
    return {
        "id": str(uuid.uuid4()),
        "org_id": org_id,
        "name": name,
        "scopes": scopes,
        "created_at": int(time.time()),
        "raw_key": raw,
        "masked_key": _mask_key(raw),
        "_mem": True,
    }


@router.get("/orgs", dependencies=[Depends(require_scopes({"admin:orgs:manage"}))])
def list_orgs(limit: int = Query(50, ge=1, le=500), q: str = Query("", max_length=120)):
    qn = (q or "").strip().lower()

    url = _db_url_optional()
    if not url and _env() in {"local", "test", "dev"}:
        items = list(_MEM_ORGS.values())
        if qn:
            items = [
                o
                for o in items
                if qn in (o.get("slug", "") or "")
                or qn in (o.get("name", "") or "").lower()
            ]
        items = sorted(items, key=lambda x: x.get("created_at", 0), reverse=True)[: int(limit)]
        return {"ok": True, "items": items}

    with closing(_pg_connect()) as conn:
        with conn:
            if qn:
                rows = conn.execute(
                    """
                    SELECT id::text, name, slug, plan, created_at, updated_at
                    FROM organizations
                    WHERE slug ILIKE %s OR name ILIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (f"%{qn}%", f"%{qn}%", int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id::text, name, slug, plan, created_at, updated_at
                    FROM organizations
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (int(limit),),
                ).fetchall()

    items: list[dict[str, Any]] = []
    for r in rows:
        items.append(
            {
                "id": r[0],
                "name": r[1],
                "slug": r[2],
                "plan": _norm_plan(r[3]),
                "created_at": r[4],
                "updated_at": r[5],
            }
        )
    return {"ok": True, "items": items}


@router.post("/orgs", dependencies=[Depends(require_scopes({"admin:orgs:manage"}))])
def create_org(body: OrgCreateIn, request: Request):
    _require_platform_admin(request)
    org = _ensure_org(body.slug, body.name, body.plan)
    return {"ok": True, "item": org}


@router.post("/orgs/{org_id}/plan", dependencies=[Depends(require_scopes({"admin:orgs:manage"}))])
def update_org_plan(org_id: str, body: OrgUpdatePlanIn, request: Request):
    _require_platform_admin(request)
    plan_n = _norm_plan(body.plan)

    url = _db_url_optional()
    if not url and _env() in {"local", "test", "dev"}:
        for k, o in list(_MEM_ORGS.items()):
            if str(o.get("id")) == str(org_id):
                o["plan"] = plan_n
                o["updated_at"] = int(time.time())
                _MEM_ORGS[k] = o
                return {"ok": True, "plan": plan_n}
        raise HTTPException(status_code=404, detail="not_found")

    with closing(_pg_connect()) as conn:
        with conn:
            cur = conn.execute(
                "UPDATE organizations SET plan=%s, updated_at=now() WHERE id=%s::uuid",
                (plan_n, org_id),
            )
            if cur.rowcount != 1:
                raise HTTPException(status_code=404, detail="not_found")
    return {"ok": True, "plan": plan_n}


@router.post("/orgs/bootstrap", dependencies=[Depends(require_scopes({"admin:orgs:manage"}))])
def bootstrap_org(body: OrgBootstrapIn, request: Request):
    _require_platform_admin(request)
    org = _ensure_org(body.slug, body.name, body.plan)
    project = _ensure_project(org["id"], name="default")


    url = _db_url_optional()
    if not url and (_env() in {"local", "test", "dev"} or _test_db_lookup_enabled()):
        viewer = _dummy_key(org_id=org["id"], name="viewer", scopes=["jobs:read"])
        builder = _dummy_key(org_id=org["id"], name="builder", scopes=["jobs:submit", "jobs:read"])
        admin = _dummy_key(
            org_id=org["id"],
            name="admin",
            scopes=["admin:api_keys:manage", "jobs:submit", "jobs:read"],
        )
    else:
        viewer = create_api_key(org_id=org["id"], name="viewer", scopes=["jobs:read"])
        builder = create_api_key(org_id=org["id"], name="builder", scopes=["jobs:submit", "jobs:read"])
        admin = create_api_key(
            org_id=org["id"],
            name="admin",
            scopes=["admin:api_keys:manage", "jobs:submit", "jobs:read"],
        )

        if isinstance(viewer, dict) and viewer.get("raw_key") and not viewer.get("masked_key"):
            viewer["masked_key"] = _mask_key(str(viewer.get("raw_key") or ""))
        if isinstance(builder, dict) and builder.get("raw_key") and not builder.get("masked_key"):
            builder["masked_key"] = _mask_key(str(builder.get("raw_key") or ""))
        if isinstance(admin, dict) and admin.get("raw_key") and not admin.get("masked_key"):
            admin["masked_key"] = _mask_key(str(admin.get("raw_key") or ""))

    keys: dict[str, Any] = {"viewer": viewer, "builder": builder, "admin": admin}

    if not _allow_raw_keys():
        keys = {k: _strip_raw_key(v) for k, v in keys.items()}

    return {"ok": True, "org": org, "project": project, "keys": keys}
