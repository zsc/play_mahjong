type t =
  | Discard of int
  | Expose_flower
  | Hu
  | Pass
  | Chow of int
  | Pung
  | Kong
  | Concealed_kong of Tile.t
  | Added_kong of Tile.t

let equal left right =
  match left, right with
  | Discard a, Discard b -> a = b
  | Expose_flower, Expose_flower | Hu, Hu | Pass, Pass | Pung, Pung | Kong, Kong -> true
  | Chow a, Chow b -> a = b
  | Concealed_kong a, Concealed_kong b | Added_kong a, Added_kong b -> a = b
  | _ -> false

let describe = function
  | Discard instance -> "discard " ^ Tile.instance_code instance
  | Expose_flower -> "expose-flower"
  | Hu -> "hu"
  | Pass -> "pass"
  | Chow start -> "chow-" ^ string_of_int start
  | Pung -> "pung"
  | Kong -> "kong"
  | Concealed_kong kind -> "concealed-kong-" ^ Tile.code kind
  | Added_kong kind -> "added-kong-" ^ Tile.code kind

let is_claim = function Hu | Chow _ | Pung | Kong -> true | _ -> false

