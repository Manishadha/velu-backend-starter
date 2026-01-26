from __future__ import annotations

from typing import Optional, Tuple

from services.app_server.saas_registry import InMemorySaasRegistry
from services.app_server.schemas.saas import (  # type: ignore
    ApiKey,
    Subscription,
    Workspace,
    PlanName,  # noqa: F401
)


def _extract_token(raw_header: Optional[str]) -> Optional[str]:
    """
    Extracts the raw token from an Authorization-style header.

    Examples:
    - "Bearer velu_123" -> "velu_123"
    - "ApiKey velu_123" -> "velu_123"
    - "velu_123"        -> "velu_123"
    """
    if not raw_header:
        return None
    header = raw_header.strip()
    if not header:
        return None

    parts = header.split()
    if len(parts) >= 2:
        return parts[-1]

    return header


def _lookup_api_key(
    registry: InMemorySaasRegistry,
    token: str,
) -> Optional[ApiKey]:
    """
    Resolve an ApiKey from a token string.

    First we try exact match against key_prefix.
    If that fails, we try a simple prefix split on "_" or "-".
    """

    key = registry.get_api_key_by_prefix(token)
    if key is not None:
        return key

    if "_" in token:
        prefix = token.split("_", 1)[0]
        key = registry.get_api_key_by_prefix(prefix)
        if key is not None:
            return key

    if "-" in token:
        prefix = token.split("-", 1)[0]
        key = registry.get_api_key_by_prefix(prefix)
        if key is not None:
            return key

    return None


def resolve_workspace_from_header(
    registry: InMemorySaasRegistry,
    auth_header: Optional[str],
) -> Tuple[Optional[Workspace], Optional[ApiKey], Optional[Subscription], Optional[str]]:
    """
    Contract expected by the tests:

        ws, key, sub, err = resolve_workspace_from_header(registry, header)

    Semantics:
      - Success:
          (workspace, api_key, subscription_or_None, None)
      - Missing header/token:
          (None, None, None, "missing_token")
      - Invalid token (no matching API key/workspace):
          (None, None, None, "invalid_token")
      - Inactive workspace:
          (workspace, api_key, subscription_or_None, "workspace_inactive")
    """
    token = _extract_token(auth_header)
    if not token:
        return None, None, None, "missing_token"

    api_key = _lookup_api_key(registry, token)
    if api_key is None:
        return None, None, None, "invalid_token"

    workspace = registry.get_workspace(api_key.workspace_id)
    if workspace is None:

        return None, None, None, "invalid_token"

    subscription = registry.get_subscription_for_workspace(workspace.id)

    if not registry.workspace_is_active(workspace.id):
        return workspace, api_key, subscription, "workspace_inactive"

    return workspace, api_key, subscription, None
