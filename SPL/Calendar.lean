/-! DYN-CAL-01: pure, total Gregorian calendar-month addition. This primitive is
shared by native interpretation and target execution, not a preservation proof.
Supported civil dates have years 0001..9999; policies are explicit and closed. -/
namespace SPL.Calendar

private def monthLength (year month : Nat) : Nat :=
  if month == 2 then
    if year % 4 == 0 && (year % 100 != 0 || year % 400 == 0) then 29 else 28
  else if [4, 6, 9, 11].contains month then 30 else 31

private def parseDate (source : String) : Except String (Nat × Nat × Nat) := do
  let [ys, ms, ds] := source.splitOn "-" | throw "INVALID_DATE"
  unless ys.length == 4 && ms.length == 2 && ds.length == 2 &&
      [ys, ms, ds].all (fun s => s.toList.all (fun c => c >= '0' && c <= '9')) do
    throw "INVALID_DATE"
  let some year := ys.toNat? | throw "INVALID_DATE"
  let some month := ms.toNat? | throw "INVALID_DATE"
  let some day := ds.toNat? | throw "INVALID_DATE"
  unless year >= 1 && year <= 9999 && month >= 1 && month <= 12 &&
      day >= 1 && day <= monthLength year month do throw "INVALID_DATE"
  pure (year, month, day)

private def pad (width number : Nat) : String :=
  let text := toString number
  String.ofList (List.replicate (width - text.length) '0') ++ text

/-- Direct addition from the original date; clamping does not preserve end-of-month
status and repeated addition need not equal one combined addition. -/
def addMonths (source : String) (months : Nat) (policy : String) : Except String String := do
  let (year, month, day) ← parseDate source
  unless ["clamp_day", "reject_invalid_day"].contains policy do throw "CALENDAR_UNSUPPORTED_POLICY"
  let index := (year - 1) * 12 + month - 1 + months
  let targetYear := index / 12 + 1
  let targetMonth := index % 12 + 1
  unless targetYear <= 9999 do throw "CALENDAR_YEAR_RANGE"
  let limit := monthLength targetYear targetMonth
  if day > limit && policy == "reject_invalid_day" then throw "CALENDAR_INVALID_TARGET_DAY"
  pure (pad 4 targetYear ++ "-" ++ pad 2 targetMonth ++ "-" ++ pad 2 (min day limit))

end SPL.Calendar
