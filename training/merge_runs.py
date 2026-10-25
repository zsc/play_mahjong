from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def merge_reports(reports: list[dict]) -> dict:
    if not reports:
        raise ValueError("at least one evaluation report is required")
    contract_keys = (
        "policy",
        "model_scope",
        "discard_guard",
        "heuristic_variant",
        "scaffold_variant",
        "opponent_variant",
        "checkpoint",
        "opponent",
        "seat_rotation",
    )
    reference = reports[0]
    for report in reports[1:]:
        mismatches = {
            key: (reference.get(key), report.get(key))
            for key in contract_keys
            if reference.get(key) != report.get(key)
        }
        if mismatches:
            raise ValueError(f"evaluation reports have different contracts: {mismatches}")

    rows_by_key: dict[tuple[int, int], dict] = {}
    for report in reports:
        for row in report.get("rows", []):
            key = (int(row["seed"]), int(row["model_seat"]))
            if key in rows_by_key:
                raise ValueError(f"duplicate evaluation row: {key}")
            rows_by_key[key] = row
    if not rows_by_key:
        raise ValueError("evaluation reports contain no rows")

    rows = [rows_by_key[key] for key in sorted(rows_by_key)]
    deltas = np.asarray([row["model_delta"] for row in rows], dtype=np.float64)
    games = len(rows)
    wins = sum(row["winner"] == row["model_seat"] for row in rows if row["outcome"] == "win")
    discards = sum(row["discarder"] == row["model_seat"] for row in rows if row["outcome"] == "win")
    draws = sum(row["outcome"] == "exhaustive-draw" for row in rows)
    standard_error = float(deltas.std(ddof=1) / np.sqrt(games)) if games > 1 else 0.0
    merged = {key: reference.get(key) for key in contract_keys}
    merged.update(
        {
            "checkpoint_metadata": reference.get("checkpoint_metadata"),
            "games": games,
            "seed_start": min(int(row["seed"]) for row in rows),
            "mean_net_score": float(deltas.mean()),
            "std_net_score": float(deltas.std(ddof=1)) if games > 1 else 0.0,
            "mean_standard_error": standard_error,
            "win_rate": wins / games,
            "discard_rate": discards / games,
            "exhaustive_draw_rate": draws / games,
            "rows": rows,
        }
    )
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge sharded evaluation reports without double counting")
    parser.add_argument("--input", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reports = [json.loads(path.read_text()) for path in args.input]
    merged = merge_reports(reports)
    merged["shard_inputs"] = [str(path) for path in args.input]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
    print(
        f"merged {merged['games']} games: mean net score {merged['mean_net_score']:.3f} "
        f"+/- {merged['mean_standard_error']:.3f}, win {merged['win_rate']:.1%}, "
        f"discard {merged['discard_rate']:.1%}, draw {merged['exhaustive_draw_rate']:.1%}"
    )


if __name__ == "__main__":
    main()
