from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """
    Ensure <repo_root>/src is on sys.path so tests can import modules like
    `blog_mod`, `hello_mod`, `team_dashboard`, etc.
    """
    try:
        repo_root = Path(__file__).resolve().parent
    except Exception:
        return

    src = repo_root / "src"
    if src.is_dir():
        src_str = str(src)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


_ensure_src_on_path()
