from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class Account(BaseModel):
    id: UUID
    tenant_id: UUID | None
    created_at: datetime


class User(BaseModel):
    id: UUID
    tenant_id: UUID | None
    created_at: datetime
