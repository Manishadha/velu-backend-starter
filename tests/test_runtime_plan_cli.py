from __future__ import annotations

from services.console import runtime_plan_cli


def test_runtime_plan_cli_default(capsys) -> None:
    code = runtime_plan_cli.main([])
    assert code == 0
    out = capsys.readouterr().out
    assert '"project_id": "runtime_demo_cli"' in out
    assert '"id": "api"' in out
    assert '"id": "web"' in out


def test_runtime_plan_cli_node_react(capsys) -> None:
    code = runtime_plan_cli.main(
        ["--frontend", "react", "--backend", "express", "--project-id", "node_demo_cli"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert '"project_id": "node_demo_cli"' in out
    assert '"id": "api"' in out
    assert '"id": "web"' in out
