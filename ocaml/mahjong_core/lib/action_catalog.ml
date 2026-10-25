let version = 1
let size = 122

let hu = 0
let pass = 1
let expose_flower = 2
let chow_start = 3
let pung = 10
let kong = 11
let discard_start = 12
let concealed_kong_start = 46
let added_kong_start = 80
let discard_flower_start = 114

let is_flower_phase state seat =
  match state.State.phase with
  | State.Awaiting_flower current -> current = seat
  | _ -> false

let id_of_action state seat = function
  | Action.Hu -> hu
  | Action.Pass -> pass
  | Action.Expose_flower -> expose_flower
  | Action.Chow start -> chow_start + start - 1
  | Action.Pung -> pung
  | Action.Kong -> kong
  | Action.Discard instance ->
      let kind = Tile.instance_kind instance in
      if is_flower_phase state seat && Tile.is_flower kind then
        discard_flower_start + kind - Tile.flower_kind_start
      else discard_start + kind
  | Action.Concealed_kong kind -> concealed_kong_start + kind
  | Action.Added_kong kind -> added_kong_start + kind

let key id =
  if id = hu then "hu"
  else if id = pass then "pass"
  else if id = expose_flower then "expose-flower"
  else if id >= chow_start && id <= chow_start + 6 then
    "chow-" ^ string_of_int (id - chow_start + 1)
  else if id = pung then "pung"
  else if id = kong then "kong"
  else if id >= discard_start && id < discard_start + Tile.standard_kind_count then
    "discard-" ^ Tile.code (id - discard_start)
  else if id >= concealed_kong_start && id < concealed_kong_start + Tile.standard_kind_count then
    "concealed-kong-" ^ Tile.code (id - concealed_kong_start)
  else if id >= added_kong_start && id < added_kong_start + Tile.standard_kind_count then
    "added-kong-" ^ Tile.code (id - added_kong_start)
  else if id >= discard_flower_start && id < discard_flower_start + 8 then
    "discard-flower-" ^ Tile.code (Tile.flower_kind_start + id - discard_flower_start)
  else invalid_arg "action id out of range"

let legal (state : State.t) seat =
  let ids =
    Engine.legal_actions state seat
    |> List.map (fun action -> id_of_action state seat action)
    |> List.sort_uniq compare
  in
  ids

let action_of_id state seat id =
  Engine.legal_actions state seat
  |> List.find_opt (fun action -> id_of_action state seat action = id)

