let ints values = `List (List.map (fun value -> `Int value) values)
let codes kinds = `List (List.map (fun kind -> `String (Tile.code kind)) kinds)

let award_json (award : Fan.award) =
  `Assoc
    [
      ("fan", `String (Fan.name award.Fan.fan));
      ("points", `Int (Fan.points award.fan));
      ("count", `Int award.count);
    ]

let outcome_json = function
  | State.Exhaustive_draw -> `Assoc [ ("kind", `String "exhaustive-draw") ]
  | State.Win win ->
      `Assoc
        [
          ("kind", `String "win");
          ("winner", `Int win.winner);
          ("discarder", (match win.discarder with Some seat -> `Int seat | None -> `Null));
          ("winning_tile", `String (Tile.code (Tile.instance_kind win.winning_tile)));
          ("qualifying_fan", `Int win.evaluation.qualifying_fan);
          ("flower_fan", `Int win.evaluation.flower_fan);
          ("total_fan", `Int win.evaluation.total_fan);
          ("awards", `List (List.map award_json win.evaluation.awards));
          ("deltas", ints (Array.to_list win.deltas));
        ]

let phase_json = function
  | Observation.Awaiting_discard seat ->
      `Assoc [ ("kind", `String "discard"); ("seat", `Int seat) ]
  | Observation.Awaiting_flower seat ->
      `Assoc [ ("kind", `String "flower"); ("seat", `Int seat) ]
  | Observation.Awaiting_response { discarder; discard_kind } ->
      `Assoc
        [
          ("kind", `String "response");
          ("discarder", `Int discarder);
          ("tile", `String (Tile.code discard_kind));
        ]
  | Observation.Ended outcome ->
      `Assoc [ ("kind", `String "ended"); ("outcome", outcome_json outcome) ]

let meld_json meld =
  `Assoc
    [
      ("kind", `String (match meld.Observation.kind with Meld.Chow -> "chow" | Meld.Pung -> "pung" | Meld.Kong -> "kong"));
      ("tile", match meld.tile with Some tile -> `String (Tile.code tile) | None -> `Null);
      ("concealed", `Bool meld.concealed);
      ("claimed_from", match meld.claimed_from with Some seat -> `Int seat | None -> `Null);
      ("revealed", `Bool (meld.tile <> None));
    ]

let legal_action_json id =
  `Assoc [ ("id", `Int id); ("key", `String (Action_catalog.key id)) ]

let of_state ?choices state seat =
  let view = Observation.create state seat in
  let legal = Action_catalog.legal state seat in
  let hint_shanten, hint_ukeire, hint_qualifying_waits, hint_qualifying_value =
    match state.State.phase with
    | State.Awaiting_discard _ -> Heuristic.discard_hints ?choices state seat
    | _ ->
        ( Array.make Tile.standard_kind_count (-1),
          Array.make Tile.standard_kind_count 0,
          Array.make Tile.standard_kind_count 0,
          Array.make Tile.standard_kind_count 0 )
  in
  `Assoc
    [
      ("observation_version", `Int Observation.version);
      ("action_catalog_version", `Int Action_catalog.version);
      ("action_count", `Int Action_catalog.size);
      ("seat", `Int view.seat);
      ("seat_wind", `String (Tile.code view.seat_wind));
      ("round_wind", `String (Tile.code view.round_wind));
      ("hand", ints (Array.to_list view.concealed_counts));
      ("drawn", match view.drawn_kind with Some kind -> `String (Tile.code kind) | None -> `Null);
      ("flowers", codes view.own_flowers);
      ("flower_counts", ints (Array.to_list view.flower_counts));
      ("melds",
        `List
          (Array.to_list
             (Array.map (fun melds -> `List (Array.to_list (Array.map meld_json melds))) view.all_melds)));
      ("rivers",
        `List
          (Array.to_list
             (Array.map (fun river -> codes (List.map Tile.instance_kind river)) view.rivers)));
      ("known_counts", ints (Array.to_list view.known_counts));
      ("wall_remaining", `Int view.wall_remaining);
      ("discard_hints",
        `Assoc
          [
            ("shanten", ints (Array.to_list hint_shanten));
            ("ukeire", ints (Array.to_list hint_ukeire));
            ("qualifying_waits", ints (Array.to_list hint_qualifying_waits));
            ("qualifying_value", ints (Array.to_list hint_qualifying_value));
          ]);
      ("revision", `Int view.revision);
      ("phase", phase_json view.phase);
      ("legal_action_ids", ints legal);
      ("legal_actions", `List (List.map legal_action_json legal));
    ]

let to_string state seat = of_state state seat |> Yojson.Safe.to_string
