import SPL.IR

/-! Independent defensive validation of the type-annotated IR. `IR.Expr` is not
an intrinsically typed dependent syntax: its constructors are publicly usable.
This pass checks each annotation/operator, lexical scope, dependency DAG, source
metadata identity, and program ports before public execution or emission.
It does not evaluate source arithmetic or establish compiler correctness. -/
namespace SPL.ValidateIR
open IR

abbrev Validation := StateT (List Nat) (Except Syntax.Diagnostic)

private def reject (message : String) (span : Syntax.Span := {}) : Validation α :=
  throw { code := "INVALID_IR", message, span }

private def checked (result : Except Syntax.Diagnostic α) : Validation α :=
  match result with
  | .ok value => pure value
  | .error d => reject (d.code ++ ": " ++ d.message) d.span

private partial def portType : Ty → Syntax.TypeExpr
  | .atom name => if name.startsWith "Id:" then
      .named "Id" [.named (String.intercalate ":" ((name.splitOn ":").drop 1)) []]
    else .named name []
  | .money currency => .named "Money" [.named currency []]
  | .quantity unit => .named "Quantity" [.named unit []]
  | .rate unit currency => .named "Rate" [.named unit [], .named currency []]
  | .list ty => .named "List" [portType ty]
  | .option ty => .named "Option" [portType ty]
  | .tuple types => .named "Tuple" (types.map portType)
  | .map key value => .named "Map" [portType key, portType value]
  | .record name fields => if name == "literal" then .record (fields.map fun (n,t) => (n,portType t)) else .named name []

/-- Contextual empty containers and none may otherwise carry arbitrary forged
annotations. Reparse every complete type, including nested dimensions and the
exact fields of registered schemas, before trusting it as an inference hint. -/
private def validateType (ty : Ty) (span : Syntax.Span) : Validation Unit := do
  let actual ← checked (Check.parseType (portType ty))
  unless actual == ty do reject "IR type differs from its admitted structural type or registered schema" span

private def note (m : Meta) : Validation Unit := do
  if m.span.stop < m.span.start || m.span.line == 0 || m.span.column == 0 then
    reject "Invalid source span" m.span
  validateType m.ty m.span
  let seen ← get
  if seen.contains m.id then reject "Duplicate node ID" m.span
  set (m.id :: seen)

private def localName : LocalDecl → Option String
  | .define _ name _ => some name
  | _ => none

mutual
  private partial def references (e : Expr) (bound : List String := []) : List String :=
    match e with
    | .name _ name => if bound.contains name then [] else [name]
    | .unary _ _ b | .field _ b _ => references b bound
    | .binary _ _ a b => references a bound ++ references b bound
    | .ite _ c a b => references c bound ++ references a bound ++ references b bound
    | .call _ _ args | .list _ args => args.flatMap fun e => references e bound
    | .apply _ _ _ args _ _ => args.flatMap fun e => references e bound
    | .fold _ source initial state event _ order declarations body =>
      let nested := state :: event :: declarations.filterMap localName ++ bound
      references initial bound ++ references source bound ++
        order.toList.flatMap (fun (kb, key, ib, identity, _) => references key (kb :: bound) ++ references identity (ib :: bound)) ++
        declarations.flatMap (fun d => localReferences d nested) ++ references body nested
    | .record _ fields => fields.flatMap fun (_, e) => references e bound
    | .choose _ arms fallback => arms.flatMap (fun (p, b) => references p bound ++ references b bound) ++
        fallback.toList.flatMap (fun e => references e bound)
    | .selectRules _ _ arms fallback => arms.flatMap (fun (_, _, p, b) => references p bound ++ references b bound) ++
        fallback.toList.flatMap (fun (_, e) => references e bound)
    | .collection _ _ binder _ source body => references source bound ++ references body (binder :: bound)
    | .indexed _ _ source right kb _ key vb _ value => references source bound ++
        right.toList.flatMap (fun e => references e bound) ++ references key (kb :: bound) ++ references value (vb :: bound)
    | .forEach _ binder _ source declarations body =>
      let bound' := binder :: declarations.filterMap localName ++ bound
      references source bound ++ declarations.flatMap (fun d => localReferences d bound') ++ references body bound'
    | _ => []

  private partial def localReferences (d : LocalDecl) (bound : List String) : List String :=
    match d with
    | .define _ _ body | .require _ body _ => references body bound
end

private partial def visit (declarations : List LocalDecl) (name : String)
    (active doneNames : List String) : Validation (List String) := do
  if doneNames.contains name then return doneNames
  if active.contains name then reject "Cyclic definition dependency"
  let some (.define m _ body) := declarations.find? (fun d => localName d == some name)
    | return doneNames
  let mut doneNames := doneNames
  for dependency in references body do
    if dependency == name then reject "Self-referential definition" m.span
    doneNames ← visit declarations dependency (name :: active) doneNames
  pure (name :: doneNames)

private def scopeContext (outer : Check.Context) (declarations : List LocalDecl) : Validation Check.Context := do
  let mut context := outer
  for d in declarations do
    if let .define m name _ := d then context ← checked (Check.bind context name m.ty m.span)
  let mut doneNames := []
  for name in declarations.filterMap localName do doneNames ← visit declarations name [] doneNames
  pure context

/-- Rechecking one shallow operator avoids trusting its annotation or recursing
through unvalidated annotated subtrees inside the existing source checker. -/
private def inferNode (m : Meta) (context : Check.Context) (source : Syntax.Expr) : Validation Unit := do
  let actual ← checked (Check.infer context source (some m.ty))
  unless actual == m.ty do reject "Node type annotation differs from inferred type" m.span

private def childName (namePrefix : String) (index : Nat) : String := namePrefix ++ toString index

private def shallow (m : Meta) (children : List Expr)
    (shape : List Syntax.Expr → Syntax.Expr) (namePrefix : String := "@IR:") : Validation Unit := do
  let context := (children.zipIdx).map fun (e, index) => (childName namePrefix index, e.meta.ty)
  let names := (children.zipIdx).map fun (e, index) => Syntax.Expr.name e.meta.span (childName namePrefix index)
  inferNode m context (shape names)

private def validDecimal (value : String) : Bool :=
  let parts := value.splitOn "."
  (parts.length == 1 || parts.length == 2) &&
    parts.all (fun p => !p.isEmpty && p.toList.all Char.isDigit)

mutual
  private partial def expression (context : Check.Context) (e : Expr) : Validation Unit := do
    let m := e.meta
    note m
    match e with
    | .number _ value =>
      unless validDecimal value do reject "Invalid numeric literal" m.span
      inferNode m context (.number m.span value)
    | .money _ currency value =>
      unless validDecimal value do reject "Invalid monetary literal" m.span
      inferNode m context (.money m.span currency value)
    | .boolean _ value => inferNode m context (.boolean m.span value)
    | .text _ value => inferNode m context (.text m.span value)
    | .date _ value => inferNode m context (.date m.span value)
    | .name _ name => inferNode m context (.name m.span name)
    | .unary _ op b =>
      expression context b
      shallow m [b] (fun es => .unary m.span op es[0]!)
    | .binary _ op a b =>
      expression context a
      expression context b
      shallow m [a, b] (fun es => .binary m.span op es[0]! es[1]!)
    | .field _ b name =>
      expression context b
      shallow m [b] (fun es => .field m.span es[0]! name)
    | .ite _ c a b =>
      expression context c
      expression context a
      expression context b
      shallow m [c, a, b] (fun es => .ite m.span es[0]! es[1]! es[2]!)
    | .record _ fields =>
      for (_, value) in fields do expression context value
      shallow m (fields.map Prod.snd) (fun es => .record m.span ((fields.map Prod.fst).zip es))
    | .list _ items =>
      for item in items do expression context item
      shallow m items (fun es => .list m.span es)
    | .choose _ arms fallback =>
      if (arms.filter fun (p, _) => match p with | .boolean _ true => true | _ => false).length > 1 then
        reject "Multiple statically true choice arms" m.span
      for (p, b) in arms do expression context p; expression context b
      for b in fallback.toList do expression context b
      let children := arms.flatMap (fun (p, b) => [p, b]) ++ fallback.toList
      shallow m children fun es => .choose m.span
        ((List.range arms.length).map fun i => (es[2 * i]!, es[2 * i + 1]!))
        (if fallback.isSome then some es[2 * arms.length]! else none)
    | .selectRules _ priority arms fallback =>
      for (_, _, p, b) in arms do expression context p; expression context b
      for (_, b) in fallback.toList do expression context b
      let children := arms.flatMap (fun (_, _, p, b) => [p, b]) ++ fallback.toList.map Prod.snd
      shallow m children fun es => .selectRules m.span priority
        ((arms.zipIdx).map fun ((id, rank, _, _), i) => (id, rank, es[2 * i]!, es[2 * i + 1]!))
        (fallback.map fun (id, _) => (id, es[2 * arms.length]!))
    | .call _ name args =>
      for arg in args do expression context arg
      -- Literal diagnostic/rounding strings are part of these signatures.
      let context' := (args.zipIdx).map fun (arg, index) => (childName "@IR:" index, arg.meta.ty)
      let names := (args.zipIdx).map fun (arg, index) => match arg with
        | .text m value => Syntax.Expr.text m.span value
        | .number m value => Syntax.Expr.number m.span value
        | _ => Syntax.Expr.name arg.meta.span (childName "@IR:" index)
      inferNode m context' (.call m.span name names)
    | .collection _ op binder itemTy source body =>
      validateType itemTy m.span
      expression context source
      let .list actualItem := source.meta.ty | reject "Collection source is not a list" m.span
      unless actualItem == itemTy do reject "Incorrect collection binder type" m.span
      let nested ← checked (Check.bind context binder itemTy m.span)
      expression nested body
      unless ["filter", "map", "sum", "sort_by", "group_by"].contains op do reject "Unsupported collection operator" m.span
      shallow m [source, body] (fun es => .call m.span op [es[0]!, .lambda m.span binder es[1]!]) ("@IR:" ++ binder ++ ":")
    | .indexed _ op source right kb kt key vb vt value =>
      validateType kt m.span
      validateType vt m.span
      unless ["make_map", "join", "left_join"].contains op do reject "Unknown indexed operator" m.span
      unless (op == "make_map") == right.isNone do reject "Incorrect indexed source count" m.span
      expression context source
      for e in right.toList do expression context e
      unless source.meta.ty == .list kt do reject "Incorrect indexed key binder type" m.span
      let rightTy := (right.map (fun e => e.meta.ty)).getD source.meta.ty
      unless rightTy == .list vt do reject "Incorrect indexed value binder type" m.span
      expression (← checked (Check.bind context kb kt m.span)) key
      expression (← checked (Check.bind context vb vt m.span)) value
      let children := [source] ++ right.toList ++ [key,value]
      shallow m children (fun es =>
        let n := if right.isSome then 2 else 1
        .call m.span op ([es[0]!] ++ (if right.isSome then [es[1]!] else []) ++
          [.lambda m.span kb es[n]!, .lambda m.span vb es[n+1]!])) ("@IR:index:" ++ kb ++ ":" ++ vb ++ ":")
    | .apply _ label parameters args declarations body =>
      if label.isEmpty || parameters.length != args.length then reject "Invalid function application" m.span
      let mut nested : Check.Context := []
      for ((name, ty), arg) in parameters.zip args do
        expression context arg
        validateType ty m.span
        unless Check.compatible arg.meta.ty ty do reject "Function argument type mismatch" m.span
        nested ← checked (Check.bind nested name ty m.span)
      nested ← scopeContext nested declarations
      for d in declarations do localDecl nested d
      expression nested body
      unless Check.compatible body.meta.ty m.ty do reject "Function return type mismatch" m.span
    | .fold _ source initial state event eventTy order declarations body =>
      validateType eventTy m.span
      expression context initial
      expression context source
      let .list actualEventTy := source.meta.ty | reject "Fold source is not a list" m.span
      unless actualEventTy == eventTy && Check.compatible initial.meta.ty m.ty do reject "Incorrect fold state/event types" m.span
      if let some (kb, key, ib, identity, ties) := order then
        expression (← checked (Check.bind context kb eventTy m.span)) key
        expression (← checked (Check.bind context ib eventTy m.span)) identity
        unless Check.keyType key.meta.ty && Check.keyType identity.meta.ty && ties == "reject" do
          reject "Invalid ordered fold key/identity/tie policy" m.span
      let nested ← checked (Check.bind (← checked (Check.bind context state m.ty m.span)) event eventTy m.span)
      let nested ← scopeContext nested declarations
      for d in declarations do localDecl nested d
      expression nested body
      unless Check.compatible body.meta.ty m.ty do reject "Fold step changes state type" m.span
    | .forEach _ binder itemTy source declarations body =>
      validateType itemTy m.span
      expression context source
      let .list actualItem := source.meta.ty | reject "Comprehension source is not a list" m.span
      unless actualItem == itemTy do reject "Incorrect comprehension binder type" m.span
      let nested ← checked (Check.bind context binder itemTy m.span)
      let nested ← scopeContext nested declarations
      for d in declarations do localDecl nested d
      expression nested body
      shallow m [source, body] (fun es => .call m.span "map" [es[0]!, .lambda m.span binder es[1]!]) ("@IR:" ++ binder ++ ":")

  private partial def localDecl (context : Check.Context) (d : LocalDecl) : Validation Unit := do
    match d with
    | .define m _ body =>
      note m
      expression context body
      unless m.ty == body.meta.ty do reject "Definition type differs from its body" m.span
    | .require m body code =>
      note m
      expression context body
      unless m.ty == Check.boolTy && body.meta.ty == Check.boolTy && !code.isEmpty do
        reject "Assertion must have Boolean type and a diagnostic" m.span
end

private def locals (declarations : List Decl) : List LocalDecl := declarations.filterMap fun d => match d with
  | .define m name body => some (.define m name body)
  | .require m body code => some (.require m body code)
  | _ => none

private def program (p : Program) : Validation Unit := do
  if p.span.stop < p.span.start || p.span.line == 0 || p.span.column == 0 then
    reject "Invalid schedule source span" p.span
  checked (Check.check {
    name := p.name
    language := p.language
    core := p.core
    schema := p.schema
    span := p.span
    declarations := [] })
  let mut context := []
  let mut openings := []
  let mut aliases := []
  for d in p.declarations do
    match d with
    | .input m name | .opening m name _ =>
      validateType m.ty m.span
      context ← checked (Check.bind context name m.ty m.span)
      if let .opening _ _ alias := d then
        if aliases.contains alias then reject "Duplicate opening alias" m.span
        aliases := alias :: aliases
        openings := (name, m.ty) :: openings
    | _ => pure ()
  context ← scopeContext context (locals p.declarations)
  let mut closed := []
  let mut emitted := []
  for d in p.declarations do
    match d with
    | .input m _ | .opening m _ _ => note m
    | .define m name body => localDecl context (.define m name body)
    | .require m body code => localDecl context (.require m body code)
    | .closing m name body =>
      note m
      expression context body
      let some ty := Check.lookup openings name | reject "Closing port has no opening" m.span
      unless m.ty == ty && Check.compatible body.meta.ty ty && !closed.contains name do
        reject "Duplicate or incorrectly typed closing port" m.span
      closed := name :: closed
    | .emit m name body =>
      note m
      expression context body
      unless m.ty == body.meta.ty && !emitted.contains name do reject "Duplicate or incorrectly typed output" m.span
      emitted := name :: emitted
      if let .record _ fields := body.meta.ty then
        if (Check.lookup fields "payable").isSome then
          unless ["agreement_id", "participant_id", "period"].all (fun key => (Check.lookup fields key).isSome) &&
              ((Check.lookup fields "pool_id").isSome || (Check.lookup fields "asset_id").isSome) do
            reject "Payable output has no accounting scope" m.span
  unless openings.length == closed.length do reject "Missing closing port" p.span

def validate (p : Program) : Except Syntax.Diagnostic Unit := do
  pure (← (program p).run []).1

end SPL.ValidateIR
