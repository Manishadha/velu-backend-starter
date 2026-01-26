from __future__ import annotations

import json

from services.agents import ui_scaffold


def test_ui_scaffold_uses_product_locales_for_web():
    payload = {
        "frontend": "nextjs",
        "product": {
            "locales": ["en", "de", "ja"],
        },
    }
    res = ui_scaffold.handle(payload)
    files = {f["path"]: f["content"] for f in res["files"]}

    cfg = json.loads(files["web/i18n.locales.json"])
    assert cfg["locales"] == ["en", "de", "ja"]


def test_ui_scaffold_uses_product_locales_for_react_spa():
    payload = {
        "frontend": "react",
        "product": {
            "locales": ["en", "es", "pt"],
        },
    }
    res = ui_scaffold.handle(payload)
    files = {f["path"]: f["content"] for f in res["files"]}

    cfg_web = json.loads(files["web/i18n.locales.json"])
    cfg_spa = json.loads(files["react_spa/i18n.locales.json"])

    assert cfg_web["locales"] == ["en", "es", "pt"]
    assert cfg_spa["locales"] == ["en", "es", "pt"]
