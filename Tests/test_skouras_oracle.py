"""Independent raw SV controls, without reading SPL or compiler calculations."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.skouras import SkourasOracleError, exact_json, skouras


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/sv/neutral-oracle.json").read_text(encoding="utf-8"))


def recount(data):
    package = data["package"]
    for batch in package["source_batches"]:
        key = {name: batch[name] for name in ("source_system", "batch_id", "version")}
        batch["row_count"] = sum(row["batch_ref"] == key for row in package["financial_facts"])


def bundle_fixture():
    """Original parent cash100000 plus direct60000, with separate .4/.6 authority."""
    data = fixture()
    package = data["package"]
    cash_a, cash_b = package["financial_facts"][:2]
    cash_a["amount"]["value"] = "60000"
    package["assets"].append({"asset_id": "bundle-ab", "kind": "bundle"})
    invoice = deepcopy(cash_b)
    invoice.update(fact_id="invoice-bundle", source_row="invoice-bundle", event_kind="invoice", asset_id="bundle-ab",
                   amount={"value": "210000", "currency": "USD"}, dates={"invoice_date": "2026-01-01"},
                   temporal_basis={"kind": "invoice_date", "date": "2026-01-01"})
    cash_b.update(fact_id="cash-bundle", source_row="cash-bundle", asset_id="bundle-ab", parent_fact_id="invoice-bundle")
    cash_b["amount"]["value"] = "100000"
    package["financial_facts"].append(invoice)
    auth = {"source_fact_id": "cash-bundle", "allocation_group_id": "bundle-split-1", "method": "exact_weight", "method_version": "1",
            "authority_ref": "SV-8-CASH", "policy_ref": "SV-8-CASH", "scenario_id": package["manifest"]["scenario_id"],
            "effective": deepcopy(package["manifest"]["period"]),
            "weights": [{"asset_id": "picture-a", "weight": "0.4"}, {"asset_id": "picture-b", "weight": "0.6"}]}
    data["allocation_authorities"] = [auth]
    package["allocations"] = [{**{key: deepcopy(value) for key, value in auth.items() if key != "weights"},
                               "allocation_id": f"bundle-{target['asset_id']}",
                               "target_scope": {"agreement_id": "sv", "asset_ids": [target["asset_id"]]}, "weight": target["weight"]}
                              for target in auth["weights"]]
    recount(data)
    return data


class SkourasOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(SkourasOracleError) as raised:
            skouras(data)
        self.assertEqual(str(raised.exception), code)

    def test_neutral_fixture_preserves_original_package_not_bindings(self):
        data = fixture()
        original = json.loads((ROOT / "cases/sv/canonical-package.json").read_text(encoding="utf-8"))
        self.assertEqual(data["package"], original)
        self.assertNotIn("bindings", data)
        self.assertNotIn("pictures", data["package"]["parameters"])
        self.assertTrue(all("observed_at" not in row for row in data["package"]["financial_facts"]))

    def test_baseline_every_material_title_and_pool_intermediate(self):
        result = skouras(fixture())
        fields = ("cash", "participant_funding", "distributor_funding", "total_funding", "fee_rate", "fee", "allowed_cost", "basis", "share", "earned")
        self.assertEqual(tuple(result["titles"][0][key] for key in fields),
                         (100000, 0, 50000, 50000, Fraction(1, 4), 25000, 10000, 65000, Fraction(1, 5), 13000))
        self.assertEqual(tuple(result["titles"][1][key] for key in fields),
                         (60000, 40000, 60000, 100000, Fraction(3, 40), 4500, 5500, 50000, Fraction(2, 5), 20000))
        self.assertEqual(tuple(result["pool"][key] for key in ("opening_prepayment", "earned", "recovered", "payable", "closing_prepayment")),
                         (15000, 33000, 15000, 18000, 0))
        self.assertEqual(result["closing_state"]["state_key"], fixture()["package"]["state_cells"][0]["state_key"])
        self.assertEqual(result["closing_state"]["provenance_ref"], "synthetic-approved-opening")
        self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertNotIn("actual_paid", result)
        self.assertTrue(all("recovered" not in line for line in result["titles"]))

    def test_supplied_opening_variants_do_not_recompute_earned(self):
        for opening, payable, recovered, closing in (("0", 33000, 0, 0), ("12000", 21000, 12000, 0),
                                                     ("33000", 0, 33000, 0), ("40000", 0, 33000, 7000)):
            data = fixture(); data["package"]["state_cells"][0]["quantity"] = opening
            pool = skouras(data)["pool"]
            self.assertEqual((pool["earned"], pool["payable"], pool["recovered"], pool["closing_prepayment"]),
                             (33000, payable, recovered, closing))

    def test_equal_cash_control_preserves_funding_and_cost_methods(self):
        data = fixture(); data["package"]["financial_facts"][1]["amount"]["value"] = "100000"
        result = skouras(data)
        self.assertEqual((result["titles"][1]["fee"], result["titles"][1]["basis"], result["titles"][1]["earned"]), (7500, 87000, 34800))
        self.assertEqual((result["pool"]["earned"], result["pool"]["payable"]), (47800, 32800))

    def test_cash_date_boundaries_are_half_open(self):
        for day, included in (("2025-12-31", False), ("2026-01-01", True), ("2026-03-31", True), ("2026-04-01", False)):
            data = fixture(); package = data["package"]
            package["financial_facts"][0]["dates"]["cash_received_date"] = day
            package["financial_facts"][0]["temporal_basis"]["date"] = day
            # No A cost makes excluded cash an explicit zero-activity title.
            package["financial_facts"][2]["amount"]["value"] = "0"
            with self.subTest(day=day):
                result = skouras(data)
                self.assertEqual(result["titles"][0]["cash"], 100000 if included else 0)
                self.assertEqual(len(result["excluded_receipts"]), 0 if included else 1)
        data = fixture(); del data["package"]["financial_facts"][0]["dates"]["cash_received_date"]
        self.reject(data, "SV_CASH_DATE_REQUIRED")

    def test_incurred_dates_never_filled_from_posting_or_paid(self):
        data = fixture(); cost = data["package"]["financial_facts"][2]
        cost["dates"].update(incurred_date="2025-12-31", posting_date="2026-01-02", paid_date="2026-01-03")
        cost["temporal_basis"]["date"] = "2025-12-31"
        result = skouras(data)
        self.assertEqual((result["titles"][0]["allowed_cost"], result["titles"][0]["earned"], result["pool"]["payable"]), (0, 15000, 20000))
        del cost["dates"]["incurred_date"]
        original = deepcopy(data)
        self.reject(data, "SV_INCURRED_DATE_REQUIRED")
        self.assertEqual(data, original)
        data = fixture(); data["package"]["profile"] = "rq07-posting-date-v1"
        self.reject(data, "SV_SELECTED_PROFILE")
        data = fixture(); data["package"]["parameters"]["cost_date_basis"] = "posting_date"
        self.reject(data, "SV_INCURRED_POLICY_REQUIRED")

    def test_separate_reviewed_branch_eligibility_and_explicit_exclusion(self):
        data = fixture()
        package = data["package"]
        extra = deepcopy(package["financial_facts"][3])
        extra.update(fact_id="excluded-cost-b", source_row="excluded-cost-b", amount={"value": "2000", "currency": "USD"})
        package["financial_facts"].append(extra)
        package["parameters"]["cost_decisions"].append({"fact_id": "excluded-cost-b", "branch": "funded", "eligible": False,
                                                      "decision_id": "SV-8-COST-SCHEDULE", "reason": "Explicit unsupported synthetic cost"})
        recount(data)
        result = skouras(data)
        self.assertEqual(result["pool"]["payable"], 18000)
        excluded = next(row for row in result["cost_dispositions"] if row["fact_id"] == "excluded-cost-b")
        self.assertEqual((excluded["included"], excluded["amount"], excluded["reason"]), (False, 2000, "Explicit unsupported synthetic cost"))
        package["parameters"]["cost_decisions"][-1]["eligible"] = True
        self.assertEqual(skouras(data)["pool"]["payable"], 17200)
        # Such a changed supplied approval is another economic input, not
        # independent authority to change the original reviewed fixture.
        data = fixture(); data["package"]["parameters"]["cost_decisions"][0]["branch"] = "funded"
        self.reject(data, "SV_COST_BRANCH_AUTHORITY")
        data = fixture(); data["package"]["parameters"]["cost_decisions"].pop()
        self.reject(data, "SV_COST_DECISION_COVERAGE")

    def test_complete_funding_zero_is_explicit_and_later_funding_excluded(self):
        data = fixture(); package = data["package"]
        package["evidence_events"] = [row for row in package["evidence_events"] if row["asset_id"] != "picture-a"]
        self.assertEqual(skouras(data)["titles"][0]["branch"], "unfunded")
        package["parameters"]["funding_snapshot"]["complete"] = False
        self.reject(data, "SV_COMPLETE_FUNDING_SNAPSHOT_REQUIRED")
        data = fixture(); package = data["package"]
        later = deepcopy(package["evidence_events"][-1])
        later.update(event_id="later-b-distributor", amount={"value": "20000", "currency": "USD"}, effective_date="2026-02-01", observed_at="2026-02-02T00:00:00Z")
        package["evidence_events"].append(later)
        result = skouras(data)
        self.assertEqual((result["titles"][1]["share"], result["pool"]["payable"]), (Fraction(2, 5), 18000))
        self.assertEqual(result["excluded_funding"][0]["event_id"], "later-b-distributor")

    def test_funding_scope_value_authority_and_exact_cutoff(self):
        changes = [("SV_FUNDING_SCOPE", lambda p: p["evidence_events"][0].update(party_id="outside")),
                   ("SV_FUNDING_SCOPE", lambda p: p["evidence_events"][0].update(subject_ref="picture-b")),
                   ("SV_NONNEGATIVE_AMOUNT", lambda p: p["evidence_events"][0]["amount"].update(value="-1")),
                   ("SV_FUNDING_AUTHORITY", lambda p: p["evidence_events"][0].update(approval_ref="SV-8-CASH")),
                   ("SV_FUNDING_CUTOFF", lambda p: p["evidence_events"][0].update(observed_at=p["manifest"]["cutoff"])),
                   ("SV_COMPLETE_FUNDING_SNAPSHOT_REQUIRED", lambda p: p["parameters"]["funding_snapshot"].update(covered_assets=["picture-a"]))]
        for code, change in changes:
            data = fixture(); change(data["package"])
            with self.subTest(code=code):
                self.reject(data, code)
        data = fixture(); data["package"]["manifest"]["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        data["package"]["evidence_events"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        self.assertEqual(skouras(data)["pool"]["payable"], 18000)

    def test_original_parent_allocation_is_counted_once_not_as_invoice(self):
        data = bundle_fixture()
        result = skouras(data)
        self.assertEqual([row["cash"] for row in result["titles"]], [100000, 60000])
        self.assertEqual(result["pool"]["payable"], 18000)
        self.assertEqual(sum(row["amount"] for row in result["receipt_contributions"]), 160000)
        self.assertEqual((result["allocation_controls"][0]["source_amount"], result["allocation_controls"][0]["allocated_amount"]), (100000, 100000))
        lines = [row for row in result["receipt_contributions"] if row["allocation_id"]]
        self.assertTrue(all(row["source_fact_id"] == "cash-bundle" and row["parent_fact_id"] == "invoice-bundle" for row in lines))
        data["package"]["financial_facts"][-1]["amount"]["value"] = "999999"
        self.assertEqual(skouras(data)["pool"]["payable"], 18000)

    def test_conserved_unauthorized_allocation_and_bad_groups_fail(self):
        data = bundle_fixture()
        for row in data["package"]["allocations"]:
            row["weight"] = "0.5"
        self.reject(data, "SV_ALLOCATION_UNAUTHORIZED_WEIGHT")
        data = bundle_fixture(); data["package"]["allocations"][0]["allocation_group_id"] = "alternative"
        self.reject(data, "SV_ALLOCATION_UNAUTHORIZED_VARIANT")
        data = bundle_fixture(); data["package"]["allocations"].pop()
        self.reject(data, "SV_ALLOCATION_CONSERVATION")
        data = bundle_fixture(); data["allocation_authorities"] = []
        self.reject(data, "SV_ALLOCATION_AUTHORITY_REQUIRED")
        data = bundle_fixture(); data["allocation_authorities"][0]["weights"][0]["weight"] = "0.5"
        self.reject(data, "SV_ALLOCATION_AUTHORITY_CONSERVATION")
        data = bundle_fixture(); data["package"]["allocations"][0]["target_scope"]["agreement_id"] = "outside"
        self.reject(data, "SV_ALLOCATION_TARGET")

    def test_duplicate_and_overlapping_original_cash_views_fail(self):
        for field, identity in (("financial_facts", "fact_id"), ("evidence_events", "event_id"), ("mappings", "mapping_id"), ("state_cells", "state_key")):
            data = fixture(); data["package"][field].append(deepcopy(data["package"][field][0]))
            with self.subTest(field=field):
                self.reject(data, "SV_DUPLICATE_ID")
        data = fixture(); package = data["package"]
        clone = deepcopy(package["financial_facts"][0]); clone["fact_id"] = "renamed-copy"
        package["financial_facts"].append(clone); recount(data)
        self.reject(data, "SV_DUPLICATE_SOURCE_VIEW")
        data = fixture(); package = data["package"]
        package["financial_facts"][0]["external_event_ref"] = "same-cash"
        package["financial_facts"][1]["external_event_ref"] = "same-cash"
        self.reject(data, "SV_DUPLICATE_CASH_EVENT")
        data = fixture(); data["package"]["financial_facts"][1]["parent_fact_id"] = "receipt-a"
        self.reject(data, "SV_OVERLAPPING_CASH_VIEWS")
        data = bundle_fixture(); data["package"]["financial_facts"][-1]["parent_fact_id"] = "cash-bundle"
        self.reject(data, "SV_PARENT_REFERENCE_OR_CYCLE")

    def test_opening_full_scope_provenance_and_recovery_authority(self):
        for key, value in (("agreement_id", "other"), ("participant_id", "other"), ("pool_id", "other"),
                           ("scenario_id", "other"), ("unit", "EUR"), ("balance_kind", "reserve"), ("boundary", "2026-04-01")):
            data = fixture(); data["package"]["state_cells"][0][key] = value
            self.reject(data, "SV_OPENING_SCOPE")
        data = fixture(); data["package"]["state_cells"][0]["quantity"] = "-1"
        self.reject(data, "SV_NONNEGATIVE_OPENING")
        data = fixture(); data["package"]["state_cells"][0]["provenance_ref"] = "missing"
        self.reject(data, "SV_OPENING_AUTHORITY")
        data = fixture(); data["package"]["state_cells"][0]["policy_lineage"] = []
        self.reject(data, "SV_OPENING_AUTHORITY")

    def test_pool_membership_roles_and_decision_scope(self):
        data = fixture(); data["package"]["mappings"][0]["purpose"] = "reserve"
        self.reject(data, "SV_POOL_MEMBERSHIP")
        data = fixture(); data["package"]["roles"][1]["party_id"] = "skouras"
        self.reject(data, "SV_ROLE_SCOPE")
        data = fixture(); data["package"]["interpretations"][0]["decisions"][0]["scope"]["pool_id"] = "outside"
        self.reject(data, "SV_AUTHORITY_SCOPE")
        data = fixture(); data["package"]["interpretations"][0]["decisions"].pop()
        self.reject(data, "SV_AUTHORITY_REQUIRED")

    def test_source_batch_controls_and_original_temporal_basis(self):
        data = fixture(); data["package"]["source_batches"][0]["row_count"] = 3
        self.reject(data, "SV_SOURCE_BATCH_COUNT")
        data = fixture(); batch = data["package"]["source_batches"][0]
        batch["control_totals"] = [{"amount_kind": "cash_receipt", "currency": "USD", "signed_total": "160000", "absolute_total": "160000"}]
        self.assertEqual(skouras(data)["pool"]["payable"], 18000)
        batch["control_totals"][0]["signed_total"] = "160001"
        self.reject(data, "SV_SOURCE_CONTROL_TOTAL")
        data = fixture(); data["package"]["financial_facts"][0]["temporal_basis"]["date"] = "2026-01-02"
        self.reject(data, "SV_TEMPORAL_BASIS")

    def test_exact_fraction_transport_and_no_implicit_rounding(self):
        data = fixture(); package = data["package"]
        package["financial_facts"][0]["amount"]["value"] = {"numerator": "1000001", "denominator": "10"}
        result = skouras(data)
        self.assertEqual(result["titles"][0]["fee"], Fraction(1000001, 40))
        self.assertEqual(result["pool"]["payable"], Fraction("18000.015"))
        for value in (0.1, "1e5", {"numerator": "2", "denominator": "4"}):
            data = fixture(); data["package"]["financial_facts"][0]["amount"]["value"] = value
            self.reject(data, "SV_REDUCED_FRACTION_REQUIRED" if type(value) is dict else "SV_EXACT_VALUE_REQUIRED")

    def test_zero_activity_permutation_and_deterministic_original_replay(self):
        data = fixture(); expected = skouras(data)
        before = deepcopy(data)
        self.assertEqual(skouras(data), expected)
        self.assertEqual(data, before)
        for field in ("assets", "roles", "mappings", "evidence_events", "financial_facts", "parameters"):
            if type(data["package"][field]) is list:
                data["package"][field].reverse()
        self.assertEqual(skouras(data), expected)
        data = fixture(); data["package"]["financial_facts"] = []
        data["package"]["parameters"]["cost_decisions"] = []; recount(data)
        result = skouras(data)
        self.assertEqual([row["earned"] for row in result["titles"]], [0, 0])
        self.assertEqual((result["pool"]["payable"], result["pool"]["closing_prepayment"]), (0, 15000))
        data = fixture(); data["package"]["financial_facts"][0]["amount"]["value"] = "0"
        self.reject(data, "SV_NEGATIVE_EARNINGS_OUTSIDE_PROFILE")

    def test_standard_library_only_oracle_imports(self):
        tree = ast.parse((ROOT / "oracles/skouras.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
