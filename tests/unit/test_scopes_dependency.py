from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from services.app_server.dependencies.scopes import require_scopes


def _make_request_with_claims(claims: dict) -> Request:
    scope = {"type": "http", "method": "POST", "path": "/tasks", "headers": []}
    req = Request(scope)
    req.state.claims = claims
    return req


@pytest.mark.asyncio
async def test_api_key_missing_scope_denied() -> None:
    dep = require_scopes({"jobs:submit"})
    req = _make_request_with_claims({"actor_type": "api_key", "org_id": "org_1", "scopes": []})
    with pytest.raises(HTTPException) as e:
        await dep(req)
    assert e.value.status_code == 403


@pytest.mark.asyncio
async def test_api_key_with_scope_allowed() -> None:
    dep = require_scopes({"jobs:submit"})
    req = _make_request_with_claims(
        {"actor_type": "api_key", "org_id": "org_1", "scopes": ["jobs:submit"]}
    )
    await dep(req)


@pytest.mark.asyncio
async def test_legacy_env_key_not_scope_enforced() -> None:
    dep = require_scopes({"jobs:submit"})
    req = _make_request_with_claims({"actor_type": "api_key", "scopes": []})
    await dep(req)
