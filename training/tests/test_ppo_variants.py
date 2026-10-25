from __future__ import annotations

import numpy as np
import torch
import train_ppo


def test_rollout_separates_scaffold_and_opponent_variants(monkeypatch) -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.actors = iter([1, 0, None])
            self.current = None
            self.heuristic_calls: list[tuple[int, str | None]] = []

        def new_game(self, seed: int, round_wind: str) -> int:
            assert seed == 42 and round_wind == "F1"
            return 7

        def actor(self, game: int) -> int | None:
            assert game == 7
            self.current = next(self.actors)
            return self.current

        def observe(self, game: int, seat: int) -> tuple[dict, int | None]:
            assert game == 7 and seat == 0
            if self.current is None:
                return {
                    "phase": {
                        "outcome": {
                            "kind": "win",
                            "deltas": [32, -16, -8, -8],
                        }
                    }
                }, None
            return {
                "seat": 0,
                "phase": {"kind": "discard"},
                "legal_action_ids": [12, 13],
            }, 0

        def heuristic_action(self, game: int, seat: int, variant: str | None) -> int:
            assert game == 7
            self.heuristic_calls.append((seat, variant))
            return 12

        def step(self, game: int, seat: int, action_id: int) -> dict:
            assert game == 7 and action_id == 12
            return {}

        def close(self, game: int) -> None:
            assert game == 7

    monkeypatch.setattr(train_ppo, "sample_action", lambda *args: (12, -0.1, 0.0))
    monkeypatch.setattr(train_ppo, "encode_observation", lambda observation: np.zeros(771, dtype=np.float32))
    engine = FakeEngine()
    model = torch.nn.Linear(1, 1)
    rows, outcome = train_ppo.rollout_game(
        engine,
        model,
        42,
        0,
        torch.device("cpu"),
        10,
        "none",
        "closed",
        "default",
    )
    assert engine.heuristic_calls == [(1, "default"), (0, "closed")]
    assert len(rows) == 1 and rows[0]["action"] == 12
    assert outcome["deltas"][0] == 32
