import Participation.Runtime

/-! A deliberately small compiler used to exercise the build and proof setup.
This is not the participation language or a Lean source generator. -/
namespace Participation.Compiler

inductive Expr where
  | literal : Nat → Expr
  | add : Expr → Expr → Expr
  deriving Repr

def eval : Expr → Nat
  | .literal n => n
  | .add left right => eval left + eval right

def compile : Expr → Runtime.Expr
  | .literal n => .literal n
  | .add left right => .add (compile left) (compile right)

end Participation.Compiler
