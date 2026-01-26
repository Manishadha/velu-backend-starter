from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "agent": "postdeploy_checks",
        "smoke": ["GET /ready", "GET /metrics"],
    }
