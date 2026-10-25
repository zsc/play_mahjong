"""Compare exported logits and selected actions on actual player observations."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from evaluate import load_policy
from mahjong_ai.actions import DISCARD_START, HU
from mahjong_ai.engine import MahjongEngine
from mahjong_ai.features import action_mask, encode_observation
from mahjong_ai.restrictions import teacher_optimal_discards
from mahjong_ai.teachers import resolve_scaffold_variant


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--onnx", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=12500000)
    parser.add_argument("--discard-guard", choices=("none", "teacher-optimal"), default="none")
    args = parser.parse_args()
    if args.output.exists() or args.games <= 0:
        parser.error("output must be new and games positive")
    torch.set_num_threads(1)
    model, checkpoint = load_policy(args.checkpoint, torch.device("cpu"))
    scaffold = resolve_scaffold_variant(None, checkpoint)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    session = ort.InferenceSession(str(args.onnx), sess_options=options, providers=["CPUExecutionProvider"])
    samples, max_logits, max_value = 0, 0.0, 0.0
    with MahjongEngine() as engine:
        for offset in range(args.games):
            game = engine.new_game(args.seed_start + offset)
            try:
                for _ in range(2000):
                    actor = engine.actor(game)
                    if actor is None:
                        engine.validate(game)
                        break
                    if actor != offset % 4:
                        action = engine.heuristic_action(game, actor, scaffold)
                    else:
                        observation, _ = engine.observe(game, actor)
                        legal = set(observation["legal_action_ids"])
                        if observation["phase"]["kind"] == "discard" and HU not in legal:
                            allowed = {a for a in legal if DISCARD_START <= a < DISCARD_START + 34}
                            if args.discard_guard == "teacher-optimal":
                                allowed = teacher_optimal_discards(observation, allowed)
                            mask = action_mask(observation)
                            mask[:] = False
                            mask[list(allowed)] = True
                            features = encode_observation(observation)[None, :]
                            mask = mask[None, :]
                            with torch.inference_mode():
                                logits, value = model(torch.from_numpy(features), torch.from_numpy(mask))
                            actual_logits, actual_value = session.run(None, {"features": features, "mask": mask})
                            max_logits = max(max_logits, float(np.abs(logits.numpy() - actual_logits).max()))
                            max_value = max(max_value, float(np.abs(value.numpy() - actual_value).max()))
                            action = int(logits.argmax())
                            if int(actual_logits.argmax()) != action or action not in allowed:
                                raise RuntimeError("ONNX selected a different or illegal action")
                            samples += 1
                        else:
                            action = engine.heuristic_action(game, actor, scaffold)
                    engine.step(game, actor, action)
                else:
                    raise RuntimeError("game did not terminate")
            finally:
                engine.close(game)
    if samples == 0 or max_logits > 1e-4 or max_value > 1e-4:
        raise RuntimeError("real-observation parity failed")
    report = {"passed": True, "games": args.games, "seed_start": args.seed_start, "samples": samples,
              "backend": "onnxruntime CPUExecutionProvider", "all_actions_identical": True,
              "logits_max_abs_error": max_logits, "value_max_abs_error": max_value,
              "discard_guard": args.discard_guard,
              "onnx_sha256": hashlib.sha256(args.onnx.read_bytes()).hexdigest(),
              "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
