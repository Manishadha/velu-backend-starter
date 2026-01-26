from __future__ import annotations

from pathlib import Path

MODELS_SPEC: dict[str, list[tuple[str, str]]] = {
    "Account": [
        ("id", "UUID"),
        ("tenant_id", "UUID | None"),
        ("created_at", "datetime"),
    ],
    "User": [
        ("id", "UUID"),
        ("tenant_id", "UUID | None"),
        ("created_at", "datetime"),
    ],
}


def generate_models(target_path: str = "src/account_models.py") -> None:
    header = [
        "from __future__ import annotations",
        "",
        "from datetime import datetime",
        "from uuid import UUID",
        "from pydantic import BaseModel",
        "",
        "",
    ]

    lines: list[str] = header[:]
    for model_name, fields in MODELS_SPEC.items():
        lines.append(f"class {model_name}(BaseModel):")
        for name, typ in fields:
            lines.append(f"    {name}: {typ}")
        lines.append("")
        lines.append("")

    content = "\n".join(lines).rstrip() + "\n"

    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    generate_models()
