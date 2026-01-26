from __future__ import annotations

import os
import re
import subprocess  # nosec B404
from collections.abc import Sequence
from typing import Any

# Conventional commit subject: "type(scope?): message"
_CC = re.compile(r"^(feat|fix|chore|docs|refactor|test|build|ci|perf|style)" r"(\([^)]+\))?: .+")


def _run(cmd: Sequence[str]) -> tuple[int, str, str]:
    """
    Run a git command and return (returncode, stdout, stderr).
    """
    p = subprocess.Popen(  # nosec B603
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )  # nosec B603
    out, err = p.communicate()
    return p.returncode, out, err


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Git commit agent.

    Expects:
      payload["message"]: commit subject line (conventional commit style).

    Optional:
      payload["paths"]: list of paths to add; if omitted, uses "git add -A".
    """
    msg = str(payload.get("message") or "chore: snapshot").strip()
    paths = payload.get("paths")

    if not _CC.match(msg):
        return {"ok": False, "agent": "gitcommit", "error": "invalid subject"}

    # Where is the repo mounted inside the container?
    # We default to /git so we can bind-mount your host repo there.
    git_dir = os.getenv("VELU_GIT_DIR", "/git/.git")
    work_tree = os.getenv("VELU_GIT_WORKTREE", "/git")

    git = ["git", f"--git-dir={git_dir}", f"--work-tree={work_tree}"]

    # Make sure this is actually a repo
    rc, _, err = _run(git + ["rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        return {
            "ok": True,
            "agent": "gitcommit",
            "did_commit": False,
            "reason": "no repo",
            "debug": {
                "git_dir": git_dir,
                "work_tree": work_tree,
                "rev_parse_err": err.strip(),
            },
        }

    # Stage changes
    if paths and isinstance(paths, list):
        _run(git + ["add", "--"] + [str(p) for p in paths])
    else:
        _run(git + ["add", "-A"])

    # Check if anything is staged
    rc, _, _ = _run(git + ["diff", "--cached", "--quiet"])
    has_changes = rc != 0  # rc!=0 means there *are* staged changes

    if not has_changes:
        rc_h, head, _ = _run(git + ["rev-parse", "HEAD"])
        return {
            "ok": True,
            "agent": "gitcommit",
            "did_commit": False,
            "reason": "no changes",
            "head": head.strip() if rc_h == 0 else None,
            "subject": msg,
            "debug": {"git_dir": git_dir, "work_tree": work_tree},
        }

    # Commit
    rc, _, err = _run(git + ["commit", "-m", msg])
    if rc != 0:
        return {
            "ok": False,
            "agent": "gitcommit",
            "error": f"commit failed: {err.strip()}",
            "debug": {"git_dir": git_dir, "work_tree": work_tree},
        }

    rc, head, _ = _run(git + ["rev-parse", "HEAD"])
    rc, ls, _ = _run(git + ["diff-tree", "--no-commit-id", "--name-only", "-r", head.strip()])
    files = ls.splitlines() if rc == 0 else []

    return {
        "ok": True,
        "agent": "gitcommit",
        "did_commit": True,
        "head": head.strip(),
        "subject": msg,
        "files": files,
        "debug": {"git_dir": git_dir, "work_tree": work_tree},
    }
