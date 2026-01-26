from __future__ import annotations

from fastapi.testclient import TestClient

from generated.services.api.app import app


client = TestClient(app)


def test_ai_chat_echoes_last_message() -> None:
    payload = {
        "messages": [
            {"role": "user", "content": "hello from velu ai demo"},
        ]
    }
    r = client.post("/v1/ai/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("reply") == "hello from velu ai demo"


def test_ai_chat_empty_messages() -> None:
    r = client.post("/v1/ai/chat", json={"messages": []})
    assert r.status_code == 200
    data = r.json()
    assert data.get("reply") in ("", "ai reply placeholder")


def test_ai_summarize_basic() -> None:
    text = "this is some long text that should be summarized by the ai stub endpoint"
    r = client.post("/v1/ai/summarize", json={"text": text})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("summary"), str)
    assert len(data["summary"]) > 0


def test_ai_summarize_empty() -> None:
    r = client.post("/v1/ai/summarize", json={"text": ""})
    assert r.status_code == 200
    data = r.json()
    assert data.get("summary") == ""


def test_ai_models_basic(monkeypatch) -> None:
    monkeypatch.delenv("VELU_REMOTE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("VELU_REMOTE_LLM_MODEL", raising=False)
    monkeypatch.delenv("VELU_CHAT_MODEL", raising=False)

    r = client.get("/v1/ai/models")
    assert r.status_code == 200
    data = r.json()

    assert data.get("provider") == "openai"
    assert isinstance(data.get("default_model"), str)
    assert data["default_model"]


def test_ai_chat_remote_backend_uses_remote(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_remote(messages, model=None, temperature=0.2):
        calls["messages"] = messages
        calls["model"] = model
        calls["temperature"] = temperature
        return "remote says hi"

    monkeypatch.setattr(
        "generated.services.api.routes.ai.llm_client.remote_chat_completion",
        fake_remote,
    )

    payload = {
        "messages": [
            {"role": "user", "content": "hello via remote"},
        ],
        "backend": "remote_llm",
        "model": "test-model",
    }
    r = client.post("/v1/ai/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "remote says hi"

    sent = calls["messages"]
    assert isinstance(sent, list)
    assert sent[-1]["content"] == "hello via remote"


def test_ai_chat_remote_backend_fallback_on_error(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "generated.services.api.routes.ai.llm_client.remote_chat_completion",
        boom,
    )

    payload = {
        "messages": [
            {"role": "user", "content": "hello from velu ai demo"},
        ],
        "backend": "remote_llm",
    }
    r = client.post("/v1/ai/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["reply"] == "hello from velu ai demo"


def test_ai_summarize_remote_backend_uses_remote(monkeypatch) -> None:
    def fake_remote(messages, model=None, temperature=0.2):
        return "short remote summary"

    monkeypatch.setattr(
        "generated.services.api.routes.ai.llm_client.remote_chat_completion",
        fake_remote,
    )

    text = "this is some long text that should be summarized"
    r = client.post(
        "/v1/ai/summarize",
        json={"text": text, "backend": "remote_llm"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["summary"] == "short remote summary"


def test_ai_summarize_remote_backend_fallback_on_error(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "generated.services.api.routes.ai.llm_client.remote_chat_completion",
        boom,
    )

    text = "short text for fallback summary"
    r = client.post(
        "/v1/ai/summarize",
        json={"text": text, "backend": "remote_llm"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["summary"] == text
