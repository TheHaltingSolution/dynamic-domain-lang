import SPL.Fold

/-! Small executable boundary witnesses; no whole-compiler proof claim. -/
open SPL

private def blocked (expected : String) : Eval α → Bool
  | .error code => code == expected
  | .ok _ => false

def main : IO Unit := do
  let maximum := List.replicate maxCollectionItems (Value.num 0)
  unless blocked "RESOURCE_LIMIT" (appendValue (.seq maximum) (.num 1)) do
    throw (IO.userError "append must reject one item beyond the fixed collection envelope")
  unless blocked "RESOURCE_LIMIT" (concatValues (.seq maximum) (.seq [.num 1])) do
    throw (IO.userError "concat must reject an oversized intermediate collection")
  unless blocked "RESOURCE_LIMIT" (foldValues (.num 7) (.seq (.num 0 :: maximum)) (fun _ _ => .error "STEP")) do
    throw (IO.userError "oversized fold input must fail before any step")
  unless blocked "DUPLICATE_EVENT_ID" (orderFoldEntries [(.num 1,.text "a",.num 1),(.num 2,.text "a",.num 2)] "reject") do
    throw (IO.userError "different event keys cannot hide repeated declared identity")
  IO.println "Finite fold resource and identity boundaries passed."
