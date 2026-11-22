/-! Pure target semantics for the infrastructure example. -/
namespace Participation.Runtime

inductive Expr where
  | literal : Nat → Expr
  | add : Expr → Expr → Expr
  deriving Repr

def eval : Expr → Nat
  | .literal n => n
  | .add left right => eval left + eval right

end Participation.Runtime
