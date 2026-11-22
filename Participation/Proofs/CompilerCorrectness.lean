import Participation.Compiler

namespace Participation.Compiler

/-- Compilation preserves evaluation for every expression in the toy language. -/
theorem compile_correct (expr : Expr) : Runtime.eval (compile expr) = eval expr := by
  induction expr with
  | literal n => rfl
  | add left right ihLeft ihRight =>
    simp only [compile, Runtime.eval, eval, ihLeft, ihRight]

end Participation.Compiler
