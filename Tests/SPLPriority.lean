import SPL

/-! RULE-01 native runtime structure and defensive fabricated-IR checks.
The compiler proof remains the separately bounded scalar proof. -/
open SPL

private def m (id : Nat) (ty : IR.Ty) : IR.Meta := { id, ty, span := {} }

private def program (expr : IR.Expr) : IR.Program := {
  name := "PriorityArtifact", language := "spl/0.1-draft", core := "spl-core/0.1-draft",
  schema := "spl-data/0.1-draft", span := {}, declarations := [.emit (m 0 Check.usdTy) "value" expr] }

private def rejected (label : String) (expr : IR.Expr) : IO Unit := do
  let p := program expr
  match ValidateIR.validate p, Emit.emitIR p, (Interpret.interpret p [] []).result with
  | .error d, .error _, .error "INVALID_IR" =>
    unless d.code == "INVALID_IR" do throw (IO.userError (label ++ ": incorrect validation diagnostic"))
  | _, _, _ => throw (IO.userError (label ++ ": fabricated selection escaped validation"))

def main : IO Unit := do
  let yes : Unit → Eval Value := fun _ => pure (.flag true)
  let no : Unit → Eval Value := fun _ => pure (.flag false)
  let body : Unit → Eval Value := fun _ => pure (.num 20)
  let bad : Unit → Eval Value := fun _ => throw "BODY_DEMANDED"
  let predicateBad : Unit → Eval Value := fun _ => throw "PREDICATE_DEMANDED"
  for (result, expected) in [
      (selectRules true [("a", -5, yes, body)] (some ("fallback", bad)), "ok"),
      (selectRules true [("a", 0, no, bad)] (some ("fallback", body)), "ok"),
      (selectRules true [("a", 0, no, bad), ("a", 1, no, body)] none, "DUPLICATE_RULE_ID"),
      (selectRules true [("a", 1, yes, body), ("b", 0, predicateBad, bad)] none, "PREDICATE_DEMANDED"),
      (selectRules true [("a", 1, yes, bad), ("b", 1, yes, bad)] none, "AMBIGUOUS_RULE"),
      (selectRules false [("a", 0, yes, bad), ("b", 0, yes, bad)] none, "AMBIGUOUS_RULE"),
      (selectRules true [("a", 0, yes, bad)] (some ("fallback", body)), "BODY_DEMANDED")] do
    match result with
    | .ok (.num n) => unless expected == "ok" && n == 20 do throw (IO.userError "Unexpected selection value")
    | .error code => unless code == expected do throw (IO.userError ("Unexpected selection diagnostic " ++ code))
    | _ => throw (IO.userError "Unexpected selection value type")
  let usd := Check.usdTy
  let bool := Check.boolTy
  rejected "duplicate rule IDs" (.selectRules (m 1 usd) true [
    ("a", 1, .boolean (m 2 bool) false, .money (m 3 usd) "USD" "20"),
    ("a", 2, .boolean (m 4 bool) false, .money (m 5 usd) "USD" "40")] none)
  rejected "wrong body type" (.selectRules (m 1 usd) true [
    ("a", 1, .boolean (m 2 bool) true, .boolean (m 3 bool) true)] none)
  rejected "wrong predicate type" (.selectRules (m 1 usd) true [
    ("a", 1, .money (m 2 usd) "USD" "1", .money (m 3 usd) "USD" "20")] none)
  IO.println "SPL registered priority checks passed (structure, demand order, laziness, invalid IR)."
