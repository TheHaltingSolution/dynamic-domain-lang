import SPL.Bindings

/-! Input admission for the two-receipt royalties profile. The argument file
contains ordered original receipt identities and exact USD amounts. The
financial artifact receives the amounts in that same order. -/

namespace SPL.RoyaltiesAdmission

open Lean

structure Receipt where
  id : String
  amount : Rat

structure ReceiptPair where
  first : Receipt
  second : Receipt

def ReceiptPair.identifiers (pair : ReceiptPair) : List String :=
  [pair.first.id, pair.second.id]

private def decodeReceipt (value : Json) : Except String Receipt := do
  let fields ← value.getObj? |>.mapError (fun _ => "RECEIPT_INPUT_SHAPE")
  unless fields.size == 2 do throw "RECEIPT_INPUT_SHAPE"
  let id ← value.getObjVal? "id" |>.mapError (fun _ => "RECEIPT_INPUT_SHAPE")
  let amount ← value.getObjVal? "amount" |>.mapError (fun _ => "RECEIPT_INPUT_SHAPE")
  let id ← asText (← Bindings.decode (Check.idTy "Receipt") id)
  let amount ← Bindings.exact amount
  pure {id, amount}

private def decodePair (value : Json) : Except String ReceiptPair := do
  let fields ← value.getObj? |>.mapError (fun _ => "RECEIPT_INPUT_SHAPE")
  unless fields.size == 1 do throw "RECEIPT_INPUT_SHAPE"
  let receipts ← value.getObjVal? "receipts" |>.mapError (fun _ => "RECEIPT_INPUT_SHAPE")
  let rows ← receipts.getArr? |>.mapError (fun _ => "RECEIPT_INPUT_SHAPE")
  let [first, second] := rows.toList | throw "RECEIPT_COUNT"
  pure ⟨← decodeReceipt first, ← decodeReceipt second⟩

/-- Parse the same input bytes that the tool stages for this invocation, then
admit only an exact pair with distinct original receipt identities. -/
def admit (source : String) : Except String ReceiptPair :=
  ((Bindings.parseStrict source).bind decodePair).bind fun pair =>
    (Bindings.checkDistinctIdentifiers pair.identifiers "DUPLICATE_RECEIPT_ID").bind fun _ =>
      .ok pair

/-- Every successful admission returns distinct supplied identities. The
claim concerns the staged input pair and its IDs, with no assumption about
their spelling beyond the executable decoder's identifier profile. -/
theorem admit_identifiers_nodup {source : String} {pair : ReceiptPair}
    (accepted : admit source = .ok pair) : pair.identifiers.Nodup := by
  unfold admit at accepted
  cases decoded : (Bindings.parseStrict source).bind decodePair with
  | error code =>
    rw [decoded] at accepted
    contradiction
  | ok candidate =>
    rw [decoded] at accepted
    change ((Bindings.checkDistinctIdentifiers candidate.identifiers "DUPLICATE_RECEIPT_ID").bind
      fun _ => .ok candidate) = .ok pair at accepted
    cases validation : Bindings.checkDistinctIdentifiers candidate.identifiers "DUPLICATE_RECEIPT_ID" with
    | error code => simp [validation, Except.bind] at accepted
    | ok result =>
      cases result
      have same : candidate = pair := by simpa [validation, Except.bind] using accepted
      exact same ▸ (Bindings.checkDistinctIdentifiers_ok_iff _ _).mp validation

/-- Project the admitted amounts onto the generated settlement's Money inputs
without modifying their values or swapping their source order. -/
def ReceiptPair.bindings (pair : ReceiptPair) : Json :=
  let usd := fun amount => Json.mkObj [("currency", .str "USD"), ("value", valueJson (.num amount))]
  Json.mkObj [
    ("inputs", Json.mkObj [
      ("first_receipt", usd pair.first.amount),
      ("second_receipt", usd pair.second.amount)]),
    ("openings", Json.mkObj [])]

private def resultJson : Except String ReceiptPair → Json
  | .ok pair => Json.mkObj [
    ("status", .str "ok"),
    ("receipt_ids", .arr (pair.identifiers.map Json.str).toArray),
    ("bindings", pair.bindings)]
  | .error code => outcomeJson (.error code)

def run (args : List String) : IO Unit := do
  let [path] := args | IO.println (resultJson (.error "RECEIPT_FILE_ARGUMENT_REQUIRED")).compress
  let result ← try
    pure (admit (← IO.FS.readFile path))
    catch _ => pure (.error "RECEIPT_FILE_IO_ERROR")
  IO.println (resultJson result).compress

end SPL.RoyaltiesAdmission

def main (args : List String) : IO Unit := SPL.RoyaltiesAdmission.run args
