from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(path_str: str) -> Path:
    p = Path(str(path_str))
    if p.is_absolute():
        return p
    return (_root() / p).resolve()


def _safe_read(path: Path) -> str | None:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        return None
    return None


def _check_markers(content: str | None, markers: List[str]) -> Dict[str, Any]:
    if content is None:
        return {
            "exists": False,
            "present": [],
            "missing": markers,
        }

    present = [m for m in markers if m in content]
    missing = [m for m in markers if m not in content]
    return {
        "exists": True,
        "present": present,
        "missing": missing,
    }


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    spec = payload.get("spec") or {}
    apply_flag = bool(payload.get("apply", False))

    raw_targets = payload.get("target_files") or [
        "team_dashboard_api.py",
        "tests/test_team_dashboard_api.py",
    ]
    target_files: List[str] = [str(p) for p in raw_targets]

    project = spec.get("project", {}) or {}
    features = spec.get("features", {}) or {}
    modules: List[str] = features.get("modules", []) or []

    api_markers: Dict[str, List[str]] = {
        "patients": [
            '@app.get("/patients"',
            "class Patient(",
            "def list_patients",
        ],
        "appointments": [
            '@app.get("/appointments"',
            "class Appointment(",
            "def list_appointments",
            '@app.get("/appointments/summary"',
        ],
        "doctors": [
            '@app.get("/doctors"',
            "class Doctor(",
        ],
        "dashboard": [
            '@app.get("/dashboard/overview"',
        ],
    }

    test_markers: Dict[str, List[str]] = {
        "patients": [
            "test_list_patients",
            "test_get_patient_by_id_ok",
            "test_create_patient",
        ],
        "appointments": [
            "test_list_appointments_basic",
            "test_create_appointment",
            "test_get_appointment_by_id_ok",
            "test_appointments_summary",
            "test_cancel_appointment",
        ],
        "doctors": [
            "test_list_doctors_ok",
            "test_get_doctor_by_id_ok",
            "test_get_doctor_by_id_not_found",
        ],
        "dashboard": [
            "test_dashboard_overview",
        ],
    }

    analysis: Dict[str, Any] = {}

    for path_str in target_files:
        path = _resolve(path_str)
        content = _safe_read(path)

        if "test_team_dashboard_api.py" in path_str:
            markers_table = test_markers
        else:
            markers_table = api_markers

        modules_info: Dict[str, Any] = {}
        for mod in modules:
            markers = markers_table.get(mod, [])
            modules_info[mod] = _check_markers(content, markers)

        analysis[path_str] = {
            "modules": modules_info,
            "exists": content is not None,
        }

    proj_name = project.get("name") or project.get("id") or "hospital_app"
    proj_type = project.get("type", "web_app")
    frontend = (spec.get("stack") or {}).get("frontend", {}) or {}
    backend = (spec.get("stack") or {}).get("backend", {}) or {}
    database = (spec.get("stack") or {}).get("database", {}) or {}

    summary_lines = [
        f"Project: {proj_name} ({proj_type})",
        f"Frontend: {frontend.get('framework', 'unknown')} / {frontend.get('language', 'unknown')}",
        f"Backend: {backend.get('framework', 'unknown')} / {backend.get('language', 'unknown')}",
        f"Database: {database.get('engine', 'unknown')} ({database.get('mode', 'unknown')})",
        f"Modules requested: {', '.join(modules) or 'none'}",
        "Mode: plan_only (no direct writes by this agent)",
    ]

    patches: Dict[str, Any] = {}
    if apply_flag:
        for path_str in target_files:
            path = _resolve(path_str)
            content = _safe_read(path)
            patches[path_str] = {
                "kind": "full_file",
                "path": path_str,
                "original_exists": content is not None,
                "content": content or "",
            }

        summary_lines.append(
            "NOTE: apply=true requested; full-file patches prepared but not applied."
        )

    result: Dict[str, Any] = {
        "ok": True,
        "agent": "hospital_codegen",
        "mode": "plan_only",
        "summary": "\n".join(summary_lines),
        "spec": spec,
        "analysis": analysis,
    }

    if patches:
        result["patches"] = patches

    return result
