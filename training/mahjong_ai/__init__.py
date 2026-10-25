"""Training-side adapters for the OCaml MCR engine."""

from .actions import ACTION_CATALOG_VERSION, ACTION_COUNT
from .engine import EngineError, MahjongEngine

__all__ = ["ACTION_CATALOG_VERSION", "ACTION_COUNT", "EngineError", "MahjongEngine"]

