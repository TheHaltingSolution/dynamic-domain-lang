import Lean
import Init.Data.Rat
import SPL.Instant
import SPL.Calendar
import SPL.Dimensions

/-!
Pure target primitives for the bounded SPL compiler. Units and record schemas
are checked before emission; defensive runtime tag checks reject malformed direct
calls. Financial arithmetic uses exact `Rat`, with explicit zero-divisor checks.
This runtime is executable infrastructure, not a compiler correctness proof.
-/
namespace SPL

inductive Value where
  | num : Rat → Value
  | quantity : String → Rat → Value
  | rate : String → String → Rat → Value
  | instant : Rat → String → Value
  | flag : Bool → Value
  | text : String → Value
  | seq : List Value → Value
  | tuple : List Value → Value
  | map : List Value → Value
  | obj : List (String × Value) → Value
  | absent : Value
  | present : Value → Value
  deriving Inhabited, Repr

abbrev Eval := Except String
abbrev Env := List (String × Value)

/-- Fixed R1 operational envelope, not a measured throughput claim. -/
def maxCollectionItems : Nat := 100000
def maxTraceObservations : Nat := 100000

def checkCollectionSize (size : Nat) : Eval Unit :=
  if size > maxCollectionItems then .error "RESOURCE_LIMIT" else .ok ()

def lookup (env : Env) (key : String) : Eval Value :=
  match env.lookup key with
  | some value => .ok value
  | none => .error ("MISSING_BINDING:" ++ key)

def field (value : Value) (key : String) : Eval Value :=
  match value with
  | .obj fields => lookup fields key
  | _ => .error "TARGET_EXPECTED_RECORD"

def asBool : Value → Eval Bool
  | .flag b => .ok b
  | _ => .error "TARGET_EXPECTED_BOOL"

def asNum : Value → Eval Rat
  | .num n => .ok n
  | _ => .error "TARGET_EXPECTED_NUMBER"

/-- Numeric payload access is explicit; legacy asNum deliberately rejects dimensions. -/
def magnitude : Value → Eval Rat
  | .num value => pure value
  | .quantity unit value =>
    if Dimensions.admitted unit then pure value else throw "UNSUPPORTED_UNIT"
  | .rate unit currency value =>
    if !Dimensions.admitted unit then throw "UNSUPPORTED_UNIT"
    else if currency != "USD" then throw "UNSUPPORTED_CURRENCY" else pure value
  | _ => throw "TARGET_EXPECTED_NUMBER"

def withMagnitude (template : Value) (value : Rat) : Value :=
  match template with
  | .quantity unit _ => .quantity unit value
  | .rate unit currency _ => .rate unit currency value
  | _ => .num value

def sameDimension (left right : Value) : Bool :=
  match left, right with
  | .num _, .num _ => true
  | .quantity a _, .quantity b _ => a == b
  | .rate a c _, .rate b d _ => a == b && c == d
  | _, _ => false

/-- Tagged arithmetic; scalar Money/Ratio distinctions remain a checked-IR assumption. -/
def dimensionalArithmetic (op : String) (left right : Value) : Eval Value := do
  let a ← magnitude left
  let b ← magnitude right
  if op == "/" && b == 0 then throw "DIVISION_BY_ZERO"
  if (op == "+" || op == "-") && sameDimension left right then
    return withMagnitude left (if op == "+" then a + b else a - b)
  match op, left, right with
  | "*", .quantity u _, .rate v _ _ | "*", .rate v _ _, .quantity u _ =>
    if u == v then pure (.num (a * b)) else throw "TYPE_MISMATCH"
  | "*", .num _, .quantity .. | "*", .num _, .rate .. => pure (withMagnitude right (a * b))
  | "*", .quantity .., .num _ | "*", .rate .., .num _ => pure (withMagnitude left (a * b))
  | "/", .quantity .., .num _ | "/", .rate .., .num _ => pure (withMagnitude left (a / b))
  | "/", .quantity .., .quantity .. | "/", .rate .., .rate .. =>
    if sameDimension left right then pure (.num (a / b)) else throw "TYPE_MISMATCH"
  | _, _, _ => throw "TYPE_MISMATCH"

def asList : Value → Eval (List Value)
  | .seq xs => do checkCollectionSize xs.length; pure xs
  | _ => .error "TARGET_EXPECTED_LIST"

def asText : Value → Eval String
  | .text s => .ok s
  | _ => .error "TARGET_EXPECTED_TEXT"

def recordValues (fields : List (String × Eval Value)) : Eval Value := do
  pure (.obj (← fields.mapM fun (key, value) => do pure (key, ← value)))

def listValues (items : List (Eval Value)) : Eval Value := do
  checkCollectionSize items.length
  pure (.seq (← items.mapM id))

def assertValue (value : Value) (code : String) : Eval Unit := do
  if ← asBool value then pure () else throw code

def unary (op : String) (value : Value) : Eval Value := do
  match op with
  | "-" => match value with
    | .quantity unit n => pure (.quantity unit (-n))
    | .rate unit currency n => pure (.rate unit currency (-n))
    | _ => pure (.num (-(← asNum value)))
  | "not" => pure (.flag (!(← asBool value)))
  | _ => throw "TARGET_UNKNOWN_UNARY_OPERATOR"

private def compareFuel : Nat → Value → Value → Eval Ordering
  | 0, _, _ => .error "TARGET_INCOMPARABLE_VALUES"
  | fuel + 1, left, right => do
    match left, right with
    | .tuple a, .tuple b =>
      if a.length != b.length then throw "TARGET_INCOMPARABLE_VALUES"
      let mut order := Ordering.eq
      for (x,y) in a.zip b do
        if order == .eq then order ← compareFuel fuel x y
      pure order
    | .num a, .num b => pure (if a < b then .lt else if a == b then .eq else .gt)
    | .quantity u a, .quantity v b =>
      if u != v then throw "TYPE_MISMATCH"
      pure (if a < b then .lt else if a == b then .eq else .gt)
    | .rate u c a, .rate v d b =>
      if u != v || c != d then throw "TYPE_MISMATCH"
      pure (if a < b then .lt else if a == b then .eq else .gt)
    | .instant a _, .instant b _ => pure (if a < b then .lt else if a == b then .eq else .gt)
    | .text a, .text b => pure (Ord.compare a b)
    | .flag a, .flag b => pure (Ord.compare a b)
    | _, _ => throw "TARGET_INCOMPARABLE_VALUES"

mutual
  private def comparisonSize : Value → Nat
    | .tuple values => 1 + comparisonListSize values
    | _ => 1
  private def comparisonListSize : List Value → Nat
    | [] => 0
    | x :: xs => comparisonSize x + comparisonListSize xs
end

def compare (left right : Value) : Eval Ordering := do
  match left, right with
  | .num a, .num b => pure (if a < b then .lt else if a == b then .eq else .gt)
  | .quantity u a, .quantity v b =>
    if u != v then throw "TYPE_MISMATCH"
    pure (if a < b then .lt else if a == b then .eq else .gt)
  | .rate u c a, .rate v d b =>
    if u != v || c != d then throw "TYPE_MISMATCH"
    pure (if a < b then .lt else if a == b then .eq else .gt)
  | .instant a _, .instant b _ => pure (if a < b then .lt else if a == b then .eq else .gt)
  | .text a, .text b => pure (Ord.compare a b)
  | .flag a, .flag b => pure (Ord.compare a b)
  | .tuple _, .tuple _ => compareFuel (comparisonSize left + comparisonSize right + 1) left right
  | _, _ => throw "TARGET_INCOMPARABLE_VALUES"

mutual
  private def valueSize : Value → Nat
    | .num _ | .quantity .. | .rate .. | .instant .. | .flag _ | .text _ | .absent => 1
    | .present value => 1 + valueSize value
    | .seq values | .tuple values | .map values => 1 + listSize values
    | .obj fields => 1 + fieldSize fields

  private def listSize : List Value → Nat
    | [] => 0
    | value :: rest => valueSize value + listSize rest

  private def fieldSize : List (String × Value) → Nat
    | [] => 0
    | (_, value) :: rest => valueSize value + fieldSize rest
end

private def structuralEqual : Nat → Value → Value → Bool
  | 0, _, _ => false
  | fuel + 1, left, right =>
    match left, right with
    | .num a, .num b => a == b
    | .quantity u a, .quantity v b => u == v && a == b
    | .rate u c a, .rate v d b => u == v && c == d && a == b
    | .instant a _, .instant b _ => a == b
    | .flag a, .flag b => a == b
    | .text a, .text b => a == b
    | .seq a, .seq b | .tuple a, .tuple b | .map a, .map b => a.length == b.length && (a.zip b).all fun (x, y) => structuralEqual fuel x y
    | .obj a, .obj b => a.length == b.length && a.all fun (key, x) =>
        match b.lookup key with | some y => structuralEqual fuel x y | none => false
    | .absent, .absent => true
    | .present a, .present b => structuralEqual fuel a b
    | _, _ => false

def equal (left right : Value) : Bool :=
  match left, right with
  | .num a, .num b => a == b
  | .quantity u a, .quantity v b => u == v && a == b
  | .rate u c a, .rate v d b => u == v && c == d && a == b
  | .instant a _, .instant b _ => a == b
  | .flag a, .flag b => a == b
  | .text a, .text b => a == b
  | _, _ => structuralEqual (valueSize left + valueSize right + 1) left right

def binary (op : String) (left right : Value) : Eval Value := do
  match op with
  | "+" => match left, right with
    | .num a, .num b => pure (.num (a + b))
    | _, _ => dimensionalArithmetic op left right
  | "-" => match left, right with
    | .num a, .num b => pure (.num (a - b))
    | _, _ => dimensionalArithmetic op left right
  | "*" => match left, right with
    | .num a, .num b => pure (.num (a * b))
    | _, _ => dimensionalArithmetic op left right
  | "/" => match left, right with
    | .num a, .num b =>
      if b == 0 then throw "DIVISION_BY_ZERO"
      pure (.num (a / b))
    | _, _ => dimensionalArithmetic op left right
  | "==" => pure (.flag (equal left right))
  | "!=" => pure (.flag (!equal left right))
  | "<" => pure (.flag ((← compare left right) == .lt))
  | "<=" => pure (.flag ((← compare left right) != .gt))
  | ">" => pure (.flag ((← compare left right) == .gt))
  | ">=" => pure (.flag ((← compare left right) != .lt))
  | _ => throw "TARGET_UNKNOWN_BINARY_OPERATOR"

def conditional (condition : Eval Value) (yes no : Unit → Eval Value) : Eval Value := do
  if ← asBool (← condition) then yes () else no ()

def conjunction (left : Eval Value) (right : Unit → Eval Value) : Eval Value := do
  if ← asBool (← left) then right () else pure (.flag false)

def disjunction (left : Eval Value) (right : Unit → Eval Value) : Eval Value := do
  if ← asBool (← left) then pure (.flag true) else right ()

def choose (arms : List (Eval Value × (Unit → Eval Value)))
    (fallback : Option (Unit → Eval Value)) : Eval Value := do
  let mut selected : List (Unit → Eval Value) := []
  for (predicate, body) in arms do
    if ← asBool (← predicate) then selected := body :: selected
  match selected with
  | [body] => body ()
  | [] => match fallback with
    | some body => body ()
    | none => throw "NO_APPLICABLE_RULE"
  | _ => throw "AMBIGUOUS_RULE"

/-- Registered selection validates identities before predicates, evaluates every
predicate in ID order, and invokes only the unique winning body. -/
def selectRules (priority : Bool)
    (arms : List (String × Int × (Unit → Eval Value) × (Unit → Eval Value)))
    (fallback : Option (String × (Unit → Eval Value))) : Eval Value := do
  let ids := arms.map (fun (id, _, _, _) => id) ++ fallback.toList.map Prod.fst
  if ids.any String.isEmpty then throw "INVALID_RULE_ID"
  if ids.eraseDups.length != ids.length then throw "DUPLICATE_RULE_ID"
  let ordered := arms.mergeSort (fun a b => a.1 ≤ b.1)
  let mut applicableArms := []
  for (id, rank, predicate, body) in ordered do
    if ← asBool (← predicate ()) then applicableArms := applicableArms ++ [(id, rank, body)]
  let winners := if priority then
      applicableArms.filter (fun (_, rank, _) => applicableArms.all (fun (_, other, _) => other ≤ rank))
    else applicableArms
  match winners with
  | [(_, _, body)] => body ()
  | [] => match fallback with
    | some (_, body) => body ()
    | none => throw "NO_APPLICABLE_RULE"
  | _ => throw "AMBIGUOUS_RULE"

def mapValues (value : Value) (body : Value → Eval Value) : Eval Value := do
  pure (.seq (← (← asList value).mapM body))

def filterValues (value : Value) (predicate : Value → Eval Value) : Eval Value := do
  let xs ← asList value
  pure (.seq (← xs.filterM (fun x => do asBool (← predicate x))))

def sumValues (value : Value) (body : Value → Eval Value) : Eval Value := do
  let xs ← asList value
  let mut total : Rat := 0
  for x in xs do
    total := total + (← asNum (← body x))
  pure (.num total)

/-- The checked body type supplies zero even when no element is visited. -/
def sumValuesFrom (zero value : Value) (body : Value → Eval Value) : Eval Value := do
  let mut total := zero
  for item in ← asList value do
    total ← binary "+" total (← body item)
  pure total

def absolute (value : Value) : Eval Value := do
  let n ← magnitude value
  pure (withMagnitude value (if n < 0 then -n else n))

private def insertKeyed (item : Value × Value) : List (Value × Value) → Eval (List (Value × Value))
  | [] => pure [item]
  | head :: tail => do
    if (← compare item.1 head.1) == .lt then pure (item :: head :: tail)
    else pure (head :: (← insertKeyed item tail))

def sortValues (value : Value) (body : Value → Eval Value) : Eval Value := do
  let xs ← asList value
  let mut sorted := []
  for x in xs do
    sorted ← insertKeyed (← body x, x) sorted
  pure (.seq (sorted.map Prod.snd))

def tupleValues (items : List (Eval Value)) : Eval Value := do
  pure (.tuple (← items.mapM id))

def tupleGet (source index : Value) : Eval Value := do
  let .tuple values := source | throw "TARGET_EXPECTED_TUPLE"
  let n ← asNum index
  if n.den != 1 || n < 0 then throw "INVALID_TUPLE_INDEX"
  let some value := values[n.num.toNat]? | throw "INVALID_TUPLE_INDEX"
  pure value

def mapEntries (source : Value) : Eval Value := do
  let .map entries := source | throw "TARGET_EXPECTED_MAP"
  pure (.seq entries)

def mapLookup (source key : Value) : Eval Value := do
  let .map entries := source | throw "TARGET_EXPECTED_MAP"
  for entry in entries do
    if equal (← field entry "key") key then return .present (← field entry "value")
  pure .absent

/-- All key projections complete before duplicate detection or value demand. -/
def makeMap (source : Value) (key value : Value → Eval Value) : Eval Value := do
  let rows ← asList source
  let keyed ← rows.mapM fun row => do pure (← key row, row)
  let mut ordered := []
  for row in keyed do ordered ← insertKeyed row ordered
  let keys := ordered.map Prod.fst
  for k in keys do
    if (keys.filter (equal k)).length > 1 then throw "DUPLICATE_MAP_KEY"
  let entries ← ordered.mapM fun (k,row) => do pure (.obj [("key",k),("value",← value row)])
  pure (.map entries)

def groupValues (source : Value) (key : Value → Eval Value) : Eval Value := do
  let rows ← asList source
  let keyed ← rows.mapM fun row => do pure (← key row, row)
  let mut ordered := []
  for row in keyed do ordered ← insertKeyed row ordered
  let mut entries := []
  let mut seen := []
  for (k,_) in ordered do
    unless seen.any (equal k) do
      seen := seen ++ [k]
      entries := entries ++ [.obj [("key",k),("value",.seq ((keyed.filter fun p => equal k p.1).map Prod.snd))]]
  pure (.map entries)

def joinValues (preserve : Bool) (left right : Value) (leftKey rightKey : Value → Eval Value) : Eval Value := do
  let left ← asList left
  let right ← asList right
  let lk ← left.mapM leftKey
  let rk ← right.mapM rightKey
  let mut pairs := []
  for (l,k) in left.zip lk do
    let matchedRows := (right.zip rk).filter fun (_,r) => equal k r
    if preserve && matchedRows.isEmpty then
      checkCollectionSize (pairs.length + 1)
      pairs := pairs ++ [.obj [("left",l),("right",.absent)]]
    else
      for (r,_) in matchedRows do
        checkCollectionSize (pairs.length + 1)
        pairs := pairs ++ [.obj [("left",l),("right",if preserve then .present r else r)]]
  pure (.seq pairs)

def requireSome (value code : Value) : Eval Value := do
  match value with
  | .present value => pure value
  | .absent => throw (← asText code)
  | _ => throw "TARGET_EXPECTED_OPTION"

def isSome (value : Value) : Eval Value := match value with
  | .present _ => pure (.flag true)
  | .absent => pure (.flag false)
  | _ => throw "TARGET_EXPECTED_OPTION"

def getOr (value : Value) (fallback : Unit → Eval Value) : Eval Value := match value with
  | .present x => pure x
  | .absent => fallback ()
  | _ => throw "TARGET_EXPECTED_OPTION"

def extrema (isMax : Bool) (left right : Value) : Eval Value := do
  let order ← compare left right
  pure (if (isMax && order == .lt) || (!isMax && order == .gt) then right else left)

def instant (value : Value) : Eval Value := do
  let seconds ← Instant.parse (← asText value)
  pure (.instant seconds (← Instant.render seconds))

def addCalendarMonths (date months policy : Value) : Eval Value := do
  let source ← asText date
  let count ← asNum months
  let mode ← asText policy
  unless count >= 0 && count.den == 1 do throw "CALENDAR_INVALID_MONTHS"
  pure (.text (← Calendar.addMonths source count.num.toNat mode))

def inPeriod (value period : Value) : Eval Value := do
  let d ← asText value
  let start ← asText (← field period "start")
  let finish ← asText (← field period "end")
  pure (.flag (start ≤ d && d < finish))

/-- Gregorian calendar quarters, with exclusive first-day end boundaries.
This does not infer a fiscal calendar or business-day convention. -/
def isCalendarQuarter (period : Value) : Eval Value := do
  let start ← asText (← field period "start")
  let finish ← asText (← field period "end")
  match start.splitOn "-", finish.splitOn "-" with
  | [year, month, firstDay], [endYear, endMonth, endDay] =>
    match year.toNat?, month.toNat?, endYear.toNat?, endMonth.toNat? with
    | some y, some m, some ey, some em =>
      pure (.flag (y > 0 && y < 10000 && ey > 0 && ey < 10000 &&
        [1, 4, 7, 10].contains m && firstDay == "01" && endDay == "01" &&
        em == (if m == 10 then 1 else m + 3) && ey == (if m == 10 then y + 1 else y)))
    | _, _, _, _ => pure (.flag false)
  | _, _ => pure (.flag false)

def quantize (value quantum mode : Value) : Eval Value := do
  unless sameDimension value quantum do throw "TYPE_MISMATCH"
  let x ← magnitude value
  let q ← magnitude quantum
  let mode ← asText mode
  if q ≤ 0 then throw "INVALID_QUANTUM"
  let scaled := x / q
  let lo := scaled.floor
  let hi := scaled.ceil
  let fraction := scaled - (lo : Rat)
  let rounded ← match mode with
    | "floor" => pure lo
    | "ceiling" => pure hi
    | "toward_zero" => pure (if scaled < 0 then hi else lo)
    | "half_even" => pure (if fraction < mkRat 1 2 then lo
        else if fraction > mkRat 1 2 then hi
        else if lo % 2 == 0 then lo else hi)
    | "half_away_from_zero" => pure (if fraction < mkRat 1 2 then lo
        else if fraction > mkRat 1 2 then hi
        else if scaled < 0 then lo else hi)
    | _ => throw "INVALID_ROUNDING_MODE"
  pure (withMagnitude value ((rounded : Rat) * q))

structure Settlement where
  emissions : Env
  closing : Env
  deriving Repr

private def rationalJson (value : Rat) : Lean.Json :=
  Lean.Json.mkObj [("numerator", .str (toString value.num)),
    ("denominator", .str (toString value.den))]

mutual
  def valueJson : Value → Lean.Json
    | .num value => rationalJson value
    | .quantity unit value => Lean.Json.mkObj [("value", rationalJson value), ("unit", .str unit)]
    | .rate unit currency value => Lean.Json.mkObj [("value", rationalJson value), ("per_unit", .str unit), ("currency", .str currency)]
    | .instant _ canonical => .str canonical
    | .flag value => .bool value
    | .text value => .str value
    | .seq values | .tuple values | .map values => .arr (valueListJson values).toArray
    | .obj fields => Lean.Json.mkObj (valueFieldsJson fields)
    | .absent => Lean.Json.mkObj [("none", .bool true)]
    | .present value => Lean.Json.mkObj [("some", valueJson value)]

  private def valueListJson : List Value → List Lean.Json
    | [] => []
    | value :: rest => valueJson value :: valueListJson rest

  private def valueFieldsJson : List (String × Value) → List (String × Lean.Json)
    | [] => []
    | (key, value) :: rest => (key, valueJson value) :: valueFieldsJson rest
end

def outcomeJson : Eval Settlement → Lean.Json
  | .ok result => Lean.Json.mkObj [
      ("status", .str "calculated"),
      ("emissions", valueJson (.obj result.emissions)),
      ("closing", valueJson (.obj result.closing)),
      ("diagnostics", .arr #[])]
  | .error code => Lean.Json.mkObj [
      ("status", .str "blocked"), ("emissions", Lean.Json.mkObj []),
      ("closing", Lean.Json.mkObj []),
      ("diagnostics", .arr #[Lean.Json.mkObj [("code", .str code)]])]

end SPL
