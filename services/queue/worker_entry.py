# services/queue/worker_entry.py
from __future__ import annotations

import contextlib
import logging
import os
import socket  # noqa: F401
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Mapping

from services.agents import pipeline_waiter
from services.agents import (
    aggregate,
    ai_features,
    api_design,
    architecture,
    autodev,
    backend_scaffold,
    chat,
    codegen,
    datamodel,
    executor,
    gitcommit,
    hospital_apply_patches,
    hospital_codegen,
    intake,
    packager,
    planner,
    report,
    repo_summary,
    requirements,
    security_hardening,
    tester,
    testgen,
    ui_scaffold,
    sleep,
)
from services.agents import pipeline_runner, security_scan
from services.contracts.jobs import decode_task_and_payload
from services.queue import jobs as jobs_api

logger = logging.getLogger(__name__)

HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "requirements": requirements.handle,
    "architecture": architecture.handle,
    "datamodel": datamodel.handle,
    "api_design": api_design.handle,
    "ui_scaffold": ui_scaffold.handle,
    "backend_scaffold": backend_scaffold.handle,
    "ai_features": ai_features.handle,
    "security_hardening": security_hardening.handle,
    "testgen": testgen.handle,
    "pipeline": pipeline_runner.handle,
    "plan": planner.handle,
    "aggregate": aggregate.handle,
    "gitcommit": gitcommit.handle,
    "codegen": codegen.handle,
    "execute": executor.handle,
    "test": tester.handle,
    "report": report.handle,
    "intake": intake.handle,
    "chat": chat.handle,
    "hospital_codegen": hospital_codegen.handle,
    "hospital_apply_patches": hospital_apply_patches.handle,
    "packager": packager.handle,
    "autodev": autodev.handle,
    "repo_summary": repo_summary.handle,
    "security_scan": security_scan.handle,
    "pipeline_waiter": pipeline_waiter.handle,
    "sleep": sleep.handle,
}

try:
    import local_tasks as _local  # type: ignore[import]

    allow_core_override = (os.getenv("VELU_ALLOW_LOCAL_CORE_TASKS") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    for _name in ("repo_summary",):
        if hasattr(_local, _name):
            HANDLERS[_name] = getattr(_local, _name)
            logger.info("local_tasks override/extend: %s -> %r", _name, HANDLERS[_name])

    if allow_core_override:
        for _name in ("execute", "test"):
            if hasattr(_local, _name):
                HANDLERS[_name] = getattr(_local, _name)
                logger.info("local_tasks CORE override enabled: %s -> %r", _name, HANDLERS[_name])

except Exception as exc:
    logger.warning("local_tasks overrides not loaded: %s", exc)

def _default_worker_id() -> str:
    wid = (os.getenv("VELU_WORKER_ID") or "").strip()
    if wid:
        return wid
    host = "host"
    try:
        import socket
        host = socket.gethostname() or "host"
    except Exception:
        host = "host"
    return f"{host}:{os.getpid()}"


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    try:
        if hasattr(row, "keys"):
            ks = set(row.keys())
            if key in ks:
                return row[key]
            return default
    except Exception:
        pass
    if isinstance(row, Mapping):
        return row.get(key, default)
    try:
        return getattr(row, key)
    except Exception:
        return default


def _job_id(row: Any) -> str:
    v = _row_get(row, "id")
    return "" if v is None else str(v)


def _workspace_base() -> Path:
    v = (os.getenv("WORKSPACE_BASE") or "").strip()
    if v:
        return Path(v)
    env = (os.getenv("ENV") or "local").strip().lower()
    if os.getenv("PYTEST_CURRENT_TEST") or env in {"local", "test"}:
        velu_tmp = (os.getenv("VELU_TMP") or "").strip()
        base = Path(velu_tmp) if velu_tmp else Path(tempfile.gettempdir())
        return base / "velu-workspace"
    return Path("/workspace")


def _safe_seg(v: str) -> str:
    s = (v or "").strip()
    return "".join(ch for ch in s if ch.isalnum() or ch in {"-", "_"})


def _job_workspace(row: Any) -> tuple[Path, Path]:
    org_id = _row_get(row, "org_id")
    if not org_id:
        if jobs_api.using_postgres():
            raise RuntimeError("refusing job without org_id (postgres mode)")
        org = "local"
    else:
        org = _safe_seg(str(org_id))

    _, payload = decode_task_and_payload(_row_get(row, "task"), _row_get(row, "payload"))

    run_id = ""
    if isinstance(payload, dict):
        velu = payload.get("_velu")
        if isinstance(velu, dict):
            rid = velu.get("run_id")
            if isinstance(rid, str):
                run_id = _safe_seg(rid)

    if run_id:
        ws = _workspace_base() / org / run_id
    else:
        jid = _safe_seg(_job_id(row))
        if not jid:
            raise RuntimeError("missing job id")
        ws = _workspace_base() / org / jid

    tmp = ws / "tmp"
    ws.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)

    with contextlib.suppress(Exception):
        ws.chmod(0o700)
        tmp.chmod(0o700)

    return ws, tmp


@contextmanager
def _isolated_env(tmpdir: Path | str, workspace: Path | str | None = None) -> Iterator[None]:
    tmpdir_p = Path(tmpdir)
    ws_p = Path(workspace) if workspace is not None else tmpdir_p
    old_env = dict(os.environ)
    old_cwd = Path.cwd()
    try:
        os.environ["TMPDIR"] = str(tmpdir_p)
        os.environ["TEMP"] = str(tmpdir_p)
        os.environ["TMP"] = str(tmpdir_p)
        ws_p.mkdir(parents=True, exist_ok=True)
        os.chdir(str(ws_p))
        yield
    finally:
        with contextlib.suppress(Exception):
            os.chdir(str(old_cwd))
        os.environ.clear()
        os.environ.update(old_env)


def enqueue(task: str, payload: Dict[str, Any] | None = None, priority: int = 0, key: str | None = None) -> Any:
    return jobs_api.enqueue(task=str(task), payload=payload or {}, priority=int(priority), key=key)


def load(job_id: Any) -> Dict[str, Any]:
    rec = jobs_api.get(job_id)
    return rec or {}


def _materialize_files(workspace: Path, files: Any) -> list[str]:
    wrote: list[str] = []
    if not isinstance(files, list):
        return wrote

    ws = workspace.resolve()

    for item in files:
        if not isinstance(item, dict):
            continue

        raw_path = item.get("path")
        content = item.get("content")

        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        if not isinstance(content, str):
            continue

        rel_str = raw_path.strip().replace("\\", "/").lstrip("/")
        if rel_str in {".", ""}:
            continue

        rel_path = Path(rel_str)

        if rel_path.is_absolute():
            continue
        if any(part in {"..", ""} for part in rel_path.parts):
            continue

        out = (ws / rel_path).resolve()

        try:
            out.relative_to(ws)
        except ValueError:
            continue

        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8", errors="strict")

        wrote.append(rel_path.as_posix())

    return sorted(wrote)


def _process_task(row: Any, workspace: Path | None = None) -> Dict[str, Any]:
    task, payload = decode_task_and_payload(_row_get(row, "task"), _row_get(row, "payload"))
    task = (task or "").strip()
    payload = dict(payload or {})

    if workspace is not None:
        velu = payload.get("_velu")
        if not isinstance(velu, dict):
            velu = {}
        if "workspace" not in velu:
            velu["workspace"] = str(workspace)
        payload["_velu"] = velu

    handler = HANDLERS.get(task)
    if handler is None:
        return {"ok": False, "error": f"unknown task: {task}"}

    try:
        return handler(payload)
    except Exception as exc:
        return {
            "ok": False,
            "stage": f"{task}_error",
            "error": f"{exc.__class__.__name__}: {exc}",
            "trace": traceback.format_exc(),
            "payload": payload,
        }


def run_one_job() -> bool:
    jobs_api.ensure_schema()
    wid = _default_worker_id()

    # Postgres mode will use worker_id; sqlite mode ignores it (via queue_api passthrough)
    row = jobs_api.claim_one_job(worker_id=wid)
    if not row:
        return False

    jid = _job_id(row)
    if not jid:
        return False

    try:
        workspace, tmpdir = _job_workspace(row)
        with _isolated_env(tmpdir, workspace):
            result = _process_task(row, workspace)

        if not isinstance(result, dict):
            result = {"ok": True, "data": result}

        wrote = _materialize_files(workspace, result.get("files"))
        result["wrote"] = wrote
        result["cwd"] = str(workspace)

        jobs_api.finish_job(jid, result)
    except Exception as exc:
        jobs_api.fail_job(
            jid,
            {"error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc(), "job_id": jid},
        )

    return True


# --- legacy sqlite helpers (kept for compatibility/tests) ---

def _claim_one_job(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    now = float(time.time())
    conn.execute("BEGIN IMMEDIATE")

    if "priority" in cols:
        row = conn.execute(
            "SELECT * FROM jobs WHERE status='queued' ORDER BY priority DESC, id ASC LIMIT 1"
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY id ASC LIMIT 1").fetchone()

    if not row:
        conn.execute("COMMIT")
        return None

    jid = int(row["id"])

    if "attempts" in cols and "updated_at" in cols:
        cur = conn.execute(
            "UPDATE jobs SET status='working', attempts=COALESCE(attempts, 0) + 1, updated_at=? "
            "WHERE id=? AND status='queued'",
            (now, jid),
        )
    elif "attempts" in cols:
        cur = conn.execute(
            "UPDATE jobs SET status='working', attempts=COALESCE(attempts, 0) + 1 "
            "WHERE id=? AND status='queued'",
            (jid,),
        )
    elif "updated_at" in cols:
        cur = conn.execute(
            "UPDATE jobs SET status='working', updated_at=? WHERE id=? AND status='queued'",
            (now, jid),
        )
    else:
        cur = conn.execute("UPDATE jobs SET status='working' WHERE id=? AND status='queued'", (jid,))

    if cur.rowcount != 1:
        conn.execute("ROLLBACK")
        return None

    fresh = conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    conn.execute("COMMIT")
    return fresh


def _complete_job(conn, job_id: int, result: Any, error: Any):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    now = float(time.time())

    if error is None:
        status = "done"
        err_json = None
    else:
        status = "error"
        if isinstance(error, str):
            err_obj = {"error": error}
        else:
            err_obj = error
        try:
            import json as _json

            err_json = _json.dumps(err_obj, ensure_ascii=False)
        except Exception:
            err_json = '{"error":"unserializable"}'

    res_json = None
    if "result" in cols:
        try:
            import json as _json

            res_json = _json.dumps(result, ensure_ascii=False) if result is not None else None
        except Exception:
            res_json = '{"ok":false,"error":"result_not_json_serializable"}'

    has_err = "err" in cols
    has_last_error = "last_error" in cols
    has_updated_at = "updated_at" in cols
    has_result = "result" in cols

    if has_result and has_err and has_last_error and has_updated_at:
        conn.execute(
            "UPDATE jobs SET status=?, result=?, err=?, last_error=?, updated_at=? WHERE id=?",
            (status, res_json, err_json, err_json, now, int(job_id)),
        )
    elif has_result and has_err and has_updated_at:
        conn.execute(
            "UPDATE jobs SET status=?, result=?, err=?, updated_at=? WHERE id=?",
            (status, res_json, err_json, now, int(job_id)),
        )
    elif has_result and has_last_error and has_updated_at:
        conn.execute(
            "UPDATE jobs SET status=?, result=?, last_error=?, updated_at=? WHERE id=?",
            (status, res_json, err_json, now, int(job_id)),
        )
    elif has_result and has_updated_at:
        conn.execute(
            "UPDATE jobs SET status=?, result=?, updated_at=? WHERE id=?",
            (status, res_json, now, int(job_id)),
        )
    elif has_updated_at:
        conn.execute("UPDATE jobs SET status=?, updated_at=? WHERE id=?", (status, now, int(job_id)))
    else:
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, int(job_id)))

    conn.commit()

def _attach_result_meta(result: dict[str, Any], row: Any, worker_id: str) -> dict[str, Any]:
    """
    Phase 2.2: ensure job attribution is present in the RESULT JSON (not only DB columns).
    This makes downstream artifacts/reporting auditable even if a handler forgets to include attribution.
    """
    meta = result.get("_velu_meta")
    if not isinstance(meta, dict):
        meta = {}

    meta.setdefault("job_id", _job_id(row))
    meta.setdefault("org_id", str(_row_get(row, "org_id") or ""))
    meta.setdefault("project_id", str(_row_get(row, "project_id") or ""))
    meta.setdefault("actor_type", str(_row_get(row, "actor_type") or ""))
    meta.setdefault("actor_id", str(_row_get(row, "actor_id") or ""))
    meta.setdefault("claimed_by", str(worker_id or ""))

    result["_velu_meta"] = meta
    return result
def _debug_hold_after_claim(*, in_pytest: bool, using_postgres: bool) -> None:
    """
    Debug helper: keep the worker paused *after claiming* a job so you can observe the
    job in 'working' state and optionally kill the worker.

    Enabled when:
      - using_postgres is True (Phase-1 leasing is a PG behavior)
      - NOT in pytest
      - VELU_DEBUG_HOLD_AFTER_CLAIM_SEC is set to a positive number

    Notes:
      - This is intentionally a sleep in the worker process (no DB writes).
      - Keep it OFF in normal runs.
    """
    if in_pytest:
        return
    if not using_postgres:
        return

    raw = (os.getenv("VELU_DEBUG_HOLD_AFTER_CLAIM_SEC") or "").strip()
    if not raw:
        return
    try:
        sec = float(raw)
    except Exception:
        return
    if sec > 0:
        time.sleep(sec)


def _attach_result_meta(result: Dict[str, Any], row: Any, worker_id: str) -> Dict[str, Any]:
    """
    Phase-1/2 friendly: enrich result with minimal attribution/debug metadata.
    Must never raise.
    """
    try:
        org_id = None
        actor_type = None
        actor_id = None
        claimed_by = None

        if isinstance(row, Mapping):
            org_id = row.get("org_id")
            actor_type = row.get("actor_type")
            actor_id = row.get("actor_id")
            claimed_by = row.get("claimed_by")
        else:
            org_id = getattr(row, "org_id", None)
            actor_type = getattr(row, "actor_type", None)
            actor_id = getattr(row, "actor_id", None)
            claimed_by = getattr(row, "claimed_by", None)

        meta = {
            "org_id": str(org_id) if org_id else None,
            "actor_type": str(actor_type) if actor_type else None,
            "actor_id": str(actor_id) if actor_id else None,
            "claimed_by": str(claimed_by) if claimed_by else None,
            "worker_id": str(worker_id),
        }

        
        out = dict(result or {})
        out["_velu_meta"] = {k: v for k, v in meta.items() if v is not None}
        return out
    except Exception:
        return dict(result or {})


def worker_main() -> None:
    jobs_api.ensure_schema()
    using_pg = bool(jobs_api.using_postgres())
    mode = "postgres" if using_pg else "sqlite"
    print(f"worker: online backend={mode}", flush=True)

    
    wid = _default_worker_id()
    print(f"worker: id={wid}", flush=True)

    
    lease_seconds = int(os.getenv("VELU_JOB_LEASE_SEC", "300") or "300")

    in_pytest = ("pytest" in sys.modules) or bool(os.getenv("PYTEST_CURRENT_TEST"))
    max_jobs = int(os.getenv("VELU_WORKER_MAX_JOBS", "1")) if in_pytest else 0

    processed = 0
    idle_loops = 0

    while True:
        
        if using_pg:
            row = jobs_api.claim_one_job(worker_id=wid, lease_seconds=lease_seconds)
        else:
            row = jobs_api.claim_one_job()

        if not row:
            if in_pytest:
                idle_loops += 1
                if idle_loops >= 50:
                    return
            time.sleep(0.1)
            continue

        idle_loops = 0

        jid = _job_id(row)
        if not jid:
            
            continue

        
        _debug_hold_after_claim(in_pytest=in_pytest, using_postgres=using_pg)

        try:
            workspace, tmpdir = _job_workspace(row)
            with _isolated_env(tmpdir, workspace):
                result = _process_task(row, workspace)

            if not isinstance(result, dict):
                result = {"ok": True, "data": result}

            wrote = _materialize_files(workspace, result.get("files"))
            result["wrote"] = wrote
            result["cwd"] = str(workspace)

            
            result = _attach_result_meta(result, row, wid)

            jobs_api.finish_job(jid, result)
            print(f"worker: done {jid}", flush=True)

        except Exception as exc:
            jobs_api.fail_job(
                jid,
                {"error": f"{exc.__class__.__name__}: {exc}", "trace": traceback.format_exc(), "job_id": jid},
            )
            print(f"worker: error {jid}: {exc}", flush=True)

        if in_pytest:
            processed += 1
            if processed >= max_jobs:
                return



__all__ = [
    "HANDLERS",
    "enqueue",
    "load",
    "run_one_job",
    "worker_main",
    "_claim_one_job",
    "_complete_job",
]


def main() -> None:
    worker_main()


if __name__ == "__main__":
    main()
