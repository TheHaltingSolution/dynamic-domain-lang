import SPL.Bindings
import SPL.Parser
import SPL.Elaborate
import SPL.Interpret

open SPL

private def value (text : String) : IO Value :=
  match Bindings.decode Check.instantTy (.str text) with
  | .ok result => pure result
  | .error code => throw (IO.userError s!"{text}: {code}")

private def canonical (source expected : String) : IO Unit := do
  let actual ← value source
  unless valueJson actual == .str expected do
    throw (IO.userError s!"canonical timestamp: {source}: {valueJson actual}")

private def ordered (left right : String) (expected : Ordering) : IO Unit := do
  match SPL.compare (← value left) (← value right) with
  | .ok result => unless result == expected do throw (IO.userError "Timestamp chronology differs")
  | .error code => throw (IO.userError code)

def main : IO Unit := do
  canonical "2026-07-02T23:30:00-02:00" "2026-07-03T01:30:00Z"
  canonical "2026-07-03T01:00:00+02:00" "2026-07-02T23:00:00Z"
  canonical "2024-03-01T00:30:00+01:00" "2024-02-29T23:30:00Z"
  canonical "2026-01-01T00:30:00+01:00" "2025-12-31T23:30:00Z"
  canonical "2026-07-03t00:00:00.125000z" "2026-07-03T00:00:00.125Z"
  canonical "0001-01-01T00:00:00Z" "0001-01-01T00:00:00Z"
  canonical "9999-12-31T23:59:59.9Z" "9999-12-31T23:59:59.9Z"
  ordered "2026-07-03T01:00:00+02:00" "2026-07-03T00:00:00Z" .lt
  ordered "2026-07-02T23:00:00-02:00" "2026-07-03T00:00:00Z" .gt
  ordered "2026-07-03T02:00:00+02:00" "2026-07-03T00:00:00Z" .eq
  ordered "2026-07-03T00:00:00.00000000000000000001Z"
    "2026-07-03T00:00:00.00000000000000000002Z" .lt
  unless equal (← value "2026-07-03T02:00:00+02:00") (← value "2026-07-03T00:00:00Z") do
    throw (IO.userError "Equivalent offsets are unequal")
  for invalid in ["2026-07-03", "2026-07-03T00:00:00", "2026-07-03T00:00:00-00:00",
      "2026-07-03T00:00:60Z", "2026-07-03T24:00:00Z", "2025-02-29T00:00:00Z",
      "2026-07-03T00:00:00.Z", "2026-07-03T00:00:00+24:00",
      "0001-01-01T00:00:00+00:01", "9999-12-31T23:59:59-00:01"] do
    match Bindings.decode Check.instantTy (.str invalid) with
    | .error "INVALID_INSTANT" => pure ()
    | _ => throw (IO.userError s!"Malformed timestamp accepted: {invalid}")
  let header := "schedule InstantChecks language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { "
  let source := header ++ "input stamp: Instant; require stamp < instant(\"2026-07-03T00:00:00Z\") else \"CUTOFF\"; }"
  match Parser.parse source >>= fun schedule => do Check.check schedule; pure schedule with
  | .ok _ => pure ()
  | .error diagnostic => throw (IO.userError s!"Instant builtin failed: {repr diagnostic}")
  let program ← match Parser.parse source >>= Elaborate.elaborate with
    | .ok program => pure program
    | .error diagnostic => throw (IO.userError s!"Instant elaboration failed: {repr diagnostic}")
  match (Interpret.interpret program [("stamp", ← value "2026-07-03T01:00:00+02:00")] []).result with
  | .ok _ => pure ()
  | .error code => throw (IO.userError s!"Instant builtin interpretation: {code}")
  match (Interpret.interpret program [("stamp", ← value "2026-07-03T02:00:00+02:00")] []).result with
  | .error "CUTOFF" => pure ()
  | _ => throw (IO.userError "Instant builtin cutoff equality was not strict")
  let mixed := header ++ "input stamp: Instant; require stamp < date \"2026-07-03\" else \"CUTOFF\"; }"
  match Parser.parse mixed >>= fun schedule => do Check.check schedule; pure schedule with
  | .error diagnostic => unless diagnostic.code == "TYPE_MISMATCH" do
      throw (IO.userError s!"Unexpected mixed-type diagnostic: {diagnostic.code}")
  | .ok _ => throw (IO.userError "Instant/Date comparison incorrectly accepted")
  IO.println "Exact RFC3339 normalization and strict chronology checks passed."
