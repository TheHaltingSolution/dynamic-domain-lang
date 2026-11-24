import SPL.Fold
import SPL.Core
import SPL.Bindings

set_option maxRecDepth 4096
set_option maxHeartbeats 0

namespace GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116

def scheduleName : String := "SkourasVenturaIndexedExperiment"
def sourceRules : List (String × String) := [("pictures", ""), ("receipts", ""), ("eligible_costs", ""), ("policy", ""), ("prepayment", ""), ("require@8:3", ""), ("picture_count", ""), ("receipts_by_asset", ""), ("costs_by_asset", ""), ("title_results", ""), ("earned_total", ""), ("recouped", "SV-7-POOL-RECOVERY"), ("payable", ""), ("prepayment", ""), ("require@38:3", ""), ("titles", ""), ("pool", "")]

@[noinline] private def _spl_v12 (_spl_v13 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v13.get)) (fun _spl_v14 => (pure (.num (mkRat 1 1)))))

@[noinline] private def _spl_v15 (_spl_v16 : Thunk (SPL.Eval SPL.Value)) (_spl_v17 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.groupValues (← (SPL.conditional (do
    SPL.binary ">" (← (_spl_v16.get)) (← (pure (.num (mkRat 0 1))))) (fun _ => (_spl_v17.get)) (fun _ => (SPL.listValues [])))) (fun _spl_v18 => (do
    SPL.field (← (pure _spl_v18)) "asset_id")))

@[noinline] private def _spl_v19 (_spl_v20 : Thunk (SPL.Eval SPL.Value)) (_spl_v21 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.groupValues (← (SPL.conditional (do
    SPL.binary ">" (← (_spl_v20.get)) (← (pure (.num (mkRat 0 1))))) (fun _ => (_spl_v21.get)) (fun _ => (SPL.listValues [])))) (fun _spl_v22 => (do
    SPL.field (← (pure _spl_v22)) "asset_id")))

@[noinline] private def _spl_v40 (_spl_v41 : Thunk (SPL.Eval SPL.Value)) (_spl_v42 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.getOr (← (do
    SPL.mapLookup (← (_spl_v41.get)) (← (do
      SPL.field (← (_spl_v42.get)) "asset_id")))) (fun _ => (SPL.listValues [])))

@[noinline] private def _spl_v43 (_spl_v44 : Thunk (SPL.Eval SPL.Value)) (_spl_v45 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.getOr (← (do
    SPL.mapLookup (← (_spl_v44.get)) (← (do
      SPL.field (← (_spl_v45.get)) "asset_id")))) (fun _ => (SPL.listValues [])))

@[noinline] private def _spl_v46 (_spl_v47 : Thunk (SPL.Eval SPL.Value)) (_spl_v48 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.filterValues (← (_spl_v47.get)) (fun _spl_v49 => (do
    SPL.inPeriod (← (do
      SPL.field (← (pure _spl_v49)) "cash_received_date")) (← (do
      SPL.field (← (_spl_v48.get)) "period")))))

@[noinline] private def _spl_v50 (_spl_v51 : Thunk (SPL.Eval SPL.Value)) (_spl_v52 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.filterValues (← (_spl_v51.get)) (fun _spl_v53 => (do
    SPL.inPeriod (← (do
      SPL.field (← (pure _spl_v53)) "incurred_date")) (← (do
      SPL.field (← (_spl_v52.get)) "period")))))

@[noinline] private def _spl_v54 (_spl_v55 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v55.get)) (fun _spl_v56 => (do
    SPL.field (← (pure _spl_v56)) "amount")))

@[noinline] private def _spl_v57 (_spl_v58 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v58.get)) (fun _spl_v59 => (do
    SPL.field (← (pure _spl_v59)) "amount")))

@[noinline] private def _spl_v60 (_spl_v61 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.choose [((do
  SPL.field (← (_spl_v61.get)) "contribution_present"), (fun _ => (pure (.num (mkRat 75 1000)))))] (some (fun _ => (pure (.num (mkRat 25 100))))))

@[noinline] private def _spl_v62 (_spl_v63 : Thunk (SPL.Eval SPL.Value)) (_spl_v64 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .multiply (← (_spl_v63.get)) (← (_spl_v64.get)))

@[noinline] private def _spl_v65 (_spl_v66 : Thunk (SPL.Eval SPL.Value)) (_spl_v67 : Thunk (SPL.Eval SPL.Value)) (_spl_v68 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .subtract (← (do
    SPL.Core.numericBinary .subtract (← (_spl_v66.get)) (← (_spl_v67.get)))) (← (_spl_v68.get)))

@[noinline] private def _spl_v69 (_spl_v70 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.field (← (_spl_v70.get)) "contribution_present") (fun _ => (do
  SPL.field (← (_spl_v70.get)) "funding_share")) (fun _ => (pure (.num (mkRat 20 100)))))

@[noinline] private def _spl_v71 (_spl_v72 : Thunk (SPL.Eval SPL.Value)) (_spl_v73 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .multiply (← (_spl_v72.get)) (← (_spl_v73.get)))

@[noinline] private def _spl_v23 (_spl_v24 : Thunk (SPL.Eval SPL.Value)) (_spl_v25 : Thunk (SPL.Eval SPL.Value)) (_spl_v26 : Thunk (SPL.Eval SPL.Value)) (_spl_v27 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.mapValues (← (_spl_v24.get)) (fun _spl_v28 => (do
    let _spl_v29 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v40 (Thunk.mk (fun _ => (_spl_v25.get))) (Thunk.mk (fun _ => (pure _spl_v28))) ())
    let _spl_v30 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v43 (Thunk.mk (fun _ => (_spl_v26.get))) (Thunk.mk (fun _ => (pure _spl_v28))) ())
    let _spl_v31 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v46 (Thunk.mk (fun _ => (_spl_v29.get))) (Thunk.mk (fun _ => (_spl_v27.get))) ())
    let _spl_v32 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v50 (Thunk.mk (fun _ => (_spl_v30.get))) (Thunk.mk (fun _ => (_spl_v27.get))) ())
    let _spl_v33 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v54 (Thunk.mk (fun _ => (_spl_v31.get))) ())
    let _spl_v34 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v57 (Thunk.mk (fun _ => (_spl_v32.get))) ())
    let _spl_v35 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v60 (Thunk.mk (fun _ => (pure _spl_v28))) ())
    let _spl_v36 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v62 (Thunk.mk (fun _ => (_spl_v33.get))) (Thunk.mk (fun _ => (_spl_v35.get))) ())
    let _spl_v37 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v65 (Thunk.mk (fun _ => (_spl_v33.get))) (Thunk.mk (fun _ => (_spl_v36.get))) (Thunk.mk (fun _ => (_spl_v34.get))) ())
    let _spl_v38 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v69 (Thunk.mk (fun _ => (pure _spl_v28))) ())
    let _spl_v39 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v71 (Thunk.mk (fun _ => (_spl_v37.get))) (Thunk.mk (fun _ => (_spl_v38.get))) ())
    SPL.assertValue (← (SPL.conjunction (do
      SPL.binary ">=" (← (do
        SPL.field (← (pure _spl_v28)) "funding_share")) (← (pure (.num (mkRat 0 1))))) (fun _ => (do
      SPL.binary "<=" (← (do
        SPL.field (← (pure _spl_v28)) "funding_share")) (← (pure (.num (mkRat 1 1)))))))) "INVALID_FUNDING_SHARE"
    let _spl_v74 ← (_spl_v29.get)
    let _spl_v75 ← (_spl_v30.get)
    let _spl_v76 ← (_spl_v31.get)
    let _spl_v77 ← (_spl_v32.get)
    let _spl_v78 ← (_spl_v33.get)
    let _spl_v79 ← (_spl_v34.get)
    let _spl_v80 ← (_spl_v35.get)
    let _spl_v81 ← (_spl_v36.get)
    let _spl_v82 ← (_spl_v37.get)
    let _spl_v83 ← (_spl_v38.get)
    let _spl_v84 ← (_spl_v39.get)
    SPL.assertValue (← (do
      SPL.binary ">=" (← (pure _spl_v84)) (← (pure (.num (mkRat 0 1)))))) "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT"
    (SPL.recordValues [("asset_id", (do
      SPL.field (← (pure _spl_v28)) "asset_id")), ("cash", (pure _spl_v78)), ("fee", (pure _spl_v81)), ("allowed_cost", (pure _spl_v79)), ("basis", (pure _spl_v82)), ("share", (pure _spl_v83)), ("earned", (pure _spl_v84))]))))

@[noinline] private def _spl_v85 (_spl_v86 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v86.get)) (fun _spl_v87 => (do
    SPL.field (← (pure _spl_v87)) "earned")))

@[noinline] private def _spl_v88 (_spl_v89 : Thunk (SPL.Eval SPL.Value)) (_spl_v90 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.extrema false (← (_spl_v89.get)) (← (_spl_v90.get)))

@[noinline] private def _spl_v91 (_spl_v92 : Thunk (SPL.Eval SPL.Value)) (_spl_v93 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .subtract (← (_spl_v92.get)) (← (_spl_v93.get)))

def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := (do
  let _spl_v0 ← SPL.lookup _inputs "pictures"
  let _spl_v1 ← SPL.lookup _inputs "receipts"
  let _spl_v2 ← SPL.lookup _inputs "eligible_costs"
  let _spl_v3 ← SPL.lookup _inputs "policy"
  let _spl_v4 ← SPL.lookup _openings "prepayment"
  let _spl_v5 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v12 (Thunk.mk (fun _ => (pure _spl_v0))) ())
  let _spl_v6 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v15 (Thunk.mk (fun _ => (_spl_v5.get))) (Thunk.mk (fun _ => (pure _spl_v1))) ())
  let _spl_v7 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v19 (Thunk.mk (fun _ => (_spl_v5.get))) (Thunk.mk (fun _ => (pure _spl_v2))) ())
  let _spl_v8 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v23 (Thunk.mk (fun _ => (pure _spl_v0))) (Thunk.mk (fun _ => (_spl_v6.get))) (Thunk.mk (fun _ => (_spl_v7.get))) (Thunk.mk (fun _ => (pure _spl_v3))) ())
  let _spl_v9 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v85 (Thunk.mk (fun _ => (_spl_v8.get))) ())
  let _spl_v10 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v88 (Thunk.mk (fun _ => (_spl_v9.get))) (Thunk.mk (fun _ => (pure _spl_v4))) ())
  let _spl_v11 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v91 (Thunk.mk (fun _ => (_spl_v9.get))) (Thunk.mk (fun _ => (_spl_v10.get))) ())
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v4)) (← (pure (.num (mkRat 0 1)))))) "NEGATIVE_OPENING_ADVANCE"
  let _spl_v94 ← (_spl_v5.get)
  let _spl_v95 ← (_spl_v6.get)
  let _spl_v96 ← (_spl_v7.get)
  let _spl_v97 ← (_spl_v8.get)
  let _spl_v98 ← (_spl_v9.get)
  let _spl_v99 ← (_spl_v10.get)
  let _spl_v100 ← (_spl_v11.get)
  SPL.assertValue (← (do
    SPL.binary "==" (← (pure _spl_v98)) (← (do
      SPL.Core.numericBinary .add (← (pure _spl_v99)) (← (pure _spl_v100)))))) "SV_SETTLEMENT_RECONCILIATION"
  let _spl_v101 ← (do
    SPL.Core.numericBinary .subtract (← (pure _spl_v4)) (← (pure _spl_v99)))
  let _spl_v102 ← (pure _spl_v97)
  let _spl_v103 ← (SPL.recordValues [("agreement_id", (do
    SPL.field (← (pure _spl_v3)) "agreement_id")), ("participant_id", (do
    SPL.field (← (pure _spl_v3)) "participant_id")), ("pool_id", (do
    SPL.field (← (pure _spl_v3)) "pool_id")), ("period", (do
    SPL.field (← (pure _spl_v3)) "period")), ("earned", (pure _spl_v98)), ("recouped", (pure _spl_v99)), ("payable", (pure _spl_v100))])
  pure { emissions := [("titles", _spl_v102), ("pool", _spl_v103)], closing := [("prepayment", _spl_v101)] })

end GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116

namespace GeneratedSPL
abbrev scheduleName := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.scheduleName
abbrev sourceRules := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.sourceRules
abbrev settle := GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.settle
end GeneratedSPL

def main (args : List String) : IO UInt32 :=
  SPL.Bindings.runMain [("pictures", (.named "List" [(.named "SVPicture" [])])), ("receipts", (.named "List" [(.named "SVReceipt" [])])), ("eligible_costs", (.named "List" [(.named "SVCost" [])])), ("policy", (.named "SVPolicy" []))] [("prepayment", (.named "Money" [(.named "USD" [])]))] GeneratedSPL.S_83_107_111_117_114_97_115_86_101_110_116_117_114_97_73_110_100_101_120_101_100_69_120_112_101_114_105_109_101_110_116.settle args
