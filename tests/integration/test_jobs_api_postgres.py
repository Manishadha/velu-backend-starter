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
def test_jobs_api_org_scoped_and_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    db_url_raw = os.getenv("DATABASE_URL", "").strip()
    if not db_url_raw:
        pytest.skip("DATABASE_URL not set")

    db_url = _normalize_db_url(db_url_raw)

    monkeypatch.setenv("NO_EMBEDDED_API", "1")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("VELU_RUN_MIGRATIONS", "0")
    monkeypatch.setenv("VELU_TEST_DB_LOOKUP", "1")
    monkeypatch.setenv("DATABASE_URL", db_url_raw)
    monkeypatch.delenv("API_KEYS", raising=False)

    # Two orgs + one project each
    org1_slug = f"t_{uuid.uuid4().hex[:12]}"
    org2_slug = f"t_{uuid.uuid4().hex[:12]}"

    raw_admin_1 = "velu_admin_" + uuid.uuid4().hex
    raw_readonly_1 = "velu_read_" + uuid.uuid4().hex
    raw_admin_2 = "velu_admin_" + uuid.uuid4().hex

    hashed_admin_1 = _hash_key(raw_admin_1)
    hashed_readonly_1 = _hash_key(raw_readonly_1)
    hashed_admin_2 = _hash_key(raw_admin_2)

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO organizations (name, slug) VALUES (%s, %s) RETURNING id::text;",
                (f"Org {org1_slug}", org1_slug),
            )
            org1 = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO organizations (name, slug) VALUES (%s, %s) RETURNING id::text;",
                (f"Org {org2_slug}", org2_slug),
            )
            org2 = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO projects (org_id, name, slug)
                VALUES (%s::uuid, %s, %s)
                RETURNING id::text;
                """,
                (org1, "P1", "p1"),
            )
            proj1 = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO projects (org_id, name, slug)
                VALUES (%s::uuid, %s, %s)
                RETURNING id::text;
                """,
                (org2, "P2", "p2"),
            )
            proj2 = cur.fetchone()[0]  # noqa: F841

            # Admin key org1: submit+read
            cur.execute(
                """
                INSERT INTO api_keys (org_id, name, hashed_key, scopes, revoked_at)
                VALUES (%s::uuid, %s, %s, %s::text[], NULL)
                RETURNING id::text;
                """,
                (org1, "admin1", hashed_admin_1, ["jobs:submit", "jobs:read"]),
            )
            admin1_id = cur.fetchone()[0]

            # Read-only key org1: read only
            cur.execute(
                """
                INSERT INTO api_keys (org_id, name, hashed_key, scopes, revoked_at)
                VALUES (%s::uuid, %s, %s, %s::text[], NULL)
                RETURNING id::text;
                """,
                (org1, "read1", hashed_readonly_1, ["jobs:read"]),
            )
            _read1_id = cur.fetchone()[0]

            # Admin key org2
            cur.execute(
                """
                INSERT INTO api_keys (org_id, name, hashed_key, scopes, revoked_at)
                VALUES (%s::uuid, %s, %s, %s::text[], NULL)
                RETURNING id::text;
                """,
                (org2, "admin2", hashed_admin_2, ["jobs:submit", "jobs:read"]),
            )
            _admin2_id = cur.fetchone()[0]

        conn.commit()

    app = create_app()
    c = TestClient(app)

    # org1 admin submits
    r = c.post(
        f"/orgs/{org1}/projects/{proj1}/jobs",
        json={"task": "plan", "payload": {"x": 1}},
        headers={"X-API-Key": raw_admin_1},
    )
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    # org1 readonly cannot submit
    r2 = c.post(
        f"/orgs/{org1}/projects/{proj1}/jobs",
        json={"task": "plan", "payload": {"x": 2}},
        headers={"X-API-Key": raw_readonly_1},
    )
    assert r2.status_code == 403, r2.text

    # org1 admin can read
    r3 = c.get(f"/orgs/{org1}/jobs/{job_id}", headers={"X-API-Key": raw_admin_1})
    assert r3.status_code == 200, r3.text
    item = r3.json()["item"]
    assert item["org_id"] == org1
    assert item["project_id"] == proj1
    assert item.get("actor_type") == "api_key"
    assert item.get("actor_id") == admin1_id

    # org2 admin cannot read org1 job (404, no leakage)
    r4 = c.get(f"/orgs/{org1}/jobs/{job_id}", headers={"X-API-Key": raw_admin_2})
    assert r4.status_code == 404, r4.text

    # Cleanup
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM jobs_v2 WHERE id = %s::uuid;", (job_id,))
            cur.execute("DELETE FROM api_keys WHERE org_id IN (%s::uuid, %s::uuid);", (org1, org2))
            cur.execute("DELETE FROM projects WHERE org_id IN (%s::uuid, %s::uuid);", (org1, org2))
            cur.execute("DELETE FROM organizations WHERE id IN (%s::uuid, %s::uuid);", (org1, org2))
        conn.commit()
