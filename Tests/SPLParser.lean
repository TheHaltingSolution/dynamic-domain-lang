import SPL.Parser
import SPL.Check

/-! Native frontend regression checks. Expected syntax decisions are authored
independently of the parser; monetary expectations belong to settlement tests. -/
open SPL.Syntax

private def wrap (body : String) : String :=
  "schedule Test language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { " ++ body ++ " }"

private def expectError (source code : String) : IO Unit :=
  match SPL.Parser.parse source with
  | .ok _ => throw (IO.userError s!"Parser accepted invalid source; expected {code}")
  | .error diagnostic =>
    unless diagnostic.code == code do
      throw (IO.userError s!"Expected {code}, got {diagnostic.code}: {diagnostic.message}")

private def expectSuccess (source : String) : IO Schedule :=
  match SPL.Parser.parse source with
  | .ok schedule => pure schedule
  | .error diagnostic => throw (IO.userError s!"Parser failed: {repr diagnostic}")

private def expectChecked (source : String) : IO Unit := do
  let schedule ← expectSuccess source
  match SPL.Check.check schedule with
  | .ok _ => pure ()
  | .error diagnostic => throw (IO.userError s!"Static checking failed: {repr diagnostic}")

private def expectCheckError (body code : String) : IO Unit := do
  let schedule ← expectSuccess (wrap body)
  match SPL.Check.check schedule with
  | .ok _ => throw (IO.userError s!"Checker accepted invalid source; expected {code}")
  | .error diagnostic =>
    unless diagnostic.code == code do
      throw (IO.userError s!"Expected static {code}, got {diagnostic.code}: {diagnostic.message}")

def main : IO Unit := do
  for (path, name, count) in [
      ("cases/sv/sv01.spl", "SkourasVenturaPilot", 14),
      ("cases/sv/rq07.spl", "SkourasVenturaPostingPilot", 14),
      ("cases/lg/lg01.spl", "LionsgateDerivativePilot", 46)] do
    let schedule ← expectSuccess (← IO.FS.readFile path)
    unless schedule.name == name && schedule.declarations.length == count do
      throw (IO.userError s!"Incorrect parsed fixture {path}")
    expectChecked (← IO.FS.readFile path)
  let schedule ← expectSuccess (wrap "define x = USD 0.0500 + USD 0.01 * 0.10;")
  match schedule.declarations with
  | [.define _ "x" none (.binary _ "+" (.money _ "USD" "0.0500")
      (.binary _ "*" (.money _ "USD" "0.01") (.number _ "0.10"))) none] => pure ()
  | _ => throw (IO.userError "Exact numeric spelling or precedence changed")
  let _ ← expectSuccess (wrap "define x = 2 * (if true then 1 else 0);")
  let _ ← expectSuccess (wrap "define f = filter([1, 2], x => x > 0);")
  let _ ← expectSuccess (wrap "define x = choose unique { when false => 1; otherwise => 2; };")
  let _ ← expectSuccess (wrap "emit \"text\" = \"slash // quote \\\" and \\u03b1\";")
  let _ ← expectSuccess (wrap "emit \"text\" = \"\\uD83D\\uDE00\";")
  for (body, code) in [
      ("define x = 2 * if true then 1 else 0;", "SYNTAX_ERROR"),
      ("emit \"r\" = {value: 1, value: 2};", "DUPLICATE_FIELD"),
      ("while true { };", "UNSUPPORTED_DECLARATION"),
      ("define f = x => x + 1;", "SYNTAX_ERROR"),
      ("define x = record.function(1);", "UNSUPPORTED_CALL"),
      ("define x = 1e6;", "SYNTAX_ERROR"),
      ("define x = 1,000;", "SYNTAX_ERROR"),
      ("define x = 1.;", "SYNTAX_ERROR"),
      ("define x = .5;", "SYNTAX_ERROR"),
      ("define x = +1;", "SYNTAX_ERROR"),
      ("emit \"test\" = \"bad\\x20\";", "INVALID_STRING"),
      ("emit \"test\" = \"line\nbreak\";", "INVALID_STRING"),
      ("emit \"test\" = \"\\uD800\";", "INVALID_STRING"),
      ("emit \"test\" = \"\\uDC00\";", "INVALID_STRING"),
      ("define x = choose unique { otherwise => 1; };", "SYNTAX_ERROR"),
      ("define x = choose priority { when true => 1; };", "SYNTAX_ERROR"),
      ("define x = 0 < 1 < 2;", "SYNTAX_ERROR"),
      ("define x = 0 == 1 == 2;", "SYNTAX_ERROR"),
      ("define x = 1", "SYNTAX_ERROR")] do
    expectError (wrap body) code
  expectError (wrap "define x = 1;" ++ " injected") "TRAILING_CONTENT"
  expectError (wrap "emit \"test\" = \"unterminated") "INVALID_STRING"
  let nested := String.ofList (List.replicate 130 '(') ++ "1" ++ String.ofList (List.replicate 130 ')')
  expectError (wrap ("define x = " ++ nested ++ ";")) "RESOURCE_LIMIT"
  expectChecked (wrap "define a = b + 1; define b = 2; emit \"value\" = a;")
  expectChecked (wrap "define date_value = date \"2024-02-29\";")
  for (body, code) in [
      ("define x = USD 1 * USD 2;", "TYPE_MISMATCH"),
      ("define x = USD 1 + 2;", "TYPE_MISMATCH"),
      ("define x = true and 1;", "TYPE_MISMATCH"),
      ("define x = date \"2026-02-29\";", "INVALID_DATE"),
      ("define x = mystery(1);", "UNSUPPORTED_BUILTIN"),
      ("define x = 1; define x = 2;", "DUPLICATE_NAME"),
      ("define x = missing + 1;", "UNRESOLVED_NAME_OR_CYCLE"),
      ("define x = y + 1; define y = x + 1;", "UNRESOLVED_NAME_OR_CYCLE"),
      ("define x = [];", "AMBIGUOUS_EMPTY_LIST"),
      ("define x = choose unique { when true => 1; when true => 2; };", "AMBIGUOUS_RULE"),
      ("input x: Money<EUR>;", "UNSUPPORTED_CURRENCY"),
      ("input x: UnknownType;", "UNSUPPORTED_TYPE"),
      ("input x: Period; define y = x.missing;", "UNKNOWN_FIELD"),
      ("opening x: Money<USD> from \"pool\";", "MISSING_CLOSING_PORT"),
      ("closing x = USD 0;", "INVALID_CLOSING_PORT"),
      ("opening x: Money<USD> from \"pool\"; closing x = 1;", "TYPE_MISMATCH"),
      ("emit \"x\" = 1; emit \"x\" = 2;", "DUPLICATE_OUTPUT"),
      ("emit \"pool\" = {payable: USD 1};", "UNRESOLVED_OUTPUT_SCOPE"),
      ("define x = 1; define ys = for each y in [2] { define x = 3; yield x; };", "DUPLICATE_NAME"),
      ("define x = quantize(USD 1, USD 0.01, \"unknown\");", "UNSUPPORTED_ROUNDING_MODE")] do
    expectCheckError body code
  IO.println "Native SPL parser/checker checks passed (SV, RQ-07, LG, exact tokens, grammar, types, scopes, cycles, limits)."
