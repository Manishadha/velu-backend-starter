from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "services.console.cli", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_cli_version() -> None:
    code, out, err = run_cli(["version"])
    assert code == 0
    assert "Velu CLI" in out


def test_cli_doctor() -> None:
    code, out, err = run_cli(["doctor"])
    assert code == 0
    assert "Velu doctor report" in out
    assert "python_version" in out


def test_cli_list_pipelines() -> None:
    code, out, err = run_cli(["list-pipelines"])
    assert code == 0
    assert "pipelines" in out
