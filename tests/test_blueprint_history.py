from __future__ import annotations

from services.agents import blueprint_history


def _bp(version: int) -> dict:
    return {
        "frontend": {"framework": f"f{version}"},
        "database": {"engine": "sqlite"},
        "plugins": [],
    }


def test_init_history_single_revision() -> None:
    bp = _bp(1)
    history, idx = blueprint_history.init_history(bp)
    assert idx == 0
    assert len(history) == 1
    assert history[0]["frontend"]["framework"] == "f1"


def test_apply_edit_appends_and_truncates_future() -> None:
    bp = _bp(1)
    history, idx = blueprint_history.init_history(bp)

    bp2 = _bp(2)
    history, idx = blueprint_history.apply_edit(history, idx, bp2)
    assert idx == 1
    assert len(history) == 2

    # Now "time travel" and edit from index 0 → future should be truncated
    bp3 = _bp(3)
    history, idx = blueprint_history.apply_edit(history, 0, bp3)
    assert idx == 1
    assert len(history) == 2
    assert history[1]["frontend"]["framework"] == "f3"


def test_undo_and_redo() -> None:
    bp = _bp(1)
    history, idx = blueprint_history.init_history(bp)

    for v in (2, 3):
        bpv = _bp(v)
        history, idx = blueprint_history.apply_edit(history, idx, bpv)

    assert idx == 2

    # undo twice
    idx, bp_prev = blueprint_history.undo(history, idx)
    assert idx == 1
    assert bp_prev["frontend"]["framework"] == "f2"

    idx, bp_prev = blueprint_history.undo(history, idx)
    assert idx == 0
    assert bp_prev["frontend"]["framework"] == "f1"

    # redo once
    idx, bp_next = blueprint_history.redo(history, idx)
    assert idx == 1
    assert bp_next["frontend"]["framework"] == "f2"
