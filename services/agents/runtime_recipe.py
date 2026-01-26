from __future__ import annotations

from typing import Any, Dict, List

from services.agents import runtime_command_planner


def _render_unix_script(project_id: str, services: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("#!/usr/bin/env bash")
    lines.append("set -euo pipefail")
    lines.append("")
    lines.append(f'PROJECT_ID="{project_id}"')
    lines.append("export PROJECT_ID")
    lines.append("")
    for svc in services:
        sid = str(svc.get("id") or "service")
        cmd = str(svc.get("command") or "").strip()
        if not cmd:
            continue
        lines.append(f'echo "Starting {sid}..."')
        lines.append(cmd)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_windows_script(project_id: str, services: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("@echo off")
    lines.append(f"set PROJECT_ID={project_id}")
    lines.append("")
    for svc in services:
        sid = str(svc.get("id") or "service")
        cmd = str(svc.get("command") or "").strip()
        if not cmd:
            continue
        lines.append(f"echo Starting {sid}...")
        lines.append(cmd)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime = payload.get("runtime") or {}
    os_name = str(payload.get("os") or "linux").lower()

    planner_payload = {"runtime": runtime, "os": os_name}
    planner_res = runtime_command_planner.handle(planner_payload)

    services = planner_res.get("services") or []
    if not isinstance(services, list):
        services = []

    project_id = str(runtime.get("project_id") or "project")

    if os_name in ("linux", "darwin", "mac", "macos"):
        script = _render_unix_script(project_id, services)
    else:
        script = _render_windows_script(project_id, services)

    return {
        "ok": True,
        "agent": "runtime_recipe",
        "os": os_name,
        "project_id": project_id,
        "services": services,
        "script": script,
    }
