#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
eval "$(opam env --switch="${OPAM_SWITCH:-mahjong}" --set-switch)"
cd "$root"
mkdir -p web/public/runtime
dune build --root ocaml mahjong_ffi/wasm/mahjong_wasm.bc
# CPS avoids requiring JSPI or experimental stack switching in the browser.
wasm_of_ocaml compile --effects=cps --opt=3 --pretty \
  -o web/public/runtime/engine.js ocaml/_build/default/mahjong_ffi/wasm/mahjong_wasm.bc
