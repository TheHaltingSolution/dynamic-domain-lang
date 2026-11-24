import Lean
import SPL.Elaborate
import SPL.ValidateIR

/-! Hygienic direct emission from the whole-program typed IR.
This module generates direct pure target computations, not a call to the source
interpreter. Generated names use a private counter; source strings are quoted.
-/
namespace SPL.Emit

open IR
abbrev Span := Syntax.Span
abbrev Diagnostic := Syntax.Diagnostic

abbrev Gen := StateT Nat (Except Diagnostic)
abbrev Names := List (String × String)

def quoted (value : String) : String :=
  (Lean.Json.compress (.str value)).replace "\\b" "\\x08" |>.replace "\\f" "\\x0c"

private def brackets (values : List String) : String :=
  "[" ++ String.intercalate ", " values ++ "]"

private def pair (key value : String) : String := "(" ++ quoted key ++ ", " ++ value ++ ")"

private def block (lines : List String) (result : String) : String :=
  "(do\n" ++ String.intercalate "\n" ((lines ++ [result]).map fun s => "  " ++ s.replace "\n" "\n  ") ++ ")"

private def fresh : Gen String := do
  let counter ← get
  set (counter + 1)
  pure ("_spl_v" ++ toString counter)

private def fail (code message : String) (span : Span := {}) : Gen α :=
  throw { code, message, span }

private def localName : LocalDecl → Option String
  | .define _ name _ => some name
  | _ => none

mutual
  private partial def references (expr : Expr) (bound : List String := []) : List String :=
    match expr with
    | .name _ name => if bound.contains name then [] else [name]
    | .unary _ _ value | .field _ value _ => references value bound
    | .binary _ _ left right => references left bound ++ references right bound
    | .ite _ condition yes no => references condition bound ++ references yes bound ++ references no bound
    | .call _ _ args | .list _ args => args.flatMap fun e => references e bound
    | .apply _ _ _ args _ _ => args.flatMap fun e => references e bound
    | .fold _ source initial state event _ order declarations body =>
      let nested := state :: event :: declarations.filterMap localName ++ bound
      references initial bound ++ references source bound ++
        order.toList.flatMap (fun (kb, key, ib, identity, _) => references key (kb :: bound) ++ references identity (ib :: bound)) ++
        declarations.flatMap (fun d => localReferences d nested) ++ references body nested
    | .collection _ _ name _ source body => references source bound ++ references body (name :: bound)
    | .indexed _ _ source right kb _ key vb _ value => references source bound ++
        right.toList.flatMap (fun e => references e bound) ++ references key (kb :: bound) ++ references value (vb :: bound)
    | .record _ fields => fields.flatMap fun (_, e) => references e bound
    | .choose _ arms fallback =>
      arms.flatMap (fun (p, b) => references p bound ++ references b bound) ++
        (fallback.toList.flatMap fun e => references e bound)
    | .selectRules _ _ arms fallback =>
      arms.flatMap (fun (_, _, p, b) => references p bound ++ references b bound) ++
        (fallback.toList.flatMap fun (_, e) => references e bound)
    | .forEach _ name _ source declarations body =>
      let localBound := name :: declarations.filterMap localName ++ bound
      references source bound ++ declarations.flatMap (fun d => localReferences d localBound) ++ references body localBound
    | _ => []

  private partial def localReferences (decl : LocalDecl) (bound : List String) : List String :=
    match decl with
    | .define _ _ expr | .require _ expr _ => references expr bound
end

private def definitionName : Decl → Option String
  | .define _ name _ => some name
  | _ => none

private def decimal (value : String) (span : Span) : Gen String := do
  let parts := value.splitOn "."
  let digits := String.join parts
  let some numerator := digits.toNat? | fail "INVALID_NUMBER" "Invalid source number reached emitter" span
  let denominator := match parts with
    | [_, fraction] => 10 ^ fraction.length
    | [_] => 1
    | _ => 0
  if denominator == 0 then fail "INVALID_NUMBER" "Invalid source decimal" span
  pure ("(pure (.num (mkRat " ++ toString numerator ++ " " ++ toString denominator ++ ")))" )

mutual
  private partial def expression (expr : Expr) (env : Names) : Gen String := do
    match expr with
    | .number m value | .money m _ value => decimal value m.span
    | .boolean _ value => pure ("(pure (.flag " ++ (if value then "true" else "false") ++ "))")
    | .text _ value | .date _ value => pure ("(pure (.text " ++ quoted value ++ "))")
    | .name m name =>
      let some binderVar := env.lookup name | fail "UNKNOWN_NAME" ("Unknown checked name " ++ name) m.span
      pure binderVar
    | .field _ value name =>
      pure (block [] ("SPL.field (← " ++ (← expression value env) ++ ") " ++ quoted name))
    | .unary m op value =>
      let target := if op == "-" && !Check.dimensional m.ty then "SPL.Core.numericUnary" else "SPL.unary " ++ quoted op
      pure (block [] (target ++ " (← " ++ (← expression value env) ++ ")"))
    | .binary _ op left right =>
      let a ← expression left env
      let b ← expression right env
      if op == "and" || op == "or" then
        pure ("(SPL." ++ (if op == "and" then "conjunction" else "disjunction") ++ " " ++ a ++ " (fun _ => " ++ b ++ "))")
      else
        let arithmetic := match op with
          | "+" => some "add" | "-" => some "subtract" | "*" => some "multiply" | "/" => some "divide" | _ => none
        let target := match arithmetic with
          | some arithmetic => if Check.dimensional left.meta.ty || Check.dimensional right.meta.ty then "SPL.binary " ++ quoted op else "SPL.Core.numericBinary ." ++ arithmetic
          | none => "SPL.binary " ++ quoted op
        pure (block [] (target ++ " (← " ++ a ++ ") (← " ++ b ++ ")"))
    | .ite _ condition yes no =>
      pure ("(SPL.conditional " ++ (← expression condition env) ++ " (fun _ => " ++ (← expression yes env) ++
        ") (fun _ => " ++ (← expression no env) ++ "))")
    | .record _ fields =>
      let values ← fields.mapM fun (key, value) => do pure (pair key (← expression value env))
      pure ("(SPL.recordValues " ++ brackets values ++ ")")
    | .list _ values => pure ("(SPL.listValues " ++ brackets (← values.mapM fun e => expression e env) ++ ")")
    | .choose _ arms fallback =>
      let values ← arms.mapM fun (predicate, body) => do
        pure ("(" ++ (← expression predicate env) ++ ", (fun _ => " ++ (← expression body env) ++ "))")
      let fallback ← match fallback with
        | none => pure "none"
        | some body => do pure ("(some (fun _ => " ++ (← expression body env) ++ "))")
      pure ("(SPL.choose " ++ brackets values ++ " " ++ fallback ++ ")")
    | .selectRules _ priority arms fallback =>
      let values ← arms.mapM fun (id, rank, predicate, body) => do
        pure ("(" ++ quoted id ++ ", (" ++ toString rank ++ " : Int), (fun _ => " ++
          (← expression predicate env) ++ "), (fun _ => " ++ (← expression body env) ++ "))")
      let fallback ← match fallback with
        | none => pure "none"
        | some (id, body) => do pure ("(some (" ++ quoted id ++ ", (fun _ => " ++ (← expression body env) ++ "))) ")
      pure ("(SPL.selectRules " ++ (if priority then "true" else "false") ++ " " ++ brackets values ++ " " ++ fallback ++ ")")
    | .apply _ _ parameters args declarations body =>
      let mut lines := []
      let mut nested : Names := []
      for ((name, _), arg) in parameters.zip args do
        let argumentVar ← fresh
        lines := lines ++ ["let " ++ argumentVar ++ " : SPL.Value ← " ++ (← expression arg env)]
        nested := nested ++ [(name, "(pure " ++ argumentVar ++ ")")]
      let (localLines, localEnv) ← scope (declarations.map localToDecl) nested
      pure (block (lines ++ localLines) (← expression body localEnv))
    | .fold _ source initial state event _ order declarations body =>
      let initialVar ← fresh
      let sourceVar ← fresh
      let stateVar ← fresh
      let eventVar ← fresh
      let lines := ["let " ++ initialVar ++ " ← " ++ (← expression initial env),
        "let " ++ sourceVar ++ " ← " ++ (← expression source env)]
      let (localLines, nested) ← scope (declarations.map localToDecl)
        ((state, "(pure " ++ stateVar ++ ")") :: (event, "(pure " ++ eventVar ++ ")") :: env)
      let step := "(fun " ++ stateVar ++ " " ++ eventVar ++ " => " ++ block localLines (← expression body nested) ++ ")"
      if let some (kb, key, ib, identity, ties) := order then
        let keyVar ← fresh
        let idVar ← fresh
        let keyBody ← expression key ((kb, "(pure " ++ keyVar ++ ")") :: env)
        let idBody ← expression identity ((ib, "(pure " ++ idVar ++ ")") :: env)
        pure (block lines ("SPL.orderedFoldValues " ++ initialVar ++ " " ++ sourceVar ++
          " (fun " ++ keyVar ++ " => " ++ keyBody ++ ") (fun " ++ idVar ++ " => " ++ idBody ++ ") " ++ quoted ties ++ " " ++ step))
      else pure (block lines ("SPL.foldValues " ++ initialVar ++ " " ++ sourceVar ++ " " ++ step))
    | .forEach _ name _ source declarations body =>
      let binderVar ← fresh
      let (lines, nested) ← scope (declarations.map localToDecl) ((name, "(pure " ++ binderVar ++ ")") :: env)
      let body := block lines (← expression body nested)
      pure (block [] ("SPL.mapValues (← " ++ (← expression source env) ++ ") (fun " ++ binderVar ++ " => " ++ body ++ ")"))
    | .collection m name binder _ source body =>
      let binderVar ← fresh
      let target ← match name with
        | "filter" => pure "filterValues"
        | "sum" => pure (match m.ty with
          | .quantity unit => "sumValuesFrom (.quantity " ++ quoted unit ++ " 0)"
          | .rate unit currency => "sumValuesFrom (.rate " ++ quoted unit ++ " " ++ quoted currency ++ " 0)"
          | _ => "sumValues")
        | "sort_by" => pure "sortValues"
        | "map" => pure "mapValues"
        | "group_by" => pure "groupValues"
        | _ => fail "UNSUPPORTED_BUILTIN" ("Unsupported typed collection " ++ name) m.span
      pure (block [] ("SPL." ++ target ++ " (← " ++ (← expression source env) ++ ") (fun " ++ binderVar ++
        " => " ++ (← expression body ((binder, "(pure " ++ binderVar ++ ")") :: env)) ++ ")"))
    | .indexed _ op source right kb _ key vb _ value =>
      let k ← fresh
      let v ← fresh
      let key ← expression key ((kb,"(pure " ++ k ++ ")") :: env)
      let value ← expression value ((vb,"(pure " ++ v ++ ")") :: env)
      let left ← expression source env
      let projections := " (fun " ++ k ++ " => " ++ key ++ ") (fun " ++ v ++ " => " ++ value ++ ")"
      if op == "make_map" then pure (block [] ("SPL.makeMap (← " ++ left ++ ")" ++ projections))
      else
        let some right := right | fail "INVALID_IR" "Join requires right source"
        pure (block [] ("SPL.joinValues " ++ (if op == "left_join" then "true" else "false") ++
          " (← " ++ left ++ ") (← " ++ (← expression right env) ++ ")" ++ projections))
    | .call m name args =>
      if name == "tuple" then
        return "(SPL.tupleValues " ++ brackets (← args.mapM fun e => expression e env) ++ ")"
      if name == "none" then return "(pure .absent)"
      if name == "some" then return block [] ("pure (.present (← " ++ (← expression args[0]! env) ++ "))")
      if name == "get_or" then return block [] ("SPL.getOr (← " ++ (← expression args[0]! env) ++
        ") (fun _ => " ++ (← expression args[1]! env) ++ ")")
      let values ← args.mapM fun e => do pure ("(← " ++ (← expression e env) ++ ")")
      let target ← match name with
        | "abs" => pure "absolute"
        | "min" => pure "extrema false"
        | "max" => pure "extrema true"
        | "in_period" => pure "inPeriod"
        | "add_calendar_months" => pure "addCalendarMonths"
        | "is_calendar_quarter" => pure "isCalendarQuarter"
          | "instant" => pure "instant"
        | "quantize" => pure "quantize"
        | "require_some" => pure "requireSome"
        | "is_some" => pure "isSome"
        | "tuple_get" => pure "tupleGet"
        | "lookup" => pure "mapLookup"
        | "entries" => pure "mapEntries"
        | "append" => pure "appendValue"
        | "concat" => pure "concatValues"
        | _ => fail "UNSUPPORTED_BUILTIN" ("Unsupported target builtin " ++ name) m.span
      pure (block [] ("SPL." ++ target ++ " " ++ String.intercalate " " values))

  private partial def scope (declarations : List Decl) (outer : Names) : Gen (List String × Names) := do
    let mut env := outer
    let mut functions : Names := []
    for declaration in declarations do
      match declaration with
      | .define _ name _ =>
        let functionName ← fresh
        functions := (name, functionName) :: functions
        env := (name, "(" ++ functionName ++ ".get)") :: env
      | _ => pure ()
    let mut lines := []
    let mut emitted := []
    -- Only memoizing thunks are hoisted. First demand forces a body inside its
    -- selected lazy branch; later demands reuse the same pure Except value.
    -- Each call/loop scope constructs fresh thunks, never a cross-input cache.
    for declaration in declarations do
      if let .define _ name _ := declaration then
        let (closureLines, doneNames) ← emitDefinition name declarations env functions emitted []
        lines := lines ++ closureLines
        emitted := doneNames
    for declaration in declarations do
      match declaration with
      | .define _ name _ =>
        let valueName ← fresh
        lines := lines ++ ["let " ++ valueName ++ " ← " ++ (env.lookup name).getD "unreachable"]
        env := (name, "(pure " ++ valueName ++ ")") :: env
      | .require _ expr code =>
        lines := lines ++ ["SPL.assertValue (← " ++ (← expression expr env) ++ ") " ++ quoted code]
      | _ => pure ()
    pure (lines, env)

  /-- Order definition closures by their static DAG without forcing any body. -/
  private partial def emitDefinition (name : String) (declarations : List Decl)
      (env functions : Names) (emitted active : List String) : Gen (List String × List String) := do
    if emitted.contains name then return ([], emitted)
    let some declaration := declarations.find? (fun d => definitionName d == some name)
      | return ([], emitted)
    let .define m _ body := declaration | return ([], emitted)
    if active.contains name then fail "DEPENDENCY_CYCLE" "Cyclic definition reached emitter" m.span
    let mut lines := []
    let mut doneNames := emitted
    for reference in references body do
      let (requiredLines, nextDone) ← emitDefinition reference declarations env functions doneNames (name :: active)
      lines := lines ++ requiredLines
      doneNames := nextDone
    lines := lines ++ ["let " ++ (functions.lookup name).getD "unreachable" ++
      " : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => " ++ (← expression body env) ++ ")"]
    pure (lines, name :: doneNames)

  private partial def localToDecl : LocalDecl → Decl
    | .define m name expr => .define m name expr
    | .require span expr code => .require span expr code
end

private def declarationName : Decl → String
  | .input _ name | .opening _ name _ | .define _ name _ | .closing _ name _ | .emit _ name _ => name
  | .require m _ _ => "require@" ++ toString m.span.line ++ ":" ++ toString m.span.column

private def declarationCitation : Decl → String
  | .define m _ _ => m.citation.getD ""
  | _ => ""

private partial def typeSource : Ty → String
  | .atom name =>
    if name.startsWith "Id:" then
      "(.named \"Id\" [(.named " ++ quoted (String.intercalate ":" ((name.splitOn ":").drop 1)) ++ " [])])"
    else "(.named " ++ quoted name ++ " [])"
  | .money currency => "(.named \"Money\" [(.named " ++ quoted currency ++ " [])])"
  | .quantity unit => "(.named \"Quantity\" [(.named " ++ quoted unit ++ " [])])"
  | .rate unit currency => "(.named \"Rate\" [(.named " ++ quoted unit ++ " []), (.named " ++ quoted currency ++ " [])])"
  | .list item => "(.named \"List\" [" ++ typeSource item ++ "])"
  | .option item => "(.named \"Option\" [" ++ typeSource item ++ "])"
  | .tuple items => "(.named \"Tuple\" " ++ brackets (items.map typeSource) ++ ")"
  | .map key value => "(.named \"Map\" [" ++ typeSource key ++ ", " ++ typeSource value ++ "])"
  | .record name fields => if name == "literal" then
      "(.record " ++ brackets (fields.map fun (n,t) => pair n (typeSource t)) ++ ")"
    else "(.named " ++ quoted name ++ " [])"

/-- Injective ASCII encoding of Unicode scalar schedule names. It avoids Lean
keywords, punctuation, and collisions caused by replacing punctuation with `_`. -/
def scheduleNamespace (name : String) : String :=
  "GeneratedSPL.S" ++ String.join (name.toList.map fun c => "_" ++ toString c.toNat)

private def generate (schedule : Program) (standalone : Bool) : Gen String := do
  let mut env : Names := []
  let mut lines : List String := []
  for declaration in schedule.declarations do
    match declaration with
    | .input _ name | .opening _ name _ =>
      let binderVar ← fresh
      env := (name, "(pure " ++ binderVar ++ ")") :: env
      let source := match declaration with | .input .. => "_inputs" | _ => "_openings"
      lines := lines ++ ["let " ++ binderVar ++ " ← SPL.lookup " ++ source ++ " " ++ quoted name]
    | _ => pure ()
  let (body, nestedEnv) ← scope schedule.declarations env
  env := nestedEnv
  lines := lines ++ body
  let mut emissions := []
  let mut closing := []
  for declaration in schedule.declarations do
    match declaration with
    | .emit _ name expr | .closing _ name expr =>
      let binderVar ← fresh
      lines := lines ++ ["let " ++ binderVar ++ " ← " ++ (← expression expr env)]
      match declaration with
      | .emit .. => emissions := emissions ++ [pair name binderVar]
      | _ => closing := closing ++ [pair name binderVar]
    | _ => pure ()
  let result := "pure { emissions := " ++ brackets emissions ++ ", closing := " ++ brackets closing ++ " }"
  let rules := brackets (schedule.declarations.map fun d => pair (declarationName d) (quoted (declarationCitation d)))
  let inputTypes := brackets (schedule.declarations.filterMap fun d => match d with
    | .input m name => some (pair name (typeSource m.ty)) | _ => none)
  let openingTypes := brackets (schedule.declarations.filterMap fun d => match d with
    | .opening m name _ => some (pair name (typeSource m.ty)) | _ => none)
  let ns := scheduleNamespace schedule.name
  let entry := if standalone then
    "\n\nnamespace GeneratedSPL\n" ++
    "abbrev scheduleName := " ++ ns ++ ".scheduleName\n" ++
    "abbrev sourceRules := " ++ ns ++ ".sourceRules\n" ++
    "abbrev settle := " ++ ns ++ ".settle\n" ++
    "end GeneratedSPL\n\n" ++
    "def main (args : List String) : IO UInt32 :=\n  SPL.Bindings.runMain " ++ inputTypes ++ " " ++ openingTypes ++ " " ++ ns ++ ".settle args\n"
    else "\n"
  pure ("import SPL.Fold\nimport SPL.Core\nimport SPL.Bindings\n\nset_option maxRecDepth 4096\nset_option maxHeartbeats 0\n\nnamespace " ++ ns ++ "\n\n" ++
    "def scheduleName : String := " ++ quoted schedule.name ++ "\n" ++
    "def sourceRules : List (String × String) := " ++ rules ++ "\n\n" ++
    "def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := " ++ block lines result ++
    "\n\nend " ++ ns ++ entry)

def emitIR (schedule : Program) : Except Diagnostic String := do
  ValidateIR.validate schedule
  pure ((← generate schedule true |>.run 0).1)

/-- Importable module mode has only schedule-specific declarations, with no
global executable entry or convenience aliases that collide across modules. -/
def emitLibraryIR (schedule : Program) : Except Diagnostic String := do
  ValidateIR.validate schedule
  pure ((← generate schedule false |>.run 0).1)

/-- Compatibility entry: checking and elaboration happen before generation. -/
def emit (schedule : Syntax.Schedule) : Except Diagnostic String := do
  emitIR (← Elaborate.elaborate schedule)

end SPL.Emit

