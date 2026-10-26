"""Run one bounded, reproducible PPO branch on its assigned SOFY accelerator."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", type=int, choices=range(4), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ["MAHJONG_FFI_LIBRARY"] = str(root / "native/mahjong_ffi.so")
    learning_rate, teacher_bc = [(3e-5, 0.1), (3e-5, 0.5), (1e-4, 0.1), (1e-4, 0.5)][args.branch]
    run = root / f"large-ppo-b{args.branch}"
    run.mkdir(exist_ok=False)
    initial = root / "initial.bin"
    if hashlib.sha256(initial.read_bytes()).hexdigest() != "1f865a82f1d0ff30266ec9ae0857993bb600700727de3799987b2f86b390dc62":
        raise ValueError("wrong initial checkpoint")
    config = {"branch": args.branch, "learning_rate": learning_rate, "teacher_bc": teacher_bc,
              "updates": 128, "games_per_update": 4096, "workers": 32, "batch_size": 32,
              "training_seed_start": 21000000 + args.branch * 2000000,
              "selection_seed_start": 30000000, "selection_games": 3200,
              "holdout_seed_start": 31000000, "holdout_games": 6400,
              "initial_sha256": hashlib.sha256(initial.read_bytes()).hexdigest(),
              "task_id": os.environ.get("SOFY_TASK_ID"), "torch": torch.__version__}
    (run / "config.json").write_text(json.dumps(config, indent=2))
    print(json.dumps(config), flush=True)
    subprocess.run([sys.executable, "-u", "training/train_ppo.py", "--init", str(initial),
                    "--output", str(run / "latest.pt"), "--updates", "128", "--games-per-update", "4096",
                    "--workers", "32", "--rollout-batch-size", "32", "--device", "cuda",
                    "--minibatch-size", "2048", "--ppo-epochs", "4", "--learning-rate", str(learning_rate),
                    "--teacher-bc-coefficient", str(teacher_bc), "--discard-guard", "none",
                    "--scaffold-variant", "qualified-tenpai", "--opponent-variant", "qualified-tenpai",
                    "--seed-start", str(config["training_seed_start"]), "--seed", str(202610260 + args.branch),
                    "--snapshot-every", "32", "--snapshot-dir", str(run)], check=True, timeout=3600)
    saved = torch.load(run / "latest.pt", map_location="cpu", weights_only=False)
    if saved["update"] != 128 or not all(torch.isfinite(t).all() for t in saved["model"].values()):
        raise RuntimeError("invalid trained checkpoint")
    (run / "history.json").write_text(json.dumps(saved["history"], indent=2))
    print(f"TRAINING_COMPLETE branch={args.branch} games={128 * 4096}", flush=True)


if __name__ == "__main__":
    main()
