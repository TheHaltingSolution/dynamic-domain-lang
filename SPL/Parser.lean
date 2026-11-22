import Lean
import SPL.Syntax

/-! Closed SPL lexer and recursive-descent parser. No host-language evaluation.
The executable parser is trusted frontend code; no parser-correctness theorem is
claimed. Resource exhaustion fails instead of returning a partial schedule. -/
namespace SPL.Parser
open SPL.Syntax

structure Token where
  kind : String := "eof"
  value : String := ""
  span : Span := {}
  deriving Repr, Inhabited

private def asciiLetter (c : Char) : Bool :=
  ('a' ≤ c && c ≤ 'z') || ('A' ≤ c && c ≤ 'Z') || c == '_'

private def digit (c : Char) : Bool := '0' ≤ c && c ≤ '9'

private def identChar (c : Char) : Bool := asciiLetter c || digit c

private def advance (s : Span) (chars : List Char) : Span :=
  chars.foldl (fun s c =>
    { start := s.start + 1
      stop := s.stop + 1
      line := if c == '\n' then s.line + 1 else s.line
      column := if c == '\n' then 1 else s.column + 1 }) s

private def positioned (s : Span) (chars : List Char) : Span :=
  { s with stop := s.start + chars.length }

private def hexDigit (c : Char) : Option Nat :=
  if '0' ≤ c && c ≤ '9' then some (c.toNat - '0'.toNat)
  else if 'a' ≤ c && c ≤ 'f' then some (c.toNat - 'a'.toNat + 10)
  else if 'A' ≤ c && c ≤ 'F' then some (c.toNat - 'A'.toNat + 10)
  else none

private def hexFour (a b c d : Char) : Option Nat := do
  return 4096 * (← hexDigit a) + 256 * (← hexDigit b) + 16 * (← hexDigit c) + (← hexDigit d)

-- Lean's general JSON reader replaces isolated surrogate escapes with U+FFFD.
-- SPL rejects that lossy normalization while accepting valid surrogate pairs.
private partial def validUnicodeEscapes : List Char → Bool
  | '\\' :: 'u' :: a :: b :: c :: d :: rest =>
    match hexFour a b c d with
    | none => false
    | some value =>
      if 0xD800 ≤ value && value ≤ 0xDBFF then
        match rest with
        | '\\' :: 'u' :: e :: f :: g :: h :: tail =>
          match hexFour e f g h with
          | some low => 0xDC00 ≤ low && low ≤ 0xDFFF && validUnicodeEscapes tail
          | none => false
        | _ => false
      else if 0xDC00 ≤ value && value ≤ 0xDFFF then false
      else validUnicodeEscapes rest
  | '\\' :: _ :: rest => validUnicodeEscapes rest
  | _ :: rest => validUnicodeEscapes rest
  | [] => true

private partial def stringChars (chars : List Char) (acc : List Char) :
    Except String (List Char × List Char) :=
  match chars with
  | [] => .error "Unterminated JSON string"
  | '\\' :: c :: rest => stringChars rest (c :: '\\' :: acc)
  | '"' :: rest => .ok (('"' :: acc).reverse, rest)
  | c :: rest => stringChars rest (c :: acc)

private partial def lexLoop (chars : List Char) (position : Span)
    (tokens : Array Token) : Except Diagnostic (Array Token) := do
  if tokens.size > 200000 then
    throw { code := "RESOURCE_LIMIT", message := "Source exceeds 200000 tokens", span := position }
  match chars with
  | [] => return tokens.push { span := position }
  | c :: rest =>
    if c == ' ' || c == '\t' || c == '\r' || c == '\n' then
      lexLoop rest (advance position [c]) tokens
    else if chars.take 2 == ['/', '/'] then
      let comment := chars.takeWhile (· != '\n')
      lexLoop (chars.drop comment.length) (advance position comment) tokens
    else if c == '"' then
      let (raw, remaining) ← match stringChars rest ['"'] with
        | .ok value => pure value
        | .error message => throw { code := "INVALID_STRING", message, span := position }
      unless validUnicodeEscapes raw do
        throw { code := "INVALID_STRING", message := "Invalid Unicode escape or unpaired surrogate", span := positioned position raw }
      let value ← match Lean.Json.parse (String.ofList raw) with
        | .ok (.str value) => pure value
        | _ => throw { code := "INVALID_STRING", message := "Expected a valid JSON string", span := positioned position raw }
      lexLoop remaining (advance position raw)
        (tokens.push { kind := "string", value, span := positioned position raw })
    else if asciiLetter c then
      let raw := chars.takeWhile identChar
      lexLoop (chars.drop raw.length) (advance position raw)
        (tokens.push { kind := "identifier", value := String.ofList raw, span := positioned position raw })
    else if digit c then
      let whole := chars.takeWhile digit
      let after := chars.drop whole.length
      let fractional := match after with
        | '.' :: next :: _ => if digit next then '.' :: ((after.drop 1).takeWhile digit) else []
        | _ => []
      let raw := whole ++ fractional
      lexLoop (chars.drop raw.length) (advance position raw)
        (tokens.push { kind := "number", value := String.ofList raw, span := positioned position raw })
    else
      let pair := String.ofList (chars.take 2)
      let raw := if ["==", "!=", "<=", ">=", "=>"].contains pair then chars.take 2 else [c]
      if raw.length == 1 && !("{}()[]:;,.<>+-*/=".toList.contains c) then
        throw { code := "INVALID_CHARACTER", message := s!"Unexpected character {c}", span := positioned position [c] }
      lexLoop (chars.drop raw.length) (advance position raw)
        (tokens.push { kind := "symbol", value := String.ofList raw, span := positioned position raw })

def lex (source : String) : Except Diagnostic (Array Token) := do
  if source.length > 1000000 then
    throw { code := "RESOURCE_LIMIT", message := "Source exceeds 1000000 Unicode scalars" }
  lexLoop source.toList {} #[]

private structure Cursor where
  tokens : Array Token
  offset : Nat := 0
  depth : Nat := 0
  deriving Inhabited

private abbrev P := StateT Cursor (Except Diagnostic)

private def peek : P Token := do
  let state ← get
  return state.tokens[state.offset]?.getD {}

private def takeToken : P Token := do
  let token ← peek
  modify fun s => { s with offset := s.offset + 1 }
  return token

private def fail (message : String) (code : String := "SYNTAX_ERROR") : P α := do
  throw { code, message, span := (← peek).span }

private def isToken (value : String) : P Bool := do
  let current ← peek
  return current.kind != "eof" && current.value == value

private def accept (value : String) : P Bool := do
  if ← isToken value then
    let _ ← takeToken
    return true
  return false

private def expect (value : String) : P Token := do
  unless ← isToken value do
    fail s!"Expected '{value}', found '{(← peek).value}'"
  takeToken

private def reserved : List String :=
  ["schedule", "language", "core", "schema", "input", "opening", "from", "define",
   "citing", "require", "else", "closing", "emit", "if", "then", "choose", "unique",
   "when", "otherwise", "for", "each", "in", "yield", "and", "or", "not", "true", "false", "date"]

private def identifier : P Token := do
  let token ← peek
  unless token.kind == "identifier" && !(reserved.contains token.value) do
    fail "Expected an identifier"
  takeToken

private def stringToken : P Token := do
  unless (← peek).kind == "string" do fail "Expected a JSON string"
  takeToken

private def endSpan (start : Span) : P Span := do
  let state ← get
  return { start with stop := (state.tokens[state.offset - 1]?.getD {}).span.stop }

private def enter : P Unit := do
  let state ← get
  if state.depth ≥ 128 then fail "Source expression nesting exceeds 128" "RESOURCE_LIMIT"
  modify fun s => { s with depth := s.depth + 1 }

private def leave : P Unit := modify fun s => { s with depth := s.depth - 1 }

private def precedence (level : Nat) : List String :=
  match level with
  | 0 => ["or"] | 1 => ["and"] | 2 => ["==", "!="]
  | 3 => ["<", "<=", ">", ">="] | 4 => ["+", "-"] | 5 => ["*", "/"] | _ => []

mutual
  private partial def typeExpr : P TypeExpr := do
    if ← accept "{" then
      let mut fields := []
      unless ← accept "}" do
        let name ← identifier
        let _ ← expect ":"
        fields := [(name.value, ← typeExpr)]
        while ← accept "," do
          let name ← identifier
          let _ ← expect ":"
          fields := fields ++ [(name.value, ← typeExpr)]
        let _ ← expect "}"
      return .record fields
    enter
    let name := (← identifier).value
    let mut args := []
    if ← accept "<" then
      args := [← typeExpr]
      while ← accept "," do args := args ++ [← typeExpr]
      let _ ← expect ">"
    leave
    return .named name args

  private partial def expression : P Expr := do
    enter
    let start := (← peek).span
    let result ← if ← accept "if" then do
      let condition ← expression
      let _ ← expect "then"
      let yes ← expression
      let _ ← expect "else"
      let no ← expression
      pure (.ite (← endSpan start) condition yes no)
    else if ← accept "choose" then do
      if (← isToken "priority") || (← isToken "registered") then
        let priority ← accept "priority"
        unless priority do
          let _ ← expect "registered"
          let _ ← expect "unique"
        let _ ← expect "{"
        let mut arms := []
        while ← accept "rule" do
          let id := (← stringToken).value
          let mut rank : Int := 0
          if priority then
            let _ ← expect "priority"
            let negative ← accept "-"
            let token ← takeToken
            unless token.kind == "number" do fail "Priority requires an integer"
            let some natural := token.value.toNat? | fail "Priority requires an integer"
            rank := if negative then -(Int.ofNat natural) else Int.ofNat natural
          let _ ← expect "when"
          let predicate ← expression
          let _ ← expect "=>"
          let body ← expression
          let _ ← expect ";"
          arms := arms ++ [(id, rank, predicate, body)]
        let mut fallback := none
        if ← accept "otherwise" then
          let id := (← stringToken).value
          let _ ← expect "=>"
          fallback := some (id, ← expression)
          let _ ← expect ";"
        let _ ← expect "}"
        return .selectRules (← endSpan start) priority arms fallback
      let _ ← expect "unique"
      let _ ← expect "{"
      let mut arms := []
      while ← accept "when" do
        let condition ← expression
        let _ ← expect "=>"
        let body ← expression
        let _ ← expect ";"
        arms := arms ++ [(condition, body)]
      if arms.isEmpty then fail "choose unique requires a when arm"
      let mut otherwise := none
      if ← accept "otherwise" then
        let _ ← expect "=>"
        otherwise := some (← expression)
        let _ ← expect ";"
      let _ ← expect "}"
      pure (.choose (← endSpan start) arms otherwise)
    else if (← isToken "fold") || (← isToken "ordered_fold") then do
      let ordered ← accept "ordered_fold"
      unless ordered do let _ ← expect "fold"; pure ()
      let source ← expression
      let _ ← expect "from"
      let initial ← expression
      let mut order := none
      if ordered then
        let _ ← expect "by"
        let keyBinder := (← identifier).value
        let _ ← expect "=>"
        let key ← expression
        let _ ← expect "identified"
        let _ ← expect "by"
        let idBinder := (← identifier).value
        let _ ← expect "=>"
        let identity ← expression
        unless ← accept "ties" do fail "Ordered fold requires an explicit tie policy" "UNRESOLVED_EVENT_ORDER"
        let ties := (← stringToken).value
        order := some (keyBinder, key, idBinder, identity, ties)
      let _ ← expect "with"
      let state := (← identifier).value
      let _ ← expect ","
      let event := (← identifier).value
      let _ ← expect "{"
      let mut declarations := []
      while !(← isToken "yield") do declarations := declarations ++ [← localDeclaration]
      let _ ← expect "yield"
      let body ← expression
      let _ ← expect ";"
      let _ ← expect "}"
      pure (.fold (← endSpan start) source initial state event order declarations body)
    else if ← accept "for" then do
      let _ ← expect "each"
      let name := (← identifier).value
      let _ ← expect "in"
      let source ← expression
      let _ ← expect "{"
      let mut declarations := []
      while !(← isToken "yield") do
        declarations := declarations ++ [← localDeclaration]
      let _ ← expect "yield"
      let yielded ← expression
      let _ ← expect ";"
      let _ ← expect "}"
      pure (.forEach (← endSpan start) name source declarations yielded)
    else binary 0
    leave
    return result

  private partial def binary (level : Nat) : P Expr := do
    if level ≥ 6 then return ← unary
    let start := (← peek).span
    let mut result ← binary (level + 1)
    let mut count := 0
    while (precedence level).contains (← peek).value do
      if (level == 2 || level == 3) && count > 0 then
        fail "Equality and comparison operators cannot be chained"
      let op := (← takeToken).value
      let right ← binary (level + 1)
      result := .binary (← endSpan start) op result right
      count := count + 1
    return result

  private partial def unary : P Expr := do
    if (← isToken "-") || (← isToken "not") then
      let start ← takeToken
      let operand ← postfixExpr
      return .unary (← endSpan start.span) start.value operand
    postfixExpr

  private partial def postfixExpr : P Expr := do
    let start := (← peek).span
    let mut result ← atom
    let mut running := true
    while running do
      if ← accept "." then
        let name := (← identifier).value
        result := .field (← endSpan start) result name
      else if ← accept "(" then
        let name ← match result with
          | .name _ name => pure name
          | _ => fail "Only a named published built-in may be called" "UNSUPPORTED_CALL"
        let mut args := []
        unless ← isToken ")" do
          args := [← argument]
          while ← accept "," do args := args ++ [← argument]
        let _ ← expect ")"
        result := .call (← endSpan start) name args
      else running := false
    return result

  private partial def argument : P Expr := do
    let state ← get
    if (← peek).kind == "identifier" && (state.tokens[state.offset + 1]?.getD {}).value == "=>" then
      let start ← identifier
      let _ ← expect "=>"
      let body ← expression
      return .lambda (← endSpan start.span) start.value body
    expression

  private partial def atom : P Expr := do
    let start ← peek
    if start.kind == "number" then
      let _ ← takeToken
      return .number start.span start.value
    if start.kind == "string" then
      let _ ← takeToken
      return .text start.span start.value
    if ← accept "true" then return .boolean start.span true
    if ← accept "false" then return .boolean start.span false
    if ← accept "date" then
      let value := (← stringToken).value
      return .date (← endSpan start.span) value
    if ← accept "USD" then
      unless (← peek).kind == "number" do fail "Money literal requires unsigned decimal"
      let value := (← takeToken).value
      return .money (← endSpan start.span) "USD" value
    if ← accept "(" then
      let result ← expression
      let _ ← expect ")"
      return result
    if ← accept "[" then
      let mut items := []
      unless ← isToken "]" do
        items := [← expression]
        while ← accept "," do items := items ++ [← expression]
      let _ ← expect "]"
      return .list (← endSpan start.span) items
    if ← accept "{" then
      let mut fields := []
      unless ← isToken "}" do
        let mut running := true
        while running do
          let name := (← identifier).value
          if fields.any (fun pair : String × Expr => pair.1 == name) then
            fail s!"Duplicate record field '{name}'" "DUPLICATE_FIELD"
          let _ ← expect ":"
          fields := fields ++ [(name, ← expression)]
          running ← accept ","
      let _ ← expect "}"
      return .record (← endSpan start.span) fields
    if start.kind == "identifier" && !(reserved.contains start.value) then
      let _ ← takeToken
      return .name start.span start.value
    fail "Expected an expression"

  private partial def localDeclaration : P LocalDecl := do
    let start ← peek
    if start.value == "require" then
      let _ ← takeToken
      let condition ← expression
      let _ ← expect "else"
      let code := (← stringToken).value
      let _ ← expect ";"
      return .require (← endSpan start.span) condition code
    if start.value == "define" then
      let _ ← takeToken
      let name := (← identifier).value
      let mut type := none
      if ← accept ":" then type := some (← typeExpr)
      let _ ← expect "="
      let value ← expression
      let mut citation := none
      if ← accept "citing" then citation := some (← stringToken).value
      let _ ← expect ";"
      return .define (← endSpan start.span) name type value citation
    fail "Expected local define or require" "UNSUPPORTED_DECLARATION"
end

private def declaration : P Decl := do
  let start ← peek
  if ← accept "input" then
    let name := (← identifier).value
    let _ ← expect ":"
    let type ← typeExpr
    let _ ← expect ";"
    return .input (← endSpan start.span) name type
  if ← accept "opening" then
    let name := (← identifier).value
    let _ ← expect ":"
    let type ← typeExpr
    let _ ← expect "from"
    let alias := (← stringToken).value
    let _ ← expect ";"
    return .opening (← endSpan start.span) name type alias
  if (← isToken "define") || (← isToken "require") then
    match ← localDeclaration with
    | .define span name type value citation => return .define span name type value citation
    | .require span condition code => return .require span condition code
  if ← accept "closing" then
    let name := (← identifier).value
    let _ ← expect "="
    let value ← expression
    let _ ← expect ";"
    return .closing (← endSpan start.span) name value
  if ← accept "emit" then
    let name := (← stringToken).value
    let _ ← expect "="
    let value ← expression
    let _ ← expect ";"
    return .emit (← endSpan start.span) name value
  fail "Expected a supported declaration" "UNSUPPORTED_DECLARATION"

private def schedule : P Schedule := do
  let start ← expect "schedule"
  let name := (← identifier).value
  let _ ← expect "language"
  let language := (← stringToken).value
  let _ ← expect "core"
  let core := (← stringToken).value
  let _ ← expect "schema"
  let schema := (← stringToken).value
  let _ ← expect "{"
  let mut declarations := []
  while !(← isToken "}") do
    declarations := declarations ++ [← declaration]
  let _ ← expect "}"
  unless (← peek).kind == "eof" do fail "Trailing source after schedule" "TRAILING_CONTENT"
  return { name, language, core, schema, declarations, span := ← endSpan start.span }

def parse (source : String) : Except Diagnostic Schedule := do
  let tokens ← lex source
  let (result, _) ← schedule.run { tokens }
  return result

end SPL.Parser
