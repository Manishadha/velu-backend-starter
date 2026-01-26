from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.agents import assistant_intake, blueprint_editor, blueprint_history  # noqa: E402
from services.agents import packager  # noqa: E402

from configs.language_catalog import list_codes  # noqa: E402
import os  # noqa: E402


def format_help() -> str:
    return (
        "\nVelu console commands:\n"
        "  [enter]        Start a new idea / intake\n"
        "  d              Dump full JSON result (intake + blueprint + i18n)\n"
        "  p              Run packager for the current blueprint summary\n"
        "  edit <rule>    Apply a rule-based edit to the blueprint\n"
        "  ai <rule>      Apply an LLM-style edit to the blueprint (same engine)\n"
        "  u / undo       Undo the last blueprint change\n"
        "  r / redo       Redo a previously undone blueprint change\n"
        "  h / history    Show blueprint revision history\n"
        "  e              Export blueprint to 'blueprint.json'\n"
        "  export <file>  Export blueprint to a custom file name\n"
        "  q / quit       Exit the console\n"
    )


def get_ui_language() -> str:
    lang = (os.getenv("VELU_UI_LANG") or "").strip()
    if lang and lang in list_codes():
        return lang
    return "en"


def run_intake(idea: str) -> Dict[str, Any]:
    ui_lang = get_ui_language()
    payload: Dict[str, Any] = {
        "idea": idea,
        "ui_language": ui_lang,
        "company": {},
        "product": {},
    }
    result = assistant_intake.handle(payload)
    return result


def _first_non_empty(*values: Any) -> Any:
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def extract_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    blueprint: Dict[str, Any] = result.get("blueprint") or {}
    intake: Dict[str, Any] = result.get("intake") or {}
    product: Dict[str, Any] = intake.get("product") or {}
    i18n: Dict[str, Any] = result.get("i18n") or {}

    plugins = list(blueprint.get("plugins") or [])

    product_type = _first_non_empty(
        product.get("type"),
        product.get("product_type"),
        blueprint.get("product_type"),
        blueprint.get("kind"),
    )

    if not product_type and "ecommerce" in plugins:
        product_type = "ecommerce"

    goal = _first_non_empty(
        product.get("goal"),
        blueprint.get("goal"),
        blueprint.get("product_goal"),
    )

    locales: List[str] = list(
        product.get("locales") or i18n.get("locales") or intake.get("locales") or ["en"]
    )

    channels: List[str] = list(product.get("channels") or blueprint.get("channels") or [])

    frontend_cfg: Dict[str, Any] = blueprint.get("frontend") or {}
    backend_cfg: Dict[str, Any] = blueprint.get("backend") or {}
    db_cfg: Dict[str, Any] = blueprint.get("database") or {}

    frontend = frontend_cfg.get("framework")
    backend = backend_cfg.get("framework")
    database = db_cfg.get("engine")

    plan_tier = blueprint.get("plan_tier") or blueprint.get("tier") or intake.get("plan_tier")

    module_name = (
        blueprint.get("module_name")
        or blueprint.get("module")
        or blueprint.get("id")
        or intake.get("module_name")
        or "product"
    )

    return {
        "type": product_type,
        "goal": goal,
        "locales": locales,
        "channels": channels,
        "frontend": frontend,
        "backend": backend,
        "database": database,
        "plan_tier": plan_tier,
        "plugins": plugins,
        "module": module_name,
    }


def print_summary(summary: Dict[str, Any]) -> None:
    print("\n=== Product summary ===")
    print(f"type:       {summary.get('type')}")
    print(f"goal:       {summary.get('goal')}")
    print(f"locales:    {summary.get('locales')}")
    print(f"channels:   {summary.get('channels')}")
    print(f"frontend:   {summary.get('frontend')}")
    print(f"backend:    {summary.get('backend')}")
    print(f"database:   {summary.get('database')}")
    print(f"plan_tier:  {summary.get('plan_tier')}")
    print(f"plugins:    {summary.get('plugins')}")
    print(f"module:     {summary.get('module')}")
    print("=======================\n")


def run_packager_with_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "module": summary.get("module") or "product",
        "kind": summary.get("type") or "app",
        "backend": summary.get("backend") or "fastapi",
        "database": summary.get("database") or "sqlite",
        "plan_tier": (summary.get("plan_tier") or "starter"),
        "plugins": summary.get("plugins") or [],
    }
    return packager.handle(payload)


def main() -> None:
    print("Velu console assistant")
    print("----------------------")
    print("Type an idea and press Enter.")
    print("Commands: 'q' / 'quit' to exit.")
    print()

    while True:
        try:
            idea = input("Idea> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not idea:
            continue
        if idea.lower() in {"q", "quit"}:
            print("Bye.")
            break

        print("\nRunning intake…")
        result = run_intake(idea)
        summary = extract_summary(result)
        print_summary(summary)

        blueprint = result.get("blueprint") or {}
        history: List[Dict[str, Any]]
        history, history_index = blueprint_history.init_history(blueprint)

        while True:
            try:
                raw_cmd = input(
                    "[enter]=new idea, "
                    "'d'=dump JSON, "
                    "'p'=packager, "
                    "'edit <rule>', "
                    "'ai <rule>', "
                    "'u'=undo, 'r'=redo, "
                    "'h'=history, "
                    "'e' or 'export [file]'=export blueprint, "
                    "'q'=quit\n"
                    "cmd> "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                return

            cmd = raw_cmd.lower()

            if cmd in {"", "n"}:
                print()
                break
            if cmd in {"?", "help"}:
                print(format_help())
                print()
                continue

            if cmd in {"q", "quit"}:
                print("Bye.")
                return

            if cmd == "d":
                print(json.dumps(result, indent=2, default=str))
                print()
                continue

            if cmd == "p":
                print("\nRunning packager…")
                pkg_result = run_packager_with_summary(summary)
                print(json.dumps(pkg_result, indent=2, default=str))
                print()
                continue

            if cmd.startswith("edit "):
                instruction = raw_cmd[5:].strip()
                if not instruction:
                    print("Usage: edit <instruction>")
                    continue

                blueprint = result["blueprint"]
                new_bp = blueprint_editor.edit_blueprint(blueprint, instruction)
                result["blueprint"] = new_bp

                history, history_index = blueprint_history.apply_edit(
                    history, history_index, new_bp
                )

                print("\nBlueprint updated (edit):")
                print(f"  frontend.framework = " f"{new_bp.get('frontend', {}).get('framework')}")
                print(f"  database.engine    = " f"{new_bp.get('database', {}).get('engine')}")
                print(f"  plugins            = {new_bp.get('plugins')}")
                print()
                continue

            if cmd.startswith("ai "):
                instruction = raw_cmd[3:].strip()
                if not instruction:
                    print("Usage: ai <instruction>")
                    continue

                blueprint = result["blueprint"]
                new_bp = blueprint_editor.edit_blueprint(blueprint, instruction)
                result["blueprint"] = new_bp

                history, history_index = blueprint_history.apply_edit(
                    history, history_index, new_bp
                )

                print("\n(LLM-style edit applied):")
                print(f"  frontend.framework = " f"{new_bp.get('frontend', {}).get('framework')}")
                print(f"  database.engine    = " f"{new_bp.get('database', {}).get('engine')}")
                print(f"  plugins            = {new_bp.get('plugins')}")
                print()
                continue

            if cmd in {"u", "undo"}:
                try:
                    history_index, bp = blueprint_history.undo(history, history_index)
                    result["blueprint"] = bp
                    print(f"\nUndo: now at revision #{history_index}")
                    print(f"  frontend.framework = " f"{bp.get('frontend', {}).get('framework')}")
                    print(f"  database.engine    = " f"{bp.get('database', {}).get('engine')}")
                    print(f"  plugins            = {bp.get('plugins')}")
                    print()
                except ValueError as exc:
                    print(f"Cannot undo: {exc}")
                continue

            if cmd in {"r", "redo"}:
                try:
                    history_index, bp = blueprint_history.redo(history, history_index)
                    result["blueprint"] = bp
                    print(f"\nRedo: now at revision #{history_index}")
                    print(f"  frontend.framework = " f"{bp.get('frontend', {}).get('framework')}")
                    print(f"  database.engine    = " f"{bp.get('database', {}).get('engine')}")
                    print(f"  plugins            = {bp.get('plugins')}")
                    print()
                except ValueError as exc:
                    print(f"Cannot redo: {exc}")
                continue

            if cmd in {"h", "history"}:
                print("\nHistory:")
                for i, bp in enumerate(history):
                    mark = "*" if i == history_index else " "
                    f_fw = bp.get("frontend", {}).get("framework")
                    db_eng = bp.get("database", {}).get("engine")
                    plugins = bp.get("plugins") or []
                    print(f" {mark} [{i}] frontend={f_fw}, db={db_eng}, plugins={plugins}")
                print()
                continue

            if cmd.startswith("e") or cmd.startswith("export"):
                parts = raw_cmd.split(maxsplit=1)
                filename = parts[1].strip() if len(parts) == 2 else "blueprint.json"

                bp = result.get("blueprint") or {}
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(bp, f, indent=2, default=str)
                    print(f"\nExported blueprint to {filename}\n")
                except Exception as exc:
                    print(f"Failed to export blueprint: {exc}")
                continue

            print("Unknown command, use [enter], d, p, edit, ai, u, r, h, e, or q.\n")


if __name__ == "__main__":
    main()
