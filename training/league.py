"""Full-action, unguarded PPO with frozen opponents and per-player trajectories."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import random
import time
from pathlib import Path

import numpy as np
import torch
from evaluate import load_policy
from mahjong_ai.engine import MahjongEngine
from mahjong_ai.features import action_mask, encode_observation
from mahjong_ai.restrictions import teacher_optimal_discards
from model import TilePolicyValueNet, model_from_checkpoint
from train_ppo import compute_gae, ppo_update

_CACHE = {}


def frozen(path, expected_hash):
    key = (path, expected_hash)
    if key not in _CACHE:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected_hash:
            raise ValueError("frozen opponent checkpoint changed")
        _CACHE[key] = load_policy(Path(path), torch.device("cpu"))[0]
    return _CACHE[key]


def expert_actions(model, observations, features, masks, teachers):
    """Exact current website composite, used only as opponent/training labels."""
    result = list(teachers)
    indices = [i for i, o in enumerate(observations) if o["phase"]["kind"] == "discard" and 0 not in o["legal_action_ids"]]
    if indices:
        allowed = masks[indices].copy()
        for row, i in enumerate(indices):
            allowed[row] = False
            allowed[row, list(teacher_optimal_discards(observations[i], set(observations[i]["legal_action_ids"])))] = True
        with torch.inference_mode():
            logits, _ = model(torch.from_numpy(features[indices]), torch.from_numpy(allowed))
        for i, action in zip(indices, logits.argmax(1).tolist(), strict=True):
            result[i] = action
    return result


def finish_trajectories(trajectories, outcome, gamma, gae_lambda):
    """Every controlled player receives terminal settlement, even without another turn."""
    result = []
    for seat, rows in enumerate(trajectories):
        if rows:
            rows[-1]["reward"] = float(outcome.get("deltas", [0]*4)[seat])/64
            compute_gae(rows, gamma, gae_lambda)
            result.extend(rows)
    return result


def collect_worker(payload):
    torch.set_num_threads(1)
    torch.manual_seed(payload["sampling_seed"])
    rng = random.Random(payload["sampling_seed"])
    learner = model_from_checkpoint(payload["model"])
    learner.load_state_dict(payload["model"]["model"])
    learner.eval()
    expert = frozen(payload["expert"], payload["expert_sha256"])
    historical = {f"history-{i}": frozen(p["path"], p["sha256"]) for i, p in enumerate(payload["opponents"])}
    models = {"learner": learner, "expert": expert, **historical}
    # Cache misses construct networks and consume RNG; rollout randomness must
    # depend only on this batch seed, including after a worker/process restart.
    torch.manual_seed(payload["sampling_seed"])
    rows, scores, game_records = [], [], []
    offsets = list(range(payload["worker"], payload["games"], payload["workers"]))
    with MahjongEngine() as engine:
        for start in range(0, len(offsets), payload["batch_size"]):
            games = []
            try:
                for offset in offsets[start:start+payload["batch_size"]]:
                    seat = offset % 4
                    self_play = payload["phase"] == "distill" or rng.random() < payload["self_play_fraction"]
                    opponents = [rng.choice(["expert", "qualified", *historical]) for _ in range(4)]
                    policies = ["learner"]*4 if self_play else opponents
                    policies[seat] = "learner"
                    games.append({"game": engine.new_game(payload["seed_base"]+offset), "seed": payload["seed_base"]+offset,
                                  "policies": policies, "seat": seat, "rows": [[] for _ in range(4)],
                                  "action_id": None, "revision": None, "actor": None, "outcome": None,
                                  "self_play": self_play})
                active = games[:]
                while active:
                    responses = engine.decision_batch([{"game": g["game"], "max_steps": 2000,
                        "action_id": g["action_id"], "seat": g["actor"], "revision": g["revision"]} for g in active])
                    pending, decisions = [], []
                    for game, response in zip(active, responses, strict=True):
                        if "outcome" in response:
                            game["outcome"] = response["outcome"]
                        else:
                            game.update(actor=response["actor"], revision=response["revision"])
                            pending.append(game)
                            decisions.append(response)
                    active = pending
                    if not active:
                        break
                    observations = [d["observation"] for d in decisions]
                    features = np.stack([encode_observation(o) for o in observations])
                    masks = np.stack([action_mask(o) for o in observations])
                    teachers = expert_actions(expert, observations, features, masks, [d["teacher_action"] for d in decisions])
                    for policy, model in models.items():
                        indices = [i for i, g in enumerate(active) if g["policies"][g["actor"]] == policy]
                        if not indices:
                            continue
                        if policy == "expert":
                            for i in indices:
                                active[i]["action_id"] = teachers[i]
                            continue
                        with torch.inference_mode():
                            logits, values = model(torch.from_numpy(features[indices]), torch.from_numpy(masks[indices]))
                            distribution = torch.distributions.Categorical(logits=logits)
                            actions = distribution.sample() if policy == "learner" else logits.argmax(1)
                            logs = distribution.log_prob(actions).tolist()
                        for k, i in enumerate(indices):
                            game = active[i]
                            action = int(actions[k])
                            if policy == "learner" and payload["phase"] == "distill" and rng.random() < payload["teacher_mix"]:
                                action = teachers[i]
                            game["action_id"] = action
                            if policy == "learner":
                                game["rows"][game["actor"]].append({"features": features[i], "mask": masks[i],
                                    "action": action, "teacher_action": teachers[i], "old_log_probability": logs[k],
                                    "value": float(values[k]), "reward": 0.0})
                    for i, game in enumerate(active):
                        if game["policies"][game["actor"]] == "qualified":
                            game["action_id"] = decisions[i]["teacher_action"]
                for game in games:
                    engine.validate(game["game"])
                    rows.extend(finish_trajectories(game["rows"], game["outcome"], payload["gamma"], payload["gae_lambda"]))
                    score = game["outcome"].get("deltas", [0]*4)[game["seat"]]
                    scores.append(score)
                    game_records.append({"seed": game["seed"], "seat": game["seat"], "policies": game["policies"],
                                         "self_play": game["self_play"], "score": score,
                                         "kind": game["outcome"]["kind"]})
            finally:
                for game in games:
                    engine.close(game["game"])
    return rows, scores, game_records


def distill_update(model, optimiser, rows, device, epochs, minibatch_size, rng):
    x = torch.from_numpy(np.stack([r["features"] for r in rows])).to(device)
    mask = torch.from_numpy(np.stack([r["mask"] for r in rows])).to(device)
    targets = torch.tensor([r["teacher_action"] for r in rows], device=device)
    returns = torch.tensor([r["return"] for r in rows], device=device)
    order = list(range(len(rows)))
    losses, accuracies = [], []
    for _ in range(epochs):
        rng.shuffle(order)
        for start in range(0, len(order), minibatch_size):
            ids = order[start:start+minibatch_size]
            logits, values = model(x[ids], mask[ids])
            ce = torch.nn.functional.cross_entropy(logits, targets[ids])
            loss = ce + .1 * torch.nn.functional.mse_loss(values, returns[ids])
            if not torch.isfinite(loss):
                raise RuntimeError("non-finite distillation loss")
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), .5)
            optimiser.step()
            losses.append(float(ce.detach()))
            accuracies.append(float((logits.argmax(1) == targets[ids]).float().mean()))
    return {"teacher_bc_loss": float(np.mean(losses)), "teacher_agreement": float(np.mean(accuracies))}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--init", type=Path)
    src.add_argument("--resume", type=Path)
    parser.add_argument("--expert", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("distill", "ppo"), default="ppo")
    parser.add_argument("--updates", type=int, default=128)
    parser.add_argument("--games", type=int, default=1024)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--minibatch-size", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--teacher-bc", type=float, default=.1)
    parser.add_argument("--teacher-mix", type=float, default=.8)
    parser.add_argument("--self-play-fraction", type=float, default=.25)
    parser.add_argument("--entropy", type=float, default=.003)
    parser.add_argument("--seed", type=int, default=202610261)
    parser.add_argument("--seed-start", type=int, default=50000000)
    parser.add_argument("--snapshot-every", type=int, default=16)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.output.exists() or min(args.workers,args.games,args.batch_size,args.snapshot_every,args.updates) < 1:
        parser.error("new output directory and positive counts required")
    if not 0 <= args.self_play_fraction <= 1 or not 0 <= args.teacher_mix <= 1:
        parser.error("mixture probabilities must be within [0,1]")
    device = torch.device(args.device)
    torch.set_num_threads(1)
    initial = torch.load(args.resume or args.init, map_location="cpu", weights_only=True)
    if args.resume:
        saved = initial["league_config"]
        for key, value in saved.items():
            if key not in ("updates", "output", "init", "resume", "device"):
                setattr(args, key, Path(value) if key == "expert" else value)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    rng = random.Random(args.seed)
    # Validate the original checkpoint contract before any warm-start conversion.
    _, checked = load_policy(args.resume or args.init, torch.device("cpu"))
    model = TilePolicyValueNet(hidden=checked["hidden"]).to(device)
    missing, unexpected = model.load_state_dict(checked["model"], strict=False)
    if unexpected or (checked.get("model_kind") == "tile-shared-v1" and missing):
        raise ValueError("invalid warm-start weights")
    optimiser = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    history, opponents, start_update = [], [], 0
    if args.resume:
        optimiser.load_state_dict(initial["optimizer"])
        history, opponents, start_update = initial["history"], initial["opponent_pool"], initial["update"]
        if args.phase == "ppo" and args.resume.name.startswith("u"):
            member = {"path": str(args.resume.resolve()), "sha256": digest(args.resume)}
            if member not in opponents:
                opponents.append(member)
        rng.setstate(initial["rng_state"]["shuffle"])
        torch.set_rng_state(initial["rng_state"]["torch"])
        if device.type == "cuda":
            torch.cuda.set_rng_state_all(initial["rng_state"]["cuda"])
    args.output.mkdir(parents=True)
    config = {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()}
    (args.output/"config.json").write_text(json.dumps(config, indent=2))
    expert_hash = digest(args.expert)
    core_root = Path(__file__).resolve().parents[1]/"ocaml/mahjong_core/lib"
    core_hash = hashlib.sha256(b"".join(p.name.encode()+p.read_bytes() for p in sorted(core_root.glob("*.ml"))
                                      if not p.name.startswith("._"))).hexdigest()
    if args.resume and expert_hash != initial["expert_sha256"]:
        raise ValueError("expert changed on resume")
    with mp.get_context("spawn").Pool(args.workers) as pool:
        for update in range(start_update+1, args.updates+1):
            started = time.perf_counter()
            frozen_state = {"hidden": checked["hidden"], "model_kind": "tile-shared-v1",
                            "model": {k:v.detach().cpu() for k,v in model.state_dict().items()}}
            payload = {"model": frozen_state, "expert": str(args.expert), "expert_sha256": expert_hash,
                       "opponents": opponents[-4:], "seed_base": args.seed_start+(update-1)*args.games,
                       "games": args.games, "workers": args.workers, "batch_size": args.batch_size,
                       "phase": args.phase, "teacher_mix": args.teacher_mix,
                       "self_play_fraction": args.self_play_fraction, "gamma": 1.0, "gae_lambda": .95}
            results = pool.map(collect_worker, [payload | {"worker": w, "sampling_seed": args.seed+update*100003+w*104729} for w in range(args.workers)])
            rows = [r for result in results for r in result[0]]
            scores = [s for result in results for s in result[1]]
            games = [g for result in results for g in result[2]]
            rollout_seconds = time.perf_counter()-started
            if not rows:
                raise RuntimeError("empty league rollout")
            model.train()
            training_start = time.perf_counter()
            if args.phase == "distill":
                metrics = distill_update(model, optimiser, rows, device, args.epochs, args.minibatch_size, rng)
            else:
                metrics = ppo_update(model, optimiser, rows, device, args.epochs, args.minibatch_size,
                                     .15, .5, args.entropy, args.teacher_bc, rng)
            if not all(torch.isfinite(p).all() for p in model.parameters()):
                raise RuntimeError("non-finite league weights")
            row = {"update": update, "games": args.games, "samples": len(rows), "phase": args.phase,
                   "rollout_seconds": rollout_seconds, "update_seconds": time.perf_counter()-training_start,
                   "mean_training_score": float(np.mean(scores)), "self_play_games": sum(g["self_play"] for g in games),
                   "opponent_pool": payload["opponents"], **metrics}
            history.append(row)
            with (args.output/"history.jsonl").open("a") as log:
                log.write(json.dumps(row)+"\n")
            # Full frozen opponent choices make every sampled batch auditable.
            (args.output/f"rollout-{update:04d}.json").write_text(json.dumps(games))
            checkpoint = {k:checked[k] for k in ["format_version","ruleset_id","observation_version","feature_encoding_version",
                          "action_catalog_version","feature_size","action_count","hidden"]}
            checkpoint.update(model_kind="tile-shared-v1", algorithm=f"league_{args.phase}_all_actions",
                model=model.state_dict(), optimizer=optimiser.state_dict(), update=update, history=history,
                league_config=config, training_config=config, opponent_pool=opponents, expert_sha256=expert_hash,
                learned_scope="all", discard_guard="none", scaffold_variant=None, training_seed=args.seed,
                is_smoke=update*args.games<1000, value_activation="linear", initial_checkpoint_sha256=digest(args.resume or args.init),
                engine_source_sha256=core_hash,
                rng_state={"shuffle":rng.getstate(), "torch":torch.get_rng_state(),
                           "cuda":torch.cuda.get_rng_state_all() if device.type=="cuda" else []})
            if update % args.snapshot_every == 0 or update == args.updates:
                snapshot = args.output/f"u{update:04d}.pt"
                # Pool members are immutable and added only between rollout batches.
                torch.save(checkpoint, snapshot)
                if args.phase == "ppo":
                    opponents.append({"path":str(snapshot.resolve()),"sha256":digest(snapshot)})
                checkpoint["opponent_pool"] = list(opponents)
            temporary = args.output/"latest.tmp"
            torch.save(checkpoint, temporary)
            temporary.replace(args.output/"latest.pt")
            print(json.dumps(row), flush=True)
    print(f"LEAGUE_COMPLETE {args.output}", flush=True)


if __name__ == "__main__":
    main()
