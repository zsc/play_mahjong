from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mahjong_ai.engine import MahjongEngine

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "tests" / "fixtures" / "mcr-81-green-book-gold.tsv"

SUIT_BASE = {"m": 0, "s": 9, "p": 18}
HONOR_KIND = {"E": 27, "S": 28, "W": 29, "N": 30, "C": 31, "F": 32, "P": 33}
KIND_CODES = [
    "W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9",
    "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9",
    "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9",
    "F1", "F2", "F3", "F4", "J3", "J2", "J1",
]

FAN_NAMES = {
    "DASIXI": "Big Four Winds",
    "DASANYUAN": "Big Three Dragons",
    "LVYISE": "All Green",
    "JIULIANBAODENG": "Nine Gates",
    "SIGANG": "Four Kongs",
    "LIANQIDUI": "Seven Shifted Pairs",
    "SHISANYAO": "Thirteen Orphans",
    "QINGYAOJIU": "All Terminals",
    "XIAOSIXI": "Little Four Winds",
    "XIAOSANYUAN": "Little Three Dragons",
    "ZIYISE": "All Honors",
    "SIANKE": "Four Concealed Pungs",
    "YISESHUANGLONGHUI": "Pure Terminal Chows",
    "YISESITONGSHUN": "Quadruple Chow",
    "YISESIJIEGAO": "Four Pure Shifted Pungs",
    "YISESIBUGAO": "Four Pure Shifted Chows",
    "SANGANG": "Three Kongs",
    "HUNYAOJIU": "All Terminals and Honors",
    "QIDUI": "Seven Pairs",
    "QIXINGBUKAO": "Greater Honors and Knitted Tiles",
    "QUANSHUANGKE": "All Even Pungs",
    "QINGYISE": "Full Flush",
    "YISESANTONGSHUN": "Pure Triple Chow",
    "YISESANJIEGAO": "Pure Shifted Pungs",
    "QUANDA": "Upper Tiles",
    "QUANZHONG": "Middle Tiles",
    "QUANXIAO": "Lower Tiles",
    "QINGLONG": "Pure Straight",
    "SANSESHUANGLONGHUI": "Three-Suited Terminal Chows",
    "YISESANBUGAO": "Pure Shifted Chows",
    "QUANDAIWU": "All Fives",
    "SANTONGKE": "Triple Pung",
    "SANANKE": "Three Concealed Pungs",
    "QUANBUKAO": "Lesser Honors and Knitted Tiles",
    "ZUHELONG": "Knitted Straight",
    "DAYUWU": "Upper Five",
    "XIAOYUWU": "Lower Five",
    "SANFENGKE": "Big Three Winds",
    "HUALONG": "Mixed Straight",
    "TUIBUDAO": "Reversible Tiles",
    "SANSESANTONGSHUN": "Mixed Triple Chow",
    "SANSESANJIEGAO": "Mixed Shifted Pungs",
    "WUFANHU": "Chicken Hand",
    "MIAOSHOUHUICHUN": "Last Tile Draw",
    "HAIDILAOYUE": "Last Tile Claim",
    "GANGSHANGKAIHUA": "Out with Replacement Tile",
    "QIANGGANGHU": "Robbing the Kong",
    "PENGPENGHU": "All Pungs",
    "HUNYISE": "Half Flush",
    "SANSESANBUGAO": "Mixed Shifted Chows",
    "WUMENQI": "All Types",
    "QUANQIUREN": "Melded Hand",
    "SHUANGANGANG": "Two Concealed Kongs",
    "SHUANGJIANKE": "Two Dragons Pungs",
    "QUANDAIYAO": "Outside Hand",
    "BUQIUREN": "Fully Concealed Hand",
    "SHUANGMINGGANG": "Two Melded Kongs",
    "HUJUEZHANG": "Last Tile",
    "JIANKE": "Dragon Pung",
    "QUANFENGKE": "Prevalent Wind",
    "MENFENGKE": "Seat Wind",
    "MENQIANQING": "Concealed Hand",
    "PINGHU": "All Chows",
    "SIGUIYI": "Tile Hog",
    "SHUANGTONGKE": "Double Pung",
    "SHUANGANKE": "Two Concealed Pungs",
    "ANGANG": "Concealed Kong",
    "DUANYAO": "All Simples",
    "YIBANGAO": "Pure Double Chow",
    "XIXIANGFENG": "Mixed Double Chow",
    "LIANLIU": "Short Straight",
    "LAOSHAOFU": "Two Terminal Chows",
    "YAOJIUKE": "Pung of Terminals or Honors",
    "MINGGANG": "Melded Kong",
    "QUEYIMEN": "One Voided Suit",
    "WUZI": "No Honors",
    "BIANZHANG": "Edge Wait",
    "KANZHANG": "Closed Wait",
    "DANDIAOJIANG": "Single Wait",
    "ZIMO": "Self-Drawn",
    "HUAPAI": "Flower Tiles",
}


def tile_kind(code: str) -> int:
    if code in HONOR_KIND:
        return HONOR_KIND[code]
    return SUIT_BASE[code[1]] + int(code[0]) - 1


def parse_tiles(notation: str) -> tuple[list[str], list[dict[str, Any]]]:
    concealed: list[int] = []
    melds: list[dict[str, Any]] = []
    index = 0
    while index < len(notation):
        if notation[index] == "[":
            end = notation.index("]", index + 1)
            body = notation[index + 1 : end]
            index = end + 1
            value, open_meld = body.split(",", 1) if "," in body else (body, "")
            kinds = (
                [tile_kind(rank + value[-1]) for rank in value[:-1]]
                if value[-1] in SUIT_BASE
                else [tile_kind(tile) for tile in value]
            )
            if len(kinds) == 3 and len(set(kinds)) == 1:
                melds.append({"kind": "pung", "tile": KIND_CODES[kinds[0]], "concealed": False})
            elif len(kinds) == 3 and kinds[0] + 1 == kinds[1] and kinds[1] + 1 == kinds[2]:
                melds.append({"kind": "chow", "tile": KIND_CODES[kinds[1]], "concealed": False})
            elif len(kinds) == 4:
                melds.append(
                    {
                        "kind": "kong",
                        "tile": KIND_CODES[kinds[0]],
                        "concealed": not bool(open_meld),
                    }
                )
            else:
                raise ValueError(f"unsupported meld notation: {body}")
        elif notation[index].isdigit():
            end = index
            while end < len(notation) and notation[end].isdigit():
                end += 1
            suit = notation[end]
            concealed.extend(tile_kind(rank + suit) for rank in notation[index:end])
            index = end + 1
        else:
            concealed.append(tile_kind(notation[index]))
            index += 1
    return [KIND_CODES[kind] for kind in concealed], melds


def parse_fixture(notation: str) -> dict[str, Any]:
    parts = notation.replace(" ", "").split("|")
    concealed, melds = parse_tiles(parts[0])
    winning = concealed.pop()
    status = parts[1] if len(parts) > 1 and parts[1] else "EE0000"
    winds = {"E": "F1", "S": "F2", "W": "F3", "N": "F4"}
    method = "self-draw" if status[2] == "1" else "discard"
    flowers = 0
    if len(parts) > 2 and parts[2]:
        flowers = int(parts[2]) if len(parts[2]) == 1 and parts[2].isdigit() else len(parts[2])
    return {
        "concealed": concealed,
        "melds": melds,
        "winning": winning,
        "context": {
            "seat_wind": winds[status[1]],
            "round_wind": winds[status[0]],
            "method": method,
            "flowers": flowers,
            "last_of_kind": status[3] == "1",
            "last_tile": status[4] == "1",
            "after_kong": status[5] == "1" and method == "self-draw",
            "robbing_kong": status[5] == "1" and method == "discard",
        },
    }


def load_gold() -> list[tuple[str, dict[str, Any]]]:
    cases = []
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            fan_code, fixture = line.split("\t")[:2]
            cases.append((fan_code, parse_fixture(fixture)))
    return cases


GOLD_CASES = load_gold()


def score(engine: MahjongEngine, case: dict[str, Any]) -> dict[str, Any]:
    return engine._call({"op": "score", **case})["evaluation"]


def test_gold_corpus_is_complete_and_unique() -> None:
    assert len(GOLD_CASES) == 81
    assert {fan_code for fan_code, _ in GOLD_CASES} == set(FAN_NAMES)


@pytest.mark.parametrize(("fan_code", "case"), GOLD_CASES, ids=[code for code, _ in GOLD_CASES])
def test_green_book_fan_positive_fixture(fan_code: str, case: dict[str, Any]) -> None:
    with MahjongEngine() as engine:
        evaluation = score(engine, case)
    names = {award["name"] for award in evaluation["awards"]}
    assert FAN_NAMES[fan_code] in names


def test_double_chows_combine_with_their_parent_patterns() -> None:
    cases = dict(GOLD_CASES)
    with MahjongEngine() as engine:
        pure = score(engine, cases["YIBANGAO"])
        mixed = score(engine, cases["XIXIANGFENG"])
    pure_names = {award["name"] for award in pure["awards"]}
    mixed_names = {award["name"] for award in mixed["awards"]}
    assert {"Pure Double Chow", "Pure Straight"} <= pure_names
    assert {"Mixed Double Chow", "Mixed Shifted Chows"} <= mixed_names


def test_two_dragons_is_identified_but_does_not_meet_the_threshold() -> None:
    cases = dict(GOLD_CASES)
    with MahjongEngine() as engine:
        evaluation = score(engine, cases["SHUANGJIANKE"])
    assert evaluation["winning"] is False
    assert evaluation["qualifying_fan"] == 7
    assert "Two Dragons Pungs" in {award["name"] for award in evaluation["awards"]}
