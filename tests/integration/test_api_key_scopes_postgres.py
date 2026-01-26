from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from services.app_server.auth import _hash_key
from services.app_server.main import create_app


def _normalize_db_url(url: str) -> str:
    url = (url or "").strip()
    if url.lower().startswith("postgresql+psycopg://"):
        return "postgresql://" + url.split("://", 1)[1]
    if url.lower().startswith("postgres://"):
        return "postgresql://" + url.split("://", 1)[1]
    return url


@pytest.mark.integration
def test_postgres_api_key_scopes_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    db_url_raw = os.getenv("DATABASE_URL", "").strip()
    if not db_url_raw:
        pytest.skip("DATABASE_URL not set; skipping Postgres scope enforcement test")

    db_url = _normalize_db_url(db_url_raw)

    # Opt-in: allow DB lookups during pytest for THIS test.
    monkeypatch.setenv("VELU_TEST_DB_LOOKUP", "1")

    # Ensure we run app in Postgres mode and don't auto-run migrations inside the test.
    monkeypatch.setenv("VELU_RUN_MIGRATIONS", "0")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("DATABASE_URL", db_url_raw)
    monkeypatch.delenv("API_KEYS", raising=False)

    raw_key = "velu_test_" + uuid.uuid4().hex
    hashed = _hash_key(raw_key)

    org_slug = f"t_{uuid.uuid4().hex[:12]}"
    org_name = f"Test Org {org_slug}"
    key_name = f"test-key-{org_slug}"

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Create org
            cur.execute(
                """
                INSERT INTO organizations (name, slug)
                VALUES (%s, %s)
                RETURNING id::text;
                """,
                (org_name, org_slug),
            )
            org_id = cur.fetchone()[0]

            # Create api key with NO scopes
            cur.execute(
                """
                INSERT INTO api_keys (org_id, name, hashed_key, scopes)
                VALUES (%s::uuid, %s, %s, %s::text[])
                RETURNING id::text;
                """,
                (org_id, key_name, hashed, []),
            )
            key_id = cur.fetchone()[0]
        conn.commit()

    app = create_app()
    client = TestClient(app)

    # No scopes => forbidden
    r = client.post(
        "/tasks",
        json={"task": "plan", "payload": {"p": "q"}},
        headers={"X-API-Key": raw_key},
    )
    assert r.status_code == 403, r.text

    # Add required scope => OK
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_keys
                   SET scopes = %s::text[]
                 WHERE id = %s::uuid;
                """,
                (["jobs:submit"], key_id),
            )
        conn.commit()

    r2 = client.post(
        "/tasks",
        json={"task": "plan", "payload": {"ok": 1}},
        headers={"X-API-Key": raw_key},
    )
    assert r2.status_code == 200, r2.text
    # Submit requires jobs:submit (already verified by 403->200 in this test).
    job = r2.json()
    assert job.get("ok") is True
    job_id = job.get("job_id")
    assert isinstance(job_id, str) and job_id

    # Reading without jobs:read => 403
    r3 = client.get(f"/results/{job_id}", headers={"X-API-Key": raw_key})
    assert r3.status_code == 403, r3.text

    # Add jobs:read => 200 and ok True
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE api_keys
                   SET scopes = %s::text[]
                 WHERE id = %s::uuid;
                """,
                (["jobs:submit", "jobs:read"], key_id),
            )
        conn.commit()

    r4 = client.get(f"/results/{job_id}", headers={"X-API-Key": raw_key})
    assert r4.status_code == 200, r4.text
    data = r4.json()
    assert data.get("ok") is True
    assert data["item"]["id"] == job_id

    # Cross-org isolation: other org key cannot read org1 job (should look not_found)
    raw_key2 = "velu_test_" + uuid.uuid4().hex
    hashed2 = _hash_key(raw_key2)
    org_slug2 = f"t_{uuid.uuid4().hex[:12]}"
    key_name2 = f"test-key-{org_slug2}"

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO organizations (name, slug)
                VALUES (%s, %s)
                RETURNING id::text;
                """,
                (f"Test Org {org_slug2}", org_slug2),
            )
            org_id2 = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO api_keys (org_id, name, hashed_key, scopes)
                VALUES (%s::uuid, %s, %s, %s::text[])
                RETURNING id::text;
                """,
                (org_id2, key_name2, hashed2, ["jobs:read"]),
            )
            key_id2 = cur.fetchone()[0]
        conn.commit()

    r5 = client.get(f"/results/{job_id}", headers={"X-API-Key": raw_key2})
    assert r5.status_code == 200, r5.text
    leak = r5.json()
    assert leak.get("ok") is False
    assert leak.get("error") == "not_found"

    # Cleanup org2
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM api_keys WHERE id = %s::uuid;", (key_id2,))
            cur.execute("DELETE FROM organizations WHERE id = %s::uuid;", (org_id2,))
        conn.commit()
