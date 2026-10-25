type t = { mutable state : int64 }

let seed_value seed = Int64.logxor (Int64.of_int seed) 2685821657736338717L

let create seed =
  let state = seed_value seed in
  { state = if state = 0L then 2685821657736338717L else state }

let next_int64 rng =
  let value = rng.state in
  let value = Int64.logxor value (Int64.shift_left value 13) in
  let value = Int64.logxor value (Int64.shift_right_logical value 7) in
  let value = Int64.logxor value (Int64.shift_left value 17) in
  rng.state <- value;
  value

let next_int rng bound =
  if bound <= 0 then invalid_arg "bound must be positive";
  let value = Int64.shift_right_logical (next_int64 rng) 1 in
  Int64.to_int (Int64.rem value (Int64.of_int bound))

let bool rng = next_int rng 2 = 1

let shuffle rng values =
  for index = Array.length values - 1 downto 1 do
    let other = next_int rng (index + 1) in
    let current = values.(index) in
    values.(index) <- values.(other);
    values.(other) <- current
  done

