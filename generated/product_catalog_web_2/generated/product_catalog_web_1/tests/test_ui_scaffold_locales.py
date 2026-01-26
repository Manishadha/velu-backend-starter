from __future__ import annotations

import json
from typing import Any, Dict, List

from services.agents import ui_scaffold


def _get_file(files: List[Dict[str, Any]], path: str) -> str:
    for f in files:
        if f.get("path") == path:
            return str(f.get("content") or "")
    raise AssertionError(f"missing file {path!r} in files")


def test_ui_scaffold_writes_locales_file() -> None:
    payload = {"idea": "Demo", "frontend": "nextjs"}
    result = ui_scaffold.handle(payload)
    files = result.get("files") or []
    raw = _get_file(files, "web/i18n.locales.json")
    data = json.loads(raw)
    assert isinstance(data.get("locales"), list)


def test_ui_scaffold_defaults_to_global_locale_list() -> None:
    payload = {"idea": "Demo default locale", "frontend": "nextjs"}
    result = ui_scaffold.handle(payload)
    files = result.get("files") or []
    raw = _get_file(files, "web/i18n.locales.json")
    data = json.loads(raw)
    assert data["locales"] == ["en", "fr", "nl", "de", "ar", "ta"]


def test_ui_scaffold_respects_payload_locales() -> None:
    payload = {"idea": "Custom locales", "frontend": "nextjs", "locales": ["en", "es"]}
    result = ui_scaffold.handle(payload)
    files = result.get("files") or []
    raw = _get_file(files, "web/i18n.locales.json")
    data = json.loads(raw)
    assert data["locales"] == ["en", "es"]
