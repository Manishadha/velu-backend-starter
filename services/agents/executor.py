# services/agents/executor.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _check_path(rel: str) -> Tuple[bool, str | None]:
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

    # Allowed roots ONLY:
    if not (rel.startswith("src/") or rel.startswith("tests/")):
        return False, "outside allowed roots (src/, tests/)"

    return True, None


def _load_files_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    files = payload.get("files")

    # Normal case: list[dict]
    if isinstance(files, list):
        out: List[Dict[str, Any]] = []
        for it in files:
            if isinstance(it, dict):
                out.append(it)
        return out

    # Fallback: files_json is a JSON string
    fj = payload.get("files_json")
    if isinstance(fj, str) and fj.strip():
        try:
            parsed = json.loads(fj)
            if isinstance(parsed, list):
                out2: List[Dict[str, Any]] = []
                for it in parsed:
                    if isinstance(it, dict):
                        out2.append(it)
                return out2
        except Exception:
            return []

    return []


def _seed_default_files(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    If the pipeline didn't provide files, seed a minimal project under
    allowed roots so `pytest tests` can run.
    """
    module = str(payload.get("module") or "hello_mod").strip() or "hello_mod"

    return [
        {
            "path": f"src/{module}.py",
            "content": (
                "def greet(name: str) -> str:\n"
                '    """Simple greeter used by smoke tests."""\n'
                '    return f"Hello, {name}!"\n'
            ),
        },
        {
            "path": f"tests/test_{module}.py",
            "content": (
                f"from {module} import greet\n\n"
                "def test_greet_pipeline():\n"
                '    assert greet("Velu") == "Hello, Velu!"\n'
            ),
        },
    ]


# accept either handle(payload) or handle(name, payload) depending on caller
def handle(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    if len(args) == 1 and isinstance(args[0], dict):
        payload = dict(args[0] or {})
    elif len(args) >= 2 and isinstance(args[1], dict):
        payload = dict(args[1] or {})
    else:
        payload = dict(kwargs.get("payload") or {})

    base = Path.cwd()

    files = _load_files_from_payload(payload)
    seeded = False
    if not files:
        files = _seed_default_files(payload)
        seeded = True

    wrote: List[str] = []
    refused: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []

    for item in files:
        rel_path = str(item.get("path", "")).strip()
        content = item.get("content", "")

        is_safe, reason = _check_path(rel_path)
        if not is_safe:
            refused.append({"path": rel_path, "reason": reason or "invalid path"})
            continue

        try:
            dst = (base / rel_path).resolve()

            # Ensure it stays inside workspace
            try:
                dst.relative_to(base.resolve())
            except Exception:
                refused.append({"path": rel_path, "reason": "escaped workspace"})
                continue

            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(str(content), encoding="utf-8")
            wrote.append(rel_path)
        except Exception as e:
            errors.append({"path": rel_path, "error": f"{type(e).__name__}: {e}"})

    # IMPORTANT: keep old keys so nothing else breaks
    return {
        "ok": True,
        "agent": "execute",
        "seeded": seeded,
        "cwd": str(base),
        "base_dir": str(base),
        "wrote": wrote,
        "refused": refused,
        "errors": errors or None,
    }
