from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
from mahjong_ai.actions import (
    ACTION_CATALOG_VERSION,
    ACTION_COUNT,
    ADDED_KONG_START,
    CONCEALED_KONG_START,
    DISCARD_START,
)
from mahjong_ai.features import (
    FEATURE_ENCODING_VERSION,
    FEATURE_SIZE,
    HINT_QUALIFYING_VALUE_OFFSET,
    HINT_QUALIFYING_WAITS_OFFSET,
    HINT_SHANTEN_OFFSET,
    HINT_UKEIRE_OFFSET,
    OBSERVATION_VERSION,
    SUIT_FEATURE_BLOCKS,
)
from mahjong_ai.teachers import DEFAULT_HEURISTIC_VARIANT, HEURISTIC_VARIANTS
from model import PolicyValueNet
from torch import nn
from torch.utils.data import DataLoader, Dataset, TensorDataset

RULESET_ID = "mcr-wmo2006-stage1"
SUIT_PERMUTATIONS = (
    (0, 1, 2),
    (0, 2, 1),
    (1, 0, 2),
    (1, 2, 0),
    (2, 0, 1),
    (2, 1, 0),
)
ACTION_CATEGORIES = (
    "hu",
    "pass",
    "expose-flower",
    "chow",
    "pung-kong",
    "discard",
    "concealed-kong",
    "added-kong",
    "discard-flower",
)
ACTION_CATEGORY_ENDS = np.asarray([1, 2, 3, 10, 12, 46, 80, 114, ACTION_COUNT])


class SuitAugmentedDataset(Dataset):
    def __init__(
        self,
        features: np.ndarray,
        masks: np.ndarray,
        actions: np.ndarray,
        returns: np.ndarray,
        seed: int,
    ) -> None:
        self.features = features
        self.masks = masks
        self.actions = actions
        self.returns = returns
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return len(self.actions)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        permutation = SUIT_PERMUTATIONS[int(self.rng.integers(len(SUIT_PERMUTATIONS)))]
        features = self.features[index].copy()
        for offset in SUIT_FEATURE_BLOCKS:
            block = features[offset : offset + 27].reshape(3, 9).copy()
            features[offset : offset + 27] = block[list(permutation)].reshape(-1)
        mask = self.masks[index].copy()
        tile_action_starts = (DISCARD_START, CONCEALED_KONG_START, ADDED_KONG_START)
        for action_start in tile_action_starts:
            suit_mask = mask[action_start : action_start + 27].reshape(3, 9).copy()
            mask[action_start : action_start + 27] = suit_mask[list(permutation)].reshape(-1)
        action = int(self.actions[index])
        for action_start in tile_action_starts:
            kind = action - action_start
            if 0 <= kind < 27:
                new_suit = permutation.index(kind // 9)
                action = action_start + new_suit * 9 + kind % 9
                break
        return (
            torch.from_numpy(features),
            torch.from_numpy(mask),
            torch.tensor(action, dtype=torch.long),
            torch.tensor(self.returns[index], dtype=torch.float32),
        )


class VectorizedLoader:
    """Index whole CPU batches, avoiding one Python Dataset call per row."""

    def __init__(self, dataset: TensorDataset, batch_size: int, shuffle: bool) -> None:
        self.dataset, self.batch_size, self.shuffle = dataset, batch_size, shuffle

    def __iter__(self):
        order = torch.randperm(len(self.dataset)) if self.shuffle else torch.arange(len(self.dataset))
        for indices in order.split(self.batch_size):
            yield tuple(tensor[indices] for tensor in self.dataset.tensors)


class BatchSuitAugmenter:
    def __init__(self, device: torch.device) -> None:
        feature_indices = np.tile(np.arange(FEATURE_SIZE), (6, 1))
        mask_indices = np.tile(np.arange(ACTION_COUNT), (6, 1))
        for index, permutation in enumerate(SUIT_PERMUTATIONS):
            for offset in SUIT_FEATURE_BLOCKS:
                feature_indices[index, offset:offset + 27] = (
                    np.arange(offset, offset + 27).reshape(3, 9)[list(permutation)].reshape(-1)
                )
            for offset in (DISCARD_START, CONCEALED_KONG_START, ADDED_KONG_START):
                mask_indices[index, offset:offset + 27] = (
                    np.arange(offset, offset + 27).reshape(3, 9)[list(permutation)].reshape(-1)
                )
        self.feature_indices = torch.as_tensor(feature_indices, device=device)
        self.mask_indices = torch.as_tensor(mask_indices, device=device)
        self.action_indices = torch.as_tensor(np.argsort(mask_indices, axis=1), device=device)

    def __call__(self, features, masks, actions, permutations=None):
        if permutations is None:
            permutations = torch.randint(6, (len(actions),), device=features.device)
        return (
            features.gather(1, self.feature_indices[permutations]),
            masks.gather(1, self.mask_indices[permutations]),
            self.action_indices[permutations, actions],
        )


def seed_augmentation_worker(worker_id: int) -> None:
    info = torch.utils.data.get_worker_info()
    if info is not None and isinstance(info.dataset, SuitAugmentedDataset):
        info.dataset.rng = np.random.default_rng(info.dataset.seed + (worker_id + 1) * 104729)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_versioned_dataset(path: Path) -> tuple[np.lib.npyio.NpzFile, dict]:
    meta_path = path.with_suffix(".meta.json")
    if not meta_path.exists():
        raise ValueError(f"dataset metadata is missing: {meta_path}")
    metadata = json.loads(meta_path.read_text())
    expected = {
        "ruleset_id": RULESET_ID,
        "observation_version": OBSERVATION_VERSION,
        "feature_encoding_version": FEATURE_ENCODING_VERSION,
        "action_catalog_version": ACTION_CATALOG_VERSION,
        "feature_size": FEATURE_SIZE,
        "action_count": ACTION_COUNT,
    }
    mismatches = {
        key: (metadata.get(key), value)
        for key, value in expected.items()
        if metadata.get(key) != value
    }
    if mismatches:
        raise ValueError(f"dataset contract mismatch in {meta_path}: {mismatches}")
    teacher_variant = metadata.get("teacher_variant", DEFAULT_HEURISTIC_VARIANT)
    if teacher_variant not in HEURISTIC_VARIANTS:
        raise ValueError(f"unsupported teacher variant in {meta_path}: {teacher_variant}")
    return np.load(path), metadata


def choose_device(requested: str) -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def split_indices(seeds: np.ndarray, validation_fraction: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    unique = np.unique(seeds)
    if len(unique) < 2:
        raise ValueError("at least two games are required for a train/validation split")
    rng = np.random.default_rng(seed)
    shuffled = unique.copy()
    rng.shuffle(shuffled)
    validation_count = max(1, round(len(unique) * validation_fraction))
    validation_games = set(shuffled[:validation_count].tolist())
    is_validation = np.isin(seeds, list(validation_games))
    return np.flatnonzero(~is_validation), np.flatnonzero(is_validation)


def masked_cross_entropy(logits: torch.Tensor, actions: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
    masked = logits.masked_fill(~masks, torch.finfo(logits.dtype).min)
    return nn.functional.cross_entropy(masked, actions)


def action_category_metrics(predictions: torch.Tensor, actions: torch.Tensor) -> dict[str, dict[str, float | int]]:
    category_ids = np.searchsorted(ACTION_CATEGORY_ENDS, actions.cpu().numpy(), side="right")
    predicted = predictions.cpu().numpy()
    actual = actions.cpu().numpy()
    metrics: dict[str, dict[str, float | int]] = {}
    for category_id, category in enumerate(ACTION_CATEGORIES):
        selected = category_ids == category_id
        total = int(selected.sum())
        if total == 0:
            continue
        correct = int((predicted[selected] == actual[selected]).sum())
        metrics[category] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total,
        }
    return metrics


def restrict_to_teacher_optimal(features: np.ndarray, masks: np.ndarray) -> np.ndarray:
    discard_mask = masks[:, DISCARD_START : DISCARD_START + 34]
    shanten = features[:, HINT_SHANTEN_OFFSET : HINT_SHANTEN_OFFSET + 34]
    ukeire = features[:, HINT_UKEIRE_OFFSET : HINT_UKEIRE_OFFSET + 34]
    qualifying_waits = features[
        :, HINT_QUALIFYING_WAITS_OFFSET : HINT_QUALIFYING_WAITS_OFFSET + 34
    ]
    qualifying_value = features[
        :, HINT_QUALIFYING_VALUE_OFFSET : HINT_QUALIFYING_VALUE_OFFSET + 34
    ]
    best_shanten = np.min(np.where(discard_mask, shanten, np.inf), axis=1, keepdims=True)
    best_value = np.max(
        np.where(
            discard_mask & (shanten == best_shanten),
            qualifying_value,
            -np.inf,
        ),
        axis=1,
        keepdims=True,
    )
    best_qualifying_waits = np.max(
        np.where(
            discard_mask & (shanten == best_shanten) & (qualifying_value == best_value),
            qualifying_waits,
            -np.inf,
        ),
        axis=1,
        keepdims=True,
    )
    best_ukeire = np.max(
        np.where(
            discard_mask
            & (shanten == best_shanten)
            & (qualifying_value == best_value)
            & (qualifying_waits == best_qualifying_waits),
            ukeire,
            -np.inf,
        ),
        axis=1,
        keepdims=True,
    )
    optimal = (
        discard_mask
        & (shanten == best_shanten)
        & (qualifying_value == best_value)
        & (qualifying_waits == best_qualifying_waits)
        & (ukeire == best_ukeire)
    )
    restricted = np.zeros_like(masks)
    restricted[:, DISCARD_START : DISCARD_START + 34] = optimal
    return restricted


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a masked behavior-cloning policy on OCaml teacher data")
    parser.add_argument("--data", type=Path, nargs="+", required=True)
    parser.add_argument("--init-checkpoint", type=Path)
    parser.add_argument("--discard-only", action="store_true")
    parser.add_argument("--discard-guard", choices=("none", "teacher-optimal"), default="none")
    parser.add_argument("--scaffold-variant", choices=HEURISTIC_VARIANTS)
    parser.add_argument("--suit-augment", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("training/checkpoints/bc-smoke.pt"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--vectorized-batches", action="store_true")
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=256)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--value-weight", type=float, default=0.1)
    args = parser.parse_args()
    if args.num_workers < 0:
        raise SystemExit("--num-workers must be non-negative")
    if args.vectorized_batches and args.num_workers:
        raise SystemExit("--vectorized-batches requires --num-workers 0")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = choose_device(args.device)

    loaded = [load_versioned_dataset(path) for path in args.data]
    arrays = [item[0] for item in loaded]
    dataset_metadata = [item[1] for item in loaded]
    teacher_variants = {
        metadata.get("teacher_variant", DEFAULT_HEURISTIC_VARIANT)
        for metadata in dataset_metadata
    }
    if len(teacher_variants) != 1:
        raise ValueError(f"datasets use different teacher variants: {sorted(teacher_variants)}")
    teacher_variant = teacher_variants.pop()
    scaffold_variant = args.scaffold_variant or teacher_variant
    features = np.concatenate([data["features"] for data in arrays])
    if features.shape[1] != FEATURE_SIZE:
        raise ValueError(f"feature contract mismatch: {features.shape[1]} != {FEATURE_SIZE}")
    masks = np.concatenate([data["masks"] for data in arrays]).astype(np.bool_)
    actions = np.concatenate([data["actions"] for data in arrays]).astype(np.int64)
    returns = np.concatenate([data["returns"] for data in arrays]).astype(np.float32)
    seeds = np.concatenate([data["seeds"] for data in arrays])
    if args.discard_only:
        keep = (actions >= DISCARD_START) & (actions < DISCARD_START + 34)
        features = features[keep]
        masks = masks[keep]
        actions = actions[keep]
        returns = returns[keep]
        seeds = seeds[keep]
        restricted = np.zeros_like(masks)
        restricted[:, DISCARD_START : DISCARD_START + 34] = masks[
            :, DISCARD_START : DISCARD_START + 34
        ]
        masks = restricted
        if args.discard_guard == "teacher-optimal":
            masks = restrict_to_teacher_optimal(features, masks)
    elif args.discard_guard != "none":
        raise ValueError("--discard-guard requires --discard-only")
    if np.any(masks.sum(axis=1) == 0):
        raise ValueError("dataset contains empty legal masks")
    if np.any(~masks[np.arange(len(actions)), actions]):
        raise ValueError("dataset contains an illegal teacher action")

    train_indices, validation_indices = split_indices(seeds, args.validation_fraction, args.seed)
    train_dataset = (
        SuitAugmentedDataset(
            features[train_indices],
            masks[train_indices],
            actions[train_indices],
            returns[train_indices],
            args.seed + 1,
        )
        if args.suit_augment and not args.vectorized_batches
        else TensorDataset(
            torch.from_numpy(features[train_indices]),
            torch.from_numpy(masks[train_indices]),
            torch.from_numpy(actions[train_indices]),
            torch.from_numpy(returns[train_indices]),
        )
    )
    datasets = {
        "train": train_dataset,
        "validation": TensorDataset(
            torch.from_numpy(features[validation_indices]),
            torch.from_numpy(masks[validation_indices]),
            torch.from_numpy(actions[validation_indices]),
            torch.from_numpy(returns[validation_indices]),
        ),
    }
    loaders = {
        name: VectorizedLoader(dataset, args.batch_size, name == "train") if args.vectorized_batches else DataLoader(
            dataset,
            batch_size=args.batch_size,
            shuffle=name == "train",
            num_workers=args.num_workers,
            pin_memory=device.type == "cuda",
            persistent_workers=args.num_workers > 0,
            worker_init_fn=seed_augmentation_worker,
        )
        for name, dataset in datasets.items()
    }

    initial_checkpoint = None
    if args.init_checkpoint is not None:
        initial_checkpoint = torch.load(args.init_checkpoint, map_location="cpu", weights_only=True)
        if int(initial_checkpoint.get("feature_size", -1)) != FEATURE_SIZE:
            raise ValueError("initial checkpoint feature contract mismatch")
        if int(initial_checkpoint.get("action_count", -1)) != ACTION_COUNT:
            raise ValueError("initial checkpoint action contract mismatch")
        if int(initial_checkpoint.get("feature_encoding_version", -1)) != FEATURE_ENCODING_VERSION:
            raise ValueError("initial checkpoint feature encoding mismatch")
        if int(initial_checkpoint["hidden"]) != args.hidden:
            raise ValueError("--hidden must match the initial checkpoint")
    model = PolicyValueNet(hidden=args.hidden).to(device)
    if initial_checkpoint is not None:
        model.load_state_dict(initial_checkpoint["model"])
    optimiser = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    best_validation = float("inf")
    history: list[dict] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset_sha256 = hashlib.sha256(
        "".join(f"{path.name}:{sha256(path)}\n" for path in args.data).encode()
    ).hexdigest()
    augmenter = BatchSuitAugmenter(device) if args.suit_augment and args.vectorized_batches else None

    for epoch in range(1, args.epochs + 1):
        epoch_start = time.perf_counter()
        model.train()
        train_losses = []
        for batch_features, batch_masks, batch_actions, batch_returns in loaders["train"]:
            batch_features = batch_features.to(device)
            batch_masks = batch_masks.to(device)
            batch_actions = batch_actions.to(device)
            batch_returns = batch_returns.to(device)
            if augmenter is not None:
                batch_features, batch_masks, batch_actions = augmenter(batch_features, batch_masks, batch_actions)
            logits, values = model(batch_features)
            policy_loss = masked_cross_entropy(logits, batch_actions, batch_masks)
            value_loss = nn.functional.mse_loss(values, batch_returns)
            loss = policy_loss + args.value_weight * value_loss
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimiser.step()
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite training loss")
            train_losses.append(float(loss.detach().cpu()))

        model.eval()
        validation_losses = []
        correct = 0
        total = 0
        validation_predictions: list[torch.Tensor] = []
        validation_actions: list[torch.Tensor] = []
        with torch.inference_mode():
            for batch_features, batch_masks, batch_actions, batch_returns in loaders["validation"]:
                batch_features = batch_features.to(device)
                batch_masks = batch_masks.to(device)
                batch_actions = batch_actions.to(device)
                batch_returns = batch_returns.to(device)
                logits, values = model(batch_features)
                policy_loss = masked_cross_entropy(logits, batch_actions, batch_masks)
                value_loss = nn.functional.mse_loss(values, batch_returns)
                validation_losses.append(float((policy_loss + args.value_weight * value_loss).cpu()))
                masked_logits = logits.masked_fill(~batch_masks, torch.finfo(logits.dtype).min)
                predictions = masked_logits.argmax(dim=1)
                correct += int((predictions == batch_actions).sum().cpu())
                total += len(batch_actions)
                validation_predictions.append(predictions.cpu())
                validation_actions.append(batch_actions.cpu())
        row = {
            "epoch": epoch,
            "epoch_seconds": time.perf_counter() - epoch_start,
            "train_loss": float(np.mean(train_losses)),
            "validation_loss": float(np.mean(validation_losses)),
            "validation_action_accuracy": correct / max(total, 1),
            "validation_action_metrics": action_category_metrics(
                torch.cat(validation_predictions), torch.cat(validation_actions)
            ),
        }
        history.append(row)
        print(json.dumps(row), flush=True)
        if row["validation_loss"] < best_validation:
            best_validation = row["validation_loss"]
            checkpoint = {
                "format_version": 1,
                "algorithm": "behavior_cloning",
                "ruleset_id": RULESET_ID,
                "observation_version": OBSERVATION_VERSION,
                "feature_encoding_version": FEATURE_ENCODING_VERSION,
                "action_catalog_version": ACTION_CATALOG_VERSION,
                "feature_size": FEATURE_SIZE,
                "action_count": int(model.action_count),
                "hidden": args.hidden,
                "model": model.state_dict(),
                "optimizer": optimiser.state_dict(),
                "epoch": epoch,
                "history": history,
                "dataset": [str(path) for path in args.data],
                "dataset_sha256": dataset_sha256,
                "initial_checkpoint": (
                    str(args.init_checkpoint) if args.init_checkpoint is not None else None
                ),
                "training_seed": args.seed,
                "learned_scope": "standard discard decisions only" if args.discard_only else "all decisions",
                "discard_only": args.discard_only,
                "suit_augmentation": args.suit_augment,
                "num_workers": args.num_workers,
                "vectorized_batches": args.vectorized_batches,
                "training_config": vars(args) | {"data": [str(path) for path in args.data],
                                                  "output": str(args.output),
                                                  "init_checkpoint": str(args.init_checkpoint) if args.init_checkpoint else None},
                "discard_guard": args.discard_guard,
                "teacher_variant": teacher_variant,
                "scaffold_variant": scaffold_variant,
                "best_validation_loss": best_validation,
                "is_smoke": len(train_indices) < 5000 or args.epochs < 5,
            }
            torch.save(checkpoint, args.output)

    print(f"saved best checkpoint to {args.output} (validation loss {best_validation:.6f})")


if __name__ == "__main__":
    main()
