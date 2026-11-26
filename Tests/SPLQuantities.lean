import SPL

/-! Executable dimensional boundary witnesses; the existing scalar theorem scope
is unchanged. This file also writes a standalone emitted module for native QA. -/
open SPL

private def ensure (condition : Bool) (message : String) : IO Unit :=
  unless condition do throw (IO.userError message)

private def get (value : Except String α) : IO α :=
  match value with
  | .ok value => pure value
  | .error code => throw (IO.userError code)

private def blocked (expected : String) : Except String α → Bool
  | .error code => code == expected
  | .ok _ => false

private def valueIs (expected : Value) : Eval Value → Bool
  | .ok value => equal value expected
  | .error _ => false

private def header := "schedule Quantities language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { "

private def program (body : String) : Except Syntax.Diagnostic IR.Program := do
  Elaborate.elaborate (← Parser.parse (header ++ body ++ " }"))

private def rejected (body code : String) : IO Unit :=
  match program body with
  | .error diagnostic => ensure (diagnostic.code == code) ("Wrong checker code: " ++ diagnostic.code)
  | .ok _ => throw (IO.userError ("Admitted invalid dimensions: " ++ body))

private def artifact (declarations : List IR.Decl) : IR.Program := {
  name := "DimensionalIRBoundary"
  language := "spl/0.1-draft"
  core := "spl-core/0.1-draft"
  schema := "spl-data/0.1-draft"
  span := {}
  declarations }

private def irMeta (id : Nat) (ty : IR.Ty) : IR.Meta := { id, ty, span := {} }

private def rejectIR (label : String) (p : IR.Program) : IO Unit := do
  match ValidateIR.validate p with
  | .error d => ensure (d.code == "INVALID_IR") (label ++ ": validation code")
  | .ok _ => throw (IO.userError (label ++ ": invalid IR accepted"))
  ensure (blocked "INVALID_IR" (Interpret.interpret p [] []).result) (label ++ ": interpreter boundary")
  for result in [Emit.emitIR p, Emit.emitLibraryIR p] do
    match result with
    | .error d => ensure (d.code == "INVALID_IR") (label ++ ": emitter code")
    | .ok _ => throw (IO.userError (label ++ ": emitter boundary"))

private def rejectHiddenDimensions : IO Unit := do
  for invalid in [Check.Ty.quantity "Unknown", .rate "Download" "EUR", .rate "Unknown" "USD"] do
    rejectIR "Empty dimensional list" (artifact [
      .emit (irMeta 0 (.list invalid)) "invalid" (.list (irMeta 1 (.list invalid)) [])])
    rejectIR "Dimensional none below a valid Boolean parent" (artifact [
      .emit (irMeta 0 Check.boolTy) "invalid" (.call (irMeta 1 Check.boolTy) "is_some" [
        .call (irMeta 2 (.option invalid)) "none" []])])
    let nested : IR.Ty := .option (.record "literal" [("values", .list invalid)])
    rejectIR "Unknown nested type hidden by none" (artifact [
      .emit (irMeta 0 Check.boolTy) "invalid" (.call (irMeta 1 Check.boolTy) "is_some" [
        .call (irMeta 2 nested) "none" []])])
    rejectIR "Typed dimensional zero from an empty sum" (artifact [
      .emit (irMeta 0 invalid) "invalid" (.collection (irMeta 1 invalid) "sum" "item" invalid
        (.list (irMeta 2 (.list invalid)) []) (.name (irMeta 3 invalid) "item"))])
    rejectIR "Unused dimensional definition" (artifact [
      .define (irMeta 0 (.option invalid)) "unused" (.call (irMeta 1 (.option invalid)) "none" []),
      .emit (irMeta 2 Check.intTy) "valid" (.number (irMeta 3 Check.intTy) "1")])

private def inventory := "
  input quantity: Quantity<Download>;
  input rate: Rate<Download,USD>;
  input quantum: Quantity<Download>;
  input rate_quantum: Rate<Download,USD>;
  input empty: List<Quantity<Download>>;
  input empty_rates: List<Rate<Download,USD>>;
  input rows: List<{units: Quantity<Download>, price: Rate<Download,USD>}>;
  input optional: Option<Quantity<Download>>;
  opening meter: Quantity<Download> from \"quantity_meter\";
  define gross = quantity * rate;
  define payable = gross * 0.5;
  define total = sum(rows, row => row.units);
  define zero = sum(empty, item => item);
  define zero_rate = sum(empty_rates, item => item);
  define positive = filter(rows, row => row.units >= zero);
  define scaled = map(positive, row => row.units * 0.5);
  define folded = fold rows from meter with state,event { yield state + event.units; };
  define sorted = sort_by(rows, row => row.units);
  define smallest = min(quantity, quantum);
  define largest_rate = max(rate, rate_quantum);
  define rounded = quantize(quantity, quantum, \"half_even\");
  define rounded_rate = quantize(rate, rate_quantum, \"half_even\");
  define absolute = abs(-quantity);
  define scaled_rate = 0.5 * rate;
  define ratio = quantity / quantity;
  define rate_ratio = rate / rate;
  define selected = require_some(optional, \"MISSING_QUANTITY\");
  define pair = tuple(quantity, rate);
  closing meter = meter + total;
  emit \"result\" = {gross: gross, share: payable, zero: zero, zero_rate: zero_rate,
    scaled: scaled, rounded: rounded, rounded_rate: rounded_rate, absolute: absolute,
    folded: folded, sorted: sorted, smallest: smallest, largest_rate: largest_rate, scaled_rate: scaled_rate, ratio: ratio, rate_ratio: rate_ratio, selected: selected, pair: pair};
"

private def bindingSource := "{\"inputs\":{\"quantity\":{\"unit\":\"Download\",\"value\":\"100\"},\"rate\":{\"per_unit\":\"Download\",\"currency\":\"USD\",\"value\":\"1.5\"},\"quantum\":{\"unit\":\"Download\",\"value\":\"1\"},\"rate_quantum\":{\"per_unit\":\"Download\",\"currency\":\"USD\",\"value\":\"0.1\"},\"empty\":[],\"empty_rates\":[],\"rows\":[{\"units\":{\"unit\":\"Download\",\"value\":\"0.5\"},\"price\":{\"per_unit\":\"Download\",\"currency\":\"USD\",\"value\":\"1.5\"}}],\"optional\":{\"some\":{\"unit\":\"Download\",\"value\":\"0.5\"}}},\"openings\":{\"meter\":{\"unit\":\"Download\",\"value\":\"2\"}}}"

def main : IO Unit := do
  rejectHiddenDimensions
  let q := Value.quantity "Download"
  let r := Value.rate "Download" "USD"
  ensure (valueIs (.num 150) (binary "*" (q 100) (r (mkRat 3 2)))) "quantity × rate"
  ensure (valueIs (.num 150) (binary "*" (r (mkRat 3 2)) (q 100))) "rate × quantity"
  ensure (valueIs (q (mkRat 1 4)) (binary "*" (.num (mkRat 1 2)) (q (mkRat 1 2)))) "fractional scaling"
  ensure (valueIs (r 3) (binary "/" (r 6) (.num 2))) "rate scaling"
  ensure (valueIs (.num 2) (binary "/" (q 6) (q 3))) "dimension cancellation"
  ensure (valueIs (q 0) (sumValuesFrom (q 0) (.seq []) pure)) "empty quantity sum"
  ensure (valueIs (r 0) (sumValuesFrom (r 0) (.seq []) pure)) "empty rate sum"
  ensure (valueIs (q 2) (absolute (q (-2)))) "signed quantity abs"
  ensure (valueIs (r 2) (unary "-" (r (-2)))) "signed rate negation"
  ensure (blocked "DIVISION_BY_ZERO" (binary "/" (q 1) (q 0))) "zero quantity divisor"
  ensure (blocked "DIVISION_BY_ZERO" (binary "/" (r 1) (.num 0))) "zero ratio divisor"
  ensure (blocked "TYPE_MISMATCH" (binary "*" (q 1) (q 2))) "quantity squared"
  ensure (blocked "TYPE_MISMATCH" (binary "+" (q 1) (.quantity "UsageMinute" 2))) "runtime mismatched unit"
  ensure (blocked "TYPE_MISMATCH" (quantize (q 1) (r 1) (.text "floor"))) "quantum dimension"
  ensure (blocked "INVALID_QUANTUM" (quantize (q 1) (q 0) (.text "floor"))) "nonpositive quantum"
  for (mode, expected) in [("floor", -3), ("ceiling", -2), ("toward_zero", -2),
      ("half_even", -2), ("half_away_from_zero", -3)] do
    ensure (valueIs (q expected) (quantize (q (mkRat (-5) 2)) (q 1) (.text mode))) ("quantity rounding: " ++ mode)
    ensure (valueIs (r expected) (quantize (r (mkRat (-5) 2)) (r 1) (.text mode))) ("rate rounding: " ++ mode)
  for body in [
      "input a: Quantity<Download>; input b: Quantity<UsageMinute>; define x = a + b;",
      "input a: Quantity<Download>; input b: Rate<UsageMinute,USD>; define x = a * b;",
      "input a: Quantity<Download>; define x = a * a;",
      "input a: Quantity<Download>; define x = USD 1 / a;",
      "input a: Quantity<Download>; define x = a + 1;",
      "input a: Quantity<Download>; define x = quantize(a, USD 1, \"floor\");"] do
    rejected body "TYPE_MISMATCH"
  rejected "input a: Quantity<Unknown>;" "UNSUPPORTED_UNIT"
  rejected "input a: Rate<Download,EUR>;" "UNSUPPORTED_CURRENCY"
  rejected "input a: Map<Quantity<Download>,Int>;" "INVALID_MAP_KEY_TYPE"
  rejected "input rows: List<{units: Quantity<Download>, id: Int}>; input zero: Quantity<Download>; define x = ordered_fold rows from zero by k => k.units identified by i => i.id ties \"reject\" with state,event { yield state; };" "INVALID_EVENT_KEY_TYPE"
  let malformed ← get (Bindings.parseStrict "{\"unit\":\"UsageMinute\",\"value\":\"1\"}")
  ensure (blocked "UNIT_MISMATCH" (Bindings.decode (.quantity "Download") malformed)) "strict quantity tag"
  let untagged ← get (Bindings.parseStrict "\"1\"")
  ensure (blocked "INVALID_QUANTITY" (Bindings.decode (.quantity "Download") untagged)) "untagged quantity"
  let p ← match program inventory with
    | .ok p => pure p
    | .error d => throw (IO.userError (reprStr d))
  match ValidateIR.validate p with
  | .ok _ => pure ()
  | .error d => throw (IO.userError (reprStr d))
  let bindings ← get (Bindings.parseStrict bindingSource)
  let inputTypes := p.declarations.filterMap fun d => match d with
    | .input m name => some (name,m.ty) | _ => none
  let inputs ← inputTypes.mapM fun (name,ty) => do
    let inputJson ← get ((bindings.getObjVal? "inputs") >>= fun json => json.getObjVal? name)
    pure (name, ← get (Bindings.decode ty inputJson))
  let outcome := Interpret.interpret p inputs [("meter", q 2)]
  let result ← get outcome.result
  let report ← get (lookup result.emissions "result")
  ensure (valueIs (.num 150) (field report "gross")) "interpreted gross"
  ensure (valueIs (.num 75) (field report "share")) "interpreted share"
  ensure (valueIs (q 0) (field report "zero")) "interpreted typed quantity zero"
  ensure (valueIs (r 0) (field report "zero_rate")) "interpreted typed rate zero"
  ensure (valueIs (q (mkRat 5 2)) (lookup result.closing "meter")) "tagged meter carry"
  ensure (valueIs (q (mkRat 5 2)) (field report "folded")) "dimensional fold state"
  ensure (valueIs (q 100) (field report "absolute")) "interpreted dimensional abs"
  ensure (outcome.trace.nodes.any fun n => n.valueType == .quantity "Download") "audit quantity dimension"
  ensure (outcome.trace.nodes.any fun n => n.valueType == .rate "Download" "USD") "audit rate dimension"
  let forged := { p with declarations := p.declarations.map fun d => match d with
    | .input m "quantity" => .input {m with ty := .quantity "Unknown"} "quantity"
    | _ => d }
  match ValidateIR.validate forged with
  | .error d => ensure (d.code == "INVALID_IR") "forged unit IR code"
  | .ok _ => throw (IO.userError "forged unregistered IR unit admitted")
  let generated ← match Emit.emitIR p with
    | .ok source => pure source
    | .error d => throw (IO.userError (reprStr d))
  IO.FS.writeFile ".lake/quantity-native-generated.lean" generated
  IO.FS.writeFile ".lake/quantity-native-bindings.json" bindingSource
  IO.println "SPL quantities passed (typed arithmetic, five rounding modes, tagged containers/zero/state, strict bindings, defensive IR, trace, emission)."
