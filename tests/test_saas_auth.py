from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.app_server.saas_auth import resolve_workspace_from_header  # type: ignore
from services.app_server.saas_registry import InMemorySaasRegistry  # type: ignore
from services.app_server.schemas.saas import ApiKey, Subscription, User, Workspace  # type: ignore


def _demo_workspace() -> Workspace:
    return Workspace(
        id="ws_1",
        name="Demo Workspace",
        slug="demo_workspace",
        owner_user_id="user_1",
        plan="pro",
    )


def _demo_user() -> User:
    return User(
        id="user_1",
        email="user@example.com",
        name="User One",
        primary_workspace_id="ws_1",
        workspace_ids=["ws_1"],
    )


def _demo_api_key(prefix: str = "velu_123") -> ApiKey:
    return ApiKey(
        id="key_1",
        workspace_id="ws_1",
        name="Main Key",
        key_prefix=prefix,
        hashed_secret="hashed_value",
    )


def _demo_subscription_active() -> Subscription:
    return Subscription(
        id="sub_1",
        workspace_id="ws_1",
        plan="pro",
        status="active",
        seats=3,
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
    )


def _demo_subscription_inactive() -> Subscription:
    return Subscription(
        id="sub_2",
        workspace_id="ws_1",
        plan="pro",
        status="canceled",
        seats=3,
        valid_until=datetime.now(timezone.utc) - timedelta(days=1),
    )


def _build_registry(active_sub: bool = True, active_workspace: bool = True) -> InMemorySaasRegistry:
    reg = InMemorySaasRegistry()
    ws = _demo_workspace()
    if not active_workspace:
        ws.is_active = False
    reg.add_workspace(ws)

    user = _demo_user()
    reg.add_user(user)

    key = _demo_api_key()
    reg.add_api_key(key)

    if active_sub:
        sub = _demo_subscription_active()
    else:
        sub = _demo_subscription_inactive()
    reg.add_subscription(sub)

    return reg


def test_resolve_valid_bearer_header() -> None:
    reg = _build_registry(active_sub=True, active_workspace=True)

    header = "Bearer velu_123"
    ws, key, sub, err = resolve_workspace_from_header(reg, header)

    assert err is None
    assert ws is not None
    assert ws.id == "ws_1"
    assert key is not None
    assert key.id == "key_1"
    assert sub is not None
    assert sub.status == "active"


def test_missing_header_returns_missing_token() -> None:
    reg = _build_registry()

    ws, key, sub, err = resolve_workspace_from_header(reg, None)

    assert ws is None
    assert key is None
    assert sub is None
    assert err == "missing_token"


def test_invalid_token_returns_invalid_token() -> None:
    reg = _build_registry()

    header = "Bearer unknown_prefix"
    ws, key, sub, err = resolve_workspace_from_header(reg, header)

    assert ws is None
    assert key is None
    assert sub is None
    assert err == "invalid_token"


def test_inactive_workspace_returns_workspace_inactive() -> None:
    reg = _build_registry(active_sub=True, active_workspace=False)

    header = "ApiKey velu_123"
    ws, key, sub, err = resolve_workspace_from_header(reg, header)

    assert ws is not None
    assert key is not None
    assert err == "workspace_inactive"
