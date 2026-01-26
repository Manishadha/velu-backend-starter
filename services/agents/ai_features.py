from __future__ import annotations

from typing import Any, Literal, Sequence

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str


class ChatRequest(BaseModel):
    messages: Sequence[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


class SummarizeRequest(BaseModel):
    text: str


class SummarizeResponse(BaseModel):
    summary: str


def _ai_enabled(payload: dict[str, Any]) -> bool:
    features = payload.get("features")
    if isinstance(features, dict):
        ai_cfg = features.get("ai")
        if isinstance(ai_cfg, dict):
            if any(bool(ai_cfg.get(k)) for k in ("assist", "summarize", "chat")):
                return True

    spec = payload.get("spec")
    if isinstance(spec, dict):
        feats = spec.get("features")
        if isinstance(feats, dict):
            ai_cfg = feats.get("ai")
            if isinstance(ai_cfg, dict):
                if any(bool(ai_cfg.get(k)) for k in ("assist", "summarize", "chat")):
                    return True

    return True


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    if not _ai_enabled(payload):
        return {
            "ok": True,
            "agent": "ai_features",
            "files": [],
            "note": "ai disabled in spec",
        }

    code = """
from __future__ import annotations

from typing import Literal, Sequence

from fastapi import APIRouter
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str


class ChatRequest(BaseModel):
    messages: Sequence[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


class SummarizeRequest(BaseModel):
    text: str


class SummarizeResponse(BaseModel):
    summary: str


router = APIRouter(prefix="/v1/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    last = req.messages[-1].content if req.messages else ""
    reply = last or "ai reply placeholder"
    return ChatResponse(reply=reply)


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest) -> SummarizeResponse:
    text = req.text.strip()
    if not text:
        return SummarizeResponse(summary="")
    summary = text if len(text) <= 280 else text[:277] + "..."
    return SummarizeResponse(summary=summary)
""".lstrip()

    files = [
        {
            "path": "generated/services/api/routes/ai.py",
            "content": code,
        }
    ]

    return {"ok": True, "agent": "ai_features", "files": files}
