from __future__ import annotations

from typing import Dict, List, Optional

from services.app_server.schemas.saas import (  # type: ignore
    ApiKey,
    PlanName,
    Subscription,
    User,
    Workspace,
)


class InMemorySaasRegistry:
    def __init__(self) -> None:
        self._workspaces: Dict[str, Workspace] = {}
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, ApiKey] = {}
        self._subscriptions: Dict[str, Subscription] = {}

    def add_workspace(self, ws: Workspace) -> None:
        self._workspaces[ws.id] = ws

    def add_user(self, user: User) -> None:
        self._users[user.id] = user

    def add_api_key(self, key: ApiKey) -> None:
        self._api_keys[key.id] = key

    def add_subscription(self, sub: Subscription) -> None:
        self._subscriptions[sub.id] = sub

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        return self._workspaces.get(workspace_id)

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_api_key_by_prefix(self, key_prefix: str) -> Optional[ApiKey]:
        for key in self._api_keys.values():
            if key.key_prefix == key_prefix and key.is_active:
                return key
        return None

    def list_api_keys_for_workspace(self, workspace_id: str) -> List[ApiKey]:
        return [
            k for k in self._api_keys.values() if k.workspace_id == workspace_id and k.is_active
        ]

    def get_workspace_by_token(self, token: str) -> Optional[Workspace]:
        """
        Resolve a workspace object from a full API token string.

        This is used by saas_auth.resolve_workspace_from_header.
        It scans the in-memory API keys and matches against common token
        attribute names so it stays compatible with the tests.
        """
        # Walk through all stored API keys
        for api_key in self._api_keys.values():
            # Skip inactive keys if the flag exists
            if getattr(api_key, "is_active", True) is False:
                continue

            # Try several common attribute names for the actual token string
            candidate_attrs = ("token", "value", "secret", "raw", "full_key", "key")
            actual_token = None
            for attr in candidate_attrs:
                val = getattr(api_key, attr, None)
                if isinstance(val, str):
                    actual_token = val
                    break

            if actual_token != token:
                continue

            # We have a matching token – now resolve the workspace
            ws_id = getattr(api_key, "workspace_id", None)
            if ws_id is None:
                ws_id = getattr(api_key, "workspace", None)

            if ws_id is None:
                return None

            # If ws_id is already a Workspace object, return it directly
            if isinstance(ws_id, Workspace):
                return ws_id

            # Otherwise, assume it's an ID and look it up in the registry
            if isinstance(ws_id, str):
                return self._workspaces.get(ws_id)

            return None

        # No matching token found
        return None

    def get_subscription_for_workspace(self, workspace_id: str) -> Optional[Subscription]:
        for sub in self._subscriptions.values():
            if sub.workspace_id == workspace_id:
                return sub
        return None

    def workspace_plan(self, workspace_id: str) -> PlanName:
        sub = self.get_subscription_for_workspace(workspace_id)
        if sub is not None:
            return sub.plan
        ws = self._workspaces.get(workspace_id)
        if ws is not None:
            return ws.plan
        return "free"

    def workspace_is_active(self, workspace_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        if not ws.is_active:
            return False
        sub = self.get_subscription_for_workspace(workspace_id)
        if sub is None:
            return True
        if sub.status in ("active", "trialing"):
            return True
        return False
