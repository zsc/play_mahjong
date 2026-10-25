from __future__ import annotations

import pytest
from merge_runs import merge_reports


def report(start: int, deltas: list[int]) -> dict:
    return {
        "policy": "heuristic",
        "model_scope": None,
        "discard_guard": None,
        "checkpoint": None,
        "opponent": "teacher",
        "seat_rotation": "model seat rotates 0,1,2,3",
        "rows": [
            {
                "seed": start + index,
                "model_seat": index % 4,
                "model_delta": delta,
                "outcome": "win",
                "winner": index % 4,
                "discarder": None,
            }
            for index, delta in enumerate(deltas)
        ],
    }


def test_merge_reports_recomputes_rates_and_rejects_duplicates() -> None:
    merged = merge_reports([report(10, [1, 0]), report(12, [-1, 2])])
    assert merged["games"] == 4
    assert merged["mean_net_score"] == pytest.approx(0.5)
    assert merged["win_rate"] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="duplicate"):
        merge_reports([report(10, [1]), report(10, [1])])
