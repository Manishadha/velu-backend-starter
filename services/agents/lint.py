# services/agents/lint.py
from __future__ import annotations

import os  # noqa: F401
import subprocess  # nosec B404
from typing import Any


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    p = subprocess.Popen(  # nosec B603
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = p.communicate()
    return p.returncode, out, err


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run ruff and black --check on the given root (default: /workspace).
    """
    root = str(payload.get("root") or "/workspace")

    ruff_args = payload.get("ruff_args") or ["check", "."]
    black_args = payload.get("black_args") or ["--check", "."]

    results: dict[str, Any] = {"root": root, "steps": []}
    ok = True

    # Ruff
    rc, out, err = _run(["ruff", *ruff_args], cwd=root)
    results["steps"].append({"tool": "ruff", "returncode": rc, "stdout": out, "stderr": err})
    if rc != 0:
        ok = False

    # Black
    rc, out, err = _run(["black", *black_args], cwd=root)
    results["steps"].append({"tool": "black", "returncode": rc, "stdout": out, "stderr": err})
    if rc != 0:
        ok = False

    return {"ok": ok, "agent": "lint", **results}
