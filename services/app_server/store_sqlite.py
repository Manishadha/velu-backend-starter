from __future__ import annotations

import json
import os
import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def db_path() -> str:
    env = os.environ.get("TASK_DB")
    if env:
        return env
    return "data/pointers/tasks.db"


def _conn() -> sqlite3.Connection:
    path = db_path()
    parent = os.path.dirname(path) or "."
    Path(parent).mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def _table_cols(cx: sqlite3.Connection, table: str) -> dict[str, str]:
    rows = cx.execute(f"PRAGMA table_info({table})").fetchall()
    out: dict[str, str] = {}
    for r in rows:
        name = str(r[1] or "")
        typ = str(r[2] or "")
        if name:
            out[name] = typ
    return out


def init_db() -> None:
    with _conn() as cx:
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                ts       REAL NOT NULL,
                task     TEXT NOT NULL,
                payload  TEXT NOT NULL
            );
            """
        )
        cx.commit()


def insert(task: dict[str, Any]) -> None:
    init_db()
    tname = str(task.get("task") or "")
    payload = task.get("payload")
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("_velu", None)
        payload.pop("_org_id", None)
    payload_json = json.dumps(payload, ensure_ascii=False)

    with _conn() as cx:
        cols = _table_cols(cx, "tasks")
        has_ts = "ts" in cols
        if has_ts:
            tstype = (cols.get("ts") or "").upper()
            tsval: Any
            if "INT" in tstype:
                tsval = int(time.time())
            else:
                tsval = float(time.time())
            cx.execute(
                "INSERT INTO tasks (ts, task, payload) VALUES (?, ?, ?)",
                (tsval, tname, payload_json),
            )
        else:
            cx.execute(
                "INSERT INTO tasks (task, payload) VALUES (?, ?)",
                (tname, payload_json),
            )
        cx.commit()


def list_recent(limit: int = 50) -> Iterable[dict[str, Any]]:
    init_db()
    with _conn() as cx:
        cols = _table_cols(cx, "tasks")
        if "ts" in cols:
            rows = cx.execute(
                """
                SELECT id, ts, task, payload
                  FROM tasks
                 ORDER BY id DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
            out: list[dict[str, Any]] = []
            for rid, ts, task, payload in rows:
                out.append(
                    {
                        "id": rid,
                        "ts": ts,
                        "task": task,
                        "payload": json.loads(payload),
                    }
                )
            return out

        rows2 = cx.execute(
            """
            SELECT id, task, payload
              FROM tasks
             ORDER BY id DESC
             LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out2: list[dict[str, Any]] = []
        for rid, task, payload in rows2:
            out2.append(
                {
                    "id": rid,
                    "ts": None,
                    "task": task,
                    "payload": json.loads(payload),
                }
            )
        return out2
