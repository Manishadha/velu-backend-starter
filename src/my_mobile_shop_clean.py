from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


def greet(name: str) -> str:
    """Simple greeter used by smoke tests."""
    return f"Hello, {name}!"


# ---------------------------
# Ecommerce blueprint (clean)
# ---------------------------


FrontendKind = Literal[
    "nextjs",
    "react",
    "vue",
    "sveltekit",
    "react_native",
    "expo",
    "flutter",
    "tauri",
    "none",
]

BackendKind = Literal[
    "fastapi",
    "django",
    "express",
    "nestjs",
    "node",
    "none",
]

DatabaseKind = Literal["sqlite", "postgres", "mysql", "mongodb", "none"]

PlanTier = Literal["starter", "pro", "enterprise"]
AssistantMode = Literal["basic", "pro", "architect"]
SecurityPosture = Literal["standard", "hardened"]


@dataclass
class TechStack:
    """Technical stack Velu should generate."""

    frontend: FrontendKind = "nextjs"
    backend: BackendKind = "fastapi"
    database: DatabaseKind = "postgres"
    mobile_frontend: str = "react_native"  # for customers
    design_style: str = "colorful_and_friendly"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "frontend": self.frontend,
            "backend": self.backend,
            "database": self.database,
            "mobile_frontend": self.mobile_frontend,
            "design_style": self.design_style,
        }


@dataclass
class EcommerceFeatures:
    """High-level ecommerce capabilities for Velu to scaffold."""

    product_type: str = "ecommerce"
    goal: str = "transactions"

    channels: List[str] = field(default_factory=lambda: ["web", "ios", "android"])

    # what the client specifically asked for
    description: str = (
        "Web: Next.js admin dashboard and product catalog. "
        "Mobile: React Native app for customers to browse products and checkout. "
        "Use FastAPI backend and Postgres. Design: colorful and friendly."
    )

    # UX + domain features
    features: List[str] = field(
        default_factory=lambda: [
            "catalog",
            "search",
            "filters",
            "product_detail",
            "cart",
            "checkout",
            "orders",
            "user_accounts",
            "admin_dashboard",
        ]
    )

    pages: List[str] = field(
        default_factory=lambda: [
            "Home",
            "Products",
            "Product detail",
            "Cart",
            "Checkout",
            "Account",
            "Admin dashboard",
            "About",
            "Contact",
        ]
    )

    ui_languages: List[str] = field(default_factory=lambda: ["en", "fr", "nl", "de", "ar", "ta"])

    def as_dict(self) -> Dict[str, Any]:
        return {
            "product_type": self.product_type,
            "goal": self.goal,
            "channels": self.channels,
            "description": self.description,
            "features": self.features,
            "pages": self.pages,
            "ui_languages": self.ui_languages,
        }


@dataclass
class AppBlueprint:
    """
    High-level blueprint Velu can use to drive:
    - planning
    - backend scaffolding
    - web UI (Next.js)
    - mobile UI (React Native)
    """

    name: str
    module: str
    plan_tier: PlanTier = "starter"
    assistant_mode: AssistantMode = "basic"
    security_posture: SecurityPosture = "standard"

    tech: TechStack = field(default_factory=TechStack)
    ecommerce: EcommerceFeatures = field(default_factory=EcommerceFeatures)

    # optional metadata Velu agents may use later
    owner: Optional[str] = "client"
    notes: str = (
        "Clean ecommerce blueprint: Next.js admin + catalog (web), "
        "React Native shopping app (mobile), FastAPI backend, Postgres DB."
    )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "plan_tier": self.plan_tier,
            "assistant_mode": self.assistant_mode,
            "security_posture": self.security_posture,
            "tech": self.tech.as_dict(),
            "ecommerce": self.ecommerce.as_dict(),
            "owner": self.owner,
            "notes": self.notes,
        }


#: Canonical blueprint instance for this module.
BLUEPRINT = AppBlueprint(
    name="my_mobile_shop_clean",
    module="my_mobile_shop_clean",
    # We’ll probably upgrade this later when you want “enterprise-by-default”
    plan_tier="starter",
    assistant_mode="pro",
    security_posture="standard",
)


def get_blueprint() -> Dict[str, Any]:
    """
    Convenience helper so agents can import this module and call get_blueprint()
    to obtain a plain dict, without caring about dataclasses.

    Example usage from other code:

        from src import my_mobile_shop_clean as shop
        spec = shop.get_blueprint()
    """
    return BLUEPRINT.as_dict()
