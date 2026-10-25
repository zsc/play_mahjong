#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
switch=${OPAM_SWITCH:-mahjong}

eval "$(opam env --switch="$switch" --set-switch)"
case "$(uname -s)" in
  Linux)
    exec "$root/scripts/build_ffi_linux.sh"
    ;;
  *)
    cd "$root/ocaml"
    dune build @ffi
    printf '%s\n' "$root/ocaml/_build/default/mahjong_ffi/mahjong_ffi.so"
    ;;
esac
