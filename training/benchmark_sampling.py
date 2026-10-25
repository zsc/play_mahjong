"""Measure actual teacher/PPO sampling, boundary calls and inference batches."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from generate_bc import play_game
from mahjong_ai.engine import DEFAULT_LIBRARY, MahjongEngine
from train_ppo import load_initial_model, rollout_range


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("teacher", "ppo"), required=True)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--games", type=int, default=240)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--checkpoint", type=Path, default=Path("training/checkpoints/bc-qualified-fast30k-v1.pt"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists")
    torch.set_num_threads(1)
    model, _ = load_initial_model(args.checkpoint, torch.device("cpu"))
    model.eval()
    inference_batches = []
    hook = model.register_forward_pre_hook(lambda _, arguments: inference_batches.append(arguments[0].shape[0]))
    repeats = []
    for repeat in range(args.repeats):
        torch.manual_seed(71)
        calls = Counter()
        inference_batches.clear()
        digest = hashlib.sha256()
        with MahjongEngine() as engine:
            original = engine._call

            def counted(request, calls=calls, original=original):
                calls[request["op"]] += 1
                return original(request)

            engine._call = counted
            start = time.perf_counter()
            if args.mode == "ppo":
                rows, outcomes, scores = rollout_range(engine, model, torch.device("cpu"), 12000000,
                    args.games, 0, 1, 2000, "none", "qualified-tenpai", "qualified-tenpai", .99, .95,
                    batch_size=args.batch_size)
            else:
                rows, outcomes, scores = [], Counter(), []
                for seed in range(12000000, 12000000 + args.games):
                    outcome, game_rows = play_game(engine, seed, "F1", 2000, "qualified-tenpai", args.chunk_size)
                    rows.extend(game_rows)
                    outcomes[outcome["kind"]] += 1
                    scores.append(outcome.get("deltas", [0, 0, 0, 0]))
            elapsed = time.perf_counter() - start
        # Fingerprinting is outside timed region, byte-identical features/masks/actions.
        for row in rows:
            digest.update(row["features"].tobytes())
            digest.update(row["mask"].tobytes())
            digest.update(np.asarray([row["action"]], dtype=np.int32).tobytes())
        digest.update(json.dumps([outcomes, scores], sort_keys=True).encode())
        repeats.append({"repeat": repeat, "seconds": elapsed, "games_per_second": args.games / elapsed,
                        "samples": len(rows), "boundary_calls": dict(calls),
                        "inference_calls": len(inference_batches),
                        "mean_inference_batch": float(np.mean(inference_batches)) if inference_batches else 0,
                        "trajectory_sha256": digest.hexdigest()})
    hook.remove()
    library = Path(os.environ.get("MAHJONG_FFI_LIBRARY", DEFAULT_LIBRARY))
    report = {"platform": platform.platform(), "cpu_count": os.cpu_count(), "workers": 1,
              "torch": torch.__version__, "ruleset_id": "mcr-wmo2006-stage1", "build": "dune native",
              "seed_start": 12000000, "sampling_seed": 71,
              "backend_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
              "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
              "config": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
              "repeats": repeats, "median_seconds": float(np.median([r["seconds"] for r in repeats]))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
