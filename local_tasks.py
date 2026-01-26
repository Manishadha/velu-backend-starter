# local_tasks.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import subprocess
import sys
import logging
from pathlib import Path

log = logging.getLogger("local_tasks")


# ---------- path checks for execute ----------


def _check_path(rel: str) -> Tuple[bool, str | None]:
    """
    Validate a relative path.

    Rules:
      - non-empty
      - not absolute
      - no leading '..'
      - no '..' segments
      - must start with 'src/' or 'tests/'
    """
    rel = (rel or "").strip()
    if not rel:
        return False, "empty path"

    if rel.startswith("/"):
        return False, "absolute path not allowed"

    if rel.startswith(".."):
        return False, "path traversal"

    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return False, "path traversal"

    if not (rel.startswith("src/") or rel.startswith("tests/")):
        return False, "outside allowed roots"

    return True, None


# ---------- execute: NOW actually writes files ----------


def execute(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Safe-ish file writer for Velu.

    - Only allows paths under src/ or tests/
    - Still validates against path traversal
    - Actually writes the provided content to disk
    """
    if payload is None:
        payload = {}

    raw_files = payload.get("files") or []
    if not isinstance(raw_files, list):
        raw_files = []

    # IMPORTANT:
    # Worker jobs run inside a per-job workspace (worker_entry chdir()).
    # Default to writing into the current working directory (workspace) to keep
    # pipeline execute+test consistent. You can override with payload.target_dir.
    target_dir = payload.get("target_dir")
    base_dir = Path(target_dir).resolve() if target_dir else Path.cwd().resolve()

    wrote: List[str] = []
    refused: List[Dict[str, str]] = []

    for item in raw_files:
        if not isinstance(item, dict):
            continue

        rel_path = str(item.get("path", "")).strip()
        if not rel_path:
            continue

        is_safe, reason = _check_path(rel_path)
        if not is_safe:
            refused.append({"path": rel_path, "reason": reason or "invalid path"})
            continue

        content = item.get("content")
        if content is None:
            content = ""
        text = str(content)

        target = base_dir / rel_path
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            wrote.append(rel_path)
        except Exception as e:  # pragma: no cover - defensive
            refused.append(
                {
                    "path": rel_path,
                    "reason": f"write failed: {type(e).__name__}: {e}",
                }
            )

    return {
        "ok": True,
        "wrote": wrote,
        "refused": refused,
        "cwd": str(Path.cwd().resolve()),
        "base_dir": str(base_dir),
    }


# ---------- local pytest runner for "test" ----------


def test(payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Run pytest locally in the checkout.

    Expected payload fields:
      - rootdir: where to run pytest (default ".")
      - tests_path: what to pass to pytest (default "tests")
      - args: extra pytest args (list)
    """
    if payload is None:
        payload = {}

    rootdir = str(payload.get("rootdir") or ".")
    tests_path = str(payload.get("tests_path") or "tests")
    args = payload.get("args") or []
    if not isinstance(args, list):
        args = []

    cmd = [sys.executable, "-m", "pytest", tests_path, *[str(a) for a in args]]

    log.info("local test: running %r in %r", cmd, rootdir)

    try:
        proc = subprocess.run(
            cmd,
            cwd=rootdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except Exception as e:  # pragma: no cover - defensive
        log.exception("local test failed: %s", e)
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"local test error: {type(e).__name__}: {e}",
        }


# ---------- install hook used by src/sitecustomize.py ----------


def install() -> None:
    """
    Patch Velu worker handlers so 'execute' and 'test'
    use our local implementations.
    """
    try:
        from services.queue import worker_entry  # type: ignore
    except Exception as exc:  # pragma: no cover
        log.warning("install(): failed to import worker_entry: %r", exc)
        return

    handlers = worker_entry.HANDLERS

    handlers["execute"] = execute
    handlers["test"] = test

    log.info(
        "local_tasks.install: patched handlers: %s",
        {k: handlers[k] for k in ("execute", "test") if k in handlers},
    )
