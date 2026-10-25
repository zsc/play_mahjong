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

let apply_action state seat action_id =
  match Action_catalog.action_of_id state seat action_id with
  | None -> invalid_arg ("action is not legal: " ^ string_of_int action_id)
  | Some action -> (match Engine.step state seat action with
      | Ok next -> next | Error message -> invalid_arg message)

let teacher state seat variant =
  match Heuristic.choose_action_id_with_variant state seat variant with
  | Some action -> action | None -> invalid_arg "teacher has no action"

let prepared_decision state seat variant =
  let choices = match state.State.phase with
    | State.Awaiting_discard _ -> Some (Heuristic.choices_for_state state seat)
    | _ -> None
  in
  let action = match Heuristic.choose_action_id_with_variant ?choices state seat variant with
    | Some value -> value | None -> invalid_arg "teacher has no action"
  in
  (action, Observation_json.of_state ?choices state seat)

(* Advance through ordinary engine transitions, stopping only at a learned-policy
   decision. No automatic action is substituted for a submitted illegal action. *)
let advance json =
  let handle = int_member "game" json in
  let model_seat = int_member "model_seat" json in
  if model_seat < 0 || model_seat > 3 then invalid_arg "model_seat must be in 0..3";
  let limit = int_member "max_steps" json in
  let scaffold = member "scaffold_variant" json |> Yojson.Safe.Util.to_string in
  let opponent = member "opponent_variant" json |> Yojson.Safe.Util.to_string in
  let state = current handle in
  let is_decision state =
    match state.State.phase with
    | State.Awaiting_discard seat when seat = model_seat ->
        not (List.exists (Action.equal Action.Hu) (Engine.legal_actions state seat))
    | _ -> false
  in
  let state = match member "action_id" json with
    | `Null -> state
    | value ->
        if not (is_decision state) then invalid_arg "submitted action outside model decision";
        apply_action state model_seat (Yojson.Safe.Util.to_int value)
  in
  let rec loop state =
    match state.State.phase with
    | State.Ended outcome -> (state, [ ("outcome", Observation_json.outcome_json outcome) ])
    | _ when state.revision >= limit -> invalid_arg "game exceeded max_steps"
    | _ when is_decision state ->
        let action, observation = prepared_decision state model_seat scaffold in
        (state, [ ("observation", observation); ("teacher_action", `Int action) ])
    | _ ->
        let seat = Option.get (Observation.actor state) in
        let variant = if seat = model_seat then scaffold else opponent in
        loop (apply_action state seat (teacher state seat variant))
  in
  let next, fields = loop state in
  Hashtbl.replace games handle next;
  `Assoc (("game", `Int handle) :: ("revision", `Int next.revision) :: fields)

let teacher_chunk json =
  let handle = int_member "game" json in
  let limit = int_member "max_steps" json in
  let count = int_member "count" json in
  if count < 1 || count > 256 then invalid_arg "chunk count must be in 1..256";
  let variant = member "variant" json |> Yojson.Safe.Util.to_string in
  let rec loop state remaining rows =
    match state.State.phase with
    | State.Ended outcome -> (state, List.rev rows, Observation_json.outcome_json outcome)
    | _ when state.revision >= limit -> invalid_arg "game exceeded max_steps"
    | _ when remaining = 0 -> (state, List.rev rows, `Null)
    | _ ->
        let seat = Option.get (Observation.actor state) in
        let action, observation = prepared_decision state seat variant in
        let row = `Assoc [ ("seat", `Int seat); ("action", `Int action);
                          ("revision", `Int state.revision); ("observation", observation) ] in
        loop (apply_action state seat action) (remaining - 1) (row :: rows)
  in
  let next, rows, outcome = loop (current handle) count [] in
  Hashtbl.replace games handle next;
  ok [ ("rows", `List rows); ("outcome", outcome) ]

let handle_request request =
  let json = Yojson.Safe.from_string request in
  match Yojson.Safe.Util.member "op" json |> Yojson.Safe.Util.to_string with
  | "advance_batch" ->
      let requests = member "requests" json |> Yojson.Safe.Util.to_list in
      let handles = List.map (int_member "game") requests in
      if List.length handles <> List.length (List.sort_uniq compare handles) then
        invalid_arg "duplicate game in batch";
      (* Commit all games together, so errors never leave a half-applied batch. *)
      let saved = List.map (fun handle -> (handle, current handle)) handles in
      (try ok [ ("results", `List (List.map advance requests)) ]
       with exn -> List.iter (fun (handle, state) -> Hashtbl.replace games handle state) saved; raise exn)
  | "teacher_chunk" -> teacher_chunk json
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
