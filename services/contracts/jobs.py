from __future__ import annotations

import json
from typing import Any, Literal, Mapping, Optional, Tuple

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "working", "done", "error", "cancelled"]


class JobCreate(BaseModel):
    task: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobCreateResponse(BaseModel):
    ok: bool = True
    job_id: str = Field(min_length=1)


class JobReadResponse(BaseModel):
    ok: bool = True
    item: dict[str, Any]


_MAX_STR = 20000
_MAX_LIST = 2000
_MAX_DICT_KEYS = 2000
_MAX_FILE_CONTENT = 20000
_MAX_FILES = 500


def _clip_str(s: str, limit: int) -> str:
    s = s or ""
    return s if len(s) <= limit else (s[:limit] + "…(truncated)…")


def sanitize_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _clip_str(value, _MAX_STR)
    if isinstance(value, (bytes, bytearray)):
        return _clip_str(value.decode("utf-8", errors="replace"), _MAX_STR)
    if isinstance(value, list):
        return [sanitize_json(x) for x in value[:_MAX_LIST]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        items = list(value.items())[:_MAX_DICT_KEYS]
        for k, v in items:
            ks = str(k)
            if ks == "files" and isinstance(v, list):
                kept: list[dict[str, Any]] = []
                for item in v[:_MAX_FILES]:
                    if isinstance(item, dict):
                        kept.append(
                            {
                                "path": _clip_str(str(item.get("path", "")), 500),
                                "content": _clip_str(str(item.get("content", "")), _MAX_FILE_CONTENT),
                            }
                        )
                out["files"] = kept
                continue
            if ks == "files_json" and isinstance(v, str):
                out["files_json"] = _clip_str(v, _MAX_STR)
                continue
            out[ks] = sanitize_json(v)
        return out
    try:
        return {"raw": _clip_str(str(value), _MAX_STR)}
    except Exception:
        return {"raw": "<unserializable>"}


def dumps_json(value: Any) -> str:
    return json.dumps(sanitize_json(value), ensure_ascii=False)


def loads_json_maybe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8", errors="ignore")
        except Exception:
            return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return value
        try:
            return json.loads(s)
        except Exception:
            return value
    return value


def decode_task_and_payload(raw_task: Any, raw_payload: Any) -> Tuple[Optional[str], dict[str, Any]]:
    task_name: Optional[str] = None
    payload: dict[str, Any] = {}

    if isinstance(raw_task, dict):
        task_name = raw_task.get("task")
        pl = raw_task.get("payload")
        if isinstance(pl, dict):
            payload = pl
    else:
        if isinstance(raw_task, (bytes, bytearray)):
            try:
                raw_task = raw_task.decode("utf-8", errors="ignore")
            except Exception:
                raw_task = ""
        if isinstance(raw_task, str):
            s = raw_task.strip()
            if s.startswith("{") and s.endswith("}"):
                obj = loads_json_maybe(s)
                if isinstance(obj, dict):
                    task_name = obj.get("task")
                    pl = obj.get("payload")
                    if isinstance(pl, dict):
                        payload = pl
                else:
                    task_name = s
            else:
                task_name = s or None

    if (not payload) and raw_payload:
        obj = loads_json_maybe(raw_payload)
        if isinstance(obj, dict):
            payload = obj

    return task_name, payload


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    try:
        if hasattr(row, "keys"):
            ks = set(row.keys())
            if key in ks:
                return row[key]
            return default
    except Exception:
        pass
    if isinstance(row, Mapping):
        return row.get(key, default)
    try:
        return getattr(row, key)
    except Exception:
        return default


def job_item_from_row(row: Any) -> dict[str, Any]:
    rid = _row_get(row, "id")
    status_raw = _row_get(row, "status")
    status = (str(status_raw or "")).strip().lower()
    if status == "running":
        status = "working"
    if status == "succeeded":
        status = "done"

    raw_task = _row_get(row, "task")
    raw_payload = _row_get(row, "payload")
    task_name, payload = decode_task_and_payload(raw_task, raw_payload)

    result_val = _row_get(row, "result")
    error_val = _row_get(row, "error") or _row_get(row, "err") or _row_get(row, "last_error")

    item: dict[str, Any] = {
        "id": rid,
        "status": status,
        "task": task_name,
        "payload": payload,
        "result": loads_json_maybe(result_val),
        "error": loads_json_maybe(error_val),
    }

    for k in ("org_id", "project_id", "actor_type", "actor_id", "created_at", "updated_at", "created_by"):
        v = _row_get(row, k, None)
        if v is not None:
            item[k] = v

    return item
