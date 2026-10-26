from __future__ import annotations

import ctypes
import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Self

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIBRARY = ROOT / "ocaml" / "_build" / "default" / "mahjong_ffi" / "mahjong_ffi.so"
DEFAULT_SERVER = (
    ROOT
    / "ocaml"
    / "_build"
    / "default"
    / "mahjong_ffi"
    / "server"
    / "mahjong_ffi_server.exe"
)


class EngineError(RuntimeError):
    pass


class MahjongEngine:
    """Thin, process-local ctypes client for the OCaml C ABI.

    The OCaml embedding is initialized with a pooled runtime. Calls are serialized
    because one Python process must not enter it concurrently from multiple threads.
    Use separate Python processes for parallel rollout workers.
    """

    _library_lock = threading.Lock()
    _library: ctypes.CDLL | None = None

    @classmethod
    def _load_library(cls) -> ctypes.CDLL:
        with cls._library_lock:
            if cls._library is not None:
                return cls._library
            path = Path(os.environ.get("MAHJONG_FFI_LIBRARY", DEFAULT_LIBRARY))
            if not path.exists():
                raise EngineError(
                    f"OCaml FFI library not found at {path}. Run scripts/build_ffi.sh first."
                )
            library = ctypes.CDLL(str(path))
            library.mahjong_ffi_call.argtypes = [ctypes.c_char_p]
            library.mahjong_ffi_call.restype = ctypes.c_void_p
            library.mahjong_ffi_free.argtypes = [ctypes.c_void_p]
            library.mahjong_ffi_free.restype = None
            library.mahjong_ffi_abi_version.restype = ctypes.c_int
            if library.mahjong_ffi_abi_version() != 1:
                raise EngineError("unsupported OCaml FFI ABI version")
            cls._library = library
            return library

    def __init__(self) -> None:
        server = os.environ.get("MAHJONG_FFI_SERVER")
        self._server: subprocess.Popen[str] | None = None
        self._library: ctypes.CDLL | None = None
        if server is not None:
            path = Path(server)
            if not path.exists():
                raise EngineError(f"OCaml FFI server not found at {path}")
            self._server = subprocess.Popen(
                [str(path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        else:
            self._library = self._load_library()
        self._call_lock = threading.Lock()
        self._handles: set[int] = set()

    def _call(self, request: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode()
        with self._call_lock:
            if self._server is not None:
                assert self._server.stdin is not None
                assert self._server.stdout is not None
                self._server.stdin.write(encoded.decode() + "\n")
                self._server.stdin.flush()
                line = self._server.stdout.readline()
                if not line:
                    stderr = ""
                    if self._server.stderr is not None:
                        stderr = self._server.stderr.read()
                    raise EngineError(f"OCaml FFI server stopped unexpectedly: {stderr.strip()}")
                response = json.loads(line)
            else:
                assert self._library is not None
                pointer = self._library.mahjong_ffi_call(encoded)
                if not pointer:
                    raise EngineError("OCaml FFI returned a null response")
                try:
                    response = json.loads(ctypes.string_at(pointer).decode())
                finally:
                    self._library.mahjong_ffi_free(pointer)
        if not response.get("ok", False):
            raise EngineError(response.get("error", "unknown OCaml engine error"))
        return response

    def new_game(self, seed: int, round_wind: str = "F1") -> int:
        handle = int(self._call({"op": "new", "seed": seed, "round_wind": round_wind})["handle"])
        self._handles.add(handle)
        return handle

    def actor(self, game: int) -> int | None:
        value = self._call({"op": "actor", "game": game})["actor"]
        return None if value is None else int(value)

    def observe(self, game: int, seat: int) -> tuple[dict[str, Any], int | None]:
        response = self._call({"op": "observe", "game": game, "seat": seat})
        actor = response["actor"]
        return response["observation"], None if actor is None else int(actor)

    def heuristic_action(self, game: int, seat: int, variant: str | None = None) -> int:
        request = {"op": "heuristic", "game": game, "seat": seat}
        if variant is not None:
            request["variant"] = variant
        return int(self._call(request)["action_id"])

    def legal_actions(self, game: int, seat: int) -> list[int]:
        observation, _ = self.observe(game, seat)
        return [int(value) for value in observation["legal_action_ids"]]

    def step(self, game: int, seat: int, action_id: int) -> dict[str, Any]:
        return self._call({"op": "step", "game": game, "seat": seat, "action_id": action_id})

    def validate(self, game: int) -> None:
        self._call({"op": "validate", "game": game})

    def advance_batch(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Atomically advance games to model discard decisions or terminal outcomes."""
        return self._call({"op": "advance_batch", "requests": requests})["results"]

    def teacher_chunk(self, game: int, variant: str, max_steps: int, count: int = 64) -> dict:
        return self._call({"op": "teacher_chunk", "game": game, "variant": variant,
                           "max_steps": max_steps, "count": count})

    def decision_batch(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Full legal choices for any seat; skip only windows with one legal action."""
        return self._call({"op": "decision_batch", "requests": requests})["results"]

    def close(self, game: int) -> None:
        if game in self._handles:
            self._call({"op": "close", "game": game})
            self._handles.remove(game)

    def close_all(self) -> None:
        for game in tuple(self._handles):
            self.close(game)

    def close_backend(self) -> None:
        if self._server is None:
            return
        if self._server.poll() is None:
            self._server.terminate()
            try:
                self._server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server.kill()
                self._server.wait(timeout=5)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close_all()
        self.close_backend()
