from __future__ import annotations

from typing import Any


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    idea = str(payload.get("idea") or "demo")
    module = str(payload.get("module") or "hello_mod")

    # Convert intake into user stories & NFRs
    stories = [
        {
            "as": "user",
            "i_want": "sign in",
            "so_that": "I can access my account",
        },
        {
            "as": "admin",
            "i_want": "manage users",
            "so_that": "I can administer the org",
        },
    ]

    ops = payload.get("ops")
    regions = ops.get("regions", []) if isinstance(ops, dict) else []

    nfr = {
        "availability_slo": "99.9%",
        "p95_latency_ms": 300,
        "regions": regions,
    }

    return {
        "ok": True,
        "agent": "requirements",
        "idea": idea,
        "module": module,
        "stories": stories,
        "nfr": nfr,
        "risks": [],
        "notes": [],
    }
