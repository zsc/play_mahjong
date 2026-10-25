"""Validate completed teacher shards before admitting them to training."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from mahjong_ai.actions import ACTION_COUNT
from mahjong_ai.features import FEATURE_SIZE
from train_bc import load_versioned_dataset


def validate(paths: list[Path], teacher: str, expected_games: int) -> dict:
    seen: set[int] = set()
    action_counts = np.zeros(ACTION_COUNT, dtype=np.int64)
    records = []
    for path in paths:
        dataset, meta = load_versioned_dataset(path)
        with dataset as data:
            if meta.get("teacher_variant") != teacher:
                raise ValueError(f"teacher mismatch: {path}")
            features, masks, actions = data["features"], data["masks"], data["actions"]
            seeds, seats, revisions, returns = (data[key] for key in ("seeds", "seats", "revisions", "returns"))
            size = len(actions)
            if size != meta["decisions"] or features.shape != (size, FEATURE_SIZE):
                raise ValueError(f"feature shape/decision count mismatch: {path}")
            if masks.dtype != np.bool_ or masks.shape != (size, ACTION_COUNT):
                raise ValueError(f"mask contract mismatch: {path}")
            if any(array.shape != (size,) for array in (actions, seeds, seats, revisions, returns)):
                raise ValueError(f"row count mismatch: {path}")
            if not np.isfinite(features).all() or not np.isfinite(returns).all():
                raise ValueError(f"non-finite input: {path}")
            if np.any(actions < 0) or np.any(actions >= ACTION_COUNT):
                raise ValueError(f"out-of-range action: {path}")
            if np.any(~masks.any(axis=1)) or not masks[np.arange(size), actions].all():
                raise ValueError(f"illegal teacher label or empty mask: {path}")
            if np.any((seats < 0) | (seats > 3)):
                raise ValueError(f"invalid seat: {path}")
            game_rows = meta["game_rows"]
            expected = set(range(meta["seed_start"], meta["seed_start"] + meta["games"]))
            game_seeds = [int(row["seed"]) for row in game_rows]
            if len(game_seeds) != len(set(game_seeds)) or set(game_seeds) != expected:
                raise ValueError(f"duplicate/missing game metadata: {path}")
            if set(np.unique(seeds).tolist()) != expected or seen & expected:
                raise ValueError(f"missing seeds or overlapping shards: {path}")
            seen.update(expected)
            for game in game_rows:
                selected = np.flatnonzero(seeds == game["seed"])
                if len(selected) != game["decisions"] or not np.array_equal(
                    revisions[selected], np.arange(len(selected))
                ):
                    raise ValueError(f"missing/duplicate decision revisions: {path}, seed={game['seed']}")
                if sum(game["deltas"]) != 0:
                    raise ValueError(f"non-zero-sum settlement: {path}")
                expected_returns = np.asarray(game["deltas"], dtype=np.float32)[seats[selected]] / 64.0
                if not np.array_equal(returns[selected], expected_returns):
                    raise ValueError(f"return/seat mismatch: {path}")
            action_counts += np.bincount(actions, minlength=ACTION_COUNT)
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            records.append({"path": str(path), "games": len(expected), "decisions": size,
                            "sha256": digest})
        print(f"validated {path.name}: {size} decisions", flush=True)
    if len(seen) != expected_games:
        raise ValueError(f"expected {expected_games} games, found {len(seen)}")
    return {"valid": True, "teacher_variant": teacher, "games": len(seen),
            "decisions": int(action_counts.sum()), "action_counts": action_counts.tolist(),
            "shards": records, "seed_min": min(seen), "seed_max": max(seen)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, nargs="+", required=True)
    parser.add_argument("--teacher", required=True)
    parser.add_argument("--expected-games", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("validation report already exists")
    report = validate(args.data, args.teacher, args.expected_games)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"validated {report['games']} games / {report['decisions']} decisions")


if __name__ == "__main__":
    main()
