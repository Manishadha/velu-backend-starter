#!/usr/bin/env python3
from __future__ import annotations

import shlex
from pathlib import Path


def main() -> int:
    p = Path("/bootstrap/test_api_keys.env")
    if not p.exists():
        raise SystemExit("ERROR: /bootstrap/test_api_keys.env missing")

    lines: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip().replace("\r", "")
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
            v = v[1:-1]
        lines.append(f"export {k}={shlex.quote(v)}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
