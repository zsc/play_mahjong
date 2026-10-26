"""Launch the fixed four-seat strength tests on the existing SOFY allocation."""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-root", type=Path, required=True)
    parser.add_argument("--suite", choices=("primary", "secondary"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ["MAHJONG_FFI_LIBRARY"] = str(root / "native/mahjong_ffi.so")
    command = [sys.executable, "-u", "training/arena.py", "--old", str(args.training_root / "initial.bin"),
               "--new", str(args.training_root / "large-ppo-b2/latest-u0032.pt"),
               "--output", str(args.training_root / f"arena-{args.suite}")]
    command += (["--seed-start", "40000000", "--seeds", "8000", "--workers", "48"] if args.suite == "primary" else
                ["--seed-start", "41000000", "--seeds", "1000", "--workers", "32",
                 "--challengers", "old-guard,new-guard,qualified", "--opponents", "closed,old-guard"])
    subprocess.run(command, check=True, timeout=1800)


if __name__ == "__main__":
    main()
