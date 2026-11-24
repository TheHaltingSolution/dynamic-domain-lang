import SPL

/-! Experimental CLI transport: retain the exact native interpreter graph, but
serialize one legacy-format node at a time. This avoids constructing the whole
graph JSON array and compressed outcome string. It is not a new trace format,
an interpreter optimization, a trace correctness theorem, or atomic publication.

`SPL.Main` also defines the global executable `main`, so this standalone driver
uses its public component APIs instead of importing that executable module.
-/
namespace SPL.TraceStream
open Lean SPL.Syntax

private def diagnosticJson (diagnostic : Diagnostic) (source : String) : Json :=
  Json.mkObj [
    ("code", .str diagnostic.code), ("message", .str diagnostic.message),
    ("source", .str source),
    ("span", Json.mkObj [
      ("start", toJson diagnostic.span.start), ("end", toJson diagnostic.span.stop),
      ("line", toJson diagnostic.span.line), ("column", toJson diagnostic.span.column)])]

private def report (diagnostic : Diagnostic) (source : String := "") : IO UInt32 := do
  IO.println (Json.mkObj [("status", .str "blocked"),
    ("diagnostics", .arr #[diagnosticJson diagnostic source])]).compress
  return 1

private abbrev Profile := Option (IO.Ref (Std.HashMap String (Nat × Nat)))

-- Keep pure work behind a native IO call, rather than eagerly computing an
-- argument to `pure` before its clock boundary. Check generated C after build.
@[noinline] private def observePure {α : Type} (action : Unit → α) : IO α :=
  return action ()

private def startStage (profile : Profile) : IO Nat :=
  if profile.isSome then IO.monoNanosNow else pure 0

private def stopStage (profile : Profile) (name : String) (start : Nat) : IO Unit := do
  let some counters := profile | return
  let stop ← IO.monoNanosNow
  counters.modify fun values =>
    let (calls, elapsed) := values[name]?.getD (0, 0)
    values.insert name (calls + 1, elapsed + (stop - start))

/-- Inclusive intervals, with no overhead correction. Disabled runs read no clocks. -/
@[noinline] private def timed {α : Type} (profile : Profile) (name : String)
    (action : IO α) : IO α := do
  match profile with
  | none => action
  | some counters =>
    let start ← IO.monoNanosNow
    try action
    finally
      let stop ← IO.monoNanosNow
      counters.modify fun values =>
        let (calls, elapsed) := values[name]?.getD (0, 0)
        values.insert name (calls + 1, elapsed + (stop - start))

private def finishProfile (profile : Profile) (start : Nat) (status : UInt32) : IO Unit := do
  let some counters := profile | return
  let elapsed := (← IO.monoNanosNow) - start
  let intervals := (← counters.get).toList.mergeSort (fun a b => a.1 ≤ b.1)
  -- Diagnostic observation only: no subtraction, and no reference/map updates.
  let probeStart ← IO.monoNanosNow
  let mut pairSpan := 0
  for _ in [:1000] do
    let a ← IO.monoNanosNow
    let b ← IO.monoNanosNow
    pairSpan := pairSpan + (b - a)
  let probeElapsed := (← IO.monoNanosNow) - probeStart
  let stderr ← IO.getStderr
  stderr.putStrLn (Json.mkObj [
    ("format", .str "spl-native-audit-profile/1"),
    ("status", .str (if status == 0 then "completed" else "blocked")),
    ("run_elapsed_ns", toJson elapsed),
    ("clock_pairs", toJson (intervals.foldl (fun n (_, calls, _) => n + calls) 0)),
    ("empty_clock_probe", Json.mkObj [("pairs", toJson (1000 : Nat)),
      ("pair_span_ns", toJson pairSpan), ("elapsed_ns", toJson probeElapsed)]),
    ("intervals", .arr (intervals.map fun (name, calls, ns) => Json.mkObj [
      ("stage", .str name), ("calls", toJson calls), ("elapsed_ns", toJson ns)]).toArray),
    ("scope", .str "monotonic instrumented IO boundaries; transport_total and sharing_and_payload_records are inclusive parents; no overhead subtraction; stdout measures stream/OS pipe acceptance, not durable disk completion")]).compress
  stderr.flush

/-- The same native public frontend boundary as `SPL.CLI.load`. -/
private def load (path : String) (linkPath : Option String) (profile : Profile) : IO (Except Diagnostic Schedule) := do
  let source ← timed profile "frontend_source_read" (IO.FS.readFile path)
  let manifest ← timed profile "frontend_manifest_read" (linkPath.mapM IO.FS.readFile)
  let parsed ← timed profile "frontend_parse" (observePure fun _ =>
    if Readable.isReadable source then Readable.parse source else Parser.parse source)
  let .ok schedule := parsed | return parsed
  let linked ← timed profile "frontend_link" (observePure fun _ => do
    match manifest with
    | none => pure schedule
    | some manifest => do
      let json ← Json.parse manifest |>.mapError (fun message =>
        ({ code := "INVALID_LINK_MANIFEST", message } : Diagnostic))
      Link.link schedule json)
  let .ok schedule := linked | return linked
  let checked ← timed profile "frontend_check" (observePure fun _ => Check.check schedule)
  let .ok _ := checked | return checked.map (fun _ => schedule)
  let elaborated ← timed profile "frontend_elaborate" (observePure fun _ => Elaborate.elaborate schedule)
  let .ok program := elaborated | return elaborated.map (fun _ => schedule)
  let valid ← timed profile "frontend_validate_ir" (observePure fun _ => ValidateIR.validate program)
  return valid.map (fun _ => schedule)

private def interpretFile (schedule : Schedule) (bindingPath : String) (profile : Profile) : IO Interpret.Outcome := do
  let elaborated ← timed profile "interpreter_elaborate" (observePure fun _ => Elaborate.elaborate schedule)
  let program ← match elaborated with
    | .ok program => pure program
    | .error diagnostic => return { result := .error diagnostic.code, trace := {} }
  let inputTypes := schedule.declarations.filterMap fun declaration => match declaration with
    | .input _ name type => some (name, type) | _ => none
  let openingTypes := schedule.declarations.filterMap fun declaration => match declaration with
    | .opening _ name type _ => some (name, type) | _ => none
  let source ← timed profile "binding_read" (IO.FS.readFile bindingPath)
  let decoded : Except String (Env × Env) ← timed profile "binding_parse_decode" (observePure fun _ => do
    let json ← Bindings.parseStrict source
    let fields ← json.getObj? |>.mapError (fun _ => "EXPECTED_BINDING_ENVELOPE")
    let names := fields.toList.map Prod.fst
    unless names.length == 2 && names.contains "inputs" && names.contains "openings" do
      throw "UNKNOWN_OR_MISSING_FIELD"
    let inputs ← Bindings.decodeBindings inputTypes (← json.getObjVal? "inputs")
    let openings ← Bindings.decodeBindings openingTypes (← json.getObjVal? "openings")
    pure (inputs, openings))
  match decoded with
  | .error code => return { result := .error code, trace := {} }
  | .ok (inputs, openings) => timed profile "interpreter_graph" (observePure fun _ => Interpret.interpret program inputs openings)

/-- Use the existing outcome formatter for every head field, with an empty graph
to avoid eager trace materialization. Every real ordered node uses Trace.nodeJson.
No business output or trace node is omitted, interned, or reinterpreted. -/
private def writeOutcome (outcome : Interpret.Outcome) (profile : Profile) : IO Unit := do
  match ← timed profile "graph_validate" (observePure fun _ => outcome.trace.validate) with
  | .error code => throw (IO.userError code)
  | .ok _ => pure ()
  let .obj head ← timed profile "outcome_head_json" (observePure fun _ => Interpret.outcomeJson { outcome with trace := {} })
    | throw (IO.userError "INVALID_OUTCOME_JSON")
  let stdout ← IO.getStdout
  timed profile "stdout_write" (stdout.putStr "{")
  for (key, value) in head.toList do
    unless key == "trace" do
      let encoded ← timed profile "record_format" (observePure fun _ => (Json.str key).compress ++ ":" ++ value.compress ++ ",")
      timed profile "stdout_write" (stdout.putStr encoded)
  timed profile "stdout_write" (stdout.putStr "\"trace\":[")
  let mut first := true
  let ordered ← timed profile "graph_order" (observePure fun _ => outcome.trace.ordered)
  for node in ordered do
    if first then first := false else timed profile "stdout_write" (stdout.putStr ",")
    let json ← timed profile "node_json" (observePure fun _ => Trace.nodeJson node)
    let encoded ← timed profile "record_format" (observePure fun _ => json.compress)
    timed profile "stdout_write" (stdout.putStr encoded)
  timed profile "stdout_write" (stdout.putStr "]}\n")
  timed profile "stdout_flush" stdout.flush

private def writeRecord (stdout : IO.FS.Stream) (record : Json) (profile : Profile) : IO Unit := do
  let encoded ← timed profile "record_format" (observePure fun _ => record.compress)
  if encoded.utf8ByteSize > 8 * 1024 * 1024 then
    throw (IO.userError "COMPACT_RECORD_BYTE_LIMIT")
  timed profile "stdout_write" (stdout.putStr (encoded ++ "\n"))

private def sharedField (name : String) : Bool :=
  ["operands", "result", "fact_ids", "value_type", "source_span", "detail",
    "scope", "instance_scope", "lineage"].contains name

/-- Opt-in lossless JSONL transport. Exact serialized payload keys, rather than
hashes, decide interning; payload IDs are consecutive first-use identities.
The full expanded graph is never converted to a JSON array here. -/
private def writeCompactOutcome (outcome : Interpret.Outcome) (indexed : Bool) (profile : Profile) : IO Unit := do
  match ← timed profile "graph_validate" (observePure fun _ => outcome.trace.validate) with
  | .error code => throw (IO.userError code)
  | .ok _ => pure ()
  let .obj head ← timed profile "outcome_head_json" (observePure fun _ => Interpret.outcomeJson { outcome with trace := {} })
    | throw (IO.userError "INVALID_OUTCOME_JSON")
  let stdout ← IO.getStdout
  writeRecord stdout (Json.mkObj [("record", .str "header"),
    ("format", .str (if indexed then "spl-native-trace-stream/0.2" else "spl-native-trace-stream/0.1")),
    ("logical_format", .str "spl-trace-dag/0.1"),
    ("head", Json.mkObj (head.toList.filter fun (key, _) => key != "trace"))]) profile
  let mut payloads : Std.HashMap String Nat := {}
  let mut payloadBytes := 0
  let mut payloadCount := 0
  let mut nodeCount := 0
  let mut expandedBytes := 2
  let mut nodeIndices : Std.HashMap String Nat := {}
  let ordered ← timed profile "graph_order" (observePure fun _ => outcome.trace.ordered)
  for node in ordered do
    if nodeCount >= 100000 then throw (IO.userError "COMPACT_NODE_LIMIT")
    let json ← timed profile "node_json" (observePure fun _ => Trace.nodeJson node)
    let .obj fields := json | throw (IO.userError "INVALID_TRACE_NODE_JSON")
    -- Encode each field once. Exact object syntax is two braces, one colon per
    -- field and one comma between fields; quoted keys use the same JSON printer.
    -- This avoids compressing the entire expanded node and then its fields again.
    let (encodedFields, objectBytes) ← timed profile "field_encoding_accounting" (observePure fun _ => Id.run do
      let encodedFields := fields.toList.map fun (field, value) => (field, value, value.compress)
      let objectBytes := encodedFields.foldl (fun size (field, _, encoded) =>
        size + (Json.str field).compress.utf8ByteSize + 1 + encoded.utf8ByteSize) 2
        + (encodedFields.length - 1)
      return (encodedFields, objectBytes))
    expandedBytes := expandedBytes + (if nodeCount == 0 then 0 else 1) + objectBytes
    if expandedBytes > 1024 * 1024 * 1024 then
      throw (IO.userError "COMPACT_EXPANDED_BYTE_LIMIT")
    let dependencyStart ← startStage profile
    let dependencyIndices ← if indexed then do
      let mut indices : List Nat := []
      for dependency in node.dependencies do
        let some index := nodeIndices[dependency]?
          | throw (IO.userError "COMPACT_FORWARD_DEPENDENCY")
        indices := index :: indices
      pure indices.reverse
      else pure []
    stopStage profile "dependency_indices" dependencyStart
    let sharingStart ← startStage profile
    let mut inlineFields := []
    let mut sharedFields := []
    for (field, value, encoded) in encodedFields do
      if indexed && field == "dependencies" then continue
      if sharedField field && encoded.utf8ByteSize >= (if indexed then 32 else 256) then
        let reference ← match payloads[encoded]? with
          | some index => pure ("p" ++ toString index)
          | none => do
            if payloadCount >= 100000 then throw (IO.userError "COMPACT_PAYLOAD_LIMIT")
            if payloadBytes + encoded.utf8ByteSize > 32 * 1024 * 1024 then
              throw (IO.userError "COMPACT_PAYLOAD_BYTE_LIMIT")
            let reference := "p" ++ toString payloadCount
            writeRecord stdout (Json.mkObj [("record", .str "payload"),
              ("id", .str reference), ("value", value)]) profile
            payloads := payloads.insert encoded payloadCount
            payloadCount := payloadCount + 1
            payloadBytes := payloadBytes + encoded.utf8ByteSize
            pure reference
        sharedFields := (field, Json.str reference) :: sharedFields
      else
        inlineFields := (field, value) :: inlineFields
    stopStage profile "sharing_and_payload_records" sharingStart
    writeRecord stdout (Json.mkObj ([("record", .str "node"),
      ("inline", Json.mkObj inlineFields), ("shared", Json.mkObj sharedFields)] ++
      (if indexed then [("dependencies", toJson dependencyIndices)] else []))) profile
    let indexStart ← startStage profile
    if indexed then nodeIndices := nodeIndices.insert node.id nodeCount
    nodeCount := nodeCount + 1
    stopStage profile "index_update" indexStart
  writeRecord stdout (Json.mkObj [("record", .str "complete"),
    ("node_count", toJson nodeCount), ("payload_count", toJson payloadCount),
    ("expanded_bytes", toJson expandedBytes)]) profile
  timed profile "stdout_flush" stdout.flush

def run (args : List String) : IO UInt32 := do
  let profiling := args.contains "--profile-stages"
  if (args.filter (· == "--profile-stages")).length > 1 then
    return ← report { code := "USAGE", message := "Only one --profile-stages flag is permitted" }
  let args := args.filter (· != "--profile-stages")
  let profile ← if profiling then do
    let counters ← IO.mkRef ({} : Std.HashMap String (Nat × Nat))
    pure (some counters)
    else pure none
  let started ← startStage profile
  let compact := args.contains "--compact"
  let compactV2 := args.contains "--compact-v2"
  if (args.filter (· == "--compact")).length > 1 then
    return ← report { code := "USAGE", message := "Only one --compact flag is permitted" }
  if (args.filter (· == "--compact-v2")).length > 1 || (compact && compactV2) then
    return ← report { code := "USAGE", message := "Select exactly one compact transport version" }
  let args := args.filter (fun arg => arg != "--compact" && arg != "--compact-v2")
  let (args, linkPath) := match args.reverse with
    | manifest :: "--link" :: rest => (rest.reverse, some manifest)
    | _ => (args, none)
  let [source, bindings] := args | report { code := "USAGE", message :=
    "Usage: spl_trace_stream SOURCE.spl BINDINGS.json [--compact | --compact-v2] [--profile-stages] [--link MANIFEST.json]" }
  let status ← do
    match ← load source linkPath profile with
    | .error diagnostic => report diagnostic source
    | .ok schedule =>
      let outcome ← interpretFile schedule bindings profile
      timed profile "transport_total" do
        if compact || compactV2 then writeCompactOutcome outcome compactV2 profile
        else writeOutcome outcome profile
      pure 0
  finishProfile profile started status
  return status

end SPL.TraceStream

def main (args : List String) : IO UInt32 := do
  try SPL.TraceStream.run args
  catch error =>
    IO.println (Lean.Json.mkObj [("status", .str "blocked"),
      ("diagnostics", .arr #[Lean.Json.mkObj [("code", .str "IO_ERROR"),
        ("message", .str error.toString), ("source", .str ""),
        ("span", Lean.Json.mkObj [("start", .num 0), ("end", .num 0),
          ("line", .num 1), ("column", .num 1)])]])]).compress
    return 1
