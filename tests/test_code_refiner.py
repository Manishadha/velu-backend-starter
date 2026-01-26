# tests/test_code_refiner.py
from __future__ import annotations

from services.agents import code_refiner


def test_code_refiner_noop_on_clean_file():
    payload = {
        "files": [
            {
                "path": "services/app_server/main.py",
                "content": "def x() -> int:\n    return 1\n",
            }
        ]
    }
    res = code_refiner.handle(payload)
    assert res["ok"] is True
    assert res["agent"] == "code_refiner"
    summary = res["summary"]
    assert summary["total_files"] == 1
    assert summary["changed_files"] == 0
    files = res["files"]
    assert len(files) == 1
    assert files[0]["path"] == "services/app_server/main.py"
    assert files[0]["content"] == "def x() -> int:\n    return 1\n"


def test_code_refiner_trims_trailing_spaces_and_newlines():
    payload = {
        "files": [
            {
                "path": "services/api/app.py",
                "content": "def x():    \r\n    return 1\t\r\n\r\n",
            }
        ]
    }
    res = code_refiner.handle(payload)
    assert res["ok"] is True
    summary = res["summary"]
    assert summary["total_files"] == 1
    assert summary["changed_files"] == 1
    out = res["files"][0]["content"]
    assert out == "def x():\n    return 1\n"


def test_code_refiner_multiple_files_mixed_changes():
    payload = {
        "files": [
            {
                "path": "a.py",
                "content": "a = 1\n",
            },
            {
                "path": "b.py",
                "content": "b = 2  ",
            },
        ]
    }
    res = code_refiner.handle(payload)
    assert res["ok"] is True
    summary = res["summary"]
    assert summary["total_files"] == 2
    assert summary["changed_files"] == 1
    files = {f["path"]: f["content"] for f in res["files"]}
    assert files["a.py"] == "a = 1\n"
    assert files["b.py"] == "b = 2\n"
