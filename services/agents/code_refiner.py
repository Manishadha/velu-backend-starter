# services/agents/code_refiner.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_trailing_whitespace(text: str) -> str:
    lines = text.split("\n")
    stripped = [line.rstrip(" \t") for line in lines]
    return "\n".join(stripped)


def _ensure_final_newline(text: str) -> str:
    if text == "":
        return text
    if text.endswith("\n"):
        while text.endswith("\n\n"):
            text = text[:-1]
        return text
    return text + "\n"


def _refine_content(content: str) -> Tuple[str, bool]:
    original = content
    text = _normalize_newlines(original)
    text = _strip_trailing_whitespace(text)
    text = _ensure_final_newline(text)
    changed = text != original
    return text, changed


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_files = payload.get("files") or []
    files: List[Dict[str, str]] = []
    changed_count = 0

    for item in raw_files:
        path = str(item.get("path") or "")
        content = str(item.get("content") or "")
        refined, changed = _refine_content(content)
        if changed:
            changed_count += 1
        files.append(
            {
                "path": path,
                "content": refined,
            }
        )

    return {
        "ok": True,
        "agent": "code_refiner",
        "files": files,
        "summary": {
            "total_files": len(files),
            "changed_files": changed_count,
        },
    }
