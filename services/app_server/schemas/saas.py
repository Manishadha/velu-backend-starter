from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


PlanName = Literal["free", "pro", "enterprise"]
SubscriptionStatus = Literal["trialing", "active", "past_due", "canceled"]


class Workspace(BaseModel):
    id: str
    name: str
    slug: str
    owner_user_id: str
    plan: PlanName = "free"
    is_active: bool = True
    created_at: datetime | None = None


class User(BaseModel):
    id: str
    email: str
    name: str
    primary_workspace_id: str | None = None
    workspace_ids: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime | None = None


class ApiKey(BaseModel):
    id: str
    workspace_id: str
    name: str
    key_prefix: str
    hashed_secret: str
    scopes: List[str] = Field(default_factory=lambda: ["generation"])
    is_active: bool = True
    created_at: datetime | None = None
    last_used_at: datetime | None = None


class Subscription(BaseModel):
    id: str
    workspace_id: str
    plan: PlanName = "free"
    status: SubscriptionStatus = "trialing"
    seats: int = 1
    valid_until: datetime | None = None
    created_at: datetime | None = None
