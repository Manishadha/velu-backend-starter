from __future__ import annotations


def greet(name: str = "Velu") -> str:
    clean = (name or "").strip() or "Velu"
    return f"Hello, {clean}!"
