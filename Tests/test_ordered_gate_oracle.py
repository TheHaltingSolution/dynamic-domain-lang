"""Independent hand controls over original gate facts; no executable SPL read."""
import ast
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest

from oracles.ordered_gates import OrderedGateOracleError, exact_json, ordered_gates, policy, FRAME

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/ordered-gates/neutral.json").read_text(encoding="utf-8"))


def sync(data):
    """Reconcile ORIGINAL membership, ordering authority and raw population only."""
    rows=data["rows"]
    data["ordering_authority"]["keys"]=[{"event_id":r["id"],"occurred_at":max(r["received_at"],r["earned_at"]) if r["kind"]=="receipt" else r["incurred_at"],"sequence":r["sequence"]} for r in rows]
    for pop in data["populations"]:
        selected=[r for r in rows if r["kind"]==pop["kind"]]
        pop["event_ids"]=[r["id"] for r in selected]
        pop["raw_total"]=str(sum((F(r["amount"] if r["kind"]=="receipt" else r["gross_amount"]) for r in selected),F()))
    required={data["ordering_authority"]["evidence_ref"],data["aggregate_hurdle"]["evidence_ref"],data["net_worksheet"]["evidence_ref"]}
    required.update(p["evidence_ref"] for p in data["populations"])
    for row in rows:
        required.update((row["evidence_ref"],row["decision"]["evidence_ref"]))
        required.update(item["evidence_ref"] for item in row.get("reductions",[]))
    required.update(("evidence:terms","evidence:work"))
    data["evidence"]=[e for e in data["evidence"] if e["id"] in required]
    return data


def frame_data(data, frame):
    for key in FRAME:data[key]=deepcopy(frame[key])
    return data


def genesis(data):
    result=frame_data(deepcopy(data),data["opening_state"]["frames"][0])
    result["opening_state"]={"origin":"genesis","boundary":result["period"]["start"]}
    return result


def carry(data, previous, frame=None):
    result=deepcopy(data)
    if frame is not None:frame_data(result,frame)
    serialized=json.loads(json.dumps(exact_json(previous)))
    result["opening_state"]=serialized["closing_state"]
    result["prior_result"]={"source_case_id":serialized["source_case_id"],"period":serialized["period"],"closing_state":deepcopy(serialized["closing_state"]),"result_ref":"supplied-calculation#"+serialized["source_case_id"]}
    return result


def q3(data):
    result={k:deepcopy(data[k]) for k in FRAME}
    def rewrite(value):
        if isinstance(value,dict):return {k:rewrite(v) for k,v in value.items()}
        if isinstance(value,list):return [rewrite(v) for v in value]
        if isinstance(value,str):return value.replace("q2","q3").replace("apr20-cost","jul10-cost").replace("jun10-receipt","jul20-receipt").replace("2008-04-20","2008-07-10").replace("2008-04-21","2008-07-11").replace("2008-06-10","2008-07-20").replace("2008-06-11","2008-07-21")
        return value
    result=rewrite(result);result.update(case_id="gate-q3",period={"start":"2008-07-01","end":"2008-10-01"},cutoff="2008-10-05T00:00:00Z")
    result["rows"]=[r for r in result["rows"] if r["id"] in {"jul10-cost","jul20-receipt"}]
    for item in [*result["populations"],result["ordering_authority"],result["net_worksheet"]]:
        item["period"]=deepcopy(result["period"]);item["observed_at"]="2008-10-01T00:00:00Z"
        next(e for e in result["evidence"] if e["id"]==item["evidence_ref"])["observed_at"]=item["observed_at"]
    return sync(result)


class OrderedGateOracleTests(unittest.TestCase):
    def reject(self,data,code):
        original=deepcopy(data)
        with self.assertRaisesRegex(OrderedGateOracleError,"^"+code+"$"):ordered_gates(data)
        self.assertEqual(data,original)

    def test_original_selected_path_6_closing150_130(self):
        result=ordered_gates(fixture())
        self.assertEqual((result["opening_receipts"],result["opening_costs"],result["closing_receipts"],result["closing_costs"]),(80,100,150,130))
        self.assertEqual((result["current_full_receipts"],result["current_eligible_costs"],result["payout_base"],result["gross_candidate"]),(70,30,30,6))
        self.assertEqual([r["admitted_full_receipt"] for r in result["path"]],[0,20,0,0,20])
        self.assertEqual([r["payout_base_contribution"] for r in result["path"]],[0,10,0,0,20])
        self.assertEqual([r["post_surplus"] for r in result["path"]],[-10,20,-10,0,20])
        self.assertFalse(result["continuous_current_history"])
        self.assertEqual(result["path"][3]["reason"],"eligible_zero_at_equality")
        self.assertEqual(result["net_status"],"computed_zero")
        self.assertEqual(result["payment_evidence_status"],"not_part_of_profile")
        self.assertNotIn("actual_paid",result)
        self.assertFalse(result["bank_movement_created"])

    def test_named_methods_6_8_7_0_11(self):
        expected={"split_reopen":6,"split_latch":8,"full_cross_reopen":7,"opening_gate":0,"closing_gate":11,"next_row_reopen":4,"continuous_history":0}
        for method,amount in expected.items():
            with self.subTest(method=method):
                data=fixture();data["policy"]=policy(method);result=ordered_gates(data)
                self.assertEqual(result["gross_candidate"],amount)
                self.assertEqual((result["closing_receipts"],result["closing_costs"]),(150,130))

    def test_separately_authorized_same_time_reversal4(self):
        data=fixture();data["rows"][1]["sequence"]=2;data["rows"][2]["sequence"]=1
        result=ordered_gates(sync(data));self.assertEqual(result["gross_candidate"],4)
        self.assertEqual([r["original"]["id"] for r in result["path"]][1:3],["apr20-cost","apr20-video"])
        data=fixture();data["rows"][1]["sequence"]=2
        self.reject(data,"GATE_ORDER_AUTHORITY_MISMATCH")

    def test_crossing_without_dip_split6_full7_next4_close9(self):
        for method,expected in [("split_reopen",6),("full_cross_reopen",7),("next_row_reopen",4),("closing_gate",11)]:
            data=fixture();data["rows"]=[r for r in data["rows"] if r["kind"]!="cost"]
            # Original R10/HV30/R10/R20 remains55 proxy; endpoint11, selected8.
            data["rows"]=[r for r in data["rows"] if r["id"]!="may10-receipt"]
            data["policy"]=policy(method)
            self.assertEqual(ordered_gates(sync(data))["gross_candidate"],9 if method=="closing_gate" else expected)

    def test_continuous_dip_and_recovery_not_endpoints(self):
        for dip in (False,True):
            data=fixture();prior=data["opening_state"]["frames"][0];prior["rows"][1]["amount"]="110";sync(prior)
            data["rows"]=[r for r in data["rows"] if r["id"] in ({"apr20-cost","jun10-receipt"} if dip else {"jun10-receipt"})]
            next(r for r in data["rows"] if r["kind"]=="receipt")["amount"]="40";sync(data)
            data["policy"]=policy("continuous_history");result=ordered_gates(data)
            self.assertEqual(result["gross_candidate"],0 if dip else 8)
            self.assertEqual(result["continuous_current_history"],not dip)
            self.assertEqual(result["gross_status"],"inapplicable" if dip else "computed_positive")
            if dip:
                data["policy"]=policy("closing_gate")
                self.assertEqual(ordered_gates(data)["gross_candidate"],8)

    def test_continuous_equality_is_clear_eligible_zero_distinct(self):
        data=fixture();prior=data["opening_state"]["frames"][0];prior["rows"][1]["amount"]="100";sync(prior)
        data["rows"]=[];sync(data);data["policy"]=policy("continuous_history")
        result=ordered_gates(data)
        self.assertEqual((result["gross_candidate"],result["gross_status"],result["selected_branch"]),(0,"computed_zero","tie"))
        self.assertTrue(result["continuous_current_history"])
        data=fixture();data["rows"]=[];sync(data)
        result=ordered_gates(data)
        self.assertEqual((result["gross_status"],result["net_status"],result["selected_branch"]),("inapplicable","computed_zero","net"))

    def test_latch_false_genesis_and_positive_equality_boundary(self):
        data=genesis(fixture());data["rows"]=[];sync(data);data["policy"]=policy("split_latch")
        self.assertFalse(ordered_gates(data)["closing_latch"])
        data=genesis(fixture());data["rows"][1]["amount"]="100";sync(data);data["policy"]=policy("split_latch")
        result=ordered_gates(data);self.assertTrue(result["closing_latch"])
        self.assertEqual(result["gross_candidate"],0)
        self.assertEqual(result["gross_status"],"computed_zero")

    def test_zero_receipt_does_not_latch_and_fraction_exact(self):
        data=genesis(fixture());data["rows"]=data["rows"][1:];data["rows"][0]["amount"]="0";sync(data)
        self.assertFalse(ordered_gates(data)["closing_latch"])
        data=fixture();data["rows"]=[data["rows"][0]];data["rows"][0]["amount"]="61/3";sync(data)
        result=ordered_gates(data)
        self.assertEqual((result["payout_base"],result["gross_candidate"]),(F(1,3),F(1,15)))

    def test_video_proxy_does_not_change_full_gate(self):
        data=fixture();data["registry"]["terms"]["video_proxy"]="1/4"
        result=ordered_gates(data);self.assertEqual(result["gross_candidate"],5)
        self.assertEqual((result["closing_receipts"],result["closing_costs"]),(150,130))

    def test_actual_q1_q2_q3_serialized_replay(self):
        data=fixture();first=ordered_gates(genesis(data))
        self.assertEqual((first["closing_receipts"],first["closing_costs"],first["gross_candidate"]),(80,100,0))
        second=ordered_gates(carry(data,first));self.assertEqual(second["gross_candidate"],6)
        self.assertEqual(second,ordered_gates(data))
        third=ordered_gates(carry(data,second,q3(data)))
        self.assertEqual((third["opening_receipts"],third["opening_costs"],third["closing_receipts"],third["closing_costs"]),(150,130,170,160))
        self.assertEqual((third["gross_candidate"],third["payout_base"]),(2,10))
        self.assertEqual(third["closing_state"]["recognized_entitlement"],"8")
        self.assertEqual(len(third["closing_state"]["history"]),3)

    def test_physical_permutation_does_not_change_authorized_path(self):
        data=fixture();data["rows"].reverse();data["evidence"].reverse();data["ordering_authority"]["keys"].reverse()
        expected=ordered_gates(fixture());actual=ordered_gates(data)
        self.assertEqual(actual["path"],expected["path"])
        self.assertEqual(actual["gross_candidate"],6)

    def test_exact_submicrosecond_and_offset_instant_order(self):
        data=fixture();receipt,cost=data["rows"][1:3]
        receipt["received_at"]=receipt["earned_at"]="2008-04-20T12:00:00.0000000001Z"
        cost["incurred_at"]="2008-04-20T05:00:00.0000000002-07:00"
        cost["sequence"]=1;result=ordered_gates(sync(data))
        self.assertEqual(result["gross_candidate"],6)
        self.assertEqual(result["path"][2]["occurred_at_exact"]-result["path"][1]["occurred_at_exact"],F(1,10**10))

    def test_received_and_earned_recognition_both_preserved(self):
        data=fixture();row=data["rows"][0];row["received_at"]="2008-03-01T12:00:00Z"
        result=ordered_gates(sync(data));self.assertEqual(result["gross_candidate"],6)
        self.assertEqual(result["path"][0]["original"]["received_at"],"2008-03-01T12:00:00Z")

    def test_cost_reduction_original_line_and_exclusion(self):
        data=fixture();cost=data["rows"][2]
        reduction={k:deepcopy(cost[k]) for k in ("id","scope","original_ref","source_ref","evidence_ref","observed_at")}
        reduction.update(id="cost-rebate",original_ref="original-source#cost-rebate",evidence_ref="evidence:rebate",category="rebate",amount="10")
        cost["reductions"]=[reduction]
        data["evidence"].append({"id":"evidence:rebate","scope":deepcopy(data["scope"]),"kind":"cost_reduction","source_ref":"evidence-source#rebate","observed_at":cost["observed_at"],"approved":True})
        result=ordered_gates(data);self.assertEqual((result["current_eligible_costs"],result["gross_candidate"]),(20,8))
        cost["reductions"][0]["amount"]="31";self.reject(data,"GATE_COST_REDUCTION_OVERAPPLY")
        data=fixture();data["rows"][2]["decision"]["eligible"]=False
        result=ordered_gates(data);self.assertEqual((result["current_eligible_costs"],result["gross_candidate"]),(0,8))

    def test_missing_history_and_complete_population_unknown_block(self):
        data=fixture();data["opening_state"]["frames"]=[];self.reject(data,"GATE_COMPLETE_PREHISTORY_REQUIRED")
        data=fixture();data["populations"]=data["populations"][:1];self.reject(data,"GATE_COMPLETE_POPULATIONS_REQUIRED")
        data=fixture();data["populations"][0]["complete"]=False;self.reject(data,"GATE_POPULATION_COMPLETENESS")
        data=fixture();data["populations"][0]["event_ids"].pop();self.reject(data,"GATE_POPULATION_IDENTITIES")
        data=fixture();data["populations"][0]["raw_total"]="71";self.reject(data,"GATE_POPULATION_TOTAL")

    def test_unknown_net_is_not_zero_and_aggregate_not_derived(self):
        data=fixture();del data["net_worksheet"];self.reject(data,"GATE_RECORD_FIELDS")
        data=fixture();data["net_worksheet"]["amount"]="1";self.reject(data,"GATE_ONLY_SUPPLIED_ZERO_NET_PROFILE")
        data=fixture();data["aggregate_hurdle"]["attained"]=False;self.reject(data,"GATE_OUTSIDE_HURDLE_STRICT_BEFORE")
        data=fixture();data["aggregate_hurdle"]["effective_date"]="2008-04-01";self.reject(data,"GATE_OUTSIDE_HURDLE_STRICT_BEFORE")

    def test_cutoff_equal_late_evidence_and_unknown_support(self):
        data=fixture();data["rows"][0]["observed_at"]=data["cutoff"];self.reject(data,"GATE_OBSERVATION_CUTOFF")
        data=fixture();data["evidence"][0]["observed_at"]=data["cutoff"];self.reject(data,"GATE_EVIDENCE_CUTOFF")
        data=fixture();data["rows"][0]["evidence_ref"]="unknown";self.reject(data,"GATE_MISSING_EVIDENCE")
        data=fixture();data["rows"][0]["observed_at"]="2008-04-09T00:00:00Z";self.reject(data,"GATE_EVIDENCE_NOT_KNOWN")

    def test_work_aggregate_net_event_scope_and_effective_terms(self):
        for target in ("aggregate_hurdle","net_worksheet"):
            data=fixture();data[target]["scope"]["agreement_id"]="wrong";self.reject(data,"GATE_SCOPE")
        data=fixture();data["rows"][0]["scope"]["asset_id"]="wrong";self.reject(data,"GATE_SCOPE")
        data=fixture();data["registry"]["terms"]["effective_start"]="2008-04-01";self.reject(data,"GATE_TERMS_EFFECTIVE")
        data=fixture();data["registry"]["work"]["eligible"]=False;self.reject(data,"GATE_WORK_INELIGIBLE")
        data=fixture();data["net_worksheet"]["member_asset_ids"]=["wrong"];self.reject(data,"GATE_NET_PERIOD_MEMBERS")

    def test_duplicate_alias_history_replay_and_same_time_tie(self):
        data=fixture();data["rows"].append(deepcopy(data["rows"][0]));self.reject(data,"GATE_DUPLICATE_ID")
        data=fixture();data["rows"][1]["original_ref"]=data["rows"][0]["original_ref"];data["rows"][1]["decision"]["event_ref"]=data["rows"][1]["original_ref"]
        self.reject(data,"GATE_EVENT_REPLAY_OR_ALIAS")
        data=fixture();data["rows"][0]["original_ref"]="original-source#original-receipt80";data["rows"][0]["decision"]["event_ref"]=data["rows"][0]["original_ref"]
        self.reject(data,"GATE_EVENT_REPLAY_OR_ALIAS")
        data=fixture();data["rows"][2]["sequence"]=1;sync(data);self.reject(data,"GATE_UNRESOLVED_EVENT_TIE")

    def test_wrong_classification_and_unsupported_financial_raws(self):
        data=fixture();data["rows"][1]["decision"]["channel"]="ordinary";self.reject(data,"GATE_CHANNEL_AUTHORITY")
        data=fixture();data["rows"][0]["nonrefundable"]=False;self.reject(data,"GATE_REFUNDABLE_RECEIPT_UNSUPPORTED")
        data=fixture();data["rows"][2]["actual_third_party"]=False;self.reject(data,"GATE_COST_NOT_ACTUAL_THIRD_PARTY")
        data=fixture();data["rows"][0]["amount"]="-1";self.reject(data,"GATE_EXACT_NONNEGATIVE")

    def test_predecessor_state_policy_and_history_tampering(self):
        data=fixture();first=ordered_gates(genesis(data));linked=carry(data,first)
        bad=deepcopy(linked);bad["opening_state"]["receipts"]="81";self.reject(bad,"GATE_OPENING_RECONCILIATION")
        bad=deepcopy(linked);bad["prior_result"]["source_case_id"]="wrong";self.reject(bad,"GATE_PREDECESSOR_MISMATCH")
        bad=deepcopy(linked);bad["policy"]=policy("closing_gate");self.reject(bad,"GATE_PINNED_CONTEXT_CHANGED")
        bad=deepcopy(linked);bad["opening_state"]["history"][0]["result"]["gross_candidate"]="1";self.reject(bad,"GATE_HISTORY_FINANCIAL_REPLAY")
        bad=deepcopy(linked);del bad["prior_result"];self.reject(bad,"GATE_PREDECESSOR_REQUIRED")
        bad=deepcopy(linked);bad["registry"]["terms"]["gross_rate"]="0.3";self.reject(bad,"GATE_PINNED_CONTEXT_CHANGED")

    def test_original_text_lexemes_no_normalization_and_no_compiler_import(self):
        data=fixture();row=data["rows"][0];row["original_ref"]="original-e\u0301#é A";row["decision"]["event_ref"]=row["original_ref"]
        result=ordered_gates(data);self.assertEqual(result["path"][0]["original"]["original_ref"],"original-e\u0301#é A")
        tree=ast.parse((ROOT/"oracles/ordered_gates.py").read_text(encoding="utf-8"))
        imports={node.module.split('.')[0] if isinstance(node,ast.ImportFrom) else alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom)) for alias in (node.names if isinstance(node,ast.Import) else [None])}
        self.assertEqual(imports,{"copy","datetime","fractions","re"})
        data=fixture();data["rows"][0]["solved_payout"]="6";self.reject(data,"GATE_RECORD_FIELDS")

    def test_malformed_missing_id_nonrecord_and_unused_evidence_atomic(self):
        data=fixture();del data["rows"][0]["id"];self.reject(data,"GATE_MALFORMED_INPUT")
        data=fixture();data["rows"][0]=None;self.reject(data,"GATE_MALFORMED_INPUT")
        data=fixture();ev=deepcopy(data["evidence"][0]);ev["id"]="unused";data["evidence"].append(ev);self.reject(data,"GATE_UNUSED_EVIDENCE")

    def test_period_start_included_end_excluded_and_observation_order(self):
        data=fixture();row=data["rows"][0];row["received_at"]=row["earned_at"]="2008-04-01T00:00:00Z"
        self.assertEqual(ordered_gates(sync(data))["gross_candidate"],6)
        row["received_at"]=row["earned_at"]="2008-07-01T00:00:00Z";sync(data)
        self.reject(data,"GATE_EVENT_CHRONOLOGY")
        data=fixture();row=data["rows"][0];row["received_at"]=row["earned_at"]="2008-04-12T00:00:00Z";sync(data)
        self.reject(data,"GATE_EVENT_CHRONOLOGY")

    def test_classification_alias_and_evidence_kind_mismatch(self):
        data=fixture();data["rows"][1]["decision"]["id"]=data["rows"][0]["decision"]["id"]
        self.reject(data,"GATE_CLASSIFICATION_REPLAY_OR_ALIAS")
        data=fixture();data["rows"][1]["decision"]["original_ref"]=data["rows"][0]["decision"]["original_ref"]
        self.reject(data,"GATE_CLASSIFICATION_REPLAY_OR_ALIAS")
        data=fixture();data["evidence"][0]["kind"]="population";self.reject(data,"GATE_EVIDENCE_SCOPE_KIND")

    def test_cost_reduction_cannot_also_be_receipt(self):
        data=fixture();cost=data["rows"][2]
        reduction={k:deepcopy(cost[k]) for k in ("id","scope","original_ref","source_ref","evidence_ref","observed_at")}
        reduction.update(id="benefit",original_ref=data["rows"][0]["original_ref"],evidence_ref="benefit-evidence",category="soft_money",amount="1")
        cost["reductions"]=[reduction]
        data["evidence"].append({"id":"benefit-evidence","scope":deepcopy(data["scope"]),"kind":"cost_reduction","source_ref":"source#benefit","observed_at":cost["observed_at"],"approved":True})
        self.reject(data,"GATE_EVENT_REPLAY_OR_ALIAS")

    def test_population_cannot_omit_later_known_original(self):
        data=fixture();data["rows"][0]["observed_at"]="2008-07-02T00:00:00Z"
        self.reject(data,"GATE_POPULATION_NOT_AS_KNOWN_COMPLETE")

    def test_preperiod_own_cutoff_and_missing_history_gap(self):
        data=fixture();history=data["opening_state"]["frames"][0]
        history["evidence"][0]["observed_at"]="2008-04-05T00:00:00Z"
        self.reject(data,"GATE_EVIDENCE_CUTOFF")
        data=fixture();data["opening_state"]["frames"][0]["period"]["start"]="2008-01-02"
        self.reject(data,"GATE_HISTORY_ADJACENCY")

    def test_receipt_equality_below_and_above_discriminators(self):
        for amount,expected,status in [("19",0,"inapplicable"),("20",0,"computed_zero"),("21",F(1,5),"computed_positive")]:
            data=fixture();data["rows"]=[data["rows"][0]];data["rows"][0]["amount"]=amount;sync(data)
            result=ordered_gates(data)
            self.assertEqual((result["gross_candidate"],result["gross_status"]),(expected,status))


if __name__=="__main__":unittest.main()
