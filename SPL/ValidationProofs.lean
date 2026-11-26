import SPL.Runtime

/-! Soundness of zero-failure counting in linked validation modules. The claim
uses the scalar `sumValues`, `conditional`, `binary` and `assertValue` calls
used by the emitted checks. Input decoding and feed completeness are separate. -/
namespace SPL.ValidationProofs

@[simp] private theorem bind_ok (value : α) (next : α → Eval β) :
    (Except.ok value >>= next) = next value := rfl

@[simp] private theorem bind_error (code : String) (next : α → Eval β) :
    (Except.error code >>= next) = Except.error code := rfl

@[simp] private theorem pure_ok (value : α) : (pure value : Eval α) = .ok value := rfl

private def failureValue (predicate : Value → Eval Value) (row : Value) : Eval Value :=
  conditional (predicate row) (fun _ => pure (.num 0)) (fun _ => pure (.num 1))

private def tallyStep (predicate : Value → Eval Value) (row : Value) (total : Rat) :
    Eval (ForInStep Rat) := do
  let count ← asNum (← failureValue predicate row)
  pure (.yield (total + count))

private theorem zero_tally_all (predicate : Value → Eval Value) (rows : List Value) (total : Rat)
    (nonnegative : 0 ≤ total)
    (accepted : forIn rows total (tallyStep predicate) = .ok 0) :
    total = 0 ∧ ∀ row ∈ rows, predicate row = .ok (.flag true) := by
  induction rows generalizing total with
  | nil =>
      simp only [List.forIn_nil, pure_ok, Except.ok.injEq] at accepted
      exact ⟨accepted, by simp⟩
  | cons head tail ih =>
      rw [List.forIn_cons] at accepted
      cases decision : predicate head with
      | error code => simp [tallyStep, failureValue, conditional, decision] at accepted
      | ok value =>
          cases value <;> simp [tallyStep, failureValue, conditional, decision, asBool, asNum] at accepted
          case flag present =>
            cases present with
            | false =>
                have nonnegativeNext := Rat.add_nonneg nonnegative (show (0 : Rat) ≤ 1 by decide)
                have zeroNext := (ih (total + 1) nonnegativeNext accepted).1
                have lower : (0 : Rat) + 1 ≤ total + 1 := Rat.add_le_add_right.mpr nonnegative
                rw [Rat.zero_add, zeroNext] at lower
                exact False.elim ((show ¬ (1 : Rat) ≤ 0 by decide) lower)
            | true =>
                have tailAdmission := ih total nonnegative (by simpa [Rat.add_zero] using accepted)
                refine ⟨tailAdmission.1, ?_⟩
                intro row member
                rcases List.mem_cons.mp member with rfl | member
                · exact decision
                · exact tailAdmission.2 row member

/-- An accepted zero-failure assertion guarantees that every supplied row
evaluated the predicate successfully and satisfied it. -/
theorem all_of_zero_failure_assertion (predicate : Value → Eval Value) (rows : List Value)
    (code : String)
    (accepted : (do
      let count ← sumValues (.seq rows) (failureValue predicate)
      assertValue (← binary "==" count (.num 0)) code) = .ok ()) :
    ∀ row ∈ rows, predicate row = .ok (.flag true) := by
  have sum_shape : sumValues (.seq rows) (failureValue predicate) = (do
    let admittedRows ← asList (.seq rows)
    let total ← forIn admittedRows 0 (tallyStep predicate)
    pure (.num total)) := rfl
  by_cases withinLimit : rows.length > maxCollectionItems
  · simp [sum_shape, asList, checkCollectionSize, withinLimit] at accepted
  · simp only [sum_shape, asList, checkCollectionSize, withinLimit, ite_false, pure_ok, bind_ok,
      bind_assoc] at accepted
    cases tally : forIn rows 0 (tallyStep predicate) with
    | error message => simp [tally] at accepted
    | ok total =>
        simp [tally, binary, equal, assertValue, asBool] at accepted
        exact (zero_tally_all predicate rows 0 Rat.le_refl (by simpa [accepted] using tally)).2

/-- The guard used by the receipt and posted-cost appendices checks the date
projected from each row against the supplied half-open period. -/
theorem half_open_membership_of_period_assertion (rows : List Value) (period : Value)
    (dateField code start finish : String) (rowDate : Value → String)
    (startBound : field period "start" = .ok (.text start))
    (endBound : field period "end" = .ok (.text finish))
    (rowDates : ∀ row ∈ rows, field row dateField = .ok (.text (rowDate row)))
    (accepted : (do
      let count ← sumValues (.seq rows) (failureValue fun row => do
        inPeriod (← field row dateField) period)
      assertValue (← binary "==" count (.num 0)) code) = .ok ()) :
    ∀ row ∈ rows, start ≤ rowDate row ∧ rowDate row < finish := by
  intro row member
  have checked := all_of_zero_failure_assertion _ rows code accepted row member
  simpa [inPeriod, rowDates row member, startBound, endBound, asText] using checked

end SPL.ValidationProofs
