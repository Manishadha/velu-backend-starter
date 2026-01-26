# services/agents/sleep.py
from __future__ import annotations

import time
from typing import Any, Dict, Mapping


def handle(payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    payload = dict(payload or {})
    seconds = int(payload.get("seconds") or 15)
    seconds = max(1, min(seconds, 600))
    time.sleep(seconds)
    return {"ok": True, "slept_seconds": seconds}
