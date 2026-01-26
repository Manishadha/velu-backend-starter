from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """
    Ensure <repo_root>/src is on sys.path for tests and local runs.

    This makes modules like `blog_mod`, `hello_mod`, `team_dashboard`
    importable when they live under src/.
    """
    try:
        repo_root = Path(__file__).resolve().parent
    except Exception:
        return

    src = repo_root / "src"
    src_str = str(src)

    # Only add if it exists and isn't already there
    if src.is_dir() and src_str not in sys.path:
        sys.path.insert(0, src_str)


_ensure_src_on_path()
