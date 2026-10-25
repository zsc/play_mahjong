from __future__ import annotations

import pytest
from compare_runs import paired_comparison


def report(deltas: list[int]) -> dict:
    return {
        "rows": [
            {"seed": 10 + index, "model_seat": index % 4, "model_delta": delta}
            for index, delta in enumerate(deltas)
        ]
    }


def test_paired_comparison_uses_matching_seed_and_seat() -> None:
    candidate = report([1, 2, 3, 4])
    baseline = report([0, 2, 1, 4])
    result = paired_comparison(candidate, baseline)
    assert result["games"] == 4
    assert result["mean_difference"] == pytest.approx(0.75)


def test_paired_comparison_rejects_duplicate_rows() -> None:
    candidate = report([1, 2])
    candidate["rows"].append(dict(candidate["rows"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        paired_comparison(candidate, report([0, 0]))


def test_paired_comparison_rejects_missing_rows() -> None:
    with pytest.raises(ValueError, match="different seed/seat"):
        paired_comparison(report([1, 2, 3]), report([0, 2]))


def test_paired_comparison_rejects_different_opponent_contracts() -> None:
    candidate = report([1, 2])
    baseline = report([0, 2])
    candidate["opponent_variant"] = "default"
    baseline["opponent_variant"] = "closed"
    with pytest.raises(ValueError, match="different comparison contracts"):
        paired_comparison(candidate, baseline)
