import SPL.Parser

/-! Controlled readable SPL, version spl-readable/0.1-dev. Supporting declarations
are explicit source, not built-in agreement policy. Expansion uses the existing
closed parser/checker boundary and retains authored statement spans. This trusted
frontend has no parser-correctness theorem. -/
namespace SPL.Readable
open SPL.Syntax

structure Expansion where
  source : String
  origins : Array Span
  deriving Repr

private structure Line where
  text : String
  indent : Nat
  span : Span
  deriving Inhabited

private def strip (s : String) : String := s.trimAscii.toString
private def cut (s : String) (n : Nat) : String := String.ofList (s.toList.drop n)
private def unlast (s : String) : String := String.ofList (s.toList.take (s.length - 1))
private def middle (s : String) (n : Nat) : String := unlast (cut s n)

private def failure (line : Line) (message : String)
    (code : String := "READABLE_SYNTAX_ERROR") : Except Diagnostic α :=
  .error { code, message, span := line.span }

private def sourceLines (source : String) : Except Diagnostic (Array Line) := do
  if source.length > 1000000 then
    throw { code := "RESOURCE_LIMIT", message := "Source exceeds 1000000 Unicode scalars" }
  let mut lines := #[]
  let mut offset := 0
  let mut number := 1
  for raw in source.splitOn "\n" do
    let clean := if raw.endsWith "\r" then unlast raw else raw
    let indent := (clean.toList.takeWhile (· == ' ')).length
    let line : Line := { text := strip clean, indent := indent, span := { start := offset + indent, stop := offset + clean.length, line := number, column := indent + 1 } }
    if clean.contains '\t' then
      failure line "Use spaces, not tabs" "READABLE_INDENTATION"
    if !line.text.isEmpty && !line.text.startsWith "//" then
      lines := lines.push line
    offset := offset + raw.length + 1
    number := number + 1
  return lines

private def identifier (text : String) : Bool :=
  let letter := fun c => ('a' ≤ c && c ≤ 'z') || ('A' ≤ c && c ≤ 'Z') || c == '_'
  match text.toList with
  | [] => false
  | first :: rest => letter first && rest.all (fun c => letter c || ('0' ≤ c && c ≤ '9'))

private structure Iteration where
  phrase : String
  item : String
  collection : String
  target : String
  deriving Inhabited

private structure Config where
  aliases : List (String × String) := []
  iterations : List Iteration := []
  fields : List (String × String) := []
  declarations : Array (String × Span) := #[]
  settlements : List (String × String) := []
  schedule : Option String := none
  metadata : Option String := none
  deriving Inhabited

private def quoted (line : Line) (text : String) : Except Diagnostic (String × String) := do
  let tokens ← match SPL.Parser.lex text with
    | .ok ts => pure ts
    | .error d => throw { d with span := line.span }
  let token := tokens[0]?.getD default
  unless token.kind == "string" do failure line "Expected a quoted binding phrase"
  return (token.value, strip (cut text token.span.stop))

private def parseBindings (lines : Array Line) : Except Diagnostic Config := do
  let mut config : Config := {}
  for line in lines do
    let text := line.text
    if text.startsWith "Schedule " && text.endsWith "." then
      if config.schedule.isSome then failure line "Duplicate Schedule declaration"
      let name := middle text 9
      unless identifier name do failure line "Schedule must be a core identifier"
      config := { config with schedule := some name }
    else if text.startsWith "Using " && text.endsWith "." then
      if config.metadata.isSome then failure line "Duplicate Using declaration"
      config := { config with metadata := some (middle text 6) }
    else if text.startsWith "Bind " && text.endsWith "." then
      let (phrase, tail) ← quoted line (middle text 5)
      unless tail.startsWith "to " do failure line "Expected Bind quoted-phrase to core-expression."
      if phrase.isEmpty || config.aliases.any (fun p => p.1 == phrase) then
        failure line "Binding phrases must be nonempty and unique"
      config := { config with aliases := config.aliases ++ [(phrase, cut tail 3)] }
    else if text.startsWith "Settle " && text.endsWith "." then
      let (phrase, tail) ← quoted line (middle text 7)
      unless tail.startsWith "with " do failure line "Expected Settle quoted-party with participant-expression."
      if phrase.isEmpty || config.settlements.any (fun p => p.1 == phrase) then
        failure line "Settlement labels must be nonempty and unique"
      config := { config with settlements := config.settlements ++ [(phrase, cut tail 5)] }
    else if text.startsWith "Field " && text.endsWith "." then
      let (phrase, tail) ← quoted line (middle text 6)
      unless tail.startsWith "as " && identifier (cut tail 3) do
        failure line "Expected Field quoted-phrase as record_field."
      if config.fields.any (fun p => p.1 == phrase) then failure line "Duplicate report field phrase"
      config := { config with fields := config.fields ++ [(phrase, cut tail 3)] }
    else if text.startsWith "Iterate " && text.endsWith "." then
      let (phrase, tail) ← quoted line (middle text 8)
      unless tail.startsWith "as " do failure line "Expected Iterate phrase as item in collection into result."
      let parts := (cut tail 3).splitOn " in "
      unless parts.length == 2 do failure line "Iteration requires one item and collection"
      let item := parts[0]!
      let rest := parts[1]!.splitOn " into "
      unless rest.length == 2 && identifier item && identifier rest[1]! do
        failure line "Iteration requires identifier item and result"
      if phrase.isEmpty || config.iterations.any (fun p => p.phrase == phrase) then
        failure line "Iteration phrases must be nonempty and unique"
      config := { config with iterations := config.iterations ++
        [{ phrase, item, collection := rest[0]!, target := rest[1]! }] }
    else if text.endsWith ";" && ["input ", "opening ", "require ", "define "].any (fun key => text.startsWith key) then
      config := { config with declarations := config.declarations.push (text, line.span) }
    else
      failure line "Unsupported supporting declaration"
  return config

private def word (c : Char) : Bool :=
  ('a' ≤ c && c ≤ 'z') || ('A' ≤ c && c ≤ 'Z') || ('0' ≤ c && c ≤ '9') || c == '_'

-- One longest-match pass; aliases never recursively substitute aliases and never
-- rewrite JSON string contents. A phrase must meet an identifier boundary.
private partial def replaceNames (aliases : List (String × String))
    (chars : List Char) (previous : Option Char := none) (quotedString : Bool := false)
    (escaped : Bool := false) : List Char :=
  match chars with
  | [] => []
  | c :: rest =>
    if quotedString then
      c :: replaceNames aliases rest (some c) (escaped || c != '"') (!escaped && c == '\\')
    else if c == '"' then
      c :: replaceNames aliases rest (some c) true false
    else
      let found := aliases.find? fun (phrase, _) =>
        let key := phrase.toList
        chars.take key.length == key && !(previous.any word) &&
          !((chars[key.length]?).any word)
      match found with
      | some (phrase, value) => value.toList ++
        replaceNames aliases (chars.drop phrase.length) (phrase.toList.getLast?) false false
      | none => c :: replaceNames aliases rest (some c) false false

private def resolve (config : Config) (s : String) (grouped : Bool := false) : String :=
  let aliases := config.aliases.mergeSort (fun a b => a.1.length ≥ b.1.length)
  let aliases := if grouped then aliases.map (fun (k, v) => (k, "(" ++ v ++ ")")) else aliases
  String.ofList (replaceNames aliases s.toList)

private partial def percentages : List Char → List Char
  | [] => []
  | '"' :: rest =>
    let rec quotedPart : List Char → List Char × List Char
      | [] => ([], [])
      | '\\' :: c :: tail => let (a, b) := quotedPart tail; ('\\' :: c :: a, b)
      | '"' :: tail => (['"'], tail)
      | c :: tail => let (a, b) := quotedPart tail; (c :: a, b)
    let (inside, tail) := quotedPart rest
    '"' :: inside ++ percentages tail
  | c :: rest =>
    if '0' ≤ c && c ≤ '9' then
      let whole := (c :: rest).takeWhile (fun x => '0' ≤ x && x ≤ '9')
      let tail := (c :: rest).drop whole.length
      let frac := match tail with
        | '.' :: next :: _ => if '0' ≤ next && next ≤ '9' then
            '.' :: ((tail.drop 1).takeWhile (fun x => '0' ≤ x && x ≤ '9')) else []
        | _ => []
      let number := whole ++ frac
      let after := (c :: rest).drop number.length
      match after with
      | '%' :: remaining => ['('] ++ number ++ (if frac.isEmpty then ".0".toList else []) ++ " / 100)".toList ++ percentages remaining
      | _ => number ++ percentages after
    else c :: percentages rest

-- Rewrite financial operators outside quoted strings, after name resolution.
private partial def operators (chars : List Char) (inside : Bool := false)
    (escaped : Bool := false) : List Char :=
  match chars with
  | [] => []
  | c :: rest =>
    if inside then c :: operators rest (escaped || c != '"') (!escaped && c == '\\')
    else if c == '"' then c :: operators rest true false
    else
      match [(" less ", " - "), (" plus ", " + "), (" of ", " * ")].find?
          (fun p => chars.take p.1.length == p.1.toList) with
      | some (a, b) => b.toList ++ operators (chars.drop a.length)
      | none => c :: operators rest

private partial def expression (config : Config) (text : String) : String :=
  let text := resolve config text true
  let low := text.startsWith "the lesser of "
  let high := text.startsWith "the greater of "
  if low || high then
    let parts := (cut text (if low then 14 else 15)).splitOn " and "
    if parts.length == 2 then
      (if low then "min(" else "max(") ++ expression config parts[0]! ++ ", " ++
        expression config parts[1]! ++ ")"
    else text
  else String.ofList (operators (percentages text.toList))

private def report (config : Config) (line : Line) (text : String) : Except Diagnostic String := do
  if !(text.contains ',') || text.startsWith "{" then return expression config text
  let parts := (text.splitOn ",").map strip
  let values ← parts.mapM fun phrase => do
    let field ← match config.fields.find? (fun p => p.1 == phrase) with
      | some p => pure p.2
      | none => failure line "Every report-list name needs an explicit Field binding"
    return field ++ ": " ++ expression config phrase
  return "{ " ++ String.intercalate ", " values ++ " }"

private structure Definition where
  target : String
  value : String
  citation : String
  line : Line
  deriving Inhabited

private def definition (config : Config) (line : Line) : Except Diagnostic Definition := do
  unless line.text.endsWith "." do failure line "Readable statements must end with a period"
  let text := unlast line.text
  let isParts := text.splitOn " is "
  let parts := if isParts.length == 2 then isParts else text.splitOn " are "
  unless parts.length == 2 do failure line "Expected name is/are expression."
  let target := resolve config parts[0]!
  unless identifier target do failure line "Definition name needs an explicit identifier binding"
  let cited := parts[1]!.splitOn " citing "
  unless cited.length ≤ 2 do failure line "Only one citation is permitted per definition"
  return { target := target, value := expression config cited[0]!, line := line, citation := if cited.length == 2 then " citing " ++ cited[1]! else "" }

private def branch (config : Config) (rules : Array Line) (index parent : Nat) :
    Except Diagnostic (Array Definition × Nat) := do
  let mut values := #[]
  let mut index := index
  let level := (rules[index]?.getD default).indent
  while index < rules.size && rules[index]!.indent > parent do
    unless rules[index]!.indent == level do
      failure rules[index]! "Statements in a block must share indentation" "READABLE_INDENTATION"
    values := values.push (← definition config rules[index]!)
    index := index + 1
  if values.isEmpty then failure (rules[index - 1]?.getD default) "Conditional branch must define at least one value"
  return (values, index)

private structure CompileState where
  output : Array (String × Span) := #[]
  policies : List String := []
  deriving Inhabited

private abbrev C := StateT CompileState (Except Diagnostic)
private def emit (text : String) (line : Line) : C Unit :=
  modify fun s => { s with output := s.output.push (text, line.span) }
private def liftResult (value : Except Diagnostic α) : C α :=
  match value with
  | .ok value => pure value
  | .error error => throw error
private def failAt (line : Line) (message : String) : C α := liftResult (failure line message)

private def policyIdentity (value : String) : Bool :=
  let alnum := fun c => ('a' ≤ c && c ≤ 'z') || ('A' ≤ c && c ≤ 'Z') || ('0' ≤ c && c ≤ '9')
  let parts := value.splitOn "@"
  parts.length == 2 && parts.all (fun part => !part.isEmpty && part.toList.head?.any alnum) &&
    parts[0]!.toList.all (fun c => alnum c || c == '.' || c == '_' || c == '/' || c == '-') &&
    parts[1]!.toList.all (fun c => alnum c || c == '.' || c == '_' || c == '-')

private partial def compileBlock (config : Config) (rules : Array Line)
    (index : Nat) (parent : Option Nat := none) (depth : Nat := 0) : C Nat := do
  if depth > 64 then
    liftResult (failure (rules[index]?.getD default) "Readable block nesting exceeds 64" "RESOURCE_LIMIT")
  let mut index := index
  let level := (rules[index]?.getD default).indent
  while index < rules.size && (parent.isNone || rules[index]!.indent > parent.getD 0) do
    let line := rules[index]!
    unless line.indent == level do
      liftResult (failure line "Statements in a block must share indentation" "READABLE_INDENTATION")
    let text := line.text
    if text.startsWith "Incorporate " then
      unless text.startsWith "Incorporate policy " && text.endsWith "." && line.indent == 0 do
        failAt line "Expected top-level Incorporate policy quoted-identifier@version."
      let (identity, tail) ← liftResult (quoted line (middle text 19))
      unless tail.isEmpty && policyIdentity identity do
        failAt line "Policy identity must be an explicit identifier@version"
      let policies := (← get).policies
      if policies.contains identity then failAt line "Duplicate incorporated policy"
      -- A typed provenance declaration, retained in syntax/IR with its authored
      -- span. Canonical runs separately resolve/pin policy content and validate
      -- implementation consistency; this frontend does not read external files.
      emit s!"define incorporated_policy_{policies.length} : Text = \"{identity}\";" line
      modify fun state => { state with policies := policies ++ [identity] }
      index := index + 1
    else if text.startsWith "For each " && text.endsWith ":" then
      let phrase := middle text 9
      let iteration ← match config.iterations.find? (fun p => p.phrase == phrase) with
        | some p => pure p
        | none => failAt line "For each requires an explicit Iterate binding"
      emit (s!"define {iteration.target} = for each {iteration.item} in {iteration.collection} " ++ "{") line
      let next ← compileBlock config rules (index + 1) (some line.indent) (depth + 1)
      unless next > index + 1 && (rules[next - 1]!.text.startsWith "Report by ") do
        failAt line "For each must end with Report by label: expression."
      emit "};" line
      index := next
    else if text.startsWith "For settlement with " && text.endsWith ":" then
      let party := middle text 20
      let participant ← match config.settlements.find? (fun p => p.1 == party) with
        | some p => pure p.2
        | none => failAt line "Settlement party requires an explicit Settle binding"
      emit ("define settlement_participant : Id<Participant> = " ++ participant ++ ";") line
      let next ← compileBlock config rules (index + 1) (some line.indent) (depth + 1)
      unless next > index + 1 do failAt line "Settlement block must contain statements"
      index := next
    else if text.startsWith "If " && text.endsWith ":" then
      let (yes, next) ← liftResult (branch config rules (index + 1) line.indent)
      unless next < rules.size && rules[next]!.text == "Otherwise:" && rules[next]!.indent == line.indent do
        failAt line "If requires Otherwise: at the same indentation"
      let (no, after) ← liftResult (branch config rules (next + 1) line.indent)
      unless yes.toList.map (·.target) == no.toList.map (·.target) &&
          (yes.toList.map (·.target)).eraseDups.length == yes.size do
        failAt line "Both branches must define the same unique bound names in the same order"
      for i in [:yes.size] do
        let a := yes[i]!
        let b := no[i]!
        unless a.citation == b.citation do failAt line "Merged branch citations must agree"
        emit s!"define {a.target} = if {expression config (middle text 3)} then (" line
        emit a.value a.line
        emit ") else (" rules[next]!
        emit b.value b.line
        emit (")" ++ a.citation ++ ";") a.line
      index := after
    else
      if text.startsWith "Account for each " && text.endsWith "." then
        let phrase := middle text 17
        unless phrase == "calendar quarter" && config.aliases.any (fun p => p.1 == phrase) do
          failAt line "Account for each calendar quarter requires an explicit calendar quarter binding"
        emit ("define accounting_period = " ++ expression config phrase ++ ";") line
        emit "require is_calendar_quarter(accounting_period) else \"READABLE_CALENDAR_QUARTER_REQUIRED\";" line
      else if text.startsWith "Require " && text.endsWith "." then
        let parts := (middle text 8).splitOn " or fail "
        unless parts.length == 2 do failAt line "Require needs or fail quoted-diagnostic."
        emit ("require " ++ expression config parts[0]! ++ " else " ++ parts[1]! ++ ";") line
      else if text.startsWith "Report by " && text.endsWith "." then
        let parts := (unlast text).splitOn ": "
        unless parts.length == 2 do failAt line "Report by needs a label and expression"
        emit ("yield " ++ (← liftResult (report config line parts[1]!)) ++ ";") line
      else if text.startsWith "Report " && text.endsWith "." then
        let parts := (middle text 7).splitOn ": "
        unless parts.length == 2 do failAt line "Report needs quoted-port: expression."
        emit ("emit " ++ parts[0]! ++ " = " ++ (← liftResult (report config line parts[1]!)) ++ ";") line
      else if text.startsWith "Closing " then
        let value ← liftResult (definition config { line with text := cut text 8 })
        unless value.citation.isEmpty do failAt line "Closing citation belongs on the movement definition"
        emit s!"closing {value.target} = {value.value};" line
      else if text == "Otherwise:" then failAt line "Otherwise without If"
      else
        let value ← liftResult (definition config line)
        emit s!"define {value.target} = {value.value}{value.citation};" line
      index := index + 1
  return index

def isReadable (source : String) : Bool :=
  (strip source).startsWith "Participation Schedule for "

def expand (source : String) : Except Diagnostic Expansion := do
  let lines ← sourceLines source
  let title := lines[0]?.getD default
  unless title.text.startsWith "Participation Schedule for " do
    failure title "Expected Participation Schedule for title"
  let footers := (List.range lines.size).filter fun i => lines[i]!.text == "Bindings:"
  unless footers.length == 1 do failure title "Exactly one explicit Bindings: footer is required"
  let split := footers[0]!
  let config ← parseBindings (lines.toList.drop (split + 1)).toArray
  let name ← match config.schedule with
    | some v => pure v
    | none => failure lines[split]! "Bindings must explicitly declare Schedule and Using versions"
  let metadata ← match config.metadata with
    | some v => pure v
    | none => failure lines[split]! "Bindings must explicitly declare Schedule and Using versions"
  let rules := ((lines.toList.take split).drop 1).toArray
  if rules.isEmpty then failure title "At least one readable rule is required"
  unless rules[0]!.indent == 0 do failure rules[0]! "Top-level rules must start in column one" "READABLE_INDENTATION"
  let initial := #[((s!"schedule {name} {metadata} " ++ "{"), title.span)] ++ config.declarations
  let (_, state) ← (compileBlock config rules 0).run { output := initial }
  let output := state.output.push ("}", (lines[lines.size - 1]?.getD default).span)
  return { source := String.intercalate "\n" (output.toList.map (·.1)), origins := output.map (·.2) }

private def remapSpan (origins : Array Span) (span : Span) : Span :=
  origins[span.line - 1]?.getD (origins[origins.size - 1]?.getD default)

mutual
private partial def remapExpr (origins : Array Span) (e : Expr) : Expr :=
  let s := remapSpan origins e.span
  match e with
  | .number _ v => .number s v
  | .money _ c v => .money s c v
  | .boolean _ v => .boolean s v
  | .text _ v => .text s v
  | .date _ v => .date s v
  | .name _ v => .name s v
  | .unary _ op a => .unary s op (remapExpr origins a)
  | .binary _ op a b => .binary s op (remapExpr origins a) (remapExpr origins b)
  | .field _ a key => .field s (remapExpr origins a) key
  | .ite _ a b c => .ite s (remapExpr origins a) (remapExpr origins b) (remapExpr origins c)
  | .call _ name args => .call s name (args.map (remapExpr origins))
  | .lambda _ name body => .lambda s name (remapExpr origins body)
  | .record _ fields => .record s (fields.map fun (k, v) => (k, remapExpr origins v))
  | .list _ items => .list s (items.map (remapExpr origins))
  | .choose _ branches fallback => .choose s
      (branches.map fun (a, b) => (remapExpr origins a, remapExpr origins b)) (fallback.map (remapExpr origins))
  | .selectRules _ priority arms fallback => .selectRules s priority
      (arms.map fun (id, rank, p, b) => (id, rank, remapExpr origins p, remapExpr origins b))
      (fallback.map fun (id, b) => (id, remapExpr origins b))
  | .forEach _ item source locals result => .forEach s item (remapExpr origins source)
      (locals.map (remapLocal origins)) (remapExpr origins result)
  | .fold _ source initial state event order locals result => .fold s
      (remapExpr origins source) (remapExpr origins initial) state event
      (order.map fun (kb, key, ib, identity, ties) => (kb, remapExpr origins key, ib, remapExpr origins identity, ties))
      (locals.map (remapLocal origins)) (remapExpr origins result)
  | .apply _ label parameters args result locals body => .apply s label parameters
      (args.map (remapExpr origins)) result (locals.map (remapLocal origins)) (remapExpr origins body)
private partial def remapLocal (origins : Array Span) : LocalDecl → LocalDecl
  | .define span name ty e cite => .define (remapSpan origins span) name ty (remapExpr origins e) cite
  | .require span e code => .require (remapSpan origins span) (remapExpr origins e) code
end

private def remapDecl (origins : Array Span) : Decl → Decl
  | .input span name ty => .input (remapSpan origins span) name ty
  | .opening span name ty key => .opening (remapSpan origins span) name ty key
  | .define span name ty e cite => .define (remapSpan origins span) name ty (remapExpr origins e) cite
  | .require span e code => .require (remapSpan origins span) (remapExpr origins e) code
  | .closing span name e => .closing (remapSpan origins span) name (remapExpr origins e)
  | .emit span port e => .emit (remapSpan origins span) port (remapExpr origins e)

def parse (source : String) : Except Diagnostic Schedule := do
  let expansion ← expand source
  match SPL.Parser.parse expansion.source with
  | .error diagnostic => throw { diagnostic with span := remapSpan expansion.origins diagnostic.span }
  | .ok schedule => return { schedule with span := { start := 0, stop := source.length, line := 1, column := 1 }, declarations := schedule.declarations.map (remapDecl expansion.origins) }

end SPL.Readable
