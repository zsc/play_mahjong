type t =
  | Big_four_winds
  | Big_three_dragons
  | All_green
  | Nine_gates
  | Four_kongs
  | Seven_shifted_pairs
  | Thirteen_orphans
  | All_terminals
  | Little_four_winds
  | Little_three_dragons
  | All_honors
  | Four_concealed_pungs
  | Pure_terminal_chows
  | Quadruple_chow
  | Four_pure_shifted_pungs
  | Four_pure_shifted_chows
  | Three_kongs
  | All_terminals_and_honors
  | Seven_pairs
  | Greater_honors_and_knitted_tiles
  | All_even_pungs
  | Full_flush
  | Pure_triple_chow
  | Pure_shifted_pungs
  | Upper_tiles
  | Middle_tiles
  | Lower_tiles
  | Pure_straight
  | Three_suited_terminal_chows
  | Pure_shifted_chows
  | All_fives
  | Triple_pung
  | Three_concealed_pungs
  | Lesser_honors_and_knitted_tiles
  | Knitted_straight
  | Upper_five
  | Lower_five
  | Big_three_winds
  | Mixed_straight
  | Reversible_tiles
  | Mixed_triple_chow
  | Mixed_shifted_pungs
  | Chicken_hand
  | Last_tile_draw
  | Last_tile_claim
  | Out_with_replacement_tile
  | Robbing_the_kong
  | Two_concealed_kongs
  | All_pungs
  | Half_flush
  | Mixed_shifted_chows
  | All_types
  | Melded_hand
  | Two_dragons_pungs
  | Outside_hand
  | Fully_concealed_hand
  | Two_melded_kongs
  | Last_tile
  | Dragon_pung
  | Prevalent_wind
  | Seat_wind
  | Concealed_hand
  | All_chows
  | Tile_hog
  | Double_pung
  | Two_concealed_pungs
  | Concealed_kong
  | All_simples
  | Pure_double_chow
  | Mixed_double_chow
  | Short_straight
  | Two_terminal_chows
  | Terminal_or_honor_pung
  | Melded_kong
  | One_voided_suit
  | No_honors
  | Edge_wait
  | Closed_wait
  | Single_wait
  | Self_drawn
  | Flower_tiles

let points = function
  | Big_four_winds | Big_three_dragons | All_green | Nine_gates | Four_kongs
  | Seven_shifted_pairs | Thirteen_orphans -> 88
  | All_terminals | Little_four_winds | Little_three_dragons | All_honors
  | Four_concealed_pungs | Pure_terminal_chows -> 64
  | Quadruple_chow | Four_pure_shifted_pungs -> 48
  | Four_pure_shifted_chows | Three_kongs | All_terminals_and_honors -> 32
  | Seven_pairs | Greater_honors_and_knitted_tiles | All_even_pungs | Full_flush
  | Pure_triple_chow | Pure_shifted_pungs | Upper_tiles | Middle_tiles
  | Lower_tiles -> 24
  | Pure_straight | Three_suited_terminal_chows | Pure_shifted_chows | All_fives
  | Triple_pung | Three_concealed_pungs -> 16
  | Lesser_honors_and_knitted_tiles | Knitted_straight | Upper_five | Lower_five
  | Big_three_winds -> 12
  | Mixed_straight | Reversible_tiles | Mixed_triple_chow | Mixed_shifted_pungs | Chicken_hand
  | Last_tile_draw | Last_tile_claim | Out_with_replacement_tile | Robbing_the_kong -> 8
  | Two_concealed_kongs | All_pungs | Half_flush | Mixed_shifted_chows
  | All_types | Melded_hand | Two_dragons_pungs -> 6
  | Outside_hand | Fully_concealed_hand | Two_melded_kongs | Last_tile -> 4
  | Dragon_pung | Prevalent_wind | Seat_wind | Concealed_hand | All_chows
  | Tile_hog | Double_pung | Two_concealed_pungs | Concealed_kong | All_simples -> 2
  | Pure_double_chow | Mixed_double_chow | Short_straight | Two_terminal_chows
  | Terminal_or_honor_pung | Melded_kong | One_voided_suit | No_honors
  | Edge_wait | Closed_wait | Single_wait | Self_drawn | Flower_tiles -> 1

let name = function
  | Big_four_winds -> "Big Four Winds"
  | Big_three_dragons -> "Big Three Dragons"
  | All_green -> "All Green"
  | Nine_gates -> "Nine Gates"
  | Four_kongs -> "Four Kongs"
  | Seven_shifted_pairs -> "Seven Shifted Pairs"
  | Thirteen_orphans -> "Thirteen Orphans"
  | All_terminals -> "All Terminals"
  | Little_four_winds -> "Little Four Winds"
  | Little_three_dragons -> "Little Three Dragons"
  | All_honors -> "All Honors"
  | Four_concealed_pungs -> "Four Concealed Pungs"
  | Pure_terminal_chows -> "Pure Terminal Chows"
  | Quadruple_chow -> "Quadruple Chow"
  | Four_pure_shifted_pungs -> "Four Pure Shifted Pungs"
  | Four_pure_shifted_chows -> "Four Pure Shifted Chows"
  | Three_kongs -> "Three Kongs"
  | All_terminals_and_honors -> "All Terminals and Honors"
  | Seven_pairs -> "Seven Pairs"
  | Greater_honors_and_knitted_tiles -> "Greater Honors and Knitted Tiles"
  | All_even_pungs -> "All Even Pungs"
  | Full_flush -> "Full Flush"
  | Pure_triple_chow -> "Pure Triple Chow"
  | Pure_shifted_pungs -> "Pure Shifted Pungs"
  | Upper_tiles -> "Upper Tiles"
  | Middle_tiles -> "Middle Tiles"
  | Lower_tiles -> "Lower Tiles"
  | Pure_straight -> "Pure Straight"
  | Three_suited_terminal_chows -> "Three-Suited Terminal Chows"
  | Pure_shifted_chows -> "Pure Shifted Chows"
  | All_fives -> "All Fives"
  | Triple_pung -> "Triple Pung"
  | Three_concealed_pungs -> "Three Concealed Pungs"
  | Lesser_honors_and_knitted_tiles -> "Lesser Honors and Knitted Tiles"
  | Knitted_straight -> "Knitted Straight"
  | Upper_five -> "Upper Five"
  | Lower_five -> "Lower Five"
  | Big_three_winds -> "Big Three Winds"
  | Mixed_straight -> "Mixed Straight"
  | Reversible_tiles -> "Reversible Tiles"
  | Mixed_triple_chow -> "Mixed Triple Chow"
  | Mixed_shifted_pungs -> "Mixed Shifted Pungs"
  | Chicken_hand -> "Chicken Hand"
  | Last_tile_draw -> "Last Tile Draw"
  | Last_tile_claim -> "Last Tile Claim"
  | Out_with_replacement_tile -> "Out with Replacement Tile"
  | Robbing_the_kong -> "Robbing the Kong"
  | Two_concealed_kongs -> "Two Concealed Kongs"
  | All_pungs -> "All Pungs"
  | Half_flush -> "Half Flush"
  | Mixed_shifted_chows -> "Mixed Shifted Chows"
  | All_types -> "All Types"
  | Melded_hand -> "Melded Hand"
  | Two_dragons_pungs -> "Two Dragons Pungs"
  | Outside_hand -> "Outside Hand"
  | Fully_concealed_hand -> "Fully Concealed Hand"
  | Two_melded_kongs -> "Two Melded Kongs"
  | Last_tile -> "Last Tile"
  | Dragon_pung -> "Dragon Pung"
  | Prevalent_wind -> "Prevalent Wind"
  | Seat_wind -> "Seat Wind"
  | Concealed_hand -> "Concealed Hand"
  | All_chows -> "All Chows"
  | Tile_hog -> "Tile Hog"
  | Double_pung -> "Double Pung"
  | Two_concealed_pungs -> "Two Concealed Pungs"
  | Concealed_kong -> "Concealed Kong"
  | All_simples -> "All Simples"
  | Pure_double_chow -> "Pure Double Chow"
  | Mixed_double_chow -> "Mixed Double Chow"
  | Short_straight -> "Short Straight"
  | Two_terminal_chows -> "Two Terminal Chows"
  | Terminal_or_honor_pung -> "Pung of Terminals or Honors"
  | Melded_kong -> "Melded Kong"
  | One_voided_suit -> "One Voided Suit"
  | No_honors -> "No Honors"
  | Edge_wait -> "Edge Wait"
  | Closed_wait -> "Closed Wait"
  | Single_wait -> "Single Wait"
  | Self_drawn -> "Self-Drawn"
  | Flower_tiles -> "Flower Tiles"

type win_method = Self_draw | Discard

type flags = {
  after_kong : bool;
  last_tile : bool;
  robbing_kong : bool;
  last_of_kind : bool;
}

let no_flags =
  { after_kong = false; last_tile = false; robbing_kong = false; last_of_kind = false }

type context = {
  seat_wind : int;
  round_wind : int;
  win_method : win_method;
  flowers : int;
  flags : flags;
}

type award = { fan : t; count : int }

type evaluation = {
  winning : bool;
  qualifying_fan : int;
  flower_fan : int;
  total_fan : int;
  internal_points : int;
  awards : award list;
}

let not_winning =
  {
    winning = false;
    qualifying_fan = 0;
    flower_fan = 0;
    total_fan = 0;
    internal_points = 0;
    awards = [];
  }

type entry = { awarded : t; evidence : int list }

type acc = {
  mutable entries : entry list;
  mutable exclusions : entry list;
  mutable internal : int;
}

let add ?(evidence = []) acc fan =
  let entry = { awarded = fan; evidence } in
  if not (List.exists (( = ) entry) acc.entries) then
    acc.entries <- entry :: acc.entries

let add_internal acc points = acc.internal <- acc.internal + points
let exclude ?(evidence = []) acc fan =
  let entry = { awarded = fan; evidence } in
  if not (List.exists (( = ) entry) acc.exclusions) then
    acc.exclusions <- entry :: acc.exclusions

let has acc fan = List.exists (fun entry -> entry.awarded = fan) acc.entries
let clear_exclusions acc fan =
  acc.exclusions <- List.filter (fun entry -> entry.awarded <> fan) acc.exclusions

let force_one acc fan =
  clear_exclusions acc fan;
  acc.entries <- List.filter (fun entry -> entry.awarded <> fan) acc.entries;
  acc.entries <- { awarded = fan; evidence = [] } :: acc.entries

let finish acc =
  let entries =
    List.filter
      (fun entry -> not (List.exists (( = ) entry) acc.exclusions))
      acc.entries
  in
  let counts =
    List.fold_left
      (fun result entry ->
        match List.assoc_opt entry.awarded result with
        | None -> (entry.awarded, 1) :: result
        | Some count -> (entry.awarded, count + 1) :: List.remove_assoc entry.awarded result)
      [] entries
    |> List.sort (fun (left, _) (right, _) -> compare left right)
  in
  let fan_points =
    List.fold_left (fun total (fan, count) -> total + (points fan * count)) 0 counts
  in
  let qualifying = fan_points + acc.internal in
  let counts =
    if qualifying = 0 then [ (Chicken_hand, 1) ] else counts
  in
  let qualifying = if qualifying = 0 then points Chicken_hand else qualifying in
  let awards = List.map (fun (fan, count) -> { fan; count }) counts in
  {
    winning = qualifying >= 8;
    qualifying_fan = qualifying;
    flower_fan = 0;
    total_fan = qualifying;
    internal_points = acc.internal;
    awards;
  }

let physical_counts after melds =
  let counts = Array.copy after in
  List.iter
    (fun meld ->
      List.iter
        (fun kind -> counts.(kind) <- counts.(kind) + 1)
        (Meld.kind_tiles meld))
    melds;
  counts

let is_pair group = group.Shape.kind = Shape.Pair
let is_pung group = group.Shape.kind = Shape.Pung
let is_kong group = group.Shape.kind = Shape.Kong
let is_chow group = group.Shape.kind = Shape.Chow
let is_triplet group = is_pung group || is_kong group
let tile_kinds counts =
  List.filter (fun kind -> counts.(kind) > 0) (List.init Tile.standard_kind_count Fun.id)

let all_tiles counts predicate =
  let any = ref false in
  let valid = ref true in
  Array.iteri
    (fun kind count ->
      if count > 0 then begin
        any := true;
        if not (predicate kind) then valid := false
      end)
    counts;
  !any && !valid

let has_tile counts predicate =
  let found = ref false in
  Array.iteri
    (fun kind count -> if count > 0 && predicate kind then found := true)
    counts;
  !found

let all_groups groups predicate = List.for_all predicate groups
let group_at groups index = List.nth groups index
let indices count = List.init count Fun.id

let suit_index kind =
  if kind < 9 then 0 else if kind < 18 then 1 else if kind < 27 then 2 else 3

let is_green kind = kind = 10 || kind = 11 || kind = 12 || kind = 14 || kind = 16 || kind = 32

let is_reversible kind =
  match kind with
  | 10 | 12 | 13 | 14 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 25 | 26 | 33 -> true
  | _ -> false

let all_numeral_kinds counts predicate =
  all_tiles counts (fun kind -> Tile.is_numbered kind && predicate kind)

let all_numbers_in_one_suit counts =
  let suit = ref (-1) in
  let ok = ref true in
  Array.iteri
    (fun kind count ->
      if count > 0 then
        if not (Tile.is_numbered kind) then ok := false
        else if !suit < 0 then suit := suit_index kind
        else if !suit <> suit_index kind then ok := false)
    counts;
  !ok && !suit >= 0

let half_flush counts =
  let suit = ref (-1) in
  let numbered = ref false in
  let honor = ref false in
  let ok = ref true in
  Array.iteri
    (fun kind count ->
      if count > 0 then
        if Tile.is_honor kind then honor := true
        else begin
          numbered := true;
          if !suit < 0 then suit := suit_index kind
          else if !suit <> suit_index kind then ok := false
        end)
    counts;
  !ok && !numbered && !honor

let numbered_suit_count counts =
  let suits = Array.make 3 false in
  for kind = 0 to 26 do
    if counts.(kind) > 0 then suits.(kind / 9) <- true
  done;
  Array.fold_left (fun total present -> total + if present then 1 else 0) 0 suits

let has_all_five_gates counts =
  let gates = Array.make 5 false in
  Array.iteri
    (fun kind count ->
      if count > 0 then
        if Tile.is_numbered kind then gates.(suit_index kind) <- true
        else if Tile.is_wind kind then gates.(3) <- true
        else if Tile.is_dragon kind then gates.(4) <- true)
    counts;
  Array.for_all Fun.id gates

let is_nine_gates concealed_before melds =
  melds = []
  &&
  let ok = ref false in
  for suit = 0 to 2 do
    let base = suit * 9 in
    let matches =
      concealed_before.(base) = 3 && concealed_before.(base + 8) = 3
      && (let valid = ref true in
          for rank = 1 to 7 do
            if concealed_before.(base + rank) <> 1 then valid := false
          done;
          !valid)
    in
    let outside = ref true in
    Array.iteri
      (fun kind count ->
        if count > 0 && (kind < base || kind > base + 8) then outside := false)
      concealed_before;
    if matches && !outside then ok := true
  done;
  !ok

let contains_pattern counts pattern =
  Array.for_all (fun kind -> counts.(kind) > 0) pattern

let first_knitted_pattern counts =
  let result = ref None in
  Array.iteri
    (fun index pattern -> if !result = None && contains_pattern counts pattern then result := Some index)
    Shape.knitted_patterns;
  !result

let formal_waits concealed_before melds =
  let before = Array.copy concealed_before in
  let physical = physical_counts concealed_before melds in
  let waits = ref [] in
  for kind = 0 to Tile.standard_kind_count - 1 do
    if physical.(kind) < 4 then begin
      before.(kind) <- before.(kind) + 1;
      if Shape.winning_shape ~concealed_before ~melds ~winning:kind then waits := kind :: !waits;
      before.(kind) <- before.(kind) - 1
    end
  done;
  List.rev !waits

let formal_wait_count concealed_before melds = List.length (formal_waits concealed_before melds)

let count_overall ?(nine_gates = false) counts ~groups ~knitted ~context acc =
  if not knitted then begin
    if all_tiles counts is_green then begin
      add acc All_green;
      exclude acc Half_flush
    end;
    if nine_gates then begin
      add acc Nine_gates;
      exclude acc Full_flush;
      exclude acc Fully_concealed_hand;
      exclude acc Concealed_hand;
      exclude acc No_honors;
      List.iteri
        (fun index group ->
          if is_triplet group && Tile.is_terminal group.Shape.tile then
            exclude ~evidence:[ index ] acc Terminal_or_honor_pung)
        groups
    end;
    if all_tiles counts Tile.is_terminal then begin
      add acc All_terminals;
      exclude acc All_pungs;
      exclude acc Outside_hand;
      exclude acc No_honors;
      List.iteri
        (fun left_index left ->
          List.iteri
            (fun right_index right ->
              if
                right_index > left_index
                && is_triplet left
                && is_triplet right
                && Tile.rank left.Shape.tile = Tile.rank right.Shape.tile
              then
                exclude ~evidence:[ left_index; right_index ] acc Double_pung)
            groups)
        groups;
      List.iteri
        (fun index group ->
          if is_triplet group && Tile.is_terminal_or_honor group.Shape.tile then
            exclude ~evidence:[ index ] acc Terminal_or_honor_pung)
        groups
    end;
    if all_tiles counts Tile.is_honor then begin
      add acc All_honors;
      exclude acc All_pungs;
      exclude acc Outside_hand;
      List.iteri
        (fun index group ->
          if is_triplet group && Tile.is_terminal_or_honor group.Shape.tile then
            exclude ~evidence:[ index ] acc Terminal_or_honor_pung)
        groups
    end;
    if
      has_tile counts Tile.is_terminal
      && has_tile counts Tile.is_honor
      && all_tiles counts Tile.is_terminal_or_honor
    then begin
      add acc All_terminals_and_honors;
      exclude acc All_pungs;
      exclude acc Outside_hand;
      List.iteri
        (fun index group ->
          if is_triplet group && Tile.is_terminal_or_honor group.Shape.tile then
            exclude ~evidence:[ index ] acc Terminal_or_honor_pung)
        groups
    end;
    if
      List.length groups = 5
      && all_groups groups (fun group ->
             (is_triplet group || is_pair group)
             && Tile.is_numbered group.Shape.tile
             && Tile.rank group.Shape.tile mod 2 = 0)
    then begin
      add acc All_even_pungs;
      exclude acc All_pungs;
      exclude acc All_simples;
      exclude acc No_honors
    end;
    if all_numbers_in_one_suit counts then begin
      add acc Full_flush;
      exclude acc No_honors
    end;
    if all_numeral_kinds counts (fun kind -> Tile.rank kind >= 7) then begin
      add acc Upper_tiles;
      exclude acc Upper_five;
      exclude acc No_honors
    end;
    if all_numeral_kinds counts (fun kind -> Tile.rank kind >= 4 && Tile.rank kind <= 6) then begin
      add acc Middle_tiles;
      exclude acc All_simples;
      exclude acc No_honors
    end;
    if all_numeral_kinds counts (fun kind -> Tile.rank kind <= 3) then begin
      add acc Lower_tiles;
      exclude acc Lower_five;
      exclude acc No_honors
    end;
    if
      List.length groups = 5
      && all_groups groups (fun group ->
             let tile = group.Shape.tile in
             if is_chow group then Tile.rank tile >= 4 && Tile.rank tile <= 6
             else (is_triplet group || is_pair group) && Tile.rank tile = 5)
    then begin
      add acc All_fives;
      exclude acc All_simples;
      exclude acc No_honors
    end;
    if all_numeral_kinds counts (fun kind -> Tile.rank kind >= 6) then begin
      add acc Upper_five;
      exclude acc No_honors
    end;
    if all_numeral_kinds counts (fun kind -> Tile.rank kind <= 4) then begin
      add acc Lower_five;
      exclude acc No_honors
    end;
    if all_tiles counts is_reversible then begin
      add acc Reversible_tiles;
      exclude acc One_voided_suit
    end;
    if List.length groups = 5 && all_groups groups (fun group -> is_triplet group || is_pair group) then
      add acc All_pungs;
    if half_flush counts then add acc Half_flush;
    if
      List.length groups = 5
      && all_groups groups (fun group ->
             let tile = group.Shape.tile in
             if is_chow group then Tile.rank tile = 2 || Tile.rank tile = 8
             else (is_triplet group || is_pair group) && Tile.is_terminal_or_honor tile)
    then add acc Outside_hand;
    if all_numeral_kinds counts (fun kind -> not (Tile.is_terminal kind)) then begin
      add acc All_simples;
      exclude acc No_honors
    end;
    if numbered_suit_count counts = 2 then add acc One_voided_suit
  end;
  if has_all_five_gates counts then add acc All_types;
  if
    List.length groups <> 7
    && groups <> []
    && all_groups groups (fun group ->
           is_chow group || (is_pair group && Tile.is_numbered group.Shape.tile))
  then begin
    add acc All_chows;
    exclude acc No_honors
  end;
  List.iter
    (fun kind ->
      let judged_as_kong =
        List.exists (fun group -> is_kong group && group.Shape.tile = kind) groups
      in
      if counts.(kind) = 4 && not judged_as_kong then add acc Tile_hog)
    (tile_kinds counts);
  if not (has_tile counts Tile.is_honor) then add acc No_honors

let count_kongs groups acc =
  let concealed_kongs = List.filter (fun index -> is_kong (group_at groups index) && (group_at groups index).Shape.concealed) (indices (List.length groups)) in
  let melded_kongs = List.filter (fun index -> is_kong (group_at groups index) && not (group_at groups index).Shape.concealed) (indices (List.length groups)) in
  let concealed_pungs =
    List.filter
      (fun index -> is_pung (group_at groups index) && (group_at groups index).Shape.concealed)
      (indices (List.length groups))
  in
  let concealed = List.length concealed_kongs in
  let melded = List.length melded_kongs in
  let pungs = List.length concealed_pungs in
  let key = (concealed * 100) + (melded * 10) + pungs in
  let add_ids fan ids = add ~evidence:ids acc fan in
  let combined first second = first @ second in
  begin
    match key with
    | 400 -> add_ids Four_kongs concealed_kongs; add_ids Four_concealed_pungs concealed_kongs
    | 310 -> add_ids Four_kongs (combined concealed_kongs melded_kongs); add_ids Three_concealed_pungs concealed_kongs
    | 220 -> add_ids Four_kongs (combined concealed_kongs melded_kongs); add_ids Two_concealed_pungs concealed_kongs
    | 130 -> add_ids Four_kongs (combined concealed_kongs melded_kongs)
    | 301 -> add_ids Three_kongs concealed_kongs; add_ids Four_concealed_pungs (combined concealed_kongs concealed_pungs)
    | 300 -> add_ids Three_kongs concealed_kongs; add_ids Three_concealed_pungs concealed_kongs
    | 211 -> add_ids Three_kongs (combined concealed_kongs melded_kongs); add_ids Three_concealed_pungs (combined concealed_kongs concealed_pungs)
    | 210 -> add_ids Three_kongs (combined concealed_kongs melded_kongs); add_ids Two_concealed_pungs concealed_kongs
    | 121 ->
        add_ids Three_kongs (combined concealed_kongs melded_kongs);
        add_ids Two_concealed_pungs [ List.hd concealed_kongs; List.hd concealed_pungs ]
    | 120 -> add_ids Three_kongs (combined concealed_kongs melded_kongs)
    | 202 -> add_ids Two_concealed_kongs concealed_kongs; add_ids Four_concealed_pungs (combined concealed_kongs concealed_pungs)
    | 201 -> add_ids Two_concealed_kongs concealed_kongs; add_ids Three_concealed_pungs (combined concealed_kongs concealed_pungs)
    | 112 ->
        add_internal acc 6;
        add_ids Three_concealed_pungs
          [ List.hd concealed_kongs; List.nth concealed_pungs 0; List.nth concealed_pungs 1 ]
    | 111 ->
        add_internal acc 6;
        add_ids Two_concealed_pungs [ List.hd concealed_kongs; List.hd concealed_pungs ]
    | 22 ->
        add_ids Two_melded_kongs melded_kongs;
        add_ids Two_concealed_pungs concealed_pungs
    | 103 -> add_ids Concealed_kong concealed_kongs; add_ids Four_concealed_pungs (combined concealed_kongs concealed_pungs)
    | 102 -> add_ids Concealed_kong concealed_kongs; add_ids Three_concealed_pungs (combined concealed_kongs concealed_pungs)
    | 101 -> add_ids Concealed_kong concealed_kongs; add_ids Two_concealed_pungs (combined concealed_kongs concealed_pungs)
    | 13 -> add_ids Melded_kong melded_kongs; add_ids Three_concealed_pungs concealed_pungs
    | 12 -> add_ids Melded_kong melded_kongs; add_ids Two_concealed_pungs concealed_pungs
    | _ ->
        if melded = 4 then add_ids Four_kongs melded_kongs
        else if pungs = 4 then add_ids Four_concealed_pungs concealed_pungs
        else if melded = 3 then add_ids Three_kongs melded_kongs
        else if pungs = 3 then add_ids Three_concealed_pungs concealed_pungs
        else if concealed = 2 then add_ids Two_concealed_kongs concealed_kongs
        else if melded = 2 then add_ids Two_melded_kongs melded_kongs
        else if pungs = 2 then add_ids Two_concealed_pungs concealed_pungs
        else if melded = 1 && concealed = 1 then add_internal acc 6
        else if concealed = 1 then add_ids Concealed_kong concealed_kongs
        else if melded = 1 then add_ids Melded_kong melded_kongs
  end;
  if has acc Four_kongs then begin
    exclude acc All_pungs;
    List.iteri
      (fun index group -> if is_pair group then exclude ~evidence:[ index ] acc Single_wait)
      groups
  end;
  if has acc Two_concealed_kongs then
    exclude ~evidence:concealed_kongs acc Two_concealed_pungs;
  if has acc Four_concealed_pungs then begin
    exclude acc All_pungs;
    exclude acc Fully_concealed_hand;
    exclude acc Concealed_hand
  end

type combo = { combo_fan : t; ids : int list }

let count_associated groups acc =
  let candidates = ref [] in
  let add_combo fan ids =
    let combo = { combo_fan = fan; ids } in
    if not (List.exists (( = ) combo) !candidates) then candidates := combo :: !candidates
  in
  let sequences = List.filter (fun index -> is_chow (group_at groups index)) (indices (List.length groups)) in
  let triplets = List.filter (fun index -> is_triplet (group_at groups index)) (indices (List.length groups)) in
  let pairs = List.filter (fun index -> is_pair (group_at groups index)) (indices (List.length groups)) in
  let winds = List.filter (fun index -> Tile.is_wind (group_at groups index).Shape.tile) (indices (List.length groups)) in
  let dragons = List.filter (fun index -> Tile.is_dragon (group_at groups index).Shape.tile) (indices (List.length groups)) in
  let wind_triplets = List.filter (fun index -> List.mem index triplets) winds in
  let wind_pairs = List.filter (fun index -> List.mem index pairs) winds in
  let dragon_triplets = List.filter (fun index -> List.mem index triplets) dragons in
  let dragon_pairs = List.filter (fun index -> List.mem index pairs) dragons in
  if List.length wind_triplets = 4 then add_combo Big_four_winds wind_triplets;
  if List.length wind_triplets = 3 && List.length wind_pairs = 1 then
    add_combo Little_four_winds (wind_triplets @ wind_pairs);
  if List.length wind_triplets = 3 then add_combo Big_three_winds wind_triplets;
  if List.length dragon_triplets = 3 then add_combo Big_three_dragons dragon_triplets;
  if List.length dragon_triplets = 2 && List.length dragon_pairs = 1 then
    add_combo Little_three_dragons (dragon_triplets @ dragon_pairs);
  if List.length dragon_triplets = 2 then add_combo Two_dragons_pungs dragon_triplets;

  let low = List.filter (fun index -> Tile.rank (group_at groups index).Shape.tile = 2) sequences in
  let high = List.filter (fun index -> Tile.rank (group_at groups index).Shape.tile = 8) sequences in
  if List.length low = 2 && List.length high = 2 && List.length pairs = 1 then begin
    let pair = List.hd pairs in
    if Tile.rank (group_at groups pair).Shape.tile = 5 then begin
      let low_a, low_b = (List.nth low 0, List.nth low 1) in
      let high_a, high_b = (List.nth high 0, List.nth high 1) in
      let tile index = (group_at groups index).Shape.tile in
      let ids = [ low_a; low_b; high_a; high_b; pair ] in
      let suits = List.map (fun index -> suit_index (tile index)) ids in
      let unique_suits = List.sort_uniq compare suits in
      if List.length unique_suits = 1 then add_combo Pure_terminal_chows ids
      else if
        suit_index (tile low_a) <> suit_index (tile low_b)
        && suit_index (tile pair) <> suit_index (tile low_a)
        && suit_index (tile pair) <> suit_index (tile low_b)
        && ((suit_index (tile low_a) = suit_index (tile high_a)
             && suit_index (tile low_b) = suit_index (tile high_b))
            || (suit_index (tile low_a) = suit_index (tile high_b)
                && suit_index (tile low_b) = suit_index (tile high_a)))
      then add_combo Three_suited_terminal_chows ids
    end
  end;

  let sequence_array = Array.of_list sequences in
  for left = 0 to Array.length sequence_array - 1 do
    for middle = left + 1 to Array.length sequence_array - 1 do
      let first = sequence_array.(left) in
      let second = sequence_array.(middle) in
      if
        (group_at groups first).Shape.kind = (group_at groups second).Shape.kind
        && (group_at groups first).Shape.tile = (group_at groups second).Shape.tile
      then begin
        add_combo Pure_double_chow [ first; second ];
        for right = middle + 1 to Array.length sequence_array - 1 do
          let third = sequence_array.(right) in
          if
            (group_at groups second).Shape.kind = (group_at groups third).Shape.kind
            && (group_at groups second).Shape.tile = (group_at groups third).Shape.tile
          then begin
            add_combo Pure_triple_chow [ first; second; third ];
            for fourth = right + 1 to Array.length sequence_array - 1 do
              let last = sequence_array.(fourth) in
              if
                (group_at groups third).Shape.kind = (group_at groups last).Shape.kind
                && (group_at groups third).Shape.tile = (group_at groups last).Shape.tile
              then add_combo Quadruple_chow [ first; second; third; last ]
            done
          end
        done
      end
    done
  done;

  let sorted_numbered_triplets =
    triplets
    |> List.filter (fun index -> Tile.is_numbered (group_at groups index).Shape.tile)
    |> List.sort (fun left right ->
           let left_tile = (group_at groups left).Shape.tile in
           let right_tile = (group_at groups right).Shape.tile in
           let by_rank = compare (Tile.rank left_tile) (Tile.rank right_tile) in
           if by_rank <> 0 then by_rank else compare (suit_index left_tile) (suit_index right_tile))
  in
  let triplet_array = Array.of_list sorted_numbered_triplets in
  for left = 0 to Array.length triplet_array - 1 do
    let first = triplet_array.(left) in
    let first_tile = (group_at groups first).Shape.tile in
    for middle = left + 1 to Array.length triplet_array - 1 do
      let second = triplet_array.(middle) in
      let second_tile = (group_at groups second).Shape.tile in
      if Tile.rank second_tile = Tile.rank first_tile + 1 then
        for right = middle + 1 to Array.length triplet_array - 1 do
          let third = triplet_array.(right) in
          let third_tile = (group_at groups third).Shape.tile in
          if Tile.rank third_tile = Tile.rank second_tile + 1 then
            if
              suit_index first_tile <> suit_index second_tile
              && suit_index first_tile <> suit_index third_tile
              && suit_index second_tile <> suit_index third_tile
            then add_combo Mixed_shifted_pungs [ first; second; third ]
            else if
              suit_index first_tile = suit_index second_tile
              && suit_index first_tile = suit_index third_tile
            then begin
              add_combo Pure_shifted_pungs [ first; second; third ];
              for fourth = right + 1 to Array.length triplet_array - 1 do
                let last = triplet_array.(fourth) in
                let last_tile = (group_at groups last).Shape.tile in
                if
                  suit_index last_tile = suit_index first_tile
                  && Tile.rank last_tile = Tile.rank third_tile + 1
                then add_combo Four_pure_shifted_pungs [ first; second; third; last ]
              done
            end
        done
    done
  done;

  let sorted_sequences =
    sequences
    |> List.sort (fun left right ->
           let left_tile = (group_at groups left).Shape.tile in
           let right_tile = (group_at groups right).Shape.tile in
           let by_rank = compare (Tile.rank left_tile) (Tile.rank right_tile) in
           if by_rank <> 0 then by_rank else compare (suit_index left_tile) (suit_index right_tile))
  in
  let sorted_array = Array.of_list sorted_sequences in
  for left = 0 to Array.length sorted_array - 1 do
    let first = sorted_array.(left) in
    let first_tile = (group_at groups first).Shape.tile in
    for middle = left + 1 to Array.length sorted_array - 1 do
      let second = sorted_array.(middle) in
      let second_tile = (group_at groups second).Shape.tile in
      let step_one = Tile.rank second_tile - Tile.rank first_tile in
      if (step_one = 1 || step_one = 2) && suit_index first_tile = suit_index second_tile then
        for right = middle + 1 to Array.length sorted_array - 1 do
          let third = sorted_array.(right) in
          let third_tile = (group_at groups third).Shape.tile in
          let step_two = Tile.rank third_tile - Tile.rank second_tile in
          if
            (step_two = 1 || step_two = 2)
            && suit_index second_tile = suit_index third_tile
          then begin
            if step_one = step_two then add_combo Pure_shifted_chows [ first; second; third ];
            for fourth = right + 1 to Array.length sorted_array - 1 do
              let last = sorted_array.(fourth) in
              let last_tile = (group_at groups last).Shape.tile in
              let step_three = Tile.rank last_tile - Tile.rank third_tile in
              if
                (step_three = 1 || step_three = 2)
                && suit_index third_tile = suit_index last_tile
                && step_one = step_two
                && step_one = step_three
              then add_combo Four_pure_shifted_chows [ first; second; third; last ]
            done
          end
        done
    done
  done;

  for left = 0 to Array.length sorted_array - 1 do
    let first = sorted_array.(left) in
    let first_tile = (group_at groups first).Shape.tile in
    for middle = left + 1 to Array.length sorted_array - 1 do
      let second = sorted_array.(middle) in
      let second_tile = (group_at groups second).Shape.tile in
      if
        Tile.rank second_tile = Tile.rank first_tile + 1
        && suit_index first_tile <> suit_index second_tile
      then
        for right = middle + 1 to Array.length sorted_array - 1 do
          let third = sorted_array.(right) in
          let third_tile = (group_at groups third).Shape.tile in
          if
            Tile.rank third_tile = Tile.rank second_tile + 1
            && suit_index first_tile <> suit_index third_tile
            && suit_index second_tile <> suit_index third_tile
          then add_combo Mixed_shifted_chows [ first; second; third ]
        done
    done
  done;

  let rank_buckets = Array.make 10 [] in
  List.iter (fun index -> rank_buckets.(Tile.rank (group_at groups index).Shape.tile) <- index :: rank_buckets.(Tile.rank (group_at groups index).Shape.tile)) sequences;
  List.iter
    (fun low ->
      List.iter
        (fun middle ->
          List.iter
            (fun high ->
              let low_tile = (group_at groups low).Shape.tile in
              let middle_tile = (group_at groups middle).Shape.tile in
              let high_tile = (group_at groups high).Shape.tile in
              if
                suit_index low_tile = suit_index middle_tile
                && suit_index low_tile = suit_index high_tile
              then add_combo Pure_straight [ low; middle; high ]
              else if
                suit_index low_tile <> suit_index middle_tile
                && suit_index low_tile <> suit_index high_tile
                && suit_index middle_tile <> suit_index high_tile
              then add_combo Mixed_straight [ low; middle; high ])
            rank_buckets.(8))
        rank_buckets.(5))
    rank_buckets.(2);

  for left = 0 to List.length triplets - 1 do
    let first = List.nth triplets left in
    let first_tile = (group_at groups first).Shape.tile in
    if Tile.is_numbered first_tile then
      for middle = left + 1 to List.length triplets - 1 do
        let second = List.nth triplets middle in
        let second_tile = (group_at groups second).Shape.tile in
        if Tile.is_numbered second_tile && Tile.rank second_tile = Tile.rank first_tile then begin
          add_combo Double_pung [ first; second ];
          for right = middle + 1 to List.length triplets - 1 do
            let third = List.nth triplets right in
            let third_tile = (group_at groups third).Shape.tile in
            if Tile.is_numbered third_tile && Tile.rank third_tile = Tile.rank first_tile then
              add_combo Triple_pung [ first; second; third ]
          done
        end
      done
  done;

  for left = 0 to List.length sequences - 1 do
    let first = List.nth sequences left in
    let first_tile = (group_at groups first).Shape.tile in
    for middle = left + 1 to List.length sequences - 1 do
      let second = List.nth sequences middle in
      let second_tile = (group_at groups second).Shape.tile in
      if
        Tile.rank first_tile = Tile.rank second_tile
        && suit_index first_tile <> suit_index second_tile
      then
        for right = middle + 1 to List.length sequences - 1 do
          let third = List.nth sequences right in
          let third_tile = (group_at groups third).Shape.tile in
          if
            Tile.rank third_tile = Tile.rank first_tile
            && suit_index first_tile <> suit_index third_tile
            && suit_index second_tile <> suit_index third_tile
          then add_combo Mixed_triple_chow [ first; second; third ]
        done
    done
  done;

  for left = 0 to List.length sequences - 1 do
    let first = List.nth sequences left in
    let first_tile = (group_at groups first).Shape.tile in
    for middle = left + 1 to List.length sequences - 1 do
      let second = List.nth sequences middle in
      let second_tile = (group_at groups second).Shape.tile in
      if
        suit_index first_tile <> suit_index second_tile
        && Tile.rank first_tile = Tile.rank second_tile
      then add_combo Mixed_double_chow [ first; second ]
      else if suit_index first_tile = suit_index second_tile then begin
        let delta = abs (Tile.rank first_tile - Tile.rank second_tile) in
        if delta = 3 then add_combo Short_straight [ first; second ]
        else if delta = 6 then add_combo Two_terminal_chows [ first; second ]
      end
    done
  done;

  let candidates = Array.of_list (List.rev !candidates) in
  let group_count = List.length groups in
  let rec find parent value =
    if parent.(value) = value then value
    else begin
      let root = find parent parent.(value) in
      parent.(value) <- root;
      root
    end
  in
  let rec component_key parent =
    let labels = Array.make group_count (-1) in
    let next_label = ref 0 in
    let key = ref 0 in
    for index = 0 to group_count - 1 do
      let root = find parent index in
      if labels.(root) < 0 then begin
        labels.(root) <- !next_label;
        incr next_label
      end;
      key := (!key * group_count) + labels.(root)
    done;
    !key
  in
  let memo = Hashtbl.create 32 in
  let rec choose parent =
    let key = component_key parent in
    match Hashtbl.find_opt memo key with
    | Some result -> result
    | None ->
        let best_points = ref 0 in
        let best_selected = ref [] in
        Array.iteri
          (fun index candidate ->
            let roots = List.map (find parent) candidate.ids in
            if List.length (List.sort_uniq compare roots) = List.length roots then begin
              let next = Array.copy parent in
              match roots with
              | [] -> ()
              | root :: rest ->
                  List.iter (fun other -> next.(find next other) <- root) rest;
                  let rest_points, rest_selected = choose next in
                  let total = points candidate.combo_fan + rest_points in
                  if total > !best_points then begin
                    best_points := total;
                    best_selected := index :: rest_selected
                  end
            end)
          candidates;
        let result = (!best_points, !best_selected) in
        Hashtbl.add memo key result;
        result
  in
  let _, selected = choose (Array.init group_count Fun.id) in
  List.iter
    (fun index ->
      let combo = candidates.(index) in
      add ~evidence:combo.ids acc combo.combo_fan;
      match combo.combo_fan with
      | Big_four_winds ->
          exclude acc All_pungs;
          List.iter
            (fun group_index ->
              if Tile.is_wind (group_at groups group_index).Shape.tile then begin
                exclude ~evidence:[ group_index ] acc Prevalent_wind;
                exclude ~evidence:[ group_index ] acc Seat_wind;
                exclude ~evidence:[ group_index ] acc Terminal_or_honor_pung
              end)
            combo.ids
      | Big_three_dragons | Little_three_dragons | Two_dragons_pungs ->
          List.iter
            (fun group_index ->
              if Tile.is_dragon (group_at groups group_index).Shape.tile then begin
                exclude ~evidence:[ group_index ] acc Dragon_pung;
                exclude ~evidence:[ group_index ] acc Terminal_or_honor_pung
              end)
            combo.ids
      | Little_four_winds | Big_three_winds ->
          List.iter
            (fun group_index ->
              if Tile.is_wind (group_at groups group_index).Shape.tile then
                exclude ~evidence:[ group_index ] acc Terminal_or_honor_pung)
            combo.ids
      | Pure_terminal_chows ->
          exclude acc Full_flush;
          exclude acc All_chows;
          exclude acc No_honors
      | Quadruple_chow -> exclude acc Tile_hog
      | Four_pure_shifted_pungs -> exclude acc All_pungs
      | Three_suited_terminal_chows -> exclude acc All_chows
      | _ -> ())
    selected

let count_single groups ~context acc =
  List.iteri
    (fun index group ->
      if is_triplet group then begin
        let tile = group.Shape.tile in
        if Tile.is_dragon tile then begin
          add ~evidence:[ index ] acc Dragon_pung;
          exclude ~evidence:[ index ] acc Terminal_or_honor_pung
        end;
        if tile = context.round_wind then begin
          add ~evidence:[ index ] acc Prevalent_wind;
          exclude ~evidence:[ index ] acc Terminal_or_honor_pung
        end;
        if tile = context.seat_wind then begin
          add ~evidence:[ index ] acc Seat_wind;
          exclude ~evidence:[ index ] acc Terminal_or_honor_pung
        end;
        if Tile.is_terminal_or_honor tile then add ~evidence:[ index ] acc Terminal_or_honor_pung
      end)
    groups

let count_win_mode groups ~context ~knitted_pattern ~wait_count ~winning ~menqing
    ~totally_exposed acc =
  let self_draw = context.win_method = Self_draw in
  let exclude_pair_wait fan =
    List.iteri
      (fun index group -> if is_pair group then exclude ~evidence:[ index ] acc fan)
      groups
  in
  if context.flags.last_tile && self_draw then begin
    add acc Last_tile_draw;
    exclude acc Self_drawn
  end;
  if context.flags.last_tile && not self_draw then add acc Last_tile_claim;
  if context.flags.after_kong then begin
    add acc Out_with_replacement_tile;
    exclude acc Self_drawn
  end;
  if context.flags.robbing_kong then begin
    add acc Robbing_the_kong;
    exclude acc Last_tile
  end;
  if totally_exposed && not self_draw then begin
    add acc Melded_hand;
    exclude_pair_wait Single_wait
  end;
  if menqing && self_draw then begin
    add acc Fully_concealed_hand;
    exclude acc Concealed_hand;
    exclude acc Self_drawn
  end;
  if context.flags.last_of_kind then begin
    add acc Last_tile;
    exclude_pair_wait Single_wait
  end;
  if menqing then add acc Concealed_hand;
  if wait_count = 1 then begin
    let winning_in_pattern =
      match knitted_pattern with
      | None -> false
      | Some index -> Array.exists (( = ) winning) Shape.knitted_patterns.(index)
    in
    if not winning_in_pattern then
      let rec mark = function
        | [] -> ()
        | group :: rest ->
            if group.Shape.contains_winning then begin
              if is_pair group then add acc Single_wait
              else if is_chow group then begin
                let middle = group.Shape.tile in
                if
                  (Tile.rank middle = 2 && Tile.rank winning = 3)
                  || (Tile.rank middle = 8 && Tile.rank winning = 7)
                then add acc Edge_wait
                else if middle = winning then add acc Closed_wait
              end
            end
            else mark rest
      in
      mark groups
  end;
  if self_draw then begin
    add acc Self_drawn;
    if
      (has acc Nine_gates || has acc Four_concealed_pungs)
      && not (has acc Last_tile_draw)
      && not (has acc Out_with_replacement_tile)
    then clear_exclusions acc Self_drawn
  end

let score_basic groups ~counts ~concealed_before ~context ~melds ~decomposition
    ~formal_wait_count ~winning =
  let acc = { entries = []; exclusions = []; internal = 0 } in
  let knitted = decomposition.Shape.knitted_pattern <> None in
  count_overall ~nine_gates:(is_nine_gates concealed_before melds)
    counts ~groups ~knitted ~context acc;
  count_kongs groups acc;
  count_associated groups acc;
  count_single groups ~context acc;
  let menqing = List.for_all (fun meld -> meld.Meld.concealed) melds in
  let totally_exposed =
    List.length melds = 4 && List.for_all (fun meld -> not meld.Meld.concealed) melds
  in
  count_win_mode groups ~context
    ~knitted_pattern:decomposition.Shape.knitted_pattern
    ~wait_count:formal_wait_count ~winning ~menqing ~totally_exposed acc;
  if decomposition.Shape.knitted_pattern <> None then add acc Knitted_straight;
  finish acc

let score_special shape counts ~context =
  let acc = { entries = []; exclusions = []; internal = 0 } in
  begin
    match shape with
    | Shape.Thirteen_orphans -> add acc Thirteen_orphans
    | Shape.Fully_disconnected -> add acc Lesser_honors_and_knitted_tiles
    | Shape.Seven_star_disconnected -> add acc Greater_honors_and_knitted_tiles
    | Shape.Seven_pairs -> add acc Seven_pairs
    | Shape.Consecutive_seven_pairs -> add acc Seven_shifted_pairs
    | Shape.None -> ()
  end;
  if shape = Shape.Seven_pairs || shape = Shape.Consecutive_seven_pairs then
    count_overall counts ~groups:[] ~knitted:false ~context acc;
  if shape = Shape.Fully_disconnected || shape = Shape.Seven_star_disconnected then
    if first_knitted_pattern counts <> None then add acc Knitted_straight;
  exclude acc Fully_concealed_hand;
  exclude acc Concealed_hand;
  if shape = Shape.Consecutive_seven_pairs then begin
    exclude acc Full_flush;
    exclude acc No_honors
  end;
  count_win_mode [] ~context ~knitted_pattern:None ~wait_count:0 ~winning:(-1)
    ~menqing:true ~totally_exposed:false acc;
  exclude acc Fully_concealed_hand;
  exclude acc Concealed_hand;
  if context.win_method = Self_draw then force_one acc Self_drawn;
  finish acc

let better left right =
  if left.qualifying_fan >= right.qualifying_fan then left else right

let evaluate ~concealed_before ~melds ~winning ~context =
  if not (Shape.winning_shape ~concealed_before ~melds ~winning) then not_winning
  else
    let after = Array.copy concealed_before in
    after.(winning) <- after.(winning) + 1;
    let counts = physical_counts after melds in
    let special = Shape.special after melds in
    let formal_waits = formal_wait_count concealed_before melds in
    let candidates = ref [] in
    if special <> Shape.None then
      candidates := score_special special counts ~context :: !candidates;
    let shape_method = match context.win_method with Self_draw -> `Self_draw | Discard -> `Discard in
    let decompositions =
      Shape.decompositions ~counts:after ~melds ~winning ~win_method:shape_method
    in
    List.iter
      (fun decomposition ->
        candidates :=
          score_basic decomposition.Shape.groups ~counts ~context ~melds ~concealed_before
            ~decomposition ~formal_wait_count:formal_waits ~winning
          :: !candidates)
      decompositions;
    let best =
      match !candidates with
      | [] -> not_winning
      | first :: rest -> List.fold_left better first rest
    in
    if not best.winning && best.qualifying_fan = 0 then best
    else
      let flower_fan = context.flowers in
      let awards =
        if flower_fan > 0 then best.awards @ [ { fan = Flower_tiles; count = flower_fan } ]
        else best.awards
      in
      {
        best with
        winning = best.qualifying_fan >= 8;
        flower_fan;
        total_fan = best.qualifying_fan + flower_fan;
        awards;
      }
