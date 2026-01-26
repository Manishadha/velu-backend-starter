from __future__ import annotations

from src.velu_console_assistant import format_help


def test_format_help_contains_core_commands() -> None:
    text = format_help()
    # sanity checks: about exact wording, just that
    # the key commands are documented.
    assert "edit <rule>" in text
    assert "ai <rule>" in text
    assert "undo" in text
    assert "redo" in text
    assert "history" in text
    assert "export" in text
    assert "packager" in text or "Run packager" in text
