# services/agents/test_fix_assistant.py
from __future__ import annotations

from typing import Any, Dict, List


def _extract_issues_from_lines(lines: List[str]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("FAILED "):
            continue
        rest = stripped[len("FAILED ") :]
        parts = rest.split(" - ", 1)
        test_path = parts[0].strip()
        message = parts[1].strip() if len(parts) > 1 else ""
        file_path = test_path.split("::", 1)[0]
        issues.append(
            {
                "test": test_path,
                "file": file_path,
                "message": message,
            }
        )
    return issues


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    text = str(payload.get("output") or payload.get("text") or "")
    lines = text.splitlines()
    issues = _extract_issues_from_lines(lines)
    return {
        "ok": True,
        "agent": "test_fix_assistant",
        "issues": issues,
        "summary": {
            "total_issues": len(issues),
        },
    }
