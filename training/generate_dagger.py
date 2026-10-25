from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from evaluate import load_policy, model_action
from mahjong_ai.actions import ACTION_CATALOG_VERSION, ACTION_COUNT, DISCARD_START, HU
from mahjong_ai.engine import MahjongEngine
from mahjong_ai.features import (
    FEATURE_ENCODING_VERSION,
    FEATURE_SIZE,
    OBSERVATION_VERSION,
    action_mask,
    encode_observation,
)
from mahjong_ai.restrictions import teacher_optimal_discards
from mahjong_ai.teachers import HEURISTIC_VARIANTS, resolve_scaffold_variant
from train_bc import choose_device, sha256

RULESET_ID = "mcr-wmo2006-stage1"


def learned_action(
    engine: MahjongEngine,
    model,
    observation: dict,
    game: int,
    scope: str,
    device: torch.device,
    discard_guard: str = "none",
    scaffold_variant: str = "default",
) -> int:
    legal = set(observation["legal_action_ids"])
    if scope == "all":
        return model_action(model, observation, device)
    if observation["phase"]["kind"] != "discard" or HU in legal:
        return engine.heuristic_action(game, int(observation["seat"]), scaffold_variant)
    discards = {action for action in legal if DISCARD_START <= action < DISCARD_START + 34}
    if discard_guard == "teacher-optimal":
        discards = teacher_optimal_discards(observation, discards)
    if not discards:
        return engine.heuristic_action(game, int(observation["seat"]), scaffold_variant)
    return model_action(model, observation, device, discards)


def play_game(
    engine: MahjongEngine,
    model,
    seed: int,
    model_seat: int,
    scope: str,
    device: torch.device,
    max_steps: int,
    discard_guard: str,
    scaffold_variant: str,
) -> tuple[dict, list[dict]]:
    game = engine.new_game(seed, "F1")
    rows: list[dict] = []
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
            teacher_action = engine.heuristic_action(game, actor, scaffold_variant)
            mask = action_mask(observation)
            if not mask[teacher_action]:
                raise RuntimeError(f"teacher selected illegal action {teacher_action}")
            if actor == model_seat:
                rows.append(
                    {
                        "features": encode_observation(observation),
                        "mask": mask,
                        "action": teacher_action,
                        "seat": actor,
                        "revision": revision,
                    }
                )
                action = learned_action(
                    engine,
                    model,
                    observation,
                    game,
                    scope,
                    device,
                    discard_guard,
                    scaffold_variant,
                )
            else:
                action = teacher_action
            if not mask[action]:
                raise RuntimeError(f"learned policy selected illegal action {action}")
            engine.step(game, actor, action)
        else:
            raise RuntimeError(f"game {seed} exceeded {max_steps} decisions")
    finally:
        engine.close(game)
    if outcome is None:
        raise RuntimeError(f"game {seed} did not expose a terminal outcome")
    return outcome, rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect teacher-labelled states from the learned policy")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--model-scope", choices=("all", "discard"), default="discard")
    parser.add_argument("--discard-guard", choices=("none", "teacher-optimal"), default="none")
    parser.add_argument("--scaffold-variant", choices=HEURISTIC_VARIANTS)
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--seed-start", type=int, default=200000)
    parser.add_argument("--max-steps", type=int, default=2000)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output", type=Path, default=Path("training/data/dagger-v1.npz"))
    args = parser.parse_args()
    if args.games <= 0:
        raise SystemExit("--games must be positive")

    device = choose_device(args.device)
    model, checkpoint = load_policy(args.checkpoint, device)
    scaffold_variant = resolve_scaffold_variant(args.scaffold_variant, checkpoint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    features: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    actions: list[int] = []
    seats: list[int] = []
    seeds: list[int] = []
    revisions: list[int] = []
    game_rows: list[dict] = []

    with MahjongEngine() as engine:
        for offset in range(args.games):
            seed = args.seed_start + offset
            model_seat = offset % 4
            outcome, rows = play_game(
                engine,
                model,
                seed,
                model_seat,
                args.model_scope,
                device,
                args.max_steps,
                args.discard_guard,
                scaffold_variant,
            )
            if not rows:
                raise RuntimeError(f"game {seed} produced no model-seat decisions")
            deltas = outcome.get("deltas", [0, 0, 0, 0]) if outcome["kind"] == "win" else [0, 0, 0, 0]
            for row in rows:
                features.append(row["features"])
                masks.append(row["mask"])
                actions.append(row["action"])
                seats.append(row["seat"])
                seeds.append(seed)
                revisions.append(row["revision"])
            game_rows.append(
                {
                    "seed": seed,
                    "model_seat": model_seat,
                    "decisions": len(rows),
                    "outcome": outcome["kind"],
                    "winner": outcome.get("winner"),
                    "total_fan": outcome.get("total_fan"),
                    "model_delta": int(deltas[model_seat]),
                }
            )
            if args.games >= 20 and (offset + 1) % 20 == 0:
                print(f"generated {offset + 1}/{args.games} DAgger games", flush=True)

    deltas_by_seed = {row["seed"]: row["model_delta"] for row in game_rows}
    returns = np.asarray(
        [deltas_by_seed[seed] / 64.0 for seed in seeds],
        dtype=np.float32,
    )
    np.savez_compressed(
        args.output,
        features=np.stack(features).astype(np.float32),
        masks=np.stack(masks).astype(np.bool_),
        actions=np.asarray(actions, dtype=np.int16),
        returns=returns,
        seats=np.asarray(seats, dtype=np.int8),
        seeds=np.asarray(seeds, dtype=np.int64),
        revisions=np.asarray(revisions, dtype=np.int32),
    )
    meta = {
        "dataset": args.output.name,
        "kind": "dagger",
        "ruleset_id": RULESET_ID,
        "observation_version": OBSERVATION_VERSION,
        "feature_encoding_version": FEATURE_ENCODING_VERSION,
        "action_catalog_version": ACTION_CATALOG_VERSION,
        "feature_size": FEATURE_SIZE,
        "action_count": ACTION_COUNT,
        "policy_checkpoint": str(args.checkpoint),
        "policy_checkpoint_sha256": sha256(args.checkpoint),
        "policy_scope": args.model_scope,
        "discard_guard": args.discard_guard,
        "scaffold_variant": scaffold_variant,
        "teacher_variant": scaffold_variant,
        "teacher": checkpoint.get("opponent", "ocaml-structural-shanten-heuristic-v1"),
        "seed_start": args.seed_start,
        "games": args.games,
        "decisions": len(actions),
        "wins": sum(row["winner"] == row["model_seat"] for row in game_rows),
        "exhaustive_draws": sum(row["outcome"] == "exhaustive-draw" for row in game_rows),
        "dataset_sha256": sha256(args.output),
    }
    args.output.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        f"wrote {len(actions)} DAgger decisions from {args.games} games to {args.output} "
        f"({meta['wins']} wins, {meta['exhaustive_draws']} draws)"
    )


if __name__ == "__main__":
    main()
