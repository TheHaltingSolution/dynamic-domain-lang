import SPL

/-! Self-contained native smoke executable. Importing SPL kernel-checks its
explicitly bounded arithmetic-lowering proof. The larger parser, bindings and
emitter regression scripts are run separately; they are not Lake libraries. -/

private def header : String :=
  "schedule Smoke language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { "

private def checked (source : String) : Except SPL.Syntax.Diagnostic SPL.Syntax.Schedule := do
  let schedule ← SPL.Parser.parse source
  SPL.Check.check schedule
  return schedule

def main : IO Unit := do
  for (path, expectedName) in [
      ("cases/sv/sv01.spl", "SkourasVenturaPilot"),
      ("cases/sv/rq07.spl", "SkourasVenturaPostingPilot"),
      ("cases/lg/lg01.spl", "LionsgateDerivativePilot")] do
    let schedule ← match checked (← IO.FS.readFile path) with
      | .ok schedule => pure schedule
      | .error diagnostic => throw (IO.userError s!"Native fixture failed: {repr diagnostic}")
    unless schedule.name == expectedName do throw (IO.userError "Incorrect parsed schedule identity")
    match SPL.Emit.emit schedule with
    | .ok generated =>
      unless generated.contains '←' && generated.length > 200 do
        throw (IO.userError "Native emission is incomplete")
    | .error diagnostic => throw (IO.userError s!"Native emitter failed: {repr diagnostic}")
  let invalid := header ++ "define invalid = USD 1 * USD 2; }"
  match checked invalid with
  | .error diagnostic =>
    unless diagnostic.code == "TYPE_MISMATCH" do throw (IO.userError "Unexpected type diagnostic")
  | .ok _ => throw (IO.userError "Money times money incorrectly accepted")
  for source in ["{\"a\":\"1\",\"a\":\"2\"}", "{\"number\":0.1}", "{\"missing\":null}", "{\"bad\":\"\\uD800\"}"] do
    match SPL.Bindings.parseStrict source with
    | .error _ => pure ()
    | .ok _ => throw (IO.userError "Strict native JSON accepted invalid transport")
  let bindings ← match SPL.Bindings.parseStrict "{\"n\":{\"value\":\"12.50\",\"currency\":\"USD\"}}" with
    | .ok json => pure json
    | .error message => throw (IO.userError message)
  let types := [("n", SPL.Syntax.TypeExpr.named "Money" [.named "USD" []])]
  match SPL.Bindings.decodeBindings types bindings with
  | .ok [("n", .num amount)] =>
    unless amount == mkRat 25 2 do throw (IO.userError "Exact native money decoding changed")
  | _ => throw (IO.userError "Native typed binding decoding failed")
  IO.println "SPL native smoke passed (parser, checker, emitter, strict bindings, scoped kernel proof)."
