# services/app_server/schemas/intake.py
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

ProductType = Literal["website", "saas", "mobile_app", "ecommerce", "marketplace", "portal", "docs"]
Goal = Literal["lead_gen", "self_service", "transactions", "community", "internal_tool"]


class Company(BaseModel):
    name: str
    industry: str | None = None
    region: str | None = None
    contact_email: EmailStr | None = None


class AIFeatures(BaseModel):
    assist: bool = False
    summarize: bool = False
    chat: bool = False


class Features(BaseModel):
    auth: Literal["email_magic", "password", "oauth", "sso", "otp", "none"] = "email_magic"
    billing: Literal["none", "stripe", "paddle"] = "none"
    realtime: bool = False
    search: Literal["none", "basic", "semantic"] = "basic"
    roles: list[str] = Field(default_factory=lambda: ["user"])
    cms: Literal["none", "headless"] = "none"
    file_uploads: bool = False
    notifications: list[Literal["email", "push", "webpush"]] = Field(default_factory=list)
    ai: AIFeatures = AIFeatures()


class Entity(BaseModel):
    name: str
    fields: dict[str, str] = Field(default_factory=dict)


class DataSpec(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    retention_policy_days: int = 365


class SecuritySpec(BaseModel):
    pii: bool = False
    regimes: list[str] = Field(default_factory=list)
    sso: Literal["none", "okta", "azuread", "google"] = "none"
    allowed_origins: list[str] = Field(default_factory=list)
    ip_allowlist: list[str] = Field(default_factory=list)


class OpsSpec(BaseModel):
    deploy_target: Literal["docker", "kubernetes"] = "docker"
    regions: list[str] = Field(default_factory=list)
    rpo_minutes: int = 30
    rto_minutes: int = 60
    observability: Literal["standard", "enhanced"] = "standard"


class Constraints(BaseModel):
    budget: Literal["low", "mid", "high"] = "mid"
    time_to_first_release_days: int = 10


class Product(BaseModel):
    name: str = "Product"
    type: ProductType
    goal: Goal
    audiences: list[str] = Field(default_factory=list)
    channels: list[Literal["web", "ios", "android"]] = Field(default_factory=lambda: ["web"])
    # ISO language / locale codes, e.g. ["en", "fr", "ta-IN"]
    locales: list[str] = Field(default_factory=lambda: ["en"])
    brand_assets: str | None = None  # URL(s) or figma://


class Intake(BaseModel):
    company: Company
    product: Product
    features: Features = Features()
    data: DataSpec = DataSpec()
    security: SecuritySpec = SecuritySpec()
    ops: OpsSpec = OpsSpec()
    constraints: Constraints = Constraints()
    # Preferred language inferred or provided for this intake, e.g. "fr", "ta-IN".
    user_language: str | None = None
    # Optional: language detected from the original free-text description.
    original_text_language: str | None = None

    def to_pipeline_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "company": self.company.model_dump(),
            "product": self.product.model_dump(),
            "features": self.features.model_dump(),
            "data": self.data.model_dump(),
            "security": self.security.model_dump(),
            "ops": self.ops.model_dump(),
            "constraints": self.constraints.model_dump(),
        }
        payload["user_language"] = self.user_language
        payload["original_text_language"] = self.original_text_language
        payload["ui_languages"] = list(self.product.locales or ["en"])
        return payload
