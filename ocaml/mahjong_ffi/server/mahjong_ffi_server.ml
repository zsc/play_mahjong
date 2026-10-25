let () =
  try
    while true do
      let request = input_line stdin in
      output_string stdout (Mahjong_ffi_dispatch.dispatch request);
      output_char stdout '\n';
      flush stdout
    done
  with End_of_file -> ()
