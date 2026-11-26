import SPL.Runtime
import SPL.IR
import Std.Data.HashMap
import Std.Data.HashSet
import Std.Data.TreeSet

/-! Native, pure calculation observations. Keys describe source and economic
instance identity; array position is never an observation identity. Serialization
orders dependencies before consumers, with lexical keys breaking ready-node ties.
This is executable audit infrastructure, not a trace-correctness theorem. -/
namespace SPL.Trace
open Lean

structure Node where
  id : String
  kind : String
  rule : String
  scope : String
  span : Syntax.Span
  valueType : IR.Ty := .atom "$observation"
  citation : Option String := none
  status : String := "evaluated"
  dependencies : List String := []
  operands : List Value := []
  result : Option Value := none
  detail : Lean.Json := .null
  deriving Inhabited

structure Graph where
  /-- Unordered observation storage. `ordered` defines the serialized order. -/
  nodes : List Node := []
  collisions : List String := []
  private index : Option (Std.HashMap String Node) := none
  private nodeCount : Nat := 0
  deriving Inhabited

def key (schedule : String) (span : Syntax.Span) (rule scope role : String) : String :=
  -- JSON tuples make delimiters inside user-authored names unambiguous.
  (Lean.Json.arr #[.str schedule, toJson span.start, toJson span.stop,
    .str rule, .str scope, .str role]).compress

private def identityField (fields : Env) : Option String :=
  ["fact_id", "asset_id", "event_id", "decision_id", "id"].findSome? fun name =>
    match fields.lookup name with
    | some (.text value) => some (name ++ "=" ++ value)
    | _ => none

/-- Prefer source/economic keys. Scalars and anonymous records use their exact
value, so reordering a collection does not invent new instance identities. -/
def instanceIdentity (value : Value) : String :=
  match value with
  | .obj fields => (identityField fields).getD ((valueJson value).compress)
  | _ => (valueJson value).compress

private def sameObservation (a b : Node) : Bool :=
  a.kind == b.kind && a.rule == b.rule && a.scope == b.scope && a.span == b.span &&
  a.valueType == b.valueType &&
  a.citation == b.citation && a.status == b.status && a.dependencies == b.dependencies &&
  a.operands.map valueJson == b.operands.map valueJson &&
  a.result.map valueJson == b.result.map valueJson && a.detail == b.detail

private def Graph.indexed (graph : Graph) : Graph :=
  match graph.index with
  | some _ => graph
  | none => { graph with
      index := some (graph.nodes.foldl (fun index node => index.insertIfNew node.id node) {})
      nodeCount := graph.nodes.length }

def Graph.size (graph : Graph) : Nat :=
  if graph.index.isSome then graph.nodeCount else graph.nodes.length

def Graph.contains (graph : Graph) (id : String) : Bool :=
  match graph.index with
  | some index => index.contains id
  | none => graph.nodes.any (fun node => node.id == id)

def Graph.add (graph : Graph) (node : Node) : Graph :=
  let graph := graph.indexed
  let index := graph.index.getD {}
  match index[node.id]? with
  | some old => if sameObservation old node then graph
      else { graph with collisions := node.id :: graph.collisions }
  | none =>
    { graph with
      nodes := node :: graph.nodes
      index := some (index.insert node.id node)
      nodeCount := graph.nodeCount + 1 }

private def sorted (nodes : List Node) : List Node :=
  nodes.mergeSort (fun a b => a.id ≤ b.id)

/-- Kahn's algorithm with a lexical priority queue. Newly ready nodes compete
immediately with the existing frontier. Positions only break equal-ID ties on
malformed graphs, matching the stable sort used by the original ordering. -/
def Graph.ordered (graph : Graph) : List Node := Id.run do
  let nodes := graph.nodes.toArray
  let mut remaining : Array Nat := #[]
  let mut consumers : Std.HashMap String (List Nat) := {}
  let mut ready : Std.TreeSet (String × Nat) (fun a b =>
    match Ord.compare a.1 b.1 with
    | .eq => Ord.compare a.2 b.2
    | order => order) := {}
  for index in [:nodes.size] do
    let node := nodes[index]!
    remaining := remaining.push node.dependencies.length
    if node.dependencies.isEmpty then ready := ready.insert (node.id, index)
    for dependency in node.dependencies do
      consumers := consumers.insert dependency (index :: consumers.getD dependency [])
  let mut done : Std.HashSet String := {}
  let mut result := []
  -- Each position enters the frontier at most once, even for repeated IDs.
  for _ in [:nodes.size] do
    let some (id, index) := ready.min? | break
    ready := ready.erase (id, index)
    unless done.contains id do
      done := done.insert id
      result := nodes[index]! :: result
      for consumer in consumers.getD id [] do
        let count := remaining[consumer]! - 1
        remaining := remaining.set! consumer count
        if count == 0 then ready := ready.insert (nodes[consumer]!.id, consumer)
  -- Invalid cycles/missing references retain the old sorted-pending suffix.
  return result.reverse ++ sorted (graph.nodes.filter fun node => !done.contains node.id)

/-- A malformed audit graph blocks finalization; sorting never legitimizes a
missing reference, cycle, or incompatible reuse of an observation identity. -/
def Graph.validate (graph : Graph) : Except String Unit := do
  unless graph.collisions.isEmpty do throw "TRACE_ID_COLLISION"
  let mut ids : Std.HashSet String := {}
  for node in graph.nodes do
    if ids.contains node.id then throw "TRACE_ID_COLLISION"
    ids := ids.insert node.id
  let mut done : Std.HashSet String := {}
  for node in graph.ordered do
    if done.contains node.id then throw "TRACE_ID_COLLISION"
    unless node.dependencies.all done.contains do throw "INVALID_TRACE_DAG"
    done := done.insert node.id

/-- Source fact IDs remain source identities; arithmetic does not synthesize
facts or copy their amounts into a second audit ledger. Dependencies connect
scalar-only nodes back to these structurally observed record identities. -/
private partial def collectFactIds (value : Value) (ids : Std.HashSet String) : Std.HashSet String :=
  match value with
  | .obj fields => fields.foldl (fun ids (name, value) =>
      let ids := match name, value with | "fact_id", .text id => ids.insert id | _, _ => ids
      collectFactIds value ids) ids
  | .seq values | .tuple values | .map values => values.foldl (fun ids value => collectFactIds value ids) ids
  | .present value => collectFactIds value ids
  | _ => ids

/-- Preserve the legacy exact textual identity set and explicit lexical order,
without constructing duplicate lists or scanning them with `List.eraseDups`. -/
private def nodeFactIds (node : Node) : List String :=
  let ids := node.operands.foldl (fun ids value => collectFactIds value ids) {}
  let ids := match node.result with | some value => collectFactIds value ids | none => ids
  ids.toList.mergeSort (· ≤ ·)

def nodeJson (node : Node) : Lean.Json := Lean.Json.mkObj ([
  ("node_id", .str node.id), ("kind", .str node.kind), ("rule_id", .str node.rule),
  ("instance_scope", .str node.scope),
  ("value_type", IR.typeJson node.valueType),
  ("fact_ids", toJson (nodeFactIds node)),
  ("source_span", Lean.Json.mkObj [("start", toJson node.span.start),
    ("stop", toJson node.span.stop), ("line", toJson node.span.line),
    ("column", toJson node.span.column)]),
  ("status", .str node.status),
  ("outcome", .str (if node.status == "not_evaluated" then "not_evaluated"
    else if node.status == "failed" then "blocked"
    else if node.status == "discarded" then "discarded"
    else match node.result with
      | some (.num value) | some (.quantity _ value) | some (.rate _ _ value) => if value == 0 then "calculated_zero" else "calculated"
      | some _ => "calculated"
      | none => "decision")),
  ("dependencies", toJson node.dependencies),
  ("operands", .arr (node.operands.map valueJson).toArray)] ++
  (node.citation.toList.map fun citation => ("citation", .str citation)) ++
  (node.result.toList.map fun result => ("result", valueJson result)) ++
  (if node.detail == .null then [] else [("detail", node.detail)]))

def Graph.json (graph : Graph) : Lean.Json := .arr (graph.ordered.map nodeJson).toArray

/-- Any computed output observations remain provisional until the entire
settlement succeeds. A blocked run marks them discarded as well as returning
empty business output ports. -/
def Graph.discardOutputs (graph : Graph) : Graph :=
  { graph with index := none, nodeCount := 0, nodes := graph.nodes.map fun node =>
      if node.kind == "emit" || node.kind == "closing" then
        { node with status := "discarded" } else node }

end SPL.Trace
