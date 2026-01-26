# tests/unit/test_repo_summary_agent.py
from __future__ import annotations

from pathlib import Path

from services.agents import repo_summary


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_repo_summary_skips_excluded_dirs(tmp_path: Path) -> None:
    root = tmp_path / "r"
    _write(root / "services" / "a.py", "print('x')\n")
    _write(root / "node_modules" / "x.js", "console.log(1)\n")
    _write(root / ".git" / "config", "nope\n")

    out = repo_summary.handle({"root": str(root)})
    assert out["ok"] is True
    stats = out["stats"]
    assert stats["total_files_seen"] == 1
    assert stats["by_ext"].get(".py") == 1


def test_repo_summary_focus_dirs_counts(tmp_path: Path) -> None:
    root = tmp_path / "r"
    _write(root / "services" / "a.py", "print('x')\n")
    _write(root / "tests" / "t.py", "def test_x():\n  assert True\n")
    _write(root / "docs" / "readme.md", "# hi\n")

    out = repo_summary.handle({"root": str(root), "focus_dirs": ["services", "tests"]})
    assert out["ok"] is True
    stats = out["stats"]
    assert stats["focus_dirs"]["services"] == 1
    assert stats["focus_dirs"]["tests"] == 1
    assert "docs" not in stats["focus_dirs"]


def test_repo_summary_snippets_off_by_default(tmp_path: Path) -> None:
    root = tmp_path / "r"
    _write(root / "services" / "a.py", "print('x')\n")

    out = repo_summary.handle({"root": str(root)})
    assert out["ok"] is True
    assert out["snippets"] == []


def test_repo_summary_snippets_on_respects_limits(tmp_path: Path) -> None:
    root = tmp_path / "r"
    _write(root / "services" / "a.py", "print('x')\n" * 200)

    out = repo_summary.handle(
        {
            "root": str(root),
            "focus_dirs": ["services"],
            "include_snippets": True,
            "max_snippets": 1,
            "max_bytes_per_snippet": 50,
        }
    )
    assert out["ok"] is True
    assert len(out["snippets"]) == 1
    assert len(out["snippets"][0]["excerpt"].encode("utf-8")) <= 50


def test_repo_summary_root_missing(tmp_path: Path) -> None:
    out = repo_summary.handle({"root": str(tmp_path / "nope")})
    assert out["ok"] is False
