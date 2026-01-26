from __future__ import annotations

from services.agents import db_schema_optimizer


def _issues_for_table(res, table_name: str):
    tables = res.get("tables") or []
    for t in tables:
        if t.get("name") == table_name:
            return t.get("issues") or []
    return []


def test_db_schema_optimizer_flags_missing_foreign_key_index():
    payload = {
        "tables": [
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "user_id", "type": "integer"},
                    {"name": "status", "type": "text"},
                ],
                "indexes": [],
            }
        ]
    }
    res = db_schema_optimizer.handle(payload)
    assert res["ok"] is True
    issues = _issues_for_table(res, "orders")
    msgs = [i.get("message") for i in issues]
    assert any("user_id" in str(m) and "index" in str(m).lower() for m in msgs)
    summary = res.get("summary") or {}
    assert summary.get("total_issues") == len(res.get("issues") or [])


def test_db_schema_optimizer_respects_existing_indexes():
    payload = {
        "tables": [
            {
                "name": "events",
                "columns": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "user_id", "type": "integer"},
                    {"name": "created_at", "type": "timestamp"},
                ],
                "indexes": [
                    {"name": "idx_events_user_id", "columns": ["user_id"]},
                    {"name": "idx_events_created_at", "columns": ["created_at"]},
                ],
            }
        ]
    }
    res = db_schema_optimizer.handle(payload)
    issues = _issues_for_table(res, "events")
    assert issues == []


def test_db_schema_optimizer_email_needs_unique():
    payload = {
        "tables": [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "integer", "primary_key": True},
                    {"name": "email", "type": "varchar", "max_length": 255},
                ],
                "indexes": [],
            }
        ]
    }
    res = db_schema_optimizer.handle(payload)
    issues = _issues_for_table(res, "users")
    kinds = {i.get("kind") for i in issues}
    assert "missing_uniqueness" in kinds
