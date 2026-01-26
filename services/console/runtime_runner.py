from __future__ import annotations

from typing import Any, Dict, List

from services.agents import runtime_planner


def plan_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience helper for the console / CLI:

    - calls runtime_planner.handle(payload)
    - validates the result
    - returns only the 'runtime' dict (RuntimeDescriptor as plain data)
    """
    res = runtime_planner.handle(payload)
    if not res.get("ok"):
        raise RuntimeError("runtime_planner failed")
    runtime = res.get("runtime")
    if not isinstance(runtime, dict):
        raise RuntimeError("runtime_planner returned invalid runtime payload")
    return runtime


def list_service_ids(runtime: Dict[str, Any]) -> List[str]:
    """
    Return the list of service ids from a runtime descriptor dict.
    """
    services = runtime.get("services") or []
    ids: List[str] = []
    for s in services:
        if isinstance(s, dict):
            sid = s.get("id")
            if isinstance(sid, str):
                ids.append(sid)
    return ids


def find_service(runtime: Dict[str, Any], service_id: str) -> Dict[str, Any] | None:
    """
    Look up a single service by id inside the runtime descriptor.
    """
    services = runtime.get("services") or []
    for s in services:
        if isinstance(s, dict) and s.get("id") == service_id:
            return s
    return None
