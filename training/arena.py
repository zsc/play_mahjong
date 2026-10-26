"""Frozen-policy arena: replay every wall in all four seats and group statistics by wall."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import time
from pathlib import Path

import numpy as np
import torch
from evaluate import RULESET_ID, load_policy, model_action
from mahjong_ai.engine import DEFAULT_LIBRARY, ROOT, MahjongEngine
from mahjong_ai.restrictions import teacher_optimal_discards

POLICIES = ("old-guard", "new-guard", "old-raw", "new-raw", "new-full", "qualified", "closed")
_models = {}
_engine = None


def initialize(old: str, new: str):
    global _engine, _models
    torch.set_num_threads(1)
    _engine = MahjongEngine()
    _models = {}
    for name, path in [("old", old), ("new", new)]:
        model, checkpoint = load_policy(Path(path), torch.device("cpu"))
        model.learned_scope = checkpoint.get("learned_scope")
        _models[name] = model


def choose(engine, models, game, actor, policy):
    if policy in ("qualified", "closed"):
        return engine.heuristic_action(game, actor, "qualified-tenpai" if policy == "qualified" else "closed")
    observation, _ = engine.observe(game, actor)
    if policy == "new-full":
        if models["new"].learned_scope != "all":
            raise ValueError("new-full requires an all-action checkpoint")
        return model_action(models["new"], observation, torch.device("cpu"))
    legal = set(observation["legal_action_ids"])
    if observation["phase"]["kind"] != "discard" or 0 in legal:
        return engine.heuristic_action(game, actor, "qualified-tenpai")
    allowed = {a for a in legal if 12 <= a < 46}
    if policy.endswith("-guard"):
        allowed = teacher_optimal_discards(observation, allowed)
    return model_action(models[policy.split("-")[0]], observation, torch.device("cpu"), allowed)


def play(engine, models, seed, seat, challenger, opponent):
    game = engine.new_game(seed)
    try:
        for decisions in range(2001):
            actor = engine.actor(game)
            if actor is None:
                engine.validate(game)
                observation, _ = engine.observe(game, seat)
                outcome = observation["phase"]["outcome"]
                return {"seed": seed, "model_seat": seat, "model_delta": outcome.get("deltas", [0]*4)[seat],
                        "win": outcome.get("winner") == seat, "discard": outcome.get("discarder") == seat,
                        "draw": outcome["kind"] == "exhaustive-draw", "decisions": decisions}
            action = choose(engine, models, game, actor, challenger if actor == seat else opponent)
            engine.step(game, actor, action)
        raise RuntimeError("arena game failed to terminate")
    finally:
        engine.close(game)


def seed_groups(rows):
    grouped = {}
    for row in rows:
        seats = grouped.setdefault(row["seed"], {})
        if row["model_seat"] in seats:
            raise ValueError("duplicate seed/seat")
        seats[row["model_seat"]] = row["model_delta"]
    if any(set(seats) != {0, 1, 2, 3} for seats in grouped.values()):
        raise ValueError("every wall must cover all four seats")
    return {seed: float(np.mean(list(seats.values()))) for seed, seats in grouped.items()}


def confidence(values):
    values = np.asarray(values, dtype=np.float64)
    mean = float(values.mean())
    se = float(values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else None
    return {"mean": mean, "standard_error": se, "ci95": [mean - 1.96*se, mean + 1.96*se] if se is not None else None,
            "independent_wall_groups": len(values)}


def summarize(rows):
    groups = seed_groups(rows)
    return {"games": len(rows), "score": confidence(list(groups.values())),
            **{key+"_rate": sum(row[key] for row in rows)/len(rows) for key in ["win", "discard", "draw"]}}


def compare(candidate, baseline):
    a, b = seed_groups(candidate), seed_groups(baseline)
    if a.keys() != b.keys():
        raise ValueError("paired arena reports must cover identical walls")
    return confidence([a[seed]-b[seed] for seed in sorted(a)])


def chunk(payload):
    start, count, challenger, opponent = payload
    return [play(_engine, _models, seed, seat, challenger, opponent)
            for seed in range(start, start+count) for seat in range(4)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--challengers", default="old-guard,new-guard,old-raw,new-raw,qualified")
    parser.add_argument("--opponents", default="qualified")
    args = parser.parse_args()
    challengers, opponents = args.challengers.split(","), args.opponents.split(",")
    if args.output.exists() or min(args.workers, args.seeds) < 1 or any(p not in POLICIES for p in challengers+opponents):
        parser.error("use new output, positive counts, and known frozen policies")
    args.output.mkdir(parents=True)
    meta = {"ruleset_id": RULESET_ID, "observation_version": 1, "feature_encoding_version": 6,
            "action_catalog_version": 1, "seat_rotation": "each wall replayed at seats 0,1,2,3; CI grouped by wall",
            "seed_start": args.seed_start, "seeds": args.seeds, "workers": args.workers,
            "old_sha256": hashlib.sha256(args.old.read_bytes()).hexdigest(),
            "new_sha256": hashlib.sha256(args.new.read_bytes()).hexdigest(),
            "engine_sha256": hashlib.sha256(Path(os.environ.get("MAHJONG_FFI_LIBRARY", DEFAULT_LIBRARY)).read_bytes()).hexdigest(),
            "engine_source_sha256": hashlib.sha256(b"".join(p.name.encode()+p.read_bytes() for p in sorted((ROOT/"ocaml/mahjong_core/lib").glob("*.ml")) if not p.name.startswith("._"))).hexdigest(),
            "challengers": challengers, "opponents": opponents, "torch": torch.__version__,
            "frozen_before_evaluation": True}
    (args.output/"plan.json").write_text(json.dumps(meta, indent=2))
    summaries, comparisons = {}, {}
    started = time.perf_counter()
    with mp.get_context("spawn").Pool(args.workers, initializer=initialize, initargs=(str(args.old), str(args.new))) as pool:
        for opponent in opponents:
            reports = {}
            for challenger in challengers:
                payloads = [(args.seed_start+offset, min(25, args.seeds-offset), challenger, opponent) for offset in range(0, args.seeds, 25)]
                rows = [row for part in pool.map(chunk, payloads) for row in part]
                key = f"{challenger}-vs-{opponent}"
                summary = summarize(rows)
                report = {**meta, "challenger": challenger, "opponent": opponent, **summary, "rows": rows}
                (args.output/f"{key}.json").write_text(json.dumps(report))
                reports[challenger] = rows
                summaries[key] = summary
                print(json.dumps({"match": key, **summary}), flush=True)
            if "old-guard" in reports:
                comparisons[opponent] = {c: compare(rows, reports["old-guard"]) for c, rows in reports.items() if c != "old-guard"}
            result = {**meta, "summaries": summaries, "paired_vs_old_guard": comparisons, "wall_seconds": time.perf_counter()-started}
            (args.output/"summary.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
