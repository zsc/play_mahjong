from __future__ import annotations

import copy

import numpy as np
import pytest
from mahjong_ai.actions import DISCARD_START, HU, PASS
from mahjong_ai.engine import MahjongEngine
from mahjong_ai.features import (
    FEATURE_ENCODING_VERSION,
    FEATURE_SIZE,
    action_mask,
    encode_observation,
)
from mahjong_ai.teachers import HEURISTIC_VARIANTS


def test_initial_observation_and_action_mask() -> None:
    with MahjongEngine() as engine:
        game = engine.new_game(7, "F1")
        observation, actor = engine.observe(game, 0)
        assert actor == 0
        assert encode_observation(observation).shape == (FEATURE_SIZE,)
        assert FEATURE_ENCODING_VERSION == 6
        mask = action_mask(observation)
        assert mask.sum() > 0
        assert len(observation["legal_action_ids"]) == len(set(observation["legal_action_ids"]))


@pytest.mark.parametrize("variant", HEURISTIC_VARIANTS)
def test_heuristic_teacher_respects_mask(variant: str) -> None:
    with MahjongEngine() as engine:
        game = engine.new_game(9, "F1")
        for _ in range(20):
            actor = engine.actor(game)
            if actor is None:
                break
            observation, _ = engine.observe(game, actor)
            action = engine.heuristic_action(game, actor, variant)
            assert action_mask(observation)[action]
            engine.step(game, actor, action)


def test_closed_heuristic_passes_when_no_hu_is_available() -> None:
    with MahjongEngine() as engine:
        game = engine.new_game(1, "F1")
        found_response = False
        for _ in range(200):
            actor = engine.actor(game)
            if actor is None:
                break
            observation, _ = engine.observe(game, actor)
            if observation["phase"]["kind"] == "response":
                legal = set(observation["legal_action_ids"])
                closed_action = engine.heuristic_action(game, actor, "closed")
                assert closed_action in legal
                assert closed_action == (HU if HU in legal else PASS)
                found_response = True
                break
            engine.step(game, actor, engine.heuristic_action(game, actor))
        assert found_response


def test_public_meld_tiles_are_encoded() -> None:
    with MahjongEngine() as engine:
        game = engine.new_game(7, "F1")
        observation, _ = engine.observe(game, 0)
        chow = copy.deepcopy(observation)
        pung = copy.deepcopy(observation)
        chow["melds"][0] = [{"kind": "chow", "tile": "W3", "concealed": False}]
        pung["melds"][0] = [{"kind": "pung", "tile": "W3", "concealed": False}]
        assert not np.array_equal(encode_observation(chow), encode_observation(pung))


def test_flower_in_river_does_not_break_encoding() -> None:
    with MahjongEngine() as engine:
        game = engine.new_game(7, "F1")
        observation, _ = engine.observe(game, 0)
        observation["rivers"][0] = ["a", "W3"]
        encoded = encode_observation(observation)
        assert encoded.shape == (FEATURE_SIZE,)
        assert encoded[312 + 2] == np.float32(0.25)
        assert encoded[448 + 2] == np.float32(1.0)


def test_discard_hints_match_the_teacher_choice() -> None:
    with MahjongEngine() as engine:
        game = engine.new_game(19, "F1")
        for _ in range(80):
            actor = engine.actor(game)
            if actor is None:
                break
            observation, _ = engine.observe(game, actor)
            if observation["phase"]["kind"] == "discard":
                hints = observation["discard_hints"]
                candidates = [
                    kind
                    for kind, count in enumerate(observation["hand"])
                    if count > 0 and hints["shanten"][kind] >= 0
                ]
                expected_kind = min(
                    candidates,
                    key=lambda kind: (
                        hints["shanten"][kind],
                        -hints["qualifying_value"][kind],
                        -hints["qualifying_waits"][kind],
                        -hints["ukeire"][kind],
                        -kind,
                    ),
                )
                assert engine.heuristic_action(game, actor) == DISCARD_START + expected_kind
            engine.step(game, actor, engine.heuristic_action(game, actor))
