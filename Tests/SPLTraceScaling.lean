import SPL.Parser
import SPL.Elaborate
import SPL.Interpret

/-! Executable regression checks for trace storage and canonical ordering. The
bounded legacy algorithm below is an independent differential oracle, not a
production fallback or a correctness theorem. -/
open SPL

private def ensure (condition : Bool) (message : String) : IO Unit :=
  unless condition do throw (IO.userError message)

private def node (id : String) (dependencies : List String := []) : Trace.Node :=
  { id, dependencies, kind := "test", rule := "test", scope := "root", span := {} }

private def sorted (nodes : List Trace.Node) : List Trace.Node :=
  nodes.mergeSort (fun a b => a.id ≤ b.id)

private def legacyOrder : Nat → List Trace.Node → List String → List Trace.Node
  | 0, pending, _ => sorted pending
  | fuel + 1, pending, done =>
    match sorted (pending.filter fun item => item.dependencies.all done.contains) with
    | [] => sorted pending
    | first :: _ => first :: legacyOrder fuel
        (pending.filter fun item => item.id != first.id) (first.id :: done)

private def legacyValidate (graph : Trace.Graph) : Except String Unit := do
  unless graph.collisions.isEmpty do throw "TRACE_ID_COLLISION"
  unless (graph.nodes.map Trace.Node.id).eraseDups.length == graph.nodes.length do
    throw "TRACE_ID_COLLISION"
  let mut done := []
  for item in legacyOrder graph.nodes.length graph.nodes [] do
    if done.contains item.id then throw "TRACE_ID_COLLISION"
    unless item.dependencies.all done.contains do throw "INVALID_TRACE_DAG"
    done := item.id :: done

private def diagnostic : Except String Unit → Option String
  | .ok _ => none
  | .error code => some code

private def compareLegacy (graph : Trace.Graph) : IO Unit := do
  ensure (graph.ordered.map Trace.nodeJson ==
    (legacyOrder graph.nodes.length graph.nodes []).map Trace.nodeJson)
    "canonical ordering differs from the legacy oracle"
  ensure (diagnostic graph.validate == diagnostic (legacyValidate graph)) "graph validation changed"

private def fragment (body : String) : IO IR.Program :=
  match Parser.parse ("schedule TraceScaling language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { " ++ body ++ " }") >>= Elaborate.elaborate with
  | .ok program => pure program
  | .error diagnostic => throw (IO.userError diagnostic.code)

def main (args : List String) : IO Unit := do
  -- Every directed graph on three IDs, including self-cycles and all source
  -- permutations, exercises malformed suffixes as well as ordinary DAGs.
  let ids := ["a", "b", "c"]
  let permutations := [[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]]
  for mask in [:512] do
    let nodes := (List.range 3).map fun index =>
      node ids[index]! ((List.range 3).filterMap fun dependency =>
        if (mask / (2 ^ (index * 3 + dependency))) % 2 == 1 then some ids[dependency]! else none)
    for permutation in permutations do
      compareLegacy { nodes := permutation.map fun index => nodes[index]! }
  -- Selecting b makes a ready, which must precede the already-ready z.
  let frontier : Trace.Graph := { nodes := [node "z", node "a" ["b"], node "b"] }
  ensure (frontier.ordered.map Trace.Node.id == ["b", "a", "z"])
    "newly ready lexical minimum did not preempt the frontier"
  for nodes in [
      [node "ready", node "missing" ["absent"]],
      [node "a" ["b", "b"], node "b"],
      [node "a" ["b"], node "a", node "b" ["a"]],
      [node "a" ["missing"], node "a", node "b"],
      [node "a", { node "a" with status := "different" }, node "b" ["a"]]] do
    compareLegacy { nodes }
    compareLegacy { nodes := nodes.reverse }
  compareLegacy { nodes := [node "a"], collisions := ["a"] }
  let initial := node "same"
  let graph := (({} : Trace.Graph).add initial).add initial
  ensure (graph.size == 1 && graph.nodes.length == 1 && graph.validate.isOk)
    "identical observations were not idempotent"
  let collision := graph.add { initial with status := "different" }
  ensure (diagnostic collision.validate == some "TRACE_ID_COLLISION")
    "incompatible identity reuse was accepted"
  compareLegacy { graph with nodes := [initial, initial] }
  compareLegacy { graph with nodes := [node "cycle" ["cycle"]] }
  -- Publicly constructed graphs initialize their private acceleration data on
  -- first insertion; validation must inspect their actual nodes independently.
  let handmade : Trace.Graph := { nodes := [initial] }
  ensure (handmade.size == 1 && handmade.contains "same") "handmade lookup failed"
  ensure ((handmade.add initial).size == 1) "handmade observation duplicated"
  ensure (((handmade.add (node "new")).add initial).size == 2) "handmade cache initialization failed"
  ensure (diagnostic (handmade.add { initial with status := "different" }).validate == some "TRACE_ID_COLLISION")
    "handmade collision was lost"
  let output := { node "output" with kind := "emit" }
  let discarded := (({} : Trace.Graph).add output).discardOutputs
  let discardedNode := { output with status := "discarded" }
  ensure ((discarded.add discardedNode).validate.isOk && (discarded.add discardedNode).size == 1)
    "discarded observation left a stale lookup cache"
  ensure (diagnostic (discarded.add output).validate == some "TRACE_ID_COLLISION")
    "discarded output status change was lost"
  -- A failure discovered after observing children retains the original
  -- chronological dependency list, even though storage now prepends nodes.
  let failure ← fragment "emit \"first\" = 7; emit \"second\" = if true then 1.0 / 0.0 else 9.0;"
  let failed := Interpret.interpret failure [] []
  ensure (failed.result.toOption.isNone && failed.trace.validate.isOk) "failure trace invalid"
  let chronological := failed.trace.nodes.reverse
  let some branch := chronological.find? (fun item => item.kind == "branch" && item.status == "failed")
    | throw (IO.userError "missing failed branch")
  let children := (chronological.dropWhile (fun item => item.kind != "literal" ||
    !item.result.any (equal · (.flag true)))).takeWhile (fun item => item.id != branch.id)
  ensure (branch.dependencies == children.map Trace.Node.id) "failure child dependency order changed"
  -- Occurrence numbering is per exact identity, including anonymous values,
  -- and remains stable when unrelated values are inserted.
  let repeated ← fragment "input xs: List<Int>; emit \"x\" = map(xs, x => x + 1);"
  for items in [[1, 1, 2, 1], [9, 1, 1, 2, 1]] do
    let outcome := Interpret.interpret repeated [("xs", .seq (items.map fun value => .num value))] []
    ensure (outcome.result.isOk && outcome.trace.validate.isOk) "duplicate collection failed"
    let ones := (outcome.trace.nodes.reverse.filter fun item =>
      item.kind == "instance" && item.result.any (equal · (.num 1)))
    ensure ((ones.map fun item => (item.detail.getObjValAs? Nat "occurrence").toOption) ==
      [some 0, some 1, some 2]) "duplicate occurrence numbering changed"
  -- The optional larger check reaches the real quota rather than lowering a
  -- test-only limit. Run separately so bounded differential checks stay quick.
  if args.contains "--quota" then
    let quota ← fragment "input xs: List<Int>; emit \"first\" = 7; emit \"x\" = map(xs, x => x + 1);"
    let outcome := Interpret.interpret quota [("xs", .seq (List.replicate 25000 (.num 1)))] []
    ensure (outcome.result.toOption.isNone) "quota did not block settlement"
    match outcome.result with
    | .error "RESOURCE_LIMIT" => pure ()
    | _ => throw (IO.userError "quota returned the wrong diagnostic")
    ensure (outcome.trace.size == maxTraceObservations) "quota changed the retained prefix length"
    ensure (outcome.trace.validate.isOk) "quota retained an invalid dependency prefix"
    let outputs := outcome.trace.nodes.filter fun item => item.kind == "emit"
    ensure (outputs.length == 1 && outputs.all (fun item => item.status == "discarded"))
      "quota did not discard an earlier provisional output"
    ensure ((outcome.trace.nodes.head?).any (fun item => item.kind == "binary"))
      "quota changed the final retained observation"
    let instances := outcome.trace.nodes.filter fun item => item.kind == "instance"
    ensure ((instances.head?).any (fun item =>
      (item.detail.getObjValAs? Nat "occurrence").toOption == some 24998))
      "quota changed the final retained occurrence"
  IO.println "Trace ordering, validation, storage, failures, and duplicate occurrences passed."
