from __future__ import annotations

import os
from typing import Any, Dict, List  # noqa: F401


def remote_chat_completion(
    messages: List[Dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    """
    Very small stub used by the generated API.

    It just echoes the last user message so that:
    - /v1/ai/chat
    - the AI-related tests

    can run without a real remote LLM or OPENAI_API_KEY.
    """
    last_user = ""
    for m in reversed(messages or []):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break

    if not last_user and messages:
        last_user = messages[-1].get("content", "")

    text = (last_user or "").strip()
    if not text:
        return "ai reply placeholder"

    # keep it deterministic and short
    if len(text) > 400:
        text = text[:397] + "..."
    return f"echo: {text}"


def get_remote_default_model() -> str:
    """
    Used by /v1/ai/models to report a default model name.
    """
    return os.getenv("VELU_REMOTE_LLM_MODEL") or "gpt-4.1-mini"
