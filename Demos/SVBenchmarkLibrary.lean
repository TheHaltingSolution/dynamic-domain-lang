import SPL.Fold
import SPL.Core
import SPL.Bindings

set_option maxRecDepth 4096
set_option maxHeartbeats 0

namespace GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116

def scheduleName : String := "SkourasVenturaPilot"
def sourceRules : List (String × String) := [("pictures", ""), ("receipts", ""), ("eligible_costs", ""), ("policy", ""), ("prepayment", ""), ("require@8:3", ""), ("title_results", ""), ("earned_total", ""), ("recouped", "SV-7-POOL-RECOVERY"), ("payable", ""), ("prepayment", ""), ("require@35:3", ""), ("titles", ""), ("pool", "")]

@[noinline] private def _spl_v24 (_spl_v25 : Thunk (SPL.Eval SPL.Value)) (_spl_v26 : Thunk (SPL.Eval SPL.Value)) (_spl_v27 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.filterValues (← (_spl_v25.get)) (fun _spl_v28 => (SPL.conjunction (do
    SPL.binary "==" (← (do
      SPL.field (← (pure _spl_v28)) "asset_id")) (← (do
      SPL.field (← (_spl_v26.get)) "asset_id"))) (fun _ => (do
    SPL.inPeriod (← (do
      SPL.field (← (pure _spl_v28)) "cash_received_date")) (← (do
      SPL.field (← (_spl_v27.get)) "period")))))))

@[noinline] private def _spl_v29 (_spl_v30 : Thunk (SPL.Eval SPL.Value)) (_spl_v31 : Thunk (SPL.Eval SPL.Value)) (_spl_v32 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.filterValues (← (_spl_v30.get)) (fun _spl_v33 => (SPL.conjunction (do
    SPL.binary "==" (← (do
      SPL.field (← (pure _spl_v33)) "asset_id")) (← (do
      SPL.field (← (_spl_v31.get)) "asset_id"))) (fun _ => (do
    SPL.inPeriod (← (do
      SPL.field (← (pure _spl_v33)) "incurred_date")) (← (do
      SPL.field (← (_spl_v32.get)) "period")))))))

@[noinline] private def _spl_v34 (_spl_v35 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v35.get)) (fun _spl_v36 => (do
    SPL.field (← (pure _spl_v36)) "amount")))

@[noinline] private def _spl_v37 (_spl_v38 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v38.get)) (fun _spl_v39 => (do
    SPL.field (← (pure _spl_v39)) "amount")))

@[noinline] private def _spl_v40 (_spl_v41 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.choose [((do
  SPL.field (← (_spl_v41.get)) "contribution_present"), (fun _ => (pure (.num (mkRat 75 1000)))))] (some (fun _ => (pure (.num (mkRat 25 100))))))

@[noinline] private def _spl_v42 (_spl_v43 : Thunk (SPL.Eval SPL.Value)) (_spl_v44 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .multiply (← (_spl_v43.get)) (← (_spl_v44.get)))

@[noinline] private def _spl_v45 (_spl_v46 : Thunk (SPL.Eval SPL.Value)) (_spl_v47 : Thunk (SPL.Eval SPL.Value)) (_spl_v48 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .subtract (← (do
    SPL.Core.numericBinary .subtract (← (_spl_v46.get)) (← (_spl_v47.get)))) (← (_spl_v48.get)))

@[noinline] private def _spl_v49 (_spl_v50 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.field (← (_spl_v50.get)) "contribution_present") (fun _ => (do
  SPL.field (← (_spl_v50.get)) "funding_share")) (fun _ => (pure (.num (mkRat 20 100)))))

@[noinline] private def _spl_v51 (_spl_v52 : Thunk (SPL.Eval SPL.Value)) (_spl_v53 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .multiply (← (_spl_v52.get)) (← (_spl_v53.get)))

@[noinline] private def _spl_v9 (_spl_v10 : Thunk (SPL.Eval SPL.Value)) (_spl_v11 : Thunk (SPL.Eval SPL.Value)) (_spl_v12 : Thunk (SPL.Eval SPL.Value)) (_spl_v13 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.mapValues (← (_spl_v10.get)) (fun _spl_v14 => (do
    let _spl_v15 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v24 (Thunk.mk (fun _ => (_spl_v11.get))) (Thunk.mk (fun _ => (pure _spl_v14))) (Thunk.mk (fun _ => (_spl_v12.get))) ())
    let _spl_v16 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v29 (Thunk.mk (fun _ => (_spl_v13.get))) (Thunk.mk (fun _ => (pure _spl_v14))) (Thunk.mk (fun _ => (_spl_v12.get))) ())
    let _spl_v17 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v34 (Thunk.mk (fun _ => (_spl_v15.get))) ())
    let _spl_v18 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v37 (Thunk.mk (fun _ => (_spl_v16.get))) ())
    let _spl_v19 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v40 (Thunk.mk (fun _ => (pure _spl_v14))) ())
    let _spl_v20 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v42 (Thunk.mk (fun _ => (_spl_v17.get))) (Thunk.mk (fun _ => (_spl_v19.get))) ())
    let _spl_v21 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v45 (Thunk.mk (fun _ => (_spl_v17.get))) (Thunk.mk (fun _ => (_spl_v20.get))) (Thunk.mk (fun _ => (_spl_v18.get))) ())
    let _spl_v22 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v49 (Thunk.mk (fun _ => (pure _spl_v14))) ())
    let _spl_v23 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v51 (Thunk.mk (fun _ => (_spl_v21.get))) (Thunk.mk (fun _ => (_spl_v22.get))) ())
    SPL.assertValue (← (SPL.conjunction (do
      SPL.binary ">=" (← (do
        SPL.field (← (pure _spl_v14)) "funding_share")) (← (pure (.num (mkRat 0 1))))) (fun _ => (do
      SPL.binary "<=" (← (do
        SPL.field (← (pure _spl_v14)) "funding_share")) (← (pure (.num (mkRat 1 1)))))))) "INVALID_FUNDING_SHARE"
    let _spl_v54 ← (_spl_v15.get)
    let _spl_v55 ← (_spl_v16.get)
    let _spl_v56 ← (_spl_v17.get)
    let _spl_v57 ← (_spl_v18.get)
    let _spl_v58 ← (_spl_v19.get)
    let _spl_v59 ← (_spl_v20.get)
    let _spl_v60 ← (_spl_v21.get)
    let _spl_v61 ← (_spl_v22.get)
    let _spl_v62 ← (_spl_v23.get)
    SPL.assertValue (← (do
      SPL.binary ">=" (← (pure _spl_v62)) (← (pure (.num (mkRat 0 1)))))) "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT"
    (SPL.recordValues [("asset_id", (do
      SPL.field (← (pure _spl_v14)) "asset_id")), ("cash", (pure _spl_v56)), ("fee", (pure _spl_v59)), ("allowed_cost", (pure _spl_v57)), ("basis", (pure _spl_v60)), ("share", (pure _spl_v61)), ("earned", (pure _spl_v62))]))))

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
  let _spl_v5 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v9 (Thunk.mk (fun _ => (pure _spl_v0))) (Thunk.mk (fun _ => (pure _spl_v1))) (Thunk.mk (fun _ => (pure _spl_v3))) (Thunk.mk (fun _ => (pure _spl_v2))) ())
  let _spl_v6 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v63 (Thunk.mk (fun _ => (_spl_v5.get))) ())
  let _spl_v7 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v66 (Thunk.mk (fun _ => (_spl_v6.get))) (Thunk.mk (fun _ => (pure _spl_v4))) ())
  let _spl_v8 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v69 (Thunk.mk (fun _ => (_spl_v6.get))) (Thunk.mk (fun _ => (_spl_v7.get))) ())
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v4)) (← (pure (.num (mkRat 0 1)))))) "NEGATIVE_OPENING_ADVANCE"
  let _spl_v72 ← (_spl_v5.get)
  let _spl_v73 ← (_spl_v6.get)
  let _spl_v74 ← (_spl_v7.get)
  let _spl_v75 ← (_spl_v8.get)
  SPL.assertValue (← (do
    SPL.binary "==" (← (pure _spl_v73)) (← (do
      SPL.Core.numericBinary .add (← (pure _spl_v74)) (← (pure _spl_v75)))))) "SV_SETTLEMENT_RECONCILIATION"
  let _spl_v76 ← (do
    SPL.Core.numericBinary .subtract (← (pure _spl_v4)) (← (pure _spl_v74)))
  let _spl_v77 ← (pure _spl_v72)
  let _spl_v78 ← (SPL.recordValues [("agreement_id", (do
    SPL.field (← (pure _spl_v3)) "agreement_id")), ("participant_id", (do
    SPL.field (← (pure _spl_v3)) "participant_id")), ("pool_id", (do
    SPL.field (← (pure _spl_v3)) "pool_id")), ("period", (do
    SPL.field (← (pure _spl_v3)) "period")), ("earned", (pure _spl_v73)), ("recouped", (pure _spl_v74)), ("payable", (pure _spl_v75))])
  pure { emissions := [("titles", _spl_v77), ("pool", _spl_v78)], closing := [("prepayment", _spl_v76)] })

end GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_80_105_108_111_116
