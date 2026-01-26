# tests/test_hospital_apply_patches.py
from __future__ import annotations

from pathlib import Path

from services.agents import hospital_apply_patches


def test_hospital_apply_patches_writes_full_file(tmp_path: Path) -> None:
    """
    Basic happy-path test:

    - uses a temporary root directory
    - applies a single full_file patch
    - asserts that the file is written with the expected content
    """
    root = str(tmp_path)
    rel_path = "subdir/test_file.txt"
    content = "hello from hospital_apply_patches\n"

    payload = {
        "root": root,
        "patches": {
            rel_path: {
                "kind": "full_file",
                "path": rel_path,
                "original_exists": False,
                "content": content,
            }
        },
    }

    result = hospital_apply_patches.handle(payload)

    assert result["ok"] is True
    assert result["agent"] == "hospital_apply_patches"
    assert result["patch_count"] == 1

    # file should be written under the tmp_path root
    target = tmp_path / rel_path
    assert target.exists()
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == content

    # updated_files should include the absolute path to the written file
    assert str(target) in result["updated_files"]
    assert result["errors"] == []


def test_hospital_apply_patches_invalid_patches(tmp_path: Path) -> None:
    """
    When 'patches' is not a dict, the agent should return ok=False
    with an explanatory error and not write anything.
    """
    root = str(tmp_path)

    payload = {
        "root": root,
        "patches": "not-a-dict",
    }

    result = hospital_apply_patches.handle(payload)

    assert result["ok"] is False
    assert result["agent"] == "hospital_apply_patches"
    assert "invalid patches" in str(result.get("error", "")).lower()
