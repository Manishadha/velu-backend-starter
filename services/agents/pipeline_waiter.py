from __future__ import annotations

import os
import time
from typing import Any, Dict, Mapping

from services.queue import get_queue


def _as_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _as_job_id(v: Any) -> str | int | None:
    if v is None:
        return None

    if isinstance(v, int):
        return v

    s = str(v).strip()
    if not s:
        return None

    if "-" in s:
        return s

    try:
        return int(s)
    except Exception:
        return s


def _extract_stage_jobs(payload: Mapping[str, Any]) -> Dict[str, str | int]:
    sj = payload.get("stage_jobs")
    out: Dict[str, str | int] = {}

    if isinstance(sj, dict):
        for k, v in sj.items():
            name = str(k).strip()
            jid = _as_job_id(v)
            if name and jid is not None:
                out[name] = jid
        return out

    stages = payload.get("stages")
    if isinstance(stages, list):
        for item in stages:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            jid = _as_job_id(item.get("job_id"))
            if name and jid is not None:
                out[name] = jid

    return out


def _ok_of(res: Any) -> bool:
    return isinstance(res, dict) and bool(res.get("ok"))


def handle(task_or_payload: Any, payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    if isinstance(task_or_payload, dict) and payload is None:
        payload = task_or_payload
    payload = dict(payload or {})

    q = get_queue()

    stage_jobs = _extract_stage_jobs(payload)
    if not stage_jobs:
        return {"ok": False, "agent": "pipeline_waiter", "error": "missing stage_jobs"}

    gates_in = payload.get("gates")
    gates: Dict[str, Any] = dict(gates_in) if isinstance(gates_in, dict) else {}

    timeout_s = _as_float(os.getenv("PIPELINE_WAITER_TIMEOUT", "300"), 300.0)
    interval_s = _as_float(os.getenv("PIPELINE_WAITER_INTERVAL", "0.25"), 0.25)
    deadline = time.time() + max(1.0, timeout_s)

    statuses: Dict[str, Any] = {}
    results: Dict[str, Any] = {}

    while True:
        all_done = True

        for name, jid in stage_jobs.items():
            rec = q.get(jid)
            if not isinstance(rec, dict):
                all_done = False
                continue

            st = rec.get("status")
            statuses[name] = st

            if st != "done":
                all_done = False
                continue

            results[name] = rec.get("result")

        if all_done:
            break

        if time.time() >= deadline:
            return {
                "ok": False,
                "agent": "pipeline_waiter",
                "error": "timeout",
                "stage_jobs": stage_jobs,
                "statuses": statuses,
                "results": results,
                "payload": payload,
            }

        time.sleep(max(0.05, interval_s))

    if "unit_tests" in gates:
        gates["unit_tests"] = "pass" if _ok_of(results.get("test")) else "fail"
    if "build" in gates:
        gates["build"] = "pass" if _ok_of(results.get("packager")) else "fail"
    if "security" in gates:
        gates["security"] = "pass" if _ok_of(results.get("security_scan")) else "fail"

    out: Dict[str, Any] = {
        "ok": True,
        "agent": "pipeline_waiter",
        "pipeline_name": payload.get("pipeline_name"),
        "stage_jobs": stage_jobs,
        "gates": gates,
        "statuses": statuses,
        "results": results,
        "payload": payload,
    }

    pack = results.get("packager")
    if isinstance(pack, dict):
        ap = pack.get("artifact_path")
        if isinstance(ap, str) and ap.strip():
            out["artifact_path"] = ap.strip()

    return out
