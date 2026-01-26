from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.app_server.schemas.saas import (  # type: ignore
    ApiKey,
    Subscription,
    User,
    Workspace,
)
from services.app_server.saas_registry import InMemorySaasRegistry  # type: ignore


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


def _demo_api_key() -> ApiKey:
    return ApiKey(
        id="key_1",
        workspace_id="ws_1",
        name="Main Key",
        key_prefix="velu_",
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


def _demo_subscription_canceled() -> Subscription:
    return Subscription(
        id="sub_2",
        workspace_id="ws_1",
        plan="pro",
        status="canceled",
        seats=3,
        valid_until=datetime.now(timezone.utc) - timedelta(days=1),
    )


def test_add_and_get_workspace_and_user() -> None:
    reg = InMemorySaasRegistry()
    ws = _demo_workspace()
    user = _demo_user()

    reg.add_workspace(ws)
    reg.add_user(user)

    got_ws = reg.get_workspace("ws_1")
    got_user = reg.get_user("user_1")

    assert got_ws is not None
    assert got_ws.id == "ws_1"
    assert got_user is not None
    assert got_user.email == "user@example.com"


def test_api_keys_for_workspace_and_lookup_by_prefix() -> None:
    reg = InMemorySaasRegistry()
    ws = _demo_workspace()
    reg.add_workspace(ws)

    key = _demo_api_key()
    reg.add_api_key(key)

    keys = reg.list_api_keys_for_workspace("ws_1")
    assert len(keys) == 1
    assert keys[0].id == "key_1"

    found = reg.get_api_key_by_prefix("velu_")
    assert found is not None
    assert found.id == "key_1"

    key.is_active = False
    keys_after = reg.list_api_keys_for_workspace("ws_1")
    assert keys_after == []
    assert reg.get_api_key_by_prefix("velu_") is None


def test_workspace_plan_uses_subscription_if_present() -> None:
    reg = InMemorySaasRegistry()
    ws = _demo_workspace()
    reg.add_workspace(ws)

    plan_without_sub = reg.workspace_plan("ws_1")
    assert plan_without_sub == "pro"

    sub = _demo_subscription_active()
    reg.add_subscription(sub)

    plan_with_sub = reg.workspace_plan("ws_1")
    assert plan_with_sub == "pro"


def test_workspace_active_status_with_subscription() -> None:
    reg = InMemorySaasRegistry()
    ws = _demo_workspace()
    reg.add_workspace(ws)

    assert reg.workspace_is_active("ws_1") is True

    sub_active = _demo_subscription_active()
    reg.add_subscription(sub_active)
    assert reg.workspace_is_active("ws_1") is True

    reg = InMemorySaasRegistry()
    reg.add_workspace(ws)
    sub_canceled = _demo_subscription_canceled()
    reg.add_subscription(sub_canceled)
    assert reg.workspace_is_active("ws_1") is False
