from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request


@dataclass(frozen=True)
class AuthContext:
    org_id: str
    actor_type: str  # "api_key" | "user" | "system"
    actor_id: str
    scopes: list[str]


def set_auth(request: Request, ctx: AuthContext) -> None:
    request.state.auth = ctx


def get_auth(request: Request) -> Optional[AuthContext]:
    return getattr(request.state, "auth", None)
