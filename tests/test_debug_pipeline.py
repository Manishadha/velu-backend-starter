# tests/test_debug_pipeline.py
from __future__ import annotations

from services.agents import debug_pipeline


def test_debug_pipeline_no_failures_no_code():
    output = """
================================================== test session starts ===================================================
collected 2 items

tests/test_ok.py ..                                                                                               [100%]

=================================================== 2 passed in 0.10s ====================================================
"""
    res = debug_pipeline.handle({"test_output": output})
    assert res["ok"] is True
    assert res["agent"] == "debug_pipeline"

    issues = res["issues"]
    assert isinstance(issues, list)
    assert issues == []

    test_analysis = res["test_analysis"]
    assert test_analysis["summary"]["total_issues"] == 0

    assert res["refiner"] is None or res["refiner"] == {}
    assert (
        res["analysis"] is None
        or res["analysis"] == {}
        or res["analysis"]["agent"] == "ai_architect"
    )


def test_debug_pipeline_single_failure_with_code():
    output = """
================================================ short test summary info =================================================
FAILED tests/test_example.py::test_something - AssertionError: boom
"""
    code = "def add(a, b):\n    return a+b\n"
    res = debug_pipeline.handle(
        {
            "output": output,
            "code": code,
            "language": "python",
            "path": "src/example.py",
        }
    )

    assert res["ok"] is True
    assert res["agent"] == "debug_pipeline"

    issues = res["issues"]
    assert len(issues) == 1
    issue = issues[0]
    assert issue["test"] == "tests/test_example.py::test_something"
    assert issue["file"] == "tests/test_example.py"
    assert "boom" in issue["message"]

    refiner = res["refiner"]
    assert refiner is not None
    assert refiner["agent"] == "code_refiner"

    analysis = res["analysis"]
    if analysis is not None:
        assert analysis["agent"] == "ai_architect"


def test_debug_pipeline_multiple_failures_text_key():
    output = """
================================================ short test summary info =================================================
FAILED tests/test_one.py::test_a - ValueError: bad value
FAILED tests/test_two.py::test_b - AssertionError: boom
"""
    res = debug_pipeline.handle({"text": output})
    assert res["ok"] is True
    issues = res["issues"]
    assert len(issues) == 2
    tests = {i["test"] for i in issues}
    assert "tests/test_one.py::test_a" in tests
    assert "tests/test_two.py::test_b" in tests
