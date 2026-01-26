# services/queue/jobs_sqlite.py
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


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


def using_postgres() -> bool:
    return False


def db_path() -> str:
    env = (os.environ.get("TASK_DB") or "").strip()
    if env:
        return env

    if _in_pytest() or _env() in {"local", "test"}:
        base = (os.getenv("VELU_TMP") or "").strip()
        tmp = Path(base) if base else Path(tempfile.gettempdir())
        tmp.mkdir(parents=True, exist_ok=True)
        return str(tmp / "velu-jobs.db")

    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "data" / "jobs.db")


def sanitize_payload(payload: Any) -> Any:
    MAX_STR = 20000
    MAX_LIST = 2000
    MAX_DICT_KEYS = 2000
    MAX_FILE_CONTENT = 20000
    MAX_FILES = 500

    def clip_str(s: str, limit: int = MAX_STR) -> str:
        s = s or ""
        return s if len(s) <= limit else (s[:limit] + "…(truncated)…")

    if payload is None:
        return None

    if isinstance(payload, (bool, int, float)):
        return payload
    if isinstance(payload, str):
        return clip_str(payload)

    if isinstance(payload, (bytes, bytearray)):
        return clip_str(payload.decode("utf-8", errors="replace"))

    if isinstance(payload, list):
        return [sanitize_payload(x) for x in payload[:MAX_LIST]]

    if isinstance(payload, dict):
        out: Dict[str, Any] = {}
        for k, v in list(payload.items())[:MAX_DICT_KEYS]:
            ks = str(k)

            if ks == "files" and isinstance(v, list):
                kept = []
                for item in v[:MAX_FILES]:
                    if isinstance(item, dict):
                        kept.append(
                            {
                                "path": clip_str(str(item.get("path", "")), 500),
                                "content": clip_str(str(item.get("content", "")), MAX_FILE_CONTENT),
                            }
                        )
                out["files"] = kept
                continue

            if ks == "files_json" and isinstance(v, str):
                out["files_json"] = clip_str(v, MAX_STR)
                continue

            out[ks] = sanitize_payload(v)

        return out

    try:
        return {"raw": clip_str(str(payload))}
    except Exception:
        return {"raw": "<unserializable>"}


def normalize_result_for_storage(result: Any) -> str | None:
    if result is None:
        return None
    try:
        return json.dumps(result, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "result_not_json_serializable"}, ensure_ascii=False)


def _sqlite_connect() -> sqlite3.Connection:
    path = Path(db_path())
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_columns(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("PRAGMA table_info(jobs)")
    return {row[1] for row in cur.fetchall()}


def _sqlite_ensure_columns(conn: sqlite3.Connection) -> None:
    cols = _sqlite_columns(conn)
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
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {decl}")

    now = _now()
    cols2 = _sqlite_columns(conn)
    if "created_at" in cols2:
        conn.execute("UPDATE jobs SET created_at = ? WHERE created_at IS NULL", (now,))
    if "updated_at" in cols2:
        conn.execute("UPDATE jobs SET updated_at = ? WHERE updated_at IS NULL", (now,))
    if "attempts" in cols2:
        conn.execute("UPDATE jobs SET attempts = 0 WHERE attempts IS NULL")
    if "priority" in cols2:
        conn.execute("UPDATE jobs SET priority = 0 WHERE priority IS NULL")


def _sqlite_ensure_indexes(conn: sqlite3.Connection) -> None:
    cols = _sqlite_columns(conn)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_key ON jobs(key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_next_run ON jobs(next_run_at)")
    if "priority" in cols:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority)")


def ensure_schema() -> None:
    with closing(_sqlite_connect()) as conn:
        conn.execute(SCHEMA)
        _sqlite_ensure_columns(conn)
        _sqlite_ensure_indexes(conn)
        conn.commit()


def enqueue_job(
    task: dict[str, Any],
    key: str | None = None,
    priority: int = 0,
    org_id: str | None = None,
    project_id: str | None = None,
    created_by: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    *,
    require_tenant: bool = False,
) -> int:
    ensure_schema()
    now = _now()
    task_name = (task or {}).get("task") or "unknown"
    payload = (task or {}).get("payload") or {}
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("_velu", None)
    payload_json = json.dumps(sanitize_payload(payload), ensure_ascii=False)

    with closing(_sqlite_connect()) as conn:
        cur = conn.execute(
            "INSERT INTO jobs (ts, next_run_at, status, task, payload, result, err, last_error, attempts, priority, created_at, updated_at, key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (now, None, "queued", str(task_name), payload_json, None, None, None, 0, int(priority), now, now, key),
        )
        conn.commit()
        return int(cur.lastrowid)



def project_belongs_to_org(project_id: str, org_id: str) -> bool:
    pid = (project_id or "").strip()
    oid = (org_id or "").strip()
    if not pid or not oid:
        return False
    return True


def get_job(job_id: str | int) -> Optional[Dict[str, Any]]:
    ensure_schema()
    with closing(_sqlite_connect()) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (int(job_id),)).fetchone()
    if not row:
        return None

    rec = dict(row)
    raw_payload = rec.get("payload")
    if isinstance(raw_payload, (bytes, bytearray)):
        raw_payload = raw_payload.decode("utf-8", errors="ignore")
    if isinstance(raw_payload, str):
        s = raw_payload.strip()
        if s:
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    rec["payload"] = obj
            except Exception:
                pass

    return rec


def get_job_for_org(job_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    rec = get_job(job_id)
    if not rec:
        return None
    payload = rec.get("payload")
    if isinstance(payload, dict):
        velu = payload.get("_velu")
        if isinstance(velu, dict) and str(velu.get("org_id") or "") == str(org_id):
            return rec
        if str(payload.get("_org_id") or "") == str(org_id):
            return rec
    return None



def list_recent(limit: int = 50) -> Iterable[Dict[str, Any]]:
    ensure_schema()
    with closing(_sqlite_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY id DESC LIMIT ?",
            (max(1, min(1000, int(limit))),),
        ).fetchall()

    out: list[Dict[str, Any]] = []
    for r in rows:
        rec = dict(r)
        raw_payload = rec.get("payload")
        if isinstance(raw_payload, (bytes, bytearray)):
            raw_payload = raw_payload.decode("utf-8", errors="ignore")
        if isinstance(raw_payload, str):
            s = raw_payload.strip()
            if s:
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict):
                        rec["payload"] = obj
                except Exception:
                    pass
        out.append(rec)

    return out


def list_recent_for_org(*, org_id: str, limit: int = 50) -> list[dict]:
    items = list(list_recent(limit=limit))
    return [it for it in items if isinstance(it, dict)][: max(1, int(limit))]


def claim_one_job() -> Dict[str, Any] | None:
    ensure_schema()
    try:
        with closing(_sqlite_connect()) as conn:
            conn.isolation_level = None
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY priority DESC, id ASC LIMIT 1"
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            jid = int(row["id"])
            now = _now()
            cur = conn.execute(
                "UPDATE jobs SET status='working', attempts=COALESCE(attempts, 0) + 1, updated_at=? WHERE id=? AND status='queued'",
                (now, jid),
            )
            if cur.rowcount != 1:
                conn.execute("ROLLBACK")
                return None
            fresh = conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            conn.execute("COMMIT")
            return dict(fresh) if fresh else None
    except sqlite3.OperationalError as e:
        if "no such table: jobs" not in str(e).lower():
            raise
        ensure_schema()
        with closing(_sqlite_connect()) as conn:
            conn.isolation_level = None
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY priority DESC, id ASC LIMIT 1"
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            jid = int(row["id"])
            now = _now()
            cur = conn.execute(
                "UPDATE jobs SET status='working', attempts=COALESCE(attempts, 0) + 1, updated_at=? WHERE id=? AND status='queued'",
                (now, jid),
            )
            if cur.rowcount != 1:
                conn.execute("ROLLBACK")
                return None
            fresh = conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
            conn.execute("COMMIT")
            return dict(fresh) if fresh else None



def finish_job(job_id: str | int, result: dict[str, Any]) -> None:
    ensure_schema()
    with closing(_sqlite_connect()) as conn:
        with conn:
            conn.execute(
                "UPDATE jobs SET status='done', result=?, err=NULL, last_error=NULL, updated_at=? WHERE id=?",
                (normalize_result_for_storage(result), _now(), int(job_id)),
            )


def fail_job(job_id: str | int, error: Any) -> None:
    ensure_schema()
    if isinstance(error, str):
        err_json = json.dumps({"error": error}, ensure_ascii=False)
    else:
        try:
            err_json = json.dumps(error, ensure_ascii=False)
        except Exception:
            err_json = json.dumps({"error": str(error)}, ensure_ascii=False)

    with closing(_sqlite_connect()) as conn:
        with conn:
            conn.execute(
                "UPDATE jobs SET status='error', err=?, last_error=?, updated_at=? WHERE id=?",
                (err_json, err_json, _now(), int(job_id)),
            )


enqueue = enqueue_job
load = get_job
get = get_job

try:
    ensure_schema()
except Exception:
    pass
