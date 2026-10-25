#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
exec uv run python training/play_human.py \
  --checkpoint training/checkpoints/ppo-qualified-fast30k-v1-u0040.pt \
  --discard-guard teacher-optimal "$@"
