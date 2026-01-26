from __future__ import annotations
from typing import Dict, Any


def edit_blueprint(blueprint: Dict[str, Any], instruction: str) -> Dict[str, Any]:
    text = instruction.lower()

    # Framework switching
    if "react native" in text:
        blueprint.setdefault("frontend", {})["framework"] = "react_native"
        blueprint.setdefault("channels", [])
        if "ios" not in blueprint["channels"]:
            blueprint["channels"].append("ios")
        if "android" not in blueprint["channels"]:
            blueprint["channels"].append("android")

    if "flutter" in text:
        blueprint.setdefault("frontend", {})["framework"] = "flutter"
        blueprint.setdefault("channels", [])
        for ch in ("ios", "android"):
            if ch not in blueprint["channels"]:
                blueprint["channels"].append(ch)

    # Billing
    if "billing" in text or "subscription" in text:
        blueprint.setdefault("plugins", [])
        if "billing" not in blueprint["plugins"]:
            blueprint["plugins"].append("billing")

    # Database switching
    if "postgres" in text:
        blueprint.setdefault("database", {})["engine"] = "postgres"

    if "sqlite" in text:
        blueprint.setdefault("database", {})["engine"] = "sqlite"

    return blueprint
