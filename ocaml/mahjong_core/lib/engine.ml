let error message = Error message

let is_flower_instance instance = Tile.is_flower (Tile.instance_kind instance)

let counts_without_one hand kind =
  let counts = Tile_counts.of_instances hand in
  if counts.(kind) = 0 then None
  else begin
    counts.(kind) <- counts.(kind) - 1;
    Some counts
  end

let last_of_kind (state : State.t) seat kind = State.known_tile_count state seat kind = 4

let win_context (state : State.t) seat win_method flags =
  {
    Fan.seat_wind = State.seat_wind seat;
    round_wind = state.State.round_wind;
    win_method;
    flowers = List.length state.seats.(seat).flowers;
    flags;
  }

let self_draw_evaluation (state : State.t) seat =
  match state.State.drawn with
  | None -> None
  | Some winning ->
      let kind = Tile.instance_kind winning in
      if not (List.mem winning state.seats.(seat).hand) || Tile.is_flower kind then None
      else
        match counts_without_one state.seats.(seat).hand kind with
        | None -> None
        | Some concealed_before ->
            let flags =
              {
                Fan.after_kong = state.draw_source = State.Kong_replacement;
                last_tile = Wall.remaining state.wall = 0;
                robbing_kong = false;
                last_of_kind = last_of_kind state seat kind;
              }
            in
            let evaluation =
              Fan.evaluate ~concealed_before ~melds:state.seats.(seat).melds ~winning:kind
                ~context:(win_context state seat Fan.Self_draw flags)
            in
            if evaluation.Fan.winning then Some evaluation else None

let discard_evaluation (state : State.t) seat winning =
  let flags =
    {
      Fan.after_kong = false;
      last_tile = Wall.remaining state.wall = 0;
      robbing_kong = false;
      last_of_kind = last_of_kind state seat winning;
    }
  in
  let evaluation =
    Fan.evaluate ~concealed_before:(Tile_counts.of_instances state.seats.(seat).hand)
      ~melds:state.seats.(seat).melds ~winning
      ~context:(win_context state seat Fan.Discard flags)
  in
  if evaluation.Fan.winning then Some evaluation else None

let robbery_evaluation (state : State.t) seat winning =
  let flags =
    {
      Fan.after_kong = false;
      last_tile = Wall.remaining state.wall = 0;
      robbing_kong = true;
      last_of_kind = false;
    }
  in
  let evaluation =
    Fan.evaluate ~concealed_before:(Tile_counts.of_instances state.seats.(seat).hand)
      ~melds:state.seats.(seat).melds ~winning
      ~context:(win_context state seat Fan.Discard flags)
  in
  if evaluation.Fan.winning then Some evaluation else None

let chow_options hand kind =
  if not (Tile.is_numbered kind) then []
  else
    let counts = Tile_counts.of_instances hand in
    let base = (kind / 9) * 9 in
    let rank = Tile.rank kind in
    let first = max 1 (rank - 2) in
    let last = min 7 rank in
    let choices = ref [] in
    for start = first to last do
      let needed =
        [ base + start - 1; base + start; base + start + 1 ]
        |> List.filter (( <> ) kind)
      in
      let valid = List.for_all (fun needed_kind -> counts.(needed_kind) > 0) needed in
      if valid then choices := Action.Chow start :: !choices
    done;
    List.rev !choices

let discard_claim_options (state : State.t) discarder discard =
  let kind = Tile.instance_kind discard in
  let next = State.next_seat discarder in
  List.filter_map
    (fun seat ->
      if seat = discarder then None
      else
        let hand = state.State.seats.(seat).hand in
        let actions = ref [] in
        (match discard_evaluation state seat kind with
         | Some _ -> actions := Action.Hu :: !actions
         | None -> ());
        if State.count_kind hand kind >= 2 then actions := Action.Pung :: !actions;
        if State.count_kind hand kind >= 3 then actions := Action.Kong :: !actions;
        if seat = next then actions := List.rev_append (chow_options hand kind) !actions;
        if !actions = [] then None
        else Some (seat, List.sort_uniq compare (Action.Pass :: !actions)))
    [ 0; 1; 2; 3 ]

let rec draw_for state seat source back =
  let draw = if back then Wall.take_back state.State.wall else Wall.take_front state.State.wall in
  match draw with
  | None -> State.end_draw state
  | Some (instance, wall) ->
      let seat_state =
        { state.seats.(seat) with hand = State.sorted_instances (instance :: state.seats.(seat).hand) }
      in
      let seats = Array.copy state.seats in
      seats.(seat) <- seat_state;
      let state = { state with seats; wall; drawn = Some instance; draw_source = source } in
      let phase =
        if is_flower_instance instance then State.Awaiting_flower seat else State.Awaiting_discard seat
      in
      State.with_revision { state with phase }

let advance_after_discard state discarder =
  draw_for { state with drawn = None; just_claimed_meld = false } (State.next_seat discarder) State.Wall_draw false

let replace_river_discard seat_state discard =
  match State.remove_instance seat_state.State.river discard with
  | None -> None
  | Some river -> Some { seat_state with river }

let remove_flower_instance seat_state flower =
  match State.remove_instance seat_state.State.hand flower with
  | None -> None
  | Some hand -> Some { seat_state with hand; flowers = State.sorted_instances (flower :: seat_state.flowers) }

let make_window origin options = State.Reactions { origin; options; decisions = [] }

let begin_discard_window state discarder discard =
  let options = discard_claim_options state discarder discard in
  if options = [] then advance_after_discard state discarder
  else
    State.with_revision
      {
        state with
        phase = make_window (State.Discard_window { discarder; discard }) options;
        drawn = None;
      }

let discard state seat instance =
  match state.State.phase with
  | State.Awaiting_discard current when current = seat ->
      if not (List.mem instance state.seats.(seat).hand) then error "discard instance is not in hand"
      else if Tile.is_flower (Tile.instance_kind instance) then error "flower must use the flower choice window"
      else
        let seat_state = state.seats.(seat) in
        let hand = List.filter (( <> ) instance) seat_state.hand in
        let seat_state = { seat_state with hand; river = seat_state.river @ [ instance ] } in
        let seats = Array.copy state.seats in
        seats.(seat) <- seat_state;
        let state = State.with_history { state with seats } seat (Action.Discard instance) in
        Ok (begin_discard_window state seat instance)
  | _ -> error "discard is not legal in the current phase"

let expose_flower state seat =
  match state.State.phase with
  | State.Awaiting_flower current when current = seat -> (
      match state.seats.(seat).hand |> List.find_opt is_flower_instance with
      | None -> error "no concealed flower to expose"
      | Some flower -> (
          match remove_flower_instance state.seats.(seat) flower with
          | None -> error "flower disappeared from hand"
          | Some seat_state ->
              let seats = Array.copy state.seats in
              seats.(seat) <- seat_state;
              let state = State.with_history { state with seats } seat Action.Expose_flower in
              Ok (draw_for state seat State.Flower_replacement true)))
  | _ -> error "flower replacement is not legal in the current phase"

let discard_flower state seat instance =
  match state.State.phase with
  | State.Awaiting_flower current when current = seat ->
      if not (List.mem instance state.seats.(seat).hand) || not (is_flower_instance instance) then
        error "only the held flower may be discarded without replacement"
      else
        let seat_state = state.seats.(seat) in
        let seats = Array.copy state.seats in
        seats.(seat) <-
          {
            seat_state with
            hand = List.filter (( <> ) instance) seat_state.hand;
            river = seat_state.river @ [ instance ];
          };
        let state = State.with_history { state with seats } seat (Action.Discard instance) in
        Ok (advance_after_discard state seat)
  | _ -> error "flower discard is not legal in the current phase"

let self_draw state seat =
  match state.State.phase with
  | State.Awaiting_discard current when current = seat -> (
      match self_draw_evaluation state seat with
      | None -> error "self-draw hu is not legal"
      | Some evaluation ->
          let winning = Option.get state.drawn in
          Ok
            (State.with_history
               (State.finish_win state ~winner:seat ~discarder:None ~winning_tile:winning ~evaluation)
               seat Action.Hu))
  | _ -> error "self-draw hu is not legal in the current phase"

let find_four hand kind =
  if State.count_kind hand kind = 4 then
    match State.remove_kind_n hand [ kind; kind; kind; kind ] with
    | None -> None
    | Some instances ->
        Some (instances, List.filter (fun instance -> not (List.mem instance instances)) hand)
  else None

let concealed_kong state seat kind =
  match state.State.phase with
  | State.Awaiting_discard current when current = seat ->
      if state.just_claimed_meld then error "cannot kong on the same turn as a meld claim"
      else (
        match find_four state.seats.(seat).hand kind with
        | None -> error "concealed kong requires four concealed copies"
        | Some (instances, hand) ->
            let meld = Meld.concealed_kong ~tile:kind ~instances in
            let seat_state =
              {
                state.seats.(seat) with
                hand;
                melds = meld :: state.seats.(seat).melds;
              }
            in
            let seats = Array.copy state.seats in
            seats.(seat) <- seat_state;
            let state =
              State.with_history { state with seats; just_claimed_meld = true } seat (Action.Concealed_kong kind)
            in
            Ok (draw_for state seat State.Kong_replacement true))
  | _ -> error "concealed kong is not legal in the current phase"

let find_pung melds kind =
  let rec loop prefix = function
    | [] -> None
    | meld :: rest ->
        if meld.Meld.kind = Meld.Pung && meld.tile = kind then Some (meld, List.rev_append prefix rest)
        else loop (meld :: prefix) rest
  in
  loop [] melds

let added_kong_options state declarer kind fourth =
  List.filter_map
    (fun seat ->
      if seat = declarer then None
      else
        match robbery_evaluation state seat kind with
        | Some _ -> Some (seat, [ Action.Pass; Action.Hu ])
        | None -> None)
    [ 0; 1; 2; 3 ]
  |> fun options ->
  if options = [] then None
  else Some (make_window (State.Added_kong_window { declarer; kind; fourth }) options)

let rec added_kong state seat kind =
  match state.State.phase with
  | State.Awaiting_discard current when current = seat ->
      if state.just_claimed_meld then error "cannot kong on the same turn as a meld claim"
      else (
        match find_pung state.seats.(seat).melds kind with
        | None -> error "added kong requires an existing pung"
        | Some _ -> (
            match State.remove_one_kind state.seats.(seat).hand kind with
            | None -> error "added kong requires the fourth tile in hand"
            | Some (fourth, _) -> (
                match added_kong_options state seat kind fourth with
                | Some phase ->
                    Ok
                      (State.with_history
                         (State.with_revision { state with phase })
                         seat (Action.Added_kong kind))
                | None ->
                    let state = State.with_history state seat (Action.Added_kong kind) in
                    Ok (complete_added_kong state seat kind fourth))))
  | _ -> error "added kong is not legal in the current phase"

and complete_added_kong state declarer kind fourth =
  let seat_state = state.State.seats.(declarer) in
  match State.remove_instance seat_state.hand fourth, find_pung seat_state.melds kind with
  | Some hand, Some (pung, other_melds) ->
      let kong =
        Meld.kong ~tile:kind
          ~instances:(State.sorted_instances (fourth :: pung.Meld.instances))
          ~concealed:false ~origin:(Meld.Added { fourth })
      in
      let seat_state = { seat_state with hand; melds = kong :: other_melds } in
      let seats = Array.copy state.seats in
      seats.(declarer) <- seat_state;
      draw_for { state with seats; just_claimed_meld = true } declarer State.Kong_replacement true
  | _ -> State.end_draw state

let claim_meld (state : State.t) window claimant action =
  match window.State.origin with
  | State.Discard_window { discarder; discard } -> (
      let kind = Tile.instance_kind discard in
      let base = (kind / 9) * 9 in
      match replace_river_discard state.seats.(discarder) discard with
      | None -> error "discarded tile is missing from the river"
      | Some discarder_state ->
          let claimant_state = state.seats.(claimant) in
          let placed_meld =
            match action with
            | Action.Pung -> (
                match State.remove_kind_n claimant_state.hand [ kind; kind ] with
                | None -> None
                | Some instances ->
                    Some
                      (Meld.pung ~tile:kind ~instances:(discard :: instances)
                         ~origin:(Meld.Claimed { discarder; discard })))
            | Action.Kong -> (
                match State.remove_kind_n claimant_state.hand [ kind; kind; kind ] with
                | None -> None
                | Some instances ->
                    Some
                      (Meld.kong ~tile:kind ~instances:(discard :: instances) ~concealed:false
                         ~origin:(Meld.Claimed { discarder; discard })))
            | Action.Chow start ->
                let needed =
                  [ base + start - 1; base + start; base + start + 1 ]
                  |> List.filter (( <> ) kind)
                in
                (match State.remove_kind_n claimant_state.hand needed with
                 | None -> None
                 | Some instances ->
                     Some
                       (Meld.chow ~middle:(base + start) ~instances:(discard :: instances)
                          ~origin:(Meld.Claimed { discarder; discard })))
            | _ -> None
          in
          match placed_meld with
          | None ->
              error
                ("claim tiles are not available: " ^ Action.describe action ^ " discarded="
               ^ Tile.code kind ^ " hand=" ^ String.concat " " (List.map Tile.instance_code claimant_state.hand))
          | Some meld ->
              let hand =
                List.filter
                  (fun instance -> not (List.mem instance meld.Meld.instances))
                  claimant_state.hand
              in
              let seats = Array.copy state.seats in
              seats.(discarder) <- discarder_state;
              seats.(claimant) <- { claimant_state with hand; melds = meld :: claimant_state.melds };
              let state =
                State.with_revision
                  {
                    state with
                    seats;
                    phase = State.Awaiting_discard claimant;
                    drawn = None;
                    just_claimed_meld = true;
                  }
              in
              if action = Action.Kong then Ok (draw_for state claimant State.Kong_replacement true)
              else Ok state)
  | State.Added_kong_window { declarer; kind; fourth } -> (
      match action with
      | Action.Hu -> error "hu must be resolved before meld completion"
      | _ -> Ok (complete_added_kong state declarer kind fourth))

let settle_discard_win state winner discarder discard evaluation =
  let winner_state = state.State.seats.(winner) in
  match replace_river_discard state.seats.(discarder) discard with
  | None -> error "winning discard is missing from the river"
  | Some discarder_state ->
      let seats = Array.copy state.seats in
      seats.(discarder) <- discarder_state;
      seats.(winner) <- { winner_state with hand = State.sorted_instances (discard :: winner_state.hand) };
      Ok
        (State.finish_win { state with seats } ~winner ~discarder:(Some discarder)
           ~winning_tile:discard ~evaluation)

let settle_robbing_kong state winner declarer fourth evaluation =
  let declarer_state = state.State.seats.(declarer) in
  match State.remove_instance declarer_state.hand fourth with
  | None -> error "robbed kong tile is missing from declarer hand"
  | Some declarer_hand ->
      let winner_state = state.seats.(winner) in
      let seats = Array.copy state.seats in
      seats.(declarer) <- { declarer_state with hand = declarer_hand };
      seats.(winner) <- { winner_state with hand = State.sorted_instances (fourth :: winner_state.hand) };
      Ok
        (State.finish_win { state with seats } ~winner ~discarder:(Some declarer)
           ~winning_tile:fourth ~evaluation)

let nearest participants from_seat =
  match participants with
  | [] -> None
  | first :: rest ->
      Some
        (List.fold_left
           (fun best current ->
             if State.distance from_seat current < State.distance from_seat best then current else best)
           first rest)

let decide_discard_window (state : State.t) window =
  match window.State.origin with
  | State.Discard_window { discarder; discard } ->
      let hu_claimants =
        window.decisions
        |> List.filter_map (fun (seat, action) -> if action = Action.Hu then Some seat else None)
      in
      (match nearest hu_claimants discarder with
       | Some winner -> (
           match discard_evaluation state winner (Tile.instance_kind discard) with
           | None -> error "recorded hu is no longer legal"
           | Some evaluation -> settle_discard_win state winner discarder discard evaluation)
       | None ->
           let meld_claimants =
             window.decisions
             |> List.filter_map (fun (seat, action) ->
                    match action with Action.Pung | Action.Kong -> Some seat | _ -> None)
           in
           (match nearest meld_claimants discarder with
            | Some seat -> claim_meld state window seat (List.assoc seat window.decisions)
            | None ->
                let chow_claimants =
                  window.decisions
                  |> List.filter_map (fun (seat, action) ->
                         match action with Action.Chow _ -> Some seat | _ -> None)
                in
                (match nearest chow_claimants discarder with
                 | None -> Ok (advance_after_discard state discarder)
                 | Some seat -> claim_meld state window seat (List.assoc seat window.decisions))))
  | _ -> error "invalid discard reaction window"

let decide_added_kong_window (state : State.t) window =
  match window.State.origin with
  | State.Added_kong_window { declarer; kind; fourth } ->
      let hu_claimants =
        window.decisions
        |> List.filter_map (fun (seat, action) -> if action = Action.Hu then Some seat else None)
      in
      (match nearest hu_claimants declarer with
       | Some winner -> (
           match robbery_evaluation state winner kind with
           | None -> error "recorded robbing-kong hu is no longer legal"
           | Some evaluation -> settle_robbing_kong state winner declarer fourth evaluation)
       | None -> Ok (complete_added_kong state declarer kind fourth))
  | _ -> error "invalid reaction window"

let resolve_window (state : State.t) window =
  match window.State.origin with
  | State.Discard_window _ -> decide_discard_window state window
  | State.Added_kong_window _ -> decide_added_kong_window state window

let respond (state : State.t) seat action =
  match state.State.phase with
  | State.Reactions window ->
      let options =
        match List.assoc_opt seat window.options with
        | Some options -> options
        | None -> []
      in
      if options = [] then error "seat has no response in this window"
      else if List.exists (fun (decided, _) -> decided = seat) window.decisions then
        error "seat already responded in this window"
      else if not (List.exists (Action.equal action) options) then error "response is not in the legal set"
      else
        let window = { window with decisions = (seat, action) :: window.decisions } in
        let pending = List.exists (fun (responder, _) -> not (List.exists (fun (decided, _) -> decided = responder) window.decisions)) window.options in
        if pending then
          let state = State.with_revision { state with phase = State.Reactions window } in
          Ok (State.with_history state seat action)
        else
          let state = State.with_history state seat action in
          resolve_window state window
  | _ -> error "not in a response window"

let legal_actions (state : State.t) seat =
  match state.State.phase with
  | State.Awaiting_discard current when current = seat ->
      let discards = List.map (fun instance -> Action.Discard instance) state.seats.(seat).hand in
      let hu = match self_draw_evaluation state seat with Some _ -> [ Action.Hu ] | None -> [] in
      let counts = Tile_counts.of_instances state.seats.(seat).hand in
      let kongs =
        if state.just_claimed_meld then []
        else
          List.init Tile.standard_kind_count Fun.id
          |> List.filter_map (fun kind ->
                 if counts.(kind) = 4 then Some (Action.Concealed_kong kind) else None)
      in
      let added =
        if state.just_claimed_meld then []
        else
          state.seats.(seat).melds
          |> List.filter_map (fun meld ->
                 if meld.Meld.kind = Meld.Pung && counts.(meld.tile) >= 1 then Some (Action.Added_kong meld.tile)
                 else None)
      in
      hu @ kongs @ added @ discards
  | State.Awaiting_flower current when current = seat ->
      Action.Expose_flower
      :: (state.seats.(seat).hand
          |> List.filter is_flower_instance
          |> List.map (fun instance -> Action.Discard instance))
  | State.Reactions window -> (
      match List.assoc_opt seat window.options with Some actions -> actions | None -> [])
  | State.Ended _ -> []
  | _ -> []

let step (state : State.t) seat action =
  match action with
  | Action.Discard instance -> (
      match state.State.phase with
      | State.Awaiting_flower _ -> discard_flower state seat instance
      | _ -> discard state seat instance)
  | Action.Expose_flower -> expose_flower state seat
  | Action.Hu -> (
      match state.State.phase with
      | State.Reactions _ -> respond state seat action
      | _ -> self_draw state seat)
  | Action.Pass | Action.Chow _ | Action.Pung | Action.Kong -> respond state seat action
  | Action.Concealed_kong kind -> concealed_kong state seat kind
  | Action.Added_kong kind -> added_kong state seat kind
