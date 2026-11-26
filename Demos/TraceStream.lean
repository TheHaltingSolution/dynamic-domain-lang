import SPL.AuditTransport

def main (args : List String) : IO UInt32 := do
  try SPL.TraceStream.run args
  catch error =>
    IO.println (Lean.Json.mkObj [("status", .str "blocked"),
      ("diagnostics", .arr #[Lean.Json.mkObj [("code", .str "IO_ERROR"),
        ("message", .str error.toString), ("source", .str ""),
        ("span", Lean.Json.mkObj [("start", .num 0), ("end", .num 0),
          ("line", .num 1), ("column", .num 1)])]])]).compress
    return 1
