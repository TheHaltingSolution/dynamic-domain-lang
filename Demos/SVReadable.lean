import SPL.Fold
import SPL.Core
import SPL.Bindings

set_option maxRecDepth 4096
set_option maxHeartbeats 0

namespace GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116

def scheduleName : String := "SkourasVenturaPilot"
def sourceRules : List (String × String) := [("pictures", ""), ("receipts", ""), ("eligible_costs", ""), ("policy", ""), ("prepayment", ""), ("incorporated_policy_0", ""), ("accounting_period", ""), ("require@4:1", ""), ("require@5:1", ""), ("title_results", ""), ("settlement_participant", ""), ("earned_total", ""), ("recouped", "SV-7-POOL-RECOVERY"), ("payable", ""), ("prepayment", ""), ("require@28:3", ""), ("titles", ""), ("pool", "")]

@[noinline] private def _spl_v12  (_spl_force : Unit) : SPL.Eval SPL.Value := (pure (.text "sv-incurred@1"))

@[noinline] private def _spl_v13 (_spl_v14 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.field (← (_spl_v14.get)) "period")

@[noinline] private def _spl_v27 (_spl_v28 : Thunk (SPL.Eval SPL.Value)) (_spl_v29 : Thunk (SPL.Eval SPL.Value)) (_spl_v30 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (do
    SPL.filterValues (← (_spl_v28.get)) (fun _spl_v32 => (SPL.conjunction (do
      SPL.binary "==" (← (do
        SPL.field (← (pure _spl_v32)) "asset_id")) (← (do
        SPL.field (← (_spl_v29.get)) "asset_id"))) (fun _ => (do
      SPL.inPeriod (← (do
        SPL.field (← (pure _spl_v32)) "cash_received_date")) (← (_spl_v30.get)))))))) (fun _spl_v31 => (do
    SPL.field (← (pure _spl_v31)) "amount")))

@[noinline] private def _spl_v33 (_spl_v34 : Thunk (SPL.Eval SPL.Value)) (_spl_v35 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.unary "not" (← (do
    SPL.field (← (_spl_v34.get)) "contribution_present"))) (fun _ => (do
  SPL.Core.numericBinary .multiply (← (do
    SPL.Core.numericBinary .divide (← (pure (.num (mkRat 250 10)))) (← (pure (.num (mkRat 100 1)))))) (← (_spl_v35.get)))) (fun _ => (do
  SPL.Core.numericBinary .multiply (← (do
    SPL.Core.numericBinary .divide (← (pure (.num (mkRat 75 10)))) (← (pure (.num (mkRat 100 1)))))) (← (_spl_v35.get)))))

@[noinline] private def _spl_v36 (_spl_v37 : Thunk (SPL.Eval SPL.Value)) (_spl_v38 : Thunk (SPL.Eval SPL.Value)) (_spl_v39 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.unary "not" (← (do
    SPL.field (← (_spl_v37.get)) "contribution_present"))) (fun _ => (do
  SPL.sumValues (← (do
    SPL.filterValues (← (_spl_v38.get)) (fun _spl_v41 => (SPL.conjunction (do
      SPL.binary "==" (← (do
        SPL.field (← (pure _spl_v41)) "asset_id")) (← (do
        SPL.field (← (_spl_v37.get)) "asset_id"))) (fun _ => (do
      SPL.inPeriod (← (do
        SPL.field (← (pure _spl_v41)) "incurred_date")) (← (_spl_v39.get)))))))) (fun _spl_v40 => (do
    SPL.field (← (pure _spl_v40)) "amount")))) (fun _ => (do
  SPL.sumValues (← (do
    SPL.filterValues (← (_spl_v38.get)) (fun _spl_v43 => (SPL.conjunction (do
      SPL.binary "==" (← (do
        SPL.field (← (pure _spl_v43)) "asset_id")) (← (do
        SPL.field (← (_spl_v37.get)) "asset_id"))) (fun _ => (do
      SPL.inPeriod (← (do
        SPL.field (← (pure _spl_v43)) "incurred_date")) (← (_spl_v39.get)))))))) (fun _spl_v42 => (do
    SPL.field (← (pure _spl_v42)) "amount")))))

@[noinline] private def _spl_v44 (_spl_v45 : Thunk (SPL.Eval SPL.Value)) (_spl_v46 : Thunk (SPL.Eval SPL.Value)) (_spl_v47 : Thunk (SPL.Eval SPL.Value)) (_spl_v48 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.unary "not" (← (do
    SPL.field (← (_spl_v45.get)) "contribution_present"))) (fun _ => (do
  SPL.Core.numericBinary .subtract (← (do
    SPL.Core.numericBinary .subtract (← (_spl_v46.get)) (← (_spl_v47.get)))) (← (_spl_v48.get)))) (fun _ => (do
  SPL.Core.numericBinary .subtract (← (do
    SPL.Core.numericBinary .subtract (← (_spl_v46.get)) (← (_spl_v47.get)))) (← (_spl_v48.get)))))

@[noinline] private def _spl_v49 (_spl_v50 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.unary "not" (← (do
    SPL.field (← (_spl_v50.get)) "contribution_present"))) (fun _ => (do
  SPL.Core.numericBinary .divide (← (pure (.num (mkRat 200 10)))) (← (pure (.num (mkRat 100 1)))))) (fun _ => (do
  SPL.field (← (_spl_v50.get)) "funding_share")))

@[noinline] private def _spl_v51 (_spl_v52 : Thunk (SPL.Eval SPL.Value)) (_spl_v53 : Thunk (SPL.Eval SPL.Value)) (_spl_v54 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.unary "not" (← (do
    SPL.field (← (_spl_v52.get)) "contribution_present"))) (fun _ => (do
  SPL.Core.numericBinary .multiply (← (_spl_v53.get)) (← (_spl_v54.get)))) (fun _ => (do
  SPL.Core.numericBinary .multiply (← (_spl_v53.get)) (← (_spl_v54.get)))))

@[noinline] private def _spl_v15 (_spl_v16 : Thunk (SPL.Eval SPL.Value)) (_spl_v17 : Thunk (SPL.Eval SPL.Value)) (_spl_v18 : Thunk (SPL.Eval SPL.Value)) (_spl_v19 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.mapValues (← (_spl_v16.get)) (fun _spl_v20 => (do
    let _spl_v21 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v27 (Thunk.mk (fun _ => (_spl_v17.get))) (Thunk.mk (fun _ => (pure _spl_v20))) (Thunk.mk (fun _ => (_spl_v18.get))) ())
    let _spl_v22 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v33 (Thunk.mk (fun _ => (pure _spl_v20))) (Thunk.mk (fun _ => (_spl_v21.get))) ())
    let _spl_v23 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v36 (Thunk.mk (fun _ => (pure _spl_v20))) (Thunk.mk (fun _ => (_spl_v19.get))) (Thunk.mk (fun _ => (_spl_v18.get))) ())
    let _spl_v24 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v44 (Thunk.mk (fun _ => (pure _spl_v20))) (Thunk.mk (fun _ => (_spl_v21.get))) (Thunk.mk (fun _ => (_spl_v22.get))) (Thunk.mk (fun _ => (_spl_v23.get))) ())
    let _spl_v25 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v49 (Thunk.mk (fun _ => (pure _spl_v20))) ())
    let _spl_v26 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v51 (Thunk.mk (fun _ => (pure _spl_v20))) (Thunk.mk (fun _ => (_spl_v25.get))) (Thunk.mk (fun _ => (_spl_v24.get))) ())
    SPL.assertValue (← (SPL.conjunction (do
      SPL.binary ">=" (← (do
        SPL.field (← (pure _spl_v20)) "funding_share")) (← (pure (.num (mkRat 0 1))))) (fun _ => (do
      SPL.binary "<=" (← (do
        SPL.field (← (pure _spl_v20)) "funding_share")) (← (pure (.num (mkRat 1 1)))))))) "INVALID_FUNDING_SHARE"
    let _spl_v55 ← (_spl_v21.get)
    let _spl_v56 ← (_spl_v22.get)
    let _spl_v57 ← (_spl_v23.get)
    let _spl_v58 ← (_spl_v24.get)
    let _spl_v59 ← (_spl_v25.get)
    let _spl_v60 ← (_spl_v26.get)
    SPL.assertValue (← (do
      SPL.binary ">=" (← (pure _spl_v60)) (← (pure (.num (mkRat 0 1)))))) "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT"
    (SPL.recordValues [("asset_id", (do
      SPL.field (← (pure _spl_v20)) "asset_id")), ("cash", (pure _spl_v55)), ("fee", (pure _spl_v56)), ("allowed_cost", (pure _spl_v57)), ("basis", (pure _spl_v58)), ("share", (pure _spl_v59)), ("earned", (pure _spl_v60))]))))

@[noinline] private def _spl_v61 (_spl_v62 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.field (← (_spl_v62.get)) "participant_id")

@[noinline] private def _spl_v63 (_spl_v64 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v64.get)) (fun _spl_v65 => (do
    SPL.field (← (pure _spl_v65)) "earned")))

@[noinline] private def _spl_v66 (_spl_v67 : Thunk (SPL.Eval SPL.Value)) (_spl_v68 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.extrema false (← (_spl_v67.get)) (← (_spl_v68.get)))

@[noinline] private def _spl_v69 (_spl_v70 : Thunk (SPL.Eval SPL.Value)) (_spl_v71 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .subtract (← (_spl_v70.get)) (← (_spl_v71.get)))

def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := (do
  let _spl_v0 ← SPL.lookup _inputs "pictures"
  let _spl_v1 ← SPL.lookup _inputs "receipts"
  let _spl_v2 ← SPL.lookup _inputs "eligible_costs"
  let _spl_v3 ← SPL.lookup _inputs "policy"
  let _spl_v4 ← SPL.lookup _openings "prepayment"
  let _spl_v5 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v12  ())
  let _spl_v6 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v13 (Thunk.mk (fun _ => (pure _spl_v3))) ())
  let _spl_v7 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v15 (Thunk.mk (fun _ => (pure _spl_v0))) (Thunk.mk (fun _ => (pure _spl_v1))) (Thunk.mk (fun _ => (_spl_v6.get))) (Thunk.mk (fun _ => (pure _spl_v2))) ())
  let _spl_v8 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v61 (Thunk.mk (fun _ => (pure _spl_v3))) ())
  let _spl_v9 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v63 (Thunk.mk (fun _ => (_spl_v7.get))) ())
  let _spl_v10 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v66 (Thunk.mk (fun _ => (_spl_v9.get))) (Thunk.mk (fun _ => (pure _spl_v4))) ())
  let _spl_v11 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v69 (Thunk.mk (fun _ => (_spl_v9.get))) (Thunk.mk (fun _ => (_spl_v10.get))) ())
  let _spl_v72 ← (_spl_v5.get)
  let _spl_v73 ← (_spl_v6.get)
  SPL.assertValue (← (do
    SPL.isCalendarQuarter (← (pure _spl_v73)))) "READABLE_CALENDAR_QUARTER_REQUIRED"
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v4)) (← (pure (.num (mkRat 0 1)))))) "NEGATIVE_OPENING_ADVANCE"
  let _spl_v74 ← (_spl_v7.get)
  let _spl_v75 ← (_spl_v8.get)
  let _spl_v76 ← (_spl_v9.get)
  let _spl_v77 ← (_spl_v10.get)
  let _spl_v78 ← (_spl_v11.get)
  SPL.assertValue (← (do
    SPL.binary "==" (← (pure _spl_v76)) (← (do
      SPL.Core.numericBinary .add (← (pure _spl_v77)) (← (pure _spl_v78)))))) "SV_SETTLEMENT_RECONCILIATION"
  let _spl_v79 ← (do
    SPL.Core.numericBinary .subtract (← (pure _spl_v4)) (← (pure _spl_v77)))
  let _spl_v80 ← (pure _spl_v74)
  let _spl_v81 ← (SPL.recordValues [("agreement_id", (do
    SPL.field (← (pure _spl_v3)) "agreement_id")), ("participant_id", (pure _spl_v75)), ("pool_id", (do
    SPL.field (← (pure _spl_v3)) "pool_id")), ("period", (pure _spl_v73)), ("earned", (pure _spl_v76)), ("recouped", (pure _spl_v77)), ("payable", (pure _spl_v78))])
  pure { emissions := [("titles", _spl_v80), ("pool", _spl_v81)], closing := [("prepayment", _spl_v79)] })

end GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116

namespace GeneratedSPL
abbrev scheduleName := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.scheduleName
abbrev sourceRules := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.sourceRules
abbrev settle := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.settle
end GeneratedSPL

def main (args : List String) : IO UInt32 :=
  SPL.Bindings.runMain [("pictures", (.named "List" [(.named "SVPicture" [])])), ("receipts", (.named "List" [(.named "SVReceipt" [])])), ("eligible_costs", (.named "List" [(.named "SVCost" [])])), ("policy", (.named "SVPolicy" []))] [("prepayment", (.named "Money" [(.named "USD" [])]))] GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116.settle args
