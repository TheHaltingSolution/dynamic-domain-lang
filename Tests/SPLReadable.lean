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

private def multiple (rules : String) (extra : String := "") : String :=
  tiny rules ("  input first_party: Id<Participant>;\n  input second_party: Id<Participant>;\n" ++
    "  Settle \"A\" with first_party.\n  Settle \"B\" with second_party.\n" ++
    "  Bind \"Participant\" to settlement_participant.\n" ++ extra)

private def expectCheckFailure (source code : String) : IO Unit := do
  let schedule ← parsed source
  match SPL.Check.check schedule with
  | .ok _ => throw (IO.userError "Invalid readable source checked successfully")
  | .error diagnostic => unless diagnostic.code == code do
      throw (IO.userError s!"Expected {code}, got {repr diagnostic}")

def main : IO Unit := do
  let multiSource ← IO.FS.readFile "cases/readable-multi/two-participants-readable.spl"
  checked multiSource
  let multi ← parsed multiSource
  let roles := multi.declarations.filterMap fun declaration => match declaration with
    | .define span name (some (.named "Id" [.named "Participant" []])) _ _ => some (name, span.line)
    | _ => none
  unless roles.length == 2 && roles[0]!.1 != roles[1]!.1 && roles.map (·.2) == [2, 5] do
    throw (IO.userError "Multiple headings lost fresh typed participant roles or heading spans")
  let columns := multi.declarations.filterMap fun declaration => match declaration with
    | .emit span _ (.record _ fields) => some (span.line, fields.map (·.1))
    | _ => none
  unless columns == [(4, ["participant_id", "amount"]), (7, ["participant_id", "amount"])] do
    throw (IO.userError "Multiple headings changed visible report columns or authored spans")
  checked (multiple "For settlement with A:\n  Report \"one\": Participant.\nFor settlement with A:\n  Report \"two\": Participant.")
  let nested ← parsed (multiple "For settlement with A:\n  Report \"before\": Participant.\n  For settlement with B:\n    Report \"inner\": Participant.\n  Report \"after\": Participant.")
  let nestedRoles := nested.declarations.filterMap fun declaration => match declaration with
    | .emit _ _ (.name _ name) => some name
    | _ => none
  unless nestedRoles.length == 3 && nestedRoles[0]! == nestedRoles[2]! && nestedRoles[0]! != nestedRoles[1]! do
    throw (IO.userError "Nested heading did not restore its enclosing participant role")
  checked (multiple "For settlement with A:\n  For each Item:\n    Report by Row: {party: Participant, value: item}.\n  Report \"one\": rows.\nFor settlement with B:\n  Report \"two\": Participant." "  input items: List<Int>;\n  Iterate \"Item\" as item in items into rows.\n")
  let collision := multiple "For settlement with A:\n  Report \"one\": Participant.\nFor settlement with B:\n  Report \"two\": readable_settlement_participant_1." "  input readable_settlement_participant_0: Id<Participant>;\n"
  match SPL.Readable.expand collision with
  | .error diagnostic => throw (IO.userError s!"Collision expansion failed: {repr diagnostic}")
  | .ok expansion => unless (expansion.source.splitOn "define readable_settlement_participant_2 ").length == 2 &&
      (expansion.source.splitOn "define readable_settlement_participant_3 ").length == 2 do
      throw (IO.userError "Generated names captured an authored definition or unknown reference")
  expectCheckFailure collision "UNRESOLVED_NAME"
  let two := "For settlement with A:\n  Report \"one\": Participant.\nFor settlement with B:\n  Report \"two\": Participant."
  expectFailure (multiple two "  Settle \"A\" with second_party.\n")
  expectFailure (multiple (two.replace "with B:" "with Unknown:"))
  expectCheckFailure ((multiple two).replace "input first_party: Id<Participant>;" "input first_party: Id<Pool>;") "TYPE_MISMATCH"
  expectFailure (multiple (two ++ "\nReport \"outside\": Participant.")) "READABLE_SETTLEMENT_ROLE"
  expectFailure (multiple (two.replace "Report \"one\": Participant." "Report \"one\": {value: map(items, settlement_participant => settlement_participant)}.") "  input items: List<Int>;\n") "READABLE_SETTLEMENT_ROLE"
  let literals ← parsed (multiple "For settlement with A:\n  Report \"one\": {settlement_participant: Participant, selected: holder.settlement_participant, text: \"settlement_participant\"}.\nFor settlement with B:\n  Report \"two\": Participant." "  define holder = {settlement_participant: USD 3};\n")
  let literalFields : List (List (String × Expr)) := literals.declarations.filterMap fun declaration => match declaration with
    | .emit _ "one" (.record _ fields) => some fields
    | _ => none
  match literalFields with
  | [[("settlement_participant", .name _ _), ("selected", .field _ _ "settlement_participant"), ("text", .text _ "settlement_participant")]] => pure ()
  | _ => throw (IO.userError "Role rewriting changed a field label, selector or quoted string")
  expectCheckFailure (multiple "For settlement with A:\n  Amount is USD 1.\nFor settlement with B:\n  Amount is USD 2." "  Bind \"Amount\" to amount.\n") "DUPLICATE_NAME"
  expectCheckFailure (multiple "For settlement with A:\n  Report \"same\": Participant.\nFor settlement with B:\n  Report \"same\": Participant.") "DUPLICATE_OUTPUT"
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
