#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import pathlib

EXCLUDE = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".cache",
    ".DS_Store",
    ".idea",
    ".vscode",
    ".pnpm-store",
    ".next",
    ".turbo",
    ".nyc_output",
    ".coverage",
    "coverage.xml",
}
NOTES = {
    "services": "core services",
    "services/app_server": "FastAPI API",
    "services/agents": "agents",
    "services/queue": "job queue",
    "velu-console": "console UI",
    "templates": "code templates",
    "configs": "configs",
    "ops": "ops",
    "docs": "docs",
    "tests": "tests",
    "data": "runtime data",
    "ui": "static UI",
    "orchestrator": "orchestrator",
    "monitoring": "monitoring",
    "web": "generated web",
}


def skip(rel: pathlib.Path) -> bool:
    return any(p in EXCLUDE for p in rel.parts)


def note_for(rel: pathlib.Path) -> str:
    s = rel.as_posix()
    return NOTES.get(s, NOTES.get(s.split("/", 1)[0], ""))


def write_tree(root: pathlib.Path, out_path: pathlib.Path) -> None:
    lines = []
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"# tree snapshot @ {ts}")
    lines.append("./")
    for dirpath, dirnames, filenames in os.walk(root):
        dp = pathlib.Path(dirpath)
        rel = dp.relative_to(root)
        if rel != pathlib.Path(".") and skip(rel):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in sorted(dirnames) if not skip(rel / d)]
        filenames = [f for f in sorted(filenames) if not skip(rel / f)]
        depth = 0 if rel == pathlib.Path(".") else len(rel.parts)
        indent = "  " * depth
        name = "." if rel == pathlib.Path(".") else rel.name
        nf = note_for(rel)
        lines.append(f"{indent}{name}/" + (f"  # {nf}" if nf else ""))
        for f in filenames:
            lines.append(f"{indent}  {f}")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repo_root = pathlib.Path(".").resolve()
    out_repo = repo_root / "docs" / "TREE_REPO.txt"
    out_repo.parent.mkdir(parents=True, exist_ok=True)
    write_tree(repo_root, out_repo)

    # Optional host snapshot path env override (when running on host mount)
    host_root = pathlib.Path(os.environ.get("VELU_HOST_ROOT", "/opt/velu"))
    if host_root.exists():
        out_host = repo_root / "docs" / "TREE_HOST.txt"
        write_tree(host_root.resolve(), out_host)

    print("wrote: docs/TREE_REPO.txt")
    if host_root.exists():
        print("wrote: docs/TREE_HOST.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
