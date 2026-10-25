from __future__ import annotations

import numpy as np
import pytest
import torch
from generate_bc import play_game
from mahjong_ai.actions import HU
from mahjong_ai.engine import EngineError, MahjongEngine
from model import PolicyValueNet
from train_ppo import rollout_batched, rollout_range


@pytest.mark.parametrize("variant", ["default", "closed", "closed-kong", "qualified-tenpai", "qualified-best"])
def test_teacher_chunk_matches_reference(variant):
    with MahjongEngine() as engine:
        for seed in range(12000000, 12000008):
            expected, old = play_game(engine, seed, "F1", 2000, variant, chunk_size=0)
            actual, new = play_game(engine, seed, "F1", 2000, variant, chunk_size=7)
            assert actual == expected
            assert len(old) == len(new)
            for a, b in zip(old, new, strict=True):
                assert a.keys() == b.keys()
                for key in a:
                    np.testing.assert_array_equal(a[key], b[key])


def test_native_advance_matches_every_decision_and_outcome():
    with MahjongEngine() as engine:
        for seed in range(12000000, 12000024):
            seat = seed % 4
            reference, fast = engine.new_game(seed), engine.new_game(seed)
            request = {"game": fast, "model_seat": seat, "max_steps": 2000,
                       "scaffold_variant": "qualified-tenpai", "opponent_variant": "qualified-tenpai"}
            response = engine.advance_batch([request])[0]
            while (actor := engine.actor(reference)) is not None:
                obs, _ = engine.observe(reference, actor)
                action = engine.heuristic_action(reference, actor, "qualified-tenpai")
                if actor == seat and obs["phase"]["kind"] == "discard" and HU not in obs["legal_action_ids"]:
                    assert response["observation"] == obs
                    assert response["teacher_action"] == action
                    # Deliberately explore non-teacher discards too.
                    action = obs["legal_action_ids"][obs["revision"] % len(obs["legal_action_ids"])]
                    response = engine.advance_batch([request | {"action_id": action}])[0]
                engine.step(reference, actor, action)
            terminal, _ = engine.observe(reference, 0)
            assert response["outcome"] == terminal["phase"]["outcome"]
            engine.validate(reference)
            engine.validate(fast)
            engine.close(reference)
            engine.close(fast)


def test_batch_error_rolls_back_all_games():
    with MahjongEngine() as engine:
        games = [engine.new_game(31), engine.new_game(32)]
        requests = [{"game": game, "model_seat": 0, "max_steps": 2000,
                     "scaffold_variant": "qualified-tenpai", "opponent_variant": "qualified-tenpai"}
                    for game in games]
        before = [engine.observe(game, 0) for game in games]
        with pytest.raises(EngineError):
            engine.advance_batch([requests[0], requests[1] | {"action_id": 999}])
        assert [engine.observe(game, 0) for game in games] == before


def test_batched_single_lane_matches_legacy_stochastic_rollout():
    torch.set_num_threads(1)
    torch.manual_seed(99)
    model = PolicyValueNet(hidden=32).eval()
    arguments = (model, torch.device("cpu"), 12000000, 8, 0, 1, 2000,
                 "none", "qualified-tenpai", "qualified-tenpai", .99, .95)
    with MahjongEngine() as engine:
        torch.manual_seed(55)
        old, outcomes, scores = rollout_range(engine, *arguments)
        torch.manual_seed(55)
        new, new_outcomes, new_scores = rollout_batched(engine, *arguments, batch_size=1)
    assert outcomes == new_outcomes and scores == new_scores
    assert len(old) == len(new)
    for a, b in zip(old, new, strict=True):
        for key in a:
            np.testing.assert_array_equal(a[key], b[key])


def test_multi_lane_reproducible_and_log_prob_matches_frozen_policy():
    torch.set_num_threads(1)
    torch.manual_seed(99)
    model = PolicyValueNet(hidden=32).eval()
    arguments = (model, torch.device("cpu"), 12000000, 8, 0, 1, 2000,
                 "none", "qualified-tenpai", "qualified-tenpai", .99, .95)
    with MahjongEngine() as engine:
        torch.manual_seed(55)
        rows, outcomes, scores = rollout_batched(engine, *arguments, batch_size=4)
        torch.manual_seed(55)
        replay, replay_outcomes, replay_scores = rollout_batched(engine, *arguments, batch_size=4)
    assert outcomes == replay_outcomes and scores == replay_scores
    for a, b in zip(rows, replay, strict=True):
        for key in a:
            np.testing.assert_array_equal(a[key], b[key])
    with torch.inference_mode():
        logits, values = model(torch.from_numpy(np.stack([r["features"] for r in rows])),
                               torch.from_numpy(np.stack([r["mask"] for r in rows])))
        actions = torch.tensor([r["action"] for r in rows])
        probabilities = torch.log_softmax(logits, dim=1).gather(1, actions[:, None]).squeeze(1)
    np.testing.assert_allclose(probabilities.numpy(), [r["old_log_probability"] for r in rows], atol=2e-6)
    np.testing.assert_allclose(values.numpy(), [r["value"] for r in rows], atol=2e-6)
    assert all(r["mask"][r["action"]] for r in rows)
    assert sum(r["reward"] for r in rows) == sum(scores) / 64.0
