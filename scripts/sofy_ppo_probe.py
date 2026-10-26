"""Bounded single-accelerator PPO throughput probe in a SOFY code bundle."""
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import torch


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ["MAHJONG_FFI_LIBRARY"] = str(root / "native/mahjong_ffi.so")
    torch.set_num_threads(1)
    details = {"host": platform.node(), "python": sys.version, "torch": torch.__version__,
               "cpu_count": os.cpu_count(), "affinity": len(os.sched_getaffinity(0)),
               "gpu": torch.cuda.get_device_name(0), "cuda": torch.version.cuda}
    for name in ["/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/cpu/cpu.cfs_quota_us",
                 "/sys/fs/cgroup/cpu/cpu.cfs_period_us"]:
        if Path(name).exists():
            details[name] = Path(name).read_text().strip()
    print(json.dumps(details), flush=True)
    # Confirm the PPU CUDA compatibility layer really executes finite gradients.
    x = torch.randn(128, 771, device="cuda", requires_grad=True)
    w = torch.randn(771, 256, device="cuda", requires_grad=True)
    (x @ w).square().mean().backward()
    if not torch.isfinite(w.grad).all():
        raise RuntimeError("accelerator gradient smoke failed")
    out = root / "probe-results"
    out.mkdir(exist_ok=False)
    rows = []
    for workers, batch in [(8, 16), (16, 32), (32, 32), (48, 32)]:
        stem = f"w{workers}-b{batch}"
        checkpoint = out / f"{stem}.pt"
        args = [sys.executable, "-u", "training/train_ppo.py", "--init", "initial.bin",
                "--output", str(checkpoint), "--updates", "3", "--games-per-update", "2048",
                "--workers", str(workers), "--rollout-batch-size", str(batch), "--device", "cuda",
                "--minibatch-size", "2048", "--ppo-epochs", "4", "--learning-rate", "0.00003",
                "--scaffold-variant", "qualified-tenpai", "--opponent-variant", "qualified-tenpai",
                "--seed-start", "20000000", "--seed", "20261026"]
        started = time.perf_counter()
        with (out / f"{stem}.log").open("w") as log:
            subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
        saved = torch.load(checkpoint, map_location="cpu", weights_only=False)
        history = saved["history"]
        row = {"workers": workers, "batch": batch, "wall_seconds": time.perf_counter() - started,
               "history": history, "steady_games_per_second": statistics.median(h["rollout_games_per_second"] for h in history[1:])}
        rows.append(row)
        (out / "report.json").write_text(json.dumps({"environment": details, "runs": rows}, indent=2))
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
