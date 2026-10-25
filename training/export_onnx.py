from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from mahjong_ai.actions import ACTION_CATALOG_VERSION, ACTION_COUNT
from mahjong_ai.features import FEATURE_ENCODING_VERSION, FEATURE_SIZE, OBSERVATION_VERSION
from model import PolicyValueNet

RULESET_ID = "mcr-wmo2006-stage1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_checkpoint(checkpoint: dict) -> None:
    expected = {
        "ruleset_id": RULESET_ID,
        "observation_version": OBSERVATION_VERSION,
        "feature_encoding_version": FEATURE_ENCODING_VERSION,
        "action_catalog_version": ACTION_CATALOG_VERSION,
        "feature_size": FEATURE_SIZE,
        "action_count": ACTION_COUNT,
    }
    mismatches = {
        key: (checkpoint.get(key), value)
        for key, value in expected.items()
        if checkpoint.get(key) != value
    }
    if mismatches:
        raise ValueError(f"checkpoint contract mismatch: {mismatches}")
    if checkpoint.get("format_version") != 1:
        raise ValueError("unsupported checkpoint format")


def evaluation_record(path: Path, checkpoint_path: Path) -> dict:
    report = json.loads(path.read_text())
    reported_checkpoint = report.get("checkpoint")
    if reported_checkpoint is not None and Path(reported_checkpoint).resolve() != checkpoint_path.resolve():
        raise ValueError(
            f"evaluation checkpoint mismatch in {path}: {reported_checkpoint} != {checkpoint_path}"
        )
    fields = (
        "policy",
        "model_scope",
        "discard_guard",
        "heuristic_variant",
        "scaffold_variant",
        "opponent_variant",
        "games",
        "seed_start",
        "mean_net_score",
        "mean_standard_error",
        "win_rate",
        "discard_rate",
        "exhaustive_draw_rate",
        "paired_baseline",
    )
    return {
        "path": str(path),
        "sha256": sha256(path),
        **{field: report.get(field) for field in fields},
    }


def export_model(
    checkpoint_path: Path,
    output: Path,
    evaluation_paths: list[Path] | None = None,
) -> dict:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    validate_checkpoint(checkpoint)
    model = PolicyValueNet(hidden=int(checkpoint["hidden"]))
    model.load_state_dict(checkpoint["model"])
    model.eval()

    sample_features = torch.zeros(1, FEATURE_SIZE, dtype=torch.float32)
    sample_mask = torch.zeros(1, ACTION_COUNT, dtype=torch.bool)
    sample_mask[0, 0] = True
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        (sample_features, sample_mask),
        output,
        input_names=["features", "mask"],
        output_names=["logits", "value"],
        dynamic_axes={
            "features": {0: "batch"},
            "mask": {0: "batch"},
            "logits": {0: "batch"},
            "value": {0: "batch"},
        },
        opset_version=18,
        do_constant_folding=True,
        dynamo=False,
    )
    onnx_model = onnx.load(output)
    onnx.checker.check_model(onnx_model)

    mask = np.zeros((2, ACTION_COUNT), dtype=np.bool_)
    mask[0, [0, 3, 4]] = True
    mask[1, 40:50] = True
    features = np.random.default_rng(20261026).standard_normal((2, FEATURE_SIZE)).astype(np.float32)
    with torch.inference_mode():
        torch_logits, torch_value = model(torch.from_numpy(features), torch.from_numpy(mask))
    session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
    onnx_logits, onnx_value = session.run(
        ["logits", "value"], {"features": features, "mask": mask}
    )
    logits_error = float(np.max(np.abs(torch_logits.numpy() - onnx_logits)))
    value_error = float(np.max(np.abs(torch_value.numpy() - onnx_value)))
    if logits_error > 1e-4 or value_error > 1e-4:
        raise RuntimeError(
            f"ONNX parity failed: logits max error {logits_error}, value max error {value_error}"
        )

    return {
        "format_version": 1,
        "model_id": checkpoint_path.stem,
        "stage": checkpoint.get("algorithm", "unknown"),
        "is_smoke": bool(checkpoint.get("is_smoke", True)),
        "is_random": False,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "files": {
            "checkpoint": {
                "path": str(checkpoint_path),
                "sha256": sha256(checkpoint_path),
            },
            "onnx": {"path": output.name, "sha256": sha256(output)},
        },
        "contract": {
            "ruleset_id": RULESET_ID,
            "observation_version": OBSERVATION_VERSION,
            "feature_encoding_version": FEATURE_ENCODING_VERSION,
            "action_catalog_version": ACTION_CATALOG_VERSION,
            "feature_size": FEATURE_SIZE,
            "action_count": ACTION_COUNT,
            "hidden": int(checkpoint["hidden"]),
            "teacher_variant": checkpoint.get("teacher_variant"),
            "scaffold_variant": checkpoint.get("scaffold_variant"),
            "learned_scope": checkpoint.get("learned_scope"),
            "discard_guard": checkpoint.get("discard_guard"),
        },
        "io": {
            "inputs": [
                {"name": "features", "shape": ["batch", FEATURE_SIZE], "dtype": "float32"},
                {"name": "mask", "shape": ["batch", ACTION_COUNT], "dtype": "bool"},
            ],
            "outputs": [
                {"name": "logits", "shape": ["batch", ACTION_COUNT], "dtype": "float32"},
                {"name": "value", "shape": ["batch"], "dtype": "float32"},
            ],
            "mask_semantics": "true means legal; legal logits use argmax after applying the supplied mask",
            "value_semantics": "tanh-scaled expected final score divided by 64, not a win probability",
            "seat_mapping": "absolute seat indices 0..3 and one-hot seat/round winds; no relative-seat rotation",
            "normalization": "see feature_encoding_version 6; counts are divided by their tile limits and hint arrays are clipped",
            "selection": "deterministic argmax; illegal logits must never be selected by the caller",
        },
        "training": {
            "seed": checkpoint.get("training_seed"),
            "epoch": checkpoint.get("epoch"),
            "updates": checkpoint.get("update"),
            "workers": checkpoint.get("workers"),
            "best_validation_loss": checkpoint.get("best_validation_loss"),
            "dataset": checkpoint.get("dataset"),
            "dataset_sha256": checkpoint.get("dataset_sha256"),
            "initial_checkpoint": checkpoint.get("initial_checkpoint"),
            "teacher_bc_coefficient": checkpoint.get("teacher_bc_coefficient"),
            "discard_guard": checkpoint.get("discard_guard"),
            "opponent_variant": checkpoint.get("opponent_variant"),
        },
        "evaluations": [
            evaluation_record(path, checkpoint_path) for path in (evaluation_paths or [])
        ],
        "parity": {
            "backend": "onnxruntime CPUExecutionProvider",
            "samples": 2,
            "logits_max_abs_error": logits_error,
            "value_max_abs_error": value_error,
        },
        "dependencies": {
            "torch": torch.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": ort.__version__,
        },
        "opset": 18,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a contract-checked policy checkpoint to ONNX")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--evaluation", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    manifest = export_model(args.checkpoint, args.output, args.evaluation)
    manifest["files"]["onnx"]["path"] = str(args.output)
    manifest_path = args.manifest or args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {args.output} and {manifest_path}")


if __name__ == "__main__":
    main()
