# services/agents/debug_pipeline.py
from __future__ import annotations

from typing import Any, Dict, List

from . import ai_architect
from . import code_refiner
from . import test_fix_assistant


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _build_problem_from_issues(issues: List[Dict[str, Any]]) -> str:
    if not issues:
        return ""
    lines: List[str] = []
    for issue in issues:
        t = _as_str(issue.get("test")).strip()
        m = _as_str(issue.get("message")).strip()
        if t and m:
            lines.append(f"{t} - {m}")
        elif t:
            lines.append(t)
        elif m:
            lines.append(m)
    if not lines:
        return ""
    return "Test failures detected:\n" + "\n".join(lines)


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    test_text = _as_str(payload.get("test_output") or payload.get("output") or payload.get("text"))

    test_result = test_fix_assistant.handle({"output": test_text})
    issues: List[Dict[str, Any]] = list(test_result.get("issues") or [])

    refiner_result: Dict[str, Any] | None = None
    code_value = payload.get("code")
    if isinstance(code_value, str) and code_value.strip():
        ref_payload: Dict[str, Any] = {"code": code_value}
        if "language" in payload:
            ref_payload["language"] = payload["language"]
        if "path" in payload:
            ref_payload["path"] = payload["path"]
        refiner_result = code_refiner.handle(ref_payload)

    architect_result: Dict[str, Any] | None = None
    problem_text = _build_problem_from_issues(issues)
    if problem_text:
        architect_result = ai_architect.handle({"problem": problem_text})

    return {
        "ok": True,
        "agent": "debug_pipeline",
        "issues": issues,
        "test_analysis": test_result,
        "refiner": refiner_result,
        "analysis": architect_result,
    }
