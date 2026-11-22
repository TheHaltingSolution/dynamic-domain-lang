import SPL.Parser
import SPL.Elaborate
import SPL.Bindings
import SPL.Interpret

open SPL

private def ensure (condition : Bool) (message : String) : IO Unit :=
  unless condition do throw (IO.userError message)

private def compile (source : String) : IO IR.Program :=
  match Parser.parse source >>= Elaborate.elaborate with
  | .ok program => pure program
  | .error d => throw (IO.userError s!"{d.code}: {d.message}")

private def fragment (body : String) : IO IR.Program := compile
  ("schedule NativeTrace language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { " ++ body ++ " }")

private def output (outcome : Interpret.Outcome) (name : String) : IO Value :=
  match outcome.result with
  | .ok result => match result.emissions.lookup name with
    | some value => pure value
    | none => throw (IO.userError ("missing output " ++ name))
  | .error code => throw (IO.userError code)

private def decodeProgram (program : IR.Program) (json : Lean.Json) : Except String (Env × Env) := do
  let inputJson ← json.getObjVal? "inputs"
  let openingJson ← json.getObjVal? "openings"
  let inputs := program.declarations.filterMap fun d => match d with
    | .input m name => some (name, m.ty) | _ => none
  let openings := program.declarations.filterMap fun d => match d with
    | .opening m name _ => some (name, m.ty) | _ => none
  pure (← inputs.mapM (fun (name, ty) => do pure (name, ← Bindings.decode ty (← inputJson.getObjVal? name))),
    ← openings.mapM (fun (name, ty) => do pure (name, ← Bindings.decode ty (← openingJson.getObjVal? name))))

private def validateDAG (outcome : Interpret.Outcome) : IO Unit := do
  let mut ready : List String := []
  for node in outcome.trace.ordered do
    ensure (node.dependencies.all ready.contains) ("dependency order or missing child at " ++ node.id)
    ensure (!ready.contains node.id) "duplicate trace key"
    ready := node.id :: ready

def main : IO Unit := do
  -- Real case schemas are decoded before interpretation, including inactive inputs.
  for (source, binding, expected) in [
      ("cases/sv/sv01.spl", "cases/sv/bindings.json", "18000"),
      ("cases/sv/rq07.spl", "cases/rq07/bindings.json", "18000"),
      ("cases/lg/lg01.spl", "cases/lg/bindings.json", "35")] do
    let program ← compile (← IO.FS.readFile source)
    let bindings ← match Bindings.parseStrict (← IO.FS.readFile binding) >>= decodeProgram program with
      | .ok value => pure value
      | .error code => throw (IO.userError code)
    let outcome := Interpret.interpret program bindings.1 bindings.2
    let record ← output outcome (if source.startsWith "cases/lg/" then "settlement" else "pool")
    let payable ← match field record "payable" with | .ok value => pure value | .error code => throw (IO.userError code)
    ensure (equal payable (.num (mkRat expected.toNat! 1))) ("wrong case payable: " ++ source)
    validateDAG outcome
    ensure (outcome.trace.nodes.any (fun n => n.kind == "definition" && n.citation.isSome)) "definition citation omitted"
    ensure (outcome.trace.nodes.all (fun n => n.valueType != .atom "$observation")) "trace node omitted checked type"
    ensure (outcome.trace.nodes.any (fun n =>
      ((Trace.nodeJson n).getObjValAs? (List String) "fact_ids").toOption.any (! ·.isEmpty))) "source fact IDs omitted"
  let program ← fragment "define result = if true then 0 else later; define later = if false then 1.0 / 0.0 else 2.0; emit \"x\" = result;"
  let outcome := Interpret.interpret program [] []
  ensure (equal (← output outcome "x") (.num 0)) "zero output lost"
  ensure (outcome.trace.nodes.any (fun n => n.status == "not_evaluated")) "lazy branch omitted"
  ensure (outcome.trace.nodes.all (fun n => n.valueType != .atom "$observation")) "skipped node omitted type"
  ensure (!(outcome.trace.nodes.any (fun n => n.status == "failed"))) "inactive division was evaluated"
  validateDAG outcome
  let barrier ← fragment "require false else \"FIRST\"; define later = 1.0 / 0.0; emit \"x\" = later;"
  let outcome := Interpret.interpret barrier [] []
  match outcome.result with
  | .error "FIRST" => pure ()
  | _ => throw (IO.userError "assertion did not block later arithmetic")
  ensure (!(outcome.trace.nodes.any (fun n => n.kind == "definition" || n.kind == "emit"))) "work crossed assertion barrier"
  let atomic ← fragment "emit \"first\" = 1; emit \"second\" = 1.0 / 0.0;"
  let outcome := Interpret.interpret atomic [] []
  match outcome.result with
  | .error "DIVISION_BY_ZERO" => pure ()
  | _ => throw (IO.userError "output failure did not block settlement")
  ensure (outcome.trace.nodes.any (fun n => n.kind == "emit" && n.status == "discarded")) "provisional output was not discarded"
  ensure (outcome.trace.nodes.all (fun n => n.valueType != .atom "$observation")) "failed node omitted type"
  ensure (outcome.trace.nodes.any (fun n => n.kind == "binary" && n.status == "failed" &&
    n.operands.length == 2 && (n.operands.getLast?).any (equal · (.num 0)))) "failed division omitted exact divisor"
  validateDAG outcome
  let unique ← fragment "input yes: Bool; define x = choose unique { when yes => 1; when not yes => 2; }; emit \"x\" = x;"
  let outcome := Interpret.interpret unique [("yes", .flag true)] []
  ensure (equal (← output outcome "x") (.num 1)) "unique selection failed"
  ensure (outcome.trace.nodes.any (fun n => n.kind == "selection_decision")) "selection candidates omitted"
  validateDAG outcome
  let tied ← fragment "input a: Bool; input b: Bool; define x = choose unique { when a => 1; when b => 2; }; emit \"x\" = x;"
  let outcome := Interpret.interpret tied [("a", .flag true), ("b", .flag true)] []
  match outcome.result with
  | .error "AMBIGUOUS_RULE" => pure ()
  | _ => throw (IO.userError "dynamic selection tie did not block")
  ensure (outcome.trace.nodes.any (fun n => n.kind == "selection_decision" &&
    (n.detail.getObjValAs? Bool "tie").toOption == some true)) "tie reason omitted"
  validateDAG outcome
  -- Readable expansions can assign one statement span to several IR nodes.
  -- IR identity must distinguish every arithmetic operator and literal there.
  let metadata (id : Nat) : IR.Meta := { id, span := {}, ty := Check.ratioTy }
  let nested : IR.Program := {
    name := "SameSpan"
    language := "spl/0.1-draft"
    core := "spl-core/0.1-draft"
    schema := "spl-data/0.1-draft"
    span := {}
    declarations := [.emit (metadata 0) "x" (.binary (metadata 1) "+"
      (.binary (metadata 2) "*" (.number (metadata 3) "2.0") (.number (metadata 4) "3.0"))
      (.number (metadata 5) "4.0"))] }
  let outcome := Interpret.interpret nested [] []
  ensure (equal (← output outcome "x") (.num 10)) "same-span evaluation failed"
  ensure (outcome.trace.nodes.length == 6) "same-span nodes collided"
  validateDAG outcome
  let invalid : IR.Program := { nested with declarations := [.emit (metadata 0) "x"
    (.binary (metadata 1) "+" (.boolean { metadata 2 with ty := Check.boolTy } true)
      (.number (metadata 3) "1.0"))] }
  let invalidOutcome := Interpret.interpret invalid [] []
  match invalidOutcome.result with
  | .error "INVALID_IR" => ensure invalidOutcome.trace.nodes.isEmpty "invalid IR was evaluated before validation"
  | _ => throw (IO.userError "invalid annotated IR was executable")
  let repeated ← fragment "define ys = map([1.0, 1.0], x => x + 1.0); emit \"x\" = ys;"
  let outcome := Interpret.interpret repeated [] []
  ensure (equal (← output outcome "x") (.seq [.num 2, .num 2])) "duplicate values were collapsed"
  ensure ((outcome.trace.nodes.filter (fun n => n.kind == "instance")).length == 2) "duplicate instances collided"
  validateDAG outcome
  let first : Trace.Node := { id := "collision", kind := "test", rule := "test", scope := "root", span := {}, result := some (.num 1) }
  let collision := (({} : Trace.Graph).add first).add { first with result := some (.num 2) }
  match collision.validate with
  | .error "TRACE_ID_COLLISION" => pure ()
  | _ => throw (IO.userError "incompatible trace identity reuse was accepted")
  let operations ← fragment "input xs: List<Int>; input optional: Option<Money<USD>>; define sorted = sort_by(xs, x => -x); define chosen = filter(sorted, x => x >= 0); define rows = for each x in chosen { define twice = later + later; define later = x; require twice >= x else \"LOCAL\"; yield twice; }; define amount = quantize(require_some(optional, \"NO_AMOUNT\"), USD 0.01, \"half_even\"); emit \"x\" = { rows: rows, total: sum(rows, x => x), amount: amount };"
  let outcome := Interpret.interpret operations [("xs", .seq [.num 1, .num (-1), .num 3, .num 1]),
    ("optional", .present (.num (mkRat 201 200)))] []
  let report ← output outcome "x"
  ensure (equal report (.obj [("rows", .seq [.num 6, .num 2, .num 2]), ("total", .num 10),
    ("amount", .num 1)])) "collection/local-forward-ref/half-even semantics failed"
  validateDAG outcome
  let quarter ← fragment "input period: Period; require is_calendar_quarter(period) else \"READABLE_CALENDAR_QUARTER_REQUIRED\"; emit \"x\" = 0;"
  for (start, finish, expected) in [("2026-01-01", "2026-04-01", true),
      ("2026-10-01", "2027-01-01", true), ("2026-01-02", "2026-04-01", false),
      ("2026-01-01", "2026-07-01", false), ("2026-02-01", "2026-05-01", false)] do
    let outcome := Interpret.interpret quarter [("period", .obj [("start", .text start), ("end", .text finish)])] []
    match outcome.result with
    | .ok _ => ensure expected "non-quarter period was accepted"
    | .error "READABLE_CALENDAR_QUARTER_REQUIRED" => ensure (!expected) "valid quarter was blocked"
    | .error code => throw (IO.userError code)
    validateDAG outcome
  IO.println "Native typed IR interpretation and trace DAG checks passed (SV, RQ-07, LG, lazy branches, assertions, atomic outputs, selections)."
