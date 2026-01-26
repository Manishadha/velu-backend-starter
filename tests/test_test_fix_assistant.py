# tests/test_test_fix_assistant.py
from __future__ import annotations

from services.agents import test_fix_assistant


def test_test_fix_assistant_no_failures():
    output = """
================================================== test session starts ===================================================
collected 3 items

tests/test_ok.py ...                                                                                               [100%]

=================================================== 3 passed in 0.10s ====================================================
"""
    res = test_fix_assistant.handle({"output": output})
    assert res["ok"] is True
    assert res["agent"] == "test_fix_assistant"
    summary = res["summary"]
    assert summary["total_issues"] == 0
    assert res["issues"] == []


def test_test_fix_assistant_single_failure():
    output = """
======================================================== FAILURES ========================================================
________________________________________________ test_something_broke ___________________________________________________

tmp_path = PosixPath('/tmp/pytest-of-mani/pytest-29/test_something_broke0')

    def test_something_broke(tmp_path):
>       assert False is True
E       assert False is True

tests/test_example.py:10: AssertionError
================================================ short test summary info =================================================
FAILED tests/test_example.py::test_something_broke - assert False is True
"""
    res = test_fix_assistant.handle({"output": output})
    assert res["ok"] is True
    summary = res["summary"]
    assert summary["total_issues"] == 1

    issues = res["issues"]
    assert len(issues) == 1
    issue = issues[0]
    assert issue["test"] == "tests/test_example.py::test_something_broke"
    assert issue["file"] == "tests/test_example.py"
    assert issue["message"] == "assert False is True"


def test_test_fix_assistant_multiple_failures():
    output = """
================================================ short test summary info =================================================
FAILED tests/test_one.py::test_a - ValueError: bad value
FAILED tests/test_two.py::test_b - AssertionError: boom
FAILED tests/test_two.py::test_c - IndexError: out of range
"""
    res = test_fix_assistant.handle({"text": output})
    assert res["ok"] is True
    summary = res["summary"]
    assert summary["total_issues"] == 3

    issues = res["issues"]
    tests = [i["test"] for i in issues]
    assert "tests/test_one.py::test_a" in tests
    assert "tests/test_two.py::test_b" in tests
    assert "tests/test_two.py::test_c" in tests
