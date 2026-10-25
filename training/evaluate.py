from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from collections.abc import Callable
from pathlib import Path

import numpy as np
import torch
from mahjong_ai.actions import ACTION_CATALOG_VERSION, ACTION_COUNT, DISCARD_START, HU
from mahjong_ai.engine import DEFAULT_LIBRARY, ROOT, MahjongEngine
from mahjong_ai.features import (
    FEATURE_ENCODING_VERSION,
    FEATURE_SIZE,
    OBSERVATION_VERSION,
    action_mask,
    encode_observation,
)
from mahjong_ai.restrictions import teacher_optimal_discards
from mahjong_ai.teachers import HEURISTIC_VARIANTS, resolve_scaffold_variant
from model import PolicyValueNet
from train_bc import choose_device

RULESET_ID = "mcr-wmo2006-stage1"


def load_policy(checkpoint_path: Path, device: torch.device) -> tuple[PolicyValueNet, dict]:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if checkpoint.get("format_version") != 1:
        raise ValueError("unsupported checkpoint format")
    expected = {
        "ruleset_id": RULESET_ID,
        "observation_version": OBSERVATION_VERSION,
        "feature_encoding_version": FEATURE_ENCODING_VERSION,
        "action_catalog_version": ACTION_CATALOG_VERSION,
        "feature_size": FEATURE_SIZE,
        "action_count": ACTION_COUNT,
    }
    mismatches = {
        key: (checkpoint.get(key), value)
        for key, value in expected.items()
        if checkpoint.get(key) != value
    }
    if mismatches:
        raise ValueError(f"checkpoint contract does not match this evaluator: {mismatches}")
    model = PolicyValueNet(hidden=int(checkpoint["hidden"])).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model, checkpoint


def model_action(
    model: PolicyValueNet,
    observation: dict,
    device: torch.device,
    allowed_actions: set[int] | None = None,
) -> int:
    features = torch.from_numpy(encode_observation(observation)).unsqueeze(0).to(device)
    numpy_mask = action_mask(observation)
    if allowed_actions is not None:
        allowed = np.zeros_like(numpy_mask)
        allowed[list(allowed_actions)] = True
        numpy_mask &= allowed
        if not numpy_mask.any():
            raise RuntimeError("policy scope removed every legal action")
    mask = torch.from_numpy(numpy_mask).unsqueeze(0).to(device)
    with torch.inference_mode():
        logits, _ = model(features, mask)
    return int(logits.argmax(dim=1).item())


def play_evaluation_game(
    engine: MahjongEngine,
    seed: int,
    model_seat: int,
    policy: Callable[[int, dict], int],
    max_steps: int,
    opponent_variant: str = "default",
) -> dict:
    game = engine.new_game(seed, "F1")
    decisions = 0
    try:
        while decisions < max_steps:
            actor = engine.actor(game)
            if actor is None:
                observation, _ = engine.observe(game, 0)
                outcome = observation["phase"]["outcome"]
                break
            if actor == model_seat:
                observation, _ = engine.observe(game, actor)
                action = policy(game, observation)
            else:
                action = engine.heuristic_action(game, actor, opponent_variant)
            engine.step(game, actor, action)
            decisions += 1
        else:
            raise RuntimeError(f"game {seed} exceeded {max_steps} decisions")
    finally:
        engine.close(game)
    return {"outcome": outcome, "decisions": decisions}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a policy against frozen heuristic opponents")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--policy", choices=("model", "heuristic", "random"), default="model")
    parser.add_argument(
        "--heuristic-variant",
        choices=HEURISTIC_VARIANTS,
        default="default",
    )
    parser.add_argument("--opponent-variant", choices=HEURISTIC_VARIANTS, default="default")
    parser.add_argument("--scaffold-variant", choices=HEURISTIC_VARIANTS)
    parser.add_argument("--model-scope", choices=("all", "discard"), default="discard")
    parser.add_argument("--discard-guard", choices=("none", "teacher-optimal"), default="none")
    parser.add_argument("--games", type=int, default=200)
    parser.add_argument("--seed-start", type=int, default=500000)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-steps", type=int, default=2000)
    parser.add_argument("--paired-baseline", type=Path)
    parser.add_argument("--output", type=Path, default=Path("training/runs/evaluation.json"))
    args = parser.parse_args()
    if args.games <= 0:
        raise SystemExit("--games must be positive")
    if args.policy == "model" and args.checkpoint is None:
        raise SystemExit("--checkpoint is required for model evaluation")

    device = choose_device(args.device)
    model: PolicyValueNet | None = None
    checkpoint_meta: dict = {}
    if args.policy == "model":
        model, checkpoint_meta = load_policy(args.checkpoint, device)
    scaffold_variant = resolve_scaffold_variant(args.scaffold_variant, checkpoint_meta)

    rng = random.Random(args.seed_start)
    rows: list[dict] = []

    def policy(game: int, observation: dict) -> int:
        if args.policy == "heuristic":
            return current_engine.heuristic_action(
                game, int(observation["seat"]), args.heuristic_variant
            )
        if args.policy == "random":
            return rng.choice(observation["legal_action_ids"])
        assert model is not None
        if args.model_scope == "all":
            return model_action(model, observation, device)
        legal = set(observation["legal_action_ids"])
        if observation["phase"]["kind"] == "discard" and HU not in legal:
            discard_actions = {action for action in legal if DISCARD_START <= action < DISCARD_START + 34}
            if args.discard_guard == "teacher-optimal":
                discard_actions = teacher_optimal_discards(observation, discard_actions)
            return model_action(model, observation, device, discard_actions)
        return current_engine.heuristic_action(
            game, int(observation["seat"]), scaffold_variant
        )

    with MahjongEngine() as current_engine:
        for offset in range(args.games):
            seed = args.seed_start + offset
            model_seat = offset % 4
            result = play_evaluation_game(
                current_engine,
                seed,
                model_seat,
                policy,
                args.max_steps,
                args.opponent_variant,
            )
            outcome = result["outcome"]
            deltas = outcome.get("deltas", [0, 0, 0, 0]) if outcome["kind"] == "win" else [0, 0, 0, 0]
            rows.append(
                {
                    "seed": seed,
                    "model_seat": model_seat,
                    "decisions": result["decisions"],
                    "outcome": outcome["kind"],
                    "winner": outcome.get("winner"),
                    "discarder": outcome.get("discarder"),
                    "total_fan": outcome.get("total_fan"),
                    "model_delta": deltas[model_seat],
                }
            )
            if args.games >= 40 and (offset + 1) % 40 == 0:
                print(f"evaluated {offset + 1}/{args.games} games", flush=True)

    deltas = np.asarray([row["model_delta"] for row in rows], dtype=np.float64)
    wins = sum(row["winner"] == row["model_seat"] for row in rows if row["outcome"] == "win")
    discards = sum(row["discarder"] == row["model_seat"] for row in rows if row["outcome"] == "win")
    draws = sum(row["outcome"] == "exhaustive-draw" for row in rows)
    report = {
        "ruleset_id": RULESET_ID,
        "feature_encoding_version": FEATURE_ENCODING_VERSION,
        "action_catalog_version": ACTION_CATALOG_VERSION,
        "engine_sha256": hashlib.sha256(Path(os.environ.get(
            "MAHJONG_FFI_SERVER", os.environ.get("MAHJONG_FFI_LIBRARY", DEFAULT_LIBRARY)
        )).read_bytes()).hexdigest(),
        "engine_source_sha256": hashlib.sha256(b"".join(
            path.name.encode() + path.read_bytes()
            for path in sorted((ROOT / "ocaml/mahjong_core/lib").glob("*.ml"))
            if not path.name.startswith("._")
        )).hexdigest(),
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() if args.checkpoint else None,
        "policy": args.policy,
        "model_scope": args.model_scope if args.policy == "model" else None,
        "discard_guard": args.discard_guard if args.policy == "model" else None,
        "heuristic_variant": args.heuristic_variant if args.policy == "heuristic" else None,
        "scaffold_variant": scaffold_variant if args.policy == "model" else None,
        "opponent_variant": args.opponent_variant,
        "checkpoint": str(args.checkpoint) if args.checkpoint else None,
        "checkpoint_metadata": {
            key: checkpoint_meta.get(key)
            for key in (
                "algorithm",
                "ruleset_id",
                "teacher_variant",
                "scaffold_variant",
                "best_validation_loss",
                "is_smoke",
                "dataset_sha256",
            )
        },
        "games": args.games,
        "seed_start": args.seed_start,
        "opponent": "ocaml-structural-shanten-heuristic-v1",
        "seat_rotation": "model seat rotates 0,1,2,3",
        "mean_net_score": float(deltas.mean()),
        "std_net_score": float(deltas.std(ddof=1)) if len(deltas) > 1 else 0.0,
        "mean_standard_error": float(deltas.std(ddof=1) / np.sqrt(len(deltas))) if len(deltas) > 1 else 0.0,
        "win_rate": wins / args.games,
        "discard_rate": discards / args.games,
        "exhaustive_draw_rate": draws / args.games,
        "rows": rows,
    }
    if args.paired_baseline is not None:
        baseline = json.loads(args.paired_baseline.read_text())
        baseline_rows = {
            (int(row["seed"]), int(row["model_seat"])): int(row["model_delta"])
            for row in baseline.get("rows", [])
        }
        paired = [
            row["model_delta"] - baseline_rows[(int(row["seed"]), int(row["model_seat"]))]
            for row in rows
            if (int(row["seed"]), int(row["model_seat"])) in baseline_rows
        ]
        if not paired:
            raise ValueError("paired baseline has no matching seed/seat evaluations")
        paired_values = np.asarray(paired, dtype=np.float64)
        paired_se = (
            float(paired_values.std(ddof=1) / np.sqrt(len(paired_values)))
            if len(paired_values) > 1
            else 0.0
        )
        report["paired_baseline"] = {
            "path": str(args.paired_baseline),
            "games": len(paired_values),
            "mean_difference": float(paired_values.mean()),
            "standard_error": paired_se,
            "ci95": [
                float(paired_values.mean() - 1.96 * paired_se),
                float(paired_values.mean() + 1.96 * paired_se),
            ],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"mean net score {report['mean_net_score']:.3f} +/- {report['mean_standard_error']:.3f}, "
        f"win {report['win_rate']:.1%}, discard {report['discard_rate']:.1%}, draw {report['draw_rate'] if 'draw_rate' in report else report['exhaustive_draw_rate']:.1%}"
    )
    if "paired_baseline" in report:
        paired = report["paired_baseline"]
        print(
            f"paired difference vs baseline {paired['mean_difference']:.3f} "
            f"+/- {paired['standard_error']:.3f} (n={paired['games']})"
        )
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
