let () =
  let call =
    Js_of_ocaml.Js.wrap_callback (fun request ->
        Js_of_ocaml.Js.string
          (Mahjong_ffi_dispatch.dispatch (Js_of_ocaml.Js.to_string request)))
  in
  Js_of_ocaml.Js.Unsafe.set
    (Js_of_ocaml.Js.Unsafe.pure_js_expr "globalThis")
    (Js_of_ocaml.Js.string "mahjongCall")
    call
