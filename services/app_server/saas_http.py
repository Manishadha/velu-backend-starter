from __future__ import annotations

from typing import Optional, Tuple

from fastapi import Header, HTTPException

from services.app_server.saas_registry import InMemorySaasRegistry
from services.app_server.schemas.saas import Workspace  # type: ignore

import logging

logger = logging.getLogger(__name__)


_registry: Optional[InMemorySaasRegistry] = None


def get_saas_registry() -> InMemorySaasRegistry:
    """
    Global, in-memory registry used by the app server.

    In tests, this function is monkeypatched to return a pre-populated
    InMemorySaasRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = InMemorySaasRegistry()
    return _registry


def _extract_token(raw_header: Optional[str]) -> Optional[str]:
    """
    Extract the raw token from an Authorization-like header.

    Examples:
      "Bearer velu_123"   -> "velu_123"
      "ApiKey velu_123"   -> "velu_123"
      "velu_123"          -> "velu_123"
      None / "" / "   "   -> None
    """
    if not raw_header:
        return None
    value = raw_header.strip()
    if not value:
        return None

    parts = value.split()
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:

        return parts[1]

    return None


def _resolve_http(
    registry: InMemorySaasRegistry,
    raw_header: Optional[str],
) -> Tuple[Optional[Workspace], Optional[object], Optional[object], Optional[str]]:
    """
    Minimal resolver for the HTTP layer.

    Returns (workspace, api_key, subscription, error_code)

    error_code is one of:
      - None               -> success
      - "missing_token"    -> no usable token provided
      - "invalid_token"    -> token does not map to a key/workspace
      - "workspace_inactive" -> workspace exists but is inactive
    """
    token = _extract_token(raw_header)
    if not token:
        return None, None, None, "missing_token"

    api_key = None

    keys_dict = getattr(registry, "_api_keys", None)
    if isinstance(keys_dict, dict):
        for k in keys_dict.values():
            prefix = getattr(k, "key_prefix", None)
            is_active = getattr(k, "is_active", True)
            if not prefix or not is_active:
                continue

            try:
                if token == prefix or token.startswith(prefix):
                    api_key = k
                    break
            except Exception:
                logger.debug(
                    "saas_http: failed while matching host to tenant, continuing",
                    exc_info=True,
                )
                continue

    if api_key is None:
        get_by_prefix = getattr(registry, "get_api_key_by_prefix", None)
        if callable(get_by_prefix):
            candidate = get_by_prefix(token)
            if candidate is not None:
                api_key = candidate

    if api_key is None:
        return None, None, None, "invalid_token"

    workspace_id = getattr(api_key, "workspace_id", None)
    if not isinstance(workspace_id, str):
        return None, api_key, None, "invalid_token"

    workspace = registry.get_workspace(workspace_id)
    if workspace is None:
        return None, api_key, None, "invalid_token"

    sub = registry.get_subscription_for_workspace(workspace.id)

    is_active = True
    ws_active_fn = getattr(registry, "workspace_is_active", None)
    if callable(ws_active_fn):
        is_active = bool(ws_active_fn(workspace.id))

    if not is_active:
        return workspace, api_key, sub, "workspace_inactive"

    return workspace, api_key, sub, None


async def get_current_workspace(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Workspace:
    """
    FastAPI dependency used by HTTP routes.

    Semantics (matching tests):

    - Valid token + active workspace:
        - /whoami with Authorization: "Bearer <token>" -> 200
        - /whoami with X-API-Key: "<token>"            -> 200
    - Missing / invalid token:
        -> 401
    - Inactive workspace:
        -> 403
    """

    registry = get_saas_registry()

    if x_api_key:
        header_value: Optional[str] = f"ApiKey {x_api_key.strip()}"
    else:
        header_value = authorization

    workspace, _key, _sub, err = _resolve_http(registry, header_value)

    if err is None and workspace is not None:
        return workspace

    if err in ("missing_token", "invalid_token"):
        raise HTTPException(status_code=401, detail=err)

    if err == "workspace_inactive":
        raise HTTPException(status_code=403, detail=err)

    raise HTTPException(status_code=401, detail=err or "unauthorized")
