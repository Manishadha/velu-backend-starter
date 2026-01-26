from __future__ import annotations

from typing import Any

from orchestrator.agent_contracts import TaskResult
from services.agents import planner


def handle(task: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any]
    if isinstance(task, dict) and "payload" in task:
        payload = task.get("payload") or {}
    elif isinstance(task, dict):
        payload = task
    else:
        payload = {}

    base = planner.handle(payload)
    ok = bool(base.get("ok", True))
    plan = base.get("plan")

    result = TaskResult(
        status="ok" if ok else "error",
        data={
            "agent": "planning",
            "plan": plan,
            "raw": base,
        },
    ).__dict__

    result.setdefault("ok", ok)
    if plan is not None:
        result.setdefault("plan", plan)

    return result
