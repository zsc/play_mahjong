from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def indexed_deltas(report: dict) -> dict[tuple[int, int], int]:
    values: dict[tuple[int, int], int] = {}
    for row in report["rows"]:
        key = (int(row["seed"]), int(row["model_seat"]))
        if key in values:
            raise ValueError(f"duplicate evaluation row: {key}")
        values[key] = int(row["model_delta"])
    return values


def paired_comparison(candidate: dict, baseline: dict) -> dict:
    contract_keys = ("opponent_variant", "opponent", "seat_rotation", "ruleset_id",
                     "feature_encoding_version", "action_catalog_version", "engine_source_sha256")
    mismatches = {
        key: (candidate.get(key), baseline.get(key))
        for key in contract_keys
        if candidate.get(key) != baseline.get(key)
    }
    if mismatches:
        raise ValueError(f"reports use different comparison contracts: {mismatches}")
    candidate_rows = indexed_deltas(candidate)
    baseline_rows = indexed_deltas(baseline)
    candidate_keys = set(candidate_rows)
    baseline_keys = set(baseline_rows)
    if candidate_keys != baseline_keys:
        raise ValueError(
            "reports cover different seed/seat evaluations: "
            f"candidate_only={len(candidate_keys - baseline_keys)}, "
            f"baseline_only={len(baseline_keys - candidate_keys)}"
        )
    keys = sorted(candidate_keys)
    differences = np.asarray(
        [candidate_rows[key] - baseline_rows[key] for key in keys], dtype=np.float64
    )
    standard_error = (
        float(differences.std(ddof=1) / np.sqrt(len(differences)))
        if len(differences) > 1
        else 0.0
    )
    return {
        "candidate": str(candidate.get("checkpoint") or candidate.get("policy")),
        "baseline": str(baseline.get("checkpoint") or baseline.get("policy")),
        "games": len(differences),
        "mean_difference": float(differences.mean()),
        "standard_error": standard_error,
        "ci95": [
            float(differences.mean() - 1.96 * standard_error),
            float(differences.mean() + 1.96 * standard_error),
        ],
        "candidate_mean_net_score": float(np.mean(list(candidate_rows.values()))),
        "baseline_mean_net_score": float(np.mean(list(baseline_rows.values()))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare evaluation reports by seed and seat")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    candidate = json.loads(args.candidate.read_text())
    baseline = json.loads(args.baseline.read_text())
    result = paired_comparison(candidate, baseline)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
