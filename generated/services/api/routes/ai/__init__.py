from __future__ import annotations

import os
from typing import Literal, Sequence

from fastapi import APIRouter
from pydantic import BaseModel

from . import llm_client


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str


class ChatRequest(BaseModel):
    messages: Sequence[ChatMessage]
    backend: Literal["stub", "remote_llm"] | None = None
    model: str | None = None


class ChatResponse(BaseModel):
    reply: str


class SummarizeRequest(BaseModel):
    text: str
    backend: Literal["stub", "remote_llm"] | None = None
    model: str | None = None


class SummarizeResponse(BaseModel):
    summary: str


class ModelsResponse(BaseModel):
    provider: str
    default_model: str


router = APIRouter(prefix="/v1/ai", tags=["ai"])


def _stub_chat_reply(req: ChatRequest) -> str:
    last = req.messages[-1].content if req.messages else ""
    return last or "ai reply placeholder"


def _stub_summary(text: str) -> str:
    t = text.strip()
    if not t:
        return ""
    return t if len(t) <= 280 else t[:277] + "..."


def _remote_chat_reply(req: ChatRequest) -> str:
    if not req.messages:
        return _stub_chat_reply(req)
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        reply = llm_client.remote_chat_completion(
            messages,
            model=req.model,
            temperature=0.2,
        ).strip()
    except Exception:
        reply = ""
    return reply or _stub_chat_reply(req)


def _remote_summary(req: SummarizeRequest) -> str:
    text = req.text.strip()
    if not text:
        return ""
    messages = [
        {
            "role": "system",
            "content": (
                "Summarize the user text in at most 3 short sentences. "
                "Keep the main meaning and avoid adding new information."
            ),
        },
        {
            "role": "user",
            "content": text,
        },
    ]
    try:
        reply = llm_client.remote_chat_completion(
            messages,
            model=req.model,
            temperature=0.2,
        ).strip()
    except Exception:
        reply = ""
    return reply or _stub_summary(text)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    backend = (req.backend or "stub").lower()
    if backend == "remote_llm":
        reply = _remote_chat_reply(req)
    else:
        reply = _stub_chat_reply(req)
    return ChatResponse(reply=reply)


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest) -> SummarizeResponse:
    backend = (req.backend or "stub").lower()
    if backend == "remote_llm":
        summary = _remote_summary(req)
    else:
        summary = _stub_summary(req.text)
    return SummarizeResponse(summary=summary)


@router.get("/models", response_model=ModelsResponse)
async def models() -> ModelsResponse:
    provider = (os.getenv("VELU_REMOTE_LLM_PROVIDER") or "openai").lower()
    default_model = llm_client.get_remote_default_model()
    return ModelsResponse(provider=provider, default_model=default_model)
