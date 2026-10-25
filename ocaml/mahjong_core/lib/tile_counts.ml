type t = int array

let empty () = Array.make Tile.standard_kind_count 0

let copy = Array.copy

let count counts kind =
  if not (Tile.is_standard_kind kind) then invalid_arg "standard tile kind required";
  counts.(kind)

let set counts kind value =
  if not (Tile.is_standard_kind kind) then invalid_arg "standard tile kind required";
  if value < 0 || value > 4 then invalid_arg "tile count must be in 0..4";
  counts.(kind) <- value

let add counts kind =
  let next = count counts kind + 1 in
  set counts kind next

let remove counts kind =
  let value = count counts kind in
  if value = 0 then invalid_arg "cannot remove absent tile";
  set counts kind (value - 1)

let of_kinds kinds =
  let counts = empty () in
  List.iter (add counts) kinds;
  counts

let of_instances instances = of_kinds (List.map Tile.instance_kind instances)

let total counts = Array.fold_left ( + ) 0 counts

let kinds counts =
  let result = ref [] in
  for kind = Tile.standard_kind_count - 1 downto 0 do
    for _ = 1 to counts.(kind) do
      result := kind :: !result
    done
  done;
  !result

let instances counts =
  let available = Hashtbl.create 34 in
  for kind = 0 to Tile.standard_kind_count - 1 do
    Hashtbl.add available kind (ref (Tile.instances_of_kind kind))
  done;
  List.map
    (fun kind ->
      match !(Hashtbl.find available kind) with
      | instance :: rest ->
          Hashtbl.replace available kind (ref rest);
          instance
      | [] -> invalid_arg "tile counts exceed physical inventory")
    (kinds counts)

let equal = ( = )
let to_string counts = String.concat " " (List.map Tile.code (kinds counts))

