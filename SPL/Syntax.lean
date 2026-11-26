/-! Source syntax shared by the authoritative SPL frontend stages.
All offsets count Unicode scalar values in the decoded UTF-8 source. -/
namespace SPL.Syntax

structure Span where
  start : Nat := 0
  stop : Nat := 0
  line : Nat := 1
  column : Nat := 1
  deriving Repr, BEq, Inhabited

structure Diagnostic where
  code : String
  message : String
  span : Span := {}
  deriving Repr, Inhabited

inductive TypeExpr where
  | named : String → List TypeExpr → TypeExpr
  | record : List (String × TypeExpr) → TypeExpr
  deriving Repr, BEq, Inhabited

mutual
  inductive Expr where
    | number : Span → String → Expr
    | money : Span → String → String → Expr
    | boolean : Span → Bool → Expr
    | text : Span → String → Expr
    | date : Span → String → Expr
    | name : Span → String → Expr
    | unary : Span → String → Expr → Expr
    | binary : Span → String → Expr → Expr → Expr
    | field : Span → Expr → String → Expr
    | ite : Span → Expr → Expr → Expr → Expr
    | call : Span → String → List Expr → Expr
    | lambda : Span → String → Expr → Expr
    | record : Span → List (String × Expr) → Expr
    | list : Span → List Expr → Expr
    | choose : Span → List (Expr × Expr) → Option Expr → Expr
    | selectRules : Span → Bool → List (String × Int × Expr × Expr) → Option (String × Expr) → Expr
    | forEach : Span → String → Expr → List LocalDecl → Expr → Expr
    | fold : Span → Expr → Expr → String → String → Option (String × Expr × String × Expr × String) → List LocalDecl → Expr → Expr
    | apply : Span → String → List (String × TypeExpr) → List Expr → TypeExpr → List LocalDecl → Expr → Expr
    deriving Repr, Inhabited

  inductive LocalDecl where
    | define : Span → String → Option TypeExpr → Expr → Option String → LocalDecl
    | require : Span → Expr → String → LocalDecl
    deriving Repr, Inhabited
end

inductive Decl where
  | input : Span → String → TypeExpr → Decl
  | opening : Span → String → TypeExpr → String → Decl
  | define : Span → String → Option TypeExpr → Expr → Option String → Decl
  | require : Span → Expr → String → Decl
  | closing : Span → String → Expr → Decl
  | emit : Span → String → Expr → Decl
  deriving Repr, Inhabited

structure FunctionSignature where
  label : String
  parameters : List (String × TypeExpr)
  result : TypeExpr
  deriving Repr, BEq, Inhabited

structure Schedule where
  name : String
  language : String
  core : String
  schema : String
  declarations : List Decl
  span : Span := {}
  features : List String := []
  owners : List (String × List String) := []
  signatures : List FunctionSignature := []
  deriving Repr, Inhabited

def Expr.span : Expr → Span
  | .number s _ | .money s _ _ | .boolean s _ | .text s _ | .date s _ | .name s _
  | .unary s _ _ | .binary s _ _ _ | .field s _ _ | .ite s _ _ _ | .call s _ _
  | .lambda s _ _ | .record s _ | .list s _ | .choose s _ _ | .selectRules s _ _ _ | .forEach s _ _ _ _
  | .fold s _ _ _ _ _ _ _ | .apply s _ _ _ _ _ _ => s

def Decl.span : Decl → Span
  | .input s _ _ | .opening s _ _ _ | .define s _ _ _ _ | .require s _ _
  | .closing s _ _ | .emit s _ _ => s

end SPL.Syntax
