import SPL.Bindings

open SPL

private def expectFailure (label code : String) (result : Except String α) : IO Unit := do
  match result with
  | .error actual => unless actual == code do
      throw (IO.userError s!"{label}: expected {code}, got {actual}")
  | .ok _ => throw (IO.userError s!"{label}: expected rejection")

private def json (source : String) : IO Lean.Json :=
  match Bindings.parseStrict source with
  | .ok value => pure value
  | .error code => throw (IO.userError s!"test JSON failed: {code}")

private def checkAdvanceDisbursementAdmission : IO Unit := do
  let fixture ← json (← IO.FS.readFile "cases/mechanisms/advance-issues-bindings.json")
  let first ← match ((fixture.getObjValD "inputs").getObjValD "issues").getArrVal? 0 with
    | .ok row => pure row
    | .error code => throw (IO.userError code)
  let second := first.setObjVal! "event_id" (.str "issue-2") |>.setObjVal! "issue_id" (.str "advance-2")
  let distinct := second.setObjVal! "disbursement_id" (.str "disbursement-2")
  let third := first.setObjVal! "event_id" (.str "issue-3") |>.setObjVal! "issue_id" (.str "advance-3")
  let listType : SPL.Syntax.TypeExpr := .named "List" [.named "AdvanceIssue" []]
  let decode rows := Bindings.decodeBindings [("issues", listType)] (.mkObj [("issues", .arr rows)])
  match decode #[first, distinct] with
  | .ok [("issues", .seq [_, _])] => pure ()
  | _ => throw (IO.userError "Distinct disbursement identities did not reach typed bindings")
  expectFailure "nonadjacent original disbursement reuse" "DUPLICATE_DISBURSEMENT_ID"
    (decode #[first, distinct, third])

def main : IO Unit := do
  expectFailure "duplicate keys" "DUPLICATE_JSON_KEY"
    (Bindings.parseStrict "{\"x\":\"1\",\"x\":\"2\"}")
  expectFailure "escaped duplicate keys" "DUPLICATE_JSON_KEY"
    (Bindings.parseStrict "{\"x\":true,\"\\u0078\":false}")
  expectFailure "lone high surrogate" "INVALID_UNICODE_ESCAPE"
    (Bindings.parseStrict "{\"x\":\"\\ud800\"}")
  expectFailure "lone low surrogate" "INVALID_UNICODE_ESCAPE"
    (Bindings.parseStrict "{\"x\":\"\\udc00\"}")
  expectFailure "numeric JSON" "JSON_NUMBER_NOT_ALLOWED" (Bindings.parseStrict "{\"x\":1.2}")
  expectFailure "null" "NULL_NOT_ALLOWED" (Bindings.parseStrict "{\"x\":null}")
  expectFailure "BOM" "INVALID_UTF8" (Bindings.parseStrict "\ufeff{}")
  expectFailure "trailing bytes" "INVALID_JSON" (Bindings.parseStrict "{} x")
  let surrogate ← json "{\"x\":\"\\ud83c\\udfac\"}"
  match surrogate.getObjVal? "x" >>= Lean.Json.getStr? with
  | .ok "🎬" => pure ()
  | _ => throw (IO.userError "paired surrogate changed")
  expectFailure "zero denominator" "INVALID_RATIONAL"
    (Bindings.exact (← json "{\"numerator\":\"1\",\"denominator\":\"0\"}"))
  expectFailure "unreduced ratio" "NONCANONICAL_RATIONAL"
    (Bindings.exact (← json "{\"numerator\":\"2\",\"denominator\":\"4\"}"))
  expectFailure "negative rational zero" "INVALID_RATIONAL"
    (Bindings.exact (← json "{\"numerator\":\"-0\",\"denominator\":\"1\"}"))
  expectFailure "exponent string" "INVALID_EXACT_NUMBER" (Bindings.exact (.str "1e3"))
  expectFailure "invalid leap date" "INVALID_DATE" (Bindings.decode Check.dateTy (.str "2025-02-29"))
  expectFailure "Unicode ID unsupported" "UNSUPPORTED_IDENTIFIER_PROFILE" (Bindings.decode (Check.idTy "Asset") (.str "é"))
  expectFailure "currency mismatch" "UNSUPPORTED_CURRENCY"
    (Bindings.decode Check.usdTy (← json "{\"value\":\"1\",\"currency\":\"EUR\"}"))
  expectFailure "inverted period" "INVALID_PERIOD"
    (Bindings.decode Check.periodTy (← json "{\"start\":\"2026-04-01\",\"end\":\"2026-01-01\"}"))
  let exact ← match Bindings.exact (.str "-1.005") with
    | .ok value => pure value
    | .error code => throw (IO.userError code)
  unless exact == mkRat (-201) 200 do throw (IO.userError "decimal was not exact")
  checkAdvanceDisbursementAdmission
  IO.println "Native SPL strict binding transport checks passed."
