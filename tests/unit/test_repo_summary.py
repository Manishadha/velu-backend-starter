from pathlib import Path
from services.agents import repo_summary


def test_repo_summary_basic_counts(tmp_path: Path):
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "a.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "services" / "b.py").write_text("print('yo')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# hello\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=abc\n", encoding="utf-8")

    out = repo_summary.handle({"root": str(tmp_path), "include_snippets": False})
    assert out["ok"] is True
    assert out["stats"]["total_files_seen"] == 4
    assert out["stats"]["by_ext"][".py"] == 2
    assert out["languages"]["Python"] == 2
    assert "Markdown" in out["languages"]


def test_repo_summary_snippets_are_limited_and_redacted(tmp_path: Path):
    (tmp_path / "src").mkdir()
    f = tmp_path / "src" / "secrets.py"
    f.write_text("AKIA1234567890ABCDEF\nBearer abcdefghijklmnop\n", encoding="utf-8")

    out = repo_summary.handle(
        {
            "root": str(tmp_path),
            "include_snippets": True,
            "snippet_max_files": 2,
            "snippet_max_bytes_per_file": 200,
            "snippet_max_total_bytes": 200,
            "snippet_redact": True,
        }
    )

    assert out["ok"] is True
    snips = out.get("snippets") or []
    assert len(snips) == 1
    content = snips[0]["content"]
    assert "AKIA" not in content
    assert "Bearer " not in content
    assert "[REDACTED]" in content
