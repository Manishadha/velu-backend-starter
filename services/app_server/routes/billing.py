from __future__ import annotations

import json  # noqa: F401
import os
from typing import Any  # noqa: F401

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from services.app_server.dependencies.scopes import require_scopes
from services.billing.accounts import get_org_by_slug, set_org_plan, upsert_billing_account


router = APIRouter()


def _stripe_secret() -> str:
    v = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not v:
        raise RuntimeError("STRIPE_SECRET_KEY missing")
    return v


def _stripe_webhook_secret() -> str:
    v = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not v:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET missing")
    return v


def _price_to_plan(price_id: str | None) -> str:
    p = (price_id or "").strip()
    if not p:
        return "base"
    m = {}
    base = (os.getenv("STRIPE_PRICE_BASE") or "").strip()
    hero = (os.getenv("STRIPE_PRICE_HERO") or "").strip()
    superh = (os.getenv("STRIPE_PRICE_SUPERHERO") or "").strip()
    if base:
        m[base] = "base"
    if hero:
        m[hero] = "hero"
    if superh:
        m[superh] = "superhero"
    return m.get(p, "base")


class CheckoutIn(BaseModel):
    org_slug: str = Field(min_length=1)
    price_id: str = Field(min_length=1)
    success_url: str = Field(min_length=1)
    cancel_url: str = Field(min_length=1)


@router.post("/billing/checkout-session", dependencies=[Depends(require_scopes({"admin:billing:write"}))])
async def create_checkout_session(body: CheckoutIn):
    org = get_org_by_slug(body.org_slug)
    if not org:
        raise HTTPException(status_code=404, detail="org_not_found")

    import stripe # type: ignore

    stripe.api_key = _stripe_secret()

    sess = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": body.price_id, "quantity": 1}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"org_id": org["id"], "org_slug": org["slug"], "price_id": body.price_id},
    )

    return {"ok": True, "id": sess["id"], "url": sess.get("url")}


@router.post("/billing/webhook")
async def stripe_webhook(request: Request):
    import stripe # type: ignore

    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not sig:
        raise HTTPException(status_code=400, detail="missing_signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig,
            secret=_stripe_webhook_secret(),
        )
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_signature")

    etype = event.get("type")
    data = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed":
        org_id = (data.get("metadata") or {}).get("org_id")
        price_id = (data.get("metadata") or {}).get("price_id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if org_id:
            plan = _price_to_plan(price_id)
            set_org_plan(org_id, plan)
            upsert_billing_account(
                org_id=org_id,
                stripe_customer_id=str(customer_id) if customer_id else None,
                stripe_subscription_id=str(subscription_id) if subscription_id else None,
                stripe_price_id=str(price_id) if price_id else None,
                status="active",
            )

    if etype in {"customer.subscription.updated", "customer.subscription.created"}:
        sub_id = data.get("id")
        customer_id = data.get("customer")
        items = (data.get("items") or {}).get("data") or []
        price_id = None
        if items and isinstance(items, list):
            price = (items[0].get("price") or {}) if isinstance(items[0], dict) else {}
            price_id = price.get("id")
        status = (data.get("status") or "").strip().lower() or "active"
        current_period_end = data.get("current_period_end")
        org_id = None
        md = data.get("metadata") or {}
        org_id = md.get("org_id")
        if org_id:
            plan = _price_to_plan(price_id)
            set_org_plan(org_id, plan)
            upsert_billing_account(
                org_id=org_id,
                stripe_customer_id=str(customer_id) if customer_id else None,
                stripe_subscription_id=str(sub_id) if sub_id else None,
                stripe_price_id=str(price_id) if price_id else None,
                status=status,
                current_period_end=str(current_period_end) if current_period_end else None,
            )

    if etype == "customer.subscription.deleted":
        md = data.get("metadata") or {}
        org_id = md.get("org_id")
        if org_id:
            set_org_plan(org_id, "base")
            upsert_billing_account(
                org_id=org_id,
                stripe_customer_id=str(data.get("customer")) if data.get("customer") else None,
                stripe_subscription_id=str(data.get("id")) if data.get("id") else None,
                stripe_price_id=None,
                status="inactive",
            )

    return {"ok": True}
