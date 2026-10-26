import pytest
from arena import compare, play, seed_groups, summarize
from mahjong_ai.engine import MahjongEngine


def test_ci_uses_walls_not_correlated_seats():
    rows = [{"seed": seed, "model_seat": seat, "model_delta": value, "win": False, "discard": False, "draw": True}
            for seed, value in [(10, 0), (11, 4)] for seat in range(4)]
    result = summarize(rows)
    assert result["score"]["independent_wall_groups"] == 2
    assert result["score"]["standard_error"] == pytest.approx(2)
    assert compare(rows, rows)["ci95"] == [0, 0]
    with pytest.raises(ValueError, match="all four"):
        seed_groups(rows[:-1])
    with pytest.raises(ValueError, match="duplicate"):
        seed_groups(rows+rows[:1])


def test_symmetric_frozen_policy_has_zero_wall_group_score():
    with MahjongEngine() as engine:
        rows = [play(engine, {}, 40000000, seat, "qualified", "qualified") for seat in range(4)]
    assert seed_groups(rows) == {40000000: 0.0}
    assert len({row["decisions"] for row in rows}) == 1
    assert sum(row["win"] for row in rows) in (0, 1)
