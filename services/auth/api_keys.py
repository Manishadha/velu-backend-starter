from __future__ import annotations

import secrets
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg

from services.api.db import database_url
from services.app_server.models.api_key import hash_key, mask_key


def _pg_url() -> str:
    raw = (database_url() or "").strip()
    if not raw:
        raise RuntimeError("DATABASE_URL is required")
    if raw.lower().startswith("postgresql+psycopg://"):
        return "postgresql://" + raw.split("://", 1)[1]
    if raw.lower().startswith("postgres://"):
        return "postgresql://" + raw.split("://", 1)[1]
    return raw


def _pg_connect() -> psycopg.Connection:
    return psycopg.connect(_pg_url(), autocommit=False)


def generate_raw_key() -> str:
    return "velu_" + secrets.token_urlsafe(32)


def _normalize_scopes(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return sorted({str(x).strip() for x in v if str(x).strip()})
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("{") and s.endswith("}"):
            s = s[1:-1]
        if not s:
            return []
        return sorted({p.strip() for p in s.split(",") if p.strip()})
    return [str(v).strip()] if str(v).strip() else []


def _expires_at_from_ttl(ttl_days: int | None) -> datetime | None:
    if ttl_days is None:
        return None
    try:
        days = int(ttl_days)
    except Exception:
        return None
    if days <= 0:
        return None
    return datetime.now(timezone.utc) + timedelta(days=days)


def create_api_key(org_id: str, name: str, scopes: list[str], ttl_days: int | None = None) -> dict[str, Any]:
    raw = generate_raw_key()
    hashed = hash_key(raw)
    scopes_norm = _normalize_scopes(scopes)
    expires_at = _expires_at_from_ttl(ttl_days)

    with closing(_pg_connect()) as conn:
        with conn:
            row = conn.execute(
                """
                INSERT INTO api_keys (org_id, name, hashed_key, scopes, revoked_at, expires_at)
                VALUES (%s::uuid, %s, %s, %s::text[], NULL, %s)
                RETURNING id::text, org_id::text, name, scopes, created_at, last_used_at, revoked_at, expires_at
                """,
                (org_id, name, hashed, scopes_norm, expires_at),
            ).fetchone()

    return {
        "id": row[0],
        "org_id": row[1],
        "name": row[2],
        "scopes": _normalize_scopes(row[3]),
        "created_at": row[4],
        "last_used_at": row[5],
        "revoked_at": row[6],
        "expires_at": row[7],
        "raw_key": raw,
        "masked_key": mask_key(raw),
    }


def list_api_keys(org_id: str) -> list[dict[str, Any]]:
    with closing(_pg_connect()) as conn:
        with conn:
            rows = conn.execute(
                """
                SELECT id::text, org_id::text, name, scopes, created_at, last_used_at, revoked_at, expires_at
                  FROM api_keys
                 WHERE org_id = %s::uuid
                 ORDER BY created_at DESC
                """,
                (org_id,),
            ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "org_id": r[1],
                "name": r[2],
                "scopes": _normalize_scopes(r[3]),
                "created_at": r[4],
                "last_used_at": r[5],
                "revoked_at": r[6],
                "expires_at": r[7],
            }
        )
    return out


def revoke_api_key(org_id: str, key_id: str) -> None:
    with closing(_pg_connect()) as conn:
        with conn:
            cur = conn.execute(
                """
                UPDATE api_keys
                   SET revoked_at = now()
                 WHERE id = %s::uuid
                   AND org_id = %s::uuid
                   AND revoked_at IS NULL
                """,
                (key_id, org_id),
            )
            if cur.rowcount == 1:
                return
            exists = conn.execute(
                """
                SELECT 1
                  FROM api_keys
                 WHERE id = %s::uuid
                   AND org_id = %s::uuid
                """,
                (key_id, org_id),
            ).fetchone()
            if exists:
                return
            raise KeyError("not_found")


def rotate_api_key(org_id: str, key_id: str, ttl_days: int | None = None) -> dict[str, Any]:
    raw = generate_raw_key()
    hashed = hash_key(raw)
    expires_at = _expires_at_from_ttl(ttl_days)

    with closing(_pg_connect()) as conn:
        with conn:
            row = conn.execute(
                """
                UPDATE api_keys
                   SET hashed_key = %s,
                       revoked_at = NULL,
                       expires_at = COALESCE(%s, expires_at)
                 WHERE id = %s::uuid
                   AND org_id = %s::uuid
                RETURNING id::text, org_id::text, name, scopes, created_at, last_used_at, revoked_at, expires_at
                """,
                (hashed, expires_at, key_id, org_id),
            ).fetchone()
            if not row:
                raise KeyError("not_found")

    return {
        "id": row[0],
        "org_id": row[1],
        "name": row[2],
        "scopes": _normalize_scopes(row[3]),
        "created_at": row[4],
        "last_used_at": row[5],
        "revoked_at": row[6],
        "expires_at": row[7],
        "raw_key": raw,
        "masked_key": mask_key(raw),
    }
