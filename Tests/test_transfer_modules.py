"""Canonical coordinator calculation against independently authored controls.

Native groups request compare (IR, native-emitted Lean and reference), then
execute Lean from the separate Python emitter against the same raw bindings.
Reference groups deliberately name the narrower execution evidence.
"""
import ast
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.transfers import build_modules as transfers
from cases.r1 import build_modules as registration
from oracles.contract_transfers import TransferOracleError, contract_transfers, exact_json
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import exact, read_json, write_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.run import normalize_target
from Tests.test_transfer_oracle import fixture, add_account, add_edge, successor


class TransferModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/transfer-module-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/transfers"
        cls.folder.mkdir(parents=True)
        for name in ["transfers.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/transfers" / name, cls.folder / name)
        for owner, name, value in [(transfers, "ROOT", cls.root), (transfers, "FOLDER", cls.folder),
                                   (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = transfers.register_transfers()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        package = transfers.transfers_package(data, reference=self.reference, state_cells=cells)
        result = run_module_package(package, self.root, backend=backend, artifact_dir=output)
        if backend == "compare" and result.get("trace_origin") == "native_ir_interpreter":
            checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
            reference = normalize_target(evaluate(checked, inputs, openings).to_dict())
            generated = normalize_target(run_generated(checked,
                {key: decode_value(value, checked.types[key]) for key, value in inputs.items()},
                {key: decode_value(value, checked.types[key]) for key, value in openings.items()}))
            for field in ["status", "emissions", "closing"]:
                self.assertEqual(generated[field], reference[field], field)
            self.assertEqual([row["code"] for row in generated["diagnostics"]], [row["code"] for row in reference["diagnostics"]])
        return result

    def same(self, actual, expected):
        if type(expected) in {Fraction, int}:
            self.assertEqual(Fraction(actual) if type(actual) is int else exact(actual), expected)
        elif isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key, value in expected.items():
                with self.subTest(field=key):
                    self.same(actual[key], value)
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected):
                self.same(left, right)
        else:
            self.assertEqual(actual, expected)

    def controls(self, data, result):
        expected = contract_transfers(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        values = result["results"]
        self.same(values["comparison"], {key: expected[key] for key in values["comparison"]})
        self.same(values["account_results"], expected["accounts"])
        self.same(transfers.neutral_state(values["applied_transfers"]), expected["transfers"])
        self.assertEqual(transfers.neutral_state(result["closing_state"][0]["quantity"]), exact_json(expected["closing_state"]))
        self.assertTrue(values["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertFalse({"actual_paid", "bank_refund", "payable"} & values["comparison"].keys())
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None):
        with self.assertRaises(TransferOracleError):
            contract_transfers(data)
        result = self.run_fixture(data, backend, cells=cells)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code)
        for field in ["results", "detail", "statements", "closing_state"]:
            self.assertFalse(result[field])
        return result

    def carried(self, original, previous, entitlement=None, transfer=None):
        data = successor(contract_transfers(original), entitlement, transfer)
        path = self.root / "serialized-actual-transfer-history.json"
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = transfers.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        return data, [cell]

    def test_native_source70_target30_real_scopes_and_envelope(self):
        data = fixture()
        package = transfers.transfers_package(data, reference=self.reference)
        self.assertEqual(package["scope"]["agreement_id"], data["coordinator"]["id"])
        self.assertEqual(package["scope"]["purpose"], "coordination_envelope_only")
        self.assertNotIn(package["scope"]["agreement_id"], [row["scope"]["agreement_id"] for row in data["accounts"]])
        with tempfile.TemporaryDirectory(dir=self.root) as output:
            result = self.run_fixture(data, "compare", output=output)
            self.controls(data, result)
            self.assertEqual([row["final_entitlement"] for row in result["results"]["account_results"]], ["70", "30"])
            self.assertTrue(result["verification"]["reference_agrees"])
            self.assertTrue((Path(output) / "typed-ir.json").is_file())
            self.assertTrue((Path(output) / "Settlement.lean").is_file())
            self.assertEqual(read_json(Path(output) / "result.json"), result)
            self.assertEqual(load_completed_result(output), result)

    def test_native_downstream_incoming_credit_precedes_lower_sequence(self):
        data = fixture()
        add_account(data, "third")
        add_edge(data, "downstream", "target", "third", sequence=0)
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(result["results"]["comparison"]["topological_accounts"], ["source", "target", "third"])
        self.assertEqual([row["sequence"] for row in result["results"]["applied_transfers"]], ["1", "0"])
        self.assertEqual([row["final_entitlement"] for row in result["results"]["account_results"]], ["70", "10", "20"])

    def test_native_outgoing_authorized_sequence_changes_intermediates(self):
        data = fixture()
        add_account(data, "third")
        add_edge(data, "second", "source", "third", amount="60", sequence=2)
        first = self.run_fixture(data, "compare")
        self.controls(data, first)
        data["authorizations"][1]["sequence"] = 0
        second = self.run_fixture(data, "compare")
        self.controls(data, second)
        self.assertEqual([row["source_after"] for row in first["results"]["applied_transfers"]], ["70", "10"])
        self.assertEqual([row["source_after"] for row in second["results"]["applied_transfers"]], ["40", "10"])
        self.assertEqual(first["results"]["account_results"], second["results"]["account_results"])

    def test_native_serialized_history_never_reuses_prior_money(self):
        original = fixture()
        first = self.run_fixture(original, "compare")
        self.controls(original, first)
        empty, cells = self.carried(original, first)
        empty_result = self.run_fixture(empty, "compare", cells=cells)
        self.controls(empty, empty_result)
        self.assertEqual([row["final_entitlement"] for row in empty_result["results"]["account_results"]], ["0", "0"])
        data, cells = self.carried(original, first, "30", "10")
        result = self.run_fixture(data, "compare", cells=cells)
        self.controls(data, result)
        self.assertEqual([row["final_entitlement"] for row in result["results"]["account_results"]], ["20", "10"])
        self.assertEqual(result["results"]["applied_transfers"][0]["source_before"], "30")
        no_funds, cells = self.carried(original, first, None, "10")
        self.blocked(no_funds, "TRANSFER_SOURCE_OVERDRAW", "compare", cells=cells)

    def test_native_fractional_current_entitlement_without_rounding(self):
        data = fixture()
        data["entitlements"][0]["amount"] = "1/3"
        data["authorizations"][0]["maximum_amount"] = "1/7"
        data["transfers"][0]["amount"] = "1/7"
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(exact(result["results"]["account_results"][0]["final_entitlement"]), Fraction(4, 21))

    def test_native_raw_timestamp_lineage_with_exact_cutoff_and_actual_carry(self):
        original = fixture()
        for row in original["entitlements"] + original["transfers"]:
            row["observed_at"] = row["observed_at"].replace("Z", ".000+00:00")
        first = self.run_fixture(original, "compare")
        self.controls(original, first)
        audit = transfers.neutral_state(first["closing_state"][0]["quantity"])["last_period"][0]
        self.assertEqual(audit["entitlement_facts"][0]["observed_at"], original["entitlements"][0]["observed_at"])
        self.assertEqual(audit["applied_transfers"][0]["observed_at"], original["transfers"][0]["observed_at"])
        data, cells = self.carried(original, first, "30", "10")
        data["entitlements"][0]["observed_at"] = "2026-06-21T01:00:00+01:00"
        data["cutoff"] = "2026-07-03T00:00:00.0000002Z"
        data["transfers"][0]["observed_at"] = "2026-07-03T01:00:00.0000001+01:00"
        second = self.run_fixture(data, "compare", cells=cells)
        self.controls(data, second)
        self.assertEqual([row["final_entitlement"] for row in second["results"]["account_results"]], ["20", "10"])
        cutoff = deepcopy(data)
        cutoff["transfers"][0]["observed_at"] = cutoff["cutoff"]
        self.blocked(cutoff, "TRANSFER_FACT_CUTOFF", cells=cells)
        data["opening_state"]["last_period"][0]["entitlement_facts"][0]["observed_at"] = original["entitlements"][0]["observed_at"].replace(".000+00:00", "Z")
        self.blocked(data, "TRANSFER_OPENING_SNAPSHOT", cells=cells)

    def test_native_cycles_overdraw_unapproved_and_unknown_atomic(self):
        data = fixture()
        add_edge(data, "cycle", "target", "source", amount="1")
        self.blocked(data, "TRANSFER_GRAPH_CYCLE", "compare")
        for code, change in [
                ("TRANSFER_SOURCE_OVERDRAW", lambda d: (d["transfers"][0].update(amount="101"), d["authorizations"][0].update(maximum_amount="101"))),
                ("TRANSFER_AUTHORIZATION_ASOF", lambda d: d["authorizations"][0].update(approved=False)),
                ("TRANSFER_UNKNOWN_ACCOUNT", lambda d: d["authorizations"][0].update(target_account="missing"))]:
            data = fixture()
            change(data)
            with self.subTest(code=code):
                result = self.blocked(data, code, "compare")
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_native_consumed_upstream_alias_is_not_fresh_entitlement(self):
        original = fixture()
        first = self.run_fixture(original)
        data, cells = self.carried(original, first, "30", "10")
        data["entitlements"][0]["upstream_result_ref"] = original["entitlements"][0]["upstream_result_ref"]
        self.blocked(data, "TRANSFER_UPSTREAM_ALREADY_CONSUMED", "compare", cells=cells)

    def test_reference_duplicates_authority_reuse_and_original_aliases(self):
        for field in ["accounts", "entitlements", "authorizations", "transfers", "evidence"]:
            data = fixture()
            data[field].append(deepcopy(data[field][0]))
            self.blocked(data)
        data = fixture()
        data["transfers"].append({**deepcopy(data["transfers"][0]), "id": "other-id"})
        self.blocked(data, "TRANSFER_AUTHORIZATION_REFERENCE_OR_REUSE")
        for same_source, code in [(False, "TRANSFER_UPSTREAM_ALREADY_CONSUMED"), (True, "TRANSFER_DUPLICATE_SOURCE_VIEW")]:
            data = fixture()
            row = deepcopy(data["entitlements"][0])
            row.update(id="other-id", source_ref="other-source")
            if same_source:
                row.update(source_ref=data["entitlements"][0]["source_ref"], upstream_result_ref="artifact#other-line")
            data["entitlements"].append(row)
            self.blocked(data, code)

    def test_reference_scope_evidence_period_cutoff_and_unused_authority(self):
        for code, change in [
                ("TRANSFER_SELF_EDGE", lambda d: d["authorizations"][0].update(target_account="source")),
                ("TRANSFER_ENDPOINT_SCOPE", lambda d: d["authorizations"][0]["target_scope"].update(pool_id="outside")),
                ("TRANSFER_FACT_CUTOFF", lambda d: d["transfers"][0].update(observed_at=d["cutoff"])),
                ("TRANSFER_ENTITLEMENT_PERIOD", lambda d: d["entitlements"][0].update(effective_date=d["period"]["end"])),
                ("TRANSFER_EVIDENCE_REQUIRED", lambda d: d["evidence"][-1].update(account_ids=["source"])),
                ("TRANSFER_AUTHORIZATION_ASOF", lambda d: (d.update(transfers=[]), d["authorizations"][0].update(approved=False)))]:
            data = fixture()
            change(data)
            with self.subTest(code=code):
                self.blocked(data, code)
        data = fixture()
        for row in [data["accounts"][1]["scope"], data["opening_state"]["account_scopes"][1]["scope"],
                    data["authorizations"][0]["target_scope"], data["transfers"][0]["target_scope"]]:
            row["agreement_id"] = data["accounts"][0]["scope"]["agreement_id"]
        self.blocked(data, "TRANSFER_CROSS_AGREEMENT_REQUIRED")
        data = fixture()
        data["authorizations"][0]["approved_date"] = data["as_of"]
        self.controls(data, self.run_fixture(data))

    def test_reference_actual_predecessor_full_scope_set_and_consumed_ids(self):
        original = fixture()
        first = self.run_fixture(original)
        for field, key, old, code in [
                ("entitlements", "id", "entitlement-source-q1", "TRANSFER_ENTITLEMENT_ALREADY_CONSUMED"),
                ("authorizations", "id", "authorization-q1", "TRANSFER_AUTHORIZATION_ALREADY_CONSUMED"),
                ("transfers", "id", "transfer-q1", "TRANSFER_ALREADY_CONSUMED")]:
            data, cells = self.carried(original, first, "30", "10")
            data[field][0][key] = old
            self.blocked(data, code, cells=cells)
        data, cells = self.carried(original, first, "30", "10")
        data["accounts"][1]["scope"]["pool_id"] = "changed-real-account"
        self.blocked(data, "TRANSFER_OPENING_SCOPE", cells=cells)
        data, cells = self.carried(original, first, "30", "10")
        data.pop("prior_result")
        self.blocked(data, "TRANSFER_PREDECESSOR_REQUIRED", cells=cells)
        data, cells = self.carried(original, first, "30", "10")
        data["prior_result"]["result_ref"] = "result@sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "TRANSFER_CANONICAL_PREDECESSOR_MISMATCH"):
            self.run_fixture(data, cells=cells)

    def test_reference_permutation_same_opening_replay_and_raw_amount_history(self):
        data = fixture()
        add_account(data, "alpha")
        original = deepcopy(data)
        first = self.run_fixture(data)
        self.controls(data, first)
        for field in ["accounts", "entitlements", "authorizations", "transfers", "evidence"]:
            data[field].reverse()
        second = self.run_fixture(data)
        replay = self.run_fixture(original)
        self.controls(data, second)
        for candidate in [second, replay]:
            self.assertEqual(first["results"], candidate["results"])
            self.assertEqual(first["closing_state"][0]["quantity"], candidate["closing_state"][0]["quantity"])
        data = fixture()
        data["entitlements"][0]["amount"] = "0.10"
        data["authorizations"], data["transfers"] = [], []
        first = self.run_fixture(data)
        self.controls(data, first)
        following, cells = self.carried(data, first)
        self.controls(following, self.run_fixture(following, cells=cells))
        self.assertEqual(first["closing_state"][0]["quantity"]["last_period"][0]["entitlement_facts"][0]["amount"], "0.10")

    def test_adapter_is_transport_only_and_requires_original_line(self):
        tree = ast.parse((ROOT / "cases/transfers/build_modules.py").read_text(encoding="utf-8"))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertFalse(any(name.startswith("oracles") for name in imports))
        package = transfers.transfers_package(fixture(), reference=self.reference)
        self.assertFalse({"topology", "balances", "account_results", "applied_transfers"} & package["inputs"].keys())
        data = fixture()
        data["entitlements"][0]["upstream_result_ref"] = "whole-artifact-only"
        with self.assertRaisesRegex(ValueError, "TRANSFER_UPSTREAM_LINE_REFERENCE"):
            self.run_fixture(data)


if __name__ == "__main__":
    unittest.main()
