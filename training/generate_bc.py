from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from mahjong_ai.actions import ACTION_CATALOG_VERSION, ACTION_COUNT
from mahjong_ai.engine import MahjongEngine
from mahjong_ai.features import (
    FEATURE_ENCODING_VERSION,
    FEATURE_SIZE,
    OBSERVATION_VERSION,
    action_mask,
    encode_observation,
)
from mahjong_ai.teachers import HEURISTIC_VARIANTS

RULESET_ID = "mcr-wmo2006-stage1"


def play_game(
    engine: MahjongEngine,
    seed: int,
    round_wind: str,
    max_steps: int,
    teacher_variant: str,
) -> tuple[dict, list[dict]]:
    game = engine.new_game(seed, round_wind)
    decisions: list[dict] = []
    outcome: dict | None = None
    try:
        for revision in range(max_steps):
            actor = engine.actor(game)
            if actor is None:
                observation, _ = engine.observe(game, 0)
                outcome = observation["phase"]["outcome"]
                break
            observation, observed_actor = engine.observe(game, actor)
            if observed_actor != actor:
                raise RuntimeError("actor changed between scheduler and observation")
            mask = action_mask(observation)
            action = engine.heuristic_action(game, actor, teacher_variant)
            if not mask[action]:
                raise RuntimeError(f"teacher selected illegal action {action}")
            decisions.append(
                {
                    "features": encode_observation(observation),
                    "mask": mask,
                    "action": action,
                    "seat": actor,
                    "revision": revision,
                    "seed": seed,
                }
            )
            engine.step(game, actor, action)
        else:
            raise RuntimeError(f"game {seed} exceeded {max_steps} decisions")
    finally:
        engine.close(game)
    if outcome is None:
        raise RuntimeError(f"game {seed} did not expose a terminal outcome")
    return outcome, decisions


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate behavior-cloning data with the OCaml heuristic teacher")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--round-wind", default="F1")
    parser.add_argument(
        "--teacher-variant",
        choices=HEURISTIC_VARIANTS,
        default="default",
    )
    parser.add_argument("--max-steps", type=int, default=2000)
    parser.add_argument("--output", type=Path, default=Path("training/data/teacher-heuristic-v1.npz"))
    args = parser.parse_args()
    if args.games <= 0:
        raise SystemExit("--games must be positive")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    features: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    actions: list[int] = []
    seats: list[int] = []
    seeds: list[int] = []
    revisions: list[int] = []
    game_rows: list[dict] = []

    with MahjongEngine() as engine:
        for seed in range(args.seed_start, args.seed_start + args.games):
            outcome, decisions = play_game(
                engine, seed, args.round_wind, args.max_steps, args.teacher_variant
            )
            if not decisions:
                raise RuntimeError(f"game {seed} produced no decisions")
            deltas = outcome.get("deltas", [0, 0, 0, 0]) if outcome["kind"] == "win" else [0, 0, 0, 0]
            for decision in decisions:
                features.append(decision["features"])
                masks.append(decision["mask"])
                actions.append(decision["action"])
                seats.append(decision["seat"])
                seeds.append(decision["seed"])
                revisions.append(decision["revision"])
            game_rows.append(
                {
                    "seed": seed,
                    "decisions": len(decisions),
                    "outcome": outcome["kind"],
                    "winner": outcome.get("winner"),
                    "discarder": outcome.get("discarder"),
                    "total_fan": outcome.get("total_fan"),
                    "deltas": deltas,
                }
            )
            if args.games >= 20 and (seed - args.seed_start + 1) % 20 == 0:
                print(f"generated {seed - args.seed_start + 1}/{args.games} games", flush=True)

    feature_array = np.stack(features).astype(np.float32)
    mask_array = np.stack(masks).astype(np.bool_)
    action_array = np.asarray(actions, dtype=np.int16)
    seed_array = np.asarray(seeds, dtype=np.int64)
    deltas_by_seed = {row["seed"]: row["deltas"] for row in game_rows}
    normalised_returns = np.asarray(
        [deltas_by_seed[seed][seat] / 64.0 for seed, seat in zip(seeds, seats)],
        dtype=np.float32,
    )
    np.savez_compressed(
        args.output,
        features=feature_array,
        masks=mask_array,
        actions=action_array,
        returns=normalised_returns,
        seats=np.asarray(seats, dtype=np.int8),
        seeds=seed_array,
        revisions=np.asarray(revisions, dtype=np.int32),
    )
    meta = {
        "dataset": args.output.name,
        "ruleset_id": RULESET_ID,
        "observation_version": OBSERVATION_VERSION,
        "feature_encoding_version": FEATURE_ENCODING_VERSION,
        "action_catalog_version": ACTION_CATALOG_VERSION,
        "feature_size": FEATURE_SIZE,
        "action_count": ACTION_COUNT,
        "teacher": "ocaml-structural-shanten-effective-waits-v2",
        "teacher_variant": args.teacher_variant,
        "games": args.games,
        "seed_start": args.seed_start,
        "round_wind": args.round_wind,
        "decisions": int(feature_array.shape[0]),
        "wins": sum(row["outcome"] == "win" for row in game_rows),
        "exhaustive_draws": sum(row["outcome"] == "exhaustive-draw" for row in game_rows),
        "mean_abs_delta": float(np.mean(np.abs(np.asarray([row["deltas"] for row in game_rows], dtype=np.float32)))),
        "game_rows": game_rows,
    }
    args.output.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(
        f"wrote {feature_array.shape[0]} decisions from {args.games} games to {args.output} "
        f"({meta['wins']} wins, {meta['exhaustive_draws']} draws)"
    )


if __name__ == "__main__":
    main()
