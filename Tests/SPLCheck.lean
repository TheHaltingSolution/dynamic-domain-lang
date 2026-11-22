import SPL.Check
import SPL.Parser

namespace SPL.CheckTests

def headerText := "schedule CheckTest language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { "

def checked (body : String) : Except SPL.Syntax.Diagnostic Unit := do
  SPL.Check.check (← SPL.Parser.parse (headerText ++ body ++ " }"))

def expectCode (body expected : String) : IO Unit := do
  match checked body with
  | .ok _ => throw (IO.userError ("Expected failure " ++ expected))
  | .error d => unless d.code == expected do
      throw (IO.userError ("Expected " ++ expected ++ ", got " ++ d.code ++ ": " ++ d.message))

def main : IO Unit := do
  for path in ["cases/sv/sv01.spl", "cases/sv/rq07.spl", "cases/lg/lg01.spl"] do
    let source ← IO.FS.readFile path
    match SPL.Parser.parse source >>= SPL.Check.check with
    | .ok _ => pure ()
    | .error d => throw (IO.userError (path ++ ": " ++ d.code ++ " " ++ d.message))
  expectCode "define x = USD 1 * USD 2;" "TYPE_MISMATCH"
  expectCode "define x = y; define y = x;" "UNRESOLVED_NAME_OR_CYCLE"
  expectCode "define x = 1; define x = 2;" "DUPLICATE_NAME"
  expectCode "define x = invented(1);" "UNSUPPORTED_BUILTIN"
  expectCode "define x = choose unique { when true => 0.1; when true => 0.2; };" "AMBIGUOUS_RULE"
  expectCode "opening x: Money<USD> from \"alias\";" "MISSING_CLOSING_PORT"
  expectCode "define x = date \"2026-02-29\";" "INVALID_DATE"
  expectCode "input xs: List<SVPicture>; define ys = for each p in xs { define later = 1; yield p; }; define later = 2;" "DUPLICATE_NAME"
  match checked "define x = later + 0.1; define later = 0.2; emit \"x\" = x;" with
  | .ok _ => pure ()
  | .error d => throw (IO.userError ("Forward reference rejected: " ++ d.code))
  IO.println "SPL native checker tests passed (SV/LG, units, names, cycles, ports, dates)."

end SPL.CheckTests

def main : IO Unit := SPL.CheckTests.main
