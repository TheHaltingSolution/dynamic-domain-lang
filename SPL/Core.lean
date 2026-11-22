import SPL.Runtime

/-!
A typed, total arithmetic core with independent exact semantics. This is the
explicitly verified subset of SPL lowering: rational arithmetic, demanded
division errors, numeric comparisons, Boolean short circuiting, lazy conditional
branches and guards. Numbers may denote USD amounts or dimensionless ratios;
unit checking and record/collection elaboration are outside this core theorem.
-/
namespace SPL.Core

inductive Kind where
  | number | boolean

abbrev Meaning : Kind → Type
  | .number => Rat
  | .boolean => Bool

inductive Arithmetic where
  | add | subtract | multiply | divide
  deriving Repr

inductive Comparison where
  | less | equal
  deriving Repr

inductive Logical where
  | conjunction | disjunction
  deriving Repr

inductive Expr : Kind → Type where
  | literal : Rat → Expr .number
  | parameter : Nat → Expr .number
  | flag : Bool → Expr .boolean
  | arithmetic : Arithmetic → Expr .number → Expr .number → Expr .number
  | comparison : Comparison → Expr .number → Expr .number → Expr .boolean
  | logical : Logical → Expr .boolean → Expr .boolean → Expr .boolean
  | negate : Expr .number → Expr .number
  | invert : Expr .boolean → Expr .boolean
  | conditional : Expr .boolean → Expr kind → Expr kind → Expr kind
  | guard : Expr .boolean → String → Expr kind → Expr kind

def arithmeticMeaning (op : Arithmetic) (left right : Rat) : Except String Rat :=
  match op with
  | .add => .ok (left + right)
  | .subtract => .ok (left - right)
  | .multiply => .ok (left * right)
  | .divide => if right == 0 then .error "DIVISION_BY_ZERO" else .ok (left / right)

def comparisonMeaning (op : Comparison) (left right : Rat) : Bool :=
  match op with
  | .less => left < right
  | .equal => left == right

/-- Source semantics does not call the SPL target runtime. -/
def eval (inputs : Nat → Rat) : Expr kind → Except String (Meaning kind)
  | .literal value => .ok value
  | .parameter index => .ok (inputs index)
  | .flag value => .ok value
  | .arithmetic op left right => do arithmeticMeaning op (← eval inputs left) (← eval inputs right)
  | .comparison op left right => do pure (comparisonMeaning op (← eval inputs left) (← eval inputs right))
  | .logical op left right => do
    let left ← eval inputs left
    match op with
    | .conjunction => if left then eval inputs right else pure false
    | .disjunction => if left then pure true else eval inputs right
  | .negate body => do pure (-(← eval inputs body))
  | .invert body => do pure (!(← eval inputs body))
  | .conditional condition yes no => do
    if ← eval inputs condition then eval inputs yes else eval inputs no
  | .guard condition code body => do
    if ← eval inputs condition then eval inputs body else throw code

def embed : (kind : Kind) → Meaning kind → Value
  | .number, value => .num value
  | .boolean, value => .flag value

def arithmeticToken : Arithmetic → String
  | .add => "+" | .subtract => "-" | .multiply => "*" | .divide => "/"

def comparisonToken : Comparison → String
  | .less => "<" | .equal => "=="

/-- Shallow lowering into the same pure target primitives used by Lean emission.
Parameter decoding and source-code serialization are separate trusted stages. -/
def lower (inputs : Nat → Rat) : Expr kind → Eval Value
  | .literal value => .ok (.num value)
  | .parameter index => .ok (.num (inputs index))
  | .flag value => .ok (.flag value)
  | .arithmetic op left right => do
    binary (arithmeticToken op) (← lower inputs left) (← lower inputs right)
  | .comparison op left right => do
    binary (comparisonToken op) (← lower inputs left) (← lower inputs right)
  | .logical op left right => match op with
    | .conjunction => conjunction (lower inputs left) (fun _ => lower inputs right)
    | .disjunction => disjunction (lower inputs left) (fun _ => lower inputs right)
  | .negate body => do unary "-" (← lower inputs body)
  | .invert body => do unary "not" (← lower inputs body)
  | .conditional condition yes no =>
    conditional (lower inputs condition) (fun _ => lower inputs yes) (fun _ => lower inputs no)
  | .guard condition code body => do
    assertValue (← lower inputs condition) code
    lower inputs body

/-- Scalar numeric lowering entry used by the real source emitter. Each demanded
scalar arithmetic node materializes a typed core node; boundary decoding and
operand evaluation remain outside the lowering theorem. -/
def numericBinary (op : Arithmetic) (left right : Value) : Eval Value := do
  let a ← asNum left
  let b ← asNum right
  lower (fun index => if index == 0 then a else b)
    (.arithmetic op (.parameter 0) (.parameter 1))

/-- Unary numeric entry used by the real source emitter. -/
def numericUnary (value : Value) : Eval Value := do
  let number ← asNum value
  lower (fun _ => number) (.negate (.parameter 0))

end SPL.Core
