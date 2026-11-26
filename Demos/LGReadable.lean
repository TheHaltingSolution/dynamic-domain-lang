import SPL.Fold
import SPL.Core
import SPL.Bindings

set_option maxRecDepth 4096
set_option maxHeartbeats 0

namespace GeneratedSPL.S_76_105_111_110_115_103_97_116_101_68_101_114_105_118_97_116_105_118_101_80_105_108_111_116

def scheduleName : String := "LionsgateDerivativePilot"
def sourceRules : List (String × String) := [("receipts", ""), ("actual_costs", ""), ("policy", ""), ("outside_hurdle", ""), ("work_gate_history", ""), ("crossed_net_subtotal", ""), ("producer_fee_offset", ""), ("payment_holdback_addition", ""), ("payment_holdback_release", ""), ("gate_gross", ""), ("gate_cost", ""), ("payment_holdback", ""), ("incorporated_policy_0", ""), ("accounting_period", ""), ("require@4:1", ""), ("require@5:1", ""), ("outside_hurdle_attained", "LG-OUTSIDE-HURDLE"), ("require@7:1", ""), ("require@8:1", ""), ("require@9:1", ""), ("require@10:1", ""), ("work_cleared_throughout", "LG-GATE-HISTORY"), ("require@12:1", ""), ("require@13:1", ""), ("require@14:1", ""), ("require@15:1", ""), ("require@16:1", ""), ("current_receipts", ""), ("current_costs", ""), ("cash_measure", "LG-TRUE-CASH"), ("actual_cost_measure", "LG-TRUE-CASH-COST"), ("next_gate_gross", ""), ("next_gate_cost", ""), ("require@24:1", ""), ("breakeven_satisfied", ""), ("payout_base", "LG-GROSS-VIDEO-PROXY"), ("gross_candidate", "LG-GROSS-BRANCH"), ("net_candidate", "LG-NET-BRANCH"), ("contingent_earned", "LG-GREATER-OF"), ("selected_label", ""), ("settlement_participant", ""), ("before_holdback", ""), ("require@37:3", ""), ("require@38:3", ""), ("payable", "SYNTHETIC-PAYMENT-HOLDBACK"), ("gate_gross", ""), ("gate_cost", ""), ("payment_holdback", ""), ("comparison", ""), ("settlement", "")]

@[noinline] private def _spl_v31  (_spl_force : Unit) : SPL.Eval SPL.Value := (pure (.text "lg-cleared@1"))

@[noinline] private def _spl_v32 (_spl_v33 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.field (← (_spl_v33.get)) "period")

@[noinline] private def _spl_v34 (_spl_v35 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.field (← (_spl_v35.get)) "attained")

@[noinline] private def _spl_v36 (_spl_v37 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.field (← (_spl_v37.get)) "cleared_throughout")

@[noinline] private def _spl_v38 (_spl_v39 : Thunk (SPL.Eval SPL.Value)) (_spl_v40 : Thunk (SPL.Eval SPL.Value)) (_spl_v41 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.filterValues (← (_spl_v39.get)) (fun _spl_v42 => (SPL.conjunction (do
    SPL.binary "==" (← (do
      SPL.field (← (pure _spl_v42)) "asset_id")) (← (do
      SPL.field (← (_spl_v40.get)) "asset_id"))) (fun _ => (do
    SPL.inPeriod (← (do
      SPL.field (← (pure _spl_v42)) "cash_received_date")) (← (_spl_v41.get)))))))

@[noinline] private def _spl_v43 (_spl_v44 : Thunk (SPL.Eval SPL.Value)) (_spl_v45 : Thunk (SPL.Eval SPL.Value)) (_spl_v46 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.filterValues (← (_spl_v44.get)) (fun _spl_v47 => (SPL.conjunction (do
    SPL.binary "==" (← (do
      SPL.field (← (pure _spl_v47)) "asset_id")) (← (do
      SPL.field (← (_spl_v45.get)) "asset_id"))) (fun _ => (do
    SPL.inPeriod (← (do
      SPL.field (← (pure _spl_v47)) "incurred_date")) (← (_spl_v46.get)))))))

@[noinline] private def _spl_v48 (_spl_v49 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v49.get)) (fun _spl_v50 => (do
    SPL.field (← (pure _spl_v50)) "amount")))

@[noinline] private def _spl_v51 (_spl_v52 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v52.get)) (fun _spl_v53 => (do
    SPL.field (← (pure _spl_v53)) "amount")))

@[noinline] private def _spl_v54 (_spl_v55 : Thunk (SPL.Eval SPL.Value)) (_spl_v56 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .add (← (_spl_v55.get)) (← (_spl_v56.get)))

@[noinline] private def _spl_v57 (_spl_v58 : Thunk (SPL.Eval SPL.Value)) (_spl_v59 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .add (← (_spl_v58.get)) (← (_spl_v59.get)))

@[noinline] private def _spl_v60 (_spl_v61 : Thunk (SPL.Eval SPL.Value)) (_spl_v62 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.binary ">=" (← (_spl_v61.get)) (← (_spl_v62.get)))

@[noinline] private def _spl_v63 (_spl_v64 : Thunk (SPL.Eval SPL.Value)) (_spl_v65 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.sumValues (← (_spl_v64.get)) (fun _spl_v66 => (do
    SPL.Core.numericBinary .multiply (← (do
      SPL.field (← (pure _spl_v66)) "amount")) (← (SPL.conditional (do
      SPL.field (← (pure _spl_v66)) "is_home_video") (fun _ => (do
      SPL.field (← (_spl_v65.get)) "video_proxy")) (fun _ => (pure (.num (mkRat 1 1)))))))))

@[noinline] private def _spl_v67 (_spl_v68 : Thunk (SPL.Eval SPL.Value)) (_spl_v69 : Thunk (SPL.Eval SPL.Value)) (_spl_v70 : Thunk (SPL.Eval SPL.Value)) (_spl_v71 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (_spl_v68.get) (fun _ => (do
  SPL.extrema true (← (pure (.num (mkRat 0 1)))) (← (do
    SPL.Core.numericBinary .subtract (← (do
      SPL.Core.numericBinary .multiply (← (do
        SPL.field (← (_spl_v69.get)) "gross_rate")) (← (_spl_v70.get)))) (← (_spl_v71.get)))))) (fun _ => (pure (.num (mkRat 0 1)))))

@[noinline] private def _spl_v72 (_spl_v73 : Thunk (SPL.Eval SPL.Value)) (_spl_v74 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .multiply (← (do
    SPL.field (← (_spl_v73.get)) "net_rate")) (← (_spl_v74.get)))

@[noinline] private def _spl_v75 (_spl_v76 : Thunk (SPL.Eval SPL.Value)) (_spl_v77 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.extrema true (← (_spl_v76.get)) (← (_spl_v77.get)))

@[noinline] private def _spl_v78 (_spl_v79 : Thunk (SPL.Eval SPL.Value)) (_spl_v80 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (SPL.conditional (do
  SPL.binary "==" (← (_spl_v79.get)) (← (_spl_v80.get))) (fun _ => (pure (.text "tie"))) (fun _ => (SPL.conditional (do
  SPL.binary ">" (← (_spl_v79.get)) (← (_spl_v80.get))) (fun _ => (pure (.text "gross"))) (fun _ => (pure (.text "net"))))))

@[noinline] private def _spl_v81 (_spl_v82 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.field (← (_spl_v82.get)) "participant_id")

@[noinline] private def _spl_v83 (_spl_v84 : Thunk (SPL.Eval SPL.Value)) (_spl_v85 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .add (← (_spl_v84.get)) (← (_spl_v85.get)))

@[noinline] private def _spl_v86 (_spl_v87 : Thunk (SPL.Eval SPL.Value)) (_spl_v88 : Thunk (SPL.Eval SPL.Value)) (_spl_force : Unit) : SPL.Eval SPL.Value := (do
  SPL.Core.numericBinary .subtract (← (_spl_v87.get)) (← (_spl_v88.get)))

def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := (do
  let _spl_v0 ← SPL.lookup _inputs "receipts"
  let _spl_v1 ← SPL.lookup _inputs "actual_costs"
  let _spl_v2 ← SPL.lookup _inputs "policy"
  let _spl_v3 ← SPL.lookup _inputs "outside_hurdle"
  let _spl_v4 ← SPL.lookup _inputs "work_gate_history"
  let _spl_v5 ← SPL.lookup _inputs "crossed_net_subtotal"
  let _spl_v6 ← SPL.lookup _inputs "producer_fee_offset"
  let _spl_v7 ← SPL.lookup _inputs "payment_holdback_addition"
  let _spl_v8 ← SPL.lookup _inputs "payment_holdback_release"
  let _spl_v9 ← SPL.lookup _openings "gate_gross"
  let _spl_v10 ← SPL.lookup _openings "gate_cost"
  let _spl_v11 ← SPL.lookup _openings "payment_holdback"
  let _spl_v12 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v31  ())
  let _spl_v13 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v32 (Thunk.mk (fun _ => (pure _spl_v2))) ())
  let _spl_v14 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v34 (Thunk.mk (fun _ => (pure _spl_v3))) ())
  let _spl_v15 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v36 (Thunk.mk (fun _ => (pure _spl_v4))) ())
  let _spl_v16 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v38 (Thunk.mk (fun _ => (pure _spl_v0))) (Thunk.mk (fun _ => (pure _spl_v2))) (Thunk.mk (fun _ => (_spl_v13.get))) ())
  let _spl_v17 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v43 (Thunk.mk (fun _ => (pure _spl_v1))) (Thunk.mk (fun _ => (pure _spl_v2))) (Thunk.mk (fun _ => (_spl_v13.get))) ())
  let _spl_v18 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v48 (Thunk.mk (fun _ => (_spl_v16.get))) ())
  let _spl_v19 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v51 (Thunk.mk (fun _ => (_spl_v17.get))) ())
  let _spl_v20 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v54 (Thunk.mk (fun _ => (pure _spl_v9))) (Thunk.mk (fun _ => (_spl_v18.get))) ())
  let _spl_v21 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v57 (Thunk.mk (fun _ => (pure _spl_v10))) (Thunk.mk (fun _ => (_spl_v19.get))) ())
  let _spl_v22 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v60 (Thunk.mk (fun _ => (_spl_v20.get))) (Thunk.mk (fun _ => (_spl_v21.get))) ())
  let _spl_v23 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v63 (Thunk.mk (fun _ => (_spl_v16.get))) (Thunk.mk (fun _ => (pure _spl_v2))) ())
  let _spl_v24 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v67 (Thunk.mk (fun _ => (_spl_v22.get))) (Thunk.mk (fun _ => (pure _spl_v2))) (Thunk.mk (fun _ => (_spl_v23.get))) (Thunk.mk (fun _ => (pure _spl_v6))) ())
  let _spl_v25 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v72 (Thunk.mk (fun _ => (pure _spl_v2))) (Thunk.mk (fun _ => (pure _spl_v5))) ())
  let _spl_v26 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v75 (Thunk.mk (fun _ => (_spl_v24.get))) (Thunk.mk (fun _ => (_spl_v25.get))) ())
  let _spl_v27 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v78 (Thunk.mk (fun _ => (_spl_v24.get))) (Thunk.mk (fun _ => (_spl_v25.get))) ())
  let _spl_v28 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v81 (Thunk.mk (fun _ => (pure _spl_v2))) ())
  let _spl_v29 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v83 (Thunk.mk (fun _ => (_spl_v26.get))) (Thunk.mk (fun _ => (pure _spl_v8))) ())
  let _spl_v30 : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => _spl_v86 (Thunk.mk (fun _ => (_spl_v29.get))) (Thunk.mk (fun _ => (pure _spl_v7))) ())
  let _spl_v89 ← (_spl_v12.get)
  let _spl_v90 ← (_spl_v13.get)
  SPL.assertValue (← (do
    SPL.isCalendarQuarter (← (pure _spl_v90)))) "READABLE_CALENDAR_QUARTER_REQUIRED"
  SPL.assertValue (← (do
    SPL.binary "==" (← (do
      SPL.field (← (pure _spl_v3)) "agreement_id")) (← (do
      SPL.field (← (pure _spl_v2)) "agreement_id")))) "LG_HURDLE_WRONG_SCOPE"
  let _spl_v91 ← (_spl_v14.get)
  SPL.assertValue (← (pure _spl_v91)) "LG_OUTSIDE_HURDLE_NOT_ATTAINED"
  SPL.assertValue (← (do
    SPL.binary "<" (← (do
      SPL.field (← (pure _spl_v3)) "effective_date")) (← (do
      SPL.field (← (do
        SPL.field (← (pure _spl_v2)) "period")) "start")))) "LG_HURDLE_TIMING_POLICY_REQUIRED"
  SPL.assertValue (← (do
    SPL.binary "==" (← (do
      SPL.field (← (pure _spl_v4)) "asset_id")) (← (do
      SPL.field (← (pure _spl_v2)) "asset_id")))) "LG_GATE_HISTORY_WRONG_WORK"
  SPL.assertValue (← (SPL.conjunction (do
    SPL.binary "==" (← (do
      SPL.field (← (do
        SPL.field (← (pure _spl_v4)) "period")) "start")) (← (do
      SPL.field (← (do
        SPL.field (← (pure _spl_v2)) "period")) "start"))) (fun _ => (do
    SPL.binary "==" (← (do
      SPL.field (← (do
        SPL.field (← (pure _spl_v4)) "period")) "end")) (← (do
      SPL.field (← (do
        SPL.field (← (pure _spl_v2)) "period")) "end")))))) "LG_GATE_HISTORY_WRONG_PERIOD"
  let _spl_v92 ← (_spl_v15.get)
  SPL.assertValue (← (pure _spl_v92)) "LG_GATE_HISTORY_POLICY_REQUIRED"
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v9)) (← (pure _spl_v10)))) "LG_CROSSING_POLICY_REQUIRED"
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v6)) (← (pure (.num (mkRat 0 1)))))) "LG_NEGATIVE_FEE_OFFSET"
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v5)) (← (pure (.num (mkRat 0 1)))))) "LG_NET_LOSS_POLICY_REQUIRED"
  SPL.assertValue (← (SPL.conjunction (SPL.conjunction (do
    SPL.binary ">=" (← (pure _spl_v11)) (← (pure (.num (mkRat 0 1))))) (fun _ => (do
    SPL.binary ">=" (← (pure _spl_v7)) (← (pure (.num (mkRat 0 1))))))) (fun _ => (do
    SPL.binary ">=" (← (pure _spl_v8)) (← (pure (.num (mkRat 0 1)))))))) "SYNTHETIC_INVALID_HOLDBACK_MOVEMENT"
  let _spl_v93 ← (_spl_v16.get)
  let _spl_v94 ← (_spl_v17.get)
  let _spl_v95 ← (_spl_v18.get)
  let _spl_v96 ← (_spl_v19.get)
  let _spl_v97 ← (_spl_v20.get)
  let _spl_v98 ← (_spl_v21.get)
  SPL.assertValue (← (do
    SPL.binary ">=" (← (pure _spl_v97)) (← (pure _spl_v98)))) "LG_RECROSSING_POLICY_REQUIRED"
  let _spl_v99 ← (_spl_v22.get)
  let _spl_v100 ← (_spl_v23.get)
  let _spl_v101 ← (_spl_v24.get)
  let _spl_v102 ← (_spl_v25.get)
  let _spl_v103 ← (_spl_v26.get)
  let _spl_v104 ← (_spl_v27.get)
  let _spl_v105 ← (_spl_v28.get)
  let _spl_v106 ← (_spl_v29.get)
  SPL.assertValue (← (do
    SPL.binary "<=" (← (pure _spl_v8)) (← (pure _spl_v11)))) "SYNTHETIC_HOLDBACK_RELEASE_EXCEEDS_OPENING"
  SPL.assertValue (← (do
    SPL.binary "<=" (← (pure _spl_v7)) (← (pure _spl_v106)))) "SYNTHETIC_HOLDBACK_ADDITION_EXCEEDS_AVAILABLE"
  let _spl_v107 ← (_spl_v30.get)
  let _spl_v108 ← (pure _spl_v97)
  let _spl_v109 ← (pure _spl_v98)
  let _spl_v110 ← (do
    SPL.Core.numericBinary .subtract (← (do
      SPL.Core.numericBinary .add (← (pure _spl_v11)) (← (pure _spl_v7)))) (← (pure _spl_v8)))
  let _spl_v111 ← (SPL.recordValues [("cash_measure", (pure _spl_v95)), ("payout_base", (pure _spl_v100)), ("gross_candidate", (pure _spl_v101)), ("net_candidate", (pure _spl_v102)), ("selected_label", (pure _spl_v104)), ("earned", (pure _spl_v103)), ("outside_hurdle", (pure _spl_v3)), ("work_gate_history", (pure _spl_v4))])
  let _spl_v112 ← (SPL.recordValues [("agreement_id", (do
    SPL.field (← (pure _spl_v2)) "agreement_id")), ("participant_id", (pure _spl_v105)), ("asset_id", (do
    SPL.field (← (pure _spl_v2)) "asset_id")), ("net_pool_id", (do
    SPL.field (← (pure _spl_v2)) "pool_id")), ("period", (pure _spl_v90)), ("earned", (pure _spl_v103)), ("payment_holdback_addition", (pure _spl_v7)), ("payment_holdback_release", (pure _spl_v8)), ("payable", (pure _spl_v107))])
  pure { emissions := [("comparison", _spl_v111), ("settlement", _spl_v112)], closing := [("gate_gross", _spl_v108), ("gate_cost", _spl_v109), ("payment_holdback", _spl_v110)] })

end GeneratedSPL.S_76_105_111_110_115_103_97_116_101_68_101_114_105_118_97_116_105_118_101_80_105_108_111_116

namespace GeneratedSPL
abbrev scheduleName := GeneratedSPL.S_76_105_111_110_115_103_97_116_101_68_101_114_105_118_97_116_105_118_101_80_105_108_111_116.scheduleName
abbrev sourceRules := GeneratedSPL.S_76_105_111_110_115_103_97_116_101_68_101_114_105_118_97_116_105_118_101_80_105_108_111_116.sourceRules
abbrev settle := GeneratedSPL.S_76_105_111_110_115_103_97_116_101_68_101_114_105_118_97_116_105_118_101_80_105_108_111_116.settle
end GeneratedSPL

def main (args : List String) : IO UInt32 :=
  SPL.Bindings.runMain [("receipts", (.named "List" [(.named "LGReceipt" [])])), ("actual_costs", (.named "List" [(.named "LGCost" [])])), ("policy", (.named "LGPolicy" [])), ("outside_hurdle", (.named "LGHurdleAttestation" [])), ("work_gate_history", (.named "LGGateHistoryAttestation" [])), ("crossed_net_subtotal", (.named "Money" [(.named "USD" [])])), ("producer_fee_offset", (.named "Money" [(.named "USD" [])])), ("payment_holdback_addition", (.named "Money" [(.named "USD" [])])), ("payment_holdback_release", (.named "Money" [(.named "USD" [])]))] [("gate_gross", (.named "Money" [(.named "USD" [])])), ("gate_cost", (.named "Money" [(.named "USD" [])])), ("payment_holdback", (.named "Money" [(.named "USD" [])]))] GeneratedSPL.S_76_105_111_110_115_103_97_116_101_68_101_114_105_118_97_116_105_118_101_80_105_108_111_116.settle args
