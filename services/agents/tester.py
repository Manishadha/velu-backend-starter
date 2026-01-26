# services/agents/tester.py
from __future__ import annotations

import os
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping


def handle(task_or_payload: Any, payload: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    # Support both: handle(payload) and handle(name, payload)
    if isinstance(task_or_payload, dict) and payload is None:
        payload = task_or_payload
    payload = dict(payload or {})

    rootdir = str(payload.get("rootdir") or ".").strip() or "."
    root = Path(rootdir)

    # Respect explicit tests_path ONLY if it exists; otherwise ignore it safely.
    tests_path = payload.get("tests_path")
    if isinstance(tests_path, str) and tests_path.strip():
        candidate = tests_path.strip()
        if (root / candidate).exists():
            tests_path = candidate
        else:
            tests_path = None
    else:
        tests_path = None

    # Auto-detect
    if tests_path is None:
        if (root / "tests_app").exists() or (root / "pytest.ini").exists():
            tests_path = None  # rely on pytest.ini (testpaths=tests_app)
        elif (root / "tests").exists():
            tests_path = "tests"
        else:
            tests_path = None

    args: List[str] = payload.get("args") or [
        "-q",
        "--maxfail=1",
        "--disable-warnings",
        "--basetemp=/tmp/pytest",
    ]

    cmd = ["python", "-m", "pytest"]
    if tests_path:
        cmd.append(tests_path)
    cmd += args

    env = os.environ.copy()
    env.setdefault("HOME", tempfile.gettempdir())
    env.setdefault("PYTHONPATH", str(payload.get("pythonpath") or ".:./src"))

    try:
        cp = subprocess.run(  # nosec B603
            cmd,
            cwd=rootdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=int(payload.get("timeout") or 300),
        )

        ok = cp.returncode == 0
        if cp.returncode == 5 and payload.get("allow_no_tests", True):
            ok = True
        return {
            "ok": ok,
            "agent": "test",
            "returncode": cp.returncode,
            "cmd": cmd,
            "rootdir": rootdir,
            "tests_path": tests_path,
            "stdout": (cp.stdout or "")[-20000:],
            "stderr": (cp.stderr or "")[-20000:],
        }
    except Exception as e:
        return {
            "ok": False,
            "agent": "test",
            "error": f"pytest-failed: {type(e).__name__}: {e}",
            "cmd": cmd,
            "rootdir": rootdir,
            "tests_path": tests_path,
        }
        

