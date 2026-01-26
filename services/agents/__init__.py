# services/agents/__init__.py
from __future__ import annotations
import subprocess  # nosec B404 - used for internal subprocess calls (pytest, etc.), not user input

from typing import Any, Callable, Dict

from . import (
    aggregate,
    ai_features,
    api_design,
    architecture,
    backend_scaffold,
    codegen,
    datamodel,
    executor,
    gitcommit,
    intake,
    lint,
    pipeline,
    planner,
    report,
    requirements,
    security_hardening,
    tester,
    testgen,
    ui_scaffold,
    autodev,
    hospital_codegen,
    hospital_apply_patches,
    packager,
    ai_architect,
    code_refiner,
    test_fix_assistant,
    debug_pipeline,
    chatbot_embed,
    runtime_planner,
    runtime_script_writer,
    mobile_scaffold,
    repo_summary,
    
    
)


HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "requirements": requirements.handle,
    "architecture": architecture.handle,
    "datamodel": datamodel.handle,
    "api_design": api_design.handle,
    "ui_scaffold": ui_scaffold.handle,
    "backend_scaffold": backend_scaffold.handle,
    "ai_features": ai_features.handle,
    "security_hardening": security_hardening.handle,
    "testgen": testgen.handle,
    "pipeline": pipeline.handle,
    "plan": planner.handle,
    "aggregate": aggregate.handle,
    "gitcommit": gitcommit.handle,
    "codegen": codegen.handle,
    "execute": executor.handle,
    "test": tester.handle,
    "report": report.handle,
    "intake": intake.handle,
    "lint": lint.handle,
    "autodev": autodev.handle,
    "hospital_codegen": hospital_codegen.handle,
    "hospital_apply_patches": hospital_apply_patches.handle,
    "packager": packager.handle,
    "ai_architect": ai_architect.handle,
    "code_refiner": code_refiner.handle,
    "test_fix_assistant": test_fix_assistant.handle,
    "debug_pipeline": debug_pipeline.handle,
    "chatbot_embed": chatbot_embed.handle,
    "runtime_planner": runtime_planner.handle,
    "runtime_script_writer": runtime_script_writer.handle,
    "mobile_scaffold": mobile_scaffold.handle,
    "repo_summary": repo_summary.handle,
     
}


def run_pytest_legacy(payload: Dict[str, Any]) -> Dict[str, Any]:

    """
    Lightweight pytest runner used by the 'test' queue task.

    Expected payload:
      {
        "rootdir": ".",
        "tests_path": "tests/test_hello_mod.py",
        "args": ["-q", "--maxfail=1", ...]
      }
    """
    rootdir = str(payload.get("rootdir", ".") or ".")
    tests_path = str(payload.get("tests_path", "tests") or "tests")
    extra_args = payload.get("args") or []
    if not isinstance(extra_args, list):
        extra_args = []

    cmd = ["pytest", tests_path, *[str(a) for a in extra_args]]

    proc = subprocess.run(  # nosec B603 - cmd is built from internal options, not untrusted input
        cmd,
        cwd=rootdir,
        capture_output=True,
        text=True,
    )

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
