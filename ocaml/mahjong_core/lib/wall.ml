type t = {
  tiles : int array;
  front : int;
  back : int;
}

let create seed =
  let tiles = Array.init Tile.physical_tile_count Fun.id in
  Rng.shuffle (Rng.create seed) tiles;
  { tiles; front = 0; back = Tile.physical_tile_count - 1 }

let remaining wall = max 0 (wall.back - wall.front + 1)
let is_empty wall = remaining wall = 0

let take_front wall =
  if is_empty wall then None
  else Some (wall.tiles.(wall.front), { wall with front = wall.front + 1 })

let take_back wall =
  if is_empty wall then None
  else Some (wall.tiles.(wall.back), { wall with back = wall.back - 1 })

let remaining_tiles wall =
  Array.sub wall.tiles wall.front (remaining wall)

let copy wall = wall
