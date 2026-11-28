import SPL.Check
import SPL.Runtime
import SPL.Bindings

/-! Lexical binding lemmas for the compiler's actual `Check.bind` operation.
Scope extension preserves resolution for every existing name, and an aligned
runtime environment returns a value related to any resolved type. The
successful port decoder provides the alignment for declared inputs relative to
the existing type parser and exact value decoder. These claims begin with
resolved scopes or declared ports, after Readable alias expansion. -/
namespace SPL.ContextProofs

/-- Static name resolution and runtime association lists search the same key
in the same order. This statement also covers contexts before validation. -/
theorem lookup_eq_assoc {α : Type} (context : List (String × α)) (name : String) :
    Check.lookup context name = context.lookup name := by
  induction context with
  | nil => rfl
  | cons entry rest ih =>
    rcases entry with ⟨key, value⟩
    by_cases same : key = name
    · subst key
      simp [Check.lookup, List.lookup]
    · have reversed : (name == key) = false := beq_eq_false_iff_ne.mpr (Ne.symm same)
      simpa [Check.lookup, List.lookup, same, reversed] using ih

/-- The real scope extender accepts exactly a fresh name and records its
declared type. Freshness is stated with list membership, independently of the
implementation's lookup. -/
theorem bind_ok_iff (context : Check.Context) (name : String) (ty : Check.Ty)
    (span : Syntax.Span) (extended : Check.Context) :
    Check.bind context name ty span = .ok extended ↔
      name ∉ context.map Prod.fst ∧ extended = (name, ty) :: context := by
  unfold Check.bind
  rw [lookup_eq_assoc]
  by_cases present : name ∈ context.map Prod.fst
  · have hit : (context.lookup name).isSome = true := by
      obtain ⟨binding, member, same⟩ := List.mem_map.mp present
      exact List.lookup_isSome_iff.mpr ⟨binding, member, by simp [same]⟩
    simp [hit, present, Check.error]
  · have miss : context.lookup name = none := by
      apply List.lookup_eq_none_iff.mpr
      intro binding member
      exact bne_iff_ne.mpr fun same => present (List.mem_map.mpr ⟨binding, member, same.symm⟩)
    simp [miss, present, Pure.pure, Except.pure]
    exact eq_comm

/-- A successful extension gives the new type at its own name and leaves all
other lookups exactly unchanged, including names previously unresolved. -/
theorem bind_lookup {context extended : Check.Context} {name : String} {ty : Check.Ty}
    {span : Syntax.Span} (accepted : Check.bind context name ty span = .ok extended)
    (key : String) :
    Check.lookup extended key = if key = name then some ty else Check.lookup context key := by
  obtain ⟨_, rfl⟩ := (bind_ok_iff context name ty span extended).mp accepted
  by_cases same : key = name
  · subst key
    simp [lookup_eq_assoc]
  · have different : (key == name) = false := beq_eq_false_iff_ne.mpr same
    simp [lookup_eq_assoc, List.lookup, different, same]

/-- The checker preserves the no-shadowing invariant from an already unique
scope. -/
theorem bind_preserves_unique {context extended : Check.Context} {name : String} {ty : Check.Ty}
    {span : Syntax.Span} (accepted : Check.bind context name ty span = .ok extended)
    (unique : (context.map Prod.fst).Nodup) : (extended.map Prod.fst).Nodup := by
  obtain ⟨fresh, rfl⟩ := (bind_ok_iff context name ty span extended).mp accepted
  exact List.nodup_cons.mpr ⟨fresh, unique⟩

/-- Static types and runtime values follow the same named binding order. The
value predicate can later be instantiated with the typing relation for the
specific supported inputs, records, or other semantics under verification. -/
inductive Aligned (admitted : Check.Ty → Value → Prop) : Check.Context → Env → Prop where
  | nil : Aligned admitted [] []
  | cons : admitted ty value → Aligned admitted context values →
      Aligned admitted ((name, ty) :: context) ((name, value) :: values)

theorem Aligned.lookup {admitted : Check.Ty → Value → Prop} {context : Check.Context} {values : Env}
    (aligned : Aligned admitted context values) (key : String) :
    match Check.lookup context key with
    | none => SPL.lookup values key = .error ("MISSING_BINDING:" ++ key)
    | some ty => ∃ value, SPL.lookup values key = .ok value ∧ admitted ty value := by
  induction aligned with
  | nil => rfl
  | @cons ty value context values name typed previous ih =>
    by_cases same : key = name
    · subst key
      simp [lookup_eq_assoc, SPL.lookup, typed]
    · have different : (key == name) = false := beq_eq_false_iff_ne.mpr same
      simpa [lookup_eq_assoc, SPL.lookup, List.lookup, different] using ih

/-- Extending aligned scopes with a checker-approved binding and an admissible
value preserves alignment. `Aligned.lookup` then applies in the new scope. -/
theorem Aligned.bind {admitted : Check.Ty → Value → Prop} {context extended : Check.Context}
    {values : Env} {name : String} {ty : Check.Ty} {value : Value} {span : Syntax.Span}
    (aligned : Aligned admitted context values)
    (accepted : Check.bind context name ty span = .ok extended) (typed : admitted ty value) :
    Aligned admitted extended ((name, value) :: values) := by
  obtain ⟨_, rfl⟩ := (bind_ok_iff context name ty span extended).mp accepted
  exact .cons typed aligned

/-- A complete ordered correspondence between declared ports and the
environment returned by the native binding decoder. Each value comes from
the original member with the same key under the declared and checked type. -/
inductive DecodedPorts (owner : Dimensions.Admission) (meanings : Dimensions.Meanings)
    (members : Lean.Json) : List (String × Syntax.TypeExpr) → Env → Prop where
  | nil : DecodedPorts owner meanings members [] []
  | cons : Check.parseTypeWith owner declared = .ok checked →
      members.getObjVal? name = .ok original → Bindings.decodeWith meanings checked original = .ok value →
      DecodedPorts owner meanings members rest tail →
      DecodedPorts owner meanings members ((name, declared) :: rest) ((name, value) :: tail)

private def decodePort (owner : Dimensions.Admission) (meanings : Dimensions.Meanings)
    (members : Lean.Json) (port : String × Syntax.TypeExpr) : Eval (String × Value) := do
  let (name, declared) := port
  let checked ← Check.parseTypeWith owner declared |>.mapError (·.code)
  let original ← members.getObjVal? name
  return (name, ← Bindings.decodeWith meanings checked original)

private theorem decodePort_success {owner : Dimensions.Admission} {meanings : Dimensions.Meanings}
    {members : Lean.Json} {name : String} {declared : Syntax.TypeExpr} {pair : String × Value}
    (accepted : decodePort owner meanings members (name, declared) = .ok pair) :
    ∃ checked original value, pair = (name, value) ∧ Check.parseTypeWith owner declared = .ok checked ∧
      members.getObjVal? name = .ok original ∧ Bindings.decodeWith meanings checked original = .ok value := by
  unfold decodePort at accepted
  cases parse : Check.parseTypeWith owner declared with
  | error diagnostic => simp [parse, Except.mapError, Bind.bind, Except.bind] at accepted
  | ok checked =>
    cases field : members.getObjVal? name with
    | error message => simp [parse, field, Except.mapError, Bind.bind, Except.bind] at accepted
    | ok original =>
      cases value : Bindings.decodeWith meanings checked original with
      | error message => simp [parse, field, value, Except.mapError, Bind.bind, Except.bind] at accepted
      | ok decoded =>
        have result : (name, decoded) = pair := by
          simpa [parse, field, value, Except.mapError, Bind.bind, Except.bind, Pure.pure, Except.pure] using accepted
        exact ⟨checked, original, decoded, result.symm, rfl, rfl, value⟩

private theorem decodePortList_success {owner : Dimensions.Admission} {meanings : Dimensions.Meanings}
    {members : Lean.Json} {declared : List (String × Syntax.TypeExpr)} {values : Env}
    (accepted : declared.mapM (decodePort owner meanings members) = .ok values) :
    DecodedPorts owner meanings members declared values := by
  induction declared generalizing values with
  | nil =>
    have same : [] = values := by simpa [Pure.pure, Except.pure] using accepted
    subst values
    exact .nil
  | cons port rest ih =>
    rcases port with ⟨name, declared⟩
    cases head : decodePort owner meanings members (name, declared) with
    | error message => simp [head, Bind.bind, Except.bind] at accepted
    | ok pair =>
      cases tail : rest.mapM (decodePort owner meanings members) with
      | error message => simp [head, tail, Bind.bind, Except.bind] at accepted
      | ok remaining =>
        have result : pair :: remaining = values := by
          simpa [head, tail, Bind.bind, Except.bind, Pure.pure, Except.pure] using accepted
        obtain ⟨_, _, value, equal, parse, field, parsed⟩ := decodePort_success head
        subst pair
        subst values
        exact .cons parse field parsed (ih tail)

/-- The production decoder binds the right JSON member to every declared
name, in declared order, with the checked type. This theorem describes
successful admission relative to `parseTypeWith` and `decodeWith`; their
individual representations and rejection semantics have separate scope. -/
theorem decodeBindingsWith_correspondence {owner : Dimensions.Admission} {meanings : Dimensions.Meanings}
    {members : Lean.Json} {declared : List (String × Syntax.TypeExpr)} {values : Env}
    (accepted : Bindings.decodeBindingsWith owner meanings declared members = .ok values) :
    DecodedPorts owner meanings members declared values := by
  unfold Bindings.decodeBindingsWith at accepted
  simp only [Bind.bind, Except.bind] at accepted
  split at accepted
  · contradiction
  · exact decodePortList_success accepted

theorem DecodedPorts.keys {owner : Dimensions.Admission} {meanings : Dimensions.Meanings}
    {members : Lean.Json} {declared : List (String × Syntax.TypeExpr)} {values : Env}
    (decoded : DecodedPorts owner meanings members declared values) :
    values.map Prod.fst = declared.map Prod.fst := by
  induction decoded with
  | nil => rfl
  | cons _ _ _ _ ih => simp [ih]

/-- A successfully decoded environment is aligned with the actual parsed
port types. The value predicate is admission by the exact value decoder.
`DecodedPorts` additionally identifies the original member that supplied each
value. -/
theorem DecodedPorts.aligned {owner : Dimensions.Admission} {meanings : Dimensions.Meanings}
    {members : Lean.Json} {declared : List (String × Syntax.TypeExpr)} {values : Env}
    (decoded : DecodedPorts owner meanings members declared values) :
    ∃ context : Check.Context,
      declared.mapM (fun (name, type) => do pure (name, ← Check.parseTypeWith owner type)) = .ok context ∧
      Aligned (fun ty value => ∃ original, Bindings.decodeWith meanings ty original = .ok value) context values := by
  induction decoded with
  | nil => exact ⟨[], rfl, .nil⟩
  | cons parsed _ correct _ ih =>
    obtain ⟨context, types, aligned⟩ := ih
    refine ⟨(_, _) :: context, ?_, .cons ⟨_, correct⟩ aligned⟩
    simp only [List.mapM_cons]
    rw [types]
    simp [parsed, Bind.bind, Except.bind, Pure.pure, Except.pure]

end SPL.ContextProofs
