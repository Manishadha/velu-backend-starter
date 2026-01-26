from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RuntimeProcess(BaseModel):
    id: str
    kind: Literal["api", "web", "worker", "db", "support"]
    command: List[str]
    cwd: Optional[str] = None
    env: Dict[str, str] = Field(default_factory=dict)


class RuntimeDescriptor(BaseModel):
    project_id: str
    services: List[RuntimeProcess]
