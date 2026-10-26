"""Generate real native traces and PyTorch outputs for browser contract tests."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training"))
import torch
from evaluate import load_policy
from mahjong_ai.engine import MahjongEngine
from mahjong_ai.features import action_mask, encode_observation
from mahjong_ai.restrictions import teacher_optimal_discards

torch.set_num_threads(1)
model, _ = load_policy(ROOT / "training/checkpoints/ppo-qualified-fast30k-v1-u0040.pt", torch.device("cpu"))
traces = []
with MahjongEngine() as engine:
    for seed in range(16000100, 16000104):
        game = engine.new_game(seed)
        rows = []
        while (actor := engine.actor(game)) is not None:
            observation, _ = engine.observe(game, actor)
            row = {"observation": observation, "actor": actor,
                   "features": encode_observation(observation).tolist()}
            if observation["phase"]["kind"] == "discard" and 0 not in observation["legal_action_ids"]:
                allowed = teacher_optimal_discards(observation, {a for a in observation["legal_action_ids"] if 12 <= a < 46})
                mask = action_mask(observation)
                mask[:] = False
                mask[list(allowed)] = True
                with torch.inference_mode():
                    logits, value = model(torch.tensor([row["features"]]), torch.from_numpy(mask[None]))
                action = int(logits.argmax())
                row.update(allowed=sorted(allowed), logits=logits[0].tolist(), value=float(value.item()))
            else:
                action = engine.heuristic_action(game, actor, "qualified-tenpai")
            row["action"] = action
            row["result"] = engine.step(game, actor, action)
            rows.append(row)
            if len(rows) > 2000:
                raise RuntimeError("trace failed to terminate")
        engine.validate(game)
        final, _ = engine.observe(game, 0)
        traces.append({"seed": seed, "rows": rows, "final": final})
        engine.close(game)
out = ROOT / "web/tests/fixtures/native.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(traces))
print(f"Generated {len(traces)} games, {sum(len(t['rows']) for t in traces)} decisions: {out}")
