import SPL.Core

/-!
Kernel-checked preservation for `SPL.Core.Expr`, not the prior toy language.
Scope: all core expressions and all exact rational parameter assignments,
including errors and lazy control flow. Trusted/excluded: surface parser,
checker, named record/collection elaboration, source emitter, native compiler,
JSON, policy authority, trace and financial rounding.
-/
namespace SPL.Core

@[simp] private theorem bind_ok (value : α) (next : α → Except String β) :
    (Except.ok value >>= next) = next value := rfl
@[simp] private theorem bind_error (message : String) (next : α → Except String β) :
    (Except.error message >>= next) = Except.error message := rfl
@[simp] private theorem pure_ok (value : α) :
    (pure value : Except String α) = Except.ok value := rfl
@[simp] private theorem fmap_ok (value : α) (f : α → β) :
    f <$> (Except.ok value : Except String α) = Except.ok (f value) := rfl
@[simp] private theorem fmap_error (message : String) (f : α → β) :
    f <$> (Except.error message : Except String α) = Except.error message := rfl
@[simp] private theorem throw_error (message : String) :
    (throw message : Except String α) = Except.error message := rfl

private theorem arithmetic_primitive (op : Arithmetic) (a b : Rat) :
    SPL.binary (arithmeticToken op) (.num a) (.num b) =
      (arithmeticMeaning op a b).map Value.num := by
  cases op <;> simp [arithmeticToken, arithmeticMeaning, SPL.binary, SPL.asNum, Except.map]
  split <;> rfl

private theorem comparison_primitive (op : Comparison) (a b : Rat) :
    SPL.binary (comparisonToken op) (.num a) (.num b) =
      .ok (.flag (comparisonMeaning op a b)) := by
  cases op <;> by_cases less : a < b <;> by_cases equal : a = b <;>
    simp_all [comparisonToken, comparisonMeaning, SPL.binary, SPL.compare, SPL.equal, Rat.lt_irrefl]

/-- Exact value/error preservation for every expression in the verified SPL
arithmetic/control-flow core. No well-formed-input axiom is assumed. -/
theorem lower_correct (expression : Expr kind) (inputs : Nat → Rat) :
    lower inputs expression = (eval inputs expression).map (embed kind) := by
  induction expression with
  | literal value => rfl
  | parameter index => rfl
  | flag value => rfl
  | arithmetic op left right ihLeft ihRight =>
    simp only [lower, eval, ihLeft, ihRight]
    cases eval inputs left <;> cases eval inputs right <;>
      simp [Except.map, embed, arithmetic_primitive]
  | comparison op left right ihLeft ihRight =>
    simp only [lower, eval, ihLeft, ihRight]
    cases eval inputs left <;> cases eval inputs right <;>
      simp [Except.map, embed, comparison_primitive]
  | logical op left right ihLeft ihRight =>
    cases op <;> simp only [lower, eval, ihLeft, ihRight]
    all_goals cases eval inputs left <;> simp [Except.map, embed, SPL.conjunction,
      SPL.disjunction, SPL.asBool]
    all_goals split <;> simp_all
  | negate body ih =>
    simp only [lower, eval, ih]
    cases eval inputs body <;> simp [Except.map, embed, SPL.unary, SPL.asNum]
  | invert body ih =>
    simp only [lower, eval, ih]
    cases eval inputs body <;> simp [Except.map, embed, SPL.unary, SPL.asBool]
  | conditional condition yes no ihCondition ihYes ihNo =>
    simp only [lower, eval, ihCondition, ihYes, ihNo]
    cases eval inputs condition <;> simp [Except.map, embed, SPL.conditional, SPL.asBool]
    split <;> simp_all
  | guard condition code body ihCondition ihBody =>
    simp only [lower, eval, ihCondition, ihBody]
    cases eval inputs condition <;> simp [Except.map, embed, SPL.assertValue, SPL.asBool]
    split <;> simp_all

/-- The actual emitted arithmetic entry agrees with independent arithmetic
semantics, including invalid dynamic operand tags and demanded division errors.
This connects the checked core theorem to the active generated-code path. -/
theorem numericBinary_correct (op : Arithmetic) (left right : Value) :
    numericBinary op left right = (do
      let a ← SPL.asNum left
      let b ← SPL.asNum right
      (arithmeticMeaning op a b).map Value.num) := by
  unfold numericBinary
  simp only [lower_correct]
  cases left <;> cases right <;>
    simp [SPL.asNum, eval, embed, Except.map]

theorem numericUnary_correct (value : Value) :
    numericUnary value = (do pure (.num (-(← SPL.asNum value)))) := by
  unfold numericUnary
  simp only [lower_correct]
  cases value <;> simp [SPL.asNum, eval, embed, Except.map]

end SPL.Core
