# tests/test_multilingual_pipeline.py
from __future__ import annotations

from services.agents import pipeline


def test_pipeline_carries_user_language_and_locales() -> None:
    payload = {
        "idea": "Inventory app",
        "module": "inventory_mod",
        "frontend": "nextjs",
        "backend": "fastapi",
        "database": "sqlite",
        "kind": "web_app",
        "schema": {},
        "locales": ["en", "fr", "ta-IN"],
        "user_language": "fr",
        "original_text_language": "ta-IN",
    }

    res = pipeline.handle(payload)
    assert res["ok"] is True
    assert res["agent"] == "pipeline"

    out = res.get("payload") or {}
    # Existing fields still present
    assert out["idea"] == "Inventory app"
    assert out["module"] == "inventory_mod"
    assert out["frontend"] == "nextjs"
    assert out["backend"] == "fastapi"
    assert out["database"] == "sqlite"
    assert out["kind"] == "web_app"

    # Locales preserved
    assert out["locales"] == ["en", "fr", "ta-IN"]

    # New language hints are carried through (when provided)
    assert out["user_language"] == "fr"
    assert out["original_text_language"] == "ta-IN"
