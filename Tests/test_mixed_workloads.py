"""Mixed original-record counts, independent controls and scale admission."""
import ast
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from oracles.skouras import SkourasOracleError, skouras
from scripts.spl_mixed_benchmark import (check_prerequisite, check_projection, check_target, target_expected,
                                         equal_wire_files, reference_worker, check_reference_worker, audit_head,
                                         sequential_dependency_plan, implementation_spec, dependency_files, TARGET_GENERATION)
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import DataError, money, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.parser import parse
from spl_compiler.run import bind_package, project
from spl_compiler.schema import validate_package
from validation.mixed_workloads import canonical_bytes, generate_mixed


class MixedWorkloadTests(unittest.TestCase):
    def prepared(self):
        workload = generate_mixed()
        oracle = skouras(workload["neutral"])
        bound = bind_package(workload["neutral"]["package"], ROOT / "cases/sv/sv01.spl")
        validate_package(bound)
        inputs, aliases, lineage, dispositions = project(bound)
        openings = {"prepayment": aliases["sv/participant-prepayment/main-pool"]}
        return workload, oracle, inputs, openings, lineage, dispositions

    def test_exact_100_original_mix_separate_amount_spaces_and_invoice_links(self):
        workload = generate_mixed()
        counts, package = workload["counts"], workload["neutral"]["package"]
        self.assertEqual([counts[key] for key in ("receipt_parents", "cost_facts", "funding_evidence_events", "invoice_lineage_facts")], [60, 30, 5, 5])
        self.assertEqual([counts[key] for key in ("financial_facts", "canonical_guard_objects", "allocation_rows", "projected_receipt_cardinality", "projected_eligible_cost_cardinality")], [95, 100, 12, 66, 24])
        facts = {row["fact_id"]: row for row in package["financial_facts"]}
        self.assertEqual(len(facts), 95)
        linked = [row for row in facts.values() if "parent_fact_id" in row]
        self.assertEqual(len(linked), 5)
        self.assertTrue(all(row["event_kind"] == "cash_receipt" and facts[row["parent_fact_id"]]["event_kind"] == "invoice" for row in linked))
        self.assertEqual(len({row["parent_fact_id"] for row in linked}), 5)
        batch = package["source_batches"][0]
        self.assertEqual(batch["row_count"], 95)
        self.assertEqual(batch["sha256"], hashlib.sha256(canonical_bytes(package["financial_facts"])).hexdigest())
        controls = {row["amount_kind"]: row["signed_total"] for row in batch["control_totals"]}
        self.assertEqual(controls, {"cash_receipt": "6174", "incurred_cost": "60", "invoice": "760"})
        self.assertTrue(all("observed_at" not in row for row in facts.values()))
        self.assertEqual(package["adapter"]["source_digest"], hashlib.sha256(canonical_bytes(workload["source_records"])).hexdigest())

    def test_prior_100_1000_generator_bytes_remain_unchanged(self):
        expected = {100: "7b55e2cc1707f3b2346707d3c4d0aef4eb9718adbbc6d6e914e3903fc86adc7c",
                    1000: "46a884542a1275dd5de0db03a42f39322ffac6d179be99fd978d2b1804f83948"}
        for count, sha in expected.items():
            self.assertEqual(hashlib.sha256(canonical_bytes(generate_mixed(count))).hexdigest(), sha)

    def test_10000_original_four_way_fanout_and_independent_material_controls(self):
        workload = generate_mixed(10000)
        counts = workload["counts"]
        expected = {"raw_original_records": 10000, "receipt_parents": 6000, "cost_facts": 3000,
                    "funding_evidence_events": 500, "invoice_lineage_facts": 500, "financial_facts": 9500,
                    "canonical_guard_objects": 10000, "source_batch_rows": 9500, "allocation_parent_groups": 600,
                    "allocation_rows": 2400, "independent_allocation_authorities": 600, "projected_receipt_cardinality": 7800,
                    "projected_eligible_cost_cardinality": 2400, "explicitly_excluded_costs": 600,
                    "picture_metadata": 40, "pool_membership_mappings": 40}
        for key, value in expected.items():
            self.assertEqual(counts[key], value, key)
        package = workload["neutral"]["package"]
        groups = Counter(row["source_fact_id"] for row in package["allocations"])
        self.assertEqual(set(groups.values()), {4})
        self.assertEqual(len(groups), 600)
        for authority in workload["neutral"]["allocation_authorities"]:
            self.assertEqual([row["weight"] for row in authority["weights"]], ["0.1", "0.2", "0.3", "0.4"])
            self.assertEqual(sum(Fraction(row["weight"]) for row in authority["weights"]), 1)
            self.assertEqual(len({row["asset_id"] for row in authority["weights"]}), 4)
        # Original-fact oracle precedes canonical projection; no projected
        # financial answers are supplied to the oracle or source generator.
        oracle = skouras(workload["neutral"])
        bound = bind_package(package, ROOT / "cases/sv/sv01.spl")
        validate_package(bound)
        inputs, aliases, lineage, dispositions = project(bound)
        result = check_projection(workload, oracle, inputs,
                                  {"prepayment": aliases["sv/participant-prepayment/main-pool"]}, lineage, dispositions)
        self.assertEqual(result["projected_receipts"], 7800)
        self.assertEqual(result["projected_eligible_costs"], 2400)
        self.assertEqual(result["verified_cash_to_invoice_parent_links"], 500)
        self.assertEqual(len(oracle["titles"]), 40)
        self.assertEqual(sum(row["cash"] for row in oracle["titles"]),
                         sum(Fraction(row["amount"]["value"]) for row in package["financial_facts"] if row["event_kind"] == "cash_receipt"))

    def test_original_oracle_and_projection_agree_on_all_material_controls(self):
        workload, oracle, inputs, openings, lineage, dispositions = self.prepared()
        before = canonical_bytes(workload["neutral"])
        report = check_projection(workload, oracle, inputs, openings, lineage, dispositions)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["verified_cash_to_invoice_parent_links"], 5)
        self.assertEqual(report["original_fact_dispositions"], 95)
        checked = check_schedule(parse((ROOT / "cases/sv/sv01.spl").read_text(encoding="utf-8")))
        check_target(evaluate(checked, inputs, openings).to_dict(), target_expected(oracle))
        self.assertEqual(oracle["pool"]["earned"], Fraction(198833, 125))
        self.assertEqual(oracle["pool"]["payable"], Fraction(167583, 125))
        self.assertEqual(oracle["pool"]["recovered"], 250)
        self.assertEqual(canonical_bytes(workload["neutral"]), before)

    def test_projection_mutations_cannot_hide_in_equal_or_final_totals(self):
        prepared = self.prepared()
        changes = [lambda inputs: inputs["receipts"][0].update(amount=money("0")),
                   lambda inputs: inputs["receipts"].pop(),
                   lambda inputs: inputs["pictures"][1].update(funding_share="0"),
                   lambda inputs: inputs["eligible_costs"].pop()]
        for mutate in changes:
            workload, oracle, inputs, openings, lineage, dispositions = deepcopy(prepared)
            mutate(inputs)
            with self.assertRaises(ValueError):
                check_projection(workload, oracle, inputs, openings, lineage, dispositions)
        workload, oracle, inputs, openings, lineage, dispositions = deepcopy(prepared)
        lineage[0]["fact_ids"] = ["different-original-parent"]
        with self.assertRaisesRegex(ValueError, "MIXED_PROJECTED_LINEAGE_SOURCE"):
            check_projection(workload, oracle, inputs, openings, lineage, dispositions)

    def test_conserved_unauthorized_allocations_and_cost_selections_are_rejected(self):
        workload = generate_mixed()
        package = workload["neutral"]["package"]
        parent = package["allocations"][0]["source_fact_id"]
        for row in package["allocations"]:
            if row["source_fact_id"] == parent:
                row["weight"] = "0.5"
        with self.assertRaisesRegex(SkourasOracleError, "SV_ALLOCATION_UNAUTHORIZED_WEIGHT"):
            skouras(workload["neutral"])
        with self.assertRaises(DataError):
            validate_package(bind_package(package, ROOT / "cases/sv/sv01.spl"))
        workload = generate_mixed()
        package = workload["neutral"]["package"]
        package["parameters"]["cost_decisions"][0]["eligible"] = False
        with self.assertRaises(DataError):
            validate_package(bind_package(package, ROOT / "cases/sv/sv01.spl"))
        # The separate oracle validates supplied interpretation/branch authority;
        # canonical pinned terms add another independently checked admission path.

    def test_physical_permutation_and_seed_reproducibility_preserve_economics(self):
        first = generate_mixed(seed=7)
        self.assertEqual(canonical_bytes(first), canonical_bytes(generate_mixed(seed=7)))
        other = generate_mixed(seed=11)
        self.assertNotEqual(first["neutral"]["package"]["source_batches"][0]["sha256"], other["neutral"]["package"]["source_batches"][0]["sha256"])
        a, b = skouras(first["neutral"]), skouras(other["neutral"])
        for result in (a, b):
            result["closing_state"].pop("scenario_id")
        self.assertEqual(a, b)

    def test_guard_count_source_control_and_parent_mutations_fail_independently(self):
        workload = generate_mixed()
        workload["neutral"]["package"]["source_batches"][0]["row_count"] = 94
        with self.assertRaisesRegex(SkourasOracleError, "SV_SOURCE_BATCH_COUNT"):
            skouras(workload["neutral"])
        workload = generate_mixed()
        workload["neutral"]["package"]["source_batches"][0]["control_totals"][0]["signed_total"] = "0"
        with self.assertRaisesRegex(SkourasOracleError, "SV_SOURCE_CONTROL_TOTAL"):
            skouras(workload["neutral"])
        workload = generate_mixed()
        next(row for row in workload["neutral"]["package"]["financial_facts"] if "parent_fact_id" in row)["parent_fact_id"] = "missing-invoice"
        with self.assertRaisesRegex(SkourasOracleError, "SV_PARENT_REFERENCE_OR_CYCLE"):
            skouras(workload["neutral"])

    def test_scale_admission_requires_completed_matching_100_cohort(self):
        pins, budgets = {"harness": "abc"}, {"child_stdout_bytes": 64 * 1024 * 1024}
        good = {"format": "spl-mixed-performance/1", "status": "passed", "counts": {"raw_original_records": 100},
                "target_generation": TARGET_GENERATION,
                "required_audit_completed": True, "seed": 7, "dependency_pins": pins, "budgets": budgets, "transport": "compact-v1",
                "native_samples": [{"status": "passed", "target": {"status": "passed", "independent_control": "passed"},
                                    "audit": {"status": "passed", "independent_control": "passed"}, "reader": {"status": "passed"}}]}
        check_prerequisite(good, pins, 7, budgets)
        for field, value in [("status", "failed"), ("required_audit_completed", False),
                             ("dependency_pins", {"harness": "changed"}), ("native_samples", []), ("seed", 8), ("transport", "compact-v2"),
                             ("profile_stages", True), ("target_generation", "pre-memo-unit-closure"), ("target_generation", None)]:
            changed = deepcopy(good); changed[field] = value
            with self.assertRaisesRegex(ValueError, "MIXED_1000_REQUIRES"):
                check_prerequisite(changed, pins, 7, budgets)

    def test_wire_equality_checks_chunks_length_and_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            left, right = Path(temporary) / "left", Path(temporary) / "right"
            raw = b"a" * 65536 + b"b" * 123
            left.write_bytes(raw)
            right.write_bytes(raw)
            self.assertEqual(equal_wire_files(left, right), hashlib.sha256(raw).hexdigest())
            for changed in (raw[:-1], raw + b"c", raw[:65536] + b"z" + raw[65537:]):
                right.write_bytes(changed)
                with self.assertRaisesRegex(ValueError, "MIXED_AUDIT_WIRE_CHANGED"):
                    equal_wire_files(left, right)

    def test_10000_gate_requires_matching_completed_1000_not_100(self):
        good = {"format": "spl-mixed-performance/1", "status": "passed", "counts": {"raw_original_records": 1000},
                "target_generation": TARGET_GENERATION,
                "required_audit_completed": True, "seed": 7, "dependency_pins": {}, "budgets": {}, "transport": "compact-v2",
                "native_samples": [{"status": "passed", "target": {"status": "passed", "independent_control": "passed"},
                                    "audit": {"status": "passed", "independent_control": "passed"}, "reader": {"status": "passed"}}]}
        check_prerequisite(good, {}, 7, {}, "compact-v2", required_records=1000)
        for count in (100, 10000):
            changed = deepcopy(good)
            changed["counts"]["raw_original_records"] = count
            with self.assertRaisesRegex(ValueError, "MIXED_10000_REQUIRES_SUCCESSFUL_MATCHING_1000"):
                check_prerequisite(changed, {}, 7, {}, "compact-v2", required_records=1000)
        good["required_audit_completed"] = False
        with self.assertRaises(ValueError):
            check_prerequisite(good, {}, 7, {}, "compact-v2", required_records=1000)

    def test_reference_summary_retains_financial_checks_and_explicit_resource_failure(self):
        workload, oracle, inputs, openings, _, _ = self.prepared()
        with tempfile.TemporaryDirectory() as temporary:
            bindings = Path(temporary) / "bindings.json"
            write_json(bindings, {"inputs": inputs, "openings": openings})
            summary = reference_worker(ROOT / "cases/sv/sv01.spl", bindings)
        self.assertEqual(check_reference_worker(summary, target_expected(oracle)), "passed")
        self.assertGreater(summary["trace_nodes_observed"], 0)
        self.assertNotIn("trace", summary["outcome"])
        limited = deepcopy(summary)
        limited["outcome"] = {"status": "blocked", "emissions": {}, "closing": {}, "diagnostics": [{"code": "RESOURCE_LIMIT"}]}
        self.assertEqual(check_reference_worker(limited, target_expected(oracle)), "resource_limited")
        for mutate in (lambda s: s["outcome"].update(closing={"prepayment": "999"}),
                       lambda s: s.update(trace_nodes_observed=100001),
                       lambda s: s.update(trace_nodes_observed=True)):
            wrong = deepcopy(limited)
            mutate(wrong)
            with self.assertRaises(ValueError):
                check_reference_worker(wrong, target_expected(oracle))

    def test_partial_audit_header_never_grants_completion_or_successor_state(self):
        header = {"record": "header", "format": "spl-native-trace-stream/0.2",
                  "head": {"status": "blocked", "emissions": {}, "closing": {}, "diagnostics": [{"code": "RESOURCE_LIMIT"}]}}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "wire"
            path.write_bytes(canonical_bytes(header) + b"\ntruncated-node")
            observed = audit_head(path)
            self.assertTrue(observed["blocked_without_money_or_state"])
            self.assertNotIn("required_audit_completed", observed)
            path.write_bytes(canonical_bytes(header))
            with self.assertRaises(ValueError):
                audit_head(path)
        plans = sequential_dependency_plan(False)
        for count, plan in plans.items():
            self.assertEqual(len(plan), int(count))
            self.assertEqual(plan[0]["status"], "failed")
            for row in plan[1:]:
                self.assertEqual(row, {"close": row["close"], "status": "not_executed", "closing_state": [],
                                       "reason": "audited_predecessor_not_completed"})
        # Even a completed first close is not evidence that later closes ran.
        self.assertTrue(all(row["status"] == "not_executed" for row in sequential_dependency_plan(True)["8"][1:]))

    def test_generator_bounds_and_independent_standard_library_construction(self):
        for records, pictures, seed in [(0, None, 1), (100, 8, 1), (1001, None, 1), (True, None, 1), (100, None, True)]:
            with self.assertRaises(ValueError):
                generate_mixed(records, pictures=pictures, seed=seed)
        tree = ast.parse((ROOT / "validation/mixed_workloads.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"collections", "copy", "fractions", "hashlib", "json", "pathlib", "random"})

    def test_cli_forwards_the_explicit_transport_version(self):
        from scripts import spl_mixed_benchmark as mixed

        with patch.object(mixed, "benchmark", return_value={"status": "passed"}) as run:
            with patch("builtins.print"):
                self.assertEqual(mixed.main(["--transport", "compact-v2", "--output", "unused-mocked-output"]), 0)
            self.assertEqual(run.call_args.kwargs["transport"], "compact-v2")
            self.assertEqual(run.call_args.kwargs["implementation"], "legacy")

    def test_implementation_selector_preserves_legacy_default_and_pins_indexed_closure(self):
        self.assertEqual(implementation_spec(), {"id": "sv-legacy-source/1", "source": "cases/sv/sv01.spl",
                                               "emission": "Demos/SV.lean", "target": "spl_sv"})
        selected = implementation_spec("indexed")
        self.assertEqual(selected["id"], "sv-indexed-experiment/1")
        self.assertEqual(selected["target"], "spl_sv_indexed")
        self.assertEqual(set(dependency_files("indexed")) - set(dependency_files()),
                         {ROOT / "cases/sv/sv01-indexed.spl", ROOT / "Demos/SVIndexed.lean"})
        for invalid in ("other", "../outside.spl", "Indexed", None, False, {}):
            with self.assertRaises(ValueError):
                implementation_spec(invalid)
        from scripts import spl_mixed_benchmark as mixed
        with patch.object(mixed, "benchmark", return_value={"status": "passed"}) as run, patch("builtins.print"):
            self.assertEqual(mixed.main(["--implementation", "indexed", "--host-load-note", "isolated regression active",
                                        "--output", "unused-mocked-output"]), 0)
            self.assertEqual(run.call_args.kwargs["implementation"], "indexed")
            self.assertEqual(run.call_args.kwargs["host_load_note"], "isolated regression active")

    def test_indexed_scale_gate_requires_exact_implementation_and_old_target_control(self):
        sample = {"status": "passed", "old_target": {"status": "passed", "independent_control": "passed"},
                  "target": {"status": "passed", "independent_control": "passed"},
                  "audit": {"status": "passed", "independent_control": "passed"}, "reader": {"status": "passed"}}
        previous = {"format": "spl-mixed-performance/1", "status": "passed", "counts": {"raw_original_records": 100},
                    "target_generation": TARGET_GENERATION,
                    "required_audit_completed": True, "seed": 7, "dependency_pins": {}, "budgets": {}, "transport": "compact-v2",
                    "implementation": "indexed", "implementation_spec": implementation_spec("indexed"), "native_samples": [sample]}
        check_prerequisite(previous, {}, 7, {}, "compact-v2", implementation="indexed")
        changes = [lambda p: p.update(implementation="legacy"),
                   lambda p: p.update(implementation_spec=implementation_spec("legacy")),
                   lambda p: p["native_samples"][0].pop("old_target"),
                   lambda p: p["native_samples"][0].update(old_target=None),
                   lambda p: p["native_samples"][0]["old_target"].update(status="failed"),
                   lambda p: p["native_samples"][0]["old_target"].update(independent_control="not_checked")]
        for mutate in changes:
            changed = deepcopy(previous)
            mutate(changed)
            with self.assertRaises(ValueError):
                check_prerequisite(changed, {}, 7, {}, "compact-v2", implementation="indexed")
        with self.assertRaises(ValueError):
            check_prerequisite(previous, {}, 7, {}, "compact-v2", implementation="legacy")


if __name__ == "__main__":
    unittest.main()
