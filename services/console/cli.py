from __future__ import annotations

import argparse
import json
import os
import platform
import sys


DEFAULT_VERSION = "0.1.0"


def cmd_version(args: argparse.Namespace) -> None:
    print(f"Velu CLI {DEFAULT_VERSION}")


def cmd_doctor(args: argparse.Namespace) -> None:
    info = {
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "has_openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        "chat_backend": os.environ.get("VELU_CHAT_BACKEND") or "rules",
    }
    print("Velu doctor report")
    print(json.dumps(info, indent=2))


def cmd_list_pipelines(args: argparse.Namespace) -> None:
    pipelines = [
        {"id": "team_dashboard", "kind": "web_app"},
        {"id": "product_catalog_web_1", "kind": "web_app"},
        {"id": "product_catalog_web_2", "kind": "web_app"},
    ]
    print(json.dumps({"pipelines": pipelines}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="velu",
        description="Velu CLI entrypoint",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ver = sub.add_parser("version")
    p_ver.set_defaults(func=cmd_version)

    p_doc = sub.add_parser("doctor")
    p_doc.set_defaults(func=cmd_doctor)

    p_lp = sub.add_parser("list-pipelines")
    p_lp.set_defaults(func=cmd_list_pipelines)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
