"""Generate disjoint teacher shards without replacing existing experiments."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--games", type=int, default=30000)
    parser.add_argument("--shard-games", type=int, default=1250)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--teacher-variant", default="qualified-tenpai")
    args = parser.parse_args()
    if min(args.games, args.shard_games, args.workers) <= 0:
        parser.error("games, shard-games and workers must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "logs").mkdir()
    start = time.perf_counter()

    def run(offset: int) -> dict:
        shard = offset // args.shard_games
        games = min(args.shard_games, args.games - offset)
        output = args.output_dir / f"shard-{shard:03d}.npz"
        command = [sys.executable, str(Path(__file__).with_name("generate_bc.py")),
                   "--games", str(games), "--seed-start", str(args.seed_start + offset),
                   "--teacher-variant", args.teacher_variant, "--output", str(output)]
        shard_start = time.perf_counter()
        with (args.output_dir / "logs" / f"shard-{shard:03d}.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        result = {"shard": shard, "games": games, "seconds": time.perf_counter() - shard_start}
        print(json.dumps(result), flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        shards = list(pool.map(run, range(0, args.games, args.shard_games)))
    report = {"games": args.games, "seed_start": args.seed_start, "workers": args.workers,
              "teacher_variant": args.teacher_variant, "wall_seconds": time.perf_counter() - start,
              "shards": shards}
    (args.output_dir / "generation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
