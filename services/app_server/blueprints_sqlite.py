from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def _db_path() -> str:
    p = (os.getenv("BLUEPRINT_DB") or "").strip()
    if p:
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        return p

    if os.getenv("PYTEST_CURRENT_TEST"):
        base = Path(os.getenv("TMPDIR") or "/tmp") / "velu_test"
        base.mkdir(parents=True, exist_ok=True)
        return str(base / "blueprints.db")

    base = Path.cwd() / "data" / "pointers"
    base.mkdir(parents=True, exist_ok=True)
    return str(base / "blueprints.db")



def _ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS blueprints ("
        "id TEXT PRIMARY KEY,"
        "body TEXT NOT NULL,"
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    )


def save_blueprint(bid: str, body: dict[str, Any]) -> None:
    con = sqlite3.connect(_db_path())
    try:
        _ensure_schema(con)
        con.execute(
            "INSERT OR REPLACE INTO blueprints (id, body) VALUES (?, ?)",
            (bid, json.dumps(body, ensure_ascii=False)),
        )
        con.commit()
    finally:
        con.close()


def get_blueprint(bid: str) -> dict[str, Any] | None:
    con = sqlite3.connect(_db_path())
    try:
        _ensure_schema(con)
        cur = con.execute("SELECT body FROM blueprints WHERE id = ?", (bid,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])
    finally:
        con.close()


def list_blueprints(limit: int = 20) -> list[dict[str, Any]]:
    con = sqlite3.connect(_db_path())
    try:
        _ensure_schema(con)
        cur = con.execute(
            "SELECT id, body, created_at " "FROM blueprints " "ORDER BY created_at DESC " "LIMIT ?",
            (limit,),
        )
        items: list[dict[str, Any]] = []
        for bid, body, created_at in cur.fetchall():
            payload = json.loads(body)
            items.append({"id": bid, "body": payload, "created_at": created_at})
        return items
    finally:
        con.close()
