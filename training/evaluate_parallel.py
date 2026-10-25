"""Evaluate frozen policies in disjoint, seat-aligned shards."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path

from merge_runs import merge_reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games", type=int, default=1600)
    parser.add_argument("--shard-games", type=int, default=200)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--policy", choices=("model", "heuristic", "random"), default="model")
    parser.add_argument("--heuristic-variant", default="qualified-tenpai")
    parser.add_argument("--opponent-variant", default="qualified-tenpai")
    parser.add_argument("--scaffold-variant", default="qualified-tenpai")
    parser.add_argument("--discard-guard", choices=("none", "teacher-optimal"), default="none")
    args = parser.parse_args()
    if min(args.games, args.shard_games, args.workers) <= 0 or args.shard_games % 4:
        parser.error("positive arguments and shard-games divisible by four required")
    if args.output.exists():
        parser.error("output exists")
    shards = args.output.with_suffix("").with_name(args.output.stem + "-shards")
    shards.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()

    def run(offset: int) -> dict:
        shard = offset // args.shard_games
        output = shards / f"{shard:03d}.json"
        command = [sys.executable, str(Path(__file__).with_name("evaluate.py")),
                   "--games", str(min(args.shard_games, args.games - offset)),
                   "--seed-start", str(args.seed_start + offset), "--output", str(output),
                   "--policy", args.policy, "--heuristic-variant", args.heuristic_variant,
                   "--opponent-variant", args.opponent_variant, "--scaffold-variant", args.scaffold_variant,
                   "--discard-guard", args.discard_guard, "--device", "cpu"]
        if args.checkpoint:
            command.extend(["--checkpoint", str(args.checkpoint)])
        with output.with_suffix(".log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        return json.loads(output.read_text())

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        reports = list(pool.map(run, range(0, args.games, args.shard_games)))
    merged = merge_reports(reports)
    merged.update({"wall_seconds": time.perf_counter() - start, "workers": args.workers,
                   "shard_directory": str(shards)})
    args.output.write_text(json.dumps(merged, indent=2) + "\n")
    print(json.dumps({key: value for key, value in merged.items() if key != "rows"}), flush=True)


if __name__ == "__main__":
    main()
