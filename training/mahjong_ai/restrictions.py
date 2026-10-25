from __future__ import annotations

from .actions import DISCARD_START


def teacher_optimal_discards(observation: dict, legal_actions: set[int]) -> set[int]:
    """Return legal discards tied for the teacher's structural optimum."""
    candidates = [
        action for action in legal_actions if DISCARD_START <= action < DISCARD_START + 34
    ]
    if not candidates:
        return set()
    hints = observation["discard_hints"]
    shanten = hints["shanten"]
    ukeire = hints["ukeire"]
    qualifying_waits = hints["qualifying_waits"]
    qualifying_value = hints["qualifying_value"]
    best_shanten = min(shanten[action - DISCARD_START] for action in candidates)
    best_value = max(
        qualifying_value[action - DISCARD_START]
        for action in candidates
        if shanten[action - DISCARD_START] == best_shanten
    )
    best_qualifying_waits = max(
        qualifying_waits[action - DISCARD_START]
        for action in candidates
        if shanten[action - DISCARD_START] == best_shanten
        and qualifying_value[action - DISCARD_START] == best_value
    )
    best_ukeire = max(
        ukeire[action - DISCARD_START]
        for action in candidates
        if shanten[action - DISCARD_START] == best_shanten
        and qualifying_value[action - DISCARD_START] == best_value
        and qualifying_waits[action - DISCARD_START] == best_qualifying_waits
    )
    return {
        action
        for action in candidates
        if shanten[action - DISCARD_START] == best_shanten
        and qualifying_value[action - DISCARD_START] == best_value
        and qualifying_waits[action - DISCARD_START] == best_qualifying_waits
        and ukeire[action - DISCARD_START] == best_ukeire
    }
