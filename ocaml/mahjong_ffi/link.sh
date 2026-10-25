#!/bin/sh
set -eu

ocaml_where="$1"
output="$2"
object="$3"
directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

case "$(uname -s)" in
  Darwin)
    exec cc -dynamiclib -O2 -I "$ocaml_where" -o "$output" "$directory/wrapper.c" "$object" \
      "$ocaml_where/libasmrun.a" "$ocaml_where/libthreadsnat.a"
    ;;
  Linux)
    exec cc -shared -fPIC -O2 -I "$ocaml_where" -o "$output" "$directory/wrapper.c" "$object" \
      "$ocaml_where/libasmrun_pic.a" "$ocaml_where/libthreadsnat.a" -ldl -lpthread -lm
    ;;
  *)
    echo "unsupported platform for the OCaml Python FFI" >&2
    exit 1
    ;;
esac

