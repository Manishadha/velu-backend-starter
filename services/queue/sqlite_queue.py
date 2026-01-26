from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

IDEMP_TTL_SEC = int(os.getenv("IDEMP_TTL_SEC", "300") or "300")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL,
    next_run_at REAL,
    status      TEXT,
    task        TEXT,
    payload     TEXT,
    result      TEXT,
    err         TEXT,
    last_error  TEXT,
    attempts    INTEGER NOT NULL DEFAULT 0,
    priority    INTEGER NOT NULL DEFAULT 0,
    created_at  REAL,
    updated_at  REAL,
    key         TEXT
);
"""

_AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    event TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    actor TEXT,
    detail TEXT
);
"""


def _now() -> float:
    return float(time.time())


def _env() -> str:
    return (os.getenv("ENV") or "local").strip().lower()


def _in_pytest() -> bool:
    if "pytest" in sys.modules:
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if "pytest" in (os.getenv("PYTEST_ADDOPTS") or ""):
        return True
    return False


def _db_path() -> Path:
    task_db = (os.getenv("TASK_DB") or "").strip()
    if task_db:
        return Path(task_db).expanduser().resolve()

    override = (os.getenv("SQLITE_QUEUE_PATH") or "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if _in_pytest() or _env() in {"local", "test"}:
        base = (os.getenv("VELU_TMP") or "").strip()
        tmp = Path(base) if base else Path(tempfile.gettempdir())
        tmp.mkdir(parents=True, exist_ok=True)
        return (tmp / "velu-jobs.db").resolve()

    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / "data" / "jobs.db").resolve()


def _connect() -> sqlite3.Connection:
    path = _db_path()
    with contextlib.suppress(Exception):
        path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(path), timeout=30, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    with contextlib.suppress(Exception):
        con.execute("PRAGMA busy_timeout=5000;")
    with contextlib.suppress(Exception):
        con.execute("PRAGMA journal_mode=WAL;")
    with contextlib.suppress(Exception):
        con.execute("PRAGMA synchronous=NORMAL;")
    with contextlib.suppress(Exception):
        con.execute("PRAGMA foreign_keys=ON;")
    return con


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _ensure_jobs_schema(con: sqlite3.Connection) -> None:
    con.execute(SCHEMA)
    cols = _columns(con, "jobs")

    add: list[tuple[str, str]] = [
        ("ts", "REAL"),
        ("next_run_at", "REAL"),
        ("status", "TEXT"),
        ("task", "TEXT"),
        ("payload", "TEXT"),
        ("result", "TEXT"),
        ("err", "TEXT"),
        ("last_error", "TEXT"),
        ("attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("priority", "INTEGER NOT NULL DEFAULT 0"),
        ("created_at", "REAL"),
        ("updated_at", "REAL"),
        ("key", "TEXT"),
    ]
    for name, decl in add:
        if name not in cols:
            con.execute(f"ALTER TABLE jobs ADD COLUMN {name} {decl}")

    con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_key ON jobs(key)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_next_run ON jobs(next_run_at)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority)")

    now = _now()
    cols2 = _columns(con, "jobs")
    if "created_at" in cols2:
        con.execute("UPDATE jobs SET created_at=? WHERE created_at IS NULL", (now,))
    if "updated_at" in cols2:
        con.execute("UPDATE jobs SET updated_at=? WHERE updated_at IS NULL", (now,))
    if "attempts" in cols2:
        con.execute("UPDATE jobs SET attempts=0 WHERE attempts IS NULL")
    if "priority" in cols2:
        con.execute("UPDATE jobs SET priority=0 WHERE priority IS NULL")


def _ensure_audit_schema(con: sqlite3.Connection) -> None:
    con.execute(_AUDIT_SCHEMA)


def _ensure() -> None:
    con = _connect()
    try:
        _ensure_jobs_schema(con)
        _ensure_audit_schema(con)
        con.commit()
    finally:
        with contextlib.suppress(Exception):
            con.close()


def _maybe_json(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, (bytes, bytearray)):
        x = x.decode("utf-8", "ignore")
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return x
        try:
            return json.loads(s)
        except Exception:
            return x
    return x


def audit(event: str, *, job_id: int, actor: str, detail: dict[str, Any]) -> None:
    _ensure()
    con = _connect()
    try:
        with con:
            con.execute(
                "INSERT INTO audit (ts, event, job_id, actor, detail) VALUES (?, ?, ?, ?, ?)",
                (_now(), str(event), int(job_id), actor, json.dumps(detail, ensure_ascii=False)),
            )
    finally:
        with contextlib.suppress(Exception):
            con.close()


def audit_recent(limit: int = 50) -> list[dict[str, Any]]:
    _ensure()
    con = _connect()
    try:
        rows = con.execute(
            "SELECT id, ts, event, job_id, actor, detail FROM audit ORDER BY id DESC LIMIT ?",
            (max(1, min(500, int(limit))),),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = _maybe_json(r["detail"]) if r["detail"] else {}
            if not isinstance(d, dict):
                d = {}
            out.append(
                {
                    "id": r["id"],
                    "ts": r["ts"],
                    "event": r["event"],
                    "job_id": r["job_id"],
                    "actor": r["actor"],
                    "detail": d,
                }
            )
        return out
    finally:
        with contextlib.suppress(Exception):
            con.close()


def enqueue(*, task: str, payload: dict[str, Any], priority: int = 0, key: str | None = None) -> int:
    _ensure()
    now = _now()
    con = _connect()
    try:
        with con:
            if key:
                cutoff = now - max(0, int(IDEMP_TTL_SEC))
                row = con.execute(
                    """
                    SELECT id FROM jobs
                     WHERE key = ?
                       AND created_at >= ?
                       AND status IN ('queued','working','done','cancelled')
                     ORDER BY id DESC
                     LIMIT 1
                    """,
                    (str(key), cutoff),
                ).fetchone()
                if row:
                    return int(row["id"])

            cur = con.execute(
                """
                INSERT INTO jobs
                    (ts, next_run_at, status, task, payload, result, err, last_error,
                     attempts, priority, created_at, updated_at, key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    None,
                    "queued",
                    str(task),
                    json.dumps(payload or {}, ensure_ascii=False),
                    None,
                    None,
                    None,
                    0,
                    int(priority),
                    now,
                    now,
                    key,
                ),
            )
            return int(cur.lastrowid)
    finally:
        with contextlib.suppress(Exception):
            con.close()


def load(job_id: int) -> dict[str, Any] | None:
    _ensure()
    con = _connect()
    try:
        row = con.execute("SELECT * FROM jobs WHERE id = ?", (int(job_id),)).fetchone()
        if not row:
            return None

        last_error = row["last_error"] if "last_error" in row.keys() else None
        if (last_error is None or last_error == "") and "err" in row.keys():
            last_error = row["err"]

        status = str(row["status"] or "").lower()
        if status == "running":
            status = "working"
        if status == "succeeded":
            status = "done"

        return {
            "id": row["id"],
            "task": row["task"],
            "payload": _maybe_json(row["payload"]) or {},
            "status": status,
            "result": _maybe_json(row["result"]) or {},
            "error": _maybe_json(last_error),
            "attempts": row["attempts"],
            "priority": row["priority"],
            "next_run_at": row["next_run_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "key": row["key"],
        }
    finally:
        with contextlib.suppress(Exception):
            con.close()


def list_recent(limit: int = 50, *, cursor: int | None = None) -> list[dict[str, Any]]:
    _ensure()
    con = _connect()
    try:
        sql = "SELECT * FROM jobs"
        args: tuple[Any, ...]
        if cursor:
            sql += " WHERE id < ?"
            args = (int(cursor),)
        else:
            args = ()
        sql += " ORDER BY id DESC LIMIT ?"
        args = args + (max(1, min(1000, int(limit))),)
        rows = con.execute(sql, args).fetchall()

        out: list[dict[str, Any]] = []
        for r in rows:
            last_error_raw = r["last_error"] if "last_error" in r.keys() else None
            if (last_error_raw is None or last_error_raw == "") and "err" in r.keys():
                last_error_raw = r["err"]

            status = str(r["status"] or "").lower()
            if status == "running":
                status = "working"
            if status == "succeeded":
                status = "done"

            out.append(
                {
                    "id": r["id"],
                    "task": r["task"],
                    "payload": _maybe_json(r["payload"]) or {},
                    "status": status,
                    "result": _maybe_json(r["result"]) or {},
                    "error": _maybe_json(last_error_raw),
                    "attempts": r["attempts"],
                    "priority": r["priority"],
                    "next_run_at": r["next_run_at"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "key": r["key"],
                }
            )
        return out
    finally:
        with contextlib.suppress(Exception):
            con.close()


def dequeue() -> int | None:
    _ensure()
    con = _connect()
    try:
        con.isolation_level = None
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            """
            SELECT id FROM jobs
             WHERE status = 'queued'
             ORDER BY priority DESC, id ASC
             LIMIT 1
            """
        ).fetchone()
        if not row:
            con.execute("COMMIT")
            return None
        jid = int(row["id"])
        now = _now()
        con.execute("UPDATE jobs SET status='working', updated_at=? WHERE id=? AND status='queued'", (now, jid))
        con.execute("COMMIT")
        return jid
    except Exception:
        with contextlib.suppress(Exception):
            con.execute("ROLLBACK")
        return None
    finally:
        with contextlib.suppress(Exception):
            con.close()


def finish(job_id: int, result: dict[str, Any]) -> None:
    _ensure()
    con = _connect()
    try:
        with con:
            con.execute(
                "UPDATE jobs SET status='done', result=?, err=NULL, last_error=NULL, updated_at=? WHERE id=?",
                (json.dumps(result or {}, ensure_ascii=False), _now(), int(job_id)),
            )
    finally:
        with contextlib.suppress(Exception):
            con.close()


def fail(job_id: int, error: Any) -> None:
    _ensure()
    con = _connect()
    try:
        if isinstance(error, str):
            err_json = json.dumps({"error": error}, ensure_ascii=False)
        else:
            try:
                err_json = json.dumps(error, ensure_ascii=False)
            except Exception:
                err_json = json.dumps({"error": str(error)}, ensure_ascii=False)

        with con:
            con.execute(
                "UPDATE jobs SET status='error', err=?, last_error=?, updated_at=? WHERE id=?",
                (err_json, err_json, _now(), int(job_id)),
            )
    finally:
        with contextlib.suppress(Exception):
            con.close()


def cancel(job_id: int) -> bool:
    _ensure()
    con = _connect()
    try:
        with con:
            row = con.execute("SELECT status FROM jobs WHERE id=?", (int(job_id),)).fetchone()
            if not row or str(row["status"]).lower() != "queued":
                return False
            con.execute(
                "UPDATE jobs SET status='cancelled', updated_at=? WHERE id=?",
                (_now(), int(job_id)),
            )
            return True
    finally:
        with contextlib.suppress(Exception):
            con.close()
