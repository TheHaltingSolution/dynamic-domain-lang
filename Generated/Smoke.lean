import Participation.Runtime

/-! Handwritten stand-in for a future emitted Lean module.
The numbers are test data, not an implementation of a contract. -/
namespace Generated

def smokeProgram : Participation.Runtime.Expr :=
  .add (.literal 13000) (.literal 20000)

def smokeResult : Nat := Participation.Runtime.eval smokeProgram

end Generated
