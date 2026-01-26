# services/worker/main.py
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Iterator

from orchestrator.router_client import route

if os.getenv("RUN_PYTEST") == "1":
    import pytest


def _truthy(v: str | None) -> bool:
    return bool(v) and v.lower() not in {"0", "", "false", "no"}


def _q():
    from services.queue import get_queue

    return get_queue()


def _call_router(name: str, payload: dict) -> Any:
    try:
        return route({"task": name, "payload": payload})
    except TypeError as te:
        try:
            return route(name, payload)
        except Exception:
            raise te from None


def _normalize_result(raw: Any) -> dict:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")

    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
            return {"ok": True, "data": parsed}
        except Exception:
            return {"ok": True, "data": raw}

    if isinstance(raw, dict):
        return raw

    return {"ok": True, "data": raw}


def _as_dict_payload(val: Any) -> dict[str, Any]:
    if isinstance(val, dict):
        return val
    if val is None:
        return {}
    return {"value": val}


def _enqueue(task: str, payload: dict[str, Any], *, priority: int = 0) -> str | int:
    return _q().enqueue(task=task, payload=payload, priority=priority)


def _require_job_done(job_id: str | int) -> dict[str, Any]:
    q = _q()
    rec = q.get(job_id) or q.load(job_id)
    if not rec:
        raise RuntimeError(f"dependency job {job_id} not found")

    status = (rec.get("status") or "").lower()
    if status in {"done", "succeeded"}:
        return rec.get("result") or {}

    raise RuntimeError(f"dependency job {job_id} not ready (status={status})")


def _task_fail_n(rec: dict) -> dict:
    payload = _as_dict_payload(rec.get("payload"))
    want = int(payload.get("fail_times", 1))
    attempts_so_far = int(rec.get("attempts") or 0)
    if attempts_so_far < want:
        raise RuntimeError(f"simulated failure {attempts_so_far + 1}/{want}")
    return {"ok": True, "message": f"passed after {attempts_so_far} failures"}


def _task_plan_pipeline(rec: dict) -> dict:
    payload = _as_dict_payload(rec.get("payload"))
    idea = payload.get("idea", "demo")
    module = payload.get("module", "hello_mod")
    try:
        plan_preview = _normalize_result(_call_router("plan", {"idea": idea, "module": module}))
    except Exception:
        plan_preview = {"ok": True, "plan": f"{idea} via {module}"}

    code_job_id = _enqueue(
        "generate_code",
        {"idea": idea, "module": module, "parent_job": rec.get("id")},
    )
    test_job_id = _enqueue("run_tests", {"code_job_id": code_job_id, "parent_job": rec.get("id")})

    return {
        "ok": True,
        "message": "pipeline created",
        "subjobs": {"generate_code": code_job_id, "run_tests": test_job_id},
        "plan": plan_preview.get("plan", f"{idea} via {module}"),
    }


def _task_generate_code(rec: dict) -> dict:
    payload = _as_dict_payload(rec.get("payload"))
    idea = payload.get("idea", "demo")
    module = payload.get("module", "hello_mod")

    os.makedirs("src", exist_ok=True)
    os.makedirs("tests", exist_ok=True)

    mod_path = f"src/{module}.py"
    test_path = f"tests/test_{module}.py"

    with open(mod_path, "w", encoding="utf-8") as f:
        f.write('def greet(name: str) -> str:\n    return f"Hello, {name}!"\n')

    with open(test_path, "w", encoding="utf-8") as f:
        f.write(
            f"from {module} import greet\n\n"
            "def test_greet():\n"
            "    assert greet('Velu') == 'Hello, Velu!'\n"
        )

    return {
        "ok": True,
        "message": "code generated",
        "idea": str(idea),
        "module": str(module),
        "files": [mod_path, test_path],
    }


def _task_run_tests(rec: dict) -> dict:
    payload = _as_dict_payload(rec.get("payload"))
    code_job_id = payload.get("code_job_id")
    if not code_job_id:
        raise RuntimeError("missing code_job_id")

    code_result = _require_job_done(code_job_id)
    module = (code_result or {}).get("module", "hello_mod")
    test_path = f"tests/test_{module}.py"

    src = os.path.abspath("src")
    if src not in sys.path:
        sys.path.insert(0, src)

    if "pytest" not in globals():
        raise RuntimeError("RUN_PYTEST is not enabled (set RUN_PYTEST=1)")

    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = pytest.main(["-q", test_path])
    if rc != 0:
        raise RuntimeError(
            f"pytest returned exit code {rc}\n{buf_out.getvalue()}\n{buf_err.getvalue()}"
        )

    return {"ok": True, "stdout": buf_out.getvalue(), "stderr": buf_err.getvalue()}


def _call_agent_handler(task_name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from services.agents import HANDLERS
    except Exception:
        return None

    fn = HANDLERS.get(task_name)
    if fn is None:
        return None

    try:
        return fn(payload)
    except TypeError:
        return fn(task_name, payload)  # type: ignore[misc]


def process_job(rec: dict) -> dict:
    name = rec["task"]

    if name == "fail_n":
        return _task_fail_n(rec)

    if name == "plan":
        payload = _as_dict_payload(rec.get("payload"))
        if _truthy(os.getenv("WORKER_ENABLE_PIPELINE")) and str(payload.get("module", "")).strip():
            return _task_plan_pipeline(rec)
        res = _normalize_result(_call_router(name, payload))
        module = str(payload.get("module", "")).strip()
        if module:
            idea = str(payload.get("idea", "")).strip()
            res.setdefault("plan", f"{idea} via {module}")
        return res

    if name == "generate_code":
        return _task_generate_code(rec)

    if name == "run_tests":
        return _task_run_tests(rec)

    payload = _as_dict_payload(rec.get("payload"))
    agent_res = _call_agent_handler(name, payload)
    if agent_res is not None:
        return agent_res

    return _normalize_result(_call_router(name, payload))


def _safe_seg(v: str) -> str:
    s = (v or "").strip()
    return "".join(ch for ch in s if ch.isalnum() or ch in {"-", "_"})


def _workspace_base() -> Path:
    v = (os.getenv("WORKSPACE_BASE") or "").strip()
    if v:
        return Path(v)
    velu_tmp = (os.getenv("VELU_TMP") or "").strip()
    base = Path(velu_tmp) if velu_tmp else Path(tempfile.gettempdir())
    return base / "velu-workspace"


def _job_workspace(job: dict[str, Any]) -> tuple[Path, Path]:
    org_id = job.get("org_id") or "local"
    org = _safe_seg(str(org_id))

    payload = job.get("payload")
    if not isinstance(payload, dict):
        payload = {}

    run_id = ""
    velu = payload.get("_velu")
    if isinstance(velu, dict):
        rid = velu.get("run_id")
        if isinstance(rid, str):
            run_id = _safe_seg(rid)

    if run_id:
        ws = _workspace_base() / org / run_id
    else:
        jid = _safe_seg(str(job.get("id") or ""))
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
def _isolated_env(tmpdir: Path | str, workspace: Path | str) -> Iterator[None]:
    tmpdir_p = Path(tmpdir)
    ws_p = Path(workspace)
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


def _attach_workspace(job: dict[str, Any], workspace: Path) -> dict[str, Any]:
    payload = job.get("payload")
    if not isinstance(payload, dict):
        payload = {}

    velu = payload.get("_velu")
    if not isinstance(velu, dict):
        velu = {}

    velu.setdefault("workspace", str(workspace))
    payload["_velu"] = velu
    job["payload"] = payload
    return job


def worker_main() -> None:
    q = _q()
    q.ensure_schema()

    max_iters = int(os.getenv("WORKER_MAX_ITERS", "0") or "0")
    iters = 0

    while True:
        if max_iters and iters >= max_iters:
            return
        iters += 1

        job = q.claim_one_job()
        if not job:
            time.sleep(0.1)
            if max_iters:
                return
            continue

        job_id = job.get("id")
        try:
            workspace, tmpdir = _job_workspace(job)
            job = _attach_workspace(job, workspace)
            with _isolated_env(tmpdir, workspace):
                result = process_job(job)
            q.finish_job(job_id, result)
        except Exception as e:
            q.fail_job(
                job_id,
                {"ok": False, "error": str(e), "trace": traceback.format_exc()},
            )


def main() -> None:
    worker_main()


if __name__ == "__main__":
    main()
