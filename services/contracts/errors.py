# services/contracts/errors.py
from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: Optional[dict[str, Any]] = None
    trace: Optional[str] = None


def error(code: str, message: str, details: Any = None, trace: str | None = None) -> dict[str, Any]:
    det: Optional[dict[str, Any]]
    if details is None:
        det = None
    elif isinstance(details, dict):
        det = details
    else:
        try:
            json.dumps(details, ensure_ascii=False)
            det = {"value": details}
        except Exception:
            det = {"value": str(details)}
    return ErrorEnvelope(code=code, message=message, details=det, trace=trace).model_dump(exclude_none=True)
