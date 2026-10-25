from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import torch
from mahjong_ai.actions import ACTION_CATALOG_VERSION, ACTION_COUNT
from mahjong_ai.features import FEATURE_ENCODING_VERSION, FEATURE_SIZE, OBSERVATION_VERSION
from model import PolicyValueNet


def test_resume_matches_uninterrupted_updates(tmp_path: Path) -> None:
    torch.manual_seed(31)
    model = PolicyValueNet(hidden=32)
    initial = tmp_path / "initial.pt"
    torch.save({"format_version": 1, "ruleset_id": "mcr-wmo2006-stage1",
                "observation_version": OBSERVATION_VERSION, "feature_encoding_version": FEATURE_ENCODING_VERSION,
                "action_catalog_version": ACTION_CATALOG_VERSION, "feature_size": FEATURE_SIZE,
                "action_count": ACTION_COUNT, "hidden": 32, "model": model.state_dict(),
                "scaffold_variant": "qualified-tenpai", "is_smoke": True}, initial)
    root = Path(__file__).resolve().parents[2]
    command = [sys.executable, str(root / "training/train_ppo.py")]
    env = os.environ | {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    full = tmp_path / "full.pt"
    subprocess.run(command + ["--init", str(initial), "--output", str(full), "--updates", "2",
                             "--games-per-update", "2", "--workers", "1", "--ppo-epochs", "2",
                             "--seed-start", "12400000", "--device", "cpu", "--snapshot-every", "1",
                             "--snapshot-dir", str(tmp_path)], env=env, check=True, capture_output=True)
    split = tmp_path / "split.pt"
    subprocess.run(command + ["--resume", str(tmp_path / "full-u0001.pt"), "--output", str(split),
                             "--updates", "2", "--device", "cpu"], env=env, check=True, capture_output=True)
    a, b = (torch.load(path, weights_only=True) for path in (full, split))
    assert a["update"] == b["update"] == 2
    for name, value in a["model"].items():
        assert torch.equal(value, b["model"][name])
    for key, state in a["optimizer"]["state"].items():
        for name, value in state.items():
            assert torch.equal(value, b["optimizer"]["state"][key][name])
    assert a["rng_state"]["shuffle"] == b["rng_state"]["shuffle"]
