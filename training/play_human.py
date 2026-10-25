"""本地终端人测：玩家观察经过引擎过滤，所有动作由正式状态机校验。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch
from evaluate import load_policy, model_action
from mahjong_ai.actions import CONCEALED_KONG_START, DISCARD_START, HU
from mahjong_ai.engine import MahjongEngine
from mahjong_ai.restrictions import teacher_optimal_discards
from mahjong_ai.teachers import resolve_scaffold_variant

TILES = [f"{rank}{suit}" for suit in ("万", "条", "筒") for rank in range(1, 10)] + [
    "东", "南", "西", "北", "中", "发", "白",
]
CODES = [f"{suit}{rank}" for suit in ("W", "T", "B") for rank in range(1, 10)] + [
    "F1", "F2", "F3", "F4", "J3", "J2", "J1",
]
NAMES = dict(zip(CODES + list("abcdefgh"), TILES + list("春夏秋冬梅兰竹菊"), strict=True))


def action_label(action: dict, hidden: bool = False) -> str:
    key = action["key"]
    if hidden and CONCEALED_KONG_START <= action["id"] < CONCEALED_KONG_START + 34:
        return "暗杠（牌种未公开）"
    names = {"hu": "胡", "pass": "过", "expose-flower": "补花", "pung": "碰", "kong": "直杠"}
    if key in names:
        return names[key]
    for prefix, label in (("discard-flower-", "弃花"), ("concealed-kong-", "暗杠"),
                          ("added-kong-", "加杠"), ("discard-", "打")):
        if key.startswith(prefix):
            return label + NAMES[key[len(prefix):]]
    if key.startswith("chow-"):
        rank = int(key.split("-")[1])
        return f"吃 {rank}-{rank+1}-{rank+2}（响应牌同花色）"
    return key


def show(observation: dict) -> None:
    hand = [TILES[kind] for kind, count in enumerate(observation["hand"]) for _ in range(count)]
    flowers = " ".join(NAMES[code] for code in observation["flowers"])
    drawn = observation.get("drawn")
    print(f"\n手牌：{' '.join(hand)}  当前摸牌：{NAMES.get(drawn, '无')}  牌墙：{observation['wall_remaining']}")
    print(f"已补花牌：{flowers or '无'}")
    meld_names = {"chow": "吃", "pung": "碰", "kong": "杠"}
    for seat, melds in enumerate(observation["melds"]):
        public = [f"{meld_names[meld['kind']]}:{NAMES.get(meld['tile'], '暗牌')}" for meld in melds]
        river = " ".join(NAMES[code] for code in observation["rivers"][seat])
        print(f"{TILES[27 + seat]}家 副露 {' '.join(public) or '无'} | 牌河 {river or '无'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=15000000)
    parser.add_argument("--seat", type=int, choices=range(4), default=0)
    parser.add_argument("--discard-guard", choices=("none", "teacher-optimal"), default="none")
    parser.add_argument("--watch", action="store_true", help="四家自动对局，仍只展示所选座位可见信息")
    parser.add_argument("--replay", type=Path, help="保存含隐藏动作的完整调试回放，不直接输入策略")
    args = parser.parse_args()
    if args.replay and args.replay.exists():
        parser.error("回放路径已存在，请使用新路径")
    torch.set_num_threads(1)
    device = torch.device("cpu")
    model, checkpoint = load_policy(args.checkpoint, device)
    scaffold = resolve_scaffold_variant(None, checkpoint)
    print(f"阶段一 MCR 人测；不是完整 MCR。模型：{args.checkpoint.name}；非弃牌动作：{scaffold} 启发式。")
    print(f"玩家：{TILES[27 + args.seat]}家；输入合法动作 ID，q 退出。guard={args.discard_guard}")
    actions = []
    with MahjongEngine() as engine:
        game = engine.new_game(args.seed)
        for _ in range(2000):
            actor = engine.actor(game)
            if actor is None:
                observation, _ = engine.observe(game, args.seat)
                outcome = observation["phase"]["outcome"]
                print("结算：" + json.dumps(outcome, ensure_ascii=False))
                if args.replay:
                    replay = {"ruleset_id": "mcr-wmo2006-stage1", "seed": args.seed,
                              "checkpoint": str(args.checkpoint), "checkpoint_sha256": hashlib.sha256(
                                  args.checkpoint.read_bytes()).hexdigest(),
                              "actions": actions, "outcome": outcome,
                              "contains_hidden_actions": True}
                    args.replay.parent.mkdir(parents=True, exist_ok=True)
                    args.replay.write_text(json.dumps(replay, ensure_ascii=False, indent=2) + "\n")
                return
            observation, _ = engine.observe(game, actor)
            legal = set(observation["legal_action_ids"])
            labels = {action["id"]: action for action in observation["legal_actions"]}
            if actor == args.seat and not args.watch:
                show(observation)
                print(" | ".join(f"{action}: {action_label(labels[action])}" for action in sorted(legal)))
                while True:
                    try:
                        answer = input("动作> ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print("\n退出本盘，未结算。")
                        return
                    if answer.lower() == "q":
                        return
                    if answer.isdigit() and int(answer) in legal:
                        chosen = int(answer)
                        break
                    print("请输入上方合法动作 ID。")
            elif observation["phase"]["kind"] == "discard" and HU not in legal:
                allowed = {action for action in legal if DISCARD_START <= action < DISCARD_START + 34}
                if args.discard_guard == "teacher-optimal":
                    allowed = teacher_optimal_discards(observation, allowed)
                chosen = model_action(model, observation, device, allowed)
            else:
                chosen = engine.heuristic_action(game, actor, scaffold)
            print(f"{TILES[27 + actor]}家：{action_label(labels[chosen], hidden=actor != args.seat)}")
            event = engine.step(game, actor, chosen)
            actions.append({"seat": actor, "action_id": chosen, "event": event})
        raise RuntimeError("超出 2000 次决策，未完成结算")


if __name__ == "__main__":
    main()
