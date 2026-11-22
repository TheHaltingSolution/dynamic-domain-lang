import SPL.Calendar
import SPL.Bindings
import SPL.Parser
import SPL.Elaborate
import SPL.Interpret
import SPL.Emit

open SPL

private def checkDate (source : String) (months : Nat) (policy expected : String) : IO Unit := do
  match Calendar.addMonths source months policy with
  | .ok actual => unless actual == expected do
      throw (IO.userError s!"Calendar mismatch: {source} + {months} {policy}")
  | .error code => throw (IO.userError code)
  match addCalendarMonths (.text source) (.num months) (.text policy) with
  | .ok (.text value) => unless value == expected do throw (IO.userError "Runtime mismatch")
  | _ => throw (IO.userError "Runtime calendar failed")

private def header := "schedule CalendarChecks language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { "

private def compile (body : String) : IO IR.Program :=
  match Parser.parse (header ++ body ++ "}") >>= Elaborate.elaborate with
  | .ok p => pure p
  | .error d => throw (IO.userError s!"Calendar source rejected: {repr d}")

private def m (id : Nat) (ty : Check.Ty) : IR.Meta := { id, ty, span := {} }

def main : IO Unit := do
  for (source, months, expected) in [
      ("2025-01-31", 1, "2025-02-28"), ("2024-01-31", 1, "2024-02-29"),
      ("2024-02-29", 12, "2025-02-28"), ("2000-01-31", 1, "2000-02-29"),
      ("1900-01-31", 1, "1900-02-28"), ("2100-01-31", 1, "2100-02-28"),
      ("2025-01-31", 0, "2025-01-31"), ("2025-02-28", 1, "2025-03-28"),
      ("2025-01-31", 2, "2025-03-31"), ("2024-12-31", 2, "2025-02-28"),
      ("0001-01-01", 119987, "9999-12-01"), ("9999-12-31", 0, "9999-12-31")] do
    checkDate source months "clamp_day" expected
  checkDate "2024-02-29" 48 "reject_invalid_day" "2028-02-29"
  match Calendar.addMonths "2025-01-31" 1 "reject_invalid_day" with
  | .error "CALENDAR_INVALID_TARGET_DAY" => pure ()
  | _ => throw (IO.userError "Invalid target day accepted")
  match Calendar.addMonths "9999-12-31" 1 "clamp_day" with
  | .error "CALENDAR_YEAR_RANGE" => pure ()
  | _ => throw (IO.userError "Out of range year accepted")
  match Calendar.addMonths "2025-01-01" 0 "unknown" with
  | .error "CALENDAR_UNSUPPORTED_POLICY" => pure ()
  | _ => throw (IO.userError "Zero months skipped policy validation")
  for count in [(-1 : Rat), mkRat 1 2] do
    match addCalendarMonths (.text "2025-01-01") (.num count) (.text "clamp_day") with
    | .error "CALENDAR_INVALID_MONTHS" => pure ()
    | _ => throw (IO.userError "Malformed month count accepted")
  for bad in ["0000-01-01", "2025-02-29", "2025-1-01", "10000-01-01"] do
    match Bindings.decode Check.dateTy (.str bad) with
    | .error "INVALID_DATE" => pure ()
    | _ => throw (IO.userError "Invalid transported Date accepted")
  let p ← compile "emit \"deadline\" = add_calendar_months(date \"2025-01-31\", 1, \"clamp_day\");"
  match (Interpret.interpret p [] []).result with
  | .ok settlement =>
    match settlement.emissions.lookup "deadline" with
    | some (.text "2025-02-28") => pure ()
    | _ => throw (IO.userError "Native IR calendar result mismatch")
  | .error code => throw (IO.userError code)
  let lazyProgram ← compile "emit \"ok\" = if true then date \"2025-01-01\" else add_calendar_months(date \"2025-01-31\", 1, \"reject_invalid_day\");"
  match (Interpret.interpret lazyProgram [] []).result with
  | .ok _ => pure ()
  | .error code => throw (IO.userError ("Unused calendar body demanded: " ++ code))
  -- The generic call validator rechecks the new signature and rejects forged IR.
  let forged : IR.Program := { p with declarations := [.emit (m 0 Check.intTy) "bad"
    (.call (m 1 Check.intTy) "add_calendar_months" [
      .date (m 2 Check.dateTy) "2025-01-31", .number (m 3 (.atom "Nat")) "1",
      .text (m 4 Check.textTy) "clamp_day"])] }
  match ValidateIR.validate forged, Emit.emitIR forged with
  | .error _, .error _ => pure ()
  | _, _ => throw (IO.userError "Forged calendar result type accepted")
  IO.println "Calendar month policy, native IR, transport and defensive checks passed."
