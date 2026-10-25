let version = 1

type meld_view = {
  owner : int;
  kind : Meld.kind;
  tile : Tile.t option;
  concealed : bool;
  claimed_from : int option;
}

type phase_view =
  | Awaiting_discard of int
  | Awaiting_flower of int
  | Awaiting_response of { discarder : int; discard_kind : Tile.t }
  | Ended of State.outcome

type t = {
  seat : int;
  seat_wind : Tile.t;
  round_wind : Tile.t;
  hand : int list;
  drawn_kind : Tile.t option;
  concealed_counts : int array;
  own_flowers : int list;
  flower_counts : int array;
  all_melds : meld_view array array;
  rivers : int list array;
  known_counts : int array;
  wall_remaining : int;
  revision : int;
  phase : phase_view;
  legal_actions : Action.t list;
}

let meld_claimed_from meld =
  match meld.Meld.origin with
  | Meld.Claimed { discarder; _ } -> Some discarder
  | Meld.Concealed | Meld.Added _ -> None

let reveal_meld ~viewer ~terminal_winner owner meld =
  let reveal_tile = owner = viewer || Some owner = terminal_winner || not meld.Meld.concealed in
  {
    owner;
    kind = meld.kind;
    tile = if reveal_tile then Some meld.tile else None;
    concealed = meld.concealed;
    claimed_from = meld_claimed_from meld;
  }

let phase_view state =
  match state.State.phase with
  | State.Awaiting_discard seat -> Awaiting_discard seat
  | State.Awaiting_flower seat -> Awaiting_flower seat
  | State.Reactions { origin = State.Discard_window { discarder; discard }; _ } ->
      Awaiting_response { discarder; discard_kind = Tile.instance_kind discard }
  | State.Reactions { origin = State.Added_kong_window { declarer; kind; _ }; _ } ->
      Awaiting_response { discarder = declarer; discard_kind = kind }
  | State.Ended outcome -> Ended outcome

let meld_kind_tiles ~kind ~tile =
  match kind with
  | Meld.Chow -> [ tile - 1; tile; tile + 1 ]
  | Meld.Pung -> [ tile; tile; tile ]
  | Meld.Kong -> [ tile; tile; tile; tile ]

let known_counts ~seat ~hand ~rivers ~all_melds =
  let add_instance counts instance =
    let kind = Tile.instance_kind instance in
    if Tile.is_standard_kind kind then counts.(kind) <- counts.(kind) + 1
  in
  let counts = Tile_counts.empty () in
  List.iter (fun instance -> add_instance counts instance) hand;
  Array.iter (fun river -> List.iter (fun instance -> add_instance counts instance) river) rivers;
  Array.iter
    (fun melds ->
      Array.iter
        (fun meld ->
          match meld.tile with
          | None -> ()
          | Some tile ->
              List.iter
                (fun kind -> counts.(kind) <- counts.(kind) + 1)
                (meld_kind_tiles ~kind:meld.kind ~tile))
        melds)
    all_melds;
  counts

let create state seat =
  if seat < 0 || seat > 3 then invalid_arg "seat must be in 0..3";
  let terminal_winner =
    match state.State.phase with State.Ended (State.Win win) -> Some win.winner | _ -> None
  in
  let all_melds =
    Array.init 4 (fun owner ->
        Array.of_list
          (List.map (reveal_meld ~viewer:seat ~terminal_winner owner) state.seats.(owner).melds))
  in
  let rivers = Array.init 4 (fun owner -> state.seats.(owner).river) in
  {
    seat;
    seat_wind = State.seat_wind seat;
    round_wind = state.round_wind;
    hand = state.seats.(seat).hand;
    drawn_kind = Option.map Tile.instance_kind state.drawn;
    concealed_counts = State.hand_counts state.seats.(seat);
    own_flowers = List.map Tile.instance_kind state.seats.(seat).flowers;
    flower_counts = Array.init 4 (fun owner -> List.length state.seats.(owner).flowers);
    all_melds;
    rivers;
    known_counts = known_counts ~seat ~hand:state.seats.(seat).hand ~rivers ~all_melds;
    wall_remaining = Wall.remaining state.wall;
    revision = state.revision;
    phase = phase_view state;
    legal_actions = Engine.legal_actions state seat;
  }

let actor state =
  match state.State.phase with
  | State.Awaiting_discard seat | State.Awaiting_flower seat -> Some seat
  | State.Reactions window ->
      window.options
      |> List.find_map (fun (seat, _) ->
             if List.exists (fun (decided, _) -> decided = seat) window.decisions then None
             else Some seat)
  | State.Ended _ -> None
