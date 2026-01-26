# services/agents/aggregate.py
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import suppress
from typing import Any

from services.queue import get_queue

q = get_queue()


def _con() -> sqlite3.Connection:
    db = os.environ.get("TASK_DB", "/data/jobs.db")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def _to_json(v: Any) -> dict:
    if not v:
        return {}
    if isinstance(v, dict):
        return v
    try:
        return json.loads(v)
    except Exception:
        return {}


def _get_job(con: sqlite3.Connection, jid: int) -> dict[str, Any]:
    row = con.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    if not row:
        return {}
    d = dict(row)
    d["payload"] = _to_json(d.get("payload"))
    d["result"] = _to_json(d.get("result"))
    return d


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        parent = int(payload.get("parent_job") or 0)
        if not parent:
            return {"ok": False, "agent": "aggregate", "error": "missing parent_job"}

        con = _con()
        try:
            parent_job = _get_job(con, parent)
            if not parent_job:
                return {
                    "ok": False,
                    "agent": "aggregate",
                    "error": "parent not found",
                }
        finally:
            con.close()

        # Optional: write an audit entry that aggregation ran (best-effort)
        with suppress(Exception):
            q.audit("aggregate", job_id=parent, actor="worker", detail={})

        return {
            "ok": True,
            "agent": "aggregate",
            "parent": parent,
            "summary": "ok",
        }
    except Exception as e:
        return {"ok": False, "agent": "aggregate", "error": str(e)}
