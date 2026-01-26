from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BlueprintFrontend(BaseModel):
    framework: str = "nextjs"
    language: str = "typescript"
    targets: List[Literal["web", "android", "ios", "desktop", "cli"]] = Field(
        default_factory=lambda: ["web"]
    )


class BlueprintBackend(BaseModel):
    framework: str = "fastapi"
    language: str = "python"
    style: Literal["rest", "graphql", "rpc"] = "rest"


class BlueprintDatabase(BaseModel):
    engine: str = "sqlite"
    mode: Literal["single_node", "clustered"] = "single_node"


class BlueprintLocalization(BaseModel):
    default_language: str = "en"
    supported_languages: List[str] = Field(default_factory=lambda: ["en"])


class BlueprintBrand(BaseModel):
    name: Optional[str] = None
    primary_color: str = "#2563eb"
    secondary_color: str = "#0f172a"
    accent_color: str = "#f97316"
    font: Literal["system", "serif", "mono"] = "system"
    logo_url: Optional[str] = None


class BlueprintLayout(BaseModel):
    hero_style: Literal["centered", "split", "image_right"] = "centered"
    show_testimonials: bool = True
    show_pricing: bool = True
    show_cta: bool = True


class Blueprint(BaseModel):
    id: str
    name: str
    kind: Literal[
        "website",
        "web_app",
        "mobile_app",
        "dashboard",
        "api_only",
        "cli",
        "service",
    ] = "web_app"
    frontend: BlueprintFrontend
    backend: BlueprintBackend
    database: BlueprintDatabase
    localization: BlueprintLocalization
    brand: BlueprintBrand = Field(default_factory=BlueprintBrand)
    layout: BlueprintLayout = Field(default_factory=BlueprintLayout)
