import Lean.Data.Json.Parser
import Lean.Data.Json.Printer
import SPL.Runtime
import SPL.Check
import Std.Internal.Parsec

/-!
Standalone typed binding transport for generated SPL modules. JSON numbers,
nulls, duplicate keys, lone surrogate escapes and unknown fields are rejected.
Numbers use exact decimal strings or reduced integer-string fractions. Opaque
IDs use the deliberately narrower ASCII v0 profile; broader Unicode NFC IDs
require an explicit normalization implementation before this profile expands.
This decoder validates case-view shapes, not external contractual authority.
-/
namespace SPL.Bindings

open Lean
open Std.Internal.Parsec Std.Internal.Parsec.String

private def hex4 : Parser Nat := do
  let a ← Lean.Json.Parser.hexChar
  let b ← Lean.Json.Parser.hexChar
  let c ← Lean.Json.Parser.hexChar
  let d ← Lean.Json.Parser.hexChar
  pure (a.toNat * 4096 + b.toNat * 256 + c.toNat * 16 + d.toNat)

private def escaped : Parser Char := do
  match ← any with
  | '\\' => pure '\\'
  | '"' => pure '"'
  | '/' => pure '/'
  | 'b' => pure '\x08'
  | 'f' => pure '\x0c'
  | 'n' => pure '\n'
  | 'r' => pure '\r'
  | 't' => pure '\t'
  | 'u' =>
    let high ← hex4
    if high ≥ 0xD800 && high ≤ 0xDBFF then
      unless (← any) == '\\' do fail "INVALID_UNICODE_ESCAPE"
      unless (← any) == 'u' do fail "INVALID_UNICODE_ESCAPE"
      let low ← hex4
      unless low ≥ 0xDC00 && low ≤ 0xDFFF do fail "INVALID_UNICODE_ESCAPE"
      pure (Char.ofNat (0x10000 + (high - 0xD800) * 1024 + low - 0xDC00))
    else if high ≥ 0xDC00 && high ≤ 0xDFFF then fail "INVALID_UNICODE_ESCAPE"
    else pure (Char.ofNat high)
  | _ => fail "INVALID_JSON_ESCAPE"

private partial def stringBody (acc : String := "") : Parser String := do
  let char ← any
  if char == '"' then return acc
  if char == '\\' then return ← stringBody (acc.push (← escaped))
  if char.toNat < 32 then fail "INVALID_JSON_CONTROL_CHARACTER"
  stringBody (acc.push char)

mutual
  private partial def jsonValue : Parser Json := do
    let char ← peek!
    if char == '{' then
      skip; ws
      if (← peek!) == '}' then
        skip; ws
        return .obj ∅
      return .obj (← objectBody ∅)
    else if char == '[' then
      skip; ws
      if (← peek!) == ']' then
        skip; ws
        return .arr #[]
      return .arr (← arrayBody #[])
    else if char == '"' then
      skip
      let value ← stringBody
      ws
      return .str value
    else if char == 't' then
      skipString "true"; ws
      return .bool true
    else if char == 'f' then
      skipString "false"; ws
      return .bool false
    else if char == 'n' then fail "NULL_NOT_ALLOWED"
    else if char == '-' || char.isDigit then fail "JSON_NUMBER_NOT_ALLOWED"
    else fail "INVALID_JSON"

  private partial def objectBody (fields : Std.TreeMap.Raw String Json Ord.compare) : Parser (Std.TreeMap.Raw String Json Ord.compare) := do
    unless (← any) == '"' do fail "INVALID_JSON_OBJECT"
    let key ← stringBody
    if (fields.get? key).isSome then fail "DUPLICATE_JSON_KEY"
    ws
    unless (← any) == ':' do fail "INVALID_JSON_OBJECT"
    ws
    let value ← jsonValue
    let fields := fields.insert key value
    match ← any with
    | '}' => ws; pure fields
    | ',' => ws; objectBody fields
    | _ => fail "INVALID_JSON_OBJECT"

  private partial def arrayBody (items : Array Json) : Parser (Array Json) := do
    let value ← jsonValue
    let items := items.push value
    match ← any with
    | ']' => ws; pure items
    | ',' => ws; arrayBody items
    | _ => fail "INVALID_JSON_ARRAY"
end

def parseStrict (text : String) : Except String Json := do
  if text.startsWith "\ufeff" then throw "INVALID_UTF8"
  match Parser.run (do ws; let value ← jsonValue; eof; pure value) text with
  | .ok value => pure value
  | .error message =>
    let codes := ["DUPLICATE_JSON_KEY", "INVALID_UNICODE_ESCAPE", "NULL_NOT_ALLOWED", "JSON_NUMBER_NOT_ALLOWED"]
    let code := codes.find? fun code => (message.splitOn code).length > 1
    throw (code.getD "INVALID_JSON")

private def exactFields (value : Json) (names : List String) : Except String (List (String × Json)) := do
  let fields ← value.getObj? |>.mapError (fun _ => "EXPECTED_OBJECT")
  let fields := fields.toList
  unless fields.length == names.length && fields.all (fun (key, _) => names.contains key) do
    throw "UNKNOWN_OR_MISSING_FIELD"
  pure fields

private def str (value : Json) : Except String String :=
  value.getStr? |>.mapError (fun _ => "EXPECTED_STRING")

private def integerString (value : String) : Bool := Id.run do
  let unsigned := if value.startsWith "-" then value.drop 1 |>.toString else value
  if unsigned.isEmpty || !(unsigned.toList.all Char.isDigit) then return false
  if unsigned.length > 1 && unsigned.startsWith "0" then return false
  if value == "-0" then return false
  return true

private def decimalString (value : String) : Bool := Id.run do
  let unsigned := if value.startsWith "-" then value.drop 1 |>.toString else value
  match unsigned.splitOn "." with
  | [whole] => return integerString whole
  | [whole, fraction] => return integerString whole && !fraction.isEmpty && fraction.toList.all Char.isDigit
  | _ => return false

def exact (value : Json) : Except String Rat := do
  match value with
  | .str text =>
    unless decimalString text do throw "INVALID_EXACT_NUMBER"
    let negative := text.startsWith "-"
    let text := if negative then text.drop 1 |>.toString else text
    let parts := text.splitOn "."
    let numerator : Int := (String.join parts).toNat!
    let denominator := match parts with | [_, fraction] => 10 ^ fraction.length | _ => 1
    pure (mkRat (if negative then -numerator else numerator) denominator)
  | .obj _ =>
    let _ ← exactFields value ["numerator", "denominator"]
    let numerator ← str (← value.getObjVal? "numerator")
    let denominator ← str (← value.getObjVal? "denominator")
    unless integerString numerator && integerString denominator && !denominator.startsWith "-" do
      throw "INVALID_RATIONAL"
    let some n := numerator.toInt? | throw "INVALID_RATIONAL"
    let some d := denominator.toNat? | throw "INVALID_RATIONAL"
    if d == 0 then throw "INVALID_RATIONAL"
    if n.natAbs.gcd d != 1 then throw "NONCANONICAL_RATIONAL"
    pure (mkRat n d)
  | _ => throw "INVALID_EXACT_NUMBER"

partial def decodeWith (context : Dimensions.Meanings) (type : Check.Ty) (value : Json) : Except String Value := do
  match type with
  | .atom name =>
    if name == "Bool" then return .flag (← value.getBool? |>.mapError (fun _ => "EXPECTED_BOOL"))
    if ["Int", "Nat", "Ratio", "Rational"].contains name then
      let number ← exact value
      if (name == "Int" || name == "Nat") && number.den != 1 then throw "EXPECTED_INTEGER"
      if name == "Nat" && number < 0 then throw "NEGATIVE_NAT"
      return .num number
    let text ← str value
    if name == "Instant" then
      let seconds ← Instant.parse text
      return .instant seconds (← Instant.render seconds)
    if name == "Date" && !Check.dateValid text then throw "INVALID_DATE"
    if name.startsWith "Id:" then
      if text.isEmpty then throw "EMPTY_IDENTIFIER"
      if !text.toList.all (fun c => c.toNat < 128) then throw "UNSUPPORTED_IDENTIFIER_PROFILE"
    return .text text
  | .money currency =>
    let _ ← exactFields value ["value", "currency"]
    unless (← str (← value.getObjVal? "currency")) == currency do throw "UNSUPPORTED_CURRENCY"
    return .num (← exact (← value.getObjVal? "value"))
  | .quantity unit =>
    unless Dimensions.known context unit do throw "UNSUPPORTED_UNIT"
    let _ ← exactFields value ["value", "unit"] |>.mapError (fun _ => "INVALID_QUANTITY")
    let tag ← str (← value.getObjVal? "unit") |>.mapError (fun _ => "INVALID_QUANTITY")
    unless Dimensions.known context tag do throw "UNSUPPORTED_UNIT"
    unless tag == unit do throw "UNIT_MISMATCH"
    return .quantity unit (← exact (← value.getObjVal? "value"))
  | .rate unit currency =>
    unless Dimensions.known context unit do throw "UNSUPPORTED_UNIT"
    unless currency == "USD" do throw "UNSUPPORTED_CURRENCY"
    let _ ← exactFields value ["value", "per_unit", "currency"] |>.mapError (fun _ => "INVALID_RATE")
    let tag ← str (← value.getObjVal? "per_unit") |>.mapError (fun _ => "INVALID_RATE")
    let denomination ← str (← value.getObjVal? "currency") |>.mapError (fun _ => "INVALID_RATE")
    unless Dimensions.known context tag do throw "UNSUPPORTED_UNIT"
    unless tag == unit do throw "UNIT_MISMATCH"
    unless denomination == currency do throw "CURRENCY_MISMATCH"
    return .rate unit currency (← exact (← value.getObjVal? "value"))
  | .list type =>
    let values ← value.getArr? |>.mapError (fun _ => "EXPECTED_LIST")
    checkCollectionSize values.size
    let decoded ← values.toList.mapM (decodeWith context type)
    if let .record name _ := type then
      if ["AdvanceIssue", "ReserveMovement", "PaymentApplication"].contains name then
        let identities ← decoded.mapM fun item => do asText (← field item "event_id")
        unless identities.eraseDups.length == identities.length do throw "DUPLICATE_EVENT_ID"
    if let .record name _ := type then
      let keys := if name == "AdvanceIssue" then [("issue_id", "DUPLICATE_ISSUE_ID"), ("disbursement_id", "DUPLICATE_DISBURSEMENT_ID")]
        else if name == "AdvanceEvidence" || name == "ReserveEvidence" then [("evidence_id", "DUPLICATE_EVIDENCE_ID")]
        else if name == "ReserveVintage" then [("vintage_id", "DUPLICATE_VINTAGE_ID")] else []
      for (key, code) in keys do
        let ids ← decoded.mapM fun item => do asText (← field item key)
        unless ids.eraseDups.length == ids.length do throw code
    return .seq decoded
  | .option type =>
    let fields ← value.getObj? |>.mapError (fun _ => "EXPECTED_OPTION")
    if fields.toList.length != 1 then throw "EXPECTED_OPTION"
    if let some present := fields.get? "some" then return .present (← decodeWith context type present)
    if fields.get? "none" == some (.bool true) then return .absent
    throw "EXPECTED_OPTION"
  | .tuple types =>
    let values ← value.getArr? |>.mapError (fun _ => "EXPECTED_TUPLE")
    unless values.size == types.length do throw "TUPLE_ARITY"
    return .tuple (← (types.zip values.toList).mapM fun (ty,v) => decodeWith context ty v)
  | .map kt vt =>
    let entries ← value.getArr? |>.mapError (fun _ => "EXPECTED_MAP")
    checkCollectionSize entries.size
    let keyed ← entries.toList.mapM fun entry => do
      let _ ← exactFields entry ["key","value"]
      pure (← decodeWith context kt (← entry.getObjVal? "key"), ← entry.getObjVal? "value")
    for (key,_) in keyed do
      if (keyed.filter fun p => equal key p.1).length > 1 then throw "DUPLICATE_MAP_KEY"
    let rows ← keyed.mapM fun (key,value) => do pure (.obj [("key",key),("value",← decodeWith context vt value)])
    makeMap (.seq rows) (fun row => field row "key") (fun row => field row "value")
  | .record name fields =>
    let _ ← exactFields value (fields.map Prod.fst)
    let values ← fields.mapM fun (key, type) => do
      pure (key, ← decodeWith context type (← value.getObjVal? key))
    if name == "Period" then
      let start ← asText (← lookup values "start")
      let finish ← asText (← lookup values "end")
      unless start < finish do throw "INVALID_PERIOD"
    return .obj values

def decode (type : Check.Ty) (value : Json) : Except String Value := decodeWith {} type value

def decodeBindingsWith (owner : Dimensions.Admission) (context : Dimensions.Meanings) (types : List (String × Syntax.TypeExpr)) (value : Json) : Except String Env := do
  let _ ← exactFields value (types.map Prod.fst)
  types.mapM fun (name, type) => do
    let type ← Check.parseTypeWith owner type |>.mapError (fun diagnostic => diagnostic.code)
    pure (name, ← decodeWith context type (← value.getObjVal? name))

def decodeBindings (types : List (String × Syntax.TypeExpr)) (value : Json) : Except String Env :=
  decodeBindingsWith {} {} types value

def runMain (inputTypes openingTypes : List (String × Syntax.TypeExpr))
    (settle : Env → Env → Eval Settlement) (args : List String) : IO UInt32 := do
  let [path] := args | do
    IO.println (outcomeJson (.error "BINDING_FILE_ARGUMENT_REQUIRED")).compress
    return 1
  let result ← try
    let source ← IO.FS.readFile path
    pure (do
      let json ← parseStrict source
      let _ ← exactFields json ["inputs", "openings"]
      let inputs ← decodeBindings inputTypes (← json.getObjVal? "inputs")
      let openings ← decodeBindings openingTypes (← json.getObjVal? "openings")
      settle inputs openings)
    catch _ => pure (.error "BINDING_FILE_IO_ERROR")
  IO.println (outcomeJson result).compress
  return 0
def runMainWith (owner : Dimensions.Admission) (context : Dimensions.Meanings) (inputTypes openingTypes : List (String × Syntax.TypeExpr))
    (settle : Env → Env → Eval Settlement) (args : List String) : IO UInt32 := do
  let [path] := args | do
    IO.println (outcomeJson (.error "BINDING_FILE_ARGUMENT_REQUIRED")).compress
    return 1
  let result ← try
    let source ← IO.FS.readFile path
    pure (do
      let json ← parseStrict source
      let _ ← exactFields json ["inputs", "openings"]
      let inputs ← decodeBindingsWith owner context inputTypes (← json.getObjVal? "inputs")
      let openings ← decodeBindingsWith owner context openingTypes (← json.getObjVal? "openings")
      let settlement ← settle inputs openings
      for (_, value) in settlement.emissions ++ settlement.closing do validateValueWith context value
      pure settlement)
    catch _ => pure (.error "BINDING_FILE_IO_ERROR")
  IO.println (outcomeJson result).compress
  return 0

end SPL.Bindings
