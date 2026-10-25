from __future__ import annotations

import json

import torch
from export_onnx import RULESET_ID, export_model
from mahjong_ai.actions import ACTION_CATALOG_VERSION, ACTION_COUNT
from mahjong_ai.features import FEATURE_ENCODING_VERSION, FEATURE_SIZE, OBSERVATION_VERSION
from model import PolicyValueNet


def test_onnx_export_writes_contract_and_parity(tmp_path) -> None:
    model = PolicyValueNet(hidden=16)
    checkpoint_path = tmp_path / "tiny.pt"
    torch.save(
        {
            "format_version": 1,
            "algorithm": "behavior_cloning",
            "ruleset_id": RULESET_ID,
            "observation_version": OBSERVATION_VERSION,
            "feature_encoding_version": FEATURE_ENCODING_VERSION,
            "action_catalog_version": ACTION_CATALOG_VERSION,
            "feature_size": FEATURE_SIZE,
            "action_count": ACTION_COUNT,
            "hidden": 16,
            "model": model.state_dict(),
            "is_smoke": True,
            "teacher_variant": "closed",
            "scaffold_variant": "closed",
        },
        checkpoint_path,
    )
    output = tmp_path / "tiny.onnx"
    manifest = export_model(checkpoint_path, output)
    assert output.exists()
    assert manifest["contract"]["feature_size"] == FEATURE_SIZE
    assert manifest["contract"]["teacher_variant"] == "closed"
    assert manifest["parity"]["logits_max_abs_error"] < 1e-4
    assert manifest["parity"]["value_max_abs_error"] < 1e-4
    assert manifest["files"]["onnx"]["sha256"]
    assert manifest["evaluations"] == []

    evaluation_path = tmp_path / "evaluation.json"
    evaluation_path.write_text(
        json.dumps(
            {
                "checkpoint": str(checkpoint_path),
                "policy": "model",
                "model_scope": "discard",
                "games": 1600,
                "seed_start": 6000000,
                "mean_net_score": 1.25,
                "mean_standard_error": 0.5,
                "win_rate": 0.25,
                "discard_rate": 0.1,
                "exhaustive_draw_rate": 0.05,
            }
        )
    )
    manifest = export_model(checkpoint_path, output, [evaluation_path])
    assert manifest["evaluations"][0]["games"] == 1600
    assert manifest["evaluations"][0]["mean_net_score"] == 1.25
    assert manifest["evaluations"][0]["sha256"]
