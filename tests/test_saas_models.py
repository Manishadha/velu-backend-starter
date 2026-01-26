from __future__ import annotations

from datetime import datetime, timedelta, timezone  # noqa: F401


from services.app_server.schemas.saas import (  # type: ignore
    ApiKey,
    PlanName,  # noqa: F401
    Subscription,
    SubscriptionStatus,  # noqa: F401
    User,
    Workspace,
)


def test_workspace_defaults() -> None:
    ws = Workspace(
        id="ws_1",
        name="My Workspace",
        slug="my_workspace",
        owner_user_id="user_1",
    )
    assert ws.plan == "free"
    assert ws.is_active is True
    assert ws.slug == "my_workspace"


def test_user_defaults_and_workspaces() -> None:
    user = User(
        id="user_1",
        email="user@example.com",
        name="User One",
    )
    assert user.is_active is True
    assert user.workspace_ids == []
    assert user.primary_workspace_id is None

    user.workspace_ids.append("ws_1")
    assert "ws_1" in user.workspace_ids


def test_api_key_defaults() -> None:
    key = ApiKey(
        id="key_1",
        workspace_id="ws_1",
        name="Main Key",
        key_prefix="velu_",
        hashed_secret="hashed_value",
    )
    assert key.is_active is True
    assert key.scopes == ["generation"]
    assert key.last_used_at is None


def test_subscription_defaults_and_status() -> None:
    sub = Subscription(
        id="sub_1",
        workspace_id="ws_1",
    )
    assert sub.plan == "free"
    assert sub.status == "trialing"
    assert sub.seats == 1

    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    sub.valid_until = tomorrow
    assert isinstance(sub.valid_until, datetime)

    assert isinstance(sub.plan, str)
    assert isinstance(sub.status, str)
    assert sub.plan in {"free", "pro", "enterprise"}
    assert sub.status in {"trialing", "active", "past_due", "canceled"}
