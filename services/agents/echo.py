from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Echo agent: returns payload unchanged."""
    return {"ok": True, "agent": "echo", "data": payload or {}}
