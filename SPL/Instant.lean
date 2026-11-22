import Init.Data.Rat

/-! Exact, explicit-zone RFC3339 instants. Seconds are measured from Gregorian
0001-01-01T00:00:00Z; fractions remain rational. Leap seconds and unknown offsets
(-00:00) require a separate timescale policy and are rejected in this profile. -/
namespace SPL.Instant

private def digits (s : String) : Bool :=
  !s.isEmpty && s.toList.all (fun c => c >= '0' && c <= '9')

private def slice (s : String) (start count : Nat) : String :=
  String.ofList (s.toList.drop start |>.take count)

def parse (text : String) : Except String Rat := do
  unless text.length >= 20 do throw "INVALID_INSTANT"
  unless slice text 4 1 == "-" && slice text 7 1 == "-" &&
      ["T", "t"].contains (slice text 10 1) && slice text 13 1 == ":" &&
      slice text 16 1 == ":" do throw "INVALID_INSTANT"
  let components := [(0, 4), (5, 2), (8, 2), (11, 2), (14, 2), (17, 2)]
  unless components.all (fun (start, count) => digits (slice text start count)) do
    throw "INVALID_INSTANT"
  let year := (slice text 0 4).toNat!
  let month := (slice text 5 2).toNat!
  let day := (slice text 8 2).toNat!
  let hour := (slice text 11 2).toNat!
  let minute := (slice text 14 2).toNat!
  let second := (slice text 17 2).toNat!
  let leap := year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
  let lengths : List Nat := [31, if leap then 29 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  unless year > 0 && month > 0 && month <= 12 && day > 0 &&
      day <= lengths[month - 1]! && hour < 24 && minute < 60 && second < 60 do
    throw "INVALID_INSTANT"
  let suffix := slice text 19 (text.length - 19)
  let (fraction, zone) ← if suffix.startsWith "." then do
      let ds := (suffix.toList.drop 1).takeWhile (fun c => c >= '0' && c <= '9')
      unless !ds.isEmpty do throw "INVALID_INSTANT"
      let f := String.ofList ds
      pure (mkRat (f.toNat! : Int) (10 ^ f.length), slice suffix (1 + f.length) suffix.length)
    else pure (0, suffix)
  let offset : Int ← if zone == "Z" || zone == "z" then pure 0 else do
    unless zone.length == 6 && ["+", "-"].contains (slice zone 0 1) &&
        slice zone 3 1 == ":" && digits (slice zone 1 2) && digits (slice zone 4 2) &&
        zone != "-00:00" do throw "INVALID_INSTANT"
    let h := (slice zone 1 2).toNat!
    let m := (slice zone 4 2).toNat!
    unless h < 24 && m < 60 do throw "INVALID_INSTANT"
    let n : Int := h * 3600 + m * 60
    pure (if zone.startsWith "-" then -n else n)
  let previous := year - 1
  let days := previous * 365 + previous / 4 - previous / 100 + previous / 400 +
    (lengths.take (month - 1)).foldl (· + ·) 0 + day - 1
  let seconds : Int := days * 86400 + hour * 3600 + minute * 60 + second
  unless seconds - offset >= 0 && seconds - offset < 315537897600 do throw "INVALID_INSTANT"
  pure ((seconds - offset : Int) + fraction)

private def yearStart (year : Nat) : Nat :=
  let previous := year - 1
  previous * 365 + previous / 4 - previous / 100 + previous / 400

private def findYear : Nat → Nat → Nat → Nat → Nat
  | 0, low, _, _ => low
  | fuel + 1, low, high, days =>
    if high <= low + 1 then low else
    let middle := (low + high) / 2
    if yearStart middle <= days then findYear fuel middle high days
    else findYear fuel low middle days

private def pad (width : Nat) (n : Nat) : String :=
  let text := toString n
  String.ofList (List.replicate (width - text.length) '0') ++ text

private def fractionDigits : Nat → Nat → Nat → String
  | 0, _, _ => ""
  | fuel + 1, remainder, denominator =>
    if remainder == 0 then "" else
    toString (remainder * 10 / denominator) ++
      fractionDigits fuel (remainder * 10 % denominator) denominator

/-- Canonical UTC rendering for finite-decimal seconds in the supported year range. -/
def render (value : Rat) : Except String String := do
  let whole := value.floor
  unless whole >= 0 && whole < (yearStart 10000 : Int) * 86400 do throw "INVALID_INSTANT"
  let days := whole.toNat / 86400
  let year := findYear 20 1 10000 days
  let leap := year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
  let lengths : List Nat := [31, if leap then 29 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  let mut ordinal := days - yearStart year
  let mut month := 1
  for length in lengths do
    if ordinal >= length then
      ordinal := ordinal - length
      month := month + 1
    else break
  let time := whole.toNat % 86400
  let fraction := value - (whole : Rat)
  let ds := fractionDigits ((toString fraction.den).length * 4) fraction.num.toNat fraction.den
  -- A parsed RFC3339 fraction always has a denominator dividing a power of ten.
  unless ds.isEmpty || (mkRat (ds.toNat! : Int) (10 ^ ds.length)) == fraction do
    throw "INVALID_INSTANT"
  pure (pad 4 year ++ "-" ++ pad 2 month ++ "-" ++ pad 2 (ordinal + 1) ++ "T" ++
    pad 2 (time / 3600) ++ ":" ++ pad 2 (time / 60 % 60) ++ ":" ++ pad 2 (time % 60) ++
    (if ds.isEmpty then "" else "." ++ ds) ++ "Z")

end SPL.Instant
