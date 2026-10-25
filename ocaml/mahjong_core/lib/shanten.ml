let min_standard ~meld_count counts =
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
  let standard = min_standard ~meld_count counts in
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
      let result = of_counts_uncached ~meld_count counts in
      if Hashtbl.length cache >= cache_capacity then Hashtbl.clear cache;
      Hashtbl.add cache key result;
      result

let of_hand ~melds hand = of_counts ~meld_count:(List.length melds) (Tile_counts.of_instances hand)

