"""Independent handoff expectations, compared with observable compiler results.

All expected amounts here are authored constants from SV-01/SV-02/LG-01. They
are not produced by the evaluator, emitter, adapter, or fixture constructors.
"""
from copy import deepcopy
from pathlib import Path
import unittest

from spl_compiler.codecs import DataError, canonical, digest, loads
from spl_compiler.fixtures import add_fact, lg_package, sv_package
from spl_compiler.run import bind_package, carry_state, run_package


ROOT = Path(__file__).resolve().parents[1]
SV = ROOT / "cases/sv/sv01.spl"
LG = ROOT / "cases/lg/lg01.spl"


class AcceptanceTests(unittest.TestCase):
    def execute(self, package, schedule=SV, *, backend="reference"):
        return run_package(bind_package(package, schedule), schedule, backend=backend)

    def assert_success(self, result, *, earned, payable, recouped=None, closing=None):
        self.assertIn(result["status"], {"calculated", "calculated_zero"}, result["diagnostics"])
        self.assertFalse(result["diagnostics"])
        statement = result["statements"][0]
        self.assertEqual(earned, statement["earned"])
        self.assertEqual(payable, statement["payable"])
        if recouped is not None:
            self.assertEqual(recouped, statement["recouped"])
        if closing is not None:
            self.assertEqual([closing], [c["quantity"] for c in result["closing_state"]])
        self.assertEqual("no_event_supplied", result["payment_evidence_status"])
        self.assertEqual("unissued", result["issuance_status"])
        return statement

    def assert_blocked(self, result, code=None):
        self.assertEqual("blocked", result["status"])
        self.assertEqual([], result["statements"])
        self.assertEqual([], result["closing_state"])
        self.assertTrue(result["diagnostics"])
        if code:
            self.assertIn(code, [d["code"] for d in result["diagnostics"]])

    def test_sv01_native_lean_matches_independent_title_and_pool_expectations(self):
        result = self.execute(sv_package(), backend="compare")
        self.assert_success(result, earned="33000", recouped="15000", payable="18000", closing="0")
        self.assertTrue(result["verification"]["reference_agrees"])
        actual = {line["asset_id"]: {k: line[k] for k in ("cash", "fee", "allowed_cost", "basis", "share", "earned")}
                  for line in result["detail"]}
        self.assertEqual({
            "picture-a": {"cash": "100000", "fee": "25000", "allowed_cost": "10000", "basis": "65000", "share": "0.2", "earned": "13000"},
            "picture-b": {"cash": "60000", "fee": "4500", "allowed_cost": "5500", "basis": "50000", "share": "0.4", "earned": "20000"},
        }, actual)
        # Pool recovery has no invented allocation to the title detail.
        self.assertTrue(all("recouped" not in title for title in result["detail"]))

    def test_sv_zero_opening_and_zero_activity_are_present_results(self):
        self.assert_success(self.execute(sv_package(opening="0")), earned="33000", recouped="0", payable="33000", closing="0")
        result = self.execute(sv_package(cash_a="0", cash_b="0", cost_a="0", cost_b="0"))
        self.assert_success(result, earned="0", recouped="0", payable="0", closing="15000")
        self.assertEqual("calculated_zero", result["status"])
        self.assertEqual(2, len(result["detail"]))

    def test_sv02_three_serialized_periods_use_linked_state(self):
        first = self.execute(sv_package(opening="40000", scenario="SV-02"), backend="compare")
        self.assert_success(first, earned="33000", recouped="33000", payable="0", closing="7000")
        second_input = sv_package(cash_a="0", cash_b="20000", cost_a="0", cost_b="6000",
                                  start="2026-04-01", end="2026-07-01", scenario="SV-02")
        second_input["state_cells"] = loads(canonical(carry_state(first)))
        second = self.execute(second_input, backend="compare")
        self.assert_success(second, earned="5000", recouped="5000", payable="0", closing="2000")
        self.assertTrue(second_input["state_cells"][0]["prior_result_ref"].endswith(first["semantic_run_digest"]))
        third_input = sv_package(cash_a="0", cash_b="40000", cost_a="0", cost_b="12000",
                                 start="2026-07-01", end="2026-10-01", scenario="SV-02")
        third_input["state_cells"] = loads(canonical(carry_state(second)))
        third = self.execute(third_input, backend="compare")
        self.assert_success(third, earned="10000", recouped="2000", payable="8000", closing="0")

    def test_sv_missing_funding_and_negative_earnings_block_atomic_pool(self):
        missing = sv_package()
        missing["parameters"].pop("funding_snapshot")
        self.assert_blocked(self.execute(missing))
        self.assert_blocked(self.execute(sv_package(cash_a="0", cost_a="1")), "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT")

    def test_sv_period_is_half_open_and_date_kind_is_not_inferred(self):
        package = sv_package(cost_a="0", cost_b="0")
        for fact in package["financial_facts"]:
            if fact["fact_id"] == "receipt-a":
                fact["temporal_basis"]["date"] = "2026-04-01"
                fact["dates"]["cash_received_date"] = "2026-04-01"
        result = self.execute(package)
        # Only B contributes: 60000 - 4500 fee = 55500; 40% is 22200.
        self.assert_success(result, earned="22200", recouped="15000", payable="7200", closing="0")
        missing = sv_package()
        fact = next(f for f in missing["financial_facts"] if f["fact_id"] == "cost-a")
        fact["temporal_basis"] = {"kind": "posting_date", "date": "2026-01-01"}
        fact["dates"] = {"posting_date": "2026-01-01"}
        self.assert_blocked(self.execute(missing))

    def test_run_identity_and_input_order_do_not_change_semantic_digest(self):
        original = sv_package()
        first = self.execute(original)
        changed = deepcopy(original)
        changed["manifest"]["run_id"] = "same-economics-new-invocation"
        changed["financial_facts"].reverse()
        changed["evidence_events"].reverse()
        changed["state_cells"].reverse()
        second = self.execute(changed)
        self.assert_success(second, earned="33000", recouped="15000", payable="18000", closing="0")
        self.assertEqual(first["semantic_run_digest"], second["semantic_run_digest"])
        self.assertEqual(first["trace"], second["trace"])
        self.assertEqual(first["evidence_to_target_lineage"], second["evidence_to_target_lineage"])

    def test_lg01_native_lean_matches_independent_gates_and_candidates(self):
        result = self.execute(lg_package(), LG, backend="compare")
        self.assert_success(result, earned="35", payable="35")
        comparison = result["detail"][0]
        for key, expected in {"cash_measure": "300", "payout_base": "210", "gross_candidate": "30", "net_candidate": "35", "selected_label": "net"}.items():
            self.assertEqual(expected, comparison[key], key)
        self.assertEqual({row["target_input"]: row["evidence_ids"] for row in result["evidence_to_target_lineage"]},
                         {"outside_hurdle": ["outside-hurdle"], "work_gate_history": ["work-history"],
                          "crossed_net_subtotal": ["net-worksheet"]})
        cells = {cell["balance_kind"]: cell["quantity"] for cell in result["closing_state"]}
        self.assertEqual({"cumulative_gross": "400", "cumulative_cost": "100", "synthetic_payment_holdback": "0"}, cells)

    def test_lg_gross_winner_and_observable_tie(self):
        for subtotal, label, net in [("100", "gross", "20"), ("150", "tie", "30")]:
            with self.subTest(subtotal=subtotal):
                result = self.execute(lg_package(subtotal=subtotal), LG)
                self.assert_success(result, earned="30", payable="30")
                self.assertEqual(label, result["detail"][0]["selected_label"])
                self.assertEqual(net, result["detail"][0]["net_candidate"])

    def test_lg_hurdle_must_be_strictly_before_period_start(self):
        for date in ("2026-01-01", "2026-01-02"):
            with self.subTest(date=date):
                result = self.execute(lg_package(hurdle_date=date), LG, backend="compare" if date == "2026-01-01" else "reference")
                self.assert_blocked(result, "LG_HURDLE_TIMING_POLICY_REQUIRED")

    def test_lg_missing_false_wrong_scope_or_incomplete_history_blocks(self):
        for kind, change in [
            ("hurdle_attestation", "missing"), ("hurdle_attestation", "false"),
            ("hurdle_attestation", "wrong_agreement"),
            ("gate_history", "missing"), ("gate_history", "false"),
            ("gate_history", "wrong_asset"), ("gate_history", "wrong_period"),
            ("crossed_net_worksheet", "missing"), ("crossed_net_worksheet", "wrong_pool")]:
            with self.subTest(kind=kind, change=change):
                package = lg_package()
                event = next(e for e in package["evidence_events"] if e["kind"] == kind)
                if change == "missing":
                    package["evidence_events"].remove(event)
                elif change == "false":
                    event["satisfied"] = False
                elif change == "wrong_agreement":
                    event["agreement_id"] = "unrelated-agreement"
                elif change == "wrong_asset":
                    event["asset_id"] = "unrelated-work"
                elif change == "wrong_period":
                    event["period"] = {"start": "2026-01-01", "end": "2026-03-01"}
                elif change == "wrong_pool":
                    event["pool_id"] = "unrelated-pool"
                self.assert_blocked(self.execute(package, LG))

    def test_preview_is_not_consumable_successor_state(self):
        package = sv_package()
        package["manifest"]["mode"] = "preview"
        result = self.execute(package)
        self.assertEqual("provisional", result["status"])
        self.assertEqual([], result["closing_state"])
        with self.assertRaises(DataError):
            carry_state(result)

    def test_conditional_fields_evidence_and_policy_state_scopes_are_required(self):
        cases = [
            ("funding amount", sv_package, SV, lambda p: p["evidence_events"][0].pop("amount")),
            ("funding party", sv_package, SV, lambda p: p["evidence_events"][0].pop("party_id")),
            ("funding asset", sv_package, SV, lambda p: p["evidence_events"][0].pop("asset_id")),
            ("LG video proxy", lg_package, LG, lambda p: p["parameters"]["policy"].pop("video_proxy")),
            ("LG gross rate", lg_package, LG, lambda p: p["parameters"]["policy"].pop("gross_rate")),
            ("LG net rate", lg_package, LG, lambda p: p["parameters"]["policy"].pop("net_rate")),
            ("LG fee offset", lg_package, LG, lambda p: p["parameters"].pop("producer_fee_offset")),
            ("LG hold addition", lg_package, LG, lambda p: p["parameters"].pop("payment_holdback_addition")),
            ("LG hold release", lg_package, LG, lambda p: p["parameters"].pop("payment_holdback_release")),
            ("snapshot dangling evidence", sv_package, SV, lambda p: p["parameters"]["funding_snapshot"].update(evidence_ref="DOES-NOT-EXIST")),
            ("funding conflicting subject", sv_package, SV, lambda p: p["evidence_events"][0].update(subject_ref="unrelated-picture")),
            ("LG conflicting subject", lg_package, LG, lambda p: p["evidence_events"][0].update(subject_ref="unrelated-agreement")),
            ("wrong state purpose", sv_package, SV, lambda p: p["state_cells"][0].update(balance_kind="cumulative_cost")),
            ("decision expires within period", sv_package, SV,
             lambda p: p["interpretations"][0]["decisions"][0].update(effective={"start": "2026-01-01", "end": "2026-03-01"})),
        ]
        for label, builder, schedule, change in cases:
            with self.subTest(label=label):
                package = builder()
                change(package)
                # Missing conditional values must be diagnostics, not KeyError.
                self.assert_blocked(self.execute(package, schedule))

    def test_conserved_allocation_must_still_match_pinned_authority(self):
        package = sv_package()
        decision = next(d for d in package["interpretations"][0]["decisions"] if d["decision_id"] == "SV-8-CASH")
        decision["allocation_terms"] = [{"asset_id": "picture-a", "weight": "0.5"},
                                          {"asset_id": "picture-b", "weight": "0.5"}]
        package["allocations"] = [
            {"allocation_id": "test-bundle-" + asset, "allocation_group_id": "test-complete-bundle",
             "source_fact_id": "receipt-a", "target_scope": {"agreement_id": "sv", "pool_id": "pool-1", "asset_ids": [asset]},
             "method": "synthetic-authorized-weights", "method_version": "1", "authority_ref": "SV-8-CASH",
             "policy_ref": "SV-8-CASH", "scenario_id": "SV-01", "effective": package["manifest"]["period"], "weight": "0.5"}
            for asset in ("picture-a", "picture-b")]
        approved = self.execute(package)
        self.assert_success(approved, earned="44000", recouped="15000", payable="29000", closing="0")
        package["allocations"][0]["weight"] = "0.4"
        package["allocations"][1]["weight"] = "0.6"
        self.assert_blocked(self.execute(package), "ALLOCATION_AUTHORITY")

    def test_excluded_logical_source_fact_changes_semantic_dependency_identity(self):
        first_package = sv_package()
        add_fact(first_package, "excluded-invoice", "picture-a", "100", "invoice", "invoice_date", "2026-01-01")
        batch = first_package["source_batches"][0]
        batch.update(row_count=len(first_package["financial_facts"]), sha256=digest(first_package["financial_facts"]))
        first = self.execute(first_package)
        self.assert_success(first, earned="33000", recouped="15000", payable="18000", closing="0")
        changed = deepcopy(first_package)
        next(f for f in changed["financial_facts"] if f["fact_id"] == "excluded-invoice")["amount"]["value"] = "200"
        changed["source_batches"][0]["sha256"] = digest(changed["financial_facts"])
        second = self.execute(changed)
        self.assert_success(second, earned="33000", recouped="15000", payable="18000", closing="0")
        self.assertNotEqual(first["semantic_run_digest"], second["semantic_run_digest"])


if __name__ == "__main__":
    unittest.main()
