import SPL.Parser
import SPL.Check
import SPL.Emit

/-! Native parser/checker/emitter integration. Emitted files are disposable build
artifacts. Both source schedules are parsed at runtime, never fixture outputs. -/
open SPL.Syntax

private def emitChecked (source : String) : Except Diagnostic String := do
  let parsed ← SPL.Parser.parse source
  SPL.Check.check parsed
  SPL.Emit.emit parsed

def main : IO Unit := do
  IO.FS.createDirAll ".lake/spl"
  for (sourcePath, outputPath) in [
      ("cases/sv/sv01.spl", ".lake/spl/NativeSV.lean"),
      ("cases/sv/rq07.spl", ".lake/spl/NativeRQ07.lean"),
      ("cases/lg/lg01.spl", ".lake/spl/NativeLG.lean")] do
    let source ← IO.FS.readFile sourcePath
    let generated ← match emitChecked source with
      | .ok generated => pure generated
      | .error diagnostic => throw (IO.userError s!"Native emission failed: {repr diagnostic}")
    IO.FS.writeFile outputPath generated
    -- Inherit the caller's pinned `lake env`/LEAN_PATH rather than discover or
    -- download a different toolchain inside a compiler verification check.
    let result ← IO.Process.output { cmd := "lean", args := #[outputPath] }
    unless result.exitCode == 0 do
      throw (IO.userError s!"Generated Lean did not compile for {sourcePath}:\n{result.stdout}\n{result.stderr}")
  -- Library mode must permit two schedules in one environment, including names
  -- that collide under the tempting punctuation-to-underscore encoding.
  let header := "schedule Hygiene language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { "
  let mut namespaces := []
  let root ← IO.currentDir
  for (moduleName, scheduleName, amount) in [("SPLHygieneA", "a-b", "2"), ("SPLHygieneB", "a_b", "3")] do
    let program ← match SPL.Parser.parse (header ++ "emit \"value\" = " ++ amount ++ "; }") >>= SPL.Elaborate.elaborate with
      | .ok p => pure { p with name := scheduleName }
      | .error d => throw (IO.userError s!"Library setup failed: {repr d}")
    let generated ← match SPL.Emit.emitLibraryIR program with
      | .ok generated => pure generated
      | .error d => throw (IO.userError s!"Library emission failed: {repr d}")
    namespaces := namespaces ++ [SPL.Emit.scheduleNamespace program.name]
    IO.FS.writeFile (".lake/spl/" ++ moduleName ++ ".lean") generated
    let output := root / ".lake" / "build" / "lib" / "lean" / (moduleName ++ ".olean")
    let result ← IO.Process.output {
      cmd := "lean"
      cwd := some (root / ".lake" / "spl")
      args := #["-o", output.toString, moduleName ++ ".lean"] }
    unless result.exitCode == 0 do
      throw (IO.userError s!"Library module failed: {result.stdout}\n{result.stderr}")
  unless namespaces.length == namespaces.eraseDups.length do
    throw (IO.userError "Distinct schedule names produced identical generated namespaces")
  let combined := "import SPLHygieneA\nimport SPLHygieneB\n\n" ++
    "private def verify (result : SPL.Eval SPL.Settlement) (expected : Rat) : IO Unit := do\n" ++
    "  let .ok settlement := result | throw (IO.userError \"settlement failed\")\n" ++
    "  let .ok (.num amount) := SPL.lookup settlement.emissions \"value\" | throw (IO.userError \"missing amount\")\n" ++
    "  unless amount == expected do throw (IO.userError \"unexpected amount\")\n\n" ++
    "def main : IO Unit := do\n  verify (" ++ namespaces[0]! ++ ".settle [] []) 2\n" ++
    "  verify (" ++ namespaces[1]! ++ ".settle [] []) 3\n"
  IO.FS.writeFile ".lake/spl/CombinedLibraries.lean" combined
  let result ← IO.Process.output { cmd := "lean", args := #["--run", ".lake/spl/CombinedLibraries.lean"] }
  unless result.exitCode == 0 do
    throw (IO.userError s!"Two imported generated libraries failed: {result.stdout}\n{result.stderr}")
  IO.println "Native SPL parser/checker/emitter integration passed (SV, RQ-07, LG generated modules compiled)."
