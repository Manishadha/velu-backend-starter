from __future__ import annotations

import json
import sqlite3
from typing import Any

from pathlib import Path
import os

def _default_db() -> str:
    # Docker typically mounts /data
    if Path("/data/jobs.db").exists():
        return "/data/jobs.db"
    # Local default matches services.queue.jobs_sqlite default
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "data" / "jobs.db")

DB = (os.getenv("TASK_DB") or "").strip() or _default_db()

def _row_to_json(val: str | bytes | None) -> dict | list | None:
    if not val:
        return None
    if isinstance(val, bytes):
        val = val.decode("utf-8", "ignore")
    try:
        data = json.loads(val)
        return data if isinstance(data, (dict, list)) else {"raw": data}
    except Exception:
        return None


def _get(con: sqlite3.Connection, jid: int) -> dict[str, Any] | None:
    con.row_factory = sqlite3.Row
    r = con.execute(
        "SELECT id, task, status, result, last_error, payload FROM jobs WHERE id=?",
        (jid,),
    ).fetchone()
    return dict(r) if r else None


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    parent = int(payload.get("parent_job", 0)) or 0
    if parent <= 0:
        return {"ok": False, "agent": "report", "error": "invalid parent_job"}

    con = sqlite3.connect(DB)
    try:
        job = _get(con, parent)
        if not job:
            return {"ok": False, "agent": "report", "error": "parent not found"}

        res = _row_to_json(job.get("result"))
        if not isinstance(res, dict):
            return {"ok": False, "agent": "report", "error": "parent has no result"}

        detail = res.get("subjobs_detail") or {}
        if not isinstance(detail, dict):
            detail = {}

        return {
            "ok": True,
            "agent": "report",
            "job": {"id": job["id"], "task": job["task"], "status": job["status"]},
            "subjobs": list(detail.keys()),
        }
    finally:
        con.close()
