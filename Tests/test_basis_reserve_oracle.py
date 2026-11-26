"""Hand controls from original facts, independently of SPL/compiler code."""
import ast
from copy import deepcopy
from datetime import date
from fractions import Fraction as F
import json
from pathlib import Path
import unittest

from oracles.basis_reserves import BasisReserveOracleError, basis_reserves, exact_json, _add_six_months


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "cases/basis-reserves/neutral.json"


def original_facts():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["facts"]


def view(facts, index, prior=None):
    """Transport original known rows; no release/fee/net/recipient arithmetic."""
    data = deepcopy(facts)
    cp = data["checkpoints"][index]
    data["case_id"], data["run_checkpoint_id"] = cp["source_case_id"], cp["id"]
    data["checkpoints"] = data["checkpoints"][:index + 1]
    cps = {row["id"] for row in data["checkpoints"]}
    for key in ("populations", "clearances"):
        data[key] = [row for row in data[key] if row["checkpoint_id"] in cps]
    data["receipts"] = [row for row in data["receipts"] if row["receipt_date"] <= cp["as_of"]]
    receipt_ids = {row["id"] for row in data["receipts"]}
    data["elections"] = [row for row in data["elections"] if row["receipt_id"] in receipt_ids]
    data["returns"] = [row for row in data["returns"] if row["return_date"] <= cp["as_of"]]
    return_ids = {row["id"] for row in data["returns"]}
    data["return_authorities"] = [row for row in data["return_authorities"] if row["return_id"] in return_ids]
    # Fixture instants use UTC Z and uniform seconds; filtering preserves raw bytes.
    data["evidence"] = [row for row in data["evidence"] if row["observed_at"] < cp["cutoff"]]
    if prior is None:
        data["opening_state"] = {"scope": data["scope"], "purpose": "basis_stage_videogram_returns", "policy": data["policy"],
                                 "boundary": data["authority"]["effective"]["start"], "origin": "genesis", "source_case_id": "genesis"}
    else:
        transported = json.loads(json.dumps(exact_json(prior)))
        data["opening_state"] = transported["closing_state"]
        data["prior_result"] = {"source_case_id": transported["source_case_id"], "period": transported["period"],
                                "closing_state": transported["closing_state"], "result_ref": "supplied-result-reference#" + transported["source_case_id"]}
    return data


def chain(facts=None):
    facts = original_facts() if facts is None else facts
    results, prior = [], None
    for index in range(len(facts["checkpoints"])):
        prior = basis_reserves(view(facts, index, prior))
        results.append(prior)
    return results


def replace_amount(facts, key, identity, value):
    """Update separately declared original population totals for a changed test fact."""
    row = next(row for row in facts[key] if row["id"] == identity)
    delta = F(value) - F(row["amount"])
    row["amount"] = value
    ids_field, total_field = ("receipt_ids", "receipt_total") if key == "receipts" else ("return_ids", "return_total")
    for pop in facts["populations"]:
        if identity in pop[ids_field]:
            pop[total_field] = str(F(pop[total_field]) + delta)


def second_return(facts, amount="150", day="2009-07-15"):
    returned, authority = deepcopy(facts["returns"][0]), deepcopy(facts["return_authorities"][0])
    returned.update(id="return:2", claim_id="original-retailer-claim:2", amount=amount, return_date=day,
                    observed_at=day + "T13:00:00Z", authority_id="return-authority:2", return_line_ref="original-returns-ledger#2",
                    source_ref="synthetic-source:return:2", evidence_ref="ev:return:2")
    authority.update(id="return-authority:2", return_id="return:2", approved_date=day, observed_at=day + "T12:00:00Z",
                     source_ref="synthetic-source:return-authority:2", evidence_ref="ev:return-authority:2")
    facts["returns"].append(returned); facts["return_authorities"].append(authority)
    for row, kind in ((returned, "actual_customer_return"), (authority, "approved_original_return_application")):
        facts["evidence"].append(dict(id=row["evidence_ref"], scope=deepcopy(facts["scope"]), kind=kind, approved=True,
                                      observed_at=row["observed_at"], source_ref="synthetic-evidence:" + row["id"]))
    for cp, pop in zip(facts["checkpoints"], facts["populations"]):
        if day <= cp["as_of"]:
            pop["return_ids"].append(returned["id"]); pop["authority_ids"].append(authority["id"])
            pop["return_total"] = str(F(pop["return_total"]) + F(amount))


class BasisReserveOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaisesRegex(BasisReserveOracleError, "^" + code + "$"):
            basis_reserves(data)

    def test_five_original_checkpoints_and_stage_discriminator(self):
        results = chain()
        expected = [(1000, 200, 0, 800, 80, 720, 200), (800, 160, 0, 640, 64, 576, 360),
                    (0, 0, 0, 0, 0, 0, 300), (0, 0, 140, 140, 14, 126, 160), (0, 0, 160, 160, 16, 144, 0)]
        fields = ("gross", "added", "released", "net_receipts", "fee", "allocation", "closing_reserve")
        for result, control in zip(results, expected):
            self.assertEqual(tuple(result[key] for key in fields), control)
        self.assertEqual(results[2]["applied_returns"], 60)
        self.assertNotEqual(results[0]["fee"], 100)  # Fee-before-reserve is a different policy.
        self.assertNotEqual(results[0]["allocation"], 700)
        self.assertEqual(results[-1]["cumulative"], dict(gross=F(1800), added=F(360), applied_returns=F(60), released=F(300),
                                                       net_receipts=F(1740), fee=F(174), allocation=F(1566)))
        self.assertNotEqual(results[-1]["cumulative"]["net_receipts"], 1680)  # Return cannot reduce NR twice.

    def test_actual_serialized_predecessor_retains_originals(self):
        results = chain()
        old = results[0]["closing_state"]["vintages"][0]
        self.assertEqual(old["available"], 200)  # Later mutation cannot rewrite the original snapshot.
        final = results[-1]["closing_state"]
        self.assertEqual(final["boundary"], "2009-10-16")
        self.assertEqual(final["source_case_id"], "genius:oct")
        self.assertEqual(final["sources"]["receipts"], original_facts()["receipts"])
        self.assertEqual([v["cash_line_ref"] for v in final["vintages"]], ["original-cash-ledger#1", "original-cash-ledger#2"])
        self.assertEqual([v["release_ids"] for v in final["vintages"]], [["due-release:V1"], ["due-release:V2"]])
        self.assertEqual(final["vintages"][0]["claim_ids"], ["original-retailer-claim:1"])
        self.assertEqual(json.loads(json.dumps(exact_json(final)))["cumulative"]["allocation"], "1566")

    def test_no_release_replay_when_original_history_is_reused(self):
        data = view(original_facts(), 4, chain()[3])
        a, b = basis_reserves(data), basis_reserves(json.loads(json.dumps(data)))
        self.assertEqual(exact_json(a), exact_json(b))
        self.assertEqual(a["released"], 160)
        self.assertEqual(a["cumulative"]["released"], 300)
        self.assertEqual(len([x for x in a["closing_state"]["movements"] if x["kind"] == "calculated_due_unused_release"]), 2)

    def test_positive_non_elected_receipt_is_not_rejected(self):
        facts = original_facts(); facts["elections"][0]["elected"] = False
        result = basis_reserves(view(facts, 0))
        self.assertEqual((result["added"], result["net_receipts"], result["fee"], result["allocation"]), (0, 1000, 100, 900))
        self.assertEqual(result["vintages"][0]["available"], 0)
        self.assertFalse(result["vintages"][0]["reserve_elected"])

    def test_zero_receipt_with_explicit_election(self):
        facts = original_facts(); replace_amount(facts, "receipts", "receipt:1", "0")
        result = basis_reserves(view(facts, 0))
        self.assertEqual((result["gross"], result["added"], result["fee"], result["allocation"]), (0, 0, 0, 0))

    def test_complete_empty_population_is_explicit(self):
        data = view(original_facts(), 0)
        data["receipts"] = []; data["elections"] = []
        pop = data["populations"][0]
        pop.update(receipt_ids=[], receipt_total="0", election_ids=[])
        result = basis_reserves(data)
        self.assertEqual(result["gross"], 0)
        self.assertEqual(result["vintages"], [])

    def test_exact_fraction_without_implicit_cent_rounding(self):
        facts = original_facts(); replace_amount(facts, "receipts", "receipt:1", "1/3")
        result = basis_reserves(view(facts, 0))
        self.assertEqual((result["added"], result["net_receipts"], result["fee"], result["allocation"]), (F(1,15), F(4,15), F(2,75), F(6,25)))

    def test_due_equality_and_anniversary_clamp(self):
        self.assertEqual(_add_six_months(date(2009, 1, 15)), date(2009, 7, 15))
        self.assertEqual(_add_six_months(date(2009, 4, 30)), date(2009, 10, 30))
        self.assertEqual(_add_six_months(date(2008, 8, 31)), date(2009, 2, 28))
        self.assertEqual(_add_six_months(date(2007, 8, 31)), date(2008, 2, 29))
        self.assertEqual(chain()[3]["movements"][0]["date"], "2009-07-15")

    def test_one_day_before_deadline_has_no_release(self):
        facts = original_facts()
        cp = facts["checkpoints"][3]
        cp["as_of"] = "2009-07-14"; cp["period"]["end"] = "2009-07-15"
        facts["checkpoints"][4]["period"]["start"] = "2009-07-15"
        result = chain(facts)[3]
        self.assertEqual((result["released"], result["closing_reserve"]), (0, 300))
        self.assertEqual(chain(facts)[4]["released"], 300)  # Due event is derived inside a spanning window.

    def test_same_day_original_return_precedes_calculated_release(self):
        facts = original_facts()
        returned, auth = facts["returns"][0], facts["return_authorities"][0]
        returned.update(return_date="2009-07-15", observed_at="2009-07-15T13:00:00Z")
        auth.update(approved_date="2009-07-15", observed_at="2009-07-15T12:00:00Z")
        for row in facts["evidence"]:
            if row["id"] == returned["evidence_ref"]: row["observed_at"] = returned["observed_at"]
            if row["id"] == auth["evidence_ref"]: row["observed_at"] = auth["observed_at"]
        facts["populations"][2].update(return_ids=[], return_total="0", authority_ids=[])
        result = chain(facts)[3]
        self.assertEqual((result["applied_returns"], result["released"]), (60, 140))
        self.assertEqual([r["kind"] for r in result["movements"]], ["matched_actual_return", "calculated_due_unused_release"])

    def test_excess_vintage_return_is_qualified_unsupported(self):
        facts = original_facts(); replace_amount(facts, "returns", "return:1", "201")
        prior = chain(facts={**facts, "checkpoints": facts["checkpoints"][:2]})[-1]
        self.reject(view(facts, 2, prior), "BR_EXCESS_RETURN_VARIANT_REQUIRED")
        self.assertEqual(chain()[-1]["source_support"], "partial_within_vintage_returns_only")

    def test_return_cannot_borrow_another_vintage(self):
        facts = original_facts(); second_return(facts)
        self.reject(view(facts, 3, chain()[2]), "BR_EXCESS_RETURN_VARIANT_REQUIRED")  # V2 has160; V1 remaining140.

    def test_partial_returns_equal_remaining_vintage_before_due_release(self):
        facts = original_facts(); second_return(facts, "140")
        result = chain(facts)[3]
        self.assertEqual((result["applied_returns"], result["released"], result["closing_reserve"]), (140, 0, 160))
        self.assertEqual(result["vintages"][0]["applied_returns"], 200)
        self.assertEqual(result["vintages"][0]["return_ids"], ["return:1", "return:2"])

    def test_duplicate_claim_alias_and_explicit_sequence_tie(self):
        facts = original_facts(); second_return(facts, "10", "2009-05-15")
        facts["returns"][1]["claim_id"] = facts["returns"][0]["claim_id"]
        self.reject(view(facts, 2, chain()[1]), "BR_RETURN_CLAIM_ALIAS")
        facts["returns"][1]["claim_id"] = "original-retailer-claim:2"
        self.reject(view(facts, 2, chain()[1]), "BR_EXPLICIT_EVENT_SEQUENCE")

    def test_after_liquidation_return_requires_separate_source_variant(self):
        facts = original_facts(); second_return(facts, "1", "2009-10-15")
        self.reject(view(facts, 4, chain()[3]), "BR_RETURN_AFTER_LIQUIDATION_VARIANT_REQUIRED")

    def test_non_elected_return_has_no_invented_reserve(self):
        facts = original_facts(); facts["elections"][0]["elected"] = False
        prior = chain(facts={**facts, "checkpoints": facts["checkpoints"][:2]})[-1]
        self.reject(view(facts, 2, prior), "BR_EXCESS_RETURN_VARIANT_REQUIRED")

    def test_exact_submicrosecond_observation_before_cutoff(self):
        data = view(original_facts(), 0)
        data["evidence"][0]["observed_at"] = "2009-01-16T23:59:59.999999999999Z"
        self.assertEqual(basis_reserves(data)["net_receipts"], 800)

    def test_duplicate_original_id(self):
        data = view(original_facts(), 0); data["receipts"].append(deepcopy(data["receipts"][0]))
        self.reject(data, "BR_DUPLICATE_ID")

    def test_original_cash_parent_alias(self):
        facts = original_facts(); facts["receipts"][1]["cash_line_ref"] = facts["receipts"][0]["cash_line_ref"]
        self.reject(view(facts, 1, chain()[0]), "BR_CASH_PARENT_ALIAS")

    def test_wrong_scope_and_wrong_purpose(self):
        data = view(original_facts(), 0); data["receipts"][0]["scope"]["pool_id"] = "other"
        self.reject(data, "BR_FACT_SCOPE")
        data = view(original_facts(), 0); data["elections"][0]["purpose"] = "other"
        self.reject(data, "BR_VINTAGE_IDENTITY_PURPOSE")

    def test_missing_or_false_population_is_not_empty_zero(self):
        data = view(original_facts(), 0); data["populations"] = []
        self.reject(data, "BR_COMPLETE_POPULATION_REQUIRED")
        data = view(original_facts(), 0); data["populations"][0]["complete"] = False
        self.reject(data, "BR_COMPLETE_POPULATION_REQUIRED")

    def test_wrong_population_total(self):
        data = view(original_facts(), 0); data["populations"][0]["receipt_total"] = "999"
        self.reject(data, "BR_ORIGINAL_POPULATION_CONTROL")

    def test_missing_evidence_and_cutoff_equality(self):
        data = view(original_facts(), 0); data["evidence"] = [r for r in data["evidence"] if r["id"] != data["receipts"][0]["evidence_ref"]]
        self.reject(data, "BR_EVIDENCE_REQUIRED")
        data = view(original_facts(), 0); data["evidence"][0]["observed_at"] = data["checkpoints"][0]["cutoff"]
        self.reject(data, "BR_EVIDENCE_AFTER_CUTOFF")

    def test_late_old_fact_not_rewritten_under_current_cutoff(self):
        data = view(original_facts(), 4, chain()[3]); data["receipts"][0]["observed_at"] = "2009-02-01T00:00:00Z"
        self.reject(data, "BR_SOURCE_AFTER_CUTOFF")

    def test_selected_fee_rate_and_liquidation_policy_pinned(self):
        data = view(original_facts(), 0); data["authority"]["fee_rate"] = "1/5"
        self.reject(data, "BR_SELECTED_TERMS")
        data = view(original_facts(), 0); data["policy"]["months"] = "12"
        self.reject(data, "BR_SELECTED_POLICY")

    def test_other_claims_and_missing_clearance_block(self):
        data = view(original_facts(), 0); data["clearances"][0]["expense_remaining"] = "1"
        self.reject(data, "BR_CLAIMS_NOT_CLEARED")
        data = view(original_facts(), 0); data["clearances"] = []
        self.reject(data, "BR_CLAIM_CLEARANCE_REQUIRED")

    def test_unknown_vintage_and_unused_return_authority(self):
        data = view(original_facts(), 2, chain()[1]); data["returns"][0]["vintage_id"] = "unknown"
        self.reject(data, "BR_RETURN_VINTAGE_LINEAGE")
        data = view(original_facts(), 2, chain()[1]); data["return_authorities"][0]["return_id"] = "unknown"
        self.reject(data, "BR_UNUSED_RETURN_AUTHORITY")

    def test_actual_predecessor_required_and_scope_bound(self):
        data = view(original_facts(), 1, chain()[0]); del data["prior_result"]
        self.reject(data, "BR_PREDECESSOR_REQUIRED")
        data = view(original_facts(), 1, chain()[0]); data["prior_result"]["source_case_id"] = "other"
        self.reject(data, "BR_PREDECESSOR_MISMATCH")

    def test_forged_opening_balance_and_overdue_state(self):
        data = view(original_facts(), 1, chain()[0]); data["opening_state"]["vintages"][0]["available"] = "201"
        self.reject(data, "BR_OPENING_RECONCILIATION")
        data = view(original_facts(), 4, chain()[3]); data["opening_state"]["vintages"][0]["available"] = "1"
        self.reject(data, "BR_OPENING_OVERDUE")

    def test_original_order_not_array_order_controls(self):
        facts = original_facts()
        for key in ("receipts", "elections", "evidence", "checkpoints", "populations", "clearances"):
            # Checkpoints are deliberately left chronological in the materializer, then reverse transported list below.
            if key != "checkpoints": facts[key].reverse()
        data = view(facts, 4, chain(facts)[3]); data["checkpoints"].reverse()
        self.assertEqual(exact_json(basis_reserves(data)), exact_json(chain()[-1]))

    def test_no_solved_release_or_bank_payment_inputs(self):
        data = view(original_facts(), 0); data["receipts"][0]["release_amount"] = "200"
        self.reject(data, "BR_RECORD_FIELDS")
        result = chain()[-1]
        self.assertEqual(result["payment_status"], "not_assessed_no_bank_payment_measure")
        self.assertNotIn("paid", result)
        self.assertNotIn("payable", result)

    def test_no_compiler_or_source_dependency_and_lf_files(self):
        module = ROOT / "oracles/basis_reserves.py"
        tree = ast.parse(module.read_text(encoding="utf-8"))
        imported = {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        imported |= {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imported, {"calendar", "datetime", "fractions", "re"})
        for path in (module, FIXTURE, Path(__file__)):
            self.assertNotIn(b"\r", path.read_bytes())


if __name__ == "__main__":
    unittest.main()
