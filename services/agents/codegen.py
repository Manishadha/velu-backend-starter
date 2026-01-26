# services/agents/codegen.py
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# ruff: noqa: E501


def _slug(s: str) -> str:
    out = []
    for ch in (s or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    slug = "".join(out).strip("-")
    return slug or "app"


def _python_cli(spec: str, appname: str) -> str:
    """Deterministic Python CLI scaffold."""
    return f"""\
#!/usr/bin/env python3
# hello from codegen: {spec}
from __future__ import annotations

import argparse

def main() -> int:
    parser = argparse.ArgumentParser(prog="{appname}", description="{spec}")
    parser.add_argument("--name", default="world", help="Name to greet")
    args = parser.parse_args()
    print(f"Hello, {{args.name}}!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
"""


def _normalize_args(*args: Any, **kwargs: Any) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Supports:
      - handle(payload)
      - handle(name, payload)
      - handle(None, payload)
    """
    if kwargs and "payload" in kwargs:
        name = kwargs.get("name")
        payload = kwargs.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        return (str(name) if isinstance(name, str) else None, payload)

    if len(args) == 1:
        payload = args[0]
        if not isinstance(payload, dict):
            payload = {}
        return (None, payload)

    if len(args) >= 2:
        name = args[0]
        payload = args[1]
        nm = str(name) if isinstance(name, str) else None
        if not isinstance(payload, dict):
            payload = {}
        return (nm, payload)

    return (None, {})


def handle(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Two supported input shapes:

    1) Spec-based (unit tests use this):
       payload = {"lang": "python", "spec": "..."}
       -> returns {"ok": True, "artifact": {...}, "files":[...]}

    2) Legacy/pipeline-friendly:
       payload = {"idea": "...", "module": "..."}
       -> returns {"ok": True, "files": [...]}
    """
    _name, payload = _normalize_args(*args, **kwargs)

    # -----------------------------
    # Shape 1: language + spec
    # -----------------------------
    if "lang" in payload:
        lang = str(payload.get("lang", "")).lower().strip()
        spec = str(payload.get("spec", "")).strip() or "CLI app"

        if lang != "python":
            return {
                "ok": False,
                "error": f"unsupported lang: {lang}",
                "supported": ["python"],
            }

        fname = _slug(spec)
        path = f"generated/{fname}.py"
        code = _python_cli(spec=spec, appname=fname)

        files = [{"path": path, "content": code}]
        artifact = {"path": path, "language": "python", "code": code}

        return {"ok": True, "agent": "codegen", "artifact": artifact, "files": files}

    # -----------------------------
    # Shape 2: idea + module (pipeline legacy)
    # -----------------------------
    idea = str(payload.get("idea", "")).strip()
    module = str(payload.get("module", "")).strip() or "hello_mod"

    src_path = f"src/{module}.py"
    shim_path = f"{module}.py"
    test_path = f"tests/test_{module}.py"

    msg = idea or "demo"

    src_code = (
        'def greet(name: str = "world") -> str:\n'
        f'    return "{msg} via {module}: " + str(name)\n'
    )

    # Allows `import <module>` even when code lives in src/
    shim_code = "from __future__ import annotations\n" f"from src.{module} import *  # noqa: F403\n"

    test_code = (
        f"from {module} import greet\n\n"
        "def test_greet() -> None:\n"
        '    assert "via" in greet("x")\n'
    )

    files = [
        {"path": "src/__init__.py", "content": ""},  # make src a package
        {"path": src_path, "content": src_code},
        {"path": shim_path, "content": shim_code},
        {"path": test_path, "content": test_code},
    ]

    return {"ok": True, "agent": "codegen", "files": files}
