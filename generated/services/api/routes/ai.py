from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/ai", tags=["ai"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


@router.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    last = req.messages[-1].content if req.messages else ""
    return {"reply": last or "hello"}


class SummarizeRequest(BaseModel):
    text: str


@router.post("/summarize")
async def summarize(req: SummarizeRequest) -> Dict[str, Any]:
    text = req.text or ""
    if not text:
        return {"summary": ""}
    short = text[:200]
    if len(text) > 200:
        short += "…"
    return {"summary": short}
