"""Reproducible, single-process profiling of the real teacher/data path."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from collections import defaultdict
from pathlib import Path

from mahjong_ai.engine import DEFAULT_LIBRARY, ROOT, MahjongEngine
from mahjong_ai.features import action_mask, encode_observation
from mahjong_ai.teachers import HEURISTIC_VARIANTS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=12000000)
    parser.add_argument("--teacher-variant", choices=HEURISTIC_VARIANTS, default="qualified-tenpai")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.games <= 0:
        parser.error("--games must be positive")
    if args.output.exists():
        parser.error("output exists; choose a new path to preserve benchmark evidence")
    totals: dict[str, float] = defaultdict(float)
    calls: dict[str, int] = defaultdict(int)
    digest = hashlib.sha256()

    def measured(name, function, *arguments):
        start = time.perf_counter()
        result = function(*arguments)
        totals[name] += time.perf_counter() - start
        calls[name] += 1
        return result

    start = time.perf_counter()
    decisions = 0
    with MahjongEngine() as engine:
        for seed in range(args.seed_start, args.seed_start + args.games):
            game = measured("new", engine.new_game, seed)
            try:
                for _ in range(2000):
                    actor = measured("actor", engine.actor, game)
                    if actor is None:
                        observation, _ = measured("terminal_observe", engine.observe, game, 0)
                        digest.update(json.dumps(observation, sort_keys=True).encode())
                        engine.validate(game)
                        break
                    observation, _ = measured("observe", engine.observe, game, actor)
                    features = measured("encode", encode_observation, observation)
                    mask = measured("mask", action_mask, observation)
                    action = measured("teacher", engine.heuristic_action, game, actor, args.teacher_variant)
                    assert mask[action]
                    result = measured("step", engine.step, game, actor, action)
                    # Fingerprint all public observations, encoded features, actions and outcomes.
                    digest.update(json.dumps([seed, actor, observation, action, result], sort_keys=True).encode())
                    digest.update(features.tobytes())
                    decisions += 1
                else:
                    raise RuntimeError(f"game {seed} exceeded 2000 steps")
            finally:
                measured("close", engine.close, game)
    elapsed = time.perf_counter() - start
    backend = Path(os.environ.get("MAHJONG_FFI_SERVER", os.environ.get("MAHJONG_FFI_LIBRARY", DEFAULT_LIBRARY)))
    source_paths = sorted((ROOT / "ocaml" / "mahjong_core").rglob("*.ml"))
    source_paths += sorted((ROOT / "ocaml" / "mahjong_ffi").rglob("*.ml"))
    source_paths += sorted((ROOT / "training" / "mahjong_ai").glob("*.py"))
    report = {
        "ruleset_id": "mcr-wmo2006-stage1",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "transport": "json-lines" if os.environ.get("MAHJONG_FFI_SERVER") else "ctypes-json",
        "workers": 1,
        "batch_size": 1,
        "games": args.games,
        "seed_start": args.seed_start,
        "teacher_variant": args.teacher_variant,
        "decisions": decisions,
        "wall_seconds": elapsed,
        "decisions_per_second": decisions / elapsed,
        "games_per_second": args.games / elapsed,
        "seconds": dict(totals),
        "calls": dict(calls),
        "trajectory_sha256": digest.hexdigest(),
        "backend_sha256": hashlib.sha256(backend.read_bytes()).hexdigest(),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths
        },
        "notes": "Includes fingerprint/validation overhead; no NPZ compression, training or GPU work.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
