import SPL.AuditTransport

/-! Generic opt-in audit preparation. A single checked/validated Program supplies
the persisted IR, emitted calculation and full interpreter graph. No registered
contract names or demo targets are selected here. -/
namespace SPL.AuditCLI

def run (args : List String) : IO UInt32 := do
  let (args, link) := match args.reverse with
    | manifest :: "--link" :: rest => (rest.reverse, some manifest)
    | _ => (args, none)
  let [source, bindings, irPath, emittedPath] := args
    | throw (IO.userError "Usage: spl_audit SOURCE BINDINGS IR_DEST EMIT_DEST [--link MANIFEST]")
  match ← TraceStream.loadProgram source link none with
  | .error diagnostic =>
    throw (IO.userError (diagnostic.code ++ ": " ++ diagnostic.message))
  | .ok (schedule, program) =>
    let artifact := program.toJson
    match IRArtifact.validate artifact with
    | .error code => throw (IO.userError code)
    | .ok _ => pure ()
    let generated ← match Emit.emitIR program with
      | .error diagnostic => throw (IO.userError (diagnostic.code ++ ": " ++ diagnostic.message))
      | .ok value => pure value
    IO.FS.writeFile irPath artifact.compress
    IO.FS.writeFile emittedPath generated
    let outcome ← TraceStream.interpretProgram schedule program bindings none
    TraceStream.writeCompactOutcome outcome true none
    return 0

end SPL.AuditCLI

def main (args : List String) : IO UInt32 := do
  try SPL.AuditCLI.run args
  catch error =>
    let stderr ← IO.getStderr
    stderr.putStrLn error.toString
    return 1
