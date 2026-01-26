from __future__ import annotations

import os
from typing import Iterable, Set

from fastapi import HTTPException, status
from starlette.requests import Request

from services.app_server.auth import claims_from_request, using_postgres_api_keys


def _truthy(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def _enforce_scopes_env() -> bool:
    return _truthy("ENFORCE_SCOPES") or _truthy("VELU_ENFORCE_SCOPES")


def require_scopes(required: Iterable[str]):
    required_set: Set[str] = {str(s).strip() for s in (required or []) if str(s).strip()}

    async def _dep(request: Request) -> None:
        c = getattr(request.state, "claims", None)
        if not isinstance(c, dict) or c is None:
            c = claims_from_request(request) or {}
            request.state.claims = c

        # ---- Postgres API-key mode: accept platform admin keys too ----
        if using_postgres_api_keys():
            if not c or not (c.get("org_id") or c.get("is_platform_admin")):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="missing or invalid api key",
                )
            scopes = set(c.get("scopes") or [])
            if not required_set.issubset(scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="missing required scope",
                )
            return


        # ---- Env-key / local mode ----
        enforce = _enforce_scopes_env() or bool(c.get("org_id"))
        if not enforce:
            return

        if not c:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid api key",
            )

        scopes = set(c.get("scopes") or [])
        if not required_set.issubset(scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="missing required scope",
            )

    return _dep
