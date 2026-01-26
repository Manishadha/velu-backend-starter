from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from services.app_server.schemas.blueprint import (
    Blueprint,
    BlueprintBackend,
    BlueprintDatabase,
    BlueprintFrontend,
    BlueprintLocalization,
)
from services.console import runtime_runner


def _make_blueprint(frontend: str, backend: str, project_id: str) -> Blueprint:
    return Blueprint(
        id=project_id,
        name="Runtime Demo CLI",
        kind="web_app",
        frontend=BlueprintFrontend(
            framework=frontend,
            language="typescript",
            targets=["web"],
        ),
        backend=BlueprintBackend(
            framework=backend,
            language="python",
            style="rest",
        ),
        database=BlueprintDatabase(
            engine="sqlite",
            mode="single_node",
        ),
        localization=BlueprintLocalization(
            default_language="en",
            supported_languages=["en"],
        ),
    )


def _build_runtime(frontend: str, backend: str, project_id: str) -> Dict[str, Any]:
    bp = _make_blueprint(frontend=frontend, backend=backend, project_id=project_id)
    runtime = runtime_runner.plan_from_payload({"blueprint": bp, "project_id": project_id})
    return runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="velu-runtime-plan",
        description="Print a runtime plan JSON for a simple demo blueprint.",
    )
    parser.add_argument(
        "--frontend",
        default="nextjs",
        help="Frontend framework, for example nextjs or react.",
    )
    parser.add_argument(
        "--backend",
        default="fastapi",
        help="Backend framework, for example fastapi or express.",
    )
    parser.add_argument(
        "--project-id",
        default="runtime_demo_cli",
        help="Project id to use in the runtime descriptor.",
    )

    args = parser.parse_args(argv)

    runtime = _build_runtime(
        frontend=str(args.frontend),
        backend=str(args.backend),
        project_id=str(args.project_id),
    )

    print(json.dumps(runtime, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
