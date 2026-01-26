from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel


class LocalesResponse(BaseModel):
    locales: List[str]


router = APIRouter(prefix="/v1/i18n", tags=["i18n"])

DEFAULT_LOCALES = ["en", "fr", "nl", "de", "ar", "ta"]


@router.get("/locales", response_model=LocalesResponse)
async def get_locales() -> LocalesResponse:
    return LocalesResponse(locales=DEFAULT_LOCALES)
