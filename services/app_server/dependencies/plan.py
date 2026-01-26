from __future__ import annotations

import os
from contextlib import closing
from typing import Callable

import psycopg
from fastapi import HTTPException, Request, status


def _db_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL is required")
    if raw.lower().startswith("postgresql+psycopg://"):
        return "postgresql://" + raw.split("://", 1)[1]
    if raw.lower().startswith("postgres://"):
        return "postgresql://" + raw.split("://", 1)[1]
    return raw


def _pg_connect() -> psycopg.Connection:
    return psycopg.connect(_db_url(), autocommit=False)


def rank_plan(plan: str) -> int:
    p = (plan or "").strip().lower()
    if p == "superhero":
        return 30
    if p == "hero":
        return 20
    if p == "base":
        return 10
    return 0


def get_org_plan(org_id: str) -> str:
    oid = (org_id or "").strip()
    if not oid:
        return "base"
    with closing(_pg_connect()) as conn:
        with conn:
            row = conn.execute(
                "SELECT plan FROM organizations WHERE id=%s::uuid",
                (oid,),
            ).fetchone()
            if not row:
                return "base"
            return str(row[0] or "base").strip().lower()


def require_plan(min_plan: str) -> Callable[[Request], None]:
    min_plan_n = (min_plan or "").strip().lower() or "base"
    min_rank = rank_plan(min_plan_n)
    if min_rank <= 0:
        raise ValueError("invalid min_plan")

    async def _dep(request: Request) -> None:
        claims = getattr(request.state, "claims", None) or {}
        org_id = claims.get("org_id")
        if not org_id:
            return
        plan = get_org_plan(str(org_id))
        if rank_plan(plan) < min_rank:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="upgrade required")

    return _dep
