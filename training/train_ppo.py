from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import random
import time
from pathlib import Path

import numpy as np
import torch
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
from model import PolicyValueNet
from torch import nn
from torch.distributions import Categorical
from train_bc import choose_device

RULESET_ID = "mcr-wmo2006-stage1"


def load_initial_model(path: Path, device: torch.device) -> tuple[PolicyValueNet, dict]:
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    if checkpoint.get("format_version") != 1:
        raise ValueError("unsupported initial checkpoint format")
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
        raise ValueError(f"initial checkpoint contract mismatch: {mismatches}")
    model = PolicyValueNet(hidden=int(checkpoint["hidden"])).to(device)
    model.load_state_dict(checkpoint["model"])
    return model, checkpoint


def restricted_discard_mask(observation: dict, discard_guard: str = "none") -> np.ndarray:
    mask = action_mask(observation)
    restricted = np.zeros_like(mask)
    candidates = {
        int(action)
        for action in observation["legal_action_ids"]
        if DISCARD_START <= int(action) < DISCARD_START + 34
    }
    if discard_guard == "teacher-optimal":
        candidates = teacher_optimal_discards(observation, candidates)
    for action in candidates:
        restricted[action] = True
    if not restricted.any():
        raise RuntimeError("discard-only policy has no legal discard")
    return restricted


def sample_action(
    model: PolicyValueNet,
    observation: dict,
    mask: np.ndarray,
    device: torch.device,
    encoded_features: np.ndarray | None = None,
) -> tuple[int, float, float]:
    if encoded_features is None:
        encoded_features = encode_observation(observation)
    features = torch.from_numpy(encoded_features).unsqueeze(0).to(device)
    mask_tensor = torch.from_numpy(mask).unsqueeze(0).to(device)
    with torch.inference_mode():
        logits, value = model(features, mask_tensor)
        distribution = Categorical(logits=logits)
        action = distribution.sample()
        log_probability = distribution.log_prob(action)
    return int(action.item()), float(log_probability.item()), float(value.item())


def rollout_game(
    engine: MahjongEngine,
    model: PolicyValueNet,
    seed: int,
    model_seat: int,
    device: torch.device,
    max_steps: int,
    discard_guard: str,
    scaffold_variant: str,
    opponent_variant: str,
) -> tuple[list[dict], dict]:
    game = engine.new_game(seed, "F1")
    rows: list[dict] = []
    outcome: dict | None = None
    try:
        for step in range(max_steps):
            actor = engine.actor(game)
            if actor is None:
                observation, _ = engine.observe(game, 0)
                outcome = observation["phase"]["outcome"]
                break
            if actor == model_seat:
                observation, _ = engine.observe(game, actor)
                legal = set(observation["legal_action_ids"])
                if observation["phase"]["kind"] == "discard" and HU not in legal:
                    mask = restricted_discard_mask(observation, discard_guard)
                    teacher_action = engine.heuristic_action(game, actor, scaffold_variant)
                    features = encode_observation(observation)
                    action, old_log_probability, value = sample_action(model, observation, mask, device, features)
                    rows.append(
                        {
                            "features": features,
                            "mask": mask,
                            "action": action,
                            "teacher_action": teacher_action,
                            "old_log_probability": old_log_probability,
                            "value": value,
                            "reward": 0.0,
                        }
                    )
                else:
                    action = engine.heuristic_action(game, actor, scaffold_variant)
            else:
                action = engine.heuristic_action(game, actor, opponent_variant)
            engine.step(game, actor, action)
        else:
            raise RuntimeError(f"game {seed} exceeded {max_steps} steps")
    finally:
        engine.close(game)
    if outcome is None:
        raise RuntimeError(f"game {seed} has no terminal outcome")
    deltas = outcome.get("deltas", [0, 0, 0, 0]) if outcome["kind"] == "win" else [0, 0, 0, 0]
    if rows:
        rows[-1]["reward"] = float(deltas[model_seat]) / 64.0
    return rows, outcome


def compute_gae(rows: list[dict], gamma: float, gae_lambda: float) -> None:
    advantage = 0.0
    next_value = 0.0
    for index in range(len(rows) - 1, -1, -1):
        row = rows[index]
        delta = row["reward"] + gamma * next_value - row["value"]
        advantage = delta + gamma * gae_lambda * advantage
        row["advantage"] = advantage
        row["return"] = advantage + row["value"]
        next_value = row["value"]


def rollout_range(
    engine: MahjongEngine,
    model: PolicyValueNet,
    device: torch.device,
    seed_base: int,
    games: int,
    worker_index: int,
    worker_count: int,
    max_steps: int,
    discard_guard: str,
    scaffold_variant: str,
    opponent_variant: str,
    gamma: float,
    gae_lambda: float,
) -> tuple[list[dict], dict[str, int], list[int]]:
    rows: list[dict] = []
    outcomes = {"win": 0, "exhaustive-draw": 0}
    model_scores: list[int] = []
    for offset in range(worker_index, games, worker_count):
        seed = seed_base + offset
        model_seat = offset % 4
        game_rows, outcome = rollout_game(
            engine,
            model,
            seed,
            model_seat,
            device,
            max_steps,
            discard_guard,
            scaffold_variant,
            opponent_variant,
        )
        if game_rows:
            compute_gae(game_rows, gamma, gae_lambda)
            rows.extend(game_rows)
        kind = outcome["kind"]
        outcomes[kind] = outcomes.get(kind, 0) + 1
        deltas = outcome.get("deltas", [0, 0, 0, 0]) if kind == "win" else [0, 0, 0, 0]
        model_scores.append(int(deltas[model_seat]))
    return rows, outcomes, model_scores


def rollout_worker(payload: dict) -> tuple[list[dict], dict[str, int], list[int]]:
    torch.set_num_threads(1)
    torch.manual_seed(int(payload["sampling_seed"]))
    device = torch.device("cpu")
    model = PolicyValueNet(hidden=int(payload["hidden"]))
    model.load_state_dict(payload["state_dict"])
    model.to(device)
    model.eval()
    with MahjongEngine() as engine:
        return rollout_range(
            engine,
            model,
            device,
            int(payload["seed_base"]),
            int(payload["games"]),
            int(payload["worker_index"]),
            int(payload["worker_count"]),
            int(payload["max_steps"]),
            str(payload["discard_guard"]),
            str(payload["scaffold_variant"]),
            str(payload["opponent_variant"]),
            float(payload["gamma"]),
            float(payload["gae_lambda"]),
        )


def collect_rollouts(
    model: PolicyValueNet,
    device: torch.device,
    seed_base: int,
    games: int,
    workers: int,
    sampling_seed: int,
    max_steps: int,
    discard_guard: str,
    scaffold_variant: str,
    opponent_variant: str,
    gamma: float,
    gae_lambda: float,
) -> tuple[list[dict], dict[str, int], list[int]]:
    if workers == 1:
        torch.manual_seed(sampling_seed)
        with MahjongEngine() as engine:
            return rollout_range(
                engine,
                model,
                device,
                seed_base,
                games,
                0,
                1,
                max_steps,
                discard_guard,
                scaffold_variant,
                opponent_variant,
                gamma,
                gae_lambda,
            )

    state_dict = {name: value.detach().cpu() for name, value in model.state_dict().items()}
    payloads = [
        {
            "state_dict": state_dict,
            "hidden": int(model.encoder[0].out_features),
            "seed_base": seed_base,
            "games": games,
            "worker_index": worker_index,
            "worker_count": workers,
            "sampling_seed": sampling_seed + worker_index * 104729,
            "max_steps": max_steps,
            "discard_guard": discard_guard,
            "scaffold_variant": scaffold_variant,
            "opponent_variant": opponent_variant,
            "gamma": gamma,
            "gae_lambda": gae_lambda,
        }
        for worker_index in range(workers)
    ]
    with mp.get_context("spawn").Pool(processes=workers) as pool:
        results = pool.map(rollout_worker, payloads)
    rows: list[dict] = []
    outcomes: dict[str, int] = {}
    model_scores: list[int] = []
    for worker_rows, worker_outcomes, worker_scores in results:
        rows.extend(worker_rows)
        for kind, count in worker_outcomes.items():
            outcomes[kind] = outcomes.get(kind, 0) + count
        model_scores.extend(worker_scores)
    return rows, outcomes, model_scores


def ppo_update(
    model: PolicyValueNet,
    optimiser: torch.optim.Optimizer,
    rows: list[dict],
    device: torch.device,
    epochs: int,
    minibatch_size: int,
    clip_ratio: float,
    value_coefficient: float,
    entropy_coefficient: float,
    teacher_bc_coefficient: float,
    rng: random.Random,
) -> dict:
    features = torch.from_numpy(np.stack([row["features"] for row in rows])).to(device)
    masks = torch.from_numpy(np.stack([row["mask"] for row in rows])).to(device)
    actions = torch.tensor([row["action"] for row in rows], dtype=torch.long, device=device)
    old_log_probabilities = torch.tensor(
        [row["old_log_probability"] for row in rows], dtype=torch.float32, device=device
    )
    returns = torch.tensor([row["return"] for row in rows], dtype=torch.float32, device=device)
    advantages = torch.tensor([row["advantage"] for row in rows], dtype=torch.float32, device=device)
    advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-8)
    teacher_actions = torch.tensor([row["teacher_action"] for row in rows], dtype=torch.long, device=device)

    indices = list(range(len(rows)))
    metrics = {"policy_loss": [], "value_loss": [], "entropy": [], "approx_kl": [], "teacher_bc_loss": []}
    for _ in range(epochs):
        rng.shuffle(indices)
        for start in range(0, len(indices), minibatch_size):
            batch = indices[start : start + minibatch_size]
            batch_tensor = torch.tensor(batch, dtype=torch.long, device=device)
            logits, values = model(features[batch_tensor])
            masked_logits = logits.masked_fill(~masks[batch_tensor], torch.finfo(logits.dtype).min)
            log_probabilities = torch.log_softmax(masked_logits, dim=1)
            selected = log_probabilities.gather(1, actions[batch_tensor].unsqueeze(1)).squeeze(1)
            ratios = torch.exp(selected - old_log_probabilities[batch_tensor])
            batch_advantages = advantages[batch_tensor]
            unclipped = ratios * batch_advantages
            clipped = torch.clamp(ratios, 1.0 - clip_ratio, 1.0 + clip_ratio) * batch_advantages
            policy_loss = -torch.minimum(unclipped, clipped).mean()
            value_loss = nn.functional.mse_loss(values, returns[batch_tensor])
            probabilities = log_probabilities.exp()
            entropy = -(probabilities * log_probabilities.masked_fill(~masks[batch_tensor], 0.0)).sum(dim=1).mean()
            teacher_bc_loss = nn.functional.cross_entropy(masked_logits, teacher_actions[batch_tensor])
            loss = (
                policy_loss
                + value_coefficient * value_loss
                - entropy_coefficient * entropy
                + teacher_bc_coefficient * teacher_bc_loss
            )
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            optimiser.step()
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite PPO loss")
            with torch.no_grad():
                approx_kl = ((ratios - 1.0) - (selected - old_log_probabilities[batch_tensor])).mean()
            metrics["policy_loss"].append(float(policy_loss.detach().cpu()))
            metrics["value_loss"].append(float(value_loss.detach().cpu()))
            metrics["entropy"].append(float(entropy.detach().cpu()))
            metrics["approx_kl"].append(float(approx_kl.cpu()))
            metrics["teacher_bc_loss"].append(float(teacher_bc_loss.detach().cpu()))
    return {key: float(np.mean(values)) for key, values in metrics.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Masked PPO for discard decisions against fixed heuristic opponents")
    parser.add_argument("--init", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("training/checkpoints/ppo-discard-v1.pt"))
    parser.add_argument("--updates", type=int, default=20)
    parser.add_argument("--games-per-update", type=int, default=64)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--ppo-epochs", type=int, default=4)
    parser.add_argument("--minibatch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--clip-ratio", type=float, default=0.2)
    parser.add_argument("--value-coefficient", type=float, default=0.5)
    parser.add_argument("--entropy-coefficient", type=float, default=0.01)
    parser.add_argument("--teacher-bc-coefficient", type=float, default=0.5)
    parser.add_argument("--discard-guard", choices=("none", "teacher-optimal"), default="none")
    parser.add_argument("--scaffold-variant", choices=HEURISTIC_VARIANTS)
    parser.add_argument("--opponent-variant", choices=HEURISTIC_VARIANTS, default="default")
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--gae-lambda", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=20261027)
    parser.add_argument("--seed-start", type=int, default=700000)
    parser.add_argument("--max-steps", type=int, default=2000)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--snapshot-every", type=int, default=0)
    parser.add_argument("--snapshot-dir", type=Path, default=Path("training/checkpoints"))
    args = parser.parse_args()
    if args.workers <= 0:
        raise SystemExit("--workers must be positive")
    if args.snapshot_every < 0:
        raise SystemExit("--snapshot-every must be non-negative")

    rng = random.Random(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = choose_device(args.device)
    model, initial_checkpoint = load_initial_model(args.init, device)
    scaffold_variant = resolve_scaffold_variant(args.scaffold_variant, initial_checkpoint)
    optimiser = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    history: list[dict] = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.snapshot_every > 0:
        args.snapshot_dir.mkdir(parents=True, exist_ok=True)

    for update in range(1, args.updates + 1):
        model.eval()
        seed_base = args.seed_start + (update - 1) * args.games_per_update
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        rollout_start = time.perf_counter()
        rows, outcomes, model_scores = collect_rollouts(
            model,
            device,
            seed_base,
            args.games_per_update,
            args.workers,
            args.seed + update * 100003,
            args.max_steps,
            args.discard_guard,
            scaffold_variant,
            args.opponent_variant,
            args.gamma,
            args.gae_lambda,
        )
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        rollout_seconds = time.perf_counter() - rollout_start

        if not rows:
            raise RuntimeError("rollout batch had no learned-policy decisions")
        model.train()
        update_start = time.perf_counter()
        metrics = ppo_update(
            model,
            optimiser,
            rows,
            device,
            args.ppo_epochs,
            args.minibatch_size,
            args.clip_ratio,
            args.value_coefficient,
            args.entropy_coefficient,
            args.teacher_bc_coefficient,
            rng,
        )
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        update_seconds = time.perf_counter() - update_start
        row = {
            "update": update,
            "games": args.games_per_update,
            "workers": args.workers,
            "samples": len(rows),
            "rollout_seconds": rollout_seconds,
            "update_seconds": update_seconds,
            "rollout_games_per_second": args.games_per_update / rollout_seconds,
            "rollout_samples_per_second": len(rows) / rollout_seconds,
            "mean_net_score": float(np.mean(model_scores)),
            "wins": outcomes.get("win", 0),
            "exhaustive_draws": outcomes.get("exhaustive-draw", 0),
            **metrics,
        }
        history.append(row)
        print(json.dumps(row), flush=True)
        checkpoint = {
            "format_version": 1,
            "algorithm": "masked_ppo_discard",
            "ruleset_id": RULESET_ID,
            "observation_version": OBSERVATION_VERSION,
            "feature_encoding_version": FEATURE_ENCODING_VERSION,
            "action_catalog_version": ACTION_CATALOG_VERSION,
            "feature_size": int(model.feature_size),
            "action_count": int(model.action_count),
            "hidden": initial_checkpoint["hidden"],
            "model": model.state_dict(),
            "optimizer": optimiser.state_dict(),
            "update": update,
            "history": history,
            "training_seed": args.seed,
            "workers": args.workers,
            "initial_checkpoint": str(args.init),
            "opponent": "ocaml-structural-shanten-heuristic-v1",
            "opponent_variant": args.opponent_variant,
            "learned_scope": "discard decisions only; hu and reactions use heuristic",
            "teacher_bc_coefficient": args.teacher_bc_coefficient,
            "discard_guard": args.discard_guard,
            "scaffold_variant": scaffold_variant,
            "is_smoke": update * args.games_per_update < 1000,
        }
        torch.save(checkpoint, args.output)
        if args.snapshot_every > 0 and update % args.snapshot_every == 0:
            snapshot = args.snapshot_dir / f"{args.output.stem}-u{update:04d}.pt"
            torch.save(checkpoint, snapshot)
            print(f"saved snapshot {snapshot}", flush=True)

    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
