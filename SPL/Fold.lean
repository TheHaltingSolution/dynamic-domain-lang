import SPL.Runtime

/-! Finite strict left folds and explicit reject-on-tie ordering. These helpers
are executable semantics, with no new compiler-correctness claim. -/
namespace SPL

def appendValue (source item : Value) : Eval Value := do
  let source ← asList source
  checkCollectionSize (source.length + 1)
  return .seq (source ++ [item])

def concatValues (left right : Value) : Eval Value := do
  let left ← asList left
  let right ← asList right
  checkCollectionSize (left.length + right.length)
  return .seq (left ++ right)

abbrev FoldEntry := Value × Value × Value -- semantic key, declared identity, event

private def insertFoldEntry (entry : FoldEntry) : List FoldEntry → Eval (List FoldEntry)
  | [] => pure [entry]
  | head :: tail => do
    if (← compare entry.1 head.1) == .lt then pure (entry :: head :: tail)
    else pure (head :: (← insertFoldEntry entry tail))

/-- All identities/keys have already been evaluated before this validation phase.
Duplicate identity is independent of the semantic key, including distinct dates. -/
def orderFoldEntries (entries : List FoldEntry) (ties : String) : Eval (List FoldEntry) := do
  unless ties == "reject" do throw "UNRESOLVED_EVENT_ORDER"
  let mut identities : List Value := []
  for (_, identity, _) in entries do
    for prior in identities do
      if (← compare identity prior) == .eq then throw "DUPLICATE_EVENT_ID"
    identities := identity :: identities
  let mut ordered : List FoldEntry := []
  for entry in entries do ordered ← insertFoldEntry entry ordered
  for (a, b) in ordered.zip (ordered.drop 1) do
    if (← compare a.1 b.1) == .eq then throw "UNRESOLVED_EVENT_ORDER"
  return ordered

def foldValues (initial source : Value) (step : Value → Value → Eval Value) : Eval Value := do
  (← asList source).foldlM step initial

/-- Arguments are explicit thunks only for pure key/identity projections. The
caller evaluates the initial state before the source. No step runs until every
identity/key succeeds and duplicate identities and ordering ties are rejected. -/
def orderedFoldValues (initial source : Value) (key identity : Value → Eval Value)
    (ties : String) (step : Value → Value → Eval Value) : Eval Value := do
  let events ← asList source
  let identities ← events.mapM identity
  let keys ← events.mapM key
  let entries := (keys.zip (identities.zip events)).map fun (k, i, e) => (k, i, e)
  let ordered ← orderFoldEntries entries ties
  ordered.foldlM (fun state entry => step state entry.2.2) initial

end SPL
