from __future__ import annotations

from typing import Any


def _normalize_entities(raw: Any) -> list[dict[str, str]]:
    if isinstance(raw, list):
        out: list[dict[str, str]] = []
        for item in raw:
            if isinstance(item, dict) and "name" in item:
                out.append({"name": str(item["name"])})
            elif isinstance(item, str):
                out.append({"name": item})
        if out:
            return out
    return [{"name": "Account"}, {"name": "User"}]


def _ddl_for_sqlite(entities: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for ent in entities:
        name = str(ent["name"]).strip().lower() or "entity"
        parts.append(
            f"CREATE TABLE IF NOT EXISTS {name} ("
            "id TEXT PRIMARY KEY, "
            "tenant_id TEXT, "
            "created_at TEXT"
            ");"
        )
    return "\n".join(parts)


def _ddl_for_postgres(entities: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for ent in entities:
        name = str(ent["name"]).strip().lower() or "entity"
        parts.append(
            f"CREATE TABLE IF NOT EXISTS {name} ("
            "id uuid PRIMARY KEY, "
            "tenant_id uuid, "
            "created_at timestamptz default now()"
            ");"
        )
    return "\n".join(parts)


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    engine = str(payload.get("database") or "sqlite").strip().lower()
    entities = _normalize_entities(payload.get("entities"))

    if engine == "postgres":
        ddl = _ddl_for_postgres(entities)
        default_url = "postgresql+psycopg://app_user:app_pass@localhost:5432/app_db"
    else:
        engine = "sqlite"
        ddl = _ddl_for_sqlite(entities)
        default_url = "sqlite:///./data/app.db"

    migrations = [{"id": "001_init.sql", "sql": ddl}]

    return {
        "ok": True,
        "agent": "datamodel",
        "models": entities,
        "migrations": migrations,
        "ddl": ddl,
        "database": {
            "engine": engine,
            "default_url": default_url,
        },
    }
