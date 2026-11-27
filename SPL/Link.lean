import Lean
import SPL.Parser
import SPL.Check

/-! Pure first-order linking of a registry-verified source manifest. The canonical
registry verifies all descriptor/source hashes and complete transitive pins before
constructing this value. This pass performs no IO and no textual substitution.
Every imported call becomes an isolated, strict application node. -/
namespace SPL.Link
open Syntax

private abbrev LinkResult := Except Diagnostic

private def reject (code message : String) : LinkResult α :=
  .error { code, message }

private def field (json : Lean.Json) (name : String) : LinkResult Lean.Json :=
  json.getObjVal? name |>.mapError (fun _ => { code := "INVALID_LINK_MANIFEST", message := "Missing " ++ name })

private def text (json : Lean.Json) : LinkResult String :=
  json.getStr? |>.mapError (fun _ => { code := "INVALID_LINK_MANIFEST", message := "Expected string" })

private def array (json : Lean.Json) : LinkResult (List Lean.Json) :=
  json.getArr? |>.map (·.toList) |>.mapError (fun _ => { code := "INVALID_LINK_MANIFEST", message := "Expected array" })

private partial def typeExpr (json : Lean.Json) : LinkResult TypeExpr := do
  let name ← text (← field json "name")
  -- Structural records carry fields; an opaque Id kind named Record does not.
  if name == "Record" && (json.getObjVal? "fields").isOk then
    let fields ← array (← field json "fields")
    return .record (← fields.mapM fun item => do
      let pair ← array item
      let [key, ty] := pair | reject "INVALID_LINK_MANIFEST" "Record fields must be pairs"
      pure (← text key, ← typeExpr ty))
  return .named name (← (← array (← field json "args")).mapM typeExpr)

private def referenceKey (json : Lean.Json) : LinkResult String := do
  let fields ← json.getObj? |>.mapError (fun _ => ({ code := "INVALID_MODULE_REFERENCE", message := "Expected reference object" } : Diagnostic))
  unless fields.toList.length == 4 do reject "INVALID_MODULE_REFERENCE" "Require exact four-field reference"
  let id ← text (← field json "id")
  let revision ← text (← field json "revision")
  let locator ← text (← field json "locator")
  let sha ← text (← field json "sha256")
  return (Lean.Json.arr #[.str id, .str revision, .str locator, .str sha]).compress

private def describeReference (key : String) : String :=
  match Lean.Json.parse key with
  | .ok (.arr #[.str id, .str revision, .str locator, _]) => s!"{id}@{revision} ({locator})"
  | _ => key

private structure Export where
  name : String
  parameters : List (String × TypeExpr)
  result : TypeExpr
  definition : String
  deriving Inhabited

private structure Module where
  key : String
  id : String
  revision : String
  source : Schedule
  imports : List Lean.Json
  exports : List Export
  deriving Inhabited

private abbrev Target := String × String
private abbrev Names := List (String × Target)

private def builtins (features : List String := []) : List String := ["filter", "map", "sum", "sort_by", "min", "max", "instant",
  "in_period", "is_calendar_quarter", "add_calendar_months", "quantize", "require_some", "tuple", "tuple_get",
  "make_map", "lookup", "entries", "group_by", "join", "left_join", "some", "none", "get_or", "is_some", "append", "concat"] ++
  Dimensions.builtinNames features

private def parseExport (json : Lean.Json) : LinkResult Export := do
  let parameters ← (← array (← field json "parameters")).mapM fun p => do
    pure (← text (← field p "name"), ← typeExpr (← field p "type"))
  let name ← text (← field json "name")
  let result ← typeExpr (← field json "result")
  let definition ← text (← field json "definition")
  return { name, parameters, result, definition }

private def parseModule (json : Lean.Json) : LinkResult Module := do
  let reference ← field json "reference"
  let key ← referenceKey reference
  let descriptor ← field json "descriptor"
  let id ← text (← field descriptor "id")
  let revision ← text (← field descriptor "revision")
  unless id == (← text (← field reference "id")) && revision == (← text (← field reference "revision")) do
    reject "MODULE_IDENTITY_MISMATCH" "Descriptor and exact reference disagree"
  let source ← (Parser.parse (← text (← field json "source"))).mapError fun d =>
    { d with message := s!"Linked source {describeReference key}: {d.message}" }
  (Check.check { source with declarations := [] }).mapError fun d =>
    { d with message := s!"Linked source {describeReference key}: {d.message}" }
  unless source.declarations.all (fun d => match d with | .input .. | .define .. | .require .. => true | _ => false) do
    reject "INVALID_FUNCTION_MODULE" "Function modules permit inputs, definitions and assertions"
  let exports ← (← array (← field (← field descriptor "interface") "exports")).mapM parseExport
  let names := exports.map (·.name)
  if Check.duplicate names then reject "DUPLICATE_EXPORT" "Export names must be unique"
  if names.any (builtins source.features).contains then reject "AMBIGUOUS_EXPORT" "Export collides with published builtin"
  let moduleImports ← array (← field descriptor "imports")
  return { key, id, revision, source, exports, imports := moduleImports }

private def imports (modules : List Module) (specs : List Lean.Json) (own : List String := [])
    (features : List String := []) : LinkResult Names := do
  let mut aliases : List String := []
  let mut names : Names := []
  for spec in specs do
    let key ← referenceKey (← field spec "module_ref")
    let some dependency := modules.find? (·.key == key)
      | reject "UNRESOLVED_MODULE" s!"No exact module pin matches {describeReference key}"
    let alias ← text (← field spec "alias")
    if aliases.contains alias then reject "AMBIGUOUS_IMPORT" "Import aliases must be unique"
    aliases := alias :: aliases
    for symbol in ← array (← field spec "symbols") do
      let name ← text (← field symbol "local")
      let exported ← text (← field symbol "export")
      if (names.lookup name).isSome || own.contains name || (builtins features).contains name then
        reject "AMBIGUOUS_IMPORT" ("Imported local name collides: " ++ name)
      unless dependency.exports.any (·.name == exported) do
        reject "UNRESOLVED_EXPORT" s!"{describeReference key} does not export {exported} for import as {name}"
      names := names ++ [(name, (key, exported))]
  return names

private partial def acyclic (modules : List Module) (key : String) (active : List String) : LinkResult Unit := do
  if active.contains key then reject "MODULE_IMPORT_CYCLE" s!"Module import cycle reaches {describeReference key}"
  let some sourceModule := modules.find? (·.key == key)
    | reject "UNRESOLVED_MODULE" s!"No exact transitive module pin matches {describeReference key}"
  for spec in sourceModule.imports do acyclic modules (← referenceKey (← field spec "module_ref")) (key :: active)

mutual
  private partial def expression (modules : List Module) (names : Names) (active : List Target) : Expr → LinkResult Expr
    | .unary s op e => return .unary s op (← expression modules names active e)
    | .binary s op a b => return .binary s op (← expression modules names active a) (← expression modules names active b)
    | .field s e name => return .field s (← expression modules names active e) name
    | .ite s c y n => return .ite s (← expression modules names active c) (← expression modules names active y) (← expression modules names active n)
    | .call s name args => do
      let args ← args.mapM (expression modules names active)
      if let some target := names.lookup name then
        let (parameters, result, declarations, body, label) ← function modules target active
        return .apply s label parameters args result declarations body
      return .call s name args
    | .lambda s name body => return .lambda s name (← expression modules names active body)
    | .record s fields => return .record s (← fields.mapM fun (name, e) => do pure (name, ← expression modules names active e))
    | .list s items => return .list s (← items.mapM (expression modules names active))
    | .choose s arms fallback => do
      return .choose s
        (← arms.mapM fun (p, b) => do pure (← expression modules names active p, ← expression modules names active b))
        (← fallback.mapM (expression modules names active))
    | .selectRules s priority arms fallback => do
      return .selectRules s priority
        (← arms.mapM fun (id, rank, p, b) => do pure (id, rank, ← expression modules names active p, ← expression modules names active b))
        (← fallback.mapM fun (id, b) => do pure (id, ← expression modules names active b))
    | .forEach s name source declarations body => do
      return .forEach s name (← expression modules names active source)
        (← declarations.mapM (localDecl modules names active)) (← expression modules names active body)
    | .fold s source initial state event order declarations body => do
      let order ← order.mapM fun (kb, key, ib, identity, ties) => do
        pure (kb, ← expression modules names active key, ib, ← expression modules names active identity, ties)
      return .fold s (← expression modules names active source) (← expression modules names active initial) state event order
        (← declarations.mapM (localDecl modules names active)) (← expression modules names active body)
    | .apply .. => reject "INVALID_FUNCTION_MODULE" "Application nodes cannot occur in unlinked source"
    | other => pure other

  private partial def localDecl (modules : List Module) (names : Names) (active : List Target) : LocalDecl → LinkResult LocalDecl
    | .define s name ty body citation => return .define s name ty (← expression modules names active body) citation
    | .require s body code => return .require s (← expression modules names active body) code

  private partial def function (modules : List Module) (target : Target) (active : List Target) :
      LinkResult (List (String × TypeExpr) × TypeExpr × List LocalDecl × Expr × String) := do
    if active.contains target then reject "FUNCTION_CALL_CYCLE" "Function calls must be nonrecursive"
    if active.length >= 128 then reject "RESOURCE_LIMIT" "Function expansion depth exceeds 128"
    let some sourceModule := modules.find? (·.key == target.1) | reject "UNRESOLVED_MODULE" "Missing function module"
    let some exported := sourceModule.exports.find? (·.name == target.2) | reject "UNRESOLVED_EXPORT" "Missing export"
    let inputs := sourceModule.source.declarations.filterMap fun d => match d with
      | .input _ name ty => some (name, ty) | _ => none
    unless inputs == exported.parameters do reject "FUNCTION_INTERFACE_MISMATCH" "Function parameters must exactly match source inputs"
    let some definition := sourceModule.source.declarations.find? (fun d => match d with
      | .define _ name .. => name == exported.definition | _ => false)
      | reject "UNRESOLVED_EXPORT" "Export definition is absent"
    let .define s name .. := definition | reject "UNRESOLVED_EXPORT" "Export must name a definition"
    let names ← imports modules sourceModule.imports (sourceModule.exports.map (·.name)) sourceModule.source.features
    for declaration in sourceModule.source.declarations do
      let binding := match declaration with | .input _ name _ | .define _ name .. => some name | _ => none
      if binding.any (fun n => (names.lookup n).isSome) then reject "AMBIGUOUS_IMPORT" "Imported function collides with module binding"
    let names := names ++ sourceModule.exports.map (fun e => (e.name, (sourceModule.key, e.name)))
    let locals := sourceModule.source.declarations.filterMap fun d => match d with
      | .define s name ty body citation => some (LocalDecl.define s name ty body citation)
      | .require s body code => some (LocalDecl.require s body code) | _ => none
    let locals ← locals.mapM (localDecl modules names (target :: active))
    return (exported.parameters, exported.result, locals, .name s name,
      sourceModule.id ++ "@" ++ sourceModule.revision ++ ":" ++ exported.name)
end

private def ownerContexts (modules : List Module) : List (String × List String) :=
  modules.flatMap fun sourceModule =>
    ("@module:" ++ sourceModule.key, sourceModule.source.features) ::
    sourceModule.exports.map (fun exported =>
      (sourceModule.id ++ "@" ++ sourceModule.revision ++ ":" ++ exported.name, sourceModule.source.features))

private def linkedSignatures (modules : List Module) : List FunctionSignature :=
  modules.flatMap fun sourceModule => sourceModule.exports.map fun exported => {
    label := sourceModule.id ++ "@" ++ sourceModule.revision ++ ":" ++ exported.name
    parameters := exported.parameters
    result := exported.result }

def link (schedule : Schedule) (manifest : Lean.Json) : LinkResult Schedule := do
  let modules ← (← array (← field manifest "modules")).mapM parseModule
  if Check.duplicate (modules.map (·.key)) then reject "DUPLICATE_MODULE" "Repeated exact module reference"
  let owners := ownerContexts modules
  let extended := !schedule.features.isEmpty || owners.any (fun (_, features) => !features.isEmpty)
  let signatures := if extended then linkedSignatures modules else []
  for sourceModule in modules do
    acyclic modules sourceModule.key []
    for exported in sourceModule.exports do
      let (parameters, result, declarations, body, label) ← function modules (sourceModule.key, exported.name) []
      let settings ← Check.inference { sourceModule.source with owners, signatures }
      let context ← parameters.mapM fun (name, ty) => do pure (name, ← Check.parseTypeWith settings.lexical ty)
      let _ ← Check.inferWith settings context (.apply {} label parameters (parameters.map fun (name, _) => .name {} name) result declarations body)
  let names ← imports modules (← array (← field manifest "imports")) [] schedule.features
  for declaration in schedule.declarations do
    let name := match declaration with | .input _ name _ | .opening _ name _ _ | .define _ name .. => some name | _ => none
    if name.any (fun n => (names.lookup n).isSome) then reject "AMBIGUOUS_IMPORT" "Imported function collides with schedule binding"
  let declarations ← schedule.declarations.mapM fun d => do
    match d with
    | .define s name ty body citation => return .define s name ty (← expression modules names [] body) citation
    | .require s body code => return .require s (← expression modules names [] body) code
    | .closing s name body => return .closing s name (← expression modules names [] body)
    | .emit s name body => return .emit s name (← expression modules names [] body)
    | other => pure other
  return { schedule with declarations, owners := if extended then owners else [], signatures }

end SPL.Link
