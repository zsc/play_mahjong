open Mahjong_core

let tiles_of_strings values = List.map Tile.of_string values

let counts values = Tile_counts.of_kinds (tiles_of_strings values)

let test_physical_tiles () =
  let instances = List.init Tile.physical_tile_count Fun.id in
  Alcotest.(check int) "144 physical tiles" 144 (List.length instances);
  let ids = List.map Tile.instance_kind instances in
  let unique = List.sort_uniq compare ids in
  Alcotest.(check int) "42 kinds" 42 (List.length unique);
  for kind = 0 to 33 do
    let copies = List.filter (( = ) kind) ids in
    Alcotest.(check int) ("four copies of " ^ Tile.code kind) 4 (List.length copies)
  done;
  for kind = 34 to 41 do
    let copies = List.filter (( = ) kind) ids in
    Alcotest.(check int) ("one copy of " ^ Tile.code kind) 1 (List.length copies)
  done

let test_wall_seed () =
  let left = Wall.create 42 in
  let right = Wall.create 42 in
  Alcotest.(check int) "same seed same wall" 144 (Wall.remaining left);
  Alcotest.(check (list int)) "deterministic order" (Array.to_list (Wall.remaining_tiles left))
    (Array.to_list (Wall.remaining_tiles right));
  let sorted = Array.to_list (Wall.remaining_tiles left) |> List.sort_uniq compare in
  Alcotest.(check int) "wall is a permutation" 144 (List.length sorted);
  let front_tile, after_front = Option.get (Wall.take_front left) in
  let back_tile, after_both = Option.get (Wall.take_back after_front) in
  Alcotest.(check int) "front draw" left.tiles.(0) front_tile;
  Alcotest.(check int) "back draw" left.tiles.(143) back_tile;
  Alcotest.(check int) "two draws" 142 (Wall.remaining after_both)

let test_normal_win () =
  let hand =
    counts [ "W1"; "W2"; "W3"; "W4"; "W5"; "W6"; "W7"; "W8"; "W9"; "B1"; "B2"; "B3"; "E" ]
  in
  Alcotest.(check bool) "waiting on east pair" true
    (Shape.winning_shape ~concealed_before:hand ~melds:[] ~winning:(Tile.of_string "E"));
  Alcotest.(check bool) "not waiting on red dragon" false
    (Shape.winning_shape ~concealed_before:hand ~melds:[] ~winning:(Tile.of_string "J3"))

let test_special_wins () =
  let seven_pairs =
    counts [ "W1"; "W1"; "W3"; "W3"; "W5"; "W5"; "W7"; "W7"; "B2"; "B2"; "B4"; "B4"; "B6" ]
  in
  Alcotest.(check bool) "seven pairs" true
    (Shape.winning_shape ~concealed_before:seven_pairs ~melds:[] ~winning:(Tile.of_string "B6"));
  let orphans =
    counts [ "W1"; "W9"; "T1"; "T9"; "B1"; "B9"; "E"; "S"; "W"; "N"; "J3"; "J2"; "J1" ]
  in
  Alcotest.(check bool) "thirteen orphans" true
    (Shape.winning_shape ~concealed_before:orphans ~melds:[] ~winning:(Tile.of_string "W1"));
  Alcotest.(check bool) "special classification" true
    (Shape.special (Tile_counts.of_kinds (tiles_of_strings
       [ "W1"; "W1"; "W9"; "W9"; "T1"; "T1"; "B9"; "B9"; "E"; "E"; "S"; "S"; "J1"; "J1" ])) []
     = Shape.Seven_pairs)

let test_thirteen_distinct_is_not_thirteen_orphans () =
  let hand =
    counts [ "W7"; "W9"; "T5"; "T7"; "B2"; "B3"; "B4"; "B4"; "B7"; "B9"; "F3"; "F4"; "J3"; "J1" ]
  in
  Alcotest.(check bool) "non-orphan distinct hand is not thirteen orphans" true
    (Shape.special hand [] = Shape.None);
  Alcotest.(check bool) "non-orphan distinct hand cannot win on J1" false
    (Shape.winning_shape
       ~concealed_before:(Tile_counts.of_kinds (tiles_of_strings
          [ "W7"; "W9"; "T5"; "T7"; "B2"; "B3"; "B4"; "B4"; "B7"; "B9"; "F3"; "F4"; "J3" ]))
       ~melds:[] ~winning:(Tile.of_string "J1"))

let test_knitted () =
  let hand =
    counts [ "W1"; "W4"; "W7"; "T2"; "T5"; "T8"; "B3"; "B6"; "B9"; "E"; "E"; "E"; "N" ]
  in
  Alcotest.(check bool) "combination dragon with honor pair" true
    (Shape.winning_shape ~concealed_before:hand ~melds:[] ~winning:(Tile.of_string "N"));
  let seven_star =
    counts [ "W1"; "W4"; "W7"; "T2"; "T5"; "T8"; "B3"; "E"; "S"; "W"; "N"; "J3"; "J2" ]
  in
  Alcotest.(check bool) "seven star disconnected" true
    (Shape.winning_shape ~concealed_before:seven_star ~melds:[] ~winning:(Tile.of_string "J1"))

let context ?(method_ = Fan.Discard) ?(flowers = 0) () =
  {
    Fan.seat_wind = 27;
    round_wind = 27;
    win_method = method_;
    flowers;
    flags = Fan.no_flags;
  }

let test_fan_threshold () =
  let seven_pairs =
    counts [ "W1"; "W1"; "W3"; "W3"; "W5"; "W5"; "W7"; "W7"; "B2"; "B2"; "B4"; "B4"; "B6" ]
  in
  let result =
    Fan.evaluate ~concealed_before:seven_pairs ~melds:[] ~winning:(Tile.of_string "B6")
      ~context:(context ())
  in
  Alcotest.(check bool) "seven pairs legal" true result.winning;
  Alcotest.(check int) "seven pairs with one voided suit and no honors" 26 result.qualifying_fan;
  let low_hand =
    counts [ "W1"; "W2"; "W3"; "W5"; "W6"; "W7"; "T2"; "T3"; "T4"; "T7"; "T8"; "T9"; "T9" ]
  in
  let low =
    Fan.evaluate ~concealed_before:low_hand ~melds:[] ~winning:(Tile.of_string "T9")
      ~context:(context ~flowers:8 ())
  in
  Alcotest.(check bool) "flowers cannot satisfy threshold" false low.winning;
  Alcotest.(check int) "flower fan recorded separately" 8 low.flower_fan;
  let full_flush =
    counts [ "W1"; "W2"; "W3"; "W4"; "W5"; "W6"; "W7"; "W8"; "W6"; "W7"; "W8"; "W9"; "W9" ]
  in
  let high =
    Fan.evaluate ~concealed_before:full_flush ~melds:[] ~winning:(Tile.of_string "W9")
      ~context:(context ())
  in
  Alcotest.(check bool) "full flush legal" true high.winning;
  Alcotest.(check bool) "full flush awarded" true (List.exists (fun award -> award.Fan.fan = Fan.Full_flush) high.awards)

let test_chicken_hand () =
  let exposed = Meld.chow ~middle:(Tile.of_string "W3") ~instances:[] ~origin:(Meld.Claimed { discarder = 3; discard = 0 }) in
  let exposed_second =
    Meld.chow ~middle:(Tile.of_string "B5") ~instances:[] ~origin:(Meld.Claimed { discarder = 2; discard = 1 })
  in
  let before =
    counts [ "T7"; "T7"; "T7"; "B5"; "B6"; "E"; "E" ]
  in
  let result =
    Fan.evaluate ~concealed_before:before ~melds:[ exposed; exposed_second ] ~winning:(Tile.of_string "B7")
      ~context:(context ())
  in
  Alcotest.(check bool) "chicken hand is legal" true result.winning;
  Alcotest.(check int) "chicken hand scores exactly eight" 8 result.qualifying_fan;
  Alcotest.(check int) "chicken hand is the only award" 1 (List.length result.awards);
  Alcotest.(check bool) "chicken award" true
    (List.exists (fun award -> award.Fan.fan = Fan.Chicken_hand) result.awards)

let meld_chow code =
  Meld.chow ~middle:(Tile.of_string code) ~instances:[] ~origin:Meld.Concealed

let test_all_types () =
  let before = counts [ "E"; "E"; "E"; "J1" ] in
  let melds = [ meld_chow "W2"; meld_chow "T5"; meld_chow "B8" ] in
  let result =
    Fan.evaluate ~concealed_before:before ~melds ~winning:(Tile.of_string "J1")
      ~context:(context ())
  in
  Alcotest.(check bool) "all types awarded" true
    (List.exists (fun award -> award.Fan.fan = Fan.All_types) result.awards);
  let near_miss_before = counts [ "E"; "E"; "E"; "J1" ] in
  let near_miss_melds = [ meld_chow "W2"; meld_chow "W5"; meld_chow "B8" ] in
  let near_miss =
    Fan.evaluate ~concealed_before:near_miss_before ~melds:near_miss_melds ~winning:(Tile.of_string "J1")
      ~context:(context ())
  in
  Alcotest.(check bool) "all types needs one set per tile type" false
    (List.exists (fun award -> award.Fan.fan = Fan.All_types) near_miss.awards)

let test_formal_wait_fifth_copy () =
  let before = counts [ "W1"; "E"; "E"; "E"; "S"; "S"; "S"; "W"; "W"; "W" ] in
  let meld = Meld.pung ~tile:(Tile.of_string "W1") ~instances:[] ~origin:Meld.Concealed in
  let waits = Fan.formal_waits before [ meld ] in
  Alcotest.(check bool) "fifth physical copy is not a wait" false
    (List.mem (Tile.of_string "W1") waits)

let actor state =
  match state.State.phase with
  | State.Awaiting_discard seat | State.Awaiting_flower seat -> Some seat
  | State.Reactions window ->
      window.options
      |> List.find_map (fun (seat, _) ->
             if List.exists (fun (decided, _) -> decided = seat) window.decisions then None else Some seat)
  | State.Ended _ -> None

let test_state_start () =
  let state = State.initial 12345 27 in
  Alcotest.(check (result unit string)) "partition valid" (Ok ()) (State.validate state);
  Alcotest.(check int) "dealer concealed count" 14 (List.length state.seats.(0).hand);
  for seat = 1 to 3 do
    Alcotest.(check int) "non-dealer concealed count" 13 (List.length state.seats.(seat).hand)
  done;
  for seat = 0 to 3 do
    Alcotest.(check int) "no concealed flowers at start" 0
      (List.length (List.filter (fun instance -> Tile.is_flower (Tile.instance_kind instance)) state.seats.(seat).hand))
  done;
  Alcotest.(check bool) "dealer has legal action" true (Engine.legal_actions state 0 <> [])

let test_action_catalog () =
  let state = State.initial 13579 27 in
  let ids = Action_catalog.legal state 0 in
  Alcotest.(check bool) "dealer has catalogued actions" true (ids <> []);
  List.iter
    (fun id ->
      Alcotest.(check bool) ("action id in range " ^ string_of_int id) true
        (id >= 0 && id < Action_catalog.size);
      match Action_catalog.action_of_id state 0 id with
      | None -> Alcotest.fail ("legal id did not resolve: " ^ Action_catalog.key id)
      | Some action ->
          Alcotest.(check int) ("round trip " ^ Action.describe action) id
            (Action_catalog.id_of_action state 0 action))
    ids;
  let discard_ids =
    ids |> List.filter (fun id -> id >= Action_catalog.discard_start
                                  && id < Action_catalog.discard_start + Tile.standard_kind_count)
  in
  Alcotest.(check int) "duplicate physical copies collapse to one discard kind"
    (List.length (List.sort_uniq compare discard_ids)) (List.length discard_ids)

let test_shanten () =
  let winning =
    counts [ "W1"; "W2"; "W3"; "W4"; "W5"; "W6"; "W7"; "W8"; "W9"; "T1"; "T2"; "T3"; "E"; "E" ]
  in
  Alcotest.(check int) "complete hand" (-1) (Shanten.of_counts ~meld_count:0 winning);
  let tenpai =
    counts [ "W1"; "W2"; "W3"; "W4"; "W5"; "W6"; "W7"; "W8"; "W9"; "T1"; "T2"; "T3"; "E" ]
  in
  Alcotest.(check int) "single wait tenpai" 0 (Shanten.of_counts ~meld_count:0 tenpai);
  let two_away =
    counts [ "W1"; "W4"; "W7"; "T2"; "T5"; "T8"; "B3"; "B6"; "B9"; "E"; "S"; "W"; "N" ]
  in
  Alcotest.(check bool) "disconnected hand has a finite distance" true
    (Shanten.of_counts ~meld_count:0 two_away > 0)

let test_qualifying_wait_does_not_double_count () =
  let hand =
    counts [ "W1"; "W2"; "W3"; "W4"; "W5"; "W6"; "W7"; "W8"; "W9"; "B1"; "B2"; "B3"; "E" ]
  in
  let before = Array.copy hand in
  let unseen = Array.init Tile.standard_kind_count (fun kind -> 4 - hand.(kind)) in
  let waits, value =
    Heuristic.qualifying_stats ~melds:[] ~context:(context ()) ~unseen hand
  in
  Alcotest.(check bool) "wait scoring leaves counts unchanged" true (hand = before);
  Alcotest.(check int) "three unseen east tiles qualify" 3 waits;
  Alcotest.(check bool) "qualifying value is positive" true (value > 0)

let test_discard_does_not_reduce_unseen_copies () =
  let hand =
    counts
      [ "W1"; "W2"; "W3"; "W4"; "W5"; "W6"; "W7"; "W8"; "W9"; "B1"; "B2"; "B3"; "E"; "E" ]
  in
  let before = Array.copy hand in
  let unseen = Array.init Tile.standard_kind_count (fun kind -> 4 - hand.(kind)) in
  let choices =
    Heuristic.discard_choices ~meld_count:0 ~melds:[] ~context:(context ()) ~unseen
      ~score_waits:true hand
  in
  let east = List.find (fun choice -> choice.Heuristic.kind = Tile.of_string "E") choices in
  Alcotest.(check bool) "discard scoring leaves counts unchanged" true (hand = before);
  Alcotest.(check int) "discarding east leaves both unseen copies as ukeire" 2 east.ukeire;
  Alcotest.(check int) "discarding east leaves both unseen copies as qualifying waits" 2
    east.qualifying_waits

let play_random_game seed =
  let state = ref (State.initial seed 27) in
  let rng = Rng.create (seed lxor 0x5a5a5a) in
  let steps = ref 0 in
  while !steps < 2000 && (match !state.State.phase with State.Ended _ -> false | _ -> true) do
    match actor !state with
    | None -> failwith "non-terminal state has no actor"
    | Some seat ->
        let actions = Engine.legal_actions !state seat in
        if actions = [] then failwith ("empty legal action set at step " ^ string_of_int !steps);
        let action = List.nth actions (Rng.next_int rng (List.length actions)) in
        (match Engine.step !state seat action with
         | Error message -> failwith ("step failed: " ^ message ^ " action=" ^ Action.describe action ^ " step=" ^ string_of_int !steps)
         | Ok next ->
             state := next;
             (match State.validate !state with
              | Error message -> failwith ("state invariant failed: " ^ message ^ " step=" ^ string_of_int !steps)
              | Ok () -> ());
             incr steps)
  done;
  Alcotest.(check bool) ("game terminates seed " ^ string_of_int seed) true
    (match !state.phase with State.Ended _ -> true | _ -> false);
  !state

let test_random_games () =
  for seed = 1 to 20 do
    ignore (play_random_game seed)
  done

let play_heuristic_game seed =
  let state = ref (State.initial seed 27) in
  let steps = ref 0 in
  while !steps < 2000 && (match !state.State.phase with State.Ended _ -> false | _ -> true) do
    match actor !state with
    | None -> failwith "non-terminal state has no actor"
    | Some seat -> (
        match Heuristic.choose_action !state seat with
        | None -> failwith ("heuristic returned no action at step " ^ string_of_int !steps)
        | Some action -> (
            match Engine.step !state seat action with
            | Error message -> failwith ("heuristic action failed: " ^ message ^ " action=" ^ Action.describe action)
            | Ok next ->
                state := next;
                incr steps))
  done;
  Alcotest.(check bool) ("heuristic game terminates seed " ^ string_of_int seed) true
    (match !state.phase with State.Ended _ -> true | _ -> false)

let test_heuristic_games () =
  for seed = 1 to 12 do
    play_heuristic_game seed
  done

let test_observation_hides_other_hands () =
  let state = State.initial 24680 27 in
  let left = state.seats.(1).hand in
  let right = state.seats.(2).hand in
  let swapped_left = List.hd right :: List.tl left in
  let swapped_right = List.hd left :: List.tl right in
  let seats = Array.copy state.seats in
  seats.(1) <- { state.seats.(1) with hand = swapped_left };
  seats.(2) <- { state.seats.(2) with hand = swapped_right };
  let changed = { state with seats } in
  Alcotest.(check (result unit string)) "swapped state remains valid" (Ok ()) (State.validate changed);
  Alcotest.(check bool) "viewer observation ignores other concealed hands" true
    (Observation.create state 0 = Observation.create changed 0)

let test_observation_hides_live_kong_kind () =
  let kong = Meld.concealed_kong ~tile:(Tile.of_string "W1") ~instances:[] in
  let hidden = Observation.reveal_meld ~viewer:0 ~terminal_winner:None 1 kong in
  let own = Observation.reveal_meld ~viewer:1 ~terminal_winner:None 1 kong in
  let revealed = Observation.reveal_meld ~viewer:0 ~terminal_winner:(Some 1) 1 kong in
  Alcotest.(check bool) "opponent cannot see live concealed kong" true (hidden.tile = None);
  Alcotest.(check bool) "owner sees own concealed kong" true (own.tile = Some (Tile.of_string "W1"));
  Alcotest.(check bool) "winning owner kong is revealed at terminal state" true
    (revealed.tile = Some (Tile.of_string "W1"))

let test_observation_json () =
  let state = State.initial 1122 27 in
  let json = Observation_json.to_string state 0 |> Yojson.Safe.from_string in
  Alcotest.(check int) "observation version" 1
    (Yojson.Safe.Util.member "observation_version" json |> Yojson.Safe.Util.to_int);
  Alcotest.(check int) "action catalog size" Action_catalog.size
    (Yojson.Safe.Util.member "action_count" json |> Yojson.Safe.Util.to_int)

let test_known_counts_reference () =
  for seed = 0 to 19 do
    let state = ref (State.initial seed 27) in
    for _ = 0 to 120 do
      for seat = 0 to 3 do
        let expected = Array.init 34 (State.known_tile_count !state seat) in
        Alcotest.(check (array int)) "single-pass visibility matches reference"
          expected (State.known_tile_counts !state seat)
      done;
      match Observation.actor !state with
      | None -> ()
      | Some seat ->
          let action = Option.get (Heuristic.choose_action !state seat) in
          state := (match Engine.step !state seat action with Ok next -> next | Error e -> failwith e)
    done
  done

let test_shanten_cache_reference () =
  let rng = Rng.create 12000000 in
  for sample = 0 to 29999 do
    let meld_count = sample mod 5 in
    let hand = Array.make Tile.standard_kind_count 0 in
    for _ = 1 to 13 - (3 * meld_count) + (sample mod 2) do
      let rec draw () =
        let kind =
          if sample mod 3 = 0 then Rng.next_int rng 9
          else Rng.next_int rng Tile.standard_kind_count
        in
        if hand.(kind) >= 4 then draw ()
        else hand.(kind) <- hand.(kind) + 1
      in
      draw ()
    done;
    let before = Array.copy hand in
    let expected = Shanten.of_counts_uncached ~meld_count hand in
    Alcotest.(check int) "block frontier equals standard recursive reference"
      (Shanten.min_standard_reference ~meld_count hand)
      (Shanten.min_standard ~meld_count hand);
    Alcotest.(check int) "memoized result equals recursive reference" expected
      (Shanten.of_counts ~meld_count hand);
    let evaluator = Shanten.make_evaluator ~meld_count hand in
    Alcotest.(check int) "incremental initial equals reference" expected (Shanten.evaluate evaluator);
    if sample < 1000 then begin
      for kind = 0 to 33 do
        if hand.(kind) < 4 then begin
          hand.(kind) <- hand.(kind) + 1;
          Shanten.adjust evaluator kind 1;
          Alcotest.(check int) "incremental draw equals reference"
            (Shanten.of_counts_uncached ~meld_count hand) (Shanten.evaluate evaluator);
          hand.(kind) <- hand.(kind) - 1;
          Shanten.adjust evaluator kind (-1)
        end;
        if hand.(kind) > 0 then begin
          hand.(kind) <- hand.(kind) - 1;
          Shanten.adjust evaluator kind (-1);
          Alcotest.(check int) "incremental discard equals reference"
            (Shanten.of_counts_uncached ~meld_count hand) (Shanten.evaluate evaluator);
          hand.(kind) <- hand.(kind) + 1;
          Shanten.adjust evaluator kind 1
        end
      done;
      Alcotest.(check int) "incremental restored" expected (Shanten.evaluate evaluator)
    end;
    Array.fill hand 0 Tile.standard_kind_count 0;
    ignore (Shanten.of_counts ~meld_count hand);
    Alcotest.(check int) "key does not retain a mutable counts array" expected
      (Shanten.of_counts ~meld_count before)
  done;
  Alcotest.(check bool) "cache is bounded" true
    (Hashtbl.length Shanten.cache <= Shanten.cache_capacity)

let () =
  Alcotest.run "mahjong-core" [
    ( "tiles", [ Alcotest.test_case "physical inventory" `Quick test_physical_tiles ] );
    ( "wall", [ Alcotest.test_case "seeded wall" `Quick test_wall_seed ] );
    ( "shape", [
        Alcotest.test_case "normal hand" `Quick test_normal_win;
        Alcotest.test_case "special hands" `Quick test_special_wins;
        Alcotest.test_case "thirteen distinct false positive" `Quick test_thirteen_distinct_is_not_thirteen_orphans;
        Alcotest.test_case "knitted hands" `Quick test_knitted;
        Alcotest.test_case "fan threshold" `Quick test_fan_threshold;
        Alcotest.test_case "chicken hand" `Quick test_chicken_hand;
        Alcotest.test_case "all types" `Quick test_all_types;
        Alcotest.test_case "formal waits" `Quick test_formal_wait_fifth_copy;
        Alcotest.test_case "observation privacy" `Quick test_observation_hides_other_hands;
        Alcotest.test_case "concealed kong privacy" `Quick test_observation_hides_live_kong_kind;
        Alcotest.test_case "observation json" `Quick test_observation_json;
        Alcotest.test_case "known counts reference" `Quick test_known_counts_reference;
        Alcotest.test_case "action catalog" `Quick test_action_catalog;
        Alcotest.test_case "shanten" `Quick test_shanten;
        Alcotest.test_case "shanten cache reference" `Quick test_shanten_cache_reference;
        Alcotest.test_case "qualifying wait accounting" `Quick test_qualifying_wait_does_not_double_count;
        Alcotest.test_case "discard unseen accounting" `Quick test_discard_does_not_reduce_unseen_copies;
        Alcotest.test_case "heuristic games" `Slow test_heuristic_games;
        Alcotest.test_case "initial state" `Quick test_state_start;
        Alcotest.test_case "random playout" `Slow test_random_games;
      ] );
  ]
