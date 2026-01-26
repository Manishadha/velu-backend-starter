from __future__ import annotations

from services.agents import intake_rules


def test_intake_rules_ecommerce_postgres() -> None:
    """
    If the idea clearly talks about a shop/store with checkout and Postgres,
    we expect:
    - Product type: ecommerce
    - Goal: transactions
    - Channels: web + mobile (ios + android)
    - Database: postgres
    - Plugins: includes ecommerce + auth
    """
    idea = (
        "I want an ecommerce shop for my products with cart and checkout. "
        "Web and mobile app, and the backend database must be Postgres. "
        "Users should be able to login and manage their account."
    )

    p_type, goal = intake_rules.infer_type_and_goal(idea)
    assert p_type == "ecommerce"
    assert goal == "transactions"

    channels = intake_rules.infer_channels(idea, fallback=["web"])
    assert "web" in channels
    assert "ios" in channels
    assert "android" in channels

    db = intake_rules.infer_database_engine(idea, default="sqlite")
    assert db == "postgres"

    plugins = intake_rules.infer_plugins(idea)

    assert "ecommerce" in plugins
    assert "auth" in plugins


def test_intake_rules_multitenant_tier_and_enrich_blueprint() -> None:
    """
    If the idea mentions multi-tenant B2B SaaS, SSO and Postgres,
    we expect:
    - plan_tier: enterprise
    - database.engine: postgres after enrich
    - plugins: auth, subscriptions, billing
    """
    idea = (
        "I want a multi-tenant B2B SaaS platform with SSO (Okta, Azure AD), "
        "subscriptions and billing (Starter, Pro, Enterprise plans). "
        "Database must be Postgres."
    )

    # direct plan tier inference
    tier = intake_rules.infer_plan_tier(idea, default="starter")
    assert tier == "enterprise"

    # direct plugin inference
    plugins = intake_rules.infer_plugins(idea)
    assert "auth" in plugins
    assert "subscriptions" in plugins
    assert "billing" in plugins

    # integrated check via enrich_blueprint_dict
    base_blueprint = {
        "backend": {},
        "database": {"engine": "sqlite"},
        "plugins": [],
        "plan_tier": "starter",
    }

    enriched = intake_rules.enrich_blueprint_dict(base_blueprint, idea)

    # database upgraded to postgres
    assert enriched["database"]["engine"] == "postgres"

    # tier upgraded to enterprise
    assert enriched["plan_tier"] == "enterprise"

    # plugins merged correctly
    enriched_plugins = set(enriched.get("plugins") or [])
    assert {"auth", "subscriptions", "billing"}.issubset(enriched_plugins)
