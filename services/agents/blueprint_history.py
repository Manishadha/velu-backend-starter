from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple

Blueprint = Dict[str, Any]
History = List[Blueprint]


def init_history(blueprint: Blueprint) -> Tuple[History, int]:
    """
    Start a new history with a single snapshot (index 0).
    """
    return [deepcopy(blueprint)], 0


def apply_edit(history: History, index: int, new_bp: Blueprint) -> Tuple[History, int]:
    """
    Record a new blueprint version.

    - If we are in the middle of history (after undo),
      drop all "future" snapshots.
    - Append the new version.
    - Return updated history and new index.
    """
    if not history:
        history = []

    if 0 <= index < len(history) - 1:
        history = history[: index + 1]

    history.append(deepcopy(new_bp))
    new_index = len(history) - 1
    return history, new_index


def undo(history: History, index: int) -> Tuple[int, Blueprint]:
    """
    Move one step back in history.

    - If we are already at the first version, stay there.
    """
    if not history:
        raise ValueError("Cannot undo: empty history")

    if index <= 0:

        return 0, deepcopy(history[0])

    new_index = index - 1
    return new_index, deepcopy(history[new_index])


def redo(history: History, index: int) -> Tuple[int, Blueprint]:
    """
    Move one step forward in history.

    - If we are already at the last version, stay there.
    """
    if not history:
        raise ValueError("Cannot redo: empty history")

    if index >= len(history) - 1:

        last_index = len(history) - 1
        return last_index, deepcopy(history[last_index])

    new_index = index + 1
    return new_index, deepcopy(history[new_index])
