"""Original-fact mixed claim controls; no executable SPL is read or imported."""
import ast
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest

from oracles.mixed_claims import MixedClaimOracleError, exact_json, mixed_claims, policy

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/mixed-waterfall/neutral.json").read_text(encoding="utf-8"))


def method(data, name):
    data["policy"] = policy(name)
    ranks = {"fee":0,"approved_correction":1,"capital":2,"advance":3}
    if name == "priority_correction_first": ranks.update(fee=1, approved_correction=0)
    for claim in data["registry"]["claim_authorities"]: claim["priority"] = ranks[claim["kind"]]
    return data


def two_claims(data):
    data["registry"]["claim_authorities"] = [c for c in data["registry"]["claim_authorities"] if c["kind"] in {"capital","advance"}]
    return data


def capacity(data, amount):
    data["earnings"][0]["base_amount"] = str(F(amount) * 2)
    data["earning_population"]["gross_basis_total"] = str(F(amount) * 2)
    return data


def ledger(result):
    return {row["kind"]: row for row in result["claim_ledger"]}


def successor(original, previous, amount="90"):
    data = deepcopy(original)
    def rewrite(value):
        if isinstance(value,dict): return {k:rewrite(v) for k,v in value.items()}
        if isinstance(value,list): return [rewrite(v) for v in value]
        if isinstance(value,str): return value.replace("q1","q2").replace("2026-03-","2026-06-").replace("2026-04-","2026-07-")
        return value
    for key in ("earnings","earning_population","cash_settlement_population","evidence"): data[key] = rewrite(data[key])
    data.update(case_id="mixed-q2",period={"start":"2026-04-01","end":"2026-07-01"},as_of="2026-06-30",cutoff="2026-07-03T00:00:00Z")
    for key in ("earning_population","cash_settlement_population"): data[key]["period"] = deepcopy(data["period"])
    capacity(data,amount)
    prior = json.loads(json.dumps(exact_json(previous)))
    data["opening_state"] = prior["closing_state"]
    data["prior_result"] = {"source_case_id":prior["source_case_id"],"period":prior["period"],"closing_state":prior["closing_state"],"result_ref":"supplied-result-reference#"+prior["source_case_id"]}
    return data


class MixedClaimOracleTests(unittest.TestCase):
    def reject(self, data, code):
        before = deepcopy(data)
        with self.assertRaisesRegex(MixedClaimOracleError,"^"+code+"$"): mixed_claims(data)
        self.assertEqual(data,before)

    def test_original_amount_spaces_and_full_mixed_priority(self):
        result = mixed_claims(fixture()); claims = ledger(result)
        self.assertEqual((result["capacity"],result["recoupment_credits"],result["earning_offsets"],result["residual_entitlement"]),(120,75,45,0))
        self.assertEqual([claims[k]["remaining"] for k in ["fee","approved_correction","capital","advance"]],[0,0,25,100])
        controls = result["original_source_controls"]
        self.assertEqual((controls["capital_actual_funding"],controls["advance_actual_funding"]),(100,100))
        self.assertEqual(controls["fee_sources"],[{"id":"fee-source","original_base":F(250),"original_rate":F(1,10),"derived_fee":F(25)}])
        self.assertEqual(result["original_correction_controls"],[{"id":"correction-source","original_entitlement":F(100),"reversal":F(40),"revised_entitlement":F(60),
            "actual_original_paid":F(80),"original_outstanding":F(0),"potential_overpayment":F(20)}])
        self.assertEqual(result["unissued_allocations_added"],75)
        self.assertFalse(result["bank_movement_created"])
        self.assertEqual(result["actual_current_claim_cash_settlement"],0)

    def test_capital_advance_120_priority100_20_versus_prorata60_60(self):
        data=two_claims(fixture());priority=mixed_claims(data);proportional=mixed_claims(method(deepcopy(data),"pro_rata_eligible_balances"))
        self.assertEqual([ledger(priority)[k]["recoupment_credit"] for k in ["capital","advance"]],[100,20])
        self.assertEqual([ledger(proportional)[k]["recoupment_credit"] for k in ["capital","advance"]],[60,60])
        self.assertEqual([ledger(proportional)[k]["remaining"] for k in ["capital","advance"]],[40,40])
        self.assertEqual(priority["earning_offsets"],0)

    def test_fee_correction_competing30_changes_purpose_balances(self):
        first=mixed_claims(capacity(fixture(),"30"))
        second=mixed_claims(method(capacity(fixture(),"30"),"priority_correction_first"))
        self.assertEqual([ledger(first)[k]["earning_offset"] for k in ["fee","approved_correction"]],[25,5])
        self.assertEqual([ledger(second)[k]["earning_offset"] for k in ["fee","approved_correction"]],[10,20])
        self.assertEqual([ledger(first)[k]["remaining"] for k in ["fee","approved_correction"]],[0,15])
        self.assertEqual([ledger(second)[k]["remaining"] for k in ["fee","approved_correction"]],[15,0])
        self.assertEqual(first["original_correction_controls"][0]["actual_original_paid"],80)

    def test_exact_all_kind_pro_rata_no_cent_rounding(self):
        result=mixed_claims(method(fixture(),"pro_rata_eligible_balances"));claims=ledger(result)
        self.assertEqual([claims[k]["recoupment_credit"]+claims[k]["earning_offset"] for k in ["capital","advance","fee","approved_correction"]],
                         [F(2400,49),F(2400,49),F(600,49),F(480,49)])
        self.assertEqual((result["recoupment_credits"],result["earning_offsets"]),(F(4800,49),F(1080,49)))
        self.assertEqual(result["residual_entitlement"],0)

    def test_excess270_residual_complete_roster_and_no_double_fee_deduction(self):
        result=mixed_claims(capacity(fixture(),"270"))
        self.assertEqual((result["recoupment_credits"],result["earning_offsets"],result["residual_entitlement"]),(200,45,25))
        self.assertEqual([r["residual_entitlement"] for r in result["residual_lines"]],[F(25,2),F(25,2)])
        self.assertEqual(result["unissued_allocations_added"],225)
        self.assertEqual(sum((r["amount"] for r in result["current_unissued_allocations"]),F()),225)
        self.assertEqual(result["capacity"],270)  # Fee25 is an offset claim, not another pre-fund deduction.

    def test_actual_serialized120_then90_keeps_old_unissued_allocations(self):
        data=two_claims(fixture());first=mixed_claims(data);second_data=successor(data,first);second=mixed_claims(second_data)
        self.assertEqual((second["capacity"],second["recoupment_credits"],second["residual_entitlement"]),(90,80,10))
        self.assertEqual([r["residual_entitlement"] for r in second["residual_lines"]],[5,5])
        self.assertEqual([ledger(second)[k]["remaining"] for k in ["capital","advance"]],[0,0])
        state=second["closing_state"]
        self.assertEqual(sum((F(r["amount"]) for r in state["unissued_allocation_ledger"]),F()),210)
        self.assertEqual(len(state["history"]),2)
        self.assertEqual(state["history"][0]["facts"]["earnings"],data["earnings"])
        self.assertEqual(exact_json(mixed_claims(second_data)),exact_json(second))
        self.assertEqual(first["claim_ledger"][0]["remaining"],80)  # Prior snapshot is not later mutated.

    def test_actual_all_four_kind120_then90_consumes_fee_and_correction_once(self):
        data=fixture();first=mixed_claims(data);second_data=successor(data,first);second=mixed_claims(second_data)
        kinds=["fee","approved_correction","capital","advance"]
        def current_by_kind(result):
            return [sum((row["applied"] for row in result["claim_movements"] if row["kind"]==kind),F()) for kind in kinds]
        self.assertEqual(current_by_kind(first),[25,20,75,0])
        self.assertEqual(current_by_kind(second),[0,0,25,65])
        self.assertEqual([ledger(second)[kind]["remaining"] for kind in kinds],[0,0,0,35])
        self.assertEqual(second["earning_offsets"],0)
        self.assertEqual(second["current_offset_records"],[])
        self.assertEqual(len(second["closing_state"]["earning_offset_ledger"]),2)
        self.assertEqual(sum((F(row["amount"]) for row in second["closing_state"]["unissued_allocation_ledger"]),F()),165)
        self.assertEqual(second["original_correction_controls"][0]["actual_original_paid"],80)
        self.assertEqual([entry["facts"]["cutoff"] for entry in second["closing_state"]["history"]],["2026-04-03T00:00:00Z","2026-07-03T00:00:00Z"])
        self.assertTrue(all(entry["facts"]["cash_settlement_population"]["complete"] and entry["facts"]["cash_settlement_population"]["event_ids"]==[] for entry in second["closing_state"]["history"]))

    def test_event_time_eligibility_prevents_retroactive_offset_of_earlier_capacity(self):
        data=fixture();early=deepcopy(data["earnings"][0]);late=deepcopy(early)
        early.update(id="earning:early",base_amount="60",effective_date="2026-02-20",observed_at="2026-02-21T00:00:00Z",original_ref="original-earning#early")
        late.update(id="earning:late",base_amount="60",original_ref="original-earning#late")
        # Use original kind authority with observation moved to the earlier actual event.
        evidence=next(r for r in data["evidence"] if r["id"]==early["evidence_ref"]);evidence["observed_at"]="2026-02-21T00:00:00Z"
        data["earnings"]=[late,early];data["earning_population"].update(earning_ids=[early["id"],late["id"]],gross_basis_total="120")
        result=mixed_claims(data)
        self.assertEqual((result["capacity"],result["recoupment_credits"],result["earning_offsets"]),(60,30,30))
        self.assertEqual([r["earning"]["id"] for r in result["event_details"]],["earning:early","earning:late"])
        self.assertEqual(ledger(result)["capital"]["remaining"],70)
        self.assertEqual(ledger(result)["approved_correction"]["remaining"],15)

    def test_empty_zero_and_fully_recovered_cases(self):
        data=fixture();data["earnings"]=[];data["earning_population"].update(earning_ids=[],gross_basis_total="0")
        result=mixed_claims(data);self.assertEqual((result["capacity"],result["recoupment_credits"],result["earning_offsets"]),(0,0,0))
        data=capacity(fixture(),"0");self.assertEqual(mixed_claims(data)["residual_entitlement"],0)
        data=fixture();data["registry"]["claim_authorities"]=[]
        result=mixed_claims(data);self.assertEqual(result["residual_entitlement"],120)
        self.assertEqual([r["residual_entitlement"] for r in result["residual_lines"]],[60,60])
        first=mixed_claims(capacity(fixture(),"270"));second=mixed_claims(successor(fixture(),first,"10"))
        self.assertEqual((second["recoupment_credits"],second["earning_offsets"],second["residual_entitlement"]),(0,0,10))

    def test_whole_roster_positive_denominator_even_when_no_residual(self):
        for change,code in [(lambda r:r["residual_weights"].pop(),"MIXED_RESIDUAL_WEIGHT_POPULATION"),
            (lambda r:[v.update(weight="0") for v in r["residual_weights"]],"MIXED_RESIDUAL_WEIGHT_POPULATION"),
            (lambda r:r["roster_authority"].update(member_ids=[]),"MIXED_COMPLETE_RESIDUAL_ROSTER"),
            (lambda r:r["roster_authority"].update(complete=False),"MIXED_COMPLETE_RESIDUAL_ROSTER")]:
            data=capacity(fixture(),"0");change(data["registry"]);self.reject(data,code)
        data=capacity(fixture(),"270");data["registry"]["residual_weights"][0]["weight"]="0"
        self.assertEqual([r["residual_entitlement"] for r in mixed_claims(data)["residual_lines"]],[25,0])

    def test_current_cash_settlement_unknown_and_nonempty_are_not_zero(self):
        data=fixture();data["cash_settlement_population"]["complete"]=False;self.reject(data,"MIXED_CURRENT_CASH_SETTLEMENT_UNKNOWN")
        data=fixture();data["cash_settlement_population"].update(event_ids=["actual-bank-repayment"],total="5")
        self.reject(data,"MIXED_NONEMPTY_CASH_SETTLEMENT_VARIANT_REQUIRED")

    def test_funding_missing_population_and_face_without_actual_funding(self):
        data=fixture();data["registry"]["funding_populations"]=[p for p in data["registry"]["funding_populations"] if p["kind"]!="advance"]
        self.reject(data,"MIXED_COMPLETE_FUNDING_POPULATION_REQUIRED")
        data=fixture();data["registry"]["advance_fundings"]=[]
        pop=next(p for p in data["registry"]["funding_populations"] if p["kind"]=="advance");pop.update(funding_ids=[],total="0")
        auth=next(a for a in data["registry"]["claim_authorities"] if a["kind"]=="advance");auth["source_ids"]=[]
        self.reject(data,"MIXED_AUTHORIZED_PRINCIPAL_EXCEEDS_SOURCE")
        auth["authorized_principal"]="0"
        self.assertEqual(ledger(mixed_claims(data))["advance"]["authorized_principal"],0)

    def test_correction_requires_complete_actual_paid_not_original_entitlement(self):
        data=fixture();data["registry"]["historical_payment_populations"]=[]
        self.reject(data,"MIXED_COMPLETE_ORIGINAL_PAYMENT_POPULATION_REQUIRED")
        data=fixture();r=data["registry"];r["historical_payments"]=[];r["historical_applications"]=[]
        r["historical_payment_populations"][0].update(payment_ids=[],application_ids=[],paid_total="0")
        self.reject(data,"MIXED_AUTHORIZED_PRINCIPAL_EXCEEDS_SOURCE")
        next(a for a in r["claim_authorities"] if a["kind"]=="approved_correction")["authorized_principal"]="0"
        result=mixed_claims(data);self.assertEqual(result["original_correction_controls"][0]["actual_original_paid"],0)
        self.assertEqual(ledger(result)["approved_correction"]["authorized_principal"],0)

    def test_duplicate_original_bank_fee_and_correction_line_aliases(self):
        data=fixture();data["registry"]["advance_fundings"][0]["original_ref"]=data["registry"]["capital_fundings"][0]["original_ref"]
        self.reject(data,"MIXED_BANK_LINE_ALIAS")
        for key in ("fee_bases","correction_sources","historical_payments"):
            data=fixture();clone=deepcopy(data["registry"][key][0]);clone["id"]="relabeled-source";data["registry"][key].append(clone)
            self.reject(data,"MIXED_BANK_LINE_ALIAS" if key=="historical_payments" else "MIXED_FEE_CORRECTION_LINE_ALIAS")

    def test_reusing_source_under_new_authority_or_relabeling_authority_rejects(self):
        data=fixture();clone=deepcopy(data["registry"]["claim_authorities"][0]);clone.update(id="new-claim",sequence=2,original_ref="new-authority#line")
        data["registry"]["claim_authorities"].append(clone);self.reject(data,"MIXED_CLAIM_SOURCE_REUSE")
        clone["original_ref"]=data["registry"]["claim_authorities"][0]["original_ref"]
        self.reject(data,"MIXED_AUTHORITY_LINE_ALIAS")

    def test_principal_caps_and_per_kind_beneficiary_authority(self):
        data=fixture();next(a for a in data["registry"]["claim_authorities"] if a["kind"]=="approved_correction")["authorized_principal"]="21"
        self.reject(data,"MIXED_AUTHORIZED_PRINCIPAL_EXCEEDS_SOURCE")
        data=fixture();next(a for a in data["registry"]["claim_authorities"] if a["kind"]=="capital")["beneficiary"]="advance-owner"
        self.reject(data,"MIXED_CLAIM_FUNDING_AUTHORITY")
        data=fixture();next(a for a in data["registry"]["claim_authorities"] if a["kind"]=="fee")["beneficiary"]="capital-owner"
        self.reject(data,"MIXED_RECIPROCAL_OFFSET_AUTHORITY")

    def test_same_date_earning_and_claim_ties_do_not_use_source_position(self):
        data=fixture();other=deepcopy(data["earnings"][0]);other.update(id="other-earning",original_ref="original-earning#second")
        data["earnings"].append(other);self.reject(data,"MIXED_UNRESOLVED_EARNING_ORDER")
        data=fixture();claim=deepcopy(data["registry"]["claim_authorities"][0]);claim.update(id="other-capital",original_ref="authority#other")
        data["registry"]["claim_authorities"].append(claim);self.reject(data,"MIXED_UNRESOLVED_CLAIM_ORDER")

    def test_cutoff_scope_approval_and_original_source_chronology(self):
        data=fixture();data["earnings"][0]["scope"]["pool_id"]="other";self.reject(data,"MIXED_FACT_SCOPE")
        data=fixture();data["earnings"][0]["observed_at"]=data["cutoff"];self.reject(data,"MIXED_SOURCE_OBSERVATION_AUTHORITY")
        data=fixture();data["registry"]["claim_authorities"][0]["approved"]=False;self.reject(data,"MIXED_PROSPECTIVE_AUTHORITY")
        data=fixture();data["registry"]["historical_applications"][0]["amount"]="79";self.reject(data,"MIXED_ORIGINAL_PAYMENT_CONSERVATION")
        data=fixture();funding=data["registry"]["capital_fundings"][0]
        funding.update(funded_at="2026-04-01T00:00:00Z",observed_at="2026-04-02T00:00:00Z")
        self.reject(data,"MIXED_FUNDING_CHRONOLOGY")

    def test_fee_basis_is_not_also_current_fund_and_reversal_is_not_second_deduction(self):
        data=fixture();data["earnings"][0]["original_ref"]=data["registry"]["fee_bases"][0]["original_ref"]
        self.reject(data,"MIXED_FUND_SOURCE_AMOUNT_SPACE_OVERLAP")
        result=mixed_claims(capacity(fixture(),"30"))
        self.assertEqual(result["capacity"],30)
        self.assertEqual(result["original_correction_controls"][0]["reversal"],40)
        self.assertEqual(result["earning_offsets"],30)  # Never deduct old reversal40 as well.

    def test_actual_predecessor_registry_financial_history_and_alias_checks(self):
        original=two_claims(fixture());first=mixed_claims(original)
        data=successor(original,first);del data["prior_result"];self.reject(data,"MIXED_PREDECESSOR_REQUIRED")
        data=successor(original,first);data["opening_state"]["claim_ledger"][0]["remaining"]="0";self.reject(data,"MIXED_OPENING_RECONCILIATION")
        data=successor(original,first);data["opening_state"]["history"][0]["result"]["recoupment_credits"]="0";self.reject(data,"MIXED_HISTORY_FINANCIAL_REPLAY")
        data=successor(original,first);data["registry"]["claim_authorities"][0]["authorized_principal"]="99";self.reject(data,"MIXED_REGISTRY_AMENDMENT_OR_NEW_CLAIM")
        data=successor(original,first);data["earnings"][0]["original_ref"]=original["earnings"][0]["original_ref"];self.reject(data,"MIXED_EARNING_REPLAY_ALIAS")

    def test_fraction_and_physical_permutation_preserve_finance(self):
        data=two_claims(capacity(fixture(),"1/3"));result=mixed_claims(data)
        self.assertEqual(result["capacity"],F(1,3));self.assertEqual(ledger(result)["capital"]["recoupment_credit"],F(1,3))
        other=deepcopy(data)
        for value in other["registry"].values():
            if isinstance(value,list):value.reverse()
        self.assertEqual({k:v for k,v in result.items() if k!="closing_state"},{k:v for k,v in mixed_claims(other).items() if k!="closing_state"})

    def test_independence_and_no_data_mutation(self):
        data=fixture();before=deepcopy(data);mixed_claims(data);self.assertEqual(data,before)
        tree=ast.parse((ROOT/"oracles/mixed_claims.py").read_text(encoding="utf-8"))
        imported={n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
        imported|={a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
        self.assertEqual(imported,{"copy","datetime","fractions","re"})


if __name__ == "__main__":unittest.main()
