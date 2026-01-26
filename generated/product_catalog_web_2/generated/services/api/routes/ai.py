# generated/services/api/routes/ai.py (TEMPLATE FOR ZIPs)
from __future__ import annotations

from typing import Literal, Sequence

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/v1/ai", tags=["ai"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str


class ChatRequest(BaseModel):
    messages: Sequence[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    last = req.messages[-1].content if req.messages else ""
    if not last:
        reply = "Hello, I’m the demo AI endpoint from your packaged project."
    else:
        reply = f"You said: {last}"
    return ChatResponse(reply=reply)
