import SPL.IR

/-! Reconstruct source inference edges for extended defensive IR validation.
Inferred Meta types are deliberately not turned into source annotations. -/
namespace SPL.IRSource
open IR

partial def typeExpr : Ty → Syntax.TypeExpr
  | .atom name => if name.startsWith "Id:" then
      .named "Id" [.named (String.intercalate ":" ((name.splitOn ":").drop 1)) []]
    else .named name []
  | .money currency => .named "Money" [.named currency []]
  | .quantity unit => .named "Quantity" [.named unit []]
  | .rate unit currency => .named "Rate" [.named unit [], .named currency []]
  | .list ty => .named "List" [typeExpr ty]
  | .option ty => .named "Option" [typeExpr ty]
  | .tuple types => .named "Tuple" (types.map typeExpr)
  | .map key value => .named "Map" [typeExpr key, typeExpr value]
  | .record name fields => if name == "literal" then .record (fields.map fun (n,t) => (n,typeExpr t))
      else .named name []

mutual
  partial def expression (expr : Expr) : Syntax.Expr :=
    let span := expr.meta.span
    match expr with
    | .number _ value => .number span value
    | .money _ currency value => .money span currency value
    | .boolean _ value => .boolean span value
    | .text _ value => .text span value
    | .date _ value => .date span value
    | .name _ name => .name span name
    | .unary _ op value => .unary span op (expression value)
    | .binary _ op left right => .binary span op (expression left) (expression right)
    | .field _ value name => .field span (expression value) name
    | .ite _ predicate yes no => .ite span (expression predicate) (expression yes) (expression no)
    | .call _ name args => .call span name (args.map expression)
    | .record _ fields => .record span (fields.map fun (name, value) => (name, expression value))
    | .list _ values => .list span (values.map expression)
    | .choose _ arms fallback => .choose span (arms.map fun (a,b) => (expression a,expression b)) (fallback.map expression)
    | .selectRules _ priority arms fallback => .selectRules span priority
        (arms.map fun (id,rank,p,b) => (id,rank,expression p,expression b))
        (fallback.map fun (id,b) => (id,expression b))
    | .collection _ op binder _ source body =>
        .call span op [expression source, .lambda span binder (expression body)]
    | .indexed _ op source right kb _ key vb _ value =>
        .call span op ([expression source] ++ right.toList.map expression ++
          [.lambda span kb (expression key), .lambda span vb (expression value)])
    | .forEach _ binder _ source declarations body =>
        .forEach span binder (expression source) (declarations.map localDecl) (expression body)
    | .fold _ source initial state event _ order declarations body =>
        .fold span (expression source) (expression initial) state event
          (order.map fun (kb,k,ib,i,t) => (kb,expression k,ib,expression i,t))
          (declarations.map localDecl) (expression body)
    | .apply m label parameters args declarations body =>
        .apply span label (parameters.map fun (name,ty) => (name,typeExpr ty))
          (args.map expression) (typeExpr m.ty) (declarations.map localDecl) (expression body)

  partial def localDecl : LocalDecl → Syntax.LocalDecl
    | .define m name body => .define m.span name (m.sourceAnnotation.map typeExpr) (expression body) m.citation
    | .require m body code => .require m.span (expression body) code
end

def schedule (program : Program) : Syntax.Schedule := {
  name := program.name, language := program.language, core := program.core,
  schema := program.schema, span := program.span, features := program.features,
  owners := program.owners, declarations := program.declarations.map fun decl =>
    match decl with
    | .input m name => .input m.span name (typeExpr m.ty)
    | .opening m name alias => .opening m.span name (typeExpr m.ty) alias
    | .define m name body => .define m.span name (m.sourceAnnotation.map typeExpr) (expression body) m.citation
    | .require m body code => .require m.span (expression body) code
    | .closing m name body => .closing m.span name (expression body)
    | .emit m name body => .emit m.span name (expression body)
  signatures := program.signatures.map fun signature => {
    label := signature.label
    parameters := signature.parameters.map fun (name, ty) => (name, typeExpr ty)
    result := typeExpr signature.result } }

end SPL.IRSource
