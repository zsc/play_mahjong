open Mahjong_core

let games : (int, State.t) Hashtbl.t = Hashtbl.create 16
let next_handle = ref 1

let current handle =
  match Hashtbl.find_opt games handle with
  | Some state -> state
  | None -> invalid_arg ("unknown game handle: " ^ string_of_int handle)

let member name json = Yojson.Safe.Util.member name json
let int_member name json = Yojson.Safe.Util.to_int (member name json)

let ok fields = `Assoc (("ok", `Bool true) :: fields)
let error message = `Assoc [ ("ok", `Bool false); ("error", `String message) ]

let actor_json state = match Observation.actor state with Some seat -> `Int seat | None -> `Null

let bool_member ?(default = false) name json =
  match Yojson.Safe.Util.member name json with
  | `Null -> default
  | value -> Yojson.Safe.Util.to_bool value

let codes name json =
  Yojson.Safe.Util.to_list (member name json)
  |> List.map (fun value -> Yojson.Safe.Util.to_string value |> Tile.of_string)

let meld_json json =
  let kind = Yojson.Safe.Util.to_string (member "kind" json) in
  let tile = Yojson.Safe.Util.to_string (member "tile" json) |> Tile.of_string in
  let concealed = bool_member "concealed" json in
  match kind with
  | "chow" -> Meld.chow ~middle:tile ~instances:[] ~origin:Meld.Concealed
  | "pung" -> Meld.pung ~tile ~instances:[] ~origin:Meld.Concealed
  | "kong" -> Meld.kong ~tile ~instances:[] ~concealed ~origin:Meld.Concealed
  | _ -> invalid_arg ("unknown meld kind: " ^ kind)

let evaluation_json (evaluation : Fan.evaluation) =
  let awards =
    List.map
      (fun (award : Fan.award) ->
        `Assoc
          [
            ("name", `String (Fan.name award.Fan.fan));
            ("points", `Int (Fan.points award.fan));
          ])
      evaluation.awards
  in
  `Assoc
    [
      ("winning", `Bool evaluation.winning);
      ("qualifying_fan", `Int evaluation.qualifying_fan);
      ("flower_fan", `Int evaluation.flower_fan);
      ("total_fan", `Int evaluation.total_fan);
      ("awards", `List awards);
    ]

let handle_request request =
  let json = Yojson.Safe.from_string request in
  match Yojson.Safe.Util.member "op" json |> Yojson.Safe.Util.to_string with
  | "new" ->
      let seed = int_member "seed" json in
      let round_wind = Yojson.Safe.Util.to_string (member "round_wind" json) |> Tile.of_string in
      let handle = !next_handle in
      incr next_handle;
      Hashtbl.add games handle (State.initial seed round_wind);
      ok [ ("handle", `Int handle) ]
  | "observe" ->
      let handle = int_member "game" json in
      let state = current handle in
      let seat = int_member "seat" json in
      ok [ ("observation", Observation_json.of_state state seat); ("actor", actor_json state) ]
  | "actor" ->
      let state = current (int_member "game" json) in
      ok [ ("actor", actor_json state); ("revision", `Int state.revision) ]
  | "step" ->
      let handle = int_member "game" json in
      let state = current handle in
      let seat = int_member "seat" json in
      let action_id = int_member "action_id" json in
      (match Action_catalog.action_of_id state seat action_id with
       | None -> error ("action is not legal: " ^ string_of_int action_id)
       | Some action -> (
           match Engine.step state seat action with
           | Error message -> error message
           | Ok next ->
               Hashtbl.replace games handle next;
               ok
                 [
                   ("revision", `Int next.revision);
                   ("actor", actor_json next);
                   ("ended", `Bool (match next.phase with State.Ended _ -> true | _ -> false));
                 ]))
  | "heuristic" ->
      let state = current (int_member "game" json) in
      let seat = int_member "seat" json in
      let variant =
        match Yojson.Safe.Util.member "variant" json with
        | `Null -> "default"
        | value -> Yojson.Safe.Util.to_string value
      in
      (match Heuristic.choose_action_id_with_variant state seat variant with
       | None -> error "heuristic has no action for this seat"
       | Some action_id -> ok [ ("action_id", `Int action_id) ])
  | "validate" ->
      let state = current (int_member "game" json) in
      (match State.validate state with
       | Ok () -> ok []
       | Error message -> error message)
  | "score" ->
      let concealed = Tile_counts.of_kinds (codes "concealed" json) in
      let melds =
        Yojson.Safe.Util.to_list (member "melds" json) |> List.map meld_json
      in
      let winning = Yojson.Safe.Util.to_string (member "winning" json) |> Tile.of_string in
      let context = member "context" json in
      let method_ =
        match Yojson.Safe.Util.to_string (member "method" context) with
        | "self-draw" -> Fan.Self_draw
        | "discard" -> Fan.Discard
        | value -> invalid_arg ("unknown win method: " ^ value)
      in
      let flags =
        {
          Fan.after_kong = bool_member "after_kong" context;
          last_tile = bool_member "last_tile" context;
          robbing_kong = bool_member "robbing_kong" context;
          last_of_kind = bool_member "last_of_kind" context;
        }
      in
      let context =
        {
          Fan.seat_wind =
            Yojson.Safe.Util.to_string (member "seat_wind" context) |> Tile.of_string;
          round_wind =
            Yojson.Safe.Util.to_string (member "round_wind" context) |> Tile.of_string;
          win_method = method_;
          flowers = int_member "flowers" context;
          flags;
        }
      in
      let evaluation =
        Fan.evaluate ~concealed_before:concealed ~melds ~winning ~context
      in
      ok [ ("evaluation", evaluation_json evaluation) ]
  | "close" ->
      let handle = int_member "game" json in
      Hashtbl.remove games handle;
      ok []
  | operation -> error ("unknown operation: " ^ operation)

let dispatch request =
  try handle_request request |> Yojson.Safe.to_string
  with
  | Yojson.Json_error message -> error ("invalid json: " ^ message) |> Yojson.Safe.to_string
  | Invalid_argument message -> error message |> Yojson.Safe.to_string
  | Failure message -> error message |> Yojson.Safe.to_string
  | exn -> error (Printexc.to_string exn) |> Yojson.Safe.to_string
