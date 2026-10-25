from __future__ import annotations

from typing import Any

import numpy as np

from .actions import ACTION_COUNT

OBSERVATION_VERSION = 1
FEATURE_ENCODING_VERSION = 6
FEATURE_SIZE = 771
STANDARD_KINDS = 34
FLOWER_KINDS = 8
SEATS = 4

WIND_CODES = ("F1", "F2", "F3", "F4")
PHASE_CODES = ("discard", "flower", "response", "ended")
HINT_SHANTEN_OFFSET = 635
HINT_UKEIRE_OFFSET = 669
HINT_QUALIFYING_WAITS_OFFSET = 703
HINT_QUALIFYING_VALUE_OFFSET = 737
SUIT_FEATURE_BLOCKS = (
    0,
    34,
    68,
    102,
    *range(176, 176 + 4 * 34, 34),
    *range(312, 312 + 4 * 34, 34),
    *range(448, 448 + 4 * 34, 34),
    593,
    HINT_SHANTEN_OFFSET,
    HINT_UKEIRE_OFFSET,
    HINT_QUALIFYING_WAITS_OFFSET,
    HINT_QUALIFYING_VALUE_OFFSET,
)


def _one_hot(index: int, size: int) -> np.ndarray:
    value = np.zeros(size, dtype=np.float32)
    if 0 <= index < size:
        value[index] = 1.0
    return value


def encode_observation(observation: dict[str, Any]) -> np.ndarray:
    if int(observation["observation_version"]) != OBSERVATION_VERSION:
        raise ValueError("unsupported observation version")
    hand = np.asarray(observation["hand"], dtype=np.float32) / 4.0
    known = np.asarray(observation["known_counts"], dtype=np.float32) / 4.0
    unseen = np.clip(1.0 - known, 0.0, 1.0)

    drawn = np.zeros(STANDARD_KINDS, dtype=np.float32)
    drawn_flower = np.zeros(FLOWER_KINDS, dtype=np.float32)
    drawn_code = observation.get("drawn")
    if drawn_code is not None:
        if drawn_code in "abcdefgh":
            drawn_flower[flower_index(drawn_code)] = 1.0
        else:
            drawn[standard_index(drawn_code)] = 1.0

    own_flowers = np.zeros(FLOWER_KINDS, dtype=np.float32)
    for code in observation.get("flowers", []):
        own_flowers[flower_index(code)] = 1.0

    meld_features = np.zeros((SEATS, 6), dtype=np.float32)
    meld_tiles = np.zeros((SEATS, STANDARD_KINDS), dtype=np.float32)
    for seat, melds in enumerate(observation.get("melds", [])):
        for meld in melds:
            kind_offset = {"chow": 0, "pung": 2, "kong": 4}[meld["kind"]]
            meld_features[seat, kind_offset + (1 if meld["concealed"] else 0)] += 1.0
            tile = meld.get("tile")
            if tile is not None:
                middle = standard_index(tile)
                if meld["kind"] == "chow":
                    meld_tiles[seat, middle - 1 : middle + 2] += 1.0
                else:
                    meld_tiles[seat, middle] += 3.0 if meld["kind"] == "pung" else 4.0
    meld_features = np.clip(meld_features.reshape(-1) / 4.0, 0.0, 1.0)
    meld_tiles = np.clip(meld_tiles.reshape(-1) / 4.0, 0.0, 1.0)

    river_counts = np.zeros((SEATS, STANDARD_KINDS), dtype=np.float32)
    river_last = np.zeros((SEATS, STANDARD_KINDS), dtype=np.float32)
    for seat, river in enumerate(observation.get("rivers", [])):
        for code in river:
            if code in "abcdefgh":
                continue
            index = standard_index(code)
            river_counts[seat, index] += 1.0
        last_standard = next((code for code in reversed(river) if code not in "abcdefgh"), None)
        if last_standard is not None:
            river_last[seat, standard_index(last_standard)] = 1.0
    river_counts = np.clip(river_counts.reshape(-1) / 4.0, 0.0, 1.0)
    river_last = river_last.reshape(-1)

    flower_counts = np.asarray(observation.get("flower_counts", [0, 0, 0, 0]), dtype=np.float32) / 8.0
    wall = np.asarray([float(observation.get("wall_remaining", 0)) / 136.0], dtype=np.float32)

    phase = observation["phase"]
    phase_features = _one_hot(PHASE_CODES.index(phase["kind"]), len(PHASE_CODES))
    if phase["kind"] == "response":
        phase_features = np.concatenate(
            [phase_features, _one_hot(standard_index(phase["tile"]), STANDARD_KINDS)]
        )
    else:
        phase_features = np.concatenate([phase_features, np.zeros(STANDARD_KINDS, dtype=np.float32)])

    seat_wind = _one_hot(WIND_CODES.index(observation["seat_wind"]), 4)
    round_wind = _one_hot(WIND_CODES.index(observation["round_wind"]), 4)
    discard_hints = observation.get("discard_hints", {})
    hint_shanten = np.asarray(discard_hints.get("shanten", [0] * STANDARD_KINDS), dtype=np.float32)
    hint_ukeire = np.asarray(discard_hints.get("ukeire", [0] * STANDARD_KINDS), dtype=np.float32)
    hint_qualifying_waits = np.asarray(
        discard_hints.get("qualifying_waits", [0] * STANDARD_KINDS), dtype=np.float32
    )
    hint_qualifying_value = np.asarray(
        discard_hints.get("qualifying_value", [0] * STANDARD_KINDS), dtype=np.float32
    )
    if any(
        values.shape != (STANDARD_KINDS,)
        for values in (
            hint_shanten,
            hint_ukeire,
            hint_qualifying_waits,
            hint_qualifying_value,
        )
    ):
        raise ValueError("discard hints must contain 34 entries")
    hint_shanten = np.clip(hint_shanten, 0.0, 8.0) / 8.0
    hint_ukeire = np.clip(hint_ukeire, 0.0, 136.0) / 136.0
    hint_qualifying_waits = np.clip(hint_qualifying_waits, 0.0, 136.0) / 136.0
    hint_qualifying_value = np.clip(hint_qualifying_value, 0.0, 20000.0) / 20000.0

    result = np.concatenate(
        [
            hand,
            known,
            unseen,
            drawn,
            own_flowers,
            drawn_flower,
            meld_features,
            meld_tiles,
            river_counts,
            river_last,
            flower_counts,
            wall,
            phase_features,
            seat_wind,
            round_wind,
            hint_shanten,
            hint_ukeire,
            hint_qualifying_waits,
            hint_qualifying_value,
        ]
    ).astype(np.float32)
    if result.shape[0] != FEATURE_SIZE:
        raise AssertionError(f"feature size changed: {result.shape[0]} != {FEATURE_SIZE}")
    return result


def action_mask(observation: dict[str, Any]) -> np.ndarray:
    mask = np.zeros(ACTION_COUNT, dtype=np.bool_)
    legal = observation.get("legal_action_ids", [])
    if not legal:
        raise ValueError("decision observation has an empty legal action set")
    mask[np.asarray(legal, dtype=np.int64)] = True
    return mask


def standard_index(code: str) -> int:
    honor = {"F1": 27, "F2": 28, "F3": 29, "F4": 30, "J3": 31, "J2": 32, "J1": 33}
    if code in honor:
        return honor[code]
    if len(code) != 2 or code[0] not in "WTB" or not code[1].isdigit():
        raise ValueError(f"not a standard tile code: {code}")
    rank = int(code[1])
    if rank < 1 or rank > 9:
        raise ValueError(f"invalid rank in tile code: {code}")
    base = {"W": 0, "T": 9, "B": 18}[code[0]]
    return base + rank - 1


def flower_index(code: str) -> int:
    if code not in "abcdefgh" or len(code) != 1:
        raise ValueError(f"invalid flower tile code: {code}")
    return ord(code) - ord("a")
