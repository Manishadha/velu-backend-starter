from __future__ import annotations

import subprocess  # nosec B404 - only used to run pytest on this repository
import sys
from typing import Any, Dict, List

from services.agents import debug_pipeline


def _run_pytest(args: List[str]) -> tuple[int, str]:
    proc = subprocess.run(  # nosec B603 - arguments are fixed pytest CLI, not user-controlled
        [sys.executable, "-m", "pytest", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.returncode, proc.stdout


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def main(argv: List[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    code, output = _run_pytest(argv)
    result: Dict[str, Any] = debug_pipeline.handle({"output": output})

    sys.stdout.write(output)
    sys.stdout.write("\n\n=== Velu debug analysis ===\n")

    if not result.get("ok"):
        sys.stdout.write("No analysis available.\n")
        return code

    issues = result.get("issues") or []
    summary = (result.get("test_analysis") or {}).get("summary") or {}
    total_issues = _as_int(summary.get("total_issues"), len(issues))

    sys.stdout.write(f"Total issues detected: {total_issues}\n")

    if not issues:
        sys.stdout.write("All tests passing or no failures parsed.\n")
        return code

    for issue in issues:
        t = str(issue.get("test") or "").strip()
        msg = str(issue.get("message") or "").strip()
        if t and msg:
            sys.stdout.write(f"- {t}: {msg}\n")
        elif t:
            sys.stdout.write(f"- {t}\n")
        elif msg:
            sys.stdout.write(f"- {msg}\n")

    return code


if __name__ == "__main__":
    raise SystemExit(main())
