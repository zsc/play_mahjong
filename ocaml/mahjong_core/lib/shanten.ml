let min_standard_reference ~meld_count counts =
  let counts = Array.copy counts in
  let best = ref max_int in
  let consider sets partials head =
    let total_sets = meld_count + sets in
    let partials = min partials (max 0 (4 - total_sets)) in
    let value = 8 - (2 * total_sets) - partials - (if head then 1 else 0) in
    if value < !best then best := value
  in
  let rec visit index sets partials head =
    if sets + meld_count > 4 || partials > 4 then ()
    else if index >= Tile.standard_kind_count then consider sets partials head
    else if counts.(index) = 0 then visit (index + 1) sets partials head
    else begin
      counts.(index) <- counts.(index) - 1;
      visit (index + 1) sets partials head;
      counts.(index) <- counts.(index) + 1;
      if counts.(index) >= 3 && sets < 4 - meld_count then begin
        counts.(index) <- counts.(index) - 3;
        visit index (sets + 1) partials head;
        counts.(index) <- counts.(index) + 3
      end;
      if Tile.is_numbered index && Tile.rank index <= 7
         && counts.(index + 1) > 0 && counts.(index + 2) > 0
         && sets < 4 - meld_count then begin
        counts.(index) <- counts.(index) - 1;
        counts.(index + 1) <- counts.(index + 1) - 1;
        counts.(index + 2) <- counts.(index + 2) - 1;
        visit index (sets + 1) partials head;
        counts.(index) <- counts.(index) + 1;
        counts.(index + 1) <- counts.(index + 1) + 1;
        counts.(index + 2) <- counts.(index + 2) + 1
      end;
      if counts.(index) >= 2 then begin
        counts.(index) <- counts.(index) - 2;
        if not head then visit index sets partials true;
        visit index sets (partials + 1) head;
        counts.(index) <- counts.(index) + 2
      end;
      if Tile.is_numbered index && Tile.rank index <= 8 && counts.(index + 1) > 0 then begin
        counts.(index) <- counts.(index) - 1;
        counts.(index + 1) <- counts.(index + 1) - 1;
        visit index sets (partials + 1) head;
        counts.(index) <- counts.(index) + 1;
        counts.(index + 1) <- counts.(index + 1) + 1
      end;
      if Tile.is_numbered index && Tile.rank index <= 7 && counts.(index + 2) > 0 then begin
        counts.(index) <- counts.(index) - 1;
        counts.(index + 2) <- counts.(index + 2) - 1;
        visit index sets (partials + 1) head;
        counts.(index) <- counts.(index) + 1;
        counts.(index + 2) <- counts.(index + 2) + 1
      end
    end
  in
  visit 0 0 0 false;
  !best

(* A block frontier stores the maximum number of partial melds for every
   (complete melds, pair-as-head) combination. Each of the ten entries uses
   three bits: zero means unreachable, otherwise partials + 1 (capped at 4).
   Dominance is valid only within the SAME meld/head state, never across it. *)
let powers_of_five = [| 1; 5; 25; 125; 625; 3125; 15625; 78125; 390625; 1953125 |]
let suit_frontiers = Array.make powers_of_five.(9) (-1)
let honor_frontiers = Array.make powers_of_five.(7) (-1)

let entry frontier sets head = (frontier lsr (3 * ((2 * sets) + head))) land 7

let put frontier sets head partials =
  let shift = 3 * ((2 * sets) + head) in
  let value = 1 + min 4 partials in
  if value > ((frontier lsr shift) land 7) then
    (frontier land (lnot (7 lsl shift))) lor (value lsl shift)
  else frontier

let add_component frontier sets_delta partials_delta head_delta into =
  let result = ref into in
  for sets = 0 to 4 - sets_delta do
    for head = 0 to 1 - head_delta do
      let value = entry frontier sets head in
      if value > 0 then
        result := put !result (sets + sets_delta) (head + head_delta)
            (value - 1 + partials_delta)
    done
  done;
  !result

let rec block_frontier numbered code =
  let table = if numbered then suit_frontiers else honor_frontiers in
  let cached = table.(code) in
  if cached >= 0 then cached
  else if code = 0 then begin table.(0) <- 1; 1 end
  else begin
    let index = ref 0 in
    while (code / powers_of_five.(!index)) mod 5 = 0 do incr index done;
    let i = !index in
    let p = powers_of_five.(i) in
    let count = (code / p) mod 5 in
    let child removed = block_frontier numbered (code - removed) in
    let result = ref (child p) in
    let include_child removed sets partials head =
      result := add_component (child removed) sets partials head !result
    in
    if count >= 3 then include_child (3 * p) 1 0 0;
    if count >= 2 then begin
      include_child (2 * p) 0 1 0;
      include_child (2 * p) 0 0 1
    end;
    if numbered then begin
      let present offset = (code / powers_of_five.(i + offset)) mod 5 > 0 in
      if i <= 7 && present 1 then
        include_child (p + powers_of_five.(i + 1)) 0 1 0;
      if i <= 6 && present 2 then begin
        include_child (p + powers_of_five.(i + 2)) 0 1 0;
        if present 1 then
          include_child (p + powers_of_five.(i + 1) + powers_of_five.(i + 2)) 1 0 0
      end
    end;
    table.(code) <- !result;
    !result
  end

let combine_frontiers_uncached ~max_sets left right =
  let result = ref 0 in
  for left_sets = 0 to max_sets do
    for left_head = 0 to 1 do
      let left_value = entry left left_sets left_head in
      if left_value > 0 then
        for right_sets = 0 to max_sets - left_sets do
          for right_head = 0 to 1 - left_head do
            let right_value = entry right right_sets right_head in
            if right_value > 0 then
              result := put !result (left_sets + right_sets) (left_head + right_head)
                  (left_value + right_value - 2)
          done
        done
    done
  done;
  !result

(* Many different count blocks have the same frontier. Reuse their pure merge,
   including the meld budget in the key; suit order is irrelevant to this step. *)
let frontier_merge_cache = Hashtbl.create 32768

let combine_frontiers ~max_sets left right =
  let key = (max_sets, min left right, max left right) in
  match Hashtbl.find_opt frontier_merge_cache key with
  | Some result -> result
  | None ->
      let result = combine_frontiers_uncached ~max_sets left right in
      if Hashtbl.length frontier_merge_cache >= 32768 then Hashtbl.clear frontier_merge_cache;
      Hashtbl.add frontier_merge_cache key result;
      result

let standard_from_frontiers ~meld_count frontiers =
  let combined = ref 1 in
  for block = 0 to 3 do
    combined := combine_frontiers ~max_sets:(4 - meld_count) !combined
        frontiers.(block)
  done;
  let best = ref 8 in
  for sets = 0 to 4 - meld_count do
    for head = 0 to 1 do
      let value = entry !combined sets head in
      if value > 0 then
        best := min !best (8 - (2 * (meld_count + sets))
            - min (value - 1) (4 - meld_count - sets) - head)
    done
  done;
  !best

let block_codes counts =
  Array.init 4 (fun block ->
      let code = ref 0 in
      for rank = 0 to (if block = 3 then 6 else 8) do
        code := !code + (counts.((block * 9) + rank) * powers_of_five.(rank))
      done;
      !code)

let min_standard ~meld_count counts =
  let frontiers = Array.mapi (fun block code -> block_frontier (block < 3) code) (block_codes counts) in
  standard_from_frontiers ~meld_count frontiers

(* A private scratch evaluator for discard/draw candidates. Only the changed
   tile's block and special-hand statistics need updating. Never retain State. *)
type evaluator = {
  counts : int array;
  codes : int array;
  frontiers : int array;
  meld_count : int;
  mutable pairs : int;
  mutable distinct : int;
  mutable orphan_unique : int;
  mutable orphan_pairs : int;
}

let make_evaluator ~meld_count counts =
  let codes = block_codes counts in
  let e = { counts = Array.copy counts; codes;
            frontiers = Array.mapi (fun block code -> block_frontier (block < 3) code) codes;
            meld_count; pairs = 0; distinct = 0; orphan_unique = 0; orphan_pairs = 0 } in
  Array.iteri (fun kind count ->
      e.pairs <- e.pairs + count / 2;
      if count > 0 then e.distinct <- e.distinct + 1;
      if Tile.is_terminal_or_honor kind then begin
        if count > 0 then e.orphan_unique <- e.orphan_unique + 1;
        if count >= 2 then e.orphan_pairs <- e.orphan_pairs + 1
      end) counts;
  e

let adjust e kind delta =
  let old = e.counts.(kind) in
  let next = old + delta in
  if next < 0 || next > 4 then invalid_arg "shanten count must be in 0..4";
  e.counts.(kind) <- next;
  let present value = if value > 0 then 1 else 0 in
  let paired value = if value >= 2 then 1 else 0 in
  e.pairs <- e.pairs + next / 2 - old / 2;
  e.distinct <- e.distinct + present next - present old;
  if Tile.is_terminal_or_honor kind then begin
    e.orphan_unique <- e.orphan_unique + present next - present old;
    e.orphan_pairs <- e.orphan_pairs + paired next - paired old
  end;
  let block = kind / 9 in
  e.codes.(block) <- e.codes.(block) + delta * powers_of_five.(kind mod 9);
  e.frontiers.(block) <- block_frontier (block < 3) e.codes.(block)

let evaluate e =
  let standard = standard_from_frontiers ~meld_count:e.meld_count e.frontiers in
  if e.meld_count <> 0 then standard
  else min standard (min (6 - e.pairs + max 0 (7 - e.distinct))
                       (13 - e.orphan_unique - if e.orphan_pairs > 0 then 1 else 0))

let seven_pairs counts =
  let pairs = ref 0 in
  let distinct = ref 0 in
  Array.iter
    (fun count ->
      if count > 0 then incr distinct;
      pairs := !pairs + (count / 2))
    counts;
  6 - !pairs + max 0 (7 - !distinct)

let thirteen_orphans counts =
  let unique = ref 0 in
  let pair = ref false in
  for kind = 0 to Tile.standard_kind_count - 1 do
    if Tile.is_terminal_or_honor kind && counts.(kind) > 0 then begin
      incr unique;
      if counts.(kind) >= 2 then pair := true
    end
  done;
  13 - !unique - (if !pair then 1 else 0)

let of_counts_uncached ~meld_count counts =
  let standard = min_standard_reference ~meld_count counts in
  if meld_count = 0 then min standard (min (seven_pairs counts) (thirteen_orphans counts))
  else standard

(* Only memoize the pure structural result. No wall, opponents, fan context or
   mutable count array is retained. Bound memory separately in each worker. *)
let cache_capacity = 32768
let cache : (string, int) Hashtbl.t = Hashtbl.create cache_capacity

let of_counts ~meld_count counts =
  let key =
    String.init (Tile.standard_kind_count + 1)
      (fun index -> Char.chr (if index = 0 then meld_count else counts.(index - 1)))
  in
  match Hashtbl.find_opt cache key with
  | Some result -> result
  | None ->
      let standard = min_standard ~meld_count counts in
      let result =
        if meld_count = 0 then min standard (min (seven_pairs counts) (thirteen_orphans counts))
        else standard
      in
      if Hashtbl.length cache >= cache_capacity then Hashtbl.clear cache;
      Hashtbl.add cache key result;
      result

let of_hand ~melds hand = of_counts ~meld_count:(List.length melds) (Tile_counts.of_instances hand)

