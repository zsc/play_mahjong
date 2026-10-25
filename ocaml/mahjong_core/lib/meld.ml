type kind = Chow | Pung | Kong

type origin =
  | Concealed
  | Claimed of { discarder : int; discard : int }
  | Added of { fourth : int }

type t = {
  kind : kind;
  tile : Tile.t;
  concealed : bool;
  origin : origin;
  instances : int list;
}

let chow ~middle ~instances ~origin =
  if not (Tile.is_numbered middle) then invalid_arg "chow requires numbered tile";
  let rank = Tile.rank middle in
  if rank < 2 || rank > 8 then invalid_arg "chow middle must be 2..8";
  { kind = Chow; tile = middle; concealed = false; origin; instances }

let pung ~tile ~instances ~origin =
  if not (Tile.is_standard_kind tile) then invalid_arg "pung requires standard tile";
  { kind = Pung; tile; concealed = false; origin; instances }

let kong ~tile ~instances ~concealed ~origin =
  if not (Tile.is_standard_kind tile) then invalid_arg "kong requires standard tile";
  { kind = Kong; tile; concealed; origin; instances }

let concealed_kong ~tile ~instances =
  kong ~tile ~instances ~concealed:true ~origin:Concealed

let structural_tiles kind = match kind with Chow | Pung -> 3 | Kong -> 4
let structural_count meld = structural_tiles meld.kind
let is_kong meld = meld.kind = Kong
let breaks_concealed_hand meld = not meld.concealed

let kind_tiles meld =
  match meld.kind with
  | Chow -> [ meld.tile - 1; meld.tile; meld.tile + 1 ]
  | Pung | Kong -> List.init (structural_tiles meld.kind) (fun _ -> meld.tile)

