# services/agents/hospital_apply_patches.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    hospital_apply_patches

    Apply a set of patches produced by hospital_codegen (or similar agents).

    Expected payload:
      {
        "root": ".",          # optional project root (default: ".")
        "patches": {
          "team_dashboard_api.py": {
            "kind": "full_file",
            "path": "team_dashboard_api.py",
            "original_exists": true,
            "content": "..."
          },
          ...
        }
      }

    Behaviour:
      - Only supports kind="full_file".
      - Ensures files are written under the given root (no directory escape).
      - Creates parent directories as needed.
      - Returns updated_files, skipped, and errors.
    """
    root = str(payload.get("root") or ".")
    patches = payload.get("patches") or {}

    if not isinstance(patches, dict):
        return {
            "ok": False,
            "agent": "hospital_apply_patches",
            "error": "invalid patches: expected dict",
        }

    project_root = Path(root).resolve()
    updated_files: List[str] = []
    skipped: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for rel_path, desc in patches.items():
        try:
            rel = Path(str(rel_path))
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "path": rel_path,
                    "error": f"invalid_path: {exc.__class__.__name__}: {exc}",
                }
            )
            continue

        target = (project_root / rel).resolve()
        # prevent writing outside project_root
        try:
            project_root_str = str(project_root)
            target_str = str(target)
            if not target_str.startswith(project_root_str):
                skipped.append(
                    {
                        "path": rel_path,
                        "reason": "outside_root",
                    }
                )
                continue
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "path": rel_path,
                    "error": f"root_check_failed: {exc.__class__.__name__}: {exc}",
                }
            )
            continue

        kind = str((desc or {}).get("kind") or "full_file").lower()
        if kind != "full_file":
            skipped.append(
                {
                    "path": rel_path,
                    "reason": f"unsupported_kind:{kind}",
                }
            )
            continue

        content = (desc or {}).get("content", "")
        if not isinstance(content, str):
            skipped.append(
                {
                    "path": rel_path,
                    "reason": "invalid_content_type",
                }
            )
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            updated_files.append(str(target))
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "path": rel_path,
                    "error": f"write_failed: {exc.__class__.__name__}: {exc}",
                }
            )

    return {
        "ok": not errors,
        "agent": "hospital_apply_patches",
        "root": str(project_root),
        "patch_count": len(patches),
        "updated_files": updated_files,
        "skipped": skipped,
        "errors": errors,
    }
