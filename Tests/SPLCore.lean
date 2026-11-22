import SPL.Proofs

/-! Kernel-checked executable examples within the actual SPL scalar core.
These exercise division-error preservation and lazy branches, unlike the
separate historical toy-language smoke proof. -/
namespace SPL.CoreTests
open SPL.Core

def zeroDivisor : Expr .number := .arithmetic .divide (.literal 1) (.literal 0)

example : eval (fun _ => 0) zeroDivisor = .error "DIVISION_BY_ZERO" := rfl
example : lower (fun _ => 0) zeroDivisor = .error "DIVISION_BY_ZERO" := rfl

example : lower (fun _ => 0) (.conditional (.flag true) (.literal 7) zeroDivisor) =
    .ok (.num 7) := rfl

example : lower (fun _ => 0) (.guard (.flag false) "MISSING_POLICY" zeroDivisor) =
    .error "MISSING_POLICY" := rfl

example : lower (fun _ => 0) (.logical .conjunction (.flag false)
    (.comparison .less zeroDivisor (.literal 1))) = .ok (.flag false) := rfl

/-- This is precisely the arithmetic entry emitted by the real compiler. -/
example (left right : SPL.Value) :
    numericBinary .divide left right = (do
      let a ← SPL.asNum left
      let b ← SPL.asNum right
      (arithmeticMeaning .divide a b).map SPL.Value.num) :=
  numericBinary_correct .divide left right

end SPL.CoreTests

def main : IO Unit := IO.println "SPL scalar core examples checked."
