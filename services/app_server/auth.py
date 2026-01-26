from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from httpx import request  # noqa: F401
import psycopg
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.app_server.models.api_key import hash_key as _canonical_hash_key

DEFAULT_LOCAL_API_KEYS = {
    "local:secret123",
    "local: secret123",
    "dev",
}


def _env() -> str:
    return (os.getenv("ENV") or "local").strip().lower()


def _truthy(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _disabled_keys() -> set[str]:
    raw = (os.getenv("DISABLED_API_KEYS") or "").strip()
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


def _min_key_len() -> int:
    raw = (os.getenv("MIN_API_KEY_LEN") or "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except Exception:
            return 0
    if _env() in {"local", "test"}:
        return 0
    return 24


def _extract_api_key(request: Request) -> str:  # noqa: F811
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    k = (request.headers.get("X-API-Key") or "").strip()
    if k:
        return k
    return ""


def key_id(token: str) -> str:
    token = (token or "").strip()
    if not token:
        return "anon"
    h = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
    return f"k_{h}"


@dataclass(frozen=True)
class KeyClaims:
    role: str
    tier: str
    token: str
    kid: str
    org_id: str | None = None
    scopes: list[str] | None = None
    actor_type: str = "api_key"
    actor_id: str | None = None


def _parse_api_keys(raw: str) -> dict[str, dict[str, str]]:
    raw = (raw or "").strip()
    if not raw:
        return {}

    if raw in DEFAULT_LOCAL_API_KEYS:
        return {}

    def norm_role(r: str) -> str:
        r = (r or "").strip().lower()
        return r or "admin"

    def norm_tier(t: str) -> str:
        t = (t or "").strip().lower()
        return t if t in {"base", "hero", "superhero"} else "superhero"

    out: dict[str, dict[str, str]] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue

        if ":" not in part:
            out[part] = {"role": "admin", "tier": "superhero"}
            continue

        segs = [s.strip() for s in part.split(":") if s.strip()]
        if not segs:
            continue

        token = segs[0]
        role = segs[1] if len(segs) >= 2 else "admin"
        tier = segs[2] if len(segs) >= 3 else "superhero"

        out[token] = {"role": norm_role(role), "tier": norm_tier(tier)}

    return out


def _db_url() -> str | None:
    from services.api.db import database_url

    url = (database_url() or "").strip()
    if not url:
        return None

    low = url.lower()
    if low.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url.split("://", 1)[1]
    if low.startswith("postgres://"):
        url = "postgresql://" + url.split("://", 1)[1]
    return url


def using_postgres_api_keys() -> bool:
    v = (os.getenv("VELU_API_KEYS_BACKEND") or "").strip().lower()
    if v:
        return v == "postgres"
    url = _db_url() or ""
    return url.lower().startswith("postgres")


def _hash_key(raw: str) -> str:
    return _canonical_hash_key(raw)


def _role_from_scopes(scopes: list[str] | None) -> str:
    s = set(scopes or [])
    if "admin:api_keys:manage" in s or "admin:orgs:manage" in s or "admin:billing:write" in s:
        return "admin"
    if "jobs:submit" in s:
        return "builder"
    return "viewer"


def _tier_from_plan(plan: str | None) -> str:
    p = (plan or "").strip().lower()
    if p in {"starter", "base", "basic"}:
        return "base"
    if p in {"hero", "standard"}:
        return "hero"
    if p in {"superhero", "premium"}:
        return "superhero"
    return "base"




@lru_cache(maxsize=2048)
def _db_lookup_org_plan(org_id: str) -> str | None:
    if not using_postgres_api_keys():
        return None
    url = _db_url()
    if not url:
        return None
    oid = (org_id or "").strip()
    if not oid:
        return None
    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT plan FROM organizations WHERE id=%s::uuid LIMIT 1;",
                    (oid,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return str(row[0] or "").strip() or None
    except Exception:
        return None


def _db_lookup_api_key(raw_token: str) -> dict[str, Any] | None:
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("VELU_TEST_DB_LOOKUP") == "0":
        return None

    if not using_postgres_api_keys():
        return None
    url = _db_url()
    if not url:
        return None

    hashed = _hash_key(raw_token)

    try:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                # Enforce: not revoked, not expired (expires_at NULL means "never expires")
                cur.execute(
                    """
                    SELECT id::text, org_id::text, scopes, last_used_at
                      FROM api_keys
                     WHERE revoked_at IS NULL
                       AND (expires_at IS NULL OR expires_at > now())
                       AND hashed_key = %s
                     LIMIT 1;
                    """,
                    (hashed,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                key_id_db, org_id, scopes, last_used_at = row

                # Update last_used_at, but avoid writing on every request.
                # Default: only update if older than 5 minutes (or NULL).
                try:
                    update_every_sec = int((os.getenv("API_KEY_TOUCH_SEC") or "").strip() or 300)
                except Exception:
                    update_every_sec = 300

                do_touch = True
                if last_used_at and update_every_sec > 0:
                    # last_used_at is a datetime from psycopg; use epoch comparison safely
                    import datetime as _dt

                    now = _dt.datetime.now(_dt.timezone.utc)
                    try:
                        age = (now - last_used_at).total_seconds()
                        do_touch = age >= float(update_every_sec)
                    except Exception:
                        do_touch = True

                if do_touch:
                    cur.execute(
                        "UPDATE api_keys SET last_used_at = now() WHERE id = %s::uuid",
                        (key_id_db,),
                    )
                    conn.commit()

                return {"id": str(key_id_db), "kid": str(key_id_db), "org_id": str(org_id), "scopes": [str(s) for s in (scopes or [])]}

    except Exception:
        return None



def claims_from_request(request: Request) -> dict[str, Any] | None:  # noqa: F811
    token = _extract_api_key(request)
    if not token:
        return None

    # Always allow explicitly-configured platform/admin keys (still block if disabled)
    admin_key = (os.getenv("VELU_ADMIN_KEY") or "").strip()
    test_admin_key = (os.getenv("TEST_PLATFORM_ADMIN_KEY") or "").strip()

    if token in _disabled_keys():
        return None

    if (admin_key and token == admin_key) or (test_admin_key and token == test_admin_key):
        return {
            "role": "admin",
            "tier": "superhero",
            "_token": token,
            "kid": str(key_id(token)),
            "is_platform_admin": True,
            "org_id": None,
            "scopes": [
                "admin:orgs:manage",
                "admin:api_keys:manage",
                "admin:billing:write",
                "jobs:submit",
                "jobs:read",
            ],
            "actor_type": "platform_admin_key",
            "actor_id": "platform_admin",
        }

    # Only enforce min length for non-platform keys
    min_len = _min_key_len()
    if min_len and len(token) < min_len:
        return None

    db_hit = _db_lookup_api_key(token)
    if db_hit:
        org_id = db_hit.get("org_id")
        scopes = db_hit.get("scopes") or []
        plan = _db_lookup_org_plan(str(org_id)) if org_id else None
        tier = _tier_from_plan(plan)
        role = _role_from_scopes(scopes)
        return {
            "role": role,
            "tier": tier,
            "_token": token,
            "kid": str(key_id(token)),
            "org_id": org_id,
            "scopes": scopes,
            "actor_type": "api_key",
            "actor_id": db_hit.get("id"),
        }

    keys = _parse_api_keys(os.getenv("API_KEYS", ""))
    if not keys:
        return {"role": "admin", "tier": "superhero", "_token": token, "kid": str(key_id(token))}


    info = keys.get(token)
    if not info:
        return None

    return {
        "role": info.get("role", "admin"),
        "tier": info.get("tier", "superhero"),
        "_token": token,
        "kid": str(key_id(token)),
    }



def _need_auth(path: str, method: str) -> bool:
    return method.upper() == "POST" and path == "/tasks"


class ApiKeyRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: F811
        if request.method == "OPTIONS" or request.url.path in ("/health", "/ready"):
            return await call_next(request)

        token = _extract_api_key(request)
        request.state.kid = str(key_id(token)) if token else "anon"


        claims = claims_from_request(request) or {}
        request.state.claims = claims


        if not _need_auth(request.url.path, request.method):
            return await call_next(request)

        if using_postgres_api_keys():
            if claims and (claims.get("org_id") or claims.get("is_platform_admin")):
                return await call_next(request)
            return JSONResponse({"detail": "missing or invalid api key"}, status_code=401)


        raw = (os.getenv("API_KEYS") or "").strip()
        keys = _parse_api_keys(raw)

        if not keys:
            return await call_next(request)

        if not token or token in _disabled_keys():
            return JSONResponse({"detail": "missing or invalid api key"}, status_code=401)

        min_len = _min_key_len()
        if min_len and len(token) < min_len:
            return JSONResponse({"detail": "missing or invalid api key"}, status_code=401)

        if token not in keys:
            return JSONResponse({"detail": "missing or invalid api key"}, status_code=401)

        return await call_next(request)
