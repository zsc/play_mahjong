from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import random
import time
from contextlib import nullcontext
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
    batch_size: int = 1,
) -> tuple[list[dict], dict[str, int], list[int]]:
    if batch_size > 1:
        return rollout_batched(engine, model, device, seed_base, games, worker_index, worker_count,
                               max_steps, discard_guard, scaffold_variant, opponent_variant,
                               gamma, gae_lambda, batch_size)
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


def rollout_batched(
    engine, model, device, seed_base, games, worker_index, worker_count, max_steps,
    discard_guard, scaffold_variant, opponent_variant, gamma, gae_lambda, batch_size,
):
    """Independent games share inference; rewards and GAE remain per game/seat.

    Batched categorical sampling has its own reproducible RNG ordering. It is not
    bit-identical to the legacy sequential sampler for the same sampling seed.
    """
    offsets = list(range(worker_index, games, worker_count))
    rows, scores = [], []
    outcomes = {"win": 0, "exhaustive-draw": 0}
    for start in range(0, len(offsets), batch_size):
        trajectories = []
        try:
            for offset in offsets[start:start + batch_size]:
                trajectories.append({"game": engine.new_game(seed_base + offset), "seat": offset % 4,
                                     "rows": [], "action": None, "outcome": None})
            active = trajectories[:]
            while active:
                responses = engine.advance_batch([
                    {"game": item["game"], "model_seat": item["seat"], "action_id": item["action"],
                     "max_steps": max_steps, "scaffold_variant": scaffold_variant,
                     "opponent_variant": opponent_variant} for item in active
                ])
                pending, observations = [], []
                for item, response in zip(active, responses, strict=True):
                    if "outcome" in response:
                        item["outcome"] = response["outcome"]
                    else:
                        pending.append(item)
                        observations.append(response)
                active = pending
                if not active:
                    break
                features = np.stack([encode_observation(r["observation"]) for r in observations])
                masks = np.stack([restricted_discard_mask(r["observation"], discard_guard) for r in observations])
                with torch.inference_mode():
                    logits, values = model(torch.from_numpy(features).to(device), torch.from_numpy(masks).to(device))
                    distribution = Categorical(logits=logits)
                    actions = distribution.sample()
                    log_probs = distribution.log_prob(actions).cpu().tolist()
                    actions = actions.cpu().tolist()
                    values = values.cpu().tolist()
                for i, item in enumerate(active):
                    item["action"] = actions[i]
                    item["rows"].append({"features": features[i], "mask": masks[i], "action": actions[i],
                                         "teacher_action": observations[i]["teacher_action"],
                                         "old_log_probability": log_probs[i], "value": values[i], "reward": 0.0})
            for item in trajectories:
                outcome = item["outcome"]
                score = outcome.get("deltas", [0, 0, 0, 0])[item["seat"]]
                game_rows = item["rows"]
                if game_rows:
                    game_rows[-1]["reward"] = float(score) / 64.0
                    compute_gae(game_rows, gamma, gae_lambda)
                    rows.extend(game_rows)
                outcomes[outcome["kind"]] += 1
                scores.append(int(score))
        finally:
            for item in trajectories:
                engine.close(item["game"])
    return rows, outcomes, scores


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
            int(payload.get("rollout_batch_size", 1)),
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
    worker_pool=None,
    rollout_batch_size: int = 1,
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
                rollout_batch_size,
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
            "rollout_batch_size": rollout_batch_size,
        }
        for worker_index in range(workers)
    ]
    pool_context = nullcontext(worker_pool) if worker_pool is not None else mp.get_context("spawn").Pool(processes=workers)
    with pool_context as pool:
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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--init", type=Path)
    source.add_argument("--resume", type=Path, help="Restore optimizer, RNG and saved training settings; updates is the total target")
    parser.add_argument("--output", type=Path, default=Path("training/checkpoints/ppo-discard-v1.pt"))
    parser.add_argument("--updates", type=int, default=20)
    parser.add_argument("--games-per-update", type=int, default=64)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--rollout-batch-size", type=int, default=16,
                        help="Games sharing native advance/inference per worker; 1 keeps the legacy sampler")
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
    if args.rollout_batch_size <= 0:
        raise SystemExit("--rollout-batch-size must be positive")
    if args.snapshot_every < 0:
        raise SystemExit("--snapshot-every must be non-negative")

    device = choose_device(args.device)
    model, initial_checkpoint = load_initial_model(args.resume or args.init, device)
    resume_keys = (
        "games_per_update", "workers", "ppo_epochs", "minibatch_size", "learning_rate", "clip_ratio",
        "value_coefficient", "entropy_coefficient", "teacher_bc_coefficient", "discard_guard",
        "scaffold_variant", "opponent_variant", "gamma", "gae_lambda", "seed", "seed_start", "max_steps",
        "rollout_batch_size",
    )
    if args.resume:
        if "rng_state" not in initial_checkpoint or "training_config" not in initial_checkpoint:
            raise ValueError("legacy checkpoint cannot be resumed exactly; use --init for a documented warm start")
        for key in resume_keys:
            value = initial_checkpoint["training_config"].get(key, 1) if key == "rollout_batch_size" else initial_checkpoint["training_config"][key]
            setattr(args, key, value)
    rng = random.Random(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    scaffold_variant = resolve_scaffold_variant(args.scaffold_variant, initial_checkpoint)
    optimiser = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    history: list[dict] = []
    start_update = 0
    if args.resume:
        optimiser.load_state_dict(initial_checkpoint["optimizer"])
        history = list(initial_checkpoint["history"])
        start_update = int(initial_checkpoint["update"])
        saved_rng = initial_checkpoint["rng_state"]
        rng.setstate(saved_rng["shuffle"])
        np.random.set_state((saved_rng["numpy"][0], np.asarray(saved_rng["numpy"][1], dtype=np.uint32),
                             *saved_rng["numpy"][2:]))
        torch.set_rng_state(saved_rng["torch"].cpu())
        if device.type == "cuda" and saved_rng["cuda"]:
            torch.cuda.set_rng_state_all([state.cpu() for state in saved_rng["cuda"]])
        print(f"resuming update {start_update}; restored saved rollout/training settings", flush=True)
    training_config = {key: getattr(args, key) for key in resume_keys}
    source_root = Path(__file__).resolve().parents[1]
    source_digest = hashlib.sha256()
    for path in sorted((source_root / "ocaml/mahjong_core/lib").glob("*.ml")):
        if not path.name.startswith("._"):
            source_digest.update(path.name.encode())
            source_digest.update(path.read_bytes())
    source_sha256 = source_digest.hexdigest()
    initial_sha256 = hashlib.sha256((args.resume or args.init).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.snapshot_every > 0:
        args.snapshot_dir.mkdir(parents=True, exist_ok=True)

    pool_context = mp.get_context("spawn").Pool(processes=args.workers) if args.workers > 1 else nullcontext(None)
    with pool_context as worker_pool:
        for update in range(start_update + 1, args.updates + 1):
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
                worker_pool=worker_pool,
                rollout_batch_size=args.rollout_batch_size,
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
                "rollout_batch_size": args.rollout_batch_size,
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
                "initial_checkpoint": initial_checkpoint.get("initial_checkpoint") if args.resume else str(args.init),
                "training_config": training_config,
                "engine_source_sha256": source_sha256,
                "initial_checkpoint_sha256": initial_sha256,
                "sampler_version": "native-advance-categorical-batch-v1" if args.rollout_batch_size > 1 else "sequential-v1",
                "rng_state": {
                    "shuffle": rng.getstate(),
                    "numpy": (np.random.get_state()[0], np.random.get_state()[1].tolist(), *np.random.get_state()[2:]),
                    "torch": torch.get_rng_state(),
                    "cuda": torch.cuda.get_rng_state_all() if device.type == "cuda" else [],
                },
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
