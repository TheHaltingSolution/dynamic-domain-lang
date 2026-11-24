import SPL.Fold
import SPL.Core
import SPL.Bindings

set_option maxRecDepth 4096
set_option maxHeartbeats 0

namespace GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116

def scheduleName : String := "SkourasVenturaPilot"
def sourceRules : List (String × String) := [("pictures", ""), ("receipts", ""), ("eligible_costs", ""), ("policy", ""), ("prepayment", ""), ("require@8:3", ""), ("title_results", ""), ("earned_total", ""), ("recouped", "SV-7-POOL-RECOVERY"), ("payable", ""), ("prepayment", ""), ("require@35:3", ""), ("titles", ""), ("pool", "")]

def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := (do
  let _spl_v0 ← SPL.lookup _inputs "pictures"
  let _spl_v1 ← SPL.lookup _inputs "receipts"
  let _spl_v2 ← SPL.lookup _inputs "eligible_costs"
  let _spl_v3 ← SPL.lookup _inputs "policy"
  let _spl_v4 ← SPL.lookup _openings "prepayment"
  let _spl_v5 : Unit → SPL.Eval SPL.Value := fun _ => (do
    SPL.mapValues (← (pure _spl_v0)) (fun _spl_v9 => (do
      let _spl_v10 : Unit → SPL.Eval SPL.Value := fun _ => (do
        SPL.filterValues (← (pure _spl_v1)) (fun _spl_v19 => (SPL.conjunction (do
          SPL.binary "==" (← (do
            SPL.field (← (pure _spl_v19)) "asset_id")) (← (do
            SPL.field (← (pure _spl_v9)) "asset_id"))) (fun _ => (do
          SPL.inPeriod (← (do
            SPL.field (← (pure _spl_v19)) "cash_received_date")) (← (do
            SPL.field (← (pure _spl_v3)) "period")))))))
      let _spl_v11 : Unit → SPL.Eval SPL.Value := fun _ => (do
        SPL.filterValues (← (pure _spl_v2)) (fun _spl_v20 => (SPL.conjunction (do
          SPL.binary "==" (← (do
            SPL.field (← (pure _spl_v20)) "asset_id")) (← (do
            SPL.field (← (pure _spl_v9)) "asset_id"))) (fun _ => (do
          SPL.inPeriod (← (do
            SPL.field (← (pure _spl_v20)) "incurred_date")) (← (do
            SPL.field (← (pure _spl_v3)) "period")))))))
      let _spl_v12 : Unit → SPL.Eval SPL.Value := fun _ => (do
        SPL.sumValues (← (_spl_v10 ())) (fun _spl_v21 => (do
          SPL.field (← (pure _spl_v21)) "amount")))
      let _spl_v13 : Unit → SPL.Eval SPL.Value := fun _ => (do
        SPL.sumValues (← (_spl_v11 ())) (fun _spl_v22 => (do
          SPL.field (← (pure _spl_v22)) "amount")))
      let _spl_v14 : Unit → SPL.Eval SPL.Value := fun _ => (SPL.choose [((do
        SPL.field (← (pure _spl_v9)) "contribution_present"), (fun _ => (pure (.num (mkRat 75 1000)))))] (some (fun _ => (pure (.num (mkRat 25 100))))))
      let _spl_v15 : Unit → SPL.Eval SPL.Value := fun _ => (do
        SPL.Core.numericBinary .multiply (← (_spl_v12 ())) (← (_spl_v14 ())))
      let _spl_v16 : Unit → SPL.Eval SPL.Value := fun _ => (do
        SPL.Core.numericBinary .subtract (← (do
          SPL.Core.numericBinary .subtract (← (_spl_v12 ())) (← (_spl_v15 ())))) (← (_spl_v13 ())))
      let _spl_v17 : Unit → SPL.Eval SPL.Value := fun _ => (SPL.conditional (do
        SPL.field (← (pure _spl_v9)) "contribution_present") (fun _ => (do
        SPL.field (← (pure _spl_v9)) "funding_share")) (fun _ => (pure (.num (mkRat 20 100)))))
      let _spl_v18 : Unit → SPL.Eval SPL.Value := fun _ => (do
        SPL.Core.numericBinary .multiply (← (_spl_v16 ())) (← (_spl_v17 ())))
      SPL.assertValue (← (SPL.conjunction (do
        SPL.binary ">=" (← (do
          SPL.field (← (pure _spl_v9)) "funding_share")) (← (pure (.num (mkRat 0 1))))) (fun _ => (do
        SPL.binary "<=" (← (do
          SPL.field (← (pure _spl_v9)) "funding_share")) (← (pure (.num (mkRat 1 1)))))))) "INVALID_FUNDING_SHARE"
      let _spl_v23 ← (_spl_v10 ())
      let _spl_v24 ← (_spl_v11 ())
      let _spl_v25 ← (_spl_v12 ())
      let _spl_v26 ← (_spl_v13 ())
      let _spl_v27 ← (_spl_v14 ())
      let _spl_v28 ← (_spl_v15 ())
      let _spl_v29 ← (_spl_v16 ())
      let _spl_v30 ← (_spl_v17 ())
      let _spl_v31 ← (_spl_v18 ())
      SPL.assertValue (← (do
        SPL.binary ">=" (← (pure _spl_v31)) (← (pure (.num (mkRat 0 1)))))) "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT"
      (SPL.recordValues [("asset_id", (do
        SPL.field (← (pure _spl_v9)) "asset_id")), ("cash", (pure _spl_v25)), ("fee", (pure _spl_v28)), ("allowed_cost", (pure _spl_v26)), ("basis", (pure _spl_v29)), ("share", (pure _spl_v30)), ("earned", (pure _spl_v31))]))))
  let _spl_v6 : Unit → SPL.Eval SPL.Value := fun _ => (do
    SPL.sumValues (← (_spl_v5 ())) (fun _spl_v32 => (do
      SPL.field (← (pure _spl_v32)) "earned")))
  let _spl_v7 : Unit → SPL.Eval SPL.Value := fun _ => (do
    SPL.extrema false (← (_spl_v6 ())) (← (pure _spl_v4)))
  let _spl_v8 : Unit → SPL.Eval SPL.Value := fun _ => (do
    SPL.Core.numericBinary .subtract (← (_spl_v6 ())) (← (_spl_v7 ())))
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v4)) (← (pure (.num (mkRat 0 1)))))) "NEGATIVE_OPENING_ADVANCE"
  let _spl_v33 ← (_spl_v5 ())
  let _spl_v34 ← (_spl_v6 ())
  let _spl_v35 ← (_spl_v7 ())
  let _spl_v36 ← (_spl_v8 ())
  SPL.assertValue (← (do
    SPL.binary "==" (← (pure _spl_v34)) (← (do
      SPL.Core.numericBinary .add (← (pure _spl_v35)) (← (pure _spl_v36)))))) "SV_SETTLEMENT_RECONCILIATION"
  let _spl_v37 ← (do
    SPL.Core.numericBinary .subtract (← (pure _spl_v4)) (← (pure _spl_v35)))
  let _spl_v38 ← (pure _spl_v33)
  let _spl_v39 ← (SPL.recordValues [("agreement_id", (do
    SPL.field (← (pure _spl_v3)) "agreement_id")), ("participant_id", (do
    SPL.field (← (pure _spl_v3)) "participant_id")), ("pool_id", (do
    SPL.field (← (pure _spl_v3)) "pool_id")), ("period", (do
    SPL.field (← (pure _spl_v3)) "period")), ("earned", (pure _spl_v34)), ("recouped", (pure _spl_v35)), ("payable", (pure _spl_v36))])
  pure { emissions := [("titles", _spl_v38), ("pool", _spl_v39)], closing := [("prepayment", _spl_v37)] })

end GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116
