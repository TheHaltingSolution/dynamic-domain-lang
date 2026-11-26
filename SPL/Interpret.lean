import SPL.IR
import SPL.Trace
import SPL.ValidateIR
import SPL.Fold

/-! Independent executable semantics of the whole-program typed IR. This pass
does not invoke the Lean emitter or emitted settlement. Evaluation is pure;
bindings must have passed schema-aware decoding before entry. Definitions are
memoized lexical thunks, assertions are lexical barriers, and outputs commit
only after the complete calculation succeeds. Full verification is deferred. -/
namespace SPL.Interpret
open Lean (toJson)

open IR

structure Observed where
  value : Value
  node : String
  deriving Inhabited

private structure Frame where
  values : List (String × Observed) := []
  definitions : List (Meta × String × Expr) := []
  scope : String := "root"
  deriving Inhabited

private structure Context where
  schedule : String
  frames : List Frame
  owner : Dimensions.Admission := {}
  meanings : Dimensions.Meanings := {}
  owners : List (String × List String) := []
  rule : String := "schedule"
  scope : String := "root"
  citation : Option String := none
  deriving Inhabited

private structure Store where
  graph : Trace.Graph := {}
  cache : Std.HashMap String Observed := {}
  active : List String := []
  deriving Inhabited

private abbrev Run := ExceptT String (StateM Store)

structure Outcome where
  result : Eval Settlement
  trace : Trace.Graph

private def lift (value : Eval α) : Run α :=
  match value with | .ok x => pure x | .error code => throw code

private def nodeKey (context : Context) (mdata : Meta) (role : String) : String :=
  Trace.key context.schedule mdata.span context.rule context.scope (role ++ ":ir:" ++ toString mdata.id)

private partial def detailReferences : Lean.Json → List String
  | .obj fields => fields.toList.flatMap fun (key, value) =>
      if ["predicate_node", "skipped_node", "decision_node"].contains key then
        value.getStr?.toOption.toList
      else detailReferences value
  | .arr values => values.toList.flatMap detailReferences
  | _ => []

private def observe (context : Context) (mdata : Meta) (kind : String)
    (operands : List Observed) (result : Option Value) (detail : Lean.Json := .null)
    (status : String := "evaluated") (role : String := "") : Run String := do
  if (← get).graph.size >= maxTraceObservations then throw "RESOURCE_LIMIT"
  let id := nodeKey context mdata (if role.isEmpty then kind else role)
  let references := detailReferences detail
  modify fun state => { state with graph := state.graph.add {
    id, kind, rule := context.rule, scope := context.scope, span := mdata.span, valueType := mdata.ty,
    citation := mdata.citation.or context.citation, status,
    dependencies := (operands.map Observed.node ++ references).eraseDups,
    operands := operands.map Observed.value, result, detail } }
  pure id

private def obj := Lean.Json.mkObj

private def decimal (text : String) : Eval Value := do
  let parts := text.splitOn "."
  let some n := (String.join parts).toNat? | throw "INVALID_NUMBER"
  let d := match parts with | [_] => 1 | [_, fraction] => 10 ^ fraction.length | _ => 0
  if d == 0 then throw "INVALID_NUMBER"
  pure (.num (mkRat n d))

private def dimensionalNumeric (meanings : Dimensions.Meanings) (op : String) (left right : Value) : Eval Value := do
  let a ← magnitudeWith meanings left
  let b ← magnitudeWith meanings right
  if op == "/" && b == 0 then throw "DIVISION_BY_ZERO"
  if (op == "+" || op == "-") && sameDimension left right then
    return withMagnitude left (if op == "+" then a + b else a - b)
  match op, left, right with
  | "*", .quantity u _, .rate v _ _ | "*", .rate v _ _, .quantity u _ =>
    if u == v then pure (.num (a * b)) else throw "TYPE_MISMATCH"
  | "*", .num _, .quantity .. | "*", .num _, .rate .. => pure (withMagnitude right (a * b))
  | "*", .quantity .., .num _ | "*", .rate .., .num _ => pure (withMagnitude left (a * b))
  | "/", .quantity .., .num _ | "/", .rate .., .num _ => pure (withMagnitude left (a / b))
  | "/", .quantity .., .quantity .. | "/", .rate .., .rate .. =>
    if sameDimension left right then pure (.num (a / b)) else throw "TYPE_MISMATCH"
  | _, _, _ => throw "TYPE_MISMATCH"

/-- Arithmetic is interpreted directly, independently of target helper lowering. -/
private def numeric (meanings : Dimensions.Meanings) (op : String) (a b : Value) : Eval Value := do
  if ["+", "-", "*", "/"].contains op && !(sameDimension a (.num 0) && sameDimension b (.num 0)) then
    return ← dimensionalNumeric meanings op a b
  match op with
  | "+" => pure (.num ((← asNum a) + (← asNum b)))
  | "-" => pure (.num ((← asNum a) - (← asNum b)))
  | "*" => pure (.num ((← asNum a) * (← asNum b)))
  | "/" =>
    let x ← asNum a
    let y ← asNum b
    if y == 0 then throw "DIVISION_BY_ZERO"
    pure (.num (x / y))
  | "==" => pure (.flag (equal a b))
  | "!=" => pure (.flag (!equal a b))
  | "<" => pure (.flag ((← SPL.compare a b) == .lt))
  | "<=" => pure (.flag ((← SPL.compare a b) != .gt))
  | ">" => pure (.flag ((← SPL.compare a b) == .gt))
  | ">=" => pure (.flag ((← SPL.compare a b) != .lt))
  | _ => throw "IR_UNKNOWN_OPERATOR"

private def roundValue (meanings : Dimensions.Meanings) (value quantum mode : Value) : Eval Value := do
  unless sameDimension value quantum do throw "TYPE_MISMATCH"
  let x ← magnitudeWith meanings value
  let q ← magnitudeWith meanings quantum
  let mode ← asText mode
  if q ≤ 0 then throw "INVALID_QUANTUM"
  let scaled := x / q
  let low := scaled.floor
  let high := scaled.ceil
  let fraction := scaled - (low : Rat)
  let rounded ← match mode with
    | "floor" => pure low
    | "ceiling" => pure high
    | "toward_zero" => pure (if scaled < 0 then high else low)
    | "half_even" => pure (if fraction < mkRat 1 2 then low
        else if fraction > mkRat 1 2 then high else if low % 2 == 0 then low else high)
    | "half_away_from_zero" => pure (if fraction < mkRat 1 2 then low
        else if fraction > mkRat 1 2 then high else if scaled < 0 then low else high)
    | _ => throw "INVALID_ROUNDING_MODE"
  pure (withMagnitude value ((rounded : Rat) * q))

private def builtin (context : Context) (name : String) (values : List Value) : Eval Value := do
  match name, values with
  | "convert_quantity", [.quantity source number, .text target, .text relation] =>
    let _ ← magnitudeWith context.meanings (.quantity source number)
    let factor ← Dimensions.conversionFactor context.owner source target relation
    pure (.quantity target (number * factor))
  | "tuple", values => pure (.tuple values)
  | "append", [source, item] => SPL.appendValue source item
  | "concat", [left, right] => SPL.concatValues left right
  | "tuple_get", [.tuple values, .num index] =>
    let some value := values[index.num.toNat]? | throw "INVALID_TUPLE_INDEX"
    pure value
  | "none", [] => pure .absent
  | "some", [value] => pure (.present value)
  | "is_some", [.present _] => pure (.flag true)
  | "is_some", [.absent] => pure (.flag false)
  | "entries", [.map entries] => pure (.seq entries)
  | "lookup", [.map entries, key] =>
    for entry in entries do
      if equal (← field entry "key") key then return .present (← field entry "value")
    pure .absent
  | "instant", [value] =>
    let source ← asText value
    let seconds ← SPL.Instant.parse source
    let canonical ← SPL.Instant.render seconds
    pure (.instant seconds canonical)
  | "is_calendar_quarter", [period] =>
    let start ← asText (← field period "start")
    let finish ← asText (← field period "end")
    let valid := match start.splitOn "-", finish.splitOn "-" with
      | [year, month, "01"], [endYear, endMonth, "01"] =>
        match year.toNat?, month.toNat?, endYear.toNat?, endMonth.toNat? with
        | some y, some m, some ey, some em =>
          [1, 4, 7, 10].contains m &&
            (if m == 10 then ey == y + 1 && em == 1 else ey == y && em == m + 3)
        | _, _, _, _ => false
      | _, _ => false
    pure (.flag valid)
  | "abs", [value] =>
    let n ← magnitudeWith context.meanings value
    pure (withMagnitude value (if n < 0 then -n else n))
  | "min", [a, b] => pure (if (← SPL.compare a b) == .gt then b else a)
  | "max", [a, b] => pure (if (← SPL.compare a b) == .lt then b else a)
  | "in_period", [date, period] =>
    let date ← asText date
    let start ← asText (← field period "start")
    let finish ← asText (← field period "end")
    pure (.flag (start ≤ date && date < finish))
  | "add_calendar_months", [date, months, policy] =>
    -- Shared native calendar primitive; Python calendar oracle is independent.
    let source ← asText date
    let count ← asNum months
    let mode ← asText policy
    unless count >= 0 && count.den == 1 do throw "CALENDAR_INVALID_MONTHS"
    pure (.text (← Calendar.addMonths source count.num.toNat mode))
  | "quantize", [value, quantum, mode] => roundValue context.meanings value quantum mode
  | "require_some", [.present value, _] => pure value
  | "require_some", [.absent, code] => throw (← asText code)
  | "require_some", _ => throw "TARGET_EXPECTED_OPTION"
  | _, _ => throw "IR_UNSUPPORTED_BUILTIN"

private def kind : Expr → String
  | .number .. | .money .. | .boolean .. | .text .. | .date .. => "literal"
  | .name .. => "reference"
  | .unary .. => "unary"
  | .binary .. => "binary"
  | .field .. => "field"
  | .ite .. => "branch"
  | .call .. => "builtin"
  | .record .. => "record"
  | .list .. => "list"
  | .choose .. | .selectRules .. => "selection"
  | .collection .. | .indexed .. => "collection"
  | .forEach .. => "for_each"
  | .fold .. => "fold"
  | .apply .. => "application"

private def attempt (context : Context) (expr : Expr) (operands : List Observed)
    (detail : List (String × Lean.Json)) (result : Eval Value) : Run Value := do
  match result with
  | .ok value => pure value
  | .error code =>
    let _ ← observe context expr.meta (kind expr) operands none
      (obj (detail ++ [("code", .str code)])) "failed"
    throw code

private def skip (context : Context) (expr : Expr) (operands : List Observed)
    (reason : String) : Run String :=
  observe context expr.meta (kind expr) operands none
    (obj [("reason", .str reason)]) "not_evaluated"

private def localDefinition : LocalDecl → Option (Meta × String × Expr)
  | .define m name expr => some (m, name, expr)
  | _ => none

private def definition : Decl → Option (Meta × String × Expr)
  | .define m name expr => some (m, name, expr)
  | _ => none

private def localDecl : Decl → Option LocalDecl
  | .define m name expr => some (.define m name expr)
  | .require m expr code => some (.require m expr code)
  | _ => none

/-- Duplicate occurrences are numbered within their economic/value identity,
never by an unscoped collection index. Unique facts retain occurrence zero when
unrelated facts move or are inserted. -/
private def occurrences (items : List Value) : List (Value × Nat) := Id.run do
  let mut counts : Std.HashMap String Nat := {}
  let mut result := []
  for item in items do
    let identity := Trace.instanceIdentity item
    let occurrence := counts.getD identity 0
    result := (item, occurrence) :: result
    counts := counts.insert identity (occurrence + 1)
  return result.reverse

private def insertion (item : Observed × Observed) : List (Observed × Observed) → Eval (List (Observed × Observed))
  | [] => pure [item]
  | head :: tail => do
    if (← SPL.compare item.1.value head.1.value) == .lt then pure (item :: head :: tail)
    else pure (head :: (← insertion item tail))

mutual
  private partial def evaluate (context : Context) (expr : Expr) : Run Observed := do
    let before := (← get).graph.size
    try
      let (value, operands, detail) ← raw context expr
      let node ← observe context expr.meta (kind expr) operands (some value) detail
      pure ({ value := value, node := node } : Observed)
    catch code =>
      let graph := (← get).graph
      let children := (graph.nodes.take (graph.size - before)).reverse
      let id := nodeKey context expr.meta (kind expr)
      unless graph.contains id || graph.size >= maxTraceObservations do
        modify fun state => { state with graph := state.graph.add {
          id, kind := kind expr, rule := context.rule, scope := context.scope,
          span := expr.meta.span, citation := expr.meta.citation.or context.citation,
          valueType := expr.meta.ty,
          status := "failed", dependencies := children.map Trace.Node.id,
          detail := obj [("code", .str code)] } }
      throw code

  private partial def resolve (context : Context) (name : String) : Run Observed := do
    match context.frames with
    | [] => throw ("MISSING_BINDING:" ++ name)
    | frame :: rest =>
      if let some value := frame.values.lookup name then return value
      if let some (m, _, body) := frame.definitions.find? (fun (_, key, _) => key == name) then
        let lexical : Context := { context with scope := frame.scope, rule := name, citation := m.citation }
        let key := nodeKey lexical m "definition"
        if let some value := (← get).cache[key]? then return value
        if (← get).active.contains key then throw "DEPENDENCY_CYCLE"
        modify fun state => { state with active := key :: state.active }
        let result ← evaluate lexical body
        let node ← observe lexical m "definition" [result] (some result.value)
        let result := { result with node }
        modify fun state => { state with cache := state.cache.insert key result, active := state.active.filter (· != key) }
        return result
      resolve { context with frames := rest } name

  private partial def assertions (context : Context) (declarations : List LocalDecl) : Run Unit := do
    for declaration in declarations do
      match declaration with
      | .define _ name _ => let _ ← resolve context name; pure ()
      | .require m expr code =>
        let context := { context with rule := "assert:" ++ code, citation := m.citation }
        let condition ← evaluate context expr
        let passed ← lift (asBool condition.value)
        let _ ← observe context m "assertion" [condition] (some (.flag passed))
          (obj [("code", .str code)]) (if passed then "passed" else "failed")
        unless passed do throw code

  private partial def iteration (context : Context) (mdata : Meta) (binder : String)
      (binderTy : IR.Ty) (source : Observed) (item : Value) (occurrence : Nat) (declarations : List LocalDecl)
      (body : Expr) : Run Observed := do
    let scope := (Lean.Json.arr #[.str context.scope, toJson mdata.span.start,
      .str binder, .str (Trace.instanceIdentity item), toJson occurrence]).compress
    let inner := { context with scope }
    let node ← observe inner { mdata with ty := binderTy } "instance" [source] (some item)
      (obj [("identity", .str (Trace.instanceIdentity item)), ("occurrence", toJson occurrence)])
    let frame : Frame := { scope, values := [(binder, ({ value := item, node := node } : Observed))], definitions := declarations.filterMap localDefinition }
    let inner := { inner with frames := frame :: context.frames }
    assertions inner declarations
    evaluate inner body

  private partial def raw (context : Context) (expr : Expr) : Run (Value × List Observed × Lean.Json) := do
    match expr with
    | .number _ value | .money _ _ value => pure (← lift (decimal value), [], .null)
    | .boolean _ value => pure (.flag value, [], .null)
    | .text _ value | .date _ value => pure (.text value, [], .null)
    | .name _ name =>
      let result ← resolve context name
      pure (result.value, [result], obj [("name", .str name)])
    | .field _ base name =>
      let value ← evaluate context base
      pure (← lift (field value.value name), [value], obj [("field", .str name)])
    | .unary _ op body =>
      let value ← evaluate context body
      let result ← if op == "-" then do pure (withMagnitude value.value (-(← lift (magnitudeWith context.meanings value.value))))
        else if op == "not" then do pure (.flag (!(← lift (asBool value.value))))
        else throw "IR_UNKNOWN_OPERATOR"
      pure (result, [value], obj [("operator", .str op)])
    | .binary _ op left right =>
      let a ← evaluate context left
      if op == "and" || op == "or" then
        let flag ← lift (asBool a.value)
        if (op == "and" && !flag) || (op == "or" && flag) then
          let skipped ← skip context right [a] "short_circuit"
          pure (.flag flag, [a], obj [("operator", .str op),
            ("right", .str "not_evaluated"), ("skipped_node", .str skipped)])
        else
          let b ← evaluate context right
          let _ ← lift (asBool b.value)
          pure (b.value, [a, b], obj [("operator", .str op)])
      else
        let b ← evaluate context right
        pure (← attempt context expr [a, b] [("operator", .str op)] (numeric context.meanings op a.value b.value),
          [a, b], obj [("operator", .str op)])
    | .ite _ condition yes no =>
      let predicate ← evaluate context condition
      let selected ← lift (asBool predicate.value)
      let skipped ← skip context (if selected then no else yes) [predicate] "unselected_branch"
      let result ← evaluate context (if selected then yes else no)
      pure (result.value, [predicate, result], obj [("selected", .str (if selected then "then" else "else")),
        ("unselected", .str "not_evaluated"), ("skipped_node", .str skipped)])
    | .record _ fields =>
      let fields ← fields.mapM fun (key, body) => do pure (key, ← evaluate context body)
      pure (.obj (fields.map fun (key, value) => (key, value.value)), fields.map Prod.snd, .null)
    | .list _ values =>
      lift (checkCollectionSize values.length)
      let values ← values.mapM (evaluate context)
      pure (.seq (values.map Observed.value), values, .null)
    | .call _ "get_or" [source, fallback] =>
      let source ← evaluate context source
      match source.value with
      | .present value =>
        let skipped ← skip context fallback [source] "option_present"
        pure (value, [source], obj [("builtin",.str "get_or"),("skipped_node",.str skipped)])
      | .absent =>
        let result ← evaluate context fallback
        pure (result.value, [source,result], obj [("builtin",.str "get_or")])
      | _ => throw "TARGET_EXPECTED_OPTION"
    | .call _ name args =>
      let args ← args.mapM (evaluate context)
      let details ← if name == "convert_quantity" then lift do
          let [.quantity source _, .text target, .text relation] := args.map Observed.value
            | throw "TYPE_MISMATCH"
          let factor ← Dimensions.conversionFactor context.owner source target relation
          let definitions := Dimensions.definitions.filter (fun entry => entry.name == source || entry.name == target)
          let some entry := Dimensions.relations.find? (·.id == relation) | throw "UNSUPPORTED_CONVERSION"
          pure [("builtin", .str name), ("relation_id", .str relation), ("relation_pin", .str entry.pin),
            ("source_unit", .str source), ("target_unit", .str target), ("factor", valueJson (.num factor)),
            ("unit_definitions", .arr (definitions.map (fun entry => obj [("id", .str entry.id), ("sha256", .str entry.pin)])).toArray)]
        else pure [("builtin", .str name)]
      pure (← attempt context expr args details (builtin context name (args.map Observed.value)),
        args, obj details)
    | .choose mdata arms fallback =>
      let predicates ← arms.mapM fun (predicate, _) => evaluate context predicate
      let flags ← predicates.mapM fun value => lift (asBool value.value)
      let applicable := (arms.zip flags).filterMap fun ((_, body), flag) => if flag then some body else none
      let reason := if applicable.length == 1 then "unique_applicable_rule"
        else if applicable.isEmpty && fallback.isSome then "fallback_no_applicable_rule"
        else if applicable.isEmpty then "no_applicable_rule" else "ambiguous_applicable_rules"
      let candidates := (arms.zip (predicates.zip flags)).map fun ((_, body), (predicate, flag)) =>
        obj [("predicate_node", .str predicate.node), ("applicable", .bool flag),
          ("body_span", IR.spanJson body.meta.span)]
      let detail := obj [("reason", .str reason), ("tie", .bool (applicable.length > 1)),
        ("candidates", .arr candidates.toArray)]
      let decision ← observe context mdata "selection_decision" predicates none detail
      let selected := match applicable with | [body] => some body | [] => fallback | _ => none
      for (_, body) in arms do
        unless selected.any (fun chosen => chosen.meta.id == body.meta.id) do
          let _ ← skip context body predicates reason
      if let some body := fallback then
        unless selected.any (fun chosen => chosen.meta.id == body.meta.id) do
          let _ ← skip context body predicates reason
      let some body := selected | do
        let code := if applicable.isEmpty then "NO_APPLICABLE_RULE" else "AMBIGUOUS_RULE"
        let _ ← attempt context expr predicates [("reason", .str reason),
          ("tie", .bool (applicable.length > 1)), ("candidates", .arr candidates.toArray),
          ("decision_node", .str decision)] (.error code)
        throw code
      let result ← evaluate context body
      pure (result.value, predicates ++ [result], obj [("reason", .str reason),
        ("tie", .bool false), ("candidates", .arr candidates.toArray), ("decision_node", .str decision)])
    | .selectRules mdata priority arms fallback =>
      let ids := arms.map (fun (id, _, _, _) => id) ++ fallback.toList.map Prod.fst
      if ids.any String.isEmpty then throw "INVALID_RULE_ID"
      if ids.eraseDups.length != ids.length then throw "DUPLICATE_RULE_ID"
      let ordered := arms.mergeSort (fun a b => a.1 ≤ b.1)
      let mut predicates : List Observed := []
      let mut candidates : List Lean.Json := []
      let mut applicableArms : List (String × Int × Expr) := []
      for (id, rank, predicate, body) in ordered do
        try
          let observed ← evaluate context predicate
          let applicable ← lift (asBool observed.value)
          predicates := predicates ++ [observed]
          candidates := candidates ++ [obj [("rule_id", .str id), ("priority", toJson rank),
            ("predicate_node", .str observed.node), ("applicable", .bool applicable),
            ("reason", .str (if applicable then "predicate_true" else "predicate_false"))]]
          if applicable then applicableArms := applicableArms ++ [(id, rank, body)]
        catch code =>
          candidates := candidates ++ [obj [("rule_id", .str id), ("priority", toJson rank),
            ("reason", .str "predicate_failed"), ("code", .str code)]]
          for (laterId, laterRank, laterPredicate, _) in ordered do
            if id < laterId then
              let skipped ← skip context laterPredicate predicates "earlier_predicate_failed"
              candidates := candidates ++ [obj [("rule_id", .str laterId), ("priority", toJson laterRank),
                ("skipped_node", .str skipped), ("reason", .str "not_evaluated")]]
          for (_, _, _, unselected) in ordered do
            let _ ← skip context unselected predicates "predicate_failed"
          for (_, unselected) in fallback.toList do
            let _ ← skip context unselected predicates "predicate_failed"
          let _ ← attempt context expr predicates [("reason", .str "predicate_failed"),
            ("failed_rule_id", .str id), ("candidates", .arr candidates.toArray)] (.error code)
          throw code
      let winners := if priority then
          applicableArms.filter (fun (_, rank, _) => applicableArms.all (fun (_, other, _) => other ≤ rank))
        else applicableArms
      let selected := match winners with
        | [(id, _, body)] => some (id, body)
        | [] => fallback
        | _ => none
      let reason := if winners.length > 1 then "ambiguous_applicable_rules"
        else if applicableArms.isEmpty && fallback.isSome then "fallback_no_applicable_rule"
        else if applicableArms.isEmpty then "no_applicable_rule"
        else if priority then "greatest_priority_rule" else "unique_applicable_rule"
      let details := [("reason", .str reason), ("priority_mode", .bool priority),
        ("tie", .bool (winners.length > 1)), ("candidates", .arr candidates.toArray)] ++
        selected.toList.map (fun (id, _) => ("selected_rule_id", .str id))
      let decision ← observe context mdata "selection_decision" predicates none (obj details)
      for (id, _, _, body) in ordered do
        unless selected.any (fun (selectedId, _) => id == selectedId) do
          let _ ← skip context body predicates "unselected_rule_body"
      for (id, body) in fallback.toList do
        unless selected.any (fun (selectedId, _) => id == selectedId) do
          let _ ← skip context body predicates "unused_fallback"
      let some (_, body) := selected | do
        let code := if applicableArms.isEmpty then "NO_APPLICABLE_RULE" else "AMBIGUOUS_RULE"
        let _ ← attempt context expr predicates (details ++ [("decision_node", .str decision)]) (.error code)
        throw code
      try
        let result ← evaluate context body
        let status := match result.value with
          | .num value | .quantity _ value | .rate _ _ value => if value == 0 then "calculated_zero" else "calculated"
          | _ => "calculated"
        pure (result.value, predicates ++ [result], obj (details ++ [
          ("decision_node", .str decision), ("selection_status", .str status)]))
      catch code =>
        let _ ← attempt context expr predicates (details ++ [("decision_node", .str decision),
          ("body_status", .str "failed")]) (.error code)
        throw code
    | .collection mdata op binder binderTy source body =>
      let source ← evaluate context source
      let items ← lift (asList source.value)
      let values ← (occurrences items).mapM fun (item, occurrence) => iteration context mdata binder binderTy source item occurrence [] body
      let detail := obj [("operation", .str op), ("candidate_count", toJson items.length)]
      match op with
      | "map" => pure (.seq (values.map Observed.value), source :: values, detail)
      | "filter" =>
        let flags ← values.mapM fun value => lift (asBool value.value)
        let chosen := (items.zip flags).filterMap fun (item, flag) => if flag then some item else none
        let candidates := (items.zip (values.zip flags)).map fun (item, (value, flag)) =>
          obj [("identity", .str (Trace.instanceIdentity item)), ("predicate_node", .str value.node),
            ("selected", .bool flag), ("reason", .str (if flag then "predicate_true" else "predicate_false"))]
        pure (.seq chosen, source :: values, obj [("operation", .str op), ("candidates", .arr candidates.toArray)])
      | "sum" =>
        let mut total := match mdata.ty with
          | .quantity unit => Value.quantity unit 0
          | .rate unit currency => Value.rate unit currency 0
          | _ => .num 0
        for value in values do total ← lift (numeric context.meanings "+" total value.value)
        pure (total, source :: values, detail)
      | "sort_by" =>
        let mut sorted := []
        for (item, value) in items.zip values do
          sorted ← lift (insertion (value, { value := item, node := value.node }) sorted)
        pure (.seq (sorted.map fun pair => pair.2.value), source :: values,
          obj [("operation", .str op), ("tie_policy", .str "stable_source_order"),
            ("ordered_identities", toJson (sorted.map fun pair => Trace.instanceIdentity pair.2.value))])
      | "group_by" =>
        let mut sorted := []
        for (item,key) in items.zip values do
          sorted ← lift (insertion (key,{value := item,node := key.node}) sorted)
        let mut seen := []
        let mut entries := []
        for (key,_) in sorted do
          unless seen.any (equal key.value) do
            seen := seen ++ [key.value]
            let rows := (items.zip values).filter (fun (_,k) => equal key.value k.value)
            entries := entries ++ [.obj [("key",key.value),("value",.seq (rows.map Prod.fst))]]
        pure (.map entries,source :: values,detail)
      | _ => throw "IR_UNSUPPORTED_COLLECTION"
    | .indexed mdata op source right kb kt key vb vt value =>
      let source ← evaluate context source
      let items ← lift (asList source.value)
      let keyed ← (occurrences items).mapM fun (item,occ) => do
        let k ← iteration {context with scope := context.scope ++ ":keys:left"} mdata kb kt source item occ [] key
        pure (k,item,occ)
      if op == "make_map" then
        let mut sorted := []
        for (k,item,_) in keyed do sorted ← lift (insertion (k,{value := item,node := k.node}) sorted)
        for (k,_) in sorted do
          let duplicates := keyed.filter (fun (other,_,_) => equal k.value other.value)
          if duplicates.length > 1 then
            let _ ← attempt context expr (source :: keyed.map (fun (k,_,_) => k))
              [("operation",.str op),("key",valueJson k.value),
               ("source_identities",toJson (duplicates.map fun (_,row,occ) => (Trace.instanceIdentity row,occ)))]
              (.error "DUPLICATE_MAP_KEY")
            throw "DUPLICATE_MAP_KEY"
        let mut entries := []
        let mut observations := keyed.map (fun (k,_,_) => k)
        for (k,row) in sorted do
          let occ := (keyed.find? fun (other,_,_) => equal other.value k.value).map (fun (_,_,occ) => occ) |>.getD 0
          let v ← iteration {context with scope := context.scope ++ ":values"} mdata vb vt source row.value occ [] value
          entries := entries ++ [.obj [("key",k.value),("value",v.value)]]
          observations := observations ++ [v]
        pure (.map entries,source :: observations,obj [("operation",.str op)])
      else
        let some right := right | throw "IR_INVALID_JOIN"
        let right ← evaluate context right
        let rows ← lift (asList right.value)
        let rkeys ← (occurrences rows).mapM fun (row,occ) => do
          let k ← iteration {context with scope := context.scope ++ ":keys:right"} mdata vb vt right row occ [] value
          pure (k,row,occ)
        let mut pairs := []
        let mut lineage := []
        for (k,l,lo) in keyed do
          let matchedRows := rkeys.filter (fun (rk,_,_) => equal k.value rk.value)
          if op == "left_join" && matchedRows.isEmpty then
            lift (checkCollectionSize (pairs.length + 1))
            pairs := pairs ++ [.obj [("left",l),("right",.absent)]]
            lineage := lineage ++ [obj [("left",.str (Trace.instanceIdentity l)),("left_occurrence",toJson lo),("right_absent",.bool true)]]
          else
            for (_,r,ro) in matchedRows do
              lift (checkCollectionSize (pairs.length + 1))
              pairs := pairs ++ [.obj [("left",l),("right",if op == "left_join" then .present r else r)]]
              lineage := lineage ++ [obj [("left",.str (Trace.instanceIdentity l)),("left_occurrence",toJson lo),
                ("right",.str (Trace.instanceIdentity r)),("right_occurrence",toJson ro)]]
        pure (.seq pairs,[source,right] ++ keyed.map (fun (k,_,_) => k) ++ rkeys.map (fun (k,_,_) => k),
          obj [("operation",.str op),("pairs",.arr lineage.toArray)])
    | .apply mdata label parameters args declarations body =>
      let args ← args.mapM (evaluate context)
      let scope := (Lean.Json.arr #[.str context.scope, .str "call", toJson mdata.id, .str label]).compress
      let boundValues := (parameters.zip args).map (fun ((name, _), value) => (name, value))
      let frame : Frame := { scope, values := boundValues, definitions := declarations.filterMap localDefinition }
      let owner ← lift (Dimensions.prepare ((context.owners.lookup label).getD []))
      let inner := { context with scope, frames := [frame], owner }
      assertions inner declarations
      let result ← evaluate inner body
      pure (result.value, args ++ [result], obj [("function", .str label)])
    | .fold mdata source initial stateBinder eventBinder eventTy order declarations body =>
      let initial ← evaluate context initial
      let source ← evaluate context source
      let events ← lift (asList source.value)
      let mut orderOperands : List Observed := []
      let entries ← match order with
        | none => pure ((events.zipIdx).map fun (event, index) =>
            ((Value.num (mkRat index 1)), Value.text (Trace.instanceIdentity event), event))
        | some (kb, key, ib, identity, ties) => do
          let ids ← (occurrences events).mapM fun (event, occurrence) =>
            iteration context mdata ib eventTy source event occurrence [] identity
          let keys ← (occurrences events).mapM fun (event, occurrence) =>
            iteration context mdata kb eventTy source event occurrence [] key
          orderOperands := ids ++ keys
          let entries := (keys.zip (ids.zip events)).map fun (k, i, e) => (k.value, i.value, e)
          let ordered ← lift (orderFoldEntries entries ties)
          let _ ← observe context mdata "fold_order" (source :: orderOperands) none
            (obj [("tie_policy", .str ties), ("event_count", toJson events.length),
              ("ordered_identities", .arr (ordered.map fun (_, i, _) => valueJson i).toArray),
              ("semantic_keys", .arr (ordered.map fun (k, _, _) => valueJson k).toArray)])
          pure ordered
      let mut current := initial
      let mut results : List Observed := []
      for ((key, identity, event), index) in entries.zipIdx do
        let scope := (Lean.Json.arr #[.str context.scope, .str "fold", toJson mdata.id,
          valueJson identity, toJson index]).compress
        let inner := { context with scope }
        let eventNode ← observe inner { mdata with ty := eventTy } "fold_event" [source] (some event)
          (obj [("event_identity", valueJson identity)])
        let eventObserved : Observed := { value := event, node := eventNode }
        let beforeNode ← observe inner mdata "fold_state_before" [current, eventObserved] (some current.value)
        let before : Observed := { current with node := beforeNode }
        let details := [("event_identity", valueJson identity), ("semantic_key", valueJson key),
          ("tie_policy", .str (if order.isSome then "reject" else "supplied_list_order")),
          ("state_before", valueJson current.value)]
        let stepValues := [(stateBinder, before), (eventBinder, eventObserved)]
        let frame : Frame := { scope, values := stepValues, definitions := declarations.filterMap localDefinition }
        let inner := { inner with frames := frame :: context.frames }
        try
          assertions inner declarations
          let result ← evaluate inner body
          let stepNode ← observe inner mdata "fold_step" [before, eventObserved, result] (some result.value)
            (obj (details ++ [("state_after", valueJson result.value)])) "calculated"
          current := { result with node := stepNode }
          results := results ++ [current]
        catch code =>
          let _ ← observe inner mdata "fold_step" [before, eventObserved] none
            (obj (details ++ [("code", .str code)])) "failed"
          throw code
      pure (current.value, initial :: source :: orderOperands ++ results,
        obj [("event_count", toJson events.length), ("ordered", .bool order.isSome)])
    | .forEach mdata binder binderTy source declarations body =>
      let source ← evaluate context source
      let items ← lift (asList source.value)
      let results ← (occurrences items).mapM fun (item, occurrence) => iteration context mdata binder binderTy source item occurrence declarations body
      pure (.seq (results.map Observed.value), source :: results, .null)
end

private def calculation (program : Program) (inputs openings : Env) : Run Settlement := do
  let mut values := []
  let owner ← lift (Dimensions.prepare program.features)
  let base : Context := {
    schedule := program.name
    frames := []
    owner
    owners := program.owners
    meanings := { features := (program.features ++ program.owners.flatMap Prod.snd).eraseDups } }
  for declaration in program.declarations do
    match declaration with
    | .input m name | .opening m name _ =>
      let isInput := match declaration with | .input .. => true | _ => false
      let value ← lift (lookup (if isInput then inputs else openings) name)
      let context := { base with rule := name }
      let node ← observe context m (if isInput then "input" else "opening") [] (some value)
      values := values ++ [(name, ({ value := value, node := node } : Observed))]
    | _ => pure ()
  let frame : Frame := { values, definitions := program.declarations.filterMap definition }
  let context := { base with frames := [frame] }
  assertions context (program.declarations.filterMap localDecl)
  let mut emissions := []
  let mut closing := []
  for declaration in program.declarations do
    match declaration with
    | .emit m name body | .closing m name body =>
      let isEmit := match declaration with | .emit .. => true | _ => false
      let context := { context with rule := (if isEmit then "emit:" else "closing:") ++ name }
      let result ← evaluate context body
      let _ ← observe context m (if isEmit then "emit" else "closing") [result] (some result.value)
      if isEmit then emissions := emissions ++ [(name, result.value)]
      else closing := closing ++ [(name, result.value)]
    | _ => pure ()
  pure { emissions, closing }

def interpret (program : Program) (inputs openings : Env) : Outcome :=
  match ValidateIR.validate program with
  | .error diagnostic => { result := .error diagnostic.code, trace := {} }
  | .ok _ =>
    let (result, state) := ((calculation program inputs openings).run).run {}
    let result := match state.graph.validate with | .ok _ => result | .error code => .error code
    { result, trace := match result with
        | .ok _ => state.graph
        | .error _ => state.graph.discardOutputs }

def outcomeJson (outcome : Outcome) : Lean.Json :=
  let fields := match SPL.outcomeJson outcome.result with | .obj fields => fields.toList | _ => []
  Lean.Json.mkObj (fields ++ [("trace_origin", .str "native_ir_interpreter"),
    ("trace_format", .str "spl-trace-dag/0.1"), ("trace", outcome.trace.json)])

end SPL.Interpret
