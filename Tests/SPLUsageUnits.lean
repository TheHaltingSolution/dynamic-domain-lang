import SPL.Parser
import SPL.Link
import SPL.Elaborate
import SPL.ValidateIR
import SPL.IRArtifact
import SPL.Interpret
import SPL.Emit
import SPL.Bindings

/-! Hostile typed IR fails before observation or emitted calculation. JSON
checks are a separately labelled shape preflight, never JSON execution. -/
open SPL SPL.IR

private def load (path : String) (manifest : Option String := none) : IO Program := do
  let source ← IO.FS.readFile path
  let parsed ← match Parser.parse source with
    | .ok value => pure value
    | .error error => throw (IO.userError s!"parse {error.code}: {error.message}")
  let linked ← match manifest with
    | none => pure parsed
    | some path =>
      let json ← match Lean.Json.parse (← IO.FS.readFile path) with
        | .ok value => pure value
        | .error error => throw (IO.userError error)
      match Link.link parsed json with
      | .ok value => pure value
      | .error error => throw (IO.userError s!"link {error.code}: {error.message}")
  match Elaborate.elaborate linked with
  | .ok value => pure value
  | .error error => throw (IO.userError s!"elaborate {error.code}: {error.message}")

private def requireValid (label : String) (program : Program) : IO Unit := do
  match ValidateIR.validate program with
  | .ok _ => pure ()
  | .error error => throw (IO.userError s!"valid {label} failed: {error.code}: {error.message}")

private def requireBlocked (label : String) (program : Program) : IO Unit := do
  match ValidateIR.validate program with
  | .error error => unless error.code == "INVALID_IR" do throw (IO.userError s!"wrong IR diagnostic {label}: {error.code}")
  | .ok _ => throw (IO.userError s!"forged IR accepted: {label}")
  let outcome := Interpret.interpret program [] []
  unless outcome.result matches .error "INVALID_IR" do throw (IO.userError s!"interpreter accepted: {label}")
  unless outcome.trace.json == .arr #[] do throw (IO.userError s!"preflight emitted observations: {label}")
  match Emit.emitIR program with
  | .error error => unless error.code == "INVALID_IR" do throw (IO.userError s!"wrong emit diagnostic {label}")
  | .ok _ => throw (IO.userError s!"emitter accepted: {label}")

private def changeApplication (program : Program) (change : Expr → Expr) : Program :=
  { program with declarations := program.declarations.map fun declaration =>
    match declaration with
    | .define m "h" body => .define m "h" (change body)
    | other => other }

private def explicitHour (program : Program) : Program :=
  { program with declarations := program.declarations.map fun declaration =>
    match declaration with
    | .define m "h" body => .define { m with sourceAnnotation := some (.quantity "UsageHour") } "h" body
    | other => other }

private def extraEmpty (program : Program) (option : Bool) : Program :=
  let ty : Ty := if option then .option (.quantity "UsageHour") else .list (.quantity "UsageHour")
  let m : Meta := { id := 900001, span := {}, ty }
  let body := if option then Expr.call { m with id := 900002 } "none" [] else Expr.list { m with id := 900002 } []
  { program with declarations := program.declarations ++ [.emit m "ungrounded" body] }

private partial def addApplicationOwner (value : Lean.Json) : Lean.Json :=
  match value with
  | .arr values => .arr (values.map addApplicationOwner)
  | .obj entries =>
    let fields := entries.toList
    if entries.get? "kind" == some (.str "apply") then
      Lean.Json.mkObj (fields ++ [("owner_context", Lean.Json.mkObj [])])
    else Lean.Json.mkObj (fields.map fun (key, child) => (key, addApplicationOwner child))
  | _ => value

def main (args : List String) : IO UInt32 := do
  let [extendedSource, foreignSource, foreignManifest, unusedSource, unusedManifest, legacyArtifact] := args
    | throw (IO.userError "six fixture arguments required")
  let extended ← load extendedSource
  let foreign ← load foreignSource foreignManifest
  let unused ← load unusedSource unusedManifest
  requireValid "extended" extended
  requireValid "foreign" foreign
  requireValid "unused" unused
  unless foreign.features.isEmpty && unused.features.isEmpty && unused.format == "spl-ir/0.2" &&
      !unused.signatures.isEmpty do throw (IO.userError "closure/inference fixture lost ownership")
  let firstSignature := foreign.signatures.head!
  let baseOnly : Program := { unused with
    format := "spl-ir/0.1", features := [], owners := [], unitDefinitions := [], conversions := [], signatures := [] }
  let forgedResult := changeApplication foreign fun body => match body with
    | .apply m label parameters args declarations value =>
      .apply { m with ty := .quantity "UsageMinute" } label parameters args declarations value
    | other => other
  let forgedParameters := changeApplication foreign fun body => match body with
    | .apply m label parameters args declarations value =>
      .apply m label (parameters.map fun (name, _) => (name, .quantity "UsageHour")) args declarations value
    | other => other
  let unknownApplication := changeApplication foreign fun body => match body with
    | .apply m _ parameters args declarations value => .apply m "unknown-owner" parameters args declarations value
    | other => other
  let bads : List (String × Program) := [
    ("downgraded-v2", { extended with format := "spl-ir/0.1" }),
    ("wrong-unit-pin", { extended with unitDefinitions := extended.unitDefinitions.map fun (id, _) => (id, "forged") }),
    ("wrong-relation-pin", { extended with conversions := extended.conversions.map fun (id, _) => (id, "59:1") }),
    ("missing-unit-pins", { extended with unitDefinitions := [] }),
    ("unknown-feature", { extended with features := ["spl.usage-time/999"] }),
    ("duplicate-feature", { extended with features := extended.features ++ extended.features }),
    ("forged-apply-result", forgedResult),
    ("forged-apply-parameters", forgedParameters),
    ("unknown-application-owner", unknownApplication),
    ("duplicate-owner", { foreign with owners := foreign.owners ++ foreign.owners }),
    ("forged-owner-admission", { foreign with owners := foreign.owners.map fun (label, features) =>
      (label, if label == firstSignature.label then [] else features) }),
    ("duplicate-signature", { foreign with signatures := foreign.signatures ++ foreign.signatures }),
    ("unknown-signature-owner", { foreign with signatures := foreign.signatures.map fun signature =>
      { signature with label := "unknown-owner" } }),
    ("forged-signature-result", { foreign with signatures := foreign.signatures.map fun signature =>
      { signature with result := .quantity "UsageMinute" } }),
    ("explicit-root-hour-annotation", explicitHour foreign),
    ("v1-hidden-empty-hour", extraEmpty baseOnly false),
    ("v1-hidden-none-hour", extraEmpty baseOnly true),
    ("ungrounded-empty-hour", extraEmpty unused false),
    ("ungrounded-none-hour", extraEmpty unused true)]
  for (label, program) in bads do
    requireBlocked label program
    IO.println (Lean.Json.mkObj [("case", .str label), ("status", .str "blocked"),
      ("stage", .str "typed_ir_preflight"), ("observations", Lean.toJson (0 : Nat)),
      ("backends", .arr #[.str "native_validator", .str "native_interpreter", .str "native_emitter"])]).compress
  let legacy ← match Lean.Json.parse (← IO.FS.readFile legacyArtifact) with
    | .ok value => pure value
    | .error error => throw (IO.userError error)
  let .obj legacyFields := legacy | throw (IO.userError "legacy artifact object required")
  let badJson := [
    ("v1-empty-admission", Lean.Json.mkObj (legacyFields.toList ++ [("dimension_admission", Lean.Json.mkObj [])])),
    ("v1-application-owner", addApplicationOwner legacy)]
  for (label, value) in badJson do
    unless IRArtifact.validate value matches .error _ do throw (IO.userError s!"JSON metadata accepted: {label}")
    IO.println (Lean.Json.mkObj [("case", .str label), ("status", .str "blocked"),
      ("stage", .str "artifact_shape_preflight"), ("execution", .str "not_executed")]).compress
  let minute := Dimensions.definitions[1]!
  let hour := Dimensions.definitions[2]!
  unless Dimensions.validateRelation minute 59 hour 1 matches .error "CONVERSION_SCALE_MISMATCH" do
    throw (IO.userError "59:1 contradicted endpoint scales but was admitted")
  unless Dimensions.validateRelation minute 120 hour 2 matches .ok () do
    throw (IO.userError "120:2 scale consistency failed")
  unless Dimensions.conversionFactor { features := [Dimensions.usageFeature] }
      "UsageMinute" "UsageHour" "unregistered:120-2" matches .error "UNSUPPORTED_CONVERSION" do
    throw (IO.userError "Scale-consistent unregistered relation was executable")
  unless Dimensions.validateRelation minute 59 { hour with scale := 59 } 1 matches .error "UNIT_DEFINITION_MISMATCH" do
    throw (IO.userError "Changed immutable endpoint was admitted")
  for label in ["native-59-rejected", "native-120-consistent-not-registered", "native-definition-drift-rejected"] do
    IO.println (Lean.Json.mkObj [("case", .str label), ("status", .str "passed"),
      ("stage", .str "catalog_validation"), ("execution", .str "not_financial_execution")]).compress
  -- Independent dictionary payload/pin equality is verified by the Python test.
  IO.println (Lean.Json.mkObj [("case", .str "catalog-payload"), ("units", .arr (Dimensions.definitions.map fun unit =>
    Lean.Json.mkObj [("id", .str unit.id), ("name", .str unit.name), ("family", .str unit.family),
      ("base", .str unit.base), ("scale_to_base", .str (if unit.scale.den == 1 then toString unit.scale.num else
        toString unit.scale.num ++ "/" ++ toString unit.scale.den)), ("pin", .str unit.pin)]).toArray)]).compress
  return 0
