from __future__ import annotations

import json

import numpy as np
import pytest
import torch
from generate_dagger import learned_action
from mahjong_ai.actions import (
    ADDED_KONG_START,
    CONCEALED_KONG_START,
    DISCARD_START,
    PASS,
)
from mahjong_ai.features import FEATURE_SIZE, HINT_SHANTEN_OFFSET, HINT_UKEIRE_OFFSET
from mahjong_ai.teachers import resolve_scaffold_variant
from train_bc import (
    BatchSuitAugmenter,
    SuitAugmentedDataset,
    VectorizedLoader,
    action_category_metrics,
    load_versioned_dataset,
    restrict_to_teacher_optimal,
)


def test_batch_augmentation_matches_reference_for_every_action_and_permutation() -> None:
    rows = 122
    rng = np.random.default_rng(17)
    features = rng.random((rows, FEATURE_SIZE), dtype=np.float32)
    masks = rng.random((rows, rows)) > 0.5
    np.fill_diagonal(masks, True)
    actions = np.arange(rows)
    reference = SuitAugmentedDataset(features, masks, actions, np.zeros(rows, dtype=np.float32), seed=17)
    augmenter = BatchSuitAugmenter(torch.device("cpu"))
    for permutation in range(6):
        class FixedRng:
            def __init__(self, value):
                self.value = value

            def integers(self, _):
                return self.value
        reference.rng = FixedRng(permutation)
        actual = augmenter(torch.from_numpy(features), torch.from_numpy(masks), torch.from_numpy(actions),
                           torch.full((rows,), permutation))
        expected = [reference[index] for index in range(rows)]
        for field in range(3):
            assert torch.equal(actual[field], torch.stack([row[field] for row in expected]))
        assert actual[1][torch.arange(rows), actual[2]].all()


def test_vectorized_loader_covers_every_row_including_final_batch() -> None:
    features = torch.arange(23).reshape(-1, 1)
    dataset = torch.utils.data.TensorDataset(features, features * 2)
    for shuffle in (False, True):
        batches = list(VectorizedLoader(dataset, 7, shuffle))
        result = torch.cat([batch[0] for batch in batches]).flatten()
        assert torch.equal(result.sort().values, torch.arange(23))
        assert all(torch.equal(batch[1], batch[0] * 2) for batch in batches)
        assert len(batches[-1][0]) == 2


def test_action_category_metrics_cover_catalog_boundaries() -> None:
    actions = torch.tensor([0, 1, 2, 3, 10, 12, 46, 80, 114])
    predictions = torch.tensor([0, 1, 2, 3, 10, 12, 46, 80, 113])
    metrics = action_category_metrics(predictions, actions)
    assert list(metrics) == [
        "hu",
        "pass",
        "expose-flower",
        "chow",
        "pung-kong",
        "discard",
        "concealed-kong",
        "added-kong",
        "discard-flower",
    ]
    assert metrics["discard-flower"] == {"correct": 0, "total": 1, "accuracy": 0.0}


def test_suit_augmentation_keeps_the_discard_legal() -> None:
    features = np.zeros((1, FEATURE_SIZE), dtype=np.float32)
    masks = np.zeros((1, 122), dtype=np.bool_)
    masks[0, DISCARD_START] = True
    dataset = SuitAugmentedDataset(
        features,
        masks,
        np.asarray([DISCARD_START], dtype=np.int16),
        np.asarray([0.0], dtype=np.float32),
        seed=7,
    )
    seen = set()
    for _ in range(40):
        augmented_features, augmented_mask, action, _ = dataset[0]
        assert augmented_features.shape == (FEATURE_SIZE,)
        assert augmented_mask.shape == (122,)
        assert bool(augmented_mask[int(action)])
        assert int(action) in {DISCARD_START, DISCARD_START + 9, DISCARD_START + 18}
        seen.add(int(action))
    assert seen == {DISCARD_START, DISCARD_START + 9, DISCARD_START + 18}


def test_suit_augmentation_permutes_all_tile_indexed_actions_together() -> None:
    rows = 3
    features = np.zeros((rows, FEATURE_SIZE), dtype=np.float32)
    masks = np.zeros((rows, 122), dtype=np.bool_)
    actions = np.asarray(
        [DISCARD_START + 1, CONCEALED_KONG_START + 10, ADDED_KONG_START + 25],
        dtype=np.int16,
    )
    action_offsets = (DISCARD_START, CONCEALED_KONG_START, ADDED_KONG_START)
    for row, (action, action_start) in enumerate(zip(actions, action_offsets, strict=True)):
        features[row, int(action) - action_start] = 1.0
        masks[row, action] = True
    masks[:, PASS] = True
    masks[:, 5] = True
    dataset = SuitAugmentedDataset(features, masks, actions, np.zeros(rows, dtype=np.float32), seed=11)

    seen_suits = {DISCARD_START: set(), CONCEALED_KONG_START: set(), ADDED_KONG_START: set()}
    expected_ranks = {
        DISCARD_START: 1,
        CONCEALED_KONG_START: 1,
        ADDED_KONG_START: 7,
    }
    for _ in range(60):
        for row, action_start in enumerate(action_offsets):
            augmented_features, augmented_mask, action, _ = dataset[row]
            kind = int(action) - action_start
            assert 0 <= kind < 27
            assert kind % 9 == expected_ranks[action_start]
            assert augmented_features[kind] == pytest.approx(1.0)
            assert bool(augmented_mask[int(action)])
            assert bool(augmented_mask[PASS])
            assert bool(augmented_mask[5])
            assert int(augmented_mask.sum()) == 3
            seen_suits[action_start].add(kind // 9)
    assert all(len(suits) == 3 for suits in seen_suits.values())


def test_discard_scope_uses_teacher_outside_standard_discards() -> None:
    class FailingModel:
        def __call__(self, *args, **kwargs):
            raise AssertionError("model must only be called for standard discard decisions")

    class FakeEngine:
        def heuristic_action(self, game: int, seat: int, variant: str | None = None) -> int:
            assert game == 1 and seat == 2
            assert variant == "closed"
            return 7

    observation = {
        "seat": 2,
        "phase": {"kind": "flower"},
        "legal_action_ids": [2, 120],
    }
    assert (
        learned_action(
            FakeEngine(),
            FailingModel(),
            observation,
            1,
            "discard",
            None,
            scaffold_variant="closed",
        )
        == 7
    )


def test_teacher_optimal_guard_keeps_only_best_tied_discards() -> None:
    features = np.zeros((1, FEATURE_SIZE), dtype=np.float32)
    masks = np.zeros((1, 122), dtype=np.bool_)
    masks[0, DISCARD_START : DISCARD_START + 3] = True
    features[0, HINT_SHANTEN_OFFSET + 0] = 2 / 8
    features[0, HINT_UKEIRE_OFFSET + 0] = 4 / 136
    features[0, HINT_SHANTEN_OFFSET + 1] = 2 / 8
    features[0, HINT_UKEIRE_OFFSET + 1] = 4 / 136
    features[0, HINT_SHANTEN_OFFSET + 2] = 3 / 8
    features[0, HINT_UKEIRE_OFFSET + 2] = 9 / 136
    guarded = restrict_to_teacher_optimal(features, masks)
    assert np.flatnonzero(guarded).tolist() == [DISCARD_START, DISCARD_START + 1]


def test_versioned_dataset_rejects_stale_feature_semantics(tmp_path) -> None:
    dataset = tmp_path / "stale.npz"
    np.savez(dataset, features=np.zeros((1, FEATURE_SIZE), dtype=np.float32))
    dataset.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "ruleset_id": "mcr-wmo2006-stage1",
                "observation_version": 1,
                "feature_encoding_version": 4,
                "action_catalog_version": 1,
                "feature_size": FEATURE_SIZE,
                "action_count": 122,
            }
        )
    )
    with pytest.raises(ValueError, match="dataset contract mismatch"):
        load_versioned_dataset(dataset)


def test_scaffold_variant_prefers_explicit_then_checkpoint_then_default() -> None:
    checkpoint = {"teacher_variant": "closed", "scaffold_variant": "tenpai-only"}
    assert resolve_scaffold_variant(None, checkpoint) == "tenpai-only"
    assert resolve_scaffold_variant("no-chow", checkpoint) == "no-chow"
    assert resolve_scaffold_variant(None, {}) == "default"
