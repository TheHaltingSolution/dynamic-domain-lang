"""Finite invalid-source mutations and a public-constructor native IR probe."""

HEADER = 'schedule RejectionWitness language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" { '


def frontend_cases():
    return [{"id": identity, "source": HEADER + body + " }", "expected_code": code,
             "stage": "frontend_rejection"} for identity, body, code in [
        ("duplicate-field", 'define value = {amount: USD 1, amount: USD 2}; emit "value" = value;', "DUPLICATE_FIELD"),
        ("money-squared", 'define value = USD 1 * USD 2; emit "value" = value;', "TYPE_MISMATCH"),
        ("inconsistent-branches", 'define value = if true then USD 1 else 0.1; emit "value" = value;', "TYPE_MISMATCH"),
        ("missing-semicolon", 'emit "value" = USD 1', "SYNTAX_ERROR"),
    ]]


IR_DRIVER = '''import SPL
open SPL
private def annotation (id : Nat) (ty : IR.Ty) : IR.Meta := {id, ty, span := {}}
private def program (declarations : List IR.Decl) : IR.Program := {
  name := "GeneratedIRAdmission", language := "spl/0.1-draft",
  core := "spl-core/0.1-draft", schema := "spl-data/0.1-draft", span := {}, declarations}
private def inspect (name : String) (p : IR.Program) : Lean.Json :=
  let validation := match ValidateIR.validate p with | .ok _ => "accepted" | .error d => d.code
  let emission := match Emit.emitIR p with | .ok _ => "accepted" | .error d => d.code
  let library := match Emit.emitLibraryIR p with | .ok _ => "accepted" | .error d => d.code
  let interpretation := match (Interpret.interpret p [] []).result with
    | .ok _ => "calculated" | .error code => code
  Lean.Json.mkObj [("id", .str name), ("validation", .str validation),
    ("native_interpretation", .str interpretation), ("native_emitter", .str emission),
    ("native_library_emitter", .str library)]
def main : IO Unit := do
  let integer := Check.intTy
  let ratio := Check.ratioTy
  let valid := program [.emit (annotation 0 integer) "value"
    (.binary (annotation 1 integer) "+" (.number (annotation 2 integer) "1") (.number (annotation 3 integer) "2"))]
  let duplicate := program [.emit (annotation 0 integer) "value"
    (.binary (annotation 1 integer) "+" (.number (annotation 2 integer) "1") (.number (annotation 2 integer) "2"))]
  let wrongLeaf := program [.emit (annotation 0 ratio) "value" (.boolean (annotation 1 ratio) true)]
  IO.println (Lean.Json.arr #[inspect "valid-control" valid, inspect "duplicate-ir-id" duplicate,
    inspect "wrong-ir-leaf-type" wrongLeaf]).compress
'''
