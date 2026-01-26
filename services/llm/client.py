from __future__ import annotations

import os
from typing import Any, Dict, List

# cached OpenAI client (lazy init)
_client_openai: Any | None = None


class RemoteLLMError(Exception):
    """Raised when the remote LLM cannot be used or fails."""

    pass


def _ensure_openai_client() -> Any:
    """
    Lazy-initialize a shared OpenAI client.

    - Does NOT import openai at module import time.
    - Raises RemoteLLMError if the package or API key is missing.
    """
    global _client_openai
    if _client_openai is not None:
        return _client_openai

    try:
        from openai import OpenAI  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RemoteLLMError(
            "The 'openai' package is not installed. " "Install it with: pip install openai"
        ) from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RemoteLLMError("OPENAI_API_KEY not set")

    _client_openai = OpenAI(api_key=api_key)
    return _client_openai


def _chat_openai(
    messages: List[Dict[str, str]],
    model: str | None = None,
    temperature: float | None = None,
) -> str:
    """
    Low-level OpenAI chat wrapper.

    - Uses VELU_CHAT_MODEL and VELU_CHAT_TEMP when model/temperature not passed.
    - Raises RemoteLLMError on configuration / remote issues.
    """
    client = _ensure_openai_client()

    m = model or os.getenv("VELU_CHAT_MODEL") or "gpt-4.1-mini"
    if temperature is None:
        temp_str = os.getenv("VELU_CHAT_TEMP", "0.2")
        try:
            temp = float(temp_str)
        except Exception:
            temp = 0.2
    else:
        temp = float(temperature)

    resp = client.chat.completions.create(
        model=m,
        messages=messages,
        temperature=temp,
    )
    msg = resp.choices[0].message.content
    return msg or ""


def chat(messages: List[Dict[str, str]], model: str | None = None) -> str:
    """
    Existing high-level chat function, kept for backwards compatibility.

    - Uses LLM_PROVIDER (default: openai)
    - Re-raises RemoteLLMError as RuntimeError so existing callers see the
      same exception type as before.
    """
    provider = (os.getenv("LLM_PROVIDER") or "openai").lower()
    if provider == "openai":
        try:
            return _chat_openai(messages, model=model)
        except RemoteLLMError as exc:
            # preserve external behavior (previously raised RuntimeError)
            raise RuntimeError(str(exc)) from exc
    elif provider == "gemini":
        raise RuntimeError("LLM_PROVIDER=gemini not implemented yet")
    else:
        raise RuntimeError(f"Unknown LLM_PROVIDER={provider!r}")


# --- New: Phase 8 remote LLM helper -------------------------------------------


def get_remote_default_model() -> str:
    """
    Default model for remote_llm backend.

    Order:
      1) VELU_REMOTE_LLM_MODEL
      2) VELU_CHAT_MODEL
      3) "gpt-4.1-mini"
    """
    return os.getenv("VELU_REMOTE_LLM_MODEL") or os.getenv("VELU_CHAT_MODEL") or "gpt-4.1-mini"


def remote_chat_completion(
    messages: List[Dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    provider: str | None = None,
) -> str:
    """
    Remote LLM helper used by:
      - assistant backend="remote_llm"
      - generated /v1/ai/chat endpoints (optional)

    - messages: [{"role": "user"|"system"|"assistant", "content": "..."}]
    - model: override the default model if desired
    - temperature: 0.0–1.0
    - provider:
        * None or "openai" -> OpenAI chat.completions.create

    Raises:
      RemoteLLMError for configuration / runtime problems.
    """
    provider_value = (provider or os.getenv("VELU_REMOTE_LLM_PROVIDER") or "openai").lower()

    if provider_value not in {"openai", ""}:
        raise RemoteLLMError(f"Unsupported LLM provider: {provider_value!r}")

    # For now we only support OpenAI; we reuse the same client + wrapper.
    model_name = model or get_remote_default_model()
    return _chat_openai(messages, model=model_name, temperature=temperature)
