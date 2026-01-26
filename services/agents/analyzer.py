from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """Toy analyzer: counts keys/values and echoes back."""
    payload = payload or {}
    keys = list(payload.keys())
    return {
        "ok": True,
        "agent": "analyzer",
        "result": {
            "key_count": len(keys),
            "keys": keys,
            "summary": "analysis complete",
        },
    }
