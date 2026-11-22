import SPL.Parser
import SPL.Elaborate
import SPL.Interpret
import SPL.Bindings
import SPL.Emit

open SPL

private def ensure (test : Bool) (message : String) : IO Unit :=
  unless test do throw (IO.userError message)

private def header := "schedule Collections language \"spl/0.1-draft\" core \"spl-core/0.1-draft\" schema \"spl-data/0.1-draft\" { "

private def program (body : String) : IO IR.Program :=
  match Parser.parse (header ++ body ++ "}") >>= Elaborate.elaborate with
  | .ok p => pure p
  | .error d => throw (IO.userError (reprStr d))

def main : IO Unit := do
  let rows := Value.seq [.num 2,.num 1]
  let result := makeMap rows (fun row => pure (.tuple [row,.flag false])) (fun _ => pure (.num 0))
  let .ok m := result | throw (IO.userError "Map construction failed")
  ensure ((mapLookup m (.tuple [.num 1,.flag false])).toOption.any (equal (.present (.num 0)))) "Present zero lost"
  ensure ((mapLookup m (.tuple [.num 3,.flag false])).toOption.any (equal .absent)) "Absent key lost"
  ensure (match makeMap (.seq [.num 1,.num 1]) pure (fun _ => .error "BAD_VALUE") with
    | .error "DUPLICATE_MAP_KEY" => true | _ => false) "Duplicate must precede value"
  let .ok (.seq joined) := joinValues false (.seq [.num 1,.num 1]) (.seq [.num 1,.num 1,.num 1]) pure pure
    | throw (IO.userError "Join failed")
  ensure (joined.length == 6) "Join multiplicity lost"
  let badRight := joinValues false (.seq []) (.seq [.num 1]) pure (fun _ => .error "RIGHT_KEY")
  ensure (match badRight with | .error "RIGHT_KEY" => true | _ => false) "Empty left hid right key error"
  let p ← program "input rows:List<{id:Id<Event>,key:Tuple<Id<Asset>,Int>,value:Money<USD>}>; emit \"v\"=entries(make_map(rows,x=>x.key,y=>y.value));"
  ensure ((ValidateIR.validate p).isOk) "Valid indexed IR rejected"
  ensure ((Emit.emitIR p).isOk) "Indexed target emission rejected"
  let p ← program "define m=make_map([2,2,1,1],x=>x,y=>USD 1 / 0.0); emit \"v\"=entries(m);"
  let observed := Interpret.interpret p [] []
  ensure (match observed.result with | .error "DUPLICATE_MAP_KEY" => true | _ => false) "IR value demanded before duplicates"
  ensure ((observed.trace.validate).isOk) "Invalid collection trace"
  IO.println "SPL map/group/join tests passed."
