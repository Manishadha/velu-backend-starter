# services/agents/autodev.py
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from services.queue import get_queue
from services.queue import jobs_sqlite  # allowed

q = get_queue()

import logging  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------
# Queue helpers
# ---------------------------
def _enqueue(task: str, payload: dict, priority: int = 0) -> int:
    """
    Enqueue a job into the Velu queue using the same mechanism as /tasks.
    """
    return get_queue.enqueue(task=task, payload=payload, priority=priority)


def _load(job_id: int) -> dict:
    """
    Load a job row directly from the jobs DB.

    We read from the same SQLite DB that the worker uses (jobs_sqlite.db_path()).
    The row includes fields like: id, task, payload, status, result, err, etc.
    """
    db_path = jobs_sqlite.db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cur.fetchone()
        finally:
            conn.close()
    except Exception as exc:
        return {"ok": False, "error": f"load_failed: {exc}"}

    if not row:
        return {"ok": False, "error": "not found"}

    # Convert sqlite Row -> plain dict
    out = dict(row)

    # If result/err are JSON strings, try to decode them for convenience
    import json

    for key in ("result", "err", "payload"):
        if key in out and isinstance(out[key], str):
            s = out[key].strip()
            if s:
                try:
                    out[key] = json.loads(s)
                except Exception:
                    # keep raw string if not valid JSON, but log for debugging
                    logger.debug(
                        "autodev: could not parse JSON for key %s, keeping raw value",
                        key,
                        exc_info=True,
                    )
                    pass

    return out


# ---------------------------
# Environment / FS helpers
# ---------------------------
def _is_writable(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".velu_write_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _detect_project_root() -> Path:
    """
    Find a writable project root inside container:
    Preference order:
      1) /workspace  (external project volume when provided)
      2) /git        (if work tree is mounted here)
      3) /data/generated (we create/use this if writable)
      4) /app        (only if writable; in many images it's read-only)
    """
    candidates = [
        Path("/workspace"),
        Path("/git"),
        Path("/data/generated"),
        Path("/app"),
    ]

    for c in candidates:
        if c.exists() and _is_writable(c):
            return c

    # Last resort: try to create /data/generated
    dg = Path("/data/generated")
    if _is_writable(dg):
        return dg

    # Absolute fallback to CWD (unlikely but prevents crash)
    return Path.cwd()


def _detect_git_root() -> Path | None:
    """
    Return a git work tree if present and usable, else None.
    We check GIT_WORK_TREE first, then /git, then the detected project root.
    """
    env_wt = os.getenv("GIT_WORK_TREE", "").strip()
    if env_wt:
        gp = Path(env_wt)
        if (gp / ".git").exists():
            return gp

    # common mount
    gp = Path("/git")
    if (gp / ".git").exists():
        return gp

    root = _detect_project_root()
    if (root / ".git").exists():
        return root

    return None


def _normalize_codegen_files(root: Path, files: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Accept typical codegen outputs:
      [{ "path": "src/x.py", "content": "..." }, ...]
    Make sure paths are absolute under root, reject anything outside root.
    """
    out: List[Dict[str, str]] = []
    for f in files:
        p = str(f.get("path", "")).strip()
        content = f.get("content")
        if not p or content is None:
            continue

        # strip leading slash to avoid escaping the root
        p_rel = p[1:] if p.startswith("/") else p
        abs_path = (root / p_rel).resolve()

        try:
            # ensure abs_path is inside root
            abs_path.relative_to(root.resolve())
        except Exception:
            # skip any attempt to write outside the root, but record it
            logger.warning(
                "autodev: blocked write outside root: %s",
                abs_path,
                exc_info=True,
            )
            continue

        out.append({"path": str(abs_path), "content": str(content)})
    return out


# ---------------------------
# Pytest failures & prompts
# ---------------------------
def _pytest_failures(stdout: str, stderr: str) -> List[Dict[str, Any]]:
    """
    Very lightweight parser to extract failing test names / file paths from pytest output.
    Returns entries: {"file": "tests/test_x.py", "nodeid": "tests/test_x.py::test_y", "message": "..."}
    """
    out = stdout + "\n" + stderr
    failures: List[Dict[str, Any]] = []

    # pattern 1: "FAILED tests/test_file.py::test_func - AssertionError: ..."
    for m in re.finditer(r"FAILED\s+([^\s:]+::[^\s]+)\s+-\s+(.+)", out):
        nodeid = m.group(1).strip()
        msg = m.group(2).strip()
        file_path = nodeid.split("::", 1)[0]
        failures.append({"file": file_path, "nodeid": nodeid, "message": msg})

    # fallback: "tests/test_file.py::test_func ... FAILED"
    if not failures:
        for m in re.finditer(r"(^|\n)([^\s:]+\.py::[^\s]+).*?FAILED", out):
            nodeid = m.group(2).strip()
            file_path = nodeid.split("::", 1)[0]
            failures.append({"file": file_path, "nodeid": nodeid, "message": ""})

    return failures


def _build_fix_prompt(
    idea: str, module: str, failures: List[Dict[str, Any]], last_stdout: str
) -> str:
    lines = [
        "You are a senior software engineer. Fix the code to make tests pass.",
        f"High-level goal: {idea}",
        f"Module: {module}",
        "",
        "Failing tests:",
    ]
    for f in failures:
        lines.append(f"- {f['nodeid']} :: {f.get('message', '')}")
    lines += [
        "",
        "Rules:",
        "- Only change files that are necessary.",
        "- Do not disable or delete failing tests.",
        "- Prefer minimal, correct fixes.",
        "- Keep style consistent (Black/Ruff).",
        "",
        "Pytest output excerpt (tail):",
        "-----",
        last_stdout[-4000:],  # cap context
        "-----",
    ]
    return "\n".join(lines)


# ---------------------------
# Main handler
# ---------------------------
def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Autodev v2 (deploy-hardened):
      1) Plan/build once via 'pipeline' (seeds files if needed).
      2) Lint -> Test.
      3) If red: parse failures, call 'codegen' to patch -> Execute -> Lint -> Test again.
      4) Stop when green or max cycles exhausted; commit if green and git repo present.
    Safe when /workspace or /git are missing: it auto-detects a writable root and
    skips git commit if no repo.
    """
    idea = str(payload.get("idea") or payload.get("plan") or "Improve module")
    module = str(payload.get("module", "hello_mod"))
    message = str(payload.get("message", f"feat: {idea}"))
    run_tests = bool(payload.get("tests", True))
    max_cycles = int(payload.get("max_cycles", 5))
    priority_base = int(payload.get("priority", 5))

    project_root = _detect_project_root()
    git_root = _detect_git_root()

    steps: Dict[str, Any] = {
        "project_root": str(project_root),
        "git_root": str(git_root) if git_root else None,
        "cycles": [],
    }

    # 0) Seed once via pipeline (idempotent in your setup)
    first_cycle: Dict[str, Any] = {"stage": "seed"}
    try:
        p_id = _enqueue(
            "pipeline",
            {"idea": idea, "module": module, "tests": run_tests},
            priority=priority_base + 2,
        )
        first_cycle["pipeline_job"] = p_id
        p_rec = _load(p_id)
        first_cycle["pipeline_result"] = p_rec.get("result")
    except Exception as e:
        first_cycle["error"] = f"seed_failed: {e}"

    steps["cycles"].append(first_cycle)

    # Iterate until tests are green
    green = False
    last_stdout = ""
    cycle_idx = 0

    while cycle_idx < max_cycles:
        cycle: Dict[str, Any] = {"index": cycle_idx}

        # 1) Lint (use detected root)
        l_id = _enqueue("lint", {"root": str(project_root)}, priority=priority_base)
        cycle["lint_job"] = l_id
        l_rec = _load(l_id)
        cycle["lint_result"] = l_rec.get("result")

        # 2) Test
        if run_tests:
            t_id = _enqueue(
                "test",
                {
                    "rootdir": str(project_root),
                    "tests_path": "tests",
                    "args": [
                        "-q",
                        "--maxfail=1",
                        "--disable-warnings",
                        "--basetemp=/tmp/pytest",
                    ],
                },
                priority=priority_base,
            )
            cycle["test_job"] = t_id
            t_rec = _load(t_id)
            t_res = t_rec.get("result") or {}
            cycle["test_result"] = t_res

            rc = int(t_res.get("returncode", 1))
            last_stdout = (t_res.get("stdout") or "") + "\n" + (t_res.get("stderr") or "")

            if rc == 0:
                green = True
                steps["cycles"].append(cycle)
                break

            # 3) Tests failed → parse & patch
            failures = _pytest_failures(t_res.get("stdout", ""), t_res.get("stderr", ""))
            cycle["failures"] = failures

            fix_prompt = _build_fix_prompt(idea, module, failures, last_stdout)
            cg_id = _enqueue(
                "codegen",
                {
                    "root": str(project_root),
                    "instructions": fix_prompt,
                    "allow_files_outside_root": False,
                },
                priority=priority_base + 1,
            )
            cycle["codegen_job"] = cg_id
            cg_rec = _load(cg_id)
            cycle["codegen_result"] = cg_rec.get("result")

            # Normalize output into files list
            produced_files: List[Dict[str, Any]] = []  # noqa: F841
            cg = cg_rec.get("result") or {}
            files = []
            if isinstance(cg.get("files"), list):
                files = cg["files"]
            elif isinstance(cg.get("data"), dict) and isinstance(cg["data"].get("files"), list):
                files = cg["data"]["files"]

            files = _normalize_codegen_files(project_root, files)

            if files:
                ex_id = _enqueue("execute", {"files": files}, priority=priority_base + 1)
                cycle["execute_job"] = ex_id
                ex_rec = _load(ex_id)
                cycle["execute_result"] = ex_rec.get("result")
                ex = ex_rec.get("result") or {}
                cycle["patched_files"] = ex.get("wrote", [])
            else:
                cycle["patched_files"] = []

        steps["cycles"].append(cycle)
        cycle_idx += 1

    # Commit if green AND repo exists
    commit_info: Dict[str, Any] = {}
    if green and git_root and (git_root / ".git").exists():
        gc_id = _enqueue("gitcommit", {"message": message}, priority=1)
        commit_info["gitcommit_job"] = gc_id
        gc_rec = _load(gc_id)
        commit_info["gitcommit_result"] = gc_rec.get("result")
    elif green:
        commit_info["skipped"] = True
        commit_info["reason"] = "no git repo present"

    return {
        "ok": green,
        "agent": "autodev",
        "idea": idea,
        "module": module,
        "max_cycles": max_cycles,
        "green": green,
        "commit": commit_info,
        "steps": steps,
    }
