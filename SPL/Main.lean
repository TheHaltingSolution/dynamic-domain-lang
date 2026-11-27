import Lean
import SPL.Parser
import SPL.Check
import SPL.Emit
import SPL.Readable
import SPL.Elaborate
import SPL.ValidateIR
import SPL.Interpret
import SPL.Bindings
import SPL.Link

/-! Authoritative native frontend CLI. The Python frontend is an independent
development oracle, and is not invoked by this executable. -/
namespace SPL.CLI
open SPL.Syntax

def diagnosticJson (diagnostic : Diagnostic) (source : String) (stage : String := "") : Lean.Json :=
  Lean.Json.mkObj ([
    ("code", .str diagnostic.code), ("message", .str diagnostic.message),
    ("source", .str source),
    ("span", Lean.Json.mkObj [
      ("start", Lean.toJson diagnostic.span.start), ("end", Lean.toJson diagnostic.span.stop),
      ("line", Lean.toJson diagnostic.span.line), ("column", Lean.toJson diagnostic.span.column)])] ++
    (if stage.isEmpty then [] else [("stage", .str stage)]))

def report (diagnostic : Diagnostic) (source : String := "") (stage : String := "") : IO UInt32 := do
  IO.println (Lean.Json.compress (Lean.Json.mkObj [
    ("status", .str "blocked"),
    ("diagnostics", .arr #[diagnosticJson diagnostic source stage])]))
  return 1

structure FrontendFailure where
  diagnostic : Diagnostic
  source : String
  stage : String

private def failure (stage source : String) (diagnostic : Diagnostic) : FrontendFailure :=
  let stage := if diagnostic.code == "RESOURCE_LIMIT" then "resource"
    else if diagnostic.code.startsWith "UNSUPPORTED_" ||
      (stage == "type" && ["CONVERSION_LITERAL_REQUIRED", "CONVERSION_ENDPOINT_MISMATCH",
        "FEATURE_REQUIRED", "UNRESOLVED_EVENT_ORDER"].contains diagnostic.code) then "unsupported"
    else stage
  { stage, source, diagnostic }

private abbrev Frontend := ExceptT FrontendFailure IO

private def checkedPhase (stage source : String) (result : Except Diagnostic α) : Except FrontendFailure α :=
  result.mapError (failure stage source)

private def readPhase (stage source : String) : Frontend String :=
  ExceptT.mk (try
    return .ok (← IO.FS.readFile source)
  catch error => return .error (failure stage source { code := "IO_ERROR", message := error.toString }))

private def checkSource (path source : String) (link : Option (String × String)) : Except FrontendFailure Schedule := do
  let parsed := if SPL.Readable.isReadable source then SPL.Readable.parse source else SPL.Parser.parse source
  let mut schedule ← checkedPhase "source" path parsed
  if let some (linkPath, manifest) := link then
    let json ← checkedPhase "link" linkPath (Lean.Json.parse manifest |>.mapError fun message =>
      { code := "INVALID_LINK_MANIFEST", message })
    schedule ← checkedPhase "link" linkPath (SPL.Link.link schedule json)
  checkedPhase "type" path (SPL.Check.check schedule)
  let program ← checkedPhase "ir" path (SPL.Elaborate.elaborate schedule)
  checkedPhase "ir" path (SPL.ValidateIR.validate program)
  return schedule

def loadStaged (path : String) (linkPath : Option String := none) : IO (Except FrontendFailure Schedule) :=
  (do
    let source ← readPhase "source" path
    let link ← linkPath.mapM fun manifest => do pure (manifest, ← readPhase "link" manifest)
    liftExcept (checkSource path source link) : Frontend Schedule).run

/-- Keep the interpreter's load and I/O diagnostics in the trace wire format. -/
def load (path : String) (linkPath : Option String := none) : IO (Except Diagnostic Schedule) := do
  let source ← IO.FS.readFile path
  let link ← linkPath.mapM fun (manifest : String) => do pure (manifest, ← IO.FS.readFile manifest)
  return (checkSource path source link).mapError (·.diagnostic)

private def reportFailure (error : FrontendFailure) : IO UInt32 :=
  report error.diagnostic error.source error.stage

private def reportPhase (stage source : String) (diagnostic : Diagnostic) : IO UInt32 :=
  reportFailure (failure stage source diagnostic)

def writeArtifact (destination content : String) : IO Unit := do
  let path : System.FilePath := destination
  if let some parent := path.parent then IO.FS.createDirAll parent
  IO.FS.writeFile path content

def interpretFile (schedule : Schedule) (bindingPath : String) : IO Lean.Json := do
  let program ← match SPL.Elaborate.elaborate schedule with
    | .ok program => pure program
    | .error diagnostic => return SPL.outcomeJson (.error diagnostic.code)
  let inputTypes := schedule.declarations.filterMap fun declaration => match declaration with
    | .input _ name type => some (name, type) | _ => none
  let openingTypes := schedule.declarations.filterMap fun declaration => match declaration with
    | .opening _ name type _ => some (name, type) | _ => none
  let source ← IO.FS.readFile bindingPath
  let decoded : Except String (SPL.Env × SPL.Env) := do
    let owner ← SPL.Dimensions.prepare schedule.features
    let meanings : SPL.Dimensions.Meanings := { features := (program.features ++ program.owners.flatMap Prod.snd).eraseDups }
    let json ← SPL.Bindings.parseStrict source
    let fields ← json.getObj? |>.mapError (fun _ => "EXPECTED_BINDING_ENVELOPE")
    let names := fields.toList.map Prod.fst
    unless names.length == 2 && names.contains "inputs" && names.contains "openings" do
      throw "UNKNOWN_OR_MISSING_FIELD"
    let inputs ← SPL.Bindings.decodeBindingsWith owner meanings inputTypes (← json.getObjVal? "inputs")
    let openings ← SPL.Bindings.decodeBindingsWith owner meanings openingTypes (← json.getObjVal? "openings")
    pure (inputs, openings)
  match decoded with
  | .error code => return SPL.Interpret.outcomeJson { result := .error code, trace := {} }
  | .ok (inputs, openings) => return SPL.Interpret.outcomeJson (SPL.Interpret.interpret program inputs openings)

def runCore (args : List String) (linkPath : Option String) : IO UInt32 := do
  match args with
  | ["check", source] =>
    match ← loadStaged source linkPath with
    | .error error => reportFailure error
    | .ok schedule =>
      IO.println (Lean.Json.compress (Lean.Json.mkObj [
        ("status", .str "checked"), ("schedule", .str schedule.name),
        ("declarations", Lean.toJson schedule.declarations.length)]))
      return 0
  | ["compile", source, destination] =>
    match ← loadStaged source linkPath with
    | .error error => reportFailure error
    | .ok schedule =>
      match SPL.Emit.emit schedule with
      | .error diagnostic => reportPhase "emit" source diagnostic
      | .ok generated =>
        let path : System.FilePath := destination
        if let some parent := path.parent then IO.FS.createDirAll parent
        IO.FS.writeFile path generated
        IO.println (Lean.Json.compress (Lean.Json.mkObj [
          ("status", .str "compiled"), ("schedule", .str schedule.name),
          ("output", .str destination)]))
        return 0
  | ["compile-library", source, destination] =>
    match ← loadStaged source linkPath with
    | .error error => reportFailure error
    | .ok schedule =>
      let generated := do SPL.Emit.emitLibraryIR (← SPL.Elaborate.elaborate schedule)
      match generated with
      | .error diagnostic => reportPhase "emit" source diagnostic
      | .ok generated =>
        writeArtifact destination generated
        IO.println (Lean.Json.mkObj [("status", .str "compiled_library"), ("output", .str destination)]).compress
        return 0
  | ["compile-series", source, destination] =>
    match ← loadStaged source linkPath with
    | .error error => reportFailure error
    | .ok schedule =>
      let generated := do SPL.Emit.emitSeriesIR (← SPL.Elaborate.elaborate schedule)
      match generated with
      | .error diagnostic => reportPhase "emit" source diagnostic
      | .ok generated =>
        writeArtifact destination generated
        IO.println (Lean.Json.mkObj [("status", .str "compiled_series"), ("output", .str destination)]).compress
        return 0
  | ["ir", source] | ["ir", source, _] =>
    match ← loadStaged source linkPath with
    | .error error => reportFailure error
    | .ok schedule =>
      match SPL.Elaborate.elaborate schedule with
      | .error diagnostic => reportPhase "ir" source diagnostic
      | .ok program =>
        let artifact := program.toJson
        match SPL.IRArtifact.validate artifact with
        | .error code => return ← reportPhase "ir" source { code, message := "IR artifact preflight" }
        | .ok _ => pure ()
        let json := artifact.compress
        if let [_, _, destination] := args then writeArtifact destination json
        else IO.println json
        return 0
  | ["interpret", source, bindings] =>
    match ← load source linkPath with
    | .error diagnostic => report diagnostic source
    | .ok schedule =>
      IO.println (← interpretFile schedule bindings).compress
      return 0
  | ["expand", source, destination] =>
    let authored ← match ← (readPhase "source" source).run with
      | .error error => return ← reportFailure error
      | .ok text => pure text
    match SPL.Readable.expand authored with
    | .error diagnostic => reportPhase "source" source diagnostic
    | .ok expanded =>
      writeArtifact destination expanded.source
      let sourceMap := Lean.Json.mkObj [("format", .str "spl-readable-map/0.1"),
        ("source", .str source), ("generated", .str destination),
        ("origins", .arr (expanded.origins.map SPL.IR.spanJson))]
      writeArtifact (destination ++ ".map.json") sourceMap.compress
      IO.println (Lean.Json.mkObj [("status", .str "expanded"), ("output", .str destination)]).compress
      return 0
  | _ => report { code := "USAGE", message :=
      "Usage: spl check SOURCE.spl | spl compile SOURCE.spl OUTPUT.lean | spl compile-library SOURCE.spl OUTPUT.lean | spl compile-series SOURCE.spl OUTPUT.lean | spl ir SOURCE.spl [OUTPUT.json] | spl interpret SOURCE.spl BINDINGS.json | spl expand READABLE.spl OUTPUT.spl (source commands accept --link MANIFEST.json)" }

def run (args : List String) : IO UInt32 :=
  match args.reverse with
  | manifest :: "--link" :: rest => runCore rest.reverse (some manifest)
  | _ => runCore args none

end SPL.CLI

def main (args : List String) : IO UInt32 := do
  try SPL.CLI.run args
  catch error => SPL.CLI.report { code := "IO_ERROR", message := error.toString }
