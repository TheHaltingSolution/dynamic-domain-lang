import SPL.Readable
import SPL.Check

/-! Controlled readable frontend tests. Arithmetic expectations are authored
separately from syntax expansion; complete compiler verification is deferred. -/
open SPL.Syntax

private def tiny (rules : String) (bindings : String := "  Bind \"Amount\" to amount.\n") : String :=
  "Participation Schedule for A and B\n" ++ rules ++ "\nBindings:\n" ++
  "  Schedule Generic.\n" ++
  "  Using language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\".\n" ++ bindings

private def parsed (source : String) : IO Schedule :=
  match SPL.Readable.parse source with
  | .ok schedule => pure schedule
  | .error diagnostic => throw (IO.userError s!"Readable parsing failed: {repr diagnostic}")

private def expectFailure (source : String) (code : String := "READABLE_SYNTAX_ERROR") : IO Unit :=
  match SPL.Readable.parse source with
  | .ok _ => throw (IO.userError "Invalid readable source was accepted")
  | .error diagnostic => unless diagnostic.code == code do
      throw (IO.userError s!"Expected {code}, got {repr diagnostic}")

private def checked (source : String) : IO Unit := do
  let schedule ← parsed source
  match SPL.Check.check schedule with
  | .ok _ => pure ()
  | .error diagnostic => throw (IO.userError s!"Readable checking failed: {repr diagnostic}")

def main : IO Unit := do
  for (path, count) in [
      ("cases/sv/sv01-readable.spl", 18),
      ("cases/sv/rq07-readable.spl", 18),
      ("cases/lg/lg01-readable.spl", 50)] do
    let source ← IO.FS.readFile path
    unless SPL.Readable.isReadable source do throw (IO.userError "Readable detection failed")
    let schedule ← parsed source
    unless schedule.declarations.length == count do
      throw (IO.userError s!"Unexpected readable declaration count in {path}: {schedule.declarations.length}")
    checked source
  let percent ← parsed (tiny "Amount is 7.500% of USD 100.\nReport \"value\": Amount.")
  match percent.declarations with
  | [.define span "amount" none (.binary _ "*"
        (.binary _ "/" (.number _ "7.500") (.number _ "100")) (.money _ "USD" "100")) none,
      .emit _ "value" _] =>
    unless span.line == 2 do throw (IO.userError "Percentage definition lost its authored span")
  | _ => throw (IO.userError "Percentage lexeme or controlled multiplication changed")
  let branches ← parsed (tiny "If true:\n  Amount is 25% of USD 100.\nOtherwise:\n  Amount is 10% of USD 100.\nReport \"value\": Amount.")
  match branches.declarations with
  | .define span "amount" none (.ite _ _ a b) none :: _ =>
    unless span.line == 2 && a.span.line == 3 && b.span.line == 5 do
      throw (IO.userError s!"Branch spans were not preserved: {span.line}, {a.span.line}, {b.span.line}")
  | _ => throw (IO.userError "Conditional definition did not expand compositionally")
  let text ← parsed (tiny "Amount is \"Amount less 25% of Cash\".\nReport \"value\": Amount.")
  match text.declarations with
  | .define _ _ _ (.text _ "Amount less 25% of Cash") _ :: _ => pure ()
  | _ => throw (IO.userError "Readable rewriting changed a quoted string")
  let incorporated ← parsed (tiny "Incorporate policy \"cost-incurred@1\".\nAmount is USD 1.\nReport \"value\": Amount.")
  match incorporated.declarations with
  | .define span "incorporated_policy_0" (some (.named "Text" [])) (.text _ "cost-incurred@1") none :: _ =>
    unless span.line == 2 do throw (IO.userError "Incorporation lost its authored span")
  | _ => throw (IO.userError "Incorporation did not preserve typed policy identity")
  for source in [
      tiny "Amount is 10% of USD 100",
      tiny "If true:\n  Amount is USD 1.\nReport \"value\": Amount.",
      tiny "If true:\n  Amount is USD 1.\nOtherwise:\n  Other is USD 2.",
      tiny "Report \"value\": Amount, Other.",
      tiny "For each Something:\n  Report by Item: Amount.",
      tiny "Amount is 1.\nOtherwise:\n  Amount is 2.",
      tiny "Incorporate policy \"cost-incurred\".\nAmount is USD 1.",
      tiny "Incorporate policy \"cost@1@2\".\nAmount is USD 1.",
      tiny "Incorporate policy \"cost@1\".\nIncorporate policy \"cost@1\".\nAmount is USD 1.",
      tiny "For settlement with Party:\n  Incorporate policy \"cost@1\".\n  Amount is USD 1." "  Bind \"Amount\" to amount.\n  Settle \"Party\" with missing.\n",
      tiny "For settlement with Unknown Party:\n  Amount is 1.",
      tiny "Account for each fiscal month." "  Bind \"fiscal month\" to missing.\n",
      tiny "Amount is 1." "  Bind \"Amount\" to x.\n  Bind \"Amount\" to y.\n"] do
    expectFailure source
  for source in [tiny " Amount is 1.", tiny "Amount is 1.\n  Amount is 2.",
      tiny "\tAmount is 1."] do
    expectFailure source "READABLE_INDENTATION"
  -- Closed parser errors are remapped to the authored rule, not footer/expansion.
  match SPL.Readable.parse (tiny "Amount is USD .5.") with
  | .error diagnostic => unless diagnostic.span.line == 2 do
      throw (IO.userError "Parser diagnostic lost authored source line")
  | .ok _ => throw (IO.userError "Malformed money literal accepted")
  let changed := (← IO.FS.readFile "cases/sv/sv01-readable.spl").replace "Skouras" "Orion" |>.replace "Ventura" "Lyra" |>.replace "25%" "30%"
  checked changed
  IO.println "Readable SPL parsing, explicit bindings, percentages, branches and source spans passed."
