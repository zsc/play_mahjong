#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build="$root/ocaml/_build/default"
output="$build/mahjong_ffi/mahjong_ffi.so"
tmp=${TMPDIR:-/tmp}/mahjong-ffi-linux-$$

cleanup() {
  rm -rf "$tmp"
}
trap cleanup EXIT INT TERM
mkdir -p "$tmp"

cd "$root/ocaml"
dune build \
  mahjong_core/lib/mahjong_core.cmxa \
  mahjong_ffi/dispatch/mahjong_ffi_dispatch.cmxa \
  mahjong_ffi/.mahjong_ffi_entry.eobjs/native/dune__exe__Mahjong_ffi_entry.cmx

ocamlfind ocamlopt -package yojson -linkpkg -output-obj -o "$tmp/entry.o" \
  -I "$build/mahjong_core/lib/.mahjong_core.objs/byte" \
  -I "$build/mahjong_core/lib/.mahjong_core.objs/native" \
  -I "$build/mahjong_ffi/dispatch/.mahjong_ffi_dispatch.objs/byte" \
  -I "$build/mahjong_ffi/dispatch/.mahjong_ffi_dispatch.objs/native" \
  "$build/mahjong_core/lib/mahjong_core.cmxa" \
  "$build/mahjong_ffi/dispatch/mahjong_ffi_dispatch.cmxa" \
  "$build/mahjong_ffi/.mahjong_ffi_entry.eobjs/native/dune__exe__Mahjong_ffi_entry.cmx"

ocaml_where=$(ocamlc -where)
cc -shared -fPIC -O2 -I "$ocaml_where" -I "$root/ocaml/mahjong_ffi" \
  -o "$tmp/mahjong_ffi.so" "$root/ocaml/mahjong_ffi/wrapper.c" "$tmp/entry.o" \
  "$ocaml_where/libasmrun_pic.a" "$ocaml_where/libthreadsnat.a" \
  -ldl -lpthread -lm

# Never truncate an inode that an existing rollout worker has mmap'ed.
cp "$tmp/mahjong_ffi.so" "$output.new.$$"
mv -f "$output.new.$$" "$output"

printf 'wrote %s\n' "$output"
