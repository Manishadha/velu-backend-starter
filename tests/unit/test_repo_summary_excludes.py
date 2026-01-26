from pathlib import Path
from services.agents import repo_summary


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_repo_summary_excludes_noise(tmp_path: Path) -> None:
    root = tmp_path / "r"
    _write(root / "services" / "a.py", "print('x')\n")
    _write(root / "node_modules" / "x.js", "console.log(1)\n")
    _write(root / ".git" / "config", "nope\n")

    out = repo_summary.handle({"root": str(root)})
    assert out["ok"] is True
    assert out["stats"]["total_files_seen"] == 1
