"""Financial relationship checks at the bounded physical package boundary."""
from fractions import Fraction
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from spl_compiler.adapter import rq07
from spl_compiler.codecs import amount
from spl_compiler.fixtures import add_fact, authored_batch, sv_package
from spl_compiler.run import bind_package, project, run_package
from spl_compiler.schema import validate_package


ROOT = Path(__file__).resolve().parents[1]
SV = ROOT / "cases/sv/sv01.spl"
RQ07 = ROOT / "cases/sv/rq07.spl"


def split_package():
    package = sv_package(opening="0", cash_a="90", cash_b="60", cost_a="0", cost_b="0")
    period = package["manifest"]["period"]
    assets = package["agreements"][0]["asset_ids"]
    for asset in ("picture-c", "picture-empty"):
        assets.append(asset)
        package["assets"].append({"asset_id": asset, "kind": "picture"})
        package["mappings"].append({
            **package["mappings"][0],
            "mapping_id": "member-" + asset,
            "source_code": asset,
            "target_ref": asset,
        })
    package["parameters"]["funding_snapshot"]["covered_assets"] = assets[:]
    add_fact(package, "invoice-face", "picture-a", "1000", "invoice", "invoice_date", period["start"])

    # Two original cash applications may have the same separate invoice parent.
    # Each cash amount is allocated independently across three authorized titles.
    decision = package["interpretations"][0]["decisions"][0]
    decision["allocation_terms"] = [
        {"asset_id": asset, "weight": weight}
        for asset, weight in zip(assets, ["0.2", "0.3", "0.5"])
    ]
    for parent in package["financial_facts"][:2]:
        parent["parent_fact_id"] = "invoice-face"
        parent_id = parent["fact_id"]
        for term in decision["allocation_terms"]:
            asset, weight = term["asset_id"], term["weight"]
            package["allocations"].append({
                "allocation_id": parent_id + "/" + asset,
                "allocation_group_id": "allocation-" + parent_id,
                "source_fact_id": parent_id,
                "target_scope": {"agreement_id": "sv", "asset_ids": [asset]},
                "method": "exact_weight",
                "method_version": "1",
                "authority_ref": "SV-8-CASH",
                "policy_ref": "SV-8-CASH",
                "scenario_id": "SV-01",
                "effective": period,
                "weight": weight,
            })
    package["source_batches"].clear()
    authored_batch(package)
    return package


class PhysicalRelationshipTests(TestCase):
    def assert_pre_source_block(self, package, code, pointer, schedule=SV):
        bound = bind_package(package, schedule)
        # Relationship invalidity is a canonical input error, before SPL assertion
        # evaluation or projection.
        with patch("spl_compiler.run.project", side_effect=AssertionError("unvalidated projection")):
            result = run_package(bound, schedule, backend="reference")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["statements"], [])
        self.assertEqual(result["detail"], [])
        self.assertEqual(result["closing_state"], [])
        self.assertNotIn("semantic_run_digest", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result["diagnostics"])
        self.assertEqual(result["diagnostics"][0]["pointer"], pointer)

    def test_two_original_cash_parents_three_targets_each_and_an_empty_title(self):
        package = bind_package(split_package(), SV)
        inputs, _, lineage, dispositions = project(validate_package(package))
        self.assertEqual(
            {row["fact_id"]: amount(row["amount"]) for row in inputs["receipts"]},
            {"receipt-a/picture-a": 18, "receipt-a/picture-b": 27, "receipt-a/picture-c": 45,
             "receipt-b/picture-a": 12, "receipt-b/picture-b": 18, "receipt-b/picture-c": 30},
        )
        allocated = [row for row in lineage if "allocation_id" in row]
        self.assertEqual(len(allocated), len(inputs["receipts"]))
        self.assertEqual(
            {row["view_id"]: row["fact_ids"] for row in allocated},
            {row["fact_id"]: [row["fact_id"].split("/")[0]] for row in inputs["receipts"]},
        )
        self.assertEqual(
            {row["fact_id"]: row["disposition"] for row in dispositions if row["measure"] == "cash_receipts"},
            {"receipt-a": "included", "receipt-b": "included", "invoice-face": "excluded"},
        )
        result = run_package(package, SV, backend="compare")
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertTrue(result["verification"]["reference_agrees"])
        self.assertEqual({row["asset_id"]: Fraction(row["cash"]) for row in result["detail"]},
                         {"picture-a": 30, "picture-b": 45, "picture-c": 75, "picture-empty": 0})
        self.assertEqual(Fraction(result["statements"][0]["earned"]), Fraction("32.4"))
        self.assertEqual(Fraction(result["statements"][0]["payable"]), Fraction("32.4"))

    def test_missing_parent_and_cash_ancestor_block_without_changing_money(self):
        for parent, code in [("absent", "UNRESOLVED_REFERENCE"), ("receipt-a", "OVERLAPPING_CASH_VIEWS")]:
            with self.subTest(parent=parent):
                package = split_package()
                package["financial_facts"][1]["parent_fact_id"] = parent
                self.assert_pre_source_block(package, code, "/financial_facts/1/parent_fact_id")

    def test_dangling_ancestor_and_cycle_are_package_errors(self):
        package = split_package()
        package["financial_facts"][-1]["parent_fact_id"] = "missing"
        self.assert_pre_source_block(package, "UNRESOLVED_REFERENCE", "/financial_facts/4/parent_fact_id")

        package = split_package()
        package["financial_facts"][-1]["parent_fact_id"] = "receipt-a"
        self.assert_pre_source_block(package, "CYCLIC_REFERENCE", "/financial_facts/0/parent_fact_id")

    def test_duplicate_original_id_and_duplicate_physical_row_are_distinct(self):
        package = split_package()
        package["financial_facts"][1]["fact_id"] = "receipt-a"
        self.assert_pre_source_block(package, "DUPLICATE_ID", "")

        package = split_package()
        package["financial_facts"][1]["source_row"] = "receipt-a"
        self.assert_pre_source_block(package, "DUPLICATE_SOURCE_ROW", "/financial_facts/1/source_row")

    def test_allocation_parent_and_projected_identity_must_resolve_in_right_space(self):
        for parent in ("absent", "invoice-face", "cost-a"):
            with self.subTest(parent=parent):
                package = split_package()
                package["allocations"][0]["source_fact_id"] = parent
                self.assert_pre_source_block(package, "ALLOCATION_AUTHORITY", "/allocations/0")

        package = split_package()
        package["allocations"][0]["allocation_id"] = "receipt-b"
        self.assert_pre_source_block(package, "ALLOCATION_ID_COLLISION", "/allocations/0/allocation_id")

    def test_missing_or_repeated_recipient_and_wrong_scope_block(self):
        for target in ({"asset_ids": ["unknown"]}, {"asset_ids": []}, {"asset_ids": ["picture-a", "picture-b"]},
                       {"participant_id": "distributor"}, {"pool_id": "other-pool"}):
            with self.subTest(target=target):
                package = split_package()
                package["allocations"][0]["target_scope"].update(target)
                self.assert_pre_source_block(package, "ALLOCATION_SCOPE", "/allocations/0/target_scope")

        # Equal total weight survives this mutation, so conservation alone is
        # insufficient to prove a unique assignment to each recipient.
        package = split_package()
        package["allocations"][1]["target_scope"]["asset_ids"] = ["picture-a"]
        self.assert_pre_source_block(package, "DUPLICATE_ALLOCATION_TARGET", "")

        package = split_package()
        package["interpretations"][0]["decisions"][0]["scope"]["asset_ids"] = ["picture-a"]
        self.assert_pre_source_block(package, "ALLOCATION_SCOPE", "/allocations/1/authority_ref")

    def test_duplicate_cost_policy_and_policy_against_wrong_measure_block(self):
        package = split_package()
        package["parameters"]["cost_decisions"].append(package["parameters"]["cost_decisions"][0].copy())
        self.assert_pre_source_block(package, "DUPLICATE_ID", "")

        package = split_package()
        package["parameters"]["cost_decisions"][0]["fact_id"] = "receipt-a"
        self.assert_pre_source_block(package, "REQUIRED_COST_POLICY", "/parameters/cost_decisions/0/fact_id")

    def test_repeated_distributor_membership_and_aliased_funding_row_block(self):
        package = split_package()
        package["agreements"][0]["role_ids"].append("distributor-role")
        self.assert_pre_source_block(package, "ROLE_SCOPE", "")

        package = split_package()
        batch = package["financial_facts"][0]["batch_ref"]
        first = package["evidence_events"][0]
        first.update(batch_ref=batch, source_row="funding-row")
        package["evidence_events"].append({**first, "event_id": "aliased-funding"})
        self.assert_pre_source_block(package, "DUPLICATE_SOURCE_ROW", "/evidence_events/3/source_row")

    def test_original_rq07_applications_keep_bank_invoice_and_cash_totals_separate(self):
        source = ROOT / "cases/rq07/source"
        package = bind_package(rq07(source, observed_at="2026-03-30T00:00:00Z",
                                    ingested_at="2026-04-03T00:00:00Z"), RQ07)
        inputs, _, lineage, dispositions = project(validate_package(package))
        self.assertEqual(sum(amount(row["amount"]) for row in inputs["receipts"]), 160000)
        self.assertEqual(sum(amount(row["amount"]) for row in package["financial_facts"]
                             if row["event_kind"] == "invoice"), 210000)
        cash_parents = {row["fact_id"]: row["parent_fact_id"] for row in package["financial_facts"]
                        if row["event_kind"] == "cash_receipt"}
        self.assertEqual(cash_parents, {"receipt/APP-01": "invoice/INV-A:1", "application/APP-02": "invoice/INV-AB:1"})
        self.assertEqual({row["view_id"]: row["fact_ids"] for row in lineage if "APP-" in row["view_id"]},
                         {"receipt/APP-01": ["receipt/APP-01"],
                          "application/APP-02/PIC-A": ["application/APP-02"],
                          "application/APP-02/PIC-B": ["application/APP-02"]})
        self.assertEqual({row["fact_id"] for row in dispositions if row["disposition"] == "excluded"
                          and row["measure"] == "cash_receipts"}, set(cash_parents.values()))

    def test_rq07_canonical_application_scope_and_per_invoice_reconciliation(self):
        def original():
            return rq07(ROOT / "cases/rq07/source", observed_at="2026-03-30T00:00:00Z",
                        ingested_at="2026-04-03T00:00:00Z")

        package = original()
        package["financial_facts"][2].pop("parent_fact_id")
        self.assert_pre_source_block(package, "INVOICE_APPLICATION_SCOPE", "/financial_facts/2/parent_fact_id", RQ07)

        package = original()
        package["financial_facts"][2]["parent_fact_id"] = "invoice/INV-AB:1"
        self.assert_pre_source_block(package, "INVOICE_APPLICATION_SCOPE", "/financial_facts/2/parent_fact_id", RQ07)

        package = original()
        # Bank, application and invoice-face grand totals all stay equal to
        # their original controls, but APP-02 exceeds its own invoice face.
        package["financial_facts"][2]["amount"]["value"] = "59999"
        package["financial_facts"][3]["amount"]["value"] = "100001"
        self.assert_pre_source_block(package, "OVERAPPLICATION", "/financial_facts/1/amount", RQ07)
