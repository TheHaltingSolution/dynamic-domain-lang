import SPL.Runtime

/-! Ordered settlement with atomic in-memory results. The step is the emitted
period calculation. The wrapper owns sequencing and feeds each successful
closing state into the next step. -/
namespace SPL.Series

structure Result where
  periods : List Settlement
  closing : Env

structure Failure where
  index : Nat
  code : String

abbrev Step (Input : Type) := Input → Env → Eval Settlement

private def loop (step : Step Input) (index : Nat) (done : List Settlement)
    (opening : Env) : List Input → Except Failure Result
  | [] => .ok ⟨done.reverse, opening⟩
  | input :: rest =>
    match step input opening with
    | .error code => .error ⟨index, code⟩
    | .ok result => loop step (index + 1) (result :: done) result.closing rest

def run (step : Step Input) (opening : Env) (inputs : List Input) : Except Failure Result :=
  loop step 0 [] opening inputs

/-- Success means one observable settlement for every input, in supplied
order, with exactly the previous closing state at each following step. -/
inductive Follows (step : Step Input) : Env → List Input → List Settlement → Env → Prop
  | empty (state) : Follows step state [] [] state
  | next (settled : step input state = .ok result)
      (rest : Follows step result.closing inputs results closing) :
      Follows step state (input :: inputs) (result :: results) closing

/-- Failure is at the first rejected step after a successfully settled prefix. -/
inductive Rejects (step : Step Input) : Env → List Input → Nat → String → Prop
  | here (failed : step input state = .error code) : Rejects step state (input :: rest) 0 code
  | later (settled : step input state = .ok result)
      (rest : Rejects step result.closing inputs index code) :
      Rejects step state (input :: inputs) (index + 1) code

private def spec (step : Step Input) (opening : Env) : List Input → Except Failure Result
  | [] => .ok ⟨[], opening⟩
  | input :: rest =>
    match step input opening with
    | .error code => .error ⟨0, code⟩
    | .ok result =>
      match spec step result.closing rest with
      | .ok final => .ok ⟨result :: final.periods, final.closing⟩
      | .error failure => .error ⟨failure.index + 1, failure.code⟩

private theorem loop_eq (step : Step Input) (inputs : List Input) (opening : Env)
    (index : Nat) (done : List Settlement) :
    loop step index done opening inputs =
      match spec step opening inputs with
      | .ok result => .ok ⟨done.reverse ++ result.periods, result.closing⟩
      | .error failure => .error ⟨index + failure.index, failure.code⟩ := by
  induction inputs generalizing opening index done with
  | nil => simp [loop, spec]
  | cons input rest ih =>
    cases settled : step input opening with
    | error code => simp [loop, spec, settled]
    | ok result =>
      simp only [loop, spec, settled]
      rw [ih]
      cases spec step result.closing rest with
      | ok final => simp [List.reverse_cons, List.append_assoc]
      | error failure => simp [Nat.add_assoc, Nat.add_comm 1 failure.index]

private theorem run_eq_spec (step : Step Input) (opening : Env) (inputs : List Input) :
    run step opening inputs = spec step opening inputs := by
  unfold run
  rw [loop_eq]
  cases spec step opening inputs <;> simp

private theorem spec_follows (step : Step Input) (inputs : List Input)
    (opening : Env) (result : Result) :
    spec step opening inputs = .ok result ↔ Follows step opening inputs result.periods result.closing := by
  constructor
  · induction inputs generalizing opening result with
    | nil =>
      intro h
      have same : (⟨[], opening⟩ : Result) = result := Except.ok.inj h
      subst result
      exact .empty opening
    | cons input rest ih =>
      unfold spec
      split
      next => simp
      next prior hprior =>
        split
        next final hfinal =>
          intro h
          cases Except.ok.inj h
          exact .next hprior (ih _ _ hfinal)
        next => simp
  · intro relation
    cases result with
    | mk periods closing =>
      change Follows step opening inputs periods closing at relation
      induction relation with
      | empty => rfl
      | next settled _ ih => simp [spec, settled, ih]

private theorem spec_rejects (step : Step Input) (inputs : List Input)
    (opening : Env) (failure : Failure) :
    spec step opening inputs = .error failure ↔ Rejects step opening inputs failure.index failure.code := by
  constructor
  · induction inputs generalizing opening failure with
    | nil => simp [spec]
    | cons input rest ih =>
      unfold spec
      split
      next code hfailed =>
        intro h
        cases Except.error.inj h
        exact .here hfailed
      next result hsettled =>
        split
        next => simp
        next prior hprior =>
          intro h
          cases Except.error.inj h
          exact .later hsettled (ih _ _ hprior)
  · intro relation
    cases failure with
    | mk index code =>
      change Rejects step opening inputs index code at relation
      induction relation with
      | here failed => simp [spec, failed]
      | later settled _ ih => simp [spec, settled, ih]

theorem run_ok_iff (step : Step Input) (opening : Env) (inputs : List Input) (result : Result) :
    run step opening inputs = .ok result ↔ Follows step opening inputs result.periods result.closing := by
  rw [run_eq_spec, spec_follows]

theorem run_error_iff (step : Step Input) (opening : Env) (inputs : List Input) (failure : Failure) :
    run step opening inputs = .error failure ↔ Rejects step opening inputs failure.index failure.code := by
  rw [run_eq_spec, spec_rejects]

theorem Follows.append (first : Follows step opening inputs results intermediate)
    (second : Follows step intermediate more later closing) :
    Follows step opening (inputs ++ more) (results ++ later) closing := by
  induction first with
  | empty => exact second
  | next h _ ih => exact .next h (ih second)

/-- A successful prefix can be resumed from its closing state with exactly
the same settlements and final state as a single successful combined run. -/
theorem run_append_of_ok (first : run step opening inputs = .ok prefixResult)
    (second : run step prefixResult.closing more = .ok suffixResult) :
    run step opening (inputs ++ more) =
      .ok ⟨prefixResult.periods ++ suffixResult.periods, suffixResult.closing⟩ :=
  (run_ok_iff _ _ _ _).2
    (((run_ok_iff _ _ _ _).1 first).append ((run_ok_iff _ _ _ _).1 second))

end SPL.Series
