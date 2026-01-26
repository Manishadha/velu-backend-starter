# services/plugins/catalog.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PluginDef:
    slug: str
    label: str
    backend_tags: List[str]
    frontend_tags: List[str]


PLUGINS: Dict[str, PluginDef] = {
    "ecommerce": PluginDef(
        slug="ecommerce",
        label="Store and catalog",
        backend_tags=["ecommerce_products"],
        frontend_tags=["ecommerce_products_page", "ecommerce_checkout_page"],
    ),
    "auth": PluginDef(
        slug="auth",
        label="User authentication",
        backend_tags=["auth_basic"],
        frontend_tags=["auth_login_page"],
    ),
}


def get_plugin(slug: str) -> Optional[PluginDef]:
    return PLUGINS.get(slug)
