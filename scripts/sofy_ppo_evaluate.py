"""Evaluate predeclared immutable PPO snapshots while other branches train."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--branch", type=int, choices=range(4), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ["MAHJONG_FFI_LIBRARY"] = str(root / "native/mahjong_ffi.so")
    run = args.training_root / f"large-ppo-b{args.branch}"
    out = run / "development"
    out.mkdir(exist_ok=False)
    rows = []

    def evaluate(name, checkpoint=None, guard="none", heuristic=None):
        output = out / f"{name}.json"
        command = [sys.executable, "-u", "training/evaluate_parallel.py", "--output", str(output),
                   "--games", "3200", "--shard-games", "200", "--workers", "16", "--seed-start", "30000000",
                   "--opponent-variant", "qualified-tenpai", "--scaffold-variant", "qualified-tenpai"]
        if checkpoint:
            command += ["--checkpoint", str(checkpoint), "--discard-guard", guard]
        else:
            command += ["--policy", "heuristic", "--heuristic-variant", heuristic]
        with (out / f"{name}.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
        report = json.loads(output.read_text())
        row = {"name": name, "checkpoint": str(checkpoint) if checkpoint else None, "guard": guard,
               "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest() if checkpoint else None,
               "report": str(output), "mean_net_score": report["mean_net_score"],
               "win_rate": report["win_rate"], "discard_rate": report["discard_rate"],
               "exhaustive_draw_rate": report["exhaustive_draw_rate"], "games": report["games"]}
        rows.append(row)
        (out / "summary.json").write_text(json.dumps(rows, indent=2))
        print(json.dumps(row), flush=True)

    if args.branch == 0:
        evaluate("previous-candidate", args.training_root / "initial.bin", "teacher-optimal")
        evaluate("qualified", heuristic="qualified-tenpai")
        evaluate("closed", heuristic="closed")
    deadline = time.monotonic() + 3600
    for update in [32, 64, 96, 128]:
        checkpoint = run / f"latest-u{update:04d}.pt"
        while not checkpoint.exists():
            if time.monotonic() > deadline:
                raise TimeoutError(f"snapshot never arrived: {checkpoint}")
            time.sleep(10)
        time.sleep(2)  # Immutable snapshots must finish their initial write.
        for guard in ["none", "teacher-optimal"]:
            evaluate(f"u{update:04d}-{guard}", checkpoint, guard)
    print(f"DEVELOPMENT_COMPLETE branch={args.branch}", flush=True)


if __name__ == "__main__":
    main()
