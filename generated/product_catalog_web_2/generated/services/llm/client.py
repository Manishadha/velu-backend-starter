from __future__ import annotations

from typing import Dict, List


def get_remote_default_model() -> str:
    return "gpt-4.1-mini"


def remote_chat_completion(
    messages: List[Dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    if not messages:
        return ""
    last = messages[-1].get("content") or ""
    return last or "ai reply placeholder"
