from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from pathlib import Path
from typing import Any, Iterable  # noqa: F401

import psycopg


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def truthy(name: str) -> bool:
    return env(name).lower() in {"1", "true", "yes", "on"}


def db_url() -> str:
    url = env("DATABASE_URL")
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql://" + url[len("postgresql+psycopg://") :]
    return url


def gen_key() -> str:
    return "k_" + secrets.token_urlsafe(24).replace("-", "_")


def pepper() -> bytes:
    p = env("VELU_API_KEY_PEPPER")
    if not p:
        raise RuntimeError("VELU_API_KEY_PEPPER missing")
    return p.encode("utf-8")


def hash_key(raw: str) -> str:
    digest = hashlib.sha256(pepper() + raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def wait_for_tables(conn: psycopg.Connection, timeout_sec: int = 60) -> None:
    deadline = time.time() + max(1, int(timeout_sec))
    last_err: Exception | None = None

    required = [
        t.strip()
        for t in (os.getenv("VELU_BOOTSTRAP_REQUIRED_TABLES") or "").split(",")
        if t.strip()
    ]
    # example: VELU_BOOTSTRAP_REQUIRED_TABLES="public.organizations,public.api_keys"

    while time.time() < deadline:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.schema_migrations');")
                sm = cur.fetchone()[0]
                if not sm:
                    time.sleep(1)
                    continue

                cur.execute("SELECT count(*) FROM public.schema_migrations;")
                applied_count = cur.fetchone()[0]
                if applied_count < 1:
                    time.sleep(1)
                    continue

                ok = True
                for name in required:
                    cur.execute("SELECT to_regclass(%s);", (name,))
                    if not cur.fetchone()[0]:
                        ok = False
                        break

                if ok:
                    return

        except Exception as e:
            last_err = e

        time.sleep(1)

    if last_err:
        raise last_err
    raise RuntimeError("tables not ready")


def ensure_org(conn: psycopg.Connection, slug: str, name: str) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT id::text FROM organizations WHERE slug=%s LIMIT 1;", (slug,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO organizations (name, slug) VALUES (%s, %s) RETURNING id::text;",
            (name, slug),
        )
        return cur.fetchone()[0]


def upsert_key(conn: psycopg.Connection, org_id: str, name: str, raw_key: str, scopes: Iterable[str]) -> None:
    scopes_norm = sorted({str(s).strip() for s in scopes if s and str(s).strip()})
    hashed = hash_key(raw_key)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO api_keys (org_id, name, hashed_key, scopes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (org_id, name)
            DO UPDATE SET hashed_key=EXCLUDED.hashed_key, scopes=EXCLUDED.scopes, revoked_at=NULL;
            """,
            (org_id, name, hashed, scopes_norm),
        )


def write_env_file(path: Path, kv: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    lines = [f'{k}="{v.replace(chr(34), chr(92) + chr(34))}"' for k, v in kv.items()]
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def main() -> int:
    if not truthy("VELU_BOOTSTRAP_DB"):
        print("skip")
        return 0

    url = db_url()
    if not url:
        raise RuntimeError("DATABASE_URL missing")

    org_slug = env("VELU_BOOTSTRAP_ORG_SLUG", "velu")
    org_name = env("VELU_BOOTSTRAP_ORG_NAME", "Velu")
    out_path = Path(env("VELU_BOOTSTRAP_OUT", "/data/dev_api_keys.env"))
    rotate = truthy("VELU_BOOTSTRAP_ROTATE")

    viewer_scopes = ["jobs:read"]
    builder_scopes = ["jobs:submit", "jobs:read"]

    # ✅ FIX: /orgs/bootstrap requires admin:orgs:manage
    admin_scopes = [
    "admin:api_keys:manage",
    "admin:orgs:manage",   # <-- REQUIRED for POST /orgs/bootstrap
    "jobs:submit",
    "jobs:read",
]



    viewer_key = env("VELU_VIEWER_KEY")
    builder_key = env("VELU_BUILDER_KEY")
    admin_key = env("VELU_ADMIN_KEY")

    if rotate or not viewer_key:
        viewer_key = gen_key()
    if rotate or not builder_key:
        builder_key = gen_key()
    if rotate or not admin_key:
        admin_key = gen_key()

    with psycopg.connect(url) as conn:
        wait_for_tables(conn, int(env("VELU_BOOTSTRAP_WAIT_SEC", "60") or "60"))
        org_id = ensure_org(conn, org_slug, org_name)
        upsert_key(conn, org_id, "viewer-local", viewer_key, viewer_scopes)
        upsert_key(conn, org_id, "builder-local", builder_key, builder_scopes)
        upsert_key(conn, org_id, "admin-local", admin_key, admin_scopes)
        conn.commit()

    write_env_file(
        out_path,
        {
            "VELU_ORG_SLUG": org_slug,
            "VELU_VIEWER_KEY": viewer_key,
            "VELU_BUILDER_KEY": builder_key,
            "VELU_ADMIN_KEY": admin_key,
        },
    )

    print(f"ok {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
