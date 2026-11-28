import CertifiedArtifact
import SPL.Proofs
import Lean.Elab.Command
import Lean.Elab.Tactic.Basic
import Lean.Meta.Tactic.Delta
import Lean.Util.CollectAxioms

set_option maxRecDepth 32768
set_option maxHeartbeats 8000000

/-!
Independent semantics of the two approved authored schedules. The order of
aggregation and rounding comes from the reviewed readable rules. A half-cent
is assigned to its even neighboring cent; all arithmetic is over exact rationals.
The compiler does not supply the meaning, expected statement, or proof script.
-/
namespace PilotCertificate

inductive Profile where
  | aggregate
  | row

def centsQuantum : Rat := mkRat 1 100

def halfEvenCent (usd : Rat) : Rat :=
  let cents := usd / centsQuantum
  let below := cents.floor
  let above := cents.ceil
  let distanceFromBelow := cents - (below : Rat)
  let half := mkRat 1 2
  let chosen :=
    if distanceFromBelow < half then below
    else if distanceFromBelow > half then above
    else if below % 2 = 0 then below else above
  (chosen : Rat) * centsQuantum

def amount : Profile → Rat → Rat → Rat
  | .aggregate, first, second => halfEvenCent (mkRat 1 2 * (first + second))
  | .row, first, second => halfEvenCent (mkRat 1 2 * first) + halfEvenCent (mkRat 1 2 * second)

def observe (profile : Profile) (first second : Rat) : SPL.Eval SPL.Settlement :=
  .ok { emissions := [("participation", .num (amount profile first second))], closing := [] }

def inputs (first second : Rat) : SPL.Env :=
  [("first_receipt", .num first), ("second_receipt", .num second)]

def approvedAggregate : String := include_str "ApprovedAggregate.spl"
def approvedRow : String := include_str "ApprovedRow.spl"
def approvedPolicy : String := include_str "ApprovedPolicy.spl"
def suppliedSource : String := include_str "SuppliedSource.spl"
def suppliedPolicy : String := include_str "SuppliedPolicy.spl"

/-- The approved readable fragment has exactly two authored forms, both with
the single fixed linked policy. The recognition happens independently of SPL
parsing, expansion, type checking, and code generation. -/
def meaning (profile : Profile) (source policy : String) :
    Option (Rat → Rat → SPL.Eval SPL.Settlement) :=
  let approved := match profile with
    | .aggregate => approvedAggregate
    | .row => approvedRow
  if policy = approvedPolicy ∧ source = approved then
    some (observe profile)
  else none

private theorem cent_round (value : Rat) :
    SPL.quantize (.num value) (.num (mkRat 1 100)) (.text "half_even") =
      .ok (.num (halfEvenCent value)) := by
  simp [SPL.quantize, SPL.sameDimension, SPL.magnitude, SPL.asText, SPL.withMagnitude,
    centsQuantum, halfEvenCent]
  rfl

open Lean Elab Tactic in
elab "unfold_emitted" : tactic =>
  liftMetaTactic1 fun goal => goal.deltaTarget fun name =>
    (`GeneratedSPL).isPrefixOf name || (`_private.CertifiedArtifact).isPrefixOf name

private theorem add_rat (left right : Rat) :
    SPL.Core.numericBinary .add (.num left) (.num right) = .ok (.num (left + right)) := rfl

private theorem mul_rat (left right : Rat) :
    SPL.Core.numericBinary .multiply (.num left) (.num right) = .ok (.num (left * right)) := rfl

private theorem half : SPL.Core.numericBinary .divide
    (.num (mkRat 500 10)) (.num (mkRat 100 1)) = .ok (.num (mkRat 1 2)) := by
  have nonzero : mkRat 100 1 ≠ 0 := by decide
  have fraction : mkRat 500 10 / mkRat 100 1 = mkRat 1 2 := by decide +kernel
  rw [SPL.Core.numericBinary_correct]
  simp [SPL.asNum, SPL.Core.arithmeticMeaning, Except.map, nonzero, fraction]

private theorem cent_not_negative : ¬ mkRat 1 100 < 0 := by decide
private theorem cent_not_zero : mkRat 1 100 ≠ 0 := by decide

-- The profile token is selected by the trusted checker from exact source bytes.
theorem source_and_artifact (first second : Rat) :
    meaning .PILOT_PROFILE suppliedSource suppliedPolicy =
      some (fun a b => GeneratedSPL.settle (inputs a b) []) ∧
    GeneratedSPL.settle (inputs first second) [] = observe .PILOT_PROFILE first second := by
  have translation (a b : Rat) :
      GeneratedSPL.settle (inputs a b) [] = observe .PILOT_PROFILE a b := by
    unfold_emitted
    simp [inputs, observe, amount, SPL.lookup, List.lookup, Thunk.get,
      SPL.conditional, SPL.disjunction, SPL.assertValue,
      SPL.asBool, SPL.binary, SPL.equal, SPL.compare,
      half, add_rat, mul_rat, cent_round, cent_not_negative, cent_not_zero]
  refine ⟨?_, translation first second⟩
  rw [show meaning .PILOT_PROFILE suppliedSource suppliedPolicy =
    some (observe .PILOT_PROFILE) by
      unfold meaning
      rw [ite_eq_left (show suppliedPolicy = approvedPolicy ∧
        suppliedSource = (match Profile.PILOT_PROFILE with
          | .aggregate => approvedAggregate
          | .row => approvedRow) from ⟨rfl, rfl⟩)]]
  congr
  funext a b
  exact (translation a b).symm

/-- Keep the executed standalone entry connected to the proved calculation. -/
theorem entry : main =
    SPL.Bindings.runMain
      [("first_receipt", .named "Money" [.named "USD" []]),
       ("second_receipt", .named "Money" [.named "USD" []])]
      [] GeneratedSPL.settle := rfl

open Lean Elab Command in
run_cmd do
  for name in [`PilotCertificate.source_and_artifact, `PilotCertificate.entry] do
    let axioms ← Lean.collectAxioms name
    for axiomName in axioms do
      unless axiomName == `propext || axiomName == `Quot.sound || axiomName == `Classical.choice do
        throwError "Unexpected certificate assumption {axiomName} in {name}"

end PilotCertificate
