import SPL.Parser
import SPL.Elaborate
import SPL.Emit

open SPL

private def assertTrue (test : Bool) (message : String) : IO Unit :=
  unless test do throw (IO.userError message)

mutual
  private partial def metas (e : IR.Expr) : List IR.Meta := e.meta :: (match e with
    | .unary _ _ b | .field _ b _ => metas b
    | .binary _ _ a b => metas a ++ metas b
    | .ite _ c a b => metas c ++ metas a ++ metas b
    | .call _ _ args | .list _ args => args.flatMap metas
    | .record _ fields => fields.flatMap fun (_, value) => metas value
    | .choose _ arms fallback => arms.flatMap (fun (p, b) => metas p ++ metas b) ++
        fallback.toList.flatMap metas
    | .collection _ _ _ _ source body => metas source ++ metas body
    | .forEach _ _ _ source declarations body => metas source ++ declarations.flatMap localMetas ++ metas body
    | _ => [])

  private partial def localMetas : IR.LocalDecl → List IR.Meta
    | .define m _ body | .require m body _ => m :: metas body
end

private def allMetas (p : IR.Program) : List IR.Meta := p.declarations.flatMap fun d =>
  d.meta :: (match d with
    | .define _ _ b | .require _ b _ | .closing _ _ b | .emit _ _ b => metas b
    | _ => [])

private def fromSource (source : String) : IO IR.Program :=
  match Parser.parse source >>= Elaborate.elaborate with
  | .ok p => pure p
  | .error d => throw (IO.userError s!"IR elaboration: {repr d}")

private def expectRejected (body code : String) : IO Unit := do
  let source := "schedule Invalid language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { " ++ body ++ " }"
  match Parser.parse source >>= Elaborate.elaborate with
  | .ok _ => throw (IO.userError ("Elaboration accepted invalid program: " ++ body))
  | .error diagnostic =>
    assertTrue (diagnostic.code == code)
      ("Expected " ++ code ++ ", got " ++ diagnostic.code)

private def inventory := "schedule Inventory language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" {
  input xs: List<Int>;
  input optional: Option<Money<USD>>;
  input window: Period;
  opening balance: Money<USD> from \"balance\";
  define rows = for each x in xs {
    define doubled = later + later;
    define later = x;
    require doubled >= x else \"DOUBLED\";
    yield { value: doubled, label: \"row\" };
  };
  define selected = filter(xs, v => v >= 0);
  define ordered = sort_by(selected, v => -v);
  define mapped = map(ordered, v => v + 1);
  define total = sum(mapped, v => v);
  define expected: Ratio = if true then 1 else 0.5;
  define amount = require_some(optional, \"MISSING\");
  define rounded = quantize(amount, USD 0.01, \"half_even\");
  define capped = min(max(rounded, USD 0), balance);
  define enabled = not false and (true or false);
  define chosen = choose unique { when enabled => capped; otherwise => USD 0; } citing \"INVENTORY-CHOICE\";
  define dates = [date \"2026-01-01\", date \"2026-01-02\"];
  define active = in_period(date \"2026-01-01\", window);
  closing balance = balance - chosen;
  emit \"report\" = { rows: rows, count: total, expected: expected, active: active, dates: dates };
}"

def main : IO Unit := do
  expectRejected "define x = USD 1 * USD 2;" "TYPE_MISMATCH"
  expectRejected "define x = y; define y = x;" "UNRESOLVED_NAME_OR_CYCLE"
  expectRejected "input xs: List<Int>; define x = sum(xs, n => true);" "TYPE_MISMATCH"
  expectRejected "input xs: List<Int>; define x = filter(xs, n => n);" "TYPE_MISMATCH"
  expectRejected "input xs: List<Int>; define x = sort_by(xs, n => { value: n });" "TYPE_MISMATCH"
  expectRejected "define x = [];" "AMBIGUOUS_EMPTY_LIST"
  expectRejected "define x: Ratio = \"bad\";" "TYPE_MISMATCH"
  expectRejected "input xs: List<Int>; define x = for each n in xs { define n = 1; yield n; };" "DUPLICATE_NAME"
  for path in ["cases/sv/sv01.spl", "cases/sv/rq07.spl", "cases/lg/lg01.spl"] do
    let source ← IO.FS.readFile path
    let p ← fromSource source
    let again ← fromSource source
    let nodes := allMetas p
    let ids := nodes.map IR.Meta.id
    assertTrue (!nodes.isEmpty && ids == List.range nodes.length) (path ++ ": IDs are not unique preorder")
    assertTrue (p.toJson.compress == again.toJson.compress) (path ++ ": nondeterministic IR JSON")
    assertTrue (nodes.all fun m => m.span.stop >= m.span.start && m.ty != .atom "$pending")
      (path ++ ": invalid metadata")
    let noCitation := IR.metaJson { id := 0, span := {}, ty := Check.boolTy }
    assertTrue (match noCitation.getObjVal? "citation" with | .error _ => true | .ok _ => false)
      "Absent citation must be omitted"
    match Emit.emitIR p with
    | .error d => throw (IO.userError s!"IR emission failed: {repr d}")
    | .ok _ => pure ()
  let p ← fromSource inventory
  match ValidateIR.validate p with
  | .error d => throw (IO.userError s!"Full inventory IR validation failed: {repr d}")
  | .ok _ => pure ()
  let nodes := allMetas p
  assertTrue ((nodes.map IR.Meta.id) == List.range nodes.length) "Inventory ID traversal differs"
  let some (.define _ _ (.ite _ _ yes no)) := p.declarations.find? (fun d => match d with
      | .define _ "expected" _ => true | _ => false)
    | throw (IO.userError "Missing expected expression")
  assertTrue (yes.meta.ty == Check.ratioTy && no.meta.ty == Check.ratioTy)
    "Contextual integer literal lost its checked Ratio type"
  assertTrue ((nodes.filter fun m => m.citation == some "INVENTORY-CHOICE").length >= 5)
    "Citation was not retained on choice descendants"
  let serialized := p.toJson.compress
  assertTrue (serialized.contains '"') "Empty IR serialization"
  match Lean.Json.parse serialized with
  | .error e => throw (IO.userError ("IR JSON failed roundtrip: " ++ e))
  | .ok _ => pure ()
  IO.println "SPL whole-program typed IR checks passed (all native schedules, contextual types, IDs, citations, full operator inventory)."
