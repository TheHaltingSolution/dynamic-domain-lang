import SPL.ValidateIR
import SPL.Emit

open SPL

private def m (id : Nat) (ty : IR.Ty) : IR.Meta := { id, ty, span := {} }

private def program (declarations : List IR.Decl) : IR.Program := {
  name := "ArtifactValidation"
  language := "spl/0.1-draft"
  core := "spl-core/0.1-draft"
  schema := "spl-data/0.1-draft"
  span := {}
  declarations }

private def rejected (name : String) (p : IR.Program) : IO Unit := do
  match ValidateIR.validate p with
  | .ok _ => throw (IO.userError (name ++ ": invalid artifact was accepted"))
  | .error d => unless d.code == "INVALID_IR" do
      throw (IO.userError (name ++ ": unexpected diagnostic " ++ d.code))
  match Emit.emitIR p, Emit.emitLibraryIR p with
  | .error _, .error _ => pure ()
  | _, _ => throw (IO.userError (name ++ ": invalid artifact passed emission boundary"))

def main : IO Unit := do
  let ratio := Check.ratioTy
  let usd := Check.usdTy
  let int := Check.intTy
  let bool := Check.boolTy
  -- Public constructors permit fabricated annotations; both emitters must reject them.
  rejected "Money squared" (program [.emit (m 0 usd) "value"
    (.binary (m 1 usd) "*" (.money (m 2 usd) "USD" "2") (.money (m 3 usd) "USD" "3"))])
  rejected "Mismatched branch" (program [.emit (m 0 ratio) "value"
    (.ite (m 1 ratio) (.boolean (m 2 bool) true)
      (.number (m 3 ratio) "1") (.money (m 4 usd) "USD" "1"))])
  rejected "Incorrect binder" (program [.emit (m 0 (.list usd)) "value"
    (.collection (m 1 (.list usd)) "map" "x" usd
      (.list (m 2 (.list int)) [.number (m 3 int) "1"])
      (.name (m 4 usd) "x"))])
  rejected "Duplicate identity" (program [.emit (m 0 int) "value"
    (.binary (m 1 int) "+" (.number (m 2 int) "1") (.number (m 2 int) "2"))])
  rejected "Missing closing port" (program [.opening (m 0 usd) "balance" "main"])
  rejected "Wrong leaf annotation" (program [.emit (m 0 ratio) "value" (.boolean (m 1 ratio) true)])
  rejected "Unresolved reference" (program [.emit (m 0 int) "value" (.name (m 1 int) "missing")])
  rejected "Cyclic definitions" (program [
    .define (m 0 int) "a" (.name (m 1 int) "b"),
    .define (m 2 int) "b" (.name (m 3 int) "a")])
  rejected "Fabricated registered schema" (program [
    .input (m 0 (.record "Period" [("start", int)])) "period"])
  rejected "Invalid numeric lexeme" (program [.emit (m 0 int) "value" (.number (m 1 int) "bad")])
  -- A legitimate manually constructed artifact need not retain an original AST;
  -- contextual numeric literals and shared source spans remain valid.
  let valid := program [.emit (m 0 ratio) "value"
    (.binary (m 1 ratio) "+" (.number (m 2 ratio) "1") (.number (m 3 ratio) "2"))]
  match ValidateIR.validate valid with
  | .ok _ => pure ()
  | .error d => throw (IO.userError s!"Valid annotated artifact was rejected: {repr d}")
  IO.println "SPL independent IR validation checks passed (tampered types, binders, IDs, names, cycles, schemas and ports)."
