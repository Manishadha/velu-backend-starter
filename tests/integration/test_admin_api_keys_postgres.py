from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from services.app_server.auth import _hash_key
from services.app_server.main import create_app


os.environ.setdefault("NO_EMBEDDED_API", "1")


def _normalize_db_url(url: str) -> str:
    url = (url or "").strip()
    if url.lower().startswith("postgresql+psycopg://"):
        return "postgresql://" + url.split("://", 1)[1]
    if url.lower().startswith("postgres://"):
        return "postgresql://" + url.split("://", 1)[1]
    return url


@pytest.mark.integration
def test_admin_api_keys_create_revoke_rotate(monkeypatch: pytest.MonkeyPatch) -> None:
    db_url_raw = os.getenv("DATABASE_URL", "").strip()
    if not db_url_raw:
        pytest.skip("DATABASE_URL not set")

    db_url = _normalize_db_url(db_url_raw)

    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("ADMIN_ROUTES", "1")
    monkeypatch.setenv("VELU_RUN_MIGRATIONS", "0")
    monkeypatch.setenv("VELU_TEST_DB_LOOKUP", "1")
    monkeypatch.setenv("DATABASE_URL", db_url_raw)
    monkeypatch.delenv("API_KEYS", raising=False)

    # Create org + bootstrap admin key with manage scope directly in DB
    org_slug = f"t_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO organizations (name, slug) VALUES (%s, %s) RETURNING id::text;",
                (f"Test Org {org_slug}", org_slug),
            )
            org_id = cur.fetchone()[0]

            admin_raw = "velu_admin_" + uuid.uuid4().hex
            admin_hashed = _hash_key(admin_raw)
            cur.execute(
                """
                INSERT INTO api_keys (org_id, name, hashed_key, scopes, revoked_at)
                VALUES (%s::uuid, %s, %s, %s::text[], NULL)
                RETURNING id::text;
                """,
                (org_id, "bootstrap-admin", admin_hashed, ["admin:api_keys:manage", "jobs:submit"]),
            )
            admin_key_id = cur.fetchone()[0]
        conn.commit()

    app = create_app()
    c = TestClient(app)

    # Create a new key via admin endpoint
    r = c.post(
        "/admin/api-keys",
        json={"name": "ci", "scopes": ["jobs:submit"]},
        headers={"X-API-Key": admin_raw},
    )
    assert r.status_code == 200, r.text
    item = r.json()["item"]
    raw_once = item["raw_key"]
    created_id = item["id"]
    assert isinstance(raw_once, str) and raw_once.startswith("velu_")

    # Use created key to submit a task (requires jobs:submit)
    r2 = c.post(
        "/tasks", json={"task": "plan", "payload": {"ok": 1}}, headers={"X-API-Key": raw_once}
    )
    assert r2.status_code == 200, r2.text

    # Revoke created key -> immediate 401
    r3 = c.post(f"/admin/api-keys/{created_id}/revoke", headers={"X-API-Key": admin_raw})
    assert r3.status_code == 200, r3.text

    r4 = c.post(
        "/tasks", json={"task": "plan", "payload": {"ok": 2}}, headers={"X-API-Key": raw_once}
    )
    assert r4.status_code == 401, r4.text

    # Rotate -> old stays invalid, new works
    r5 = c.post(f"/admin/api-keys/{created_id}/rotate", headers={"X-API-Key": admin_raw})
    assert r5.status_code == 200, r5.text
    new_raw = r5.json()["item"]["raw_key"]

    r6 = c.post(
        "/tasks", json={"task": "plan", "payload": {"ok": 3}}, headers={"X-API-Key": raw_once}
    )
    assert r6.status_code == 401, r6.text

    r7 = c.post(
        "/tasks", json={"task": "plan", "payload": {"ok": 4}}, headers={"X-API-Key": new_raw}
    )
    assert r7.status_code == 200, r7.text

    # Cleanup
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM api_keys WHERE id = %s::uuid;", (created_id,))
            cur.execute("DELETE FROM api_keys WHERE id = %s::uuid;", (admin_key_id,))
            cur.execute("DELETE FROM organizations WHERE id = %s::uuid;", (org_id,))
        conn.commit()
