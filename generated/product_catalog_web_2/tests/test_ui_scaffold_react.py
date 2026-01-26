from __future__ import annotations

import json
from typing import Any, Dict, List

from services.agents import ui_scaffold


def _get_file(files: List[Dict[str, Any]], path: str) -> str:
    for f in files:
        if f.get("path") == path:
            return str(f.get("content") or "")
    raise AssertionError(f"missing file {path!r} in files")


def test_ui_scaffold_react_spa_created() -> None:
    payload = {
        "idea": "React dashboard",
        "frontend": "react",
        "locales": ["en", "de", "ar"],
    }

    result = ui_scaffold.handle(payload)
    assert result["ok"] is True
    assert result["frontend"] == "react"

    files = result.get("files") or []
    app_src = _get_file(files, "react_spa/src/App.jsx")
    assert "React SPA scaffold" in app_src

    locales_raw = _get_file(files, "react_spa/i18n.locales.json")
    data = json.loads(locales_raw)
    assert data["locales"] == ["en", "de", "ar"]
