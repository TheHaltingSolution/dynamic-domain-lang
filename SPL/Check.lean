import SPL.Syntax
import SPL.Instant
import SPL.Dimensions

/-! Native static checking for the bounded SV/LG SPL implementation.
This checker establishes structural types and ports, not contractual authority.
Definitions are resolved by a finite dependency pass; no source evaluation occurs.
-/
namespace SPL.Check
open SPL.Syntax

inductive Ty where
  | atom : String → Ty
  | money : String → Ty
  | quantity : String → Ty
  | rate : String → String → Ty
  | list : Ty → Ty
  | option : Ty → Ty
  | tuple : List Ty → Ty
  | map : Ty → Ty → Ty
  | record : String → List (String × Ty) → Ty
  deriving Repr, BEq, Inhabited

def boolTy : Ty := .atom "Bool"
def intTy : Ty := .atom "Int"
def ratioTy : Ty := .atom "Ratio"
def dateTy : Ty := .atom "Date"
def instantTy : Ty := .atom "Instant"
def textTy : Ty := .atom "Text"
def usdTy : Ty := .money "USD"
def idTy (name : String) : Ty := .atom ("Id:" ++ name)
def periodTy : Ty := .record "Period" [("start", dateTy), ("end", dateTy)]

def schema : String → Option Ty
  | "Period" => some periodTy
  | "SVPicture" => some (.record "SVPicture" [("asset_id", idTy "Asset"),
      ("contribution_present", boolTy), ("funding_share", ratioTy)])
  | "SVReceipt" => some (.record "SVReceipt" [("fact_id", idTy "Fact"),
      ("asset_id", idTy "Asset"), ("amount", usdTy), ("cash_received_date", dateTy)])
  | "SVCost" => some (.record "SVCost" [("fact_id", idTy "Fact"),
      ("asset_id", idTy "Asset"), ("amount", usdTy), ("incurred_date", dateTy),
      ("eligibility_decision_id", idTy "Decision")])
  | "SVPostingCost" => some (.record "SVPostingCost" [("fact_id", idTy "Fact"),
      ("asset_id", idTy "Asset"), ("amount", usdTy), ("recognition_date", dateTy),
      ("recognition_policy_ref", idTy "Policy"), ("eligibility_decision_id", idTy "Decision")])
  | "SVPolicy" => some (.record "SVPolicy" [("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"), ("pool_id", idTy "Pool"), ("period", periodTy)])
  | "LGReceipt" => some (.record "LGReceipt" [("fact_id", idTy "Fact"),
      ("asset_id", idTy "Asset"), ("amount", usdTy), ("cash_received_date", dateTy),
      ("is_home_video", boolTy)])
  | "LGCost" => some (.record "LGCost" [("fact_id", idTy "Fact"),
      ("asset_id", idTy "Asset"), ("amount", usdTy), ("incurred_date", dateTy)])
  | "LGPolicy" => some (.record "LGPolicy" [("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"), ("asset_id", idTy "Asset"),
      ("pool_id", idTy "Pool"), ("period", periodTy), ("video_proxy", ratioTy),
      ("gross_rate", ratioTy), ("net_rate", ratioTy)])
  | "LGHurdleAttestation" => some (.record "LGHurdleAttestation" [
      ("agreement_id", idTy "Agreement"), ("attained", boolTy), ("effective_date", dateTy)])
  | "LGGateHistoryAttestation" => some (.record "LGGateHistoryAttestation" [
      ("asset_id", idTy "Asset"), ("period", periodTy), ("cleared_throughout", boolTy)])
  | "SettlementScope" => some (.record "SettlementScope" [
      ("agreement_id", idTy "Agreement"), ("participant_id", idTy "Participant"),
      ("pool_id", idTy "Pool"), ("period", periodTy)])
  | "AdvanceIssue" => some (.record "AdvanceIssue" [
      ("event_id", idTy "Event"),
      ("issue_id", idTy "AdvanceIssue"),
      ("disbursement_id", idTy "Disbursement"),
      ("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"),
      ("pool_id", idTy "Pool"),
      ("source_title_id", idTy "Asset"),
      ("currency", textTy),
      ("balance_purpose", textTy),
      ("amount", usdTy),
      ("funded_date", dateTy),
      ("observed_at", instantTy),
      ("approved", boolTy),
      ("authority_ref", idTy "Decision"),
      ("evidence_ref", idTy "AdvanceEvidence")])
  | "AdvanceEvidence" => some (.record "AdvanceEvidence" [
      ("evidence_id", idTy "AdvanceEvidence"),
      ("issue_id", idTy "AdvanceIssue"),
      ("disbursement_id", idTy "Disbursement"),
      ("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"),
      ("pool_id", idTy "Pool"),
      ("source_title_id", idTy "Asset"),
      ("currency", textTy),
      ("balance_purpose", textTy),
      ("amount", usdTy),
      ("funded_date", dateTy),
      ("observed_at", instantTy),
      ("approved", boolTy),
      ("authority_ref", idTy "Decision"),
      ("eligible", boolTy)])
  | "ReserveVintage" => some (.record "ReserveVintage" [
      ("vintage_id", idTy "Vintage"),
      ("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"),
      ("pool_id", idTy "Pool"),
      ("purpose", textTy),
      ("currency", textTy),
      ("balance", usdTy)])
  | "ReserveMovement" => some (.record "ReserveMovement" [
      ("event_id", idTy "Event"),
      ("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"),
      ("pool_id", idTy "Pool"),
      ("purpose", textTy),
      ("currency", textTy),
      ("vintage_id", idTy "Vintage"),
      ("kind", textTy),
      ("amount", usdTy),
      ("effective_date", dateTy),
      ("observed_at", instantTy),
      ("evidence_ref", idTy "ReserveEvidence")])
  | "ReserveEvidence" => some (.record "ReserveEvidence" [
      ("evidence_id", idTy "ReserveEvidence"),
      ("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"),
      ("pool_id", idTy "Pool"),
      ("purpose", textTy),
      ("currency", textTy),
      ("vintage_id", idTy "Vintage"),
      ("kind", textTy),
      ("amount", usdTy),
      ("effective_date", dateTy),
      ("observed_at", instantTy),
      ("approved", boolTy),
      ("authority_ref", idTy "Decision")])
  | "PaymentApplication" => some (.record "PaymentApplication" [
      ("event_id", idTy "Event"), ("agreement_id", idTy "Agreement"),
      ("participant_id", idTy "Participant"), ("pool_id", idTy "Pool"),
      ("amount", usdTy), ("obligation_id", idTy "Obligation"), ("paid_date", dateTy),
      ("approved", boolTy), ("authority_ref", idTy "Decision")])
  | _ => none

def error (code message : String) (span : Span := {}) : Except Diagnostic α :=
  .error ⟨code, message, span⟩

partial def keyType : Ty → Bool
  | .atom name => ["Bool", "Int", "Nat", "Date"].contains name || name.startsWith "Id:"
  | .tuple items => items.length ≥ 2 && items.all keyType
  | _ => false

partial def parseTypeWith (admission : Dimensions.Admission) : TypeExpr → Except Diagnostic Ty
  | .record fields => do
    let names := fields.map Prod.fst
    unless names.eraseDups.length == names.length do error "DUPLICATE_FIELD" "Duplicate type field"
    return .record "literal" (← fields.mapM fun (name, ty) => do pure (name, ← parseTypeWith admission ty))
  | .named name args => do
    if let some ty := schema name then
      if !args.isEmpty then error "TYPE_ARITY" (name ++ " has no type arguments") else pure ty
    else if ["Bool", "Int", "Nat", "Ratio", "Rational", "Text", "Date", "Instant"].contains name then
      if !args.isEmpty then error "TYPE_ARITY" (name ++ " has no type arguments") else pure (.atom name)
    else match name, args with
      | "Money", [.named "USD" []] => pure usdTy
      | "Money", [.named currency []] => error "UNSUPPORTED_CURRENCY" s!"Money<{currency}> is unsupported; use Money<USD>"
      | "Money", _ => error "TYPE_ARITY" "Money requires one currency argument, as in Money<USD>"
      | "Quantity", [.named unit []] =>
        if Dimensions.admittedWith admission unit then pure (.quantity unit)
        else error "UNSUPPORTED_UNIT" ("Unknown quantity unit " ++ unit)
      | "Rate", [.named unit [], .named currency []] =>
        if !Dimensions.admittedWith admission unit then error "UNSUPPORTED_UNIT" ("Unknown rate unit " ++ unit)
        else if currency != "USD" then error "UNSUPPORTED_CURRENCY" "Only Rate<U,USD> is supported"
        else pure (.rate unit currency)
      | "List", [arg] => return .list (← parseTypeWith admission arg)
      | "Option", [arg] => return .option (← parseTypeWith admission arg)
      | "Tuple", args =>
        if args.length < 2 then error "TYPE_ARITY" "Tuple requires at least two components"
        else return .tuple (← args.mapM (parseTypeWith admission))
      | "Map", [key, value] =>
        let key ← parseTypeWith admission key
        unless keyType key do error "INVALID_MAP_KEY_TYPE" "Map requires an admitted total-order key"
        return .map key (← parseTypeWith admission value)
      | "Id", [.named kind []] => pure (idTy kind)
      | "List", _ | "Option", _ => error "TYPE_ARITY" (name ++ " requires exactly one type argument")
      | "Map", _ => error "TYPE_ARITY" "Map requires a key type and a value type"
      | "Id", _ => error "TYPE_ARITY" "Id requires one atomic identifier kind, as in Id<Receipt>"
      | "Quantity", [_] | "Rate", [_, _] => error "UNSUPPORTED_TYPE" "Dimension arguments must be atomic"
      | "Quantity", _ => error "TYPE_ARITY" "Quantity requires one atomic unit, as in Quantity<Download>"
      | "Rate", _ => error "TYPE_ARITY" "Rate requires a unit and a currency, as in Rate<Download,USD>"
      | _, _ => error "UNSUPPORTED_TYPE" ("Unsupported type " ++ name)

def parseType (ty : TypeExpr) : Except Diagnostic Ty := parseTypeWith {} ty

private def parseTypeAt (admission : Dimensions.Admission) (span : Span) (type : TypeExpr) : Except Diagnostic Ty :=
  (parseTypeWith admission type).mapError fun diagnostic => { diagnostic with span }

abbrev Context := List (String × Ty)

def lookup (context : List (String × α)) (name : String) : Option α :=
  (context.find? fun entry => entry.1 == name).map Prod.snd

partial def compatible (a b : Ty) : Bool :=
  match a, b with
  | .record _ xs, .record _ ys => xs.length == ys.length && xs.all (fun (key, ty) =>
      match lookup ys key with | some other => compatible ty other | none => false)
  | .list x, .list y | .option x, .option y => compatible x y
  | .tuple xs, .tuple ys => xs.length == ys.length && (xs.zip ys).all (fun (x,y) => compatible x y)
  | .map k v, .map k' v' => k == k' && compatible v v'
  | _, _ => a == b

def numeric : Ty → Bool
  | .money _ | .quantity _ | .rate _ _ => true
  | .atom name => ["Int", "Nat", "Ratio", "Rational"].contains name
  | _ => false

partial def scalar : Ty → Bool
  | .atom name => name != "Bool"
  | .money _ | .quantity _ | .rate _ _ => true
  | .tuple items => items.all scalar
  | _ => false

def dimensional : Ty → Bool
  | .quantity _ | .rate _ _ => true
  | _ => false

def constrain (found : Ty) (expected : Option Ty) (span : Span) : Except Diagnostic Ty := do
  if let some expected := expected then
    unless compatible found expected do
      error "TYPE_MISMATCH" ("Incompatible types: " ++ reprStr found ++ " / " ++ reprStr expected) span
  pure found

def isNumber : Expr → Bool | .number .. => true | _ => false
def dimensionless (ty : Ty) : Option Ty := match ty with
  | .atom name => if ["Int", "Nat", "Ratio", "Rational"].contains name then some ty else none
  | _ => none

def bind (context : Context) (name : String) (ty : Ty) (span : Span) : Except Diagnostic Context :=
  if (lookup context name).isSome then error "DUPLICATE_NAME" ("Duplicate/shadowing name " ++ name) span
  else pure ((name, ty) :: context)

def duplicate (names : List String) : Bool := names.length != names.eraseDups.length

def dateValid (value : String) : Bool := Id.run do
  let parts := value.splitOn "-"
  if parts.length != 3 then return false
  let [yearS, monthS, dayS] := parts | return false
  if yearS.length != 4 || monthS.length != 2 || dayS.length != 2 then return false
  let some year := yearS.toNat? | return false
  let some month := monthS.toNat? | return false
  let some day := dayS.toNat? | return false
  if year == 0 || month == 0 || month > 12 || day == 0 then return false
  let leap := year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
  let limit := if month == 2 then (if leap then 29 else 28)
    else if [4, 6, 9, 11].contains month then 30 else 31
  return day ≤ limit

structure Inference where
  lexical : Dimensions.Admission := {}
  owners : List (String × List String) := []
  signatures : List FunctionSignature := []
  deriving Repr, Inhabited

def inference (schedule : Schedule) : Except Diagnostic Inference := do
  let lexical ← (Dimensions.prepare schedule.features).mapError (fun code => { code, message := code, span := schedule.span })
  unless (schedule.owners.map Prod.fst).eraseDups.length == schedule.owners.length do
    error "INVALID_OWNER_CONTEXT" "Duplicate application owner"
  for (_, features) in schedule.owners do
    let _ ← (Dimensions.prepare features).mapError (fun code => { code, message := code })
  unless (schedule.signatures.map (·.label)).eraseDups.length == schedule.signatures.length do
    error "INVALID_FUNCTION_SIGNATURE" "Duplicate linked signature"
  for signature in schedule.signatures do
    let some features := schedule.owners.lookup signature.label
      | error "INVALID_OWNER_CONTEXT" "Signature has no owning module"
    let owner ← (Dimensions.prepare features).mapError (fun code => { code, message := code })
    unless !signature.label.isEmpty && !duplicate (signature.parameters.map Prod.fst) do
      error "INVALID_FUNCTION_SIGNATURE" "Malformed linked signature"
    for (_, ty) in signature.parameters do
      let _ ← parseTypeWith owner ty
      pure ()
    let _ ← parseTypeWith owner signature.result
    pure ()
  pure { lexical, owners := schedule.owners, signatures := schedule.signatures }

def ownerInference (settings : Inference) (label : String) : Except Diagnostic Inference := do
  let features := (settings.owners.lookup label).getD []
  let lexical ← (Dimensions.prepare features).mapError (fun code => { code, message := code })
  pure { settings with lexical }

mutual
partial def inferWith (settings : Inference) (context : Context) (expression : Expr) (expected : Option Ty := none) : Except Diagnostic Ty := do
  let found ← inferRawWith settings context expression expected
  constrain found expected expression.span

partial def inferRawWith (settings : Inference) (context : Context) (expression : Expr) (expected : Option Ty) : Except Diagnostic Ty := do
  match expression with
  | .number span value =>
    if let some (.atom name) := expected then
      if ["Ratio", "Rational", "Int", "Nat"].contains name then
        if ["Int", "Nat"].contains name && value.contains '.' then
          return ← error "TYPE_MISMATCH" "Decimal cannot become integer" span
        return .atom name
    return if value.contains '.' then ratioTy else intTy
  | .money span currency _ =>
    if currency != "USD" then error "UNSUPPORTED_CURRENCY" "Only USD is supported" span else pure usdTy
  | .boolean .. => pure boolTy
  | .text .. => pure textTy
  | .date span value => if dateValid value then pure dateTy else error "INVALID_DATE" "Invalid Gregorian date" span
  | .name span name => match lookup context name with
    | some (.atom "$pending") => error "UNRESOLVED_NAME" ("Pending definition " ++ name) span
    | some ty => pure ty
    | none => error "UNRESOLVED_NAME" ("Unresolved name " ++ name) span
  | .field span base name =>
    let .record _ fields ← inferWith settings context base | error "TYPE_MISMATCH" "Field access needs record" span
    match lookup fields name with
    | some ty => pure ty
    | none => error "UNKNOWN_FIELD" ("Unknown field " ++ name) span
  | .unary span op body =>
    if op == "not" then let _ ← inferWith settings context body (some boolTy); pure boolTy
    else if op == "-" then
      let ty ← inferWith settings context body expected
      if numeric ty && ty != .atom "Nat" then pure ty
      else error "TYPE_MISMATCH" "Minus needs signed numeric value" span
    else error "UNSUPPORTED_OPERATOR" op span
  | .binary span op left right =>
    if op == "and" || op == "or" then
      let _ ← inferWith settings context left (some boolTy)
      let _ ← inferWith settings context right (some boolTy)
      return boolTy
    let (a, b) ← if isNumber left && !isNumber right then do
        let b ← inferWith settings context right
        let hint := if op == "*" && (b == usdTy || dimensional b) then some ratioTy else dimensionless b
        let a ← inferWith settings context left hint
        pure (a, b)
      else do
        let a ← inferWith settings context left
        let hint := if (op == "*" || op == "/") && (a == usdTy || dimensional a) then some ratioTy else dimensionless a
        let b ← inferWith settings context right (if isNumber right then hint else none)
        pure (a, b)
    if ["==", "!=", "<", "<=", ">", ">="].contains op then
      unless compatible a b do error "TYPE_MISMATCH" "Comparison units differ" span
      unless op == "==" || op == "!=" || scalar a || keyType a do error "TYPE_MISMATCH" "Type has no total comparison" span
      return boolTy
    unless numeric a && numeric b do error "TYPE_MISMATCH" "Arithmetic requires numeric operands" span
    if op == "-" && a == .atom "Nat" then
      return ← error "UNSUPPORTED_OPERATOR" "Nat subtraction is outside this emitted profile" span
    if (op == "+" || op == "-") && compatible a b then return a
    if op == "*" then
      if dimensional a && b == ratioTy then return a
      if a == ratioTy && dimensional b then return b
      match a, b with
      | .quantity u, .rate v c | .rate v c, .quantity u => if u == v then return .money c
      | _, _ => pure ()
      if a == usdTy && b == ratioTy then return usdTy
      if a == ratioTy && b == usdTy then return usdTy
      if compatible a b && a != usdTy && !dimensional a then return a
    if op == "/" then
      if dimensional a && b == ratioTy then return a
      if dimensional a && compatible a b then return ratioTy
      if a == usdTy && b == ratioTy then return usdTy
      if a == usdTy && b == usdTy then return ratioTy
      if a == b && (a == ratioTy || a == .atom "Rational") then return a
    error "TYPE_MISMATCH" (s!"Operator {op} is not defined for {reprStr a} and {reprStr b}") span
  | .ite _ condition yes no =>
    let _ ← inferWith settings context condition (some boolTy)
    if let some ty := expected then
      let _ ← inferWith settings context yes (some ty)
      let _ ← inferWith settings context no (some ty)
      return ty
    else if isNumber yes && !isNumber no then
      let ty ← inferWith settings context no
      let _ ← inferWith settings context yes (some ty)
      return ty
    else
      let ty ← inferWith settings context yes
      let _ ← inferWith settings context no (some ty)
      return ty
  | .record span fields =>
    if duplicate (fields.map Prod.fst) then return ← error "DUPLICATE_FIELD" "Duplicate record fields" span
    let hints := match expected with | some (.record _ fields) => fields | _ => []
    let fields ← fields.mapM fun (name, value) => do
      let ty ← inferWith settings context value (lookup hints name)
      pure (name, ty)
    return .record "literal" fields
  | .list span items =>
    let hint := match expected with | some (.list ty) => some ty | _ => none
    let mut itemType := hint
    for item in items do itemType := some (← inferWith settings context item itemType)
    match itemType with
    | some ty => pure (.list ty)
    | none => error "AMBIGUOUS_EMPTY_LIST" "Empty list needs expected type" span
  | .lambda span .. => error "ESCAPING_LAMBDA" "Lambda is valid only inside a collection call" span
  | .choose span arms fallback =>
    if arms.isEmpty then return ← error "EMPTY_RULE_SET" "choose unique requires an arm" span
    if (arms.filter fun (p, _) => match p with | .boolean _ true => true | _ => false).length > 1 then
      return ← error "AMBIGUOUS_RULE" "Multiple statically true arms" span
    let mut resultType := expected
    for (predicate, body) in arms do
      let _ ← inferWith settings context predicate (some boolTy)
      resultType := some (← inferWith settings context body resultType)
    if let some fallback := fallback then let _ ← inferWith settings context fallback resultType; pure ()
    match resultType with
    | some ty => pure ty
    | none => error "EMPTY_RULE_SET" "Missing rule result type" span
  | .selectRules span _ arms fallback =>
    let ids := arms.map (fun (id, _, _, _) => id) ++ fallback.toList.map Prod.fst
    if ids.any String.isEmpty then return ← error "INVALID_RULE_ID" "Rule IDs must be nonempty" span
    if ids.eraseDups.length != ids.length then return ← error "DUPLICATE_RULE_ID" "Rule IDs must be unique" span
    if arms.isEmpty && (fallback.isNone || expected.isNone) then
      return ← error "EMPTY_RULE_SET" "Empty registered rules require fallback and explicit result type" span
    let mut resultType := expected
    for (_, _, predicate, body) in arms do
      let _ ← inferWith settings context predicate (some boolTy)
      resultType := some (← inferWith settings context body resultType)
    if let some (_, body) := fallback then resultType := some (← inferWith settings context body resultType)
    match resultType with
    | some ty => pure ty
    | none => error "EMPTY_RULE_SET" "Missing rule result type" span
  | .forEach span name source declarations yielded =>
    let .list itemTy ← inferWith settings context source | error "TYPE_MISMATCH" "for each requires list" span
    let nested ← bind context name itemTy span
    let nested ← checkLocalsWith settings nested declarations
    let hint := match expected with | some (.list ty) => some ty | _ => none
    return .list (← inferWith settings nested yielded hint)
  | .fold span source initial state event order declarations body =>
    let stateTy ← inferWith settings context initial expected
    let .list eventTy ← inferWith settings context source | error "TYPE_MISMATCH" "fold requires a finite list" span
    if let some (keyBinder, key, idBinder, identity, ties) := order then
      unless ties == "reject" do error "UNRESOLVED_EVENT_ORDER" "Only explicit reject tie policy is supported" span
      let keyTy ← inferWith settings (← bind context keyBinder eventTy span) key
      let idTy ← inferWith settings (← bind context idBinder eventTy span) identity
      unless keyType keyTy && keyType idTy do error "INVALID_EVENT_KEY_TYPE" "Event key and identity need admitted total-order types" span
    let nested ← bind (← bind context state stateTy span) event eventTy span
    let nested ← checkLocalsWith settings nested declarations
    let _ ← inferWith settings nested body (some stateTy)
    pure stateTy
  | .apply span label parameters args result declarations body =>
    if !(settings.lexical.features ++ settings.owners.flatMap Prod.snd).isEmpty || !settings.signatures.isEmpty then
      let some signature := settings.signatures.find? (·.label == label)
        | error "INVALID_FUNCTION_SIGNATURE" "Application lacks linked signature" span
      unless signature.parameters == parameters && signature.result == result do
        error "INVALID_FUNCTION_SIGNATURE" "Application differs from linked signature" span
    let callee ← ownerInference settings label
    unless parameters.length == args.length do error "FUNCTION_ARITY" "Function argument count differs" span
    let mut nested : Context := []
    for ((name, annotation), arg) in parameters.zip args do
      let ty ← parseTypeWith callee.lexical annotation
      let _ ← inferWith settings context arg (some ty)
      nested ← bind nested name ty span
    let resultTy ← parseTypeWith callee.lexical result
    nested ← checkLocalsWith callee nested declarations
    let _ ← inferWith callee nested body (some resultTy)
    pure resultTy
  | .call span name args =>
    if name == "convert_quantity" then
      unless Dimensions.hasBuiltin settings.lexical name do
        error "UNSUPPORTED_BUILTIN"
          s!"convert_quantity requires uses \"{Dimensions.usageFeature}\" in the calling schedule or module" span
      let [value, .text _ target, .text _ relation] := args
        | return ← error "CONVERSION_LITERAL_REQUIRED" "Expected quantity and literal target/relation" span
      let .quantity source ← inferWith settings context value
        | error "TYPE_MISMATCH" "Conversion requires Quantity" span
      let _ ← (Dimensions.conversionFactor settings.lexical source target relation).mapError
        (fun code => { code, message := code, span })
      return .quantity target
    if name == "append" || name == "concat" then
      let [source, value] := args | return ← error "BUILTIN_ARITY" "append/concat require two arguments" span
      let sourceTy ← inferWith settings context source expected
      let .list itemTy := sourceTy | error "TYPE_MISMATCH" "append/concat require a list" span
      let _ ← inferWith settings context value (some (if name == "append" then itemTy else sourceTy))
      return sourceTy
    if name == "none" then
      unless args.isEmpty do error "BUILTIN_ARITY" "none takes no arguments" span
      let some (.option ty) := expected | return ← error "AMBIGUOUS_OPTION" "none requires an expected Option type" span
      return .option ty
    if name == "some" then
      let [body] := args | return ← error "BUILTIN_ARITY" "some takes one argument" span
      return .option (← inferWith settings context body (match expected with | some (.option ty) => some ty | _ => none))
    if name == "is_some" then
      let [body] := args | return ← error "BUILTIN_ARITY" "is_some takes one argument" span
      let .option _ ← inferWith settings context body | error "TYPE_MISMATCH" "is_some requires Option" span
      return boolTy
    if name == "get_or" then
      let [body, fallback] := args | return ← error "BUILTIN_ARITY" "get_or takes Option and explicit fallback" span
      let .option ty ← inferWith settings context body (expected.map .option) | error "TYPE_MISMATCH" "get_or requires Option" span
      let _ ← inferWith settings context fallback (some ty)
      return ty
    if name == "tuple" then
      if args.length < 2 then return ← error "BUILTIN_ARITY" "tuple requires at least two components" span
      let hints := match expected with | some (.tuple ts) => ts.map some | _ => args.map (fun _ => none)
      if hints.length != args.length then return ← error "TYPE_MISMATCH" "Tuple arity differs" span
      return .tuple (← (args.zip hints).mapM fun (arg, hint) => inferWith settings context arg hint)
    if name == "tuple_get" then
      let [source, .number _ index] := args | return ← error "BUILTIN_ARITY" "tuple_get requires tuple and literal index" span
      let .tuple items ← inferWith settings context source | error "TYPE_MISMATCH" "tuple_get requires tuple" span
      let some index := index.toNat? | return ← error "INVALID_TUPLE_INDEX" "Index must be natural literal" span
      let some item := items[index]? | return ← error "INVALID_TUPLE_INDEX" "Tuple index out of bounds" span
      return item
    if name == "lookup" then
      let [source, key] := args | return ← error "BUILTIN_ARITY" "lookup requires map and key" span
      let .map kt vt ← inferWith settings context source | error "TYPE_MISMATCH" "lookup requires map" span
      let _ ← inferWith settings context key (some kt)
      return .option vt
    if name == "entries" then
      let [source] := args | return ← error "BUILTIN_ARITY" "entries requires map" span
      let .map kt vt ← inferWith settings context source | error "TYPE_MISMATCH" "entries requires map" span
      return .list (.record "literal" [("key",kt),("value",vt)])
    if ["make_map", "join", "left_join"].contains name then
      let (left, right, lb, kb, rb, vb) ← match name, args with
        | "make_map", [source, .lambda _ lb key, .lambda _ rb value] => pure (source, source, lb, key, rb, value)
        | _, [left, right, .lambda _ lb key, .lambda _ rb value] => pure (left, right, lb, key, rb, value)
        | _, _ => error "BUILTIN_ARITY" "Indexed operator requires lists and two projections" span
      let .list lt ← inferWith settings context left | error "TYPE_MISMATCH" "Indexed source requires list" span
      let .list rt ← inferWith settings context right | error "TYPE_MISMATCH" "Indexed source requires list" span
      let lc ← bind context lb lt span
      let rc ← bind context rb rt span
      let kt ← inferWith settings lc kb
      unless keyType kt do error "INVALID_MAP_KEY_TYPE" "Key type is not admitted" span
      if name == "make_map" then
        let hint := match expected with | some (.map _ vt) => some vt | _ => none
        return .map kt (← inferWith settings rc vb hint)
      let other ← inferWith settings rc vb
      unless kt == other do error "TYPE_MISMATCH" "Join keys must have identical types" span
      return .list (.record "literal" [("left",lt),("right",if name == "left_join" then .option rt else rt)])
    if ["filter", "map", "sum", "sort_by", "group_by"].contains name then
      let [source, .lambda ls binder body] := args | return ← error "BUILTIN_ARITY" "Collection call needs list and lambda" span
      let .list itemTy ← inferWith settings context source | error "TYPE_MISMATCH" "Collection call needs list" span
      let nested ← bind context binder itemTy ls
      let hint := if name == "filter" then some boolTy else if name == "sum" then expected else none
      let bodyTy ← inferWith settings nested body hint
      if name == "group_by" then
        unless keyType bodyTy do error "INVALID_MAP_KEY_TYPE" "Group key type is not admitted" span
        return .map bodyTy (.list itemTy)
      if name == "sum" then
        unless numeric bodyTy do error "TYPE_MISMATCH" "sum body must be numeric" span
        return bodyTy
      if name == "sort_by" then
        unless scalar bodyTy || keyType bodyTy do error "TYPE_MISMATCH" "sort_by requires total-order key" span
      return if name == "map" then .list bodyTy else .list itemTy
    if name == "abs" then
      let [value] := args | return ← error "BUILTIN_ARITY" "abs requires one argument" span
      let ty ← inferWith settings context value expected
      unless numeric ty do error "TYPE_MISMATCH" "abs requires number" span
      return ty
    if name == "min" || name == "max" then
      let [a, b] := args | return ← error "BUILTIN_ARITY" "min/max require two arguments" span
      let ty ← inferWith settings context a expected
      let _ ← inferWith settings context b (some ty)
      unless numeric ty do error "TYPE_MISMATCH" "min/max require numbers" span
      return ty
    if name == "instant" then
      let [value] := args | return ← error "BUILTIN_ARITY" "instant requires one Text" span
      let _ ← inferWith settings context value (some textTy)
      if let .text _ text := value then
        let _ ← Instant.parse text |>.mapError (fun _ => (⟨"INVALID_INSTANT", "Invalid explicit-zone RFC3339 timestamp", span⟩ : Diagnostic))
        pure ()
      return instantTy
    if name == "add_calendar_months" then
      let [date, months, policy] := args | return ← error "BUILTIN_ARITY" "add_calendar_months requires Date, Nat, Text" span
      let _ ← inferWith settings context date (some dateTy)
      let _ ← inferWith settings context months (some (.atom "Nat"))
      let _ ← inferWith settings context policy (some textTy)
      if let .text _ mode := policy then
        unless ["clamp_day", "reject_invalid_day"].contains mode do
          error "CALENDAR_UNSUPPORTED_POLICY" mode span
      return dateTy
    if name == "in_period" then
      let [a, b] := args | return ← error "BUILTIN_ARITY" "in_period requires two arguments" span
      let _ ← inferWith settings context a (some dateTy)
      let _ ← inferWith settings context b (some periodTy)
      return boolTy
    if name == "is_calendar_quarter" then
      let [period] := args | return ← error "BUILTIN_ARITY" "is_calendar_quarter requires one Period" span
      let _ ← inferWith settings context period (some periodTy)
      return boolTy
    if name == "quantize" then
      let [a, b, .text _ mode] := args | return ← error "BUILTIN_ARITY" "quantize requires value, quantum, literal mode" span
      let ty ← inferWith settings context a expected
      let _ ← inferWith settings context b (some ty)
      unless numeric ty do error "TYPE_MISMATCH" "quantize requires number" span
      unless ["floor", "ceiling", "toward_zero", "half_even", "half_away_from_zero"].contains mode do
        error "UNSUPPORTED_ROUNDING_MODE" mode span
      return ty
    if name == "require_some" then
      let [value, .text _ _] := args | return ← error "BUILTIN_ARITY" "require_some needs option and literal diagnostic" span
      let .option ty ← inferWith settings context value (expected.map .option) | error "TYPE_MISMATCH" "require_some requires Option" span
      return ty
    error "UNSUPPORTED_BUILTIN" ("Unsupported builtin " ++ name) span

partial def resolveDefinitionsWith (settings : Inference) (context : Context) (declarations : List LocalDecl) : Except Diagnostic Context := do
  let pending := declarations.filter fun d => match d with | .define .. => true | _ => false
  let reserved := pending.filterMap fun d => match d with
    | .define _ name .. => some (name, Ty.atom "$pending")
    | _ => none
  resolvePassWith settings (reserved ++ context) pending pending.length none

partial def resolvePassWith (settings : Inference) (context : Context) (pending : List LocalDecl) (fuel : Nat)
    (lastError : Option Diagnostic) : Except Diagnostic Context := do
  if pending.isEmpty then return context
  if fuel == 0 then
    match lastError with
    | some d => if d.code == "UNRESOLVED_NAME" then
        error "UNRESOLVED_NAME_OR_CYCLE" d.message d.span else .error d
    | none => error "DEPENDENCY_CYCLE" "Cyclic definition dependencies"
  let mut context := context
  let mut next : List LocalDecl := []
  let mut failure := lastError
  for declaration in pending do
    if let .define span name annotation body _ := declaration then
      let expected ← annotation.mapM (parseTypeAt settings.lexical span)
      match inferWith settings context body expected with
      | .ok ty => context := (name, ty) :: context
      | .error d =>
        if d.code == "UNRESOLVED_NAME" || d.code == "UNRESOLVED_NAME_OR_CYCLE" then
          next := next ++ [declaration]
          failure := some d
        else throw d
  resolvePassWith settings context next (fuel - 1) failure

partial def checkLocalsWith (settings : Inference) (context : Context) (declarations : List LocalDecl) : Except Diagnostic Context := do
  let names := declarations.filterMap fun d => match d with | .define _ name .. => some name | _ => none
  if duplicate names || names.any (fun name => (lookup context name).isSome) then
    return ← error "DUPLICATE_NAME" "nested declaration duplicates or shadows a name"
  let resolved ← resolveDefinitionsWith settings context declarations
  for declaration in declarations do
    if let .require span condition code := declaration then
      if code.isEmpty then return ← error "INVALID_DIAGNOSTIC" "Assertion code is empty" span
      let _ ← inferWith settings resolved condition (some boolTy)
  pure resolved
end

def infer (context : Context) (expression : Expr) (expected : Option Ty := none) : Except Diagnostic Ty :=
  inferWith {} context expression expected

def checkLocals (context : Context) (declarations : List LocalDecl) : Except Diagnostic Context :=
  checkLocalsWith {} context declarations

def resolveDefinitions (context : Context) (declarations : List LocalDecl) : Except Diagnostic Context :=
  resolveDefinitionsWith {} context declarations

def check (schedule : Schedule) : Except Diagnostic Unit := do
  let settings ← inference schedule
  unless schedule.language == "spl/0.1-draft" && schedule.core == "spl-core/0.1-draft" &&
      schedule.schema == "spl-data/0.1-draft" do
    error "UNSUPPORTED_VERSION" "Unsupported surface, core or schema version" schedule.span
  let mut context : Context := []
  let mut locals : List LocalDecl := []
  let mut names : List String := []
  let mut openings : List (String × Ty) := []
  let mut aliases : List String := []
  for declaration in schedule.declarations do
    match declaration with
    | .input span name ty =>
      context ← bind context name (← parseTypeAt settings.lexical span ty) span
      names := name :: names
    | .opening span name ty alias =>
      let ty ← parseTypeAt settings.lexical span ty
      context ← bind context name ty span
      openings := (name, ty) :: openings
      names := name :: names
      aliases := alias :: aliases
    | .define span name ty body citation =>
      names := name :: names
      locals := locals ++ [.define span name ty body citation]
    | .require span condition code => locals := locals ++ [.require span condition code]
    | _ => pure ()
  if duplicate names then error "DUPLICATE_NAME" "Duplicate top-level binding" schedule.span
  if duplicate aliases then error "DUPLICATE_OPENING_ALIAS" "Opening aliases must be unique" schedule.span
  context ← checkLocalsWith settings context locals
  let mut closed : List String := []
  let mut emitted : List String := []
  for declaration in schedule.declarations do
    match declaration with
    | .closing span name body =>
      if closed.contains name then return ← error "INVALID_CLOSING_PORT" "Duplicate closing port" span
      let some ty := lookup openings name | return ← error "INVALID_CLOSING_PORT" "Closing has no opening" span
      let _ ← inferWith settings context body (some ty)
      closed := name :: closed
    | .emit span name body =>
      if emitted.contains name then return ← error "DUPLICATE_OUTPUT" "Duplicate emission name" span
      emitted := name :: emitted
      let ty ← inferWith settings context body
      if let .record _ fields := ty then
        if (lookup fields "payable").isSome then
          unless ["agreement_id", "participant_id", "period"].all (fun key => (lookup fields key).isSome) &&
              ((lookup fields "pool_id").isSome || (lookup fields "asset_id").isSome) do
            error "UNRESOLVED_OUTPUT_SCOPE" "Payable needs agreement, participant, title/pool and period" span
    | _ => pure ()
  unless openings.length == closed.length do error "MISSING_CLOSING_PORT" "Every opening requires closing port" schedule.span

end SPL.Check
