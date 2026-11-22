import Participation
import Generated

open Participation

-- These checks are proved by the kernel during the normal build.
example : Compiler.eval (.literal 7) = 7 := rfl
example : Runtime.eval (Compiler.compile (.add (.literal 13) (.literal 20))) = 33 := rfl
example : Generated.smokeResult = 33000 := rfl

def main : IO Unit := do
  let source : Compiler.Expr := .add (.literal 13000) (.literal 20000)
  unless Runtime.eval (Compiler.compile source) == Compiler.eval source do
    throw (IO.userError "compiler smoke test failed")
  unless Generated.smokeResult == 33000 do
    throw (IO.userError "generated module smoke test failed")
  IO.println "Lean smoke tests passed (compiler, generated module, and checked proof)."
