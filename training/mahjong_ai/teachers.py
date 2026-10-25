from __future__ import annotations

HEURISTIC_VARIANTS = (
    "default",
    "closed",
    "closed-kong",
    "tenpai-only",
    "qualified-tenpai",
    "qualified-best",
    "no-chow",
)

DEFAULT_HEURISTIC_VARIANT = "default"


def resolve_scaffold_variant(explicit: str | None, checkpoint: dict) -> str:
    variant = (
        explicit
        or checkpoint.get("scaffold_variant")
        or checkpoint.get("teacher_variant")
        or DEFAULT_HEURISTIC_VARIANT
    )
    if variant not in HEURISTIC_VARIANTS:
        raise ValueError(f"unsupported heuristic scaffold variant: {variant}")
    return str(variant)
