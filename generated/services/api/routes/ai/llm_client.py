from __future__ import annotations

from typing import Any, Sequence

from services.llm import client as _client


def remote_chat_completion(
    messages: Sequence[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    return _client.remote_chat_completion(
        messages,
        model=model,
        temperature=temperature,
    )


def get_remote_default_model() -> str:
    return _client.get_remote_default_model()
