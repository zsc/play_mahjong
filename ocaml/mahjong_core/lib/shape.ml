type group_kind = Pair | Chow | Pung | Kong

type group = {
  kind : group_kind;
  tile : Tile.t;
  declared : bool;
  concealed : bool;
  contains_winning : bool;
}

type decomposition = {
  groups : group list;
  knitted_pattern : int option;
  winning_in_knitted : bool;
}

type special =
  | None
  | Thirteen_orphans
  | Seven_pairs
  | Consecutive_seven_pairs
  | Fully_disconnected
  | Seven_star_disconnected

let knitted_patterns =
  let permutations =
    [ [| 0; 1; 2 |]; [| 0; 2; 1 |]; [| 1; 0; 2 |]; [| 1; 2; 0 |]; [| 2; 0; 1 |]; [| 2; 1; 0 |] ]
  in
  let ranks = [| [| 1; 4; 7 |]; [| 2; 5; 8 |]; [| 3; 6; 9 |] |] in
  Array.map
    (fun permutation ->
      let tiles = Array.make 9 0 in
      let at = ref 0 in
      for suit = 0 to 2 do
        Array.iter
          (fun rank ->
            tiles.(!at) <- (suit * 9) + rank - 1;
            incr at)
          ranks.(permutation.(suit))
      done;
      tiles)
    (Array.of_list permutations)

let group_tiles group =
  match group.kind with
  | Chow -> [ group.tile - 1; group.tile; group.tile + 1 ]
  | Pung -> [ group.tile; group.tile; group.tile ]
  | Kong -> [ group.tile; group.tile; group.tile; group.tile ]
  | Pair -> [ group.tile; group.tile ]

let group_contains group kind = List.exists (( = ) kind) (group_tiles group)

let group_of_meld meld =
  let kind =
    match meld.Meld.kind with Meld.Chow -> Chow | Meld.Pung -> Pung | Meld.Kong -> Kong
  in
  {
    kind;
    tile = meld.tile;
    declared = true;
    concealed = meld.concealed;
    contains_winning = false;
  }

let is_terminal_or_honor_kind = Tile.is_terminal_or_honor

let special counts melds =
  if melds <> [] then None
  else
    let total = Tile_counts.total counts in
    let thirteen =
      total = 14
      && Array.for_all
           (fun kind -> counts.(kind) = 0 || is_terminal_or_honor_kind kind)
           (Array.init Tile.standard_kind_count Fun.id)
      && Array.fold_left (fun sum value -> sum + min 1 value) 0 counts = 13
    in
    if thirteen then Thirteen_orphans
    else
      let pair_count = ref 0 in
      let distinct = ref 0 in
      let first = ref (-1) in
      let last = ref (-1) in
      let same_suit = ref true in
      let all_exact_pairs = ref true in
      let suit = ref (-1) in
      for kind = 0 to Tile.standard_kind_count - 1 do
        let value = counts.(kind) in
        if value mod 2 <> 0 then all_exact_pairs := false;
        pair_count := !pair_count + (value / 2);
        if value > 0 then begin
          incr distinct;
          if !first < 0 then first := kind;
          last := kind;
          if not (Tile.is_numbered kind) || value <> 2 then all_exact_pairs := false;
          let current_suit = (match Tile.suit kind with Tile.Characters -> 0 | Tile.Bamboo -> 1 | Tile.Dots -> 2 | _ -> 3) in
          if !suit < 0 then suit := current_suit else if !suit <> current_suit then same_suit := false
        end
      done;
      if (!pair_count = 7 && !all_exact_pairs && !distinct = 7 && !last - !first = 6 && !same_suit)
      then Consecutive_seven_pairs
      else if total = 14 && Array.for_all (fun value -> value mod 2 = 0) counts && !pair_count = 7 then Seven_pairs
      else
        let disconnected =
          total = 14 && Array.for_all (fun value -> value <= 1) counts
          && Array.exists
               (fun pattern ->
                 let allowed = Array.make 27 false in
                 Array.iter (fun kind -> allowed.(kind) <- true) pattern;
                 let ok = ref true in
                 for kind = 0 to 26 do
                   if counts.(kind) > 0 && not allowed.(kind) then ok := false
                 done;
                 !ok)
               knitted_patterns
        in
        if disconnected then
          let all_honors = ref true in
          for kind = 27 to 33 do
            if counts.(kind) = 0 then all_honors := false
          done;
          if !all_honors then Seven_star_disconnected else Fully_disconnected
        else None

let basic_groups counts sets_needed pairs_needed =
  let result = ref [] in
  let current = ref [] in
  let rec collect sets pairs =
    let first = ref (-1) in
    for kind = 0 to Tile.standard_kind_count - 1 do
      if !first < 0 && counts.(kind) <> 0 then first := kind
    done;
    if !first < 0 then begin
      if sets = 0 && pairs = 0 then result := List.rev !current :: !result
    end
    else begin
      let kind = !first in
      if pairs > 0 && counts.(kind) >= 2 then begin
        counts.(kind) <- counts.(kind) - 2;
        current := { kind = Pair; tile = kind; declared = false; concealed = true; contains_winning = false } :: !current;
        collect sets (pairs - 1);
        current := List.tl !current;
        counts.(kind) <- counts.(kind) + 2
      end;
      if sets > 0 && counts.(kind) >= 3 then begin
        counts.(kind) <- counts.(kind) - 3;
        current := { kind = Pung; tile = kind; declared = false; concealed = true; contains_winning = false } :: !current;
        collect (sets - 1) pairs;
        current := List.tl !current;
        counts.(kind) <- counts.(kind) + 3
      end;
      if sets > 0 && Tile.is_numbered kind && Tile.rank kind <= 7
         && counts.(kind + 1) > 0 && counts.(kind + 2) > 0 then begin
        counts.(kind) <- counts.(kind) - 1;
        counts.(kind + 1) <- counts.(kind + 1) - 1;
        counts.(kind + 2) <- counts.(kind + 2) - 1;
        current := { kind = Chow; tile = kind + 1; declared = false; concealed = true; contains_winning = false } :: !current;
        collect (sets - 1) pairs;
        current := List.tl !current;
        counts.(kind) <- counts.(kind) + 1;
        counts.(kind + 1) <- counts.(kind + 1) + 1;
        counts.(kind + 2) <- counts.(kind + 2) + 1
      end
    end
  in
  if sets_needed >= 0 && pairs_needed >= 0 then collect sets_needed pairs_needed;
  List.rev !result

let mark_winning win_method group =
  let concealed =
    match win_method with
    | `Discard when group.kind = Pung -> false
    | _ -> group.concealed
  in
  { group with concealed; contains_winning = true }

let add_winning_marked declared concealed_groups winning win_method =
  List.filter_map
    (fun index ->
      let group = List.nth concealed_groups index in
      if group_contains group winning then
        let groups =
          declared
          @ List.mapi (fun current candidate -> if current = index then mark_winning win_method candidate else candidate) concealed_groups
        in
        Some { groups; knitted_pattern = None; winning_in_knitted = false }
      else None)
    (List.init (List.length concealed_groups) Fun.id)

let decompositions ~counts ~melds ~winning ~win_method =
  let counts = Array.copy counts in
  let declared = List.map group_of_meld melds in
  let meld_count = List.length melds in
  let result = ref [] in
  List.iter
    (fun groups -> result := add_winning_marked declared groups winning win_method @ !result)
    (basic_groups counts (4 - meld_count) 1);
  Array.iteri
    (fun pattern_index pattern ->
      if Array.for_all (fun kind -> counts.(kind) > 0) pattern then begin
        let remaining = Array.copy counts in
        Array.iter (fun kind -> remaining.(kind) <- remaining.(kind) - 1) pattern;
        List.iter
          (fun concealed_groups ->
            let base = declared @ concealed_groups in
            result := { groups = base; knitted_pattern = Some pattern_index; winning_in_knitted = false } :: !result;
            if Array.exists (( = ) winning) pattern then
              result := { groups = base; knitted_pattern = Some pattern_index; winning_in_knitted = true } :: !result)
          (basic_groups remaining (1 - meld_count) 1)
      end)
    knitted_patterns;
  !result

let winning_shape ~concealed_before ~melds ~winning =
  let after = Array.copy concealed_before in
  if not (Tile.is_standard_kind winning) then false
  else begin
    after.(winning) <- after.(winning) + 1;
    if after.(winning) > 4 then false
    else
      special after melds <> None
      || basic_groups (Array.copy after) (4 - List.length melds) 1 <> []
      || Array.exists
           (fun pattern ->
             if not (Array.for_all (fun kind -> after.(kind) > 0) pattern) then false
             else
               let remaining = Array.copy after in
               Array.iter (fun kind -> remaining.(kind) <- remaining.(kind) - 1) pattern;
               basic_groups remaining (1 - List.length melds) 1 <> [])
           knitted_patterns
  end
