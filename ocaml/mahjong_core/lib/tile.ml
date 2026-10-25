type suit = Characters | Bamboo | Dots | Wind | Dragon | Flower

type t = int

let standard_kind_count = 34
let flower_kind_start = 34
let kind_count = 42
let physical_tile_count = 144

let is_standard_kind kind = kind >= 0 && kind < standard_kind_count
let is_flower_kind kind = kind >= flower_kind_start && kind < kind_count

let suit kind =
  if kind < 0 || kind >= kind_count then invalid_arg "tile kind out of range"
  else if kind < 9 then Characters
  else if kind < 18 then Bamboo
  else if kind < 27 then Dots
  else if kind < 31 then Wind
  else if kind < 34 then Dragon
  else Flower

let rank kind =
  if kind < 0 || kind >= kind_count then invalid_arg "tile kind out of range"
  else if kind < 27 then (kind mod 9) + 1
  else 0

let is_numbered kind = kind >= 0 && kind < 27
let is_honor kind = kind >= 27 && kind < 34
let is_wind kind = kind >= 27 && kind < 31
let is_dragon kind = kind >= 31 && kind < 34
let is_flower kind = is_flower_kind kind

let is_terminal kind =
  is_numbered kind && let value = rank kind in value = 1 || value = 9

let is_terminal_or_honor kind = is_terminal kind || is_honor kind
let is_green kind = kind = 10 || kind = 11 || kind = 12 || kind = 14 || kind = 16 || kind = 32
let is_reversible kind = is_numbered kind && let value = rank kind in value >= 2 && value <= 8

let code kind =
  let suit_code, offset =
    if kind < 9 then ("W", kind)
    else if kind < 18 then ("T", kind - 9)
    else if kind < 27 then ("B", kind - 18)
    else ("", kind)
  in
  if kind < 27 then suit_code ^ string_of_int (offset + 1)
  else
    match kind with
    | 27 -> "F1"
    | 28 -> "F2"
    | 29 -> "F3"
    | 30 -> "F4"
    | 31 -> "J3"
    | 32 -> "J2"
    | 33 -> "J1"
    | 34 -> "a"
    | 35 -> "b"
    | 36 -> "c"
    | 37 -> "d"
    | 38 -> "e"
    | 39 -> "f"
    | 40 -> "g"
    | 41 -> "h"
    | _ -> invalid_arg "tile kind out of range"

let of_string raw =
  let value = String.trim raw in
  let upper = String.uppercase_ascii value in
  let parse_numbered expected base =
    if String.length value = 2 && value.[0] = expected then
      let rank = Char.code value.[1] - Char.code '0' in
      if rank >= 1 && rank <= 9 then Some (base + rank - 1) else None
    else None
  in
  match value with
  | "a" -> 34
  | "b" -> 35
  | "c" -> 36
  | "d" -> 37
  | "e" -> 38
  | "f" -> 39
  | "g" -> 40
  | "h" -> 41
  | _ -> (
      match upper with
      | "F1" | "E" -> 27
      | "F2" | "S" -> 28
      | "F3" | "W" -> 29
      | "F4" | "N" -> 30
      | "J3" | "C" -> 31
      | "J2" -> 32
      | "J1" -> 33
      | _ -> (
          match parse_numbered 'W' 0 with
          | Some kind -> kind
          | None -> (
              match parse_numbered 'T' 9 with
              | Some kind -> kind
              | None -> (
                  match parse_numbered 'B' 18 with
                  | Some kind -> kind
                  | None -> invalid_arg ("unsupported tile code: " ^ raw)))))

let instance_kind instance =
  if instance < 0 || instance >= physical_tile_count then invalid_arg "tile instance out of range"
  else if instance < 136 then instance / 4
  else flower_kind_start + instance - 136

let instance_code instance = code (instance_kind instance)

let instances_of_kind kind =
  if is_standard_kind kind then List.init 4 (fun copy -> (kind * 4) + copy)
  else if is_flower_kind kind then [ 136 + kind - flower_kind_start ]
  else invalid_arg "tile kind out of range"

let all_standard_kinds = List.init standard_kind_count Fun.id
