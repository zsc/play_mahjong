type discard_choice = {
  kind : Tile.t;
  shanten : int;
  ukeire : int;
  qualifying_waits : int;
  qualifying_value : int;
}

type reaction_policy =
  | Any_improvement
  | Closed_hand
  | Closed_hand_with_kong
  | Tenpai_only
  | Qualified_tenpai
  | Qualified_best
  | No_chow

let unseen_counts (state : State.t) seat =
  Array.map (fun count -> max 0 (4 - count)) (State.known_tile_counts state seat)

let fan_context state seat =
  {
    Fan.seat_wind = State.seat_wind seat;
    round_wind = state.State.round_wind;
    win_method = Fan.Discard;
    flowers = List.length state.seats.(seat).flowers;
    flags = Fan.no_flags;
  }

let ukeire ?evaluator ~meld_count ~base unseen counts =
  let total = ref 0 in
  for kind = 0 to Tile.standard_kind_count - 1 do
    if unseen.(kind) > 0 then begin
      counts.(kind) <- counts.(kind) + 1;
      let next = match evaluator with
        | None -> Shanten.of_counts ~meld_count counts
        | Some e ->
            Shanten.adjust e kind 1;
            let value = Shanten.evaluate e in
            Shanten.adjust e kind (-1);
            value
      in
      counts.(kind) <- counts.(kind) - 1;
      if next < base then total := !total + unseen.(kind)
    end
  done;
  !total

let qualifying_stats ~melds ~context ~unseen counts =
  let waits = ref 0 in
  let value = ref 0 in
  for kind = 0 to Tile.standard_kind_count - 1 do
    if unseen.(kind) > 0 && counts.(kind) < 4 then begin
      if Shape.winning_shape ~concealed_before:counts ~melds ~winning:kind then begin
        let evaluation =
          Fan.evaluate ~concealed_before:counts ~melds ~winning:kind ~context
        in
        if evaluation.Fan.winning then begin
          waits := !waits + unseen.(kind);
          value := !value + (unseen.(kind) * (evaluation.total_fan + 8))
        end
      end
    end
  done;
  (!waits, !value)

let discard_choices ~meld_count ~melds ~context ~unseen ~score_waits counts =
  let choices = ref [] in
  let evaluator = Shanten.make_evaluator ~meld_count counts in
  for kind = 0 to Tile.standard_kind_count - 1 do
    if counts.(kind) > 0 then begin
      counts.(kind) <- counts.(kind) - 1;
      Shanten.adjust evaluator kind (-1);
      let shanten = Shanten.evaluate evaluator in
      let ukeire = ukeire ~evaluator ~meld_count ~base:shanten unseen counts in
      let qualifying_waits, qualifying_value =
        if score_waits && shanten = 0 then
          qualifying_stats ~melds ~context ~unseen counts
        else (0, 0)
      in
      counts.(kind) <- counts.(kind) + 1;
      Shanten.adjust evaluator kind 1;
      choices := { kind; shanten; ukeire; qualifying_waits; qualifying_value } :: !choices
    end
  done;
  !choices

let best_discard choices =
  match choices with
  | [] -> None
  | first :: rest ->
      Some
        (List.fold_left
           (fun best current ->
             if current.shanten < best.shanten then current
             else if current.shanten > best.shanten then best
             else if current.qualifying_value > best.qualifying_value then current
             else if current.qualifying_value < best.qualifying_value then best
             else if current.qualifying_waits > best.qualifying_waits then current
             else if current.qualifying_waits < best.qualifying_waits then best
             else if current.ukeire > best.ukeire then current
             else if current.ukeire < best.ukeire then best
             else best)
           first rest)

let choose_discard ~meld_count ~melds ~context ~unseen ~score_waits counts =
  best_discard (discard_choices ~meld_count ~melds ~context ~unseen ~score_waits counts)

let choices_for_state state seat =
  let standard_instances =
    List.filter
      (fun instance -> Tile.is_standard_kind (Tile.instance_kind instance))
      state.State.seats.(seat).hand
  in
  let counts = Tile_counts.of_instances standard_instances in
  let unseen = unseen_counts state seat in
  let melds = state.seats.(seat).melds in
  let context = fan_context state seat in
  discard_choices ~meld_count:(List.length melds) ~melds ~context ~unseen
    ~score_waits:true counts

let discard_hints ?choices state seat =
  let choices = match choices with Some values -> values | None -> choices_for_state state seat in
  let shanten = Array.make Tile.standard_kind_count (-1) in
  let ukeire = Array.make Tile.standard_kind_count 0 in
  let qualifying_waits = Array.make Tile.standard_kind_count 0 in
  let qualifying_value = Array.make Tile.standard_kind_count 0 in
  List.iter
    (fun choice ->
      shanten.(choice.kind) <- choice.shanten;
      ukeire.(choice.kind) <- choice.ukeire;
      qualifying_waits.(choice.kind) <- choice.qualifying_waits;
      qualifying_value.(choice.kind) <- choice.qualifying_value)
    choices;
  (shanten, ukeire, qualifying_waits, qualifying_value)

let claim_candidate (state : State.t) seat action =
  let discarder, discard =
    match state.State.phase with
    | State.Reactions { origin = State.Discard_window { discarder; discard }; _ } ->
        (discarder, discard)
    | _ -> (-1, -1)
  in
  if discarder < 0 then None
  else
    let kind = Tile.instance_kind discard in
    let counts = Tile_counts.of_instances state.seats.(seat).hand in
    match action with
    | Action.Pung when counts.(kind) >= 2 ->
        counts.(kind) <- counts.(kind) - 2;
        Some
          ( counts,
            Meld.pung ~tile:kind ~instances:[]
              ~origin:(Meld.Claimed { discarder; discard }) )
    | Action.Kong when counts.(kind) >= 3 ->
        counts.(kind) <- counts.(kind) - 3;
        Some
          ( counts,
            Meld.kong ~tile:kind ~instances:[] ~concealed:false
              ~origin:(Meld.Claimed { discarder; discard }) )
    | Action.Chow start ->
        let base = (kind / 9) * 9 in
        let needed = [ base + start - 1; base + start; base + start + 1 ] |> List.filter (( <> ) kind) in
        if List.for_all (fun needed_kind -> counts.(needed_kind) > 0) needed then begin
          List.iter (fun needed_kind -> counts.(needed_kind) <- counts.(needed_kind) - 1) needed;
          Some
            ( counts,
              Meld.chow ~middle:(base + start) ~instances:[]
                ~origin:(Meld.Claimed { discarder; discard }) )
        end else None
    | _ -> None

let requires_tenpai = function
  | Tenpai_only | Qualified_tenpai | Qualified_best -> true
  | _ -> false

let claim_rank choice =
  ( choice.shanten,
    -choice.qualifying_value,
    -choice.qualifying_waits,
    -choice.ukeire )

let choose_reaction ~policy (state : State.t) seat actions =
  if List.exists (Action.equal Action.Hu) actions then Action.Hu
  else if policy = Closed_hand || policy = Closed_hand_with_kong then Action.Pass
  else
    let current = Tile_counts.of_instances state.seats.(seat).hand in
    let meld_count = List.length state.seats.(seat).melds in
    let current_shanten = Shanten.of_counts ~meld_count current in
    let unseen = unseen_counts state seat in
    let best_action = ref None in
    let best_shanten = ref current_shanten in
    let best_rank = ref None in
    List.iter
      (fun action ->
        match claim_candidate state seat action with
        | None -> ()
        | Some (counts, meld) ->
            let melds = meld :: state.seats.(seat).melds in
            let candidate =
              choose_discard ~meld_count:(List.length melds) ~melds
                ~context:(fan_context state seat) ~unseen
                ~score_waits:(policy = Qualified_tenpai || policy = Qualified_best) counts
            in
            match candidate with
            | Some choice
              when choice.shanten < current_shanten
                   && (not (requires_tenpai policy) || choice.shanten = 0)
                   && (policy = Closed_hand || policy = Closed_hand_with_kong
                      || policy = Any_improvement || policy = No_chow
                      || choice.qualifying_waits > 0) ->
                if policy = Qualified_best then begin
                  let rank = claim_rank choice in
                  match !best_rank with
                  | None ->
                      best_rank := Some rank;
                      best_action := Some action
                  | Some previous when rank < previous ->
                      best_rank := Some rank;
                      best_action := Some action
                  | Some _ -> ()
                end else if choice.shanten < !best_shanten then begin
                  best_shanten := choice.shanten;
                  best_action := Some action
                end
            | _ -> ())
      (match policy with
       | No_chow -> List.filter (function Action.Chow _ -> false | _ -> true) actions
       | _ -> actions);
    match !best_action with Some action -> action | None -> Action.Pass

let choose_action_with_policy ?choices policy (state : State.t) seat =
  let actions = Engine.legal_actions state seat in
  match actions with
  | [] -> None
  | _ when List.exists (Action.equal Action.Hu) actions -> Some Action.Hu
  | _ -> (
      match state.State.phase with
      | State.Awaiting_flower _ ->
          if List.exists (Action.equal Action.Expose_flower) actions then Some Action.Expose_flower
          else List.find_opt (function Action.Discard _ -> true | _ -> false) actions
      | State.Awaiting_discard _ ->
          let concealed_kong =
            if policy = Closed_hand_with_kong then
              List.find_opt (function Action.Concealed_kong _ -> true | _ -> false) actions
            else None
          in
          (match concealed_kong with
           | Some action -> Some action
           | None ->
               let choice =
                 best_discard (match choices with Some values -> values | None -> choices_for_state state seat)
               in
               (match choice with
                | None -> None
                | Some choice ->
                    List.find_opt
                      (function
                        | Action.Discard instance -> Tile.instance_kind instance = choice.kind
                        | _ -> false)
                      actions))
      | State.Reactions _ -> Some (choose_reaction ~policy state seat actions)
      | State.Ended _ -> None)

let choose_action = choose_action_with_policy Any_improvement

let choose_action_id state seat =
  match choose_action state seat with
  | None -> None
  | Some action -> Some (Action_catalog.id_of_action state seat action)

let choose_action_id_with_variant ?choices state seat variant =
  let policy =
    match variant with
    | "default" -> Any_improvement
    | "closed" -> Closed_hand
    | "closed-kong" -> Closed_hand_with_kong
    | "tenpai-only" -> Tenpai_only
    | "qualified-tenpai" -> Qualified_tenpai
    | "qualified-best" -> Qualified_best
    | "no-chow" -> No_chow
    | value -> invalid_arg ("unknown heuristic variant: " ^ value)
  in
  match choose_action_with_policy ?choices policy state seat with
  | None -> None
  | Some action -> Some (Action_catalog.id_of_action state seat action)
