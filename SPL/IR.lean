import Lean
import SPL.Check

/-! Immutable whole-program IR for the executable SPL profile. Every elaborated
expression has a checked structural type annotation. This public syntax is not
intrinsically typed; `ValidateIR.validate` defends execution/emission boundaries.
Collection binders are explicit first-order
operators, never escaping source lambdas. IDs are deterministic preorder numbers
within one source schedule; edits may renumber nodes. This is a compiler artifact,
not a proof that elaboration or accounting policy is correct. -/
namespace SPL.IR

abbrev Ty := Check.Ty

structure Meta where
  id : Nat
  span : Syntax.Span
  ty : Ty
  citation : Option String := none
  sourceAnnotation : Option Ty := none
  deriving Repr, Inhabited

mutual
  inductive Expr where
    | number : Meta → String → Expr
    | money : Meta → String → String → Expr
    | boolean : Meta → Bool → Expr
    | text : Meta → String → Expr
    | date : Meta → String → Expr
    | name : Meta → String → Expr
    | unary : Meta → String → Expr → Expr
    | binary : Meta → String → Expr → Expr → Expr
    | field : Meta → Expr → String → Expr
    | ite : Meta → Expr → Expr → Expr → Expr
    | call : Meta → String → List Expr → Expr
    | record : Meta → List (String × Expr) → Expr
    | list : Meta → List Expr → Expr
    | choose : Meta → List (Expr × Expr) → Option Expr → Expr
    | selectRules : Meta → Bool → List (String × Int × Expr × Expr) → Option (String × Expr) → Expr
    | collection : Meta → String → String → Ty → Expr → Expr → Expr
    | indexed : Meta → String → Expr → Option Expr → String → Ty → Expr → String → Ty → Expr → Expr
    | forEach : Meta → String → Ty → Expr → List LocalDecl → Expr → Expr
    | fold : Meta → Expr → Expr → String → String → Ty → Option (String × Expr × String × Expr × String) → List LocalDecl → Expr → Expr
    | apply : Meta → String → List (String × Ty) → List Expr → List LocalDecl → Expr → Expr
    deriving Repr, Inhabited

  inductive LocalDecl where
    | define : Meta → String → Expr → LocalDecl
    | require : Meta → Expr → String → LocalDecl
    deriving Repr, Inhabited
end

inductive Decl where
  | input : Meta → String → Decl
  | opening : Meta → String → String → Decl
  | define : Meta → String → Expr → Decl
  | require : Meta → Expr → String → Decl
  | closing : Meta → String → Expr → Decl
  | emit : Meta → String → Expr → Decl
  deriving Repr, Inhabited

structure FunctionSignature where
  label : String
  parameters : List (String × Ty)
  result : Ty
  deriving Repr, BEq, Inhabited

structure Program where
  name : String
  language : String
  core : String
  schema : String
  span : Syntax.Span
  declarations : List Decl
  format : String := "spl-ir/0.1"
  features : List String := []
  owners : List (String × List String) := []
  unitDefinitions : List (String × String) := []
  conversions : List (String × String) := []
  signatures : List FunctionSignature := []
  deriving Repr, Inhabited

def Expr.meta : Expr → Meta
  | .number m _ | .money m _ _ | .boolean m _ | .text m _ | .date m _ | .name m _
  | .unary m _ _ | .binary m _ _ _ | .field m _ _ | .ite m _ _ _ | .call m _ _
  | .record m _ | .list m _ | .choose m _ _ | .selectRules m _ _ _ | .collection m _ _ _ _ _
  | .indexed m _ _ _ _ _ _ _ _ _
  | .forEach m _ _ _ _ _ | .fold m _ _ _ _ _ _ _ _ | .apply m _ _ _ _ _ => m

def Decl.meta : Decl → Meta
  | .input m _ | .opening m _ _ | .define m _ _ | .require m _ _
  | .closing m _ _ | .emit m _ _ => m

private def obj := Lean.Json.mkObj
private def str := Lean.Json.str
private def arr (items : List Lean.Json) := Lean.Json.arr items.toArray

def spanJson (s : Syntax.Span) : Lean.Json := obj [
  ("start", Lean.toJson s.start), ("stop", Lean.toJson s.stop),
  ("line", Lean.toJson s.line), ("column", Lean.toJson s.column)]

partial def typeJson : Ty → Lean.Json
  | .atom name => obj [("kind", str "atom"), ("name", str name)]
  | .money currency => obj [("kind", str "money"), ("currency", str currency)]
  | .quantity unit => obj [("kind", str "quantity"), ("unit", str unit)]
  | .rate unit currency => obj [("kind", str "rate"), ("unit", str unit), ("currency", str currency)]
  | .list ty => obj [("kind", str "list"), ("item", typeJson ty)]
  | .option ty => obj [("kind", str "option"), ("item", typeJson ty)]
  | .tuple types => obj [("kind", str "tuple"), ("items", arr (types.map typeJson))]
  | .map key value => obj [("kind", str "map"), ("key", typeJson key), ("value", typeJson value)]
  | .record name fields => obj [("kind", str "record"), ("name", str name),
      ("fields", arr (fields.map fun (name, ty) => obj [("name", str name), ("type", typeJson ty)]))]

def metaJson (m : Meta) : Lean.Json := obj ([("id", Lean.toJson m.id),
  ("span", spanJson m.span), ("type", typeJson m.ty)] ++
  (m.citation.toList.map fun citation => ("citation", str citation)) ++
  (m.sourceAnnotation.toList.map fun annotation => ("source_annotation", typeJson annotation)))

mutual
  partial def exprJson (e : Expr) : Lean.Json :=
    let node (kind : String) (fields : List (String × Lean.Json)) :=
      obj ([("kind", str kind), ("meta", metaJson e.meta)] ++ fields)
    match e with
    | .number _ value => node "number" [("value", str value)]
    | .money _ currency value => node "money" [("currency", str currency), ("value", str value)]
    | .boolean _ value => node "boolean" [("value", Lean.toJson value)]
    | .text _ value => node "text" [("value", str value)]
    | .date _ value => node "date" [("value", str value)]
    | .name _ name => node "name" [("name", str name)]
    | .unary _ op body => node "unary" [("op", str op), ("body", exprJson body)]
    | .binary _ op a b => node "binary" [("op", str op), ("left", exprJson a), ("right", exprJson b)]
    | .field _ base name => node "field" [("base", exprJson base), ("name", str name)]
    | .ite _ c y n => node "if" [("condition", exprJson c), ("then", exprJson y), ("else", exprJson n)]
    | .call _ name args => node "call" [("name", str name), ("arguments", arr (args.map exprJson))]
    | .record _ fields => node "record" [("fields", arr (fields.map fun (name, value) =>
        obj [("name", str name), ("value", exprJson value)]))]
    | .list _ values => node "list" [("items", arr (values.map exprJson))]
    | .choose _ arms fallback => node "choose_unique" ([
        ("arms", arr (arms.map fun (p, b) => obj [("predicate", exprJson p), ("body", exprJson b)]))] ++
        (fallback.toList.map fun body => ("otherwise", exprJson body)))
    | .selectRules _ priority arms fallback => node "select_rules" ([
        ("priority_mode", .bool priority),
        ("arms", arr (arms.map fun (id, rank, p, b) => obj [
          ("rule_id", str id), ("priority", Lean.toJson rank),
          ("predicate", exprJson p), ("body", exprJson b)]))] ++
        (fallback.toList.map fun (id, body) => ("otherwise", obj [("rule_id", str id), ("body", exprJson body)])))
    | .collection _ op binder itemTy source body => node "collection" [("op", str op),
        ("binder", str binder), ("binder_type", typeJson itemTy), ("source", exprJson source), ("body", exprJson body)]
    | .indexed _ op source right kb kt key vb vt value => node "indexed" ([
        ("op", str op), ("source", exprJson source), ("key_binder", str kb),
        ("key_binder_type", typeJson kt), ("key", exprJson key), ("value_binder", str vb),
        ("value_binder_type", typeJson vt), ("value", exprJson value)] ++
        right.toList.map (fun e => ("right", exprJson e)))
    | .forEach _ binder itemTy source declarations body => node "for_each" [("binder", str binder),
        ("binder_type", typeJson itemTy), ("source", exprJson source),
        ("declarations", arr (declarations.map localJson)), ("yield", exprJson body)]
    | .fold _ source initial state event eventTy order declarations body => node "fold" ([
        ("source", exprJson source), ("initial", exprJson initial), ("state_binder", str state),
        ("event_binder", str event), ("event_type", typeJson eventTy),
        ("declarations", arr (declarations.map localJson)), ("yield", exprJson body)] ++
        order.toList.map (fun (kb, key, ib, identity, ties) => ("order", obj [
          ("key_binder", str kb), ("key", exprJson key), ("id_binder", str ib),
          ("identity", exprJson identity), ("ties", str ties)])))
    | .apply _ label parameters args declarations body => node "apply" [
        ("function", str label), ("parameters", arr (parameters.map fun (name, ty) => obj [
          ("name", str name), ("type", typeJson ty)])), ("arguments", arr (args.map exprJson)),
        ("declarations", arr (declarations.map localJson)), ("body", exprJson body)]

  partial def localJson : LocalDecl → Lean.Json
    | .define m name body => obj [("kind", str "define"), ("meta", metaJson m),
        ("name", str name), ("body", exprJson body)]
    | .require m body code => obj [("kind", str "require"), ("meta", metaJson m),
        ("condition", exprJson body), ("code", str code)]
end

def declJson : Decl → Lean.Json
  | .input m name => obj [("kind", str "input"), ("meta", metaJson m), ("name", str name)]
  | .opening m name alias => obj [("kind", str "opening"), ("meta", metaJson m),
      ("name", str name), ("alias", str alias)]
  | .define m name body => localJson (.define m name body)
  | .require m body code => localJson (.require m body code)
  | .closing m name body => obj [("kind", str "closing"), ("meta", metaJson m),
      ("name", str name), ("body", exprJson body)]
  | .emit m name body => obj [("kind", str "emit"), ("meta", metaJson m),
      ("name", str name), ("body", exprJson body)]

/-- Fixed object/array order and exact decimal lexemes make serialization reproducible.
The artifact format is versioned separately from the draft surface language. -/
def admissionJson (features : List String) (owners : List (String × List String))
    (definitions conversions : List (String × String)) (signatures : List FunctionSignature := []) : Lean.Json := obj [
  ("features", arr (features.map str)),
  ("owners", arr (owners.map fun (label, features) => obj [("label", str label), ("features", arr (features.map str))])),
  ("unit_definitions", arr (definitions.map fun (id, pin) => obj [("id", str id), ("sha256", str pin)])),
  ("relations", arr (conversions.map fun (id, pin) => obj [("id", str id), ("sha256", str pin)])),
  ("signatures", arr (signatures.map fun signature => obj [
    ("label", str signature.label), ("parameters", arr (signature.parameters.map fun (name, ty) =>
      obj [("name", str name), ("type", typeJson ty)])), ("result", typeJson signature.result)]))]

def Program.toJson (program : Program) : Lean.Json := obj ([("format", str program.format),
  ("name", str program.name), ("language", str program.language), ("core", str program.core),
  ("schema", str program.schema), ("span", spanJson program.span),
  ("declarations", arr (program.declarations.map declJson))] ++
  (if program.format == "spl-ir/0.1" then [] else
    [("dimension_admission", admissionJson program.features program.owners program.unitDefinitions program.conversions program.signatures)]))

end SPL.IR

