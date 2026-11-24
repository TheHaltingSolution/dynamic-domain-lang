import SPL.IR

/-! A serialized artifact version/admission shape gate. This does not execute
JSON IR; typed Program validation separately re-infers source/owner edges. -/
namespace SPL.IRArtifact
open Lean

private def reject : Except String α := .error "INVALID_IR"

private def fields (value : Json) : Except String (List (String × Json)) := do
  pure (← value.getObj? |>.mapError (fun _ => "INVALID_IR")).toList

private def exact (value : Json) (names : List String) : Except String Unit := do
  let keys := (← fields value).map Prod.fst
  unless keys.length == names.length && keys.all names.contains do reject

private def get (value : Json) (key : String) : Except String Json :=
  value.getObjVal? key |>.mapError (fun _ => "INVALID_IR")

private def text (value : Json) : Except String String := value.getStr? |>.mapError (fun _ => "INVALID_IR")
private def array (value : Json) : Except String (List Json) := do
  pure (← value.getArr? |>.mapError (fun _ => "INVALID_IR")).toList
private def strings (value : Json) : Except String (List String) := do (← array value).mapM text

private partial def walk (extended : Bool) (meanings : Dimensions.Meanings)
    (signatures : List (String × Json)) (value : Json) : Except String Unit := do
  match value with
  | .arr values => for child in values do walk extended meanings signatures child
  | .obj entries =>
    if let some mdata := entries.get? "meta" then
      let allowed := ["id", "span", "type", "citation"] ++ (if extended then ["source_annotation"] else [])
      let keys := (← fields mdata).map Prod.fst
      unless keys.all allowed.contains && ["id", "span", "type"].all keys.contains do reject
      if entries.get? "kind" == some (.str "apply") then
        exact value ["kind", "meta", "function", "parameters", "arguments", "declarations", "body"]
        if extended then
          let label ← text (← get value "function")
          let some signature := signatures.lookup label | reject
          unless (← get value "parameters") == (← get signature "parameters") &&
              (← get mdata "type") == (← get signature "result") do reject
    if entries.get? "kind" == some (.str "quantity") || entries.get? "kind" == some (.str "rate") then
      let unit ← text (← get value "unit")
      unless Dimensions.known meanings unit do reject
      if entries.get? "kind" == some (.str "rate") then
        unless (← text (← get value "currency")) == "USD" do reject
    for (_, child) in entries.toList do walk extended meanings signatures child
  | _ => pure ()

def validate (value : Json) : Except String Unit := do
  let version ← text (← get value "format")
  unless version == "spl-ir/0.1" || version == "spl-ir/0.2" do reject
  let extended := version == "spl-ir/0.2"
  exact value (["format", "name", "language", "core", "schema", "span", "declarations"] ++
    (if extended then ["dimension_admission"] else []))
  let (meanings, signatures) ← if extended then do
      let snapshot ← get value "dimension_admission"
      exact snapshot ["features", "owners", "unit_definitions", "relations", "signatures"]
      let features ← strings (← get snapshot "features")
      let _ ← Dimensions.prepare features |>.mapError (fun _ => "INVALID_IR")
      let mut owners := []
      for owner in ← array (← get snapshot "owners") do
        exact owner ["label", "features"]
        let label ← text (← get owner "label")
        unless !label.isEmpty && !(owners.map Prod.fst).contains label do reject
        let ownerFeatures ← strings (← get owner "features")
        let _ ← Dimensions.prepare ownerFeatures |>.mapError (fun _ => "INVALID_IR")
        owners := owners ++ [(label, ownerFeatures)]
      let allFeatures := (features ++ owners.flatMap Prod.snd).eraseDups
      if allFeatures.isEmpty then reject
      let expected := IR.admissionJson features owners (Dimensions.definitionPins allFeatures) (Dimensions.relationPins allFeatures)
      let stripSignatures (value : Json) : Except String Json := do
        pure (Json.mkObj ((← fields value).filter (fun (key, _) => key != "signatures")))
      unless (← stripSignatures snapshot) == (← stripSignatures expected) do reject
      let mut signatures := []
      for signature in ← array (← get snapshot "signatures") do
        exact signature ["label", "parameters", "result"]
        let label ← text (← get signature "label")
        let some ownerFeatures := owners.lookup label | reject
        unless !label.isEmpty && !(signatures.map Prod.fst).contains label do reject
        let ownerMeanings : Dimensions.Meanings := { features := ownerFeatures }
        let mut names := []
        for parameter in ← array (← get signature "parameters") do
          exact parameter ["name", "type"]
          let name ← text (← get parameter "name")
          if names.contains name then reject
          names := name :: names
          walk false ownerMeanings [] (← get parameter "type")
        walk false ownerMeanings [] (← get signature "result")
        signatures := signatures ++ [(label, signature)]
      pure (({ features := allFeatures } : Dimensions.Meanings), signatures)
    else pure (({} : Dimensions.Meanings), [])
  walk extended meanings signatures (← get value "declarations")

end SPL.IRArtifact
