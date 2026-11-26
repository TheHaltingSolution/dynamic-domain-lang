import Lean.Data.Json.FromToJson
import Demos.SVBenchmarkLibrary

/-! Bounded timer for the actual emitted SV settlement. No financial calculation
is duplicated here. Inputs, opening variants and independent expected outcomes
are decoded before timing. Result retention and loop/IO-call overhead remain in
the kernel batch; JSON serialization and whole-outcome verification are separate.
-/
namespace SPL.PureSettlementBenchmark
open Lean

private def inputTypes : List (String × Syntax.TypeExpr) :=
  [("pictures", .named "List" [.named "SVPicture" []]),
   ("receipts", .named "List" [.named "SVReceipt" []]),
   ("eligible_costs", .named "List" [.named "SVCost" []]),
   ("policy", .named "SVPolicy" [])]

private def openingTypes : List (String × Syntax.TypeExpr) :=
  [("prepayment", .named "Money" [.named "USD" []])]

private def exactFields (value : Json) (expected : List String) : Except String Unit := do
  let object ← value.getObj? |>.mapError (fun _ => "PURE_RECORD_REQUIRED")
  let keys := object.toList.map Prod.fst
  unless keys.length == expected.length && expected.all keys.contains do
    throw "PURE_UNKNOWN_OR_MISSING_FIELD"

private def natural (value : Json) (field : String) : Except String Nat := do
  let text ← (← value.getObjVal? field).getStr?
  let some result := text.toNat? | throw "PURE_NATURAL_STRING_REQUIRED"
  return result

private structure Variant where
  nonce : Nat
  openings : Env
  expected : String
  deriving Inhabited

private structure Plan where
  initialIterations : Nat
  maximumIterations : Nat
  minimumSpanNs : Nat
  warmups : Nat
  samples : Nat
  variants : Array Variant

private def decodePlan (json : Json) : Except String Plan := do
  exactFields json ["format", "initial_iterations", "maximum_iterations", "minimum_span_ns", "warmups", "samples", "variants"]
  unless (← (← json.getObjVal? "format").getStr?) == "spl-pure-benchmark-plan/1" do throw "PURE_PLAN_VERSION"
  let initialIterations ← natural json "initial_iterations"
  let maximumIterations ← natural json "maximum_iterations"
  let minimumSpanNs ← natural json "minimum_span_ns"
  let warmups ← natural json "warmups"
  let samples ← natural json "samples"
  unless initialIterations ≥ 2 && initialIterations ≤ maximumIterations && maximumIterations ≤ 8192 &&
      minimumSpanNs > 0 && minimumSpanNs ≤ 1000000000 && warmups ≤ 128 && samples > 0 && samples ≤ 10 do
    throw "PURE_PLAN_RESOURCE_LIMIT"
  let records ← (← json.getObjVal? "variants").getArr?
  unless records.size ≥ 2 && records.size ≤ 128 do throw "PURE_VARIANT_LIMIT"
  let variants ← records.mapM fun record => do
    exactFields record ["nonce", "openings", "expected"]
    let nonce ← natural record "nonce"
    let openings ← Bindings.decodeBindings openingTypes (← record.getObjVal? "openings")
    let expected := (← record.getObjVal? "expected").compress
    return { nonce, openings, expected : Variant }
  unless (variants.toList.map Variant.nonce).eraseDups.length == variants.size do throw "PURE_DUPLICATE_NONCE"
  let quantities ← variants.toList.mapM fun variant => do asNum (← lookup variant.openings "prepayment")
  unless quantities.eraseDups.length == variants.size do throw "PURE_DUPLICATE_OPENING"
  unless (variants.toList.map Variant.expected).eraseDups.length > 1 do throw "PURE_RESULT_VARIATION_REQUIRED"
  return { initialIterations, maximumIterations, minimumSpanNs, warmups, samples, variants }

/-- The emitted implementation is in a separate library module. A noinline IO
boundary plus runtime-varying opening values prevents closed-term extraction and
keeps calls sequenced between the monotonic clocks. This is executable benchmark
discipline, not a theorem about every compiler optimization. -/
@[noinline] private def runSettlement (inputs openings : Env) : IO Settlement := do
  match GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.settle inputs openings with
  | .ok result => return result
  | .error code => throw (IO.userError ("PURE_TARGET_BLOCKED:" ++ code))

private def checksum (previous : UInt64) (text : String) : UInt64 := Id.run do
  let mut value := previous
  for byte in text.toUTF8 do
    value := (value ^^^ UInt64.ofNat byte.toNat) * 1099511628211
  return value

private structure Measurement where
  iterations : Nat
  settlementNs : Nat
  serializationNs : Nat
  verificationNs : Nat
  serializedBytes : Nat
  checksum : UInt64
  deriving Inhabited

private def Measurement.json (sample : Measurement) : Json := Json.mkObj [
  ("iterations", toJson sample.iterations), ("settlement_ns", toJson sample.settlementNs),
  ("serialization_ns", toJson sample.serializationNs), ("verification_ns", toJson sample.verificationNs),
  ("serialized_bytes", toJson sample.serializedBytes), ("checksum_fnv1a64", .str (toString sample.checksum)),
  ("independent_outcome_control", .str "passed")]

private def batch (inputs : Env) (variants : Array Variant) (iterations : Nat) : IO Measurement := do
  let mut results : Array Settlement := Array.emptyWithCapacity iterations
  let started ← IO.monoNanosNow
  for index in [:iterations] do
    let variant := variants[index % variants.size]!
    results := results.push (← runSettlement inputs variant.openings)
  let calculated ← IO.monoNanosNow
  let mut encoded : Array String := Array.emptyWithCapacity iterations
  for result in results do
    encoded := encoded.push (SPL.outcomeJson (.ok result)).compress
  let serialized ← IO.monoNanosNow
  let mut totalBytes := 0
  let mut digest : UInt64 := 14695981039346656037
  for index in [:encoded.size] do
    let text := encoded[index]!
    unless text == variants[index % variants.size]!.expected do
      throw (IO.userError ("PURE_INDEPENDENT_OUTCOME_MISMATCH:" ++ toString index))
    totalBytes := totalBytes + text.utf8ByteSize
    digest := checksum digest text
  let verified ← IO.monoNanosNow
  return { iterations, settlementNs := calculated - started, serializationNs := serialized - calculated,
           verificationNs := verified - serialized, serializedBytes := totalBytes, checksum := digest }

def run (args : List String) : IO UInt32 := do
  let [bindingPath, planPath] := args | throw (IO.userError "Usage: spl_pure_benchmark BINDINGS.json PLAN.json")
  let decodeStarted ← IO.monoNanosNow
  let bindingSource ← IO.FS.readFile bindingPath
  let planSource ← IO.FS.readFile planPath
  let decoded : Except String (Env × Plan) := do
    let bindings ← Bindings.parseStrict bindingSource
    exactFields bindings ["inputs", "openings"]
    let inputs ← Bindings.decodeBindings inputTypes (← bindings.getObjVal? "inputs")
    let _ ← Bindings.decodeBindings openingTypes (← bindings.getObjVal? "openings")
    let plan ← decodePlan (← Bindings.parseStrict planSource)
    return (inputs, plan)
  let (inputs, plan) ← match decoded with
    | .ok pair => pure pair
    | .error code => throw (IO.userError code)
  let decodeFinished ← IO.monoNanosNow
  let firstStarted ← IO.monoNanosNow
  let first ← runSettlement inputs plan.variants[0]!.openings
  let firstFinished ← IO.monoNanosNow
  let firstJson := SPL.outcomeJson (.ok first)
  let firstEncoded := firstJson.compress
  unless firstEncoded == plan.variants[0]!.expected do throw (IO.userError "PURE_FIRST_OUTCOME_MISMATCH")
  let warmStarted ← IO.monoNanosNow
  let mut warmChecksum := checksum 14695981039346656037 firstEncoded
  for index in [:plan.warmups] do
    let variant := plan.variants[(index + 1) % plan.variants.size]!
    let result ← runSettlement inputs variant.openings
    let encoded := (SPL.outcomeJson (.ok result)).compress
    unless encoded == variant.expected do throw (IO.userError "PURE_WARMUP_OUTCOME_MISMATCH")
    warmChecksum := checksum warmChecksum encoded
  let warmFinished ← IO.monoNanosNow
  let mut iterations := plan.initialIterations
  let mut calibration : Array Json := #[]
  let mut samples : Array Measurement := #[]
  for _ in [:14] do
    let sample ← batch inputs plan.variants iterations
    if sample.settlementNs ≥ plan.minimumSpanNs || iterations == plan.maximumIterations then
      samples := samples.push sample
      break
    calibration := calibration.push sample.json
    iterations := min plan.maximumIterations (iterations * 2)
  unless samples.size == 1 do throw (IO.userError "PURE_CALIBRATION_FAILED")
  for _ in [:plan.samples - 1] do
    samples := samples.push (← batch inputs plan.variants iterations)
  IO.println (Json.mkObj [
    ("format", .str "spl-pure-settlement-observations/1"), ("status", .str "passed"),
    ("binding_read_decode_plan_ns", toJson (decodeFinished - decodeStarted)),
    ("first_decoded_call_ns", toJson (firstFinished - firstStarted)),
    ("first_call_scope", .str "first decoded call in this process; OS/CPU cache state uncontrolled"),
    ("first_outcome", firstJson),
    ("warmup_calls", toJson plan.warmups), ("warmup_and_check_ns", toJson (warmFinished - warmStarted)),
    ("warmup_checksum_fnv1a64", .str (toString warmChecksum)),
    ("variant_count", toJson plan.variants.size), ("minimum_batch_ns", toJson plan.minimumSpanNs),
    ("variants_exercised_per_full_batch", toJson (min iterations plan.variants.size)),
    ("maximum_iterations", toJson plan.maximumIterations),
    ("resolution_span_reached", .bool (samples[0]!.settlementNs ≥ plan.minimumSpanNs)),
    ("calibration", .arr calibration), ("samples", .arr (samples.map Measurement.json)),
    ("scope", .str "cached decoded inputs and nonce openings; emitted settle + noinline IO boundary + nonce selection + strict result retention; serialization and verification separately timed")]).compress
  return 0

end SPL.PureSettlementBenchmark

def main (args : List String) : IO UInt32 := do
  try SPL.PureSettlementBenchmark.run args
  catch error =>
    IO.println (Lean.Json.mkObj [("status", .str "failed"),
      ("diagnostics", .arr #[Lean.Json.mkObj [("code", .str "PURE_BENCHMARK_FAILED"),
        ("message", .str error.toString)]])]).compress
    return 1
