"""Freeze one development winner, then evaluate once on the untouched holdout."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-root", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    sys.path.insert(0, str(root / "training"))
    from compare_runs import paired_comparison
    os.environ["MAHJONG_FFI_LIBRARY"] = str(root / "native/mahjong_ffi.so")
    source = args.training_root
    out = source / "acceptance"
    if out.exists():
        raise ValueError("acceptance already exists; do not reuse holdout to retune")
    summaries = []
    for branch in range(4):
        rows = json.loads((source / f"large-ppo-b{branch}/development/summary.json").read_text())
        expected = {f"u{u:04d}-{g}" for u in [32, 64, 96, 128] for g in ["none", "teacher-optimal"]}
        if not expected.issubset({r["name"] for r in rows}):
            raise ValueError("development set is incomplete")
        summaries.extend(rows)
    original = next(r for r in summaries if r["name"] == "previous-candidate")
    candidates = [r for r in summaries if r["name"].startswith("u")]
    winner = max(candidates, key=lambda r: r["mean_net_score"])
    out.mkdir()
    frozen = {"selected": winner, "previous": original, "candidates": candidates,
              "holdout_seed_start": 31000000, "holdout_games": 6400}
    (out / "selection.json").write_text(json.dumps(frozen, indent=2))
    if winner["mean_net_score"] <= original["mean_net_score"]:
        (out / "result.json").write_text(json.dumps({"passed": False, "reason": "No development improvement; holdout untouched"}))
        print("NO_DEVELOPMENT_IMPROVEMENT; existing browser candidate retained", flush=True)
        return
    checkpoint = Path(winner["checkpoint"])
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != winner["sha256"]:
        raise ValueError("selected checkpoint changed")
    print("FROZEN " + json.dumps(winner), flush=True)

    def evaluate(name):
        output = out / f"{name}.json"
        command = [sys.executable, "-u", "training/evaluate_parallel.py", "--output", str(output),
                   "--games", "6400", "--shard-games", "200", "--workers", "16", "--seed-start", "31000000",
                   "--opponent-variant", "qualified-tenpai", "--scaffold-variant", "qualified-tenpai"]
        if name == "qualified":
            command += ["--policy", "heuristic", "--heuristic-variant", "qualified-tenpai"]
        else:
            command += ["--checkpoint", str(checkpoint if name == "candidate" else source / "initial.bin"),
                        "--discard-guard", winner["guard"] if name == "candidate" else "teacher-optimal"]
        with (out / f"{name}.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
        return name, json.loads(output.read_text())

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        reports = dict(pool.map(evaluate, ["candidate", "previous", "qualified"]))
    comparisons = {name: paired_comparison(reports["candidate"], reports[name]) for name in ["previous", "qualified"]}
    passed = all(value["ci95"][0] > -1 for value in comparisons.values())
    result = {"passed": passed, "proven_improvement": comparisons["previous"]["ci95"][0] > 0,
              "selection": frozen, "comparisons": comparisons,
              "reports": {name: {k: v for k, v in r.items() if k != "rows"} for name, r in reports.items()}}
    (out / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"passed": passed, "proven_improvement": result["proven_improvement"], "comparisons": comparisons}), flush=True)


if __name__ == "__main__":
    main()
