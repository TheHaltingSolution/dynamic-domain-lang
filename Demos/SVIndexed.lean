import SPL.Fold
import SPL.Core
import SPL.Bindings

set_option maxRecDepth 4096
set_option maxHeartbeats 0

namespace GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116

def scheduleName : String := "SkourasVenturaIndexedExperiment"
def sourceRules : List (String × String) := [("pictures", ""), ("receipts", ""), ("eligible_costs", ""), ("policy", ""), ("prepayment", ""), ("require@8:3", ""), ("picture_count", ""), ("receipts_by_asset", ""), ("costs_by_asset", ""), ("title_results", ""), ("earned_total", ""), ("recouped", "SV-7-POOL-RECOVERY"), ("payable", ""), ("prepayment", ""), ("require@38:3", ""), ("titles", ""), ("pool", "")]

def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := (do
  let _spl_v0 ← SPL.lookup _inputs "pictures"
  let _spl_v1 ← SPL.lookup _inputs "receipts"
  let _spl_v2 ← SPL.lookup _inputs "eligible_costs"
  let _spl_v3 ← SPL.lookup _inputs "policy"
  let _spl_v4 ← SPL.lookup _openings "prepayment"
  let _spl_v5 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.sumValues (← (pure _spl_v0)) (fun _spl_v12 => (pure (.num (mkRat 1 1))))))
  let _spl_v6 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.groupValues (← (SPL.conditional (do
      SPL.binary ">" (← (_spl_v5.get)) (← (pure (.num (mkRat 0 1))))) (fun _ => (pure _spl_v1)) (fun _ => (SPL.listValues [])))) (fun _spl_v13 => (do
      SPL.field (← (pure _spl_v13)) "asset_id"))))
  let _spl_v7 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.groupValues (← (SPL.conditional (do
      SPL.binary ">" (← (_spl_v5.get)) (← (pure (.num (mkRat 0 1))))) (fun _ => (pure _spl_v2)) (fun _ => (SPL.listValues [])))) (fun _spl_v14 => (do
      SPL.field (← (pure _spl_v14)) "asset_id"))))
  let _spl_v8 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.mapValues (← (pure _spl_v0)) (fun _spl_v15 => (do
      let _spl_v16 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.getOr (← (do
          SPL.mapLookup (← (_spl_v6.get)) (← (do
            SPL.field (← (pure _spl_v15)) "asset_id")))) (fun _ => (SPL.listValues []))))
      let _spl_v17 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.getOr (← (do
          SPL.mapLookup (← (_spl_v7.get)) (← (do
            SPL.field (← (pure _spl_v15)) "asset_id")))) (fun _ => (SPL.listValues []))))
      let _spl_v18 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.filterValues (← (_spl_v16.get)) (fun _spl_v27 => (do
          SPL.inPeriod (← (do
            SPL.field (← (pure _spl_v27)) "cash_received_date")) (← (do
            SPL.field (← (pure _spl_v3)) "period"))))))
      let _spl_v19 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.filterValues (← (_spl_v17.get)) (fun _spl_v28 => (do
          SPL.inPeriod (← (do
            SPL.field (← (pure _spl_v28)) "incurred_date")) (← (do
            SPL.field (← (pure _spl_v3)) "period"))))))
      let _spl_v20 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.sumValues (← (_spl_v18.get)) (fun _spl_v29 => (do
          SPL.field (← (pure _spl_v29)) "amount"))))
      let _spl_v21 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.sumValues (← (_spl_v19.get)) (fun _spl_v30 => (do
          SPL.field (← (pure _spl_v30)) "amount"))))
      let _spl_v22 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (SPL.choose [((do
        SPL.field (← (pure _spl_v15)) "contribution_present"), (fun _ => (pure (.num (mkRat 75 1000)))))] (some (fun _ => (pure (.num (mkRat 25 100)))))))
      let _spl_v23 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.Core.numericBinary .multiply (← (_spl_v20.get)) (← (_spl_v22.get))))
      let _spl_v24 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.Core.numericBinary .subtract (← (do
          SPL.Core.numericBinary .subtract (← (_spl_v20.get)) (← (_spl_v23.get)))) (← (_spl_v21.get))))
      let _spl_v25 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (SPL.conditional (do
        SPL.field (← (pure _spl_v15)) "contribution_present") (fun _ => (do
        SPL.field (← (pure _spl_v15)) "funding_share")) (fun _ => (pure (.num (mkRat 20 100))))))
      let _spl_v26 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.Core.numericBinary .multiply (← (_spl_v24.get)) (← (_spl_v25.get))))
      SPL.assertValue (← (SPL.conjunction (do
        SPL.binary ">=" (← (do
          SPL.field (← (pure _spl_v15)) "funding_share")) (← (pure (.num (mkRat 0 1))))) (fun _ => (do
        SPL.binary "<=" (← (do
          SPL.field (← (pure _spl_v15)) "funding_share")) (← (pure (.num (mkRat 1 1)))))))) "INVALID_FUNDING_SHARE"
      let _spl_v31 ← (_spl_v16.get)
      let _spl_v32 ← (_spl_v17.get)
      let _spl_v33 ← (_spl_v18.get)
      let _spl_v34 ← (_spl_v19.get)
      let _spl_v35 ← (_spl_v20.get)
      let _spl_v36 ← (_spl_v21.get)
      let _spl_v37 ← (_spl_v22.get)
      let _spl_v38 ← (_spl_v23.get)
      let _spl_v39 ← (_spl_v24.get)
      let _spl_v40 ← (_spl_v25.get)
      let _spl_v41 ← (_spl_v26.get)
      SPL.assertValue (← (do
        SPL.binary ">=" (← (pure _spl_v41)) (← (pure (.num (mkRat 0 1)))))) "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT"
      (SPL.recordValues [("asset_id", (do
        SPL.field (← (pure _spl_v15)) "asset_id")), ("cash", (pure _spl_v35)), ("fee", (pure _spl_v38)), ("allowed_cost", (pure _spl_v36)), ("basis", (pure _spl_v39)), ("share", (pure _spl_v40)), ("earned", (pure _spl_v41))])))))
  let _spl_v9 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.sumValues (← (_spl_v8.get)) (fun _spl_v42 => (do
      SPL.field (← (pure _spl_v42)) "earned"))))
  let _spl_v10 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.extrema false (← (_spl_v9.get)) (← (pure _spl_v4))))
  let _spl_v11 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.Core.numericBinary .subtract (← (_spl_v9.get)) (← (_spl_v10.get))))
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v4)) (← (pure (.num (mkRat 0 1)))))) "NEGATIVE_OPENING_ADVANCE"
  let _spl_v43 ← (_spl_v5.get)
  let _spl_v44 ← (_spl_v6.get)
  let _spl_v45 ← (_spl_v7.get)
  let _spl_v46 ← (_spl_v8.get)
  let _spl_v47 ← (_spl_v9.get)
  let _spl_v48 ← (_spl_v10.get)
  let _spl_v49 ← (_spl_v11.get)
  SPL.assertValue (← (do
    SPL.binary "==" (← (pure _spl_v47)) (← (do
      SPL.Core.numericBinary .add (← (pure _spl_v48)) (← (pure _spl_v49)))))) "SV_SETTLEMENT_RECONCILIATION"
  let _spl_v50 ← (do
    SPL.Core.numericBinary .subtract (← (pure _spl_v4)) (← (pure _spl_v48)))
  let _spl_v51 ← (pure _spl_v46)
  let _spl_v52 ← (SPL.recordValues [("agreement_id", (do
    SPL.field (← (pure _spl_v3)) "agreement_id")), ("participant_id", (do
    SPL.field (← (pure _spl_v3)) "participant_id")), ("pool_id", (do
    SPL.field (← (pure _spl_v3)) "pool_id")), ("period", (do
    SPL.field (← (pure _spl_v3)) "period")), ("earned", (pure _spl_v47)), ("recouped", (pure _spl_v48)), ("payable", (pure _spl_v49))])
  pure { emissions := [("titles", _spl_v51), ("pool", _spl_v52)], closing := [("prepayment", _spl_v50)] })

end GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116

namespace GeneratedSPL
abbrev scheduleName := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.scheduleName
abbrev sourceRules := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.sourceRules
abbrev settle := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.settle
end GeneratedSPL

def main (args : List String) : IO UInt32 :=
  SPL.Bindings.runMain [("pictures", (.named "List" [(.named "SVPicture" [])])), ("receipts", (.named "List" [(.named "SVReceipt" [])])), ("eligible_costs", (.named "List" [(.named "SVCost" [])])), ("policy", (.named "SVPolicy" []))] [("prepayment", (.named "Money" [(.named "USD" [])]))] GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.settle args
