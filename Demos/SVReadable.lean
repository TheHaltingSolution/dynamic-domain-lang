import SPL.Fold
import SPL.Core
import SPL.Bindings

set_option maxRecDepth 4096
set_option maxHeartbeats 0

namespace GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116

def scheduleName : String := "SkourasVenturaPilot"
def sourceRules : List (String × String) := [("pictures", ""), ("receipts", ""), ("eligible_costs", ""), ("policy", ""), ("prepayment", ""), ("incorporated_policy_0", ""), ("accounting_period", ""), ("require@4:1", ""), ("require@5:1", ""), ("title_results", ""), ("settlement_participant", ""), ("earned_total", ""), ("recouped", "SV-7-POOL-RECOVERY"), ("payable", ""), ("prepayment", ""), ("require@28:3", ""), ("titles", ""), ("pool", "")]

def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := (do
  let _spl_v0 ← SPL.lookup _inputs "pictures"
  let _spl_v1 ← SPL.lookup _inputs "receipts"
  let _spl_v2 ← SPL.lookup _inputs "eligible_costs"
  let _spl_v3 ← SPL.lookup _inputs "policy"
  let _spl_v4 ← SPL.lookup _openings "prepayment"
  let _spl_v5 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (pure (.text "sv-incurred@1")))
  let _spl_v6 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.field (← (pure _spl_v3)) "period"))
  let _spl_v7 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.mapValues (← (pure _spl_v0)) (fun _spl_v12 => (do
      let _spl_v13 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
        SPL.sumValues (← (do
          SPL.filterValues (← (pure _spl_v1)) (fun _spl_v20 => (SPL.conjunction (do
            SPL.binary "==" (← (do
              SPL.field (← (pure _spl_v20)) "asset_id")) (← (do
              SPL.field (← (pure _spl_v12)) "asset_id"))) (fun _ => (do
            SPL.inPeriod (← (do
              SPL.field (← (pure _spl_v20)) "cash_received_date")) (← (_spl_v6.get)))))))) (fun _spl_v19 => (do
          SPL.field (← (pure _spl_v19)) "amount"))))
      let _spl_v14 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (SPL.conditional (do
        SPL.unary "not" (← (do
          SPL.field (← (pure _spl_v12)) "contribution_present"))) (fun _ => (do
        SPL.Core.numericBinary .multiply (← (do
          SPL.Core.numericBinary .divide (← (pure (.num (mkRat 250 10)))) (← (pure (.num (mkRat 100 1)))))) (← (_spl_v13.get)))) (fun _ => (do
        SPL.Core.numericBinary .multiply (← (do
          SPL.Core.numericBinary .divide (← (pure (.num (mkRat 75 10)))) (← (pure (.num (mkRat 100 1)))))) (← (_spl_v13.get))))))
      let _spl_v15 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (SPL.conditional (do
        SPL.unary "not" (← (do
          SPL.field (← (pure _spl_v12)) "contribution_present"))) (fun _ => (do
        SPL.sumValues (← (do
          SPL.filterValues (← (pure _spl_v2)) (fun _spl_v22 => (SPL.conjunction (do
            SPL.binary "==" (← (do
              SPL.field (← (pure _spl_v22)) "asset_id")) (← (do
              SPL.field (← (pure _spl_v12)) "asset_id"))) (fun _ => (do
            SPL.inPeriod (← (do
              SPL.field (← (pure _spl_v22)) "incurred_date")) (← (_spl_v6.get)))))))) (fun _spl_v21 => (do
          SPL.field (← (pure _spl_v21)) "amount")))) (fun _ => (do
        SPL.sumValues (← (do
          SPL.filterValues (← (pure _spl_v2)) (fun _spl_v24 => (SPL.conjunction (do
            SPL.binary "==" (← (do
              SPL.field (← (pure _spl_v24)) "asset_id")) (← (do
              SPL.field (← (pure _spl_v12)) "asset_id"))) (fun _ => (do
            SPL.inPeriod (← (do
              SPL.field (← (pure _spl_v24)) "incurred_date")) (← (_spl_v6.get)))))))) (fun _spl_v23 => (do
          SPL.field (← (pure _spl_v23)) "amount"))))))
      let _spl_v16 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (SPL.conditional (do
        SPL.unary "not" (← (do
          SPL.field (← (pure _spl_v12)) "contribution_present"))) (fun _ => (do
        SPL.Core.numericBinary .subtract (← (do
          SPL.Core.numericBinary .subtract (← (_spl_v13.get)) (← (_spl_v14.get)))) (← (_spl_v15.get)))) (fun _ => (do
        SPL.Core.numericBinary .subtract (← (do
          SPL.Core.numericBinary .subtract (← (_spl_v13.get)) (← (_spl_v14.get)))) (← (_spl_v15.get))))))
      let _spl_v17 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (SPL.conditional (do
        SPL.unary "not" (← (do
          SPL.field (← (pure _spl_v12)) "contribution_present"))) (fun _ => (do
        SPL.Core.numericBinary .divide (← (pure (.num (mkRat 200 10)))) (← (pure (.num (mkRat 100 1)))))) (fun _ => (do
        SPL.field (← (pure _spl_v12)) "funding_share"))))
      let _spl_v18 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (SPL.conditional (do
        SPL.unary "not" (← (do
          SPL.field (← (pure _spl_v12)) "contribution_present"))) (fun _ => (do
        SPL.Core.numericBinary .multiply (← (_spl_v17.get)) (← (_spl_v16.get)))) (fun _ => (do
        SPL.Core.numericBinary .multiply (← (_spl_v17.get)) (← (_spl_v16.get))))))
      SPL.assertValue (← (SPL.conjunction (do
        SPL.binary ">=" (← (do
          SPL.field (← (pure _spl_v12)) "funding_share")) (← (pure (.num (mkRat 0 1))))) (fun _ => (do
        SPL.binary "<=" (← (do
          SPL.field (← (pure _spl_v12)) "funding_share")) (← (pure (.num (mkRat 1 1)))))))) "INVALID_FUNDING_SHARE"
      let _spl_v25 ← (_spl_v13.get)
      let _spl_v26 ← (_spl_v14.get)
      let _spl_v27 ← (_spl_v15.get)
      let _spl_v28 ← (_spl_v16.get)
      let _spl_v29 ← (_spl_v17.get)
      let _spl_v30 ← (_spl_v18.get)
      SPL.assertValue (← (do
        SPL.binary ">=" (← (pure _spl_v30)) (← (pure (.num (mkRat 0 1)))))) "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT"
      (SPL.recordValues [("asset_id", (do
        SPL.field (← (pure _spl_v12)) "asset_id")), ("cash", (pure _spl_v25)), ("fee", (pure _spl_v26)), ("allowed_cost", (pure _spl_v27)), ("basis", (pure _spl_v28)), ("share", (pure _spl_v29)), ("earned", (pure _spl_v30))])))))
  let _spl_v8 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.field (← (pure _spl_v3)) "participant_id"))
  let _spl_v9 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.sumValues (← (_spl_v7.get)) (fun _spl_v31 => (do
      SPL.field (← (pure _spl_v31)) "earned"))))
  let _spl_v10 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.extrema false (← (_spl_v9.get)) (← (pure _spl_v4))))
  let _spl_v11 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => (do
    SPL.Core.numericBinary .subtract (← (_spl_v9.get)) (← (_spl_v10.get))))
  let _spl_v32 ← (_spl_v5.get)
  let _spl_v33 ← (_spl_v6.get)
  SPL.assertValue (← (do
    SPL.isCalendarQuarter (← (pure _spl_v33)))) "READABLE_CALENDAR_QUARTER_REQUIRED"
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v4)) (← (pure (.num (mkRat 0 1)))))) "NEGATIVE_OPENING_ADVANCE"
  let _spl_v34 ← (_spl_v7.get)
  let _spl_v35 ← (_spl_v8.get)
  let _spl_v36 ← (_spl_v9.get)
  let _spl_v37 ← (_spl_v10.get)
  let _spl_v38 ← (_spl_v11.get)
  SPL.assertValue (← (do
    SPL.binary "==" (← (pure _spl_v36)) (← (do
      SPL.Core.numericBinary .add (← (pure _spl_v37)) (← (pure _spl_v38)))))) "SV_SETTLEMENT_RECONCILIATION"
  let _spl_v39 ← (do
    SPL.Core.numericBinary .subtract (← (pure _spl_v4)) (← (pure _spl_v37)))
  let _spl_v40 ← (pure _spl_v34)
  let _spl_v41 ← (SPL.recordValues [("agreement_id", (do
    SPL.field (← (pure _spl_v3)) "agreement_id")), ("participant_id", (pure _spl_v35)), ("pool_id", (do
    SPL.field (← (pure _spl_v3)) "pool_id")), ("period", (pure _spl_v33)), ("earned", (pure _spl_v36)), ("recouped", (pure _spl_v37)), ("payable", (pure _spl_v38))])
  pure { emissions := [("titles", _spl_v40), ("pool", _spl_v41)], closing := [("prepayment", _spl_v39)] })

end GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116

namespace GeneratedSPL
abbrev scheduleName := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.scheduleName
abbrev sourceRules := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.sourceRules
abbrev settle := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.settle
end GeneratedSPL

def main (args : List String) : IO UInt32 :=
  SPL.Bindings.runMain [("pictures", (.named "List" [(.named "SVPicture" [])])), ("receipts", (.named "List" [(.named "SVReceipt" [])])), ("eligible_costs", (.named "List" [(.named "SVCost" [])])), ("policy", (.named "SVPolicy" []))] [("prepayment", (.named "Money" [(.named "USD" [])]))] GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.settle args
