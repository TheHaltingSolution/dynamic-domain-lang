import SPL.IR

/-! Checked source-to-IR elaboration. The existing structural checker remains
the validation boundary; this pass resolves all definition types before walking
expressions and records contextual literal types at every node. -/
namespace SPL.Elaborate
open Syntax

abbrev Elab := StateT Nat (Except Diagnostic)

private def newMeta (span : Span) (ty : Check.Ty) (citation : Option String) : Elab IR.Meta := do
  let id ← get
  set (id + 1)
  pure { id, span, ty, citation }

private def liftCheck (result : Except Diagnostic α) : Elab α :=
  match result with | .ok value => pure value | .error diagnostic => throw diagnostic

mutual
  private partial def expression (context : Check.Context) (source : Expr)
      (expected : Option Check.Ty := none) (citation : Option String := none) : Elab IR.Expr := do
    let ty ← liftCheck (Check.infer context source expected)
    let m ← newMeta source.span ty citation
    match source with
    | .number _ value => pure (.number m value)
    | .money _ currency value => pure (.money m currency value)
    | .boolean _ value => pure (.boolean m value)
    | .text _ value => pure (.text m value)
    | .date _ value => pure (.date m value)
    | .name _ name => pure (.name m name)
    | .field _ base name => return .field m (← expression context base none citation) name
    | .unary _ op body => return .unary m op (← expression context body (some ty) citation)
    | .binary _ op a b =>
      if op == "and" || op == "or" then
        return .binary m op (← expression context a (some Check.boolTy) citation)
          (← expression context b (some Check.boolTy) citation)
      -- Match the checker's bidirectional hints, including money × literal ratio.
      let (aHint, bHint) ← if Check.isNumber a && !Check.isNumber b then do
          let bTy ← liftCheck (Check.infer context b)
          pure (if op == "*" && bTy == Check.usdTy then some Check.ratioTy else Check.dimensionless bTy, none)
        else do
          let aTy ← liftCheck (Check.infer context a)
          pure (none, if Check.isNumber b then
            (if (op == "*" || op == "/") && aTy == Check.usdTy then some Check.ratioTy else Check.dimensionless aTy)
            else none)
      return .binary m op (← expression context a aHint citation) (← expression context b bHint citation)
    | .ite _ condition yes no =>
      return .ite m
        (← expression context condition (some Check.boolTy) citation)
        (← expression context yes (some ty) citation) (← expression context no (some ty) citation)
    | .record _ fields =>
      let hints := match ty with | .record _ fields => fields | _ => []
      return .record m (← fields.mapM fun (name, value) => do
        pure (name, ← expression context value (Check.lookup hints name) citation))
    | .list _ items =>
      let hint := match ty with | .list itemTy => some itemTy | _ => none
      return .list m (← items.mapM fun item => expression context item hint citation)
    | .choose _ arms fallback =>
      let arms ← arms.mapM fun (predicate, body) => do
        pure (← expression context predicate (some Check.boolTy) citation,
          ← expression context body (some ty) citation)
      return .choose m arms (← fallback.mapM fun body => expression context body (some ty) citation)
    | .selectRules _ priority arms fallback =>
      let arms ← arms.mapM fun (id, rank, predicate, body) => do
        pure (id, rank, ← expression context predicate (some Check.boolTy) citation,
          ← expression context body (some ty) citation)
      let fallback ← fallback.mapM fun (id, body) => do
        pure (id, ← expression context body (some ty) citation)
      return .selectRules m priority arms fallback
    | .forEach span binder source declarations yielded =>
      let source ← expression context source none citation
      let .list itemTy := source.meta.ty
        | throw { code := "IR_TYPE", message := "Checked comprehension source is not a list", span }
      let nested ← liftCheck (Check.bind context binder itemTy span)
      let nested ← liftCheck (Check.checkLocals nested declarations)
      let hint := match ty with | .list itemTy => some itemTy | _ => none
      return .forEach m binder itemTy source (← declarations.mapM fun d => localDecl nested d citation)
        (← expression nested yielded hint citation)
    | .fold span source initial state event order declarations body =>
      let initial ← expression context initial (some ty) citation
      let source ← expression context source none citation
      let .list eventTy := source.meta.ty
        | throw { code := "IR_TYPE", message := "Fold source is not a list", span }
      let order ← order.mapM fun (kb, key, ib, identity, ties) => do
        let keyContext ← liftCheck (Check.bind context kb eventTy span)
        let idContext ← liftCheck (Check.bind context ib eventTy span)
        pure (kb, ← expression keyContext key none citation, ib,
          ← expression idContext identity none citation, ties)
      let nested ← liftCheck (Check.bind (← liftCheck (Check.bind context state ty span)) event eventTy span)
      let nested ← liftCheck (Check.checkLocals nested declarations)
      return .fold m source initial state event eventTy order
        (← declarations.mapM fun d => localDecl nested d citation) (← expression nested body (some ty) citation)
    | .apply span label parameters args _ declarations body =>
      let mut nested : Check.Context := []
      let mut params := []
      let mut values := []
      for ((name, annotation), arg) in parameters.zip args do
        let parameterTy ← liftCheck (Check.parseType annotation)
        nested ← liftCheck (Check.bind nested name parameterTy span)
        params := params ++ [(name, parameterTy)]
        values := values ++ [← expression context arg (some parameterTy) citation]
      nested ← liftCheck (Check.checkLocals nested declarations)
      return .apply m label params values (← declarations.mapM fun d => localDecl nested d citation)
        (← expression nested body (some ty) citation)
    | .call span name args =>
      if name == "append" || name == "concat" then
        let .list itemTy := ty | throw { code := "IR_TYPE", message := "Sequence result type", span }
        let hints := [ty, if name == "append" then itemTy else ty]
        return .call m name (← (args.zip hints).mapM fun (arg, hint) => expression context arg (some hint) citation)
      if ["make_map", "join", "left_join"].contains name then
        let (left, right, kb, key, vb, value) ← match name, args with
          | "make_map", [source, .lambda _ kb key, .lambda _ vb value] => pure (source, none, kb, key, vb, value)
          | _, [left, right, .lambda _ kb key, .lambda _ vb value] => pure (left, some right, kb, key, vb, value)
          | _, _ => throw {code := "IR_TYPE", message := "Invalid indexed arguments", span}
        let left ← expression context left none citation
        let right ← right.mapM (fun e => expression context e none citation)
        let .list lt := left.meta.ty | throw {code := "IR_TYPE", message := "Expected list", span}
        let rt := match right with
          | some e => match e.meta.ty with | .list t => t | _ => lt
          | none => lt
        let lc ← liftCheck (Check.bind context kb lt span)
        let rc ← liftCheck (Check.bind context vb rt span)
        let hint := if name == "make_map" then (match ty with | .map _ v => some v | _ => none) else none
        return .indexed m name left right kb lt (← expression lc key none citation)
          vb rt (← expression rc value hint citation)
      if ["filter", "map", "sum", "sort_by", "group_by"].contains name then
        let [source, .lambda ls binder body] := args
          | throw { code := "IR_TYPE", message := "Invalid checked collection arguments", span }
        let source ← expression context source none citation
        let .list itemTy := source.meta.ty
          | throw { code := "IR_TYPE", message := "Checked collection source is not a list", span }
        let nested ← liftCheck (Check.bind context binder itemTy ls)
        let hint := if name == "filter" then some Check.boolTy else if name == "sum" then some ty
          else if name == "map" then (match ty with | .list itemTy => some itemTy | _ => none) else none
        return .collection m name binder itemTy source (← expression nested body hint citation)
      let lookupHints ← if name == "lookup" then do
          let mt ← liftCheck (Check.infer context args[0]!)
          pure (match mt with | .map k _ => [some mt, some k] | _ => [])
        else pure []
      let hints : List (Option Check.Ty) :=
        if name == "none" then []
        else if name == "some" then (match ty with | .option t => [some t] | _ => [])
        else if name == "get_or" then [some (.option ty), some ty]
        else if name == "is_some" then [none]
        else if name == "tuple" then (match ty with | .tuple ts => ts.map some | _ => [])
        else if name == "lookup" then lookupHints
        else if name == "tuple_get" || name == "entries" then args.map (fun _ => none)
        else if name == "min" || name == "max" then [some ty, some ty]
        else if name == "add_calendar_months" then [some Check.dateTy, some (.atom "Nat"), some Check.textTy]
        else if name == "in_period" then [some Check.dateTy, some Check.periodTy]
        else if name == "is_calendar_quarter" then [some Check.periodTy]
        else if name == "instant" then [some Check.textTy]
        else if name == "quantize" then [some ty, some ty, some Check.textTy]
        else if name == "require_some" then [some (.option ty), some Check.textTy]
        else []
      let mut elaborated := []
      for (arg, hint) in args.zip hints do
        elaborated := elaborated ++ [← expression context arg hint citation]
      if elaborated.length != args.length then
        throw { code := "IR_TYPE", message := "Missing checked builtin signature", span }
      return .call m name elaborated
    | .lambda span .. => throw { code := "ESCAPING_LAMBDA", message := "Escaping lambda reached IR", span }

  private partial def localDecl (context : Check.Context) (decl : LocalDecl)
      (parentCitation : Option String) : Elab IR.LocalDecl := do
    match decl with
    | .define span name _ body citation =>
      let citation := citation.or parentCitation
      let some ty := Check.lookup context name
        | throw { code := "IR_TYPE", message := "Missing resolved local", span }
      let m ← newMeta span ty citation
      return .define m name (← expression context body (some ty) citation)
    | .require span condition code =>
      let m ← newMeta span Check.boolTy parentCitation
      return .require m (← expression context condition (some Check.boolTy) parentCitation) code
end

private def contexts (schedule : Schedule) : Except Diagnostic Check.Context := do
  let mut context := []
  let mut locals := []
  for declaration in schedule.declarations do
    match declaration with
    | .input _ name annotation | .opening _ name annotation _ =>
      context := (name, ← Check.parseType annotation) :: context
    | .define span name annotation body citation =>
      locals := locals ++ [.define span name annotation body citation]
    | .require span condition code => locals := locals ++ [.require span condition code]
    | _ => pure ()
  Check.checkLocals context locals

private def program (schedule : Schedule) (context : Check.Context) : Elab IR.Program := do
  let declarations ← schedule.declarations.mapM fun decl => do
    match decl with
    | .input span name annotation =>
      return IR.Decl.input (← newMeta span (← liftCheck (Check.parseType annotation)) none) name
    | .opening span name annotation alias =>
      return IR.Decl.opening (← newMeta span (← liftCheck (Check.parseType annotation)) none) name alias
    | .define span name annotation body citation =>
      let .define m name value ← localDecl context (.define span name annotation body citation) none
        | throw { code := "IR_TYPE", message := "Invalid definition elaboration", span }
      return IR.Decl.define m name value
    | .require span condition code =>
      let m ← newMeta span Check.boolTy none
      return IR.Decl.require m (← expression context condition (some Check.boolTy)) code
    | .closing span name body =>
      let some ty := Check.lookup context name
        | throw { code := "IR_TYPE", message := "Missing opening type", span }
      let m ← newMeta span ty none
      return IR.Decl.closing m name (← expression context body (some ty))
    | .emit span name body =>
      let ty ← liftCheck (Check.infer context body)
      let m ← newMeta span ty none
      return IR.Decl.emit m name (← expression context body (some ty))
  pure { name := schedule.name
         language := schedule.language
         core := schedule.core
         schema := schedule.schema
         span := schedule.span
         declarations := declarations }

def elaborate (schedule : Schedule) : Except Diagnostic IR.Program := do
  Check.check schedule
  let context ← contexts schedule
  pure (← (program schedule context).run 0).1

end SPL.Elaborate
