# services/pipelines/catalog.py
from __future__ import annotations

from typing import Any, Dict, List, Mapping


def _norm_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return []


def select_pipeline(product_spec: Mapping[str, Any]) -> Dict[str, Any]:
    ptype = str(product_spec.get("product_type") or "web_app").strip().lower()
    sec = str(product_spec.get("security_level") or "standard").strip().lower()
    features = set(_norm_list(product_spec.get("features")))  # noqa: F841

    stages: List[str] = ["execute", "test"]

    # keep packager always-on for now (you can gate on feature later)
    stages.append("packager")

    if sec in {"standard", "hardened", "enterprise"}:
        stages.append("security_scan")

    return {
        "name": f"{ptype}_{sec}",
        "stages": stages,
        "gates": {
            "unit_tests": "pending",
            "build": "pending",
            "security": "pending",
        },
    }
