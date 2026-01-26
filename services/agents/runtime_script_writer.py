from __future__ import annotations

from typing import Any, Dict, List

from services.agents import runtime_recipe


def _normalize_os(raw: Any) -> str:
    v = str(raw or "linux").lower()
    if v in ("darwin", "mac", "macos"):
        return "linux"
    return v


def _script_filename(os_name: str) -> str:
    if os_name == "windows":
        return "run_all.bat"
    return "run_all.sh"


def _join_dir(dir_name: str, filename: str) -> str:
    d = str(dir_name or "").strip()
    if not d or d == ".":
        return filename
    if d.endswith("/"):
        return d + filename
    return d + "/" + filename


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime = payload.get("runtime") or {}
    os_name = _normalize_os(payload.get("os"))
    output_dir = str(payload.get("output_dir") or ".").strip() or "."

    recipe_payload = {"runtime": runtime, "os": os_name}
    recipe_res = runtime_recipe.handle(recipe_payload)

    script = str(recipe_res.get("script") or "")
    project_id = str(recipe_res.get("project_id") or runtime.get("project_id") or "project")

    filename = _script_filename(os_name)
    script_path = _join_dir(output_dir, filename)

    files: List[Dict[str, str]] = []
    files.append({"path": script_path, "content": script})

    return {
        "ok": True,
        "agent": "runtime_script_writer",
        "os": os_name,
        "project_id": project_id,
        "script_path": script_path,
        "files": files,
    }
