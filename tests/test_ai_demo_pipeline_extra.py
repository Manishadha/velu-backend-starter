from __future__ import annotations

from ai_demo import greet


def test_greet_pipeline_extra() -> None:
    out = greet("Velu")
    assert isinstance(out, str)
    assert "Velu" in out
