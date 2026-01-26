from __future__ import annotations

import os
from typing import Any

import psycopg


def _db_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url.lower().startswith("postgresql+psycopg://"):
        url = "postgresql://" + url.split("://", 1)[1]
    if url.lower().startswith("postgres://"):
        url = "postgresql://" + url.split("://", 1)[1]
    return url


def set_org_plan(org_id: str, plan: str) -> None:
    plan = (plan or "").strip().lower() or "base"
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE organizations SET plan=%s, updated_at=now() WHERE id=%s::uuid",
                (plan, org_id),
            )
        conn.commit()


def upsert_billing_account(
    org_id: str,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
    stripe_price_id: str | None,
    status: str,
    current_period_end: str | None = None,
) -> None:
    status = (status or "inactive").strip().lower()
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO billing_accounts (
                  org_id, stripe_customer_id, stripe_subscription_id, stripe_price_id, status, current_period_end, updated_at
                )
                VALUES (%s::uuid, %s, %s, %s, %s, %s, now())
                ON CONFLICT (org_id)
                DO UPDATE SET
                  stripe_customer_id=EXCLUDED.stripe_customer_id,
                  stripe_subscription_id=EXCLUDED.stripe_subscription_id,
                  stripe_price_id=EXCLUDED.stripe_price_id,
                  status=EXCLUDED.status,
                  current_period_end=EXCLUDED.current_period_end,
                  updated_at=now()
                """,
                (org_id, stripe_customer_id, stripe_subscription_id, stripe_price_id, status, current_period_end),
            )
        conn.commit()


def get_org_by_slug(slug: str) -> dict[str, Any] | None:
    slug = (slug or "").strip()
    if not slug:
        return None
    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id::text, slug, plan FROM organizations WHERE slug=%s LIMIT 1", (slug,))
            row = cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "slug": row[1], "plan": row[2]}
