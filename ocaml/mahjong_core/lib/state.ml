type draw_source = Initial | Wall_draw | Kong_replacement | Flower_replacement

type seat_state = {
  hand : int list;
  flowers : int list;
  melds : Meld.t list;
  river : int list;
}

type win_result = {
  winner : int;
  discarder : int option;
  winning_tile : int;
  evaluation : Fan.evaluation;
  deltas : int array;
}

type outcome = Win of win_result | Exhaustive_draw

type reaction_origin =
  | Discard_window of { discarder : int; discard : int }
  | Added_kong_window of { declarer : int; kind : Tile.t; fourth : int }

type window = {
  origin : reaction_origin;
  options : (int * Action.t list) list;
  decisions : (int * Action.t) list;
}

type phase =
  | Awaiting_discard of int
  | Awaiting_flower of int
  | Reactions of window
  | Ended of outcome

type logged_action = { seat : int; action : Action.t }

type t = {
  seed : int;
  revision : int;
  round_wind : Tile.t;
  phase : phase;
  seats : seat_state array;
  wall : Wall.t;
  drawn : int option;
  draw_source : draw_source;
  just_claimed_meld : bool;
  history : logged_action list;
}

let empty_seat = { hand = []; flowers = []; melds = []; river = [] }
let seat_wind seat = 27 + seat
let next_seat seat = (seat + 1) mod 4
let distance from_seat to_seat = (to_seat - from_seat + 4) mod 4

let count_kind instances kind =
  List.fold_left (fun total instance -> total + if Tile.instance_kind instance = kind then 1 else 0) 0 instances

let remove_instance instances instance =
  let rec loop prefix = function
    | [] -> None
    | current :: rest -> if current = instance then Some (List.rev_append prefix rest) else loop (current :: prefix) rest
  in
  loop [] instances

let remove_one_kind instances kind =
  let rec loop prefix = function
    | [] -> None
    | current :: rest ->
        if Tile.instance_kind current = kind then Some (current, List.rev_append prefix rest)
        else loop (current :: prefix) rest
  in
  loop [] instances

let remove_kind_n instances kinds =
  let rec loop remaining selected = function
    | [] -> if remaining = [] then Some (List.rev selected) else None
    | instance :: rest ->
        let kind = Tile.instance_kind instance in
        let rec remove_first = function
          | [] -> None
          | candidate :: tail -> if candidate = kind then Some tail else Option.map (fun tail' -> candidate :: tail') (remove_first tail)
        in
        (match remove_first remaining with
         | Some next -> loop next (instance :: selected) rest
         | None -> loop remaining selected rest)
  in
  loop kinds [] instances

let hand_counts seat =
  Tile_counts.of_instances
    (List.filter (fun instance -> Tile.is_standard_kind (Tile.instance_kind instance)) seat.hand)
let sorted_instances instances = List.sort compare instances

let known_tile_count state viewer kind =
  let public_melds =
    Array.to_list state.seats
    |> List.mapi (fun seat seat_state ->
           List.filter
             (fun meld -> seat = viewer || not meld.Meld.concealed)
             seat_state.melds)
    |> List.concat
  in
  let visible_rivers = List.concat_map (fun seat_state -> seat_state.river) (Array.to_list state.seats) in
  let own_hand = state.seats.(viewer).hand in
  let counts =
    List.fold_left (fun total instance -> total + if Tile.instance_kind instance = kind then 1 else 0)
      0
      (own_hand @ visible_rivers @ List.concat_map (fun meld -> meld.Meld.instances) public_melds)
  in
  counts

(* Same visibility as known_tile_count, collected in one pass. *)
let known_tile_counts state viewer =
  let counts = Tile_counts.empty () in
  let add instance =
    let kind = Tile.instance_kind instance in
    if Tile.is_standard_kind kind then counts.(kind) <- counts.(kind) + 1
  in
  List.iter add state.seats.(viewer).hand;
  Array.iteri (fun owner seat ->
      List.iter add seat.river;
      List.iter (fun meld ->
          if owner = viewer || not meld.Meld.concealed then
            List.iter add meld.instances) seat.melds) state.seats;
  counts

let validate state =
  let owners = Array.make Tile.physical_tile_count (-1) in
  let error = ref None in
  let mark zone instance =
    if instance < 0 || instance >= Tile.physical_tile_count then error := Some "tile instance out of range"
    else if owners.(instance) <> -1 then error := Some ("duplicate physical tile " ^ string_of_int instance)
    else owners.(instance) <- zone
  in
  Array.iter (fun instance -> mark 0 instance) (Wall.remaining_tiles state.wall);
  Array.iteri
    (fun seat seat_state ->
      List.iter (mark (10 + seat)) seat_state.hand;
      List.iter (mark (20 + seat)) seat_state.flowers;
      List.iter (fun meld -> List.iter (mark (30 + seat)) meld.Meld.instances) seat_state.melds;
      List.iter (mark (40 + seat)) seat_state.river)
    state.seats;
  if Array.exists (( = ) (-1)) owners then error := Some "physical tile missing from all zones";
  match !error with None -> Ok () | Some message -> Error message

let ensure_valid state =
  match validate state with Ok () -> state | Error message -> invalid_arg ("invalid mahjong state: " ^ message)

let phase_seat = function
  | Awaiting_discard seat | Awaiting_flower seat -> Some seat
  | Reactions window -> (
      match window.origin with
      | Discard_window { discarder; _ } -> Some discarder
      | Added_kong_window { declarer; _ } -> Some declarer)
  | Ended _ -> None

let current_seat state = phase_seat state.phase

let add_instances seat instances =
  { seat with hand = sorted_instances (seat.hand @ instances) }

let draw_tile wall back =
  if back then Wall.take_back wall else Wall.take_front wall

let rec expose_initial_flowers seat_state wall =
  match List.find_opt (fun instance -> Tile.is_flower (Tile.instance_kind instance)) seat_state.hand with
  | None -> seat_state, wall, None
  | Some flower -> (
      match Wall.take_back wall with
      | None -> invalid_arg "wall exhausted during initial flower replacement"
      | Some (replacement, wall) ->
          let seat_state =
            {
              seat_state with
              hand = sorted_instances (replacement :: List.filter (( <> ) flower) seat_state.hand);
              flowers = sorted_instances (flower :: seat_state.flowers);
            }
          in
          let final_state, final_wall, _ = expose_initial_flowers seat_state wall in
          final_state, final_wall, Some replacement)

let initial seed round_wind =
  if round_wind < 27 || round_wind > 30 then invalid_arg "round wind must be East, South, West or North";
  let wall = ref (Wall.create seed) in
  let seats = Array.init 4 (fun _ -> empty_seat) in
  let draw_front () =
    match Wall.take_front !wall with
    | None -> invalid_arg "wall exhausted while dealing"
    | Some (tile, next) -> wall := next; tile
  in
  for _round = 1 to 3 do
    for seat = 0 to 3 do
      seats.(seat) <- add_instances seats.(seat) (List.init 4 (fun _ -> draw_front ()))
    done
  done;
  seats.(0) <- add_instances seats.(0) (List.init 2 (fun _ -> draw_front ()));
  for seat = 1 to 3 do
    seats.(seat) <- add_instances seats.(seat) [ draw_front () ]
  done;
  let dealer_last = ref (List.hd (seats.(0).hand)) in
  for seat = 0 to 3 do
    let replaced, next_wall, _ = expose_initial_flowers seats.(seat) !wall in
    seats.(seat) <- replaced;
    wall := next_wall
  done;
  let dealer_flowers = seats.(0).hand |> List.filter (fun instance -> not (Tile.is_flower (Tile.instance_kind instance))) in
  if dealer_flowers <> [] then dealer_last := List.hd dealer_flowers;
  let state =
    {
      seed;
      revision = 0;
      round_wind;
      phase = Awaiting_discard 0;
      seats;
      wall = !wall;
      drawn = Some !dealer_last;
      draw_source = Initial;
      just_claimed_meld = false;
      history = [];
    }
  in
  ensure_valid state

let update_seat state seat value =
  let seats = Array.copy state.seats in
  seats.(seat) <- value;
  { state with seats }

let with_revision state =
  { state with revision = state.revision + 1 }

let with_history state seat action =
  { state with history = { seat; action } :: state.history }

let payments ~winner ~discarder ~fan =
  let deltas = Array.make 4 0 in
  (match discarder with
   | Some loser ->
       for seat = 0 to 3 do
         if seat <> winner then deltas.(seat) <- -8
       done;
       deltas.(loser) <- -(fan + 8);
       deltas.(winner) <- fan + 24
   | None ->
       let payment = fan + 8 in
       for seat = 0 to 3 do
         if seat <> winner then deltas.(seat) <- -payment
       done;
       deltas.(winner) <- payment * 3);
  deltas

let finish_win state ~winner ~discarder ~winning_tile ~evaluation =
  let fan = evaluation.Fan.total_fan in
  let outcome =
    Win
      {
        winner;
        discarder;
        winning_tile;
        evaluation;
        deltas = payments ~winner ~discarder ~fan;
      }
  in
  with_revision { state with phase = Ended outcome; drawn = None }

let end_draw state = with_revision { state with phase = Ended Exhaustive_draw; drawn = None }
