"""Original paid history, separate authority and recovery: canonical controls."""
import ast
from copy import deepcopy
from fractions import Fraction
from importlib import import_module
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from oracles.authorized_offsets import AuthorizedOffsetOracleError, authorized_offsets, exact_json
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import exact, instant, read_json, write_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import resolve_module, validate_module_package
from spl_compiler.run import normalize_target
from Tests.test_authorized_offset_oracle import fixture, control, pin_bundle, payment, competing, add_cash, successor, ARRAYS

offsets = import_module("cases.authorized-offsets.build_modules")


class AuthorizedOffsetModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/ao-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/authorized-offsets"
        cls.folder.mkdir(parents=True)
        for name in ["authorized-offsets.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/authorized-offsets" / name, cls.folder / name)
        for owner, name, value in [(offsets, "ROOT", cls.root), (offsets, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            control_patch = patch.object(owner, name, value)
            control_patch.start()
            cls.addClassCleanup(control_patch.stop)
        cls.reference = offsets.register_authorized_offsets()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        package = offsets.authorized_offset_package(data, reference=self.reference, state_cells=cells)
        result = offsets.run_authorized_offset_package(package, self.root, backend=backend, artifact_dir=output)
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
        expected = authorized_offsets(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        values = result["results"]
        self.same(values["comparison"], {key: expected[key] for key in values["comparison"]})
        for port in ["claims", "earning_lines", "offset_lines"]:
            self.same(offsets.neutral_value(values[port]), expected[port])
        self.assertEqual(offsets.neutral_state(result["closing_state"][0]["quantity"]), exact_json(expected["closing_state"]))
        self.assertEqual(offsets.neutral_state(result["closing_state"][0]["quantity"])["original_bundle"], data["original_bundle"])
        histories = expected["closing_state"]["period_history"]
        self.assertEqual(len(values["period_replays"]), len(histories))
        previous = None
        for record, replay in zip(histories, values["period_replays"]):
            d = deepcopy(data)
            d.pop("prior_result", None)
            d.update(case_id=record["source_case_id"], period=deepcopy(record["period"]), as_of=record["as_of"], cutoff=record["cutoff"],
                     **{key: exact_json(record[key]) for key in ARRAYS})
            # A historical independent prefix receives only evidence observable
            # by that prefix, retaining its own original cutoff and approval date.
            d["evidence"] = [row for row in d["evidence"] if instant(row["observed_at"]).seconds < instant(record["cutoff"]).seconds]
            if previous is None:
                d["opening_state"] = exact_json({**expected["closing_state"], "origin": "genesis", "source_case_id": "genesis",
                    "boundary": record["period"]["start"], "returned_basis": "0", "claims": [], "period_history": []})
            else:
                d["opening_state"] = exact_json(previous["closing_state"])
                d["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
            previous = authorized_offsets(d)
            self.assertEqual(replay["source_case_id"], record["source_case_id"])
            self.assertEqual(replay["period"], record["period"])
            self.same(offsets.neutral_value(replay["result"]), {key: previous[key] for key in replay["result"]})
        self.assertTrue(values["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertEqual(values["comparison"]["current_settlement_payment_status"], "no_event_supplied")
        self.assertFalse({"new_actual_paid", "bank_refund", "refund_executed"} & values["comparison"].keys())
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None, output=None):
        with self.assertRaises(AuthorizedOffsetOracleError):
            authorized_offsets(data)
        result = self.run_fixture(data, backend, cells=cells, output=output)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code)
        for field in ["results", "detail", "statements", "closing_state"]:
            self.assertFalse(result[field])
        self.assertNotIn("result_digest", result)
        return result

    def carried(self, original, previous, earned="3", quarter=2):
        data = successor(authorized_offsets(original), original, earned, quarter)
        path = self.root / ("serialized-actual-offset-q" + str(quarter) + ".json")
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = offsets.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        return data, [cell]

    def test_native_original_paid80_is_immutable_and_authority_is_separate(self):
        for authority, payable in [(True, "10"), (False, "30")]:
            data = fixture()
            data["cutoff"] = "2026-04-03T01:00:00+01:00"
            data["original_bundle"]["original"]["rate"] = "0.50"
            data["original_bundle"]["payment_snapshot"]["payments"][0]["paid_at"] = "2025-12-15T13:00:00+01:00"
            pin_bundle(data)
            if not authority:
                data["offset_authorities"] = []
            else:
                data["offset_authorities"][0]["amount"] = "20.00"
            with self.subTest(authority=authority), tempfile.TemporaryDirectory(dir=self.root) as output:
                result = self.run_fixture(data, "compare", output=output)
                self.controls(data, result)
                self.assertTrue(any("id=" + data["case_id"] in node["instance_scope"] for node in result["trace"]))
                # The wrapper identity is the existing original case ID, not
                # the entire recursively escaped anonymous source record.
                self.assertTrue(all("is_current" not in node["instance_scope"] for node in result["trace"]))
                c = result["results"]["comparison"]
                self.assertEqual((c["original_gross"], c["original_issued"], c["original_actual_paid"], c["current_signed_reversal"],
                                  c["revised_original_entitlement"], c["original_outstanding"], c["potential_overpayment"], c["payable_calculated"]),
                                 ("100", "100", "80", "-40", "60", "0", "20", payable))
                self.assertEqual(read_json(Path(output) / "result.json"), result)
                self.assertEqual(load_completed_result(output), result)
                self.assertTrue((Path(output) / "typed-ir.json").is_file())
                self.assertTrue((Path(output) / "Settlement.lean").is_file())

    def test_native_actual_cash_first_and_serialized_three_period_chain(self):
        original = fixture()
        add_cash(original)
        original["future_earnings"][0]["amount"] = "10"
        first = self.run_fixture(original, "compare")
        self.controls(original, first)
        self.assertEqual(first["results"]["offset_lines"][0]["claim_before"], "15")
        second_data, cells = self.carried(original, first)
        second = self.run_fixture(second_data, "compare", cells=cells)
        self.controls(second_data, second)
        third_data, cells = self.carried(second_data, second, earned="5", quarter=3)
        third = self.run_fixture(third_data, "compare", cells=cells)
        self.controls(third_data, third)
        self.assertEqual([r["results"]["comparison"]["original_actual_paid"] for r in [first, second, third]], ["80", "80", "80"])
        self.assertEqual([r["results"]["comparison"]["current_earning_offsets"] for r in [first, second, third]], ["10", "3", "2"])
        self.assertEqual([r["results"]["claims"][0]["remaining"] for r in [first, second, third]], ["5", "2", "0"])
        self.assertEqual(third["results"]["comparison"]["payable_calculated"], "3")
        conflicting, cells = self.carried(second_data, second, earned="5", quarter=3)
        conflicting["case_id"] = original["case_id"]
        self.blocked(conflicting, "OFFSET_DUPLICATE_PERIOD_CASE", "compare", cells=cells)

    def test_native_two_priority_recipes_and_same_kind_sequences_change_amounts(self):
        for recipe, amounts in [("clawback_first", (20, 10)), ("other_claim_first", (5, 25))]:
            data = fixture()
            competing(data, recipe)
            result = self.run_fixture(data, "compare")
            self.controls(data, result)
            by_id = {row["id"]: row for row in result["results"]["claims"]}
            self.assertEqual(tuple(exact(by_id[key]["earning_offsets"]) for key in ["overpayment-claim-1", "other-claim"]), amounts)
        data = fixture()
        data["future_earnings"][0]["amount"] = "10"
        data["offset_authorities"][0]["amount"] = "8"
        row = deepcopy(data["offset_authorities"][0])
        row.update(id="second-authority", claim_id="second-claim", sequence=2, amount="12", source_ref="synthetic-second-claim")
        data["offset_authorities"].append(row)
        for switched, amounts in [(False, (8, 2)), (True, (0, 10))]:
            if switched:
                data["offset_authorities"][0]["sequence"], data["offset_authorities"][1]["sequence"] = 2, 1
            result = self.run_fixture(data, "compare")
            self.controls(data, result)
            by_id = {row["id"]: row for row in result["results"]["claims"]}
            self.assertEqual(tuple(exact(by_id[key]["earning_offsets"]) for key in ["overpayment-claim-1", "second-claim"]), amounts)

    def test_native_additional_return_expands_capacity_only_after_recognition(self):
        original = fixture()
        first = self.run_fixture(original, "compare")
        self.controls(original, first)
        data, cells = self.carried(original, first, earned="30")
        revision = deepcopy(original["revision_authorities"][0])
        revision.update(id="revision-q2", effective=deepcopy(data["period"]), approved_date="2026-04-15", recorded_date="2026-04-15",
            observed_at="2026-04-16T00:00:00Z", permitted_reversal_ids=["reversal-q2"], maximum_returned_basis="40", source_ref="synthetic-revision-q2")
        reversal = deepcopy(original["reversals"][0])
        reversal.update(id="reversal-q2", revision_authority_id="revision-q2", returned_basis="40", return_date="2026-04-15", recognition_date="2026-04-15",
            observed_at="2026-04-16T00:00:00Z", source_ref="synthetic-return-q2")
        authority = deepcopy(original["offset_authorities"][0])
        authority.update(id="offset-q2", claim_id="claim-q2", sequence=2, effective=deepcopy(data["period"]), approved_date="2026-04-16", recorded_date="2026-04-16",
            eligible_from="2026-04-17", observed_at="2026-04-17T00:00:00Z", source_ref="synthetic-offset-q2")
        data["revision_authorities"], data["reversals"], data["offset_authorities"] = [revision], [reversal], [authority]
        result = self.run_fixture(data, "compare", cells=cells)
        self.controls(data, result)
        c = result["results"]["comparison"]
        self.assertEqual((c["cumulative_signed_reversal"], c["potential_overpayment"], c["total_authorized_original"], c["current_earning_offsets"], c["payable_calculated"]), ("-60", "40", "40", "20", "10"))
        data["offset_authorities"][0]["amount"] = "21"
        self.blocked(data, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY", "compare", cells=cells)
        data = fixture()
        data["reversals"][0]["recognition_date"] = "2026-03-15"
        self.blocked(data, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY", "compare")

    def test_native_unknown_populations_block_without_finance_and_empty_paid_is_explicit(self):
        for kind, code, label in [("complete_original_payment_population", "OFFSET_PAYMENT_POPULATION_REQUIRED", "payment_evidence_status"),
                                 ("complete_cash_recovery_population", "OFFSET_RECOVERY_POPULATION_REQUIRED", "recovery_evidence_status")]:
            data = fixture()
            data["evidence"] = [row for row in data["evidence"] if row["kind"] != kind]
            with tempfile.TemporaryDirectory(dir=self.root) as output:
                result = self.blocked(data, code, "compare", output=output)
                self.assertEqual(result[label], "no_event_supplied")
                self.assertEqual(read_json(Path(output) / "result.json"), result)
                self.assertEqual(load_completed_result(output), result)
        data = fixture()
        payment(data, "0")
        data["offset_authorities"] = []
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual((result["results"]["comparison"]["original_actual_paid"], result["results"]["comparison"]["original_outstanding"],
                          result["results"]["comparison"]["original_payment_status"]), ("0", "60", "complete_no_events"))

    def test_native_bank_alias_cash_overapplication_and_unused_bad_authority_atomic(self):
        data = fixture()
        alias = deepcopy(data["original_bundle"]["payment_snapshot"]["payments"][0])
        alias.update(id="payment-alias", source_ref="same-bank-new-name")
        data["original_bundle"]["payment_snapshot"]["payments"].append(alias)
        pin_bundle(data)
        self.blocked(data, "OFFSET_DUPLICATE_BANK_PAYMENT", "compare")
        data = fixture()
        add_cash(data, "21")
        self.blocked(data, "OFFSET_CLAIM_CASH_OVERAPPLICATION", "compare")
        data = fixture()
        unused = deepcopy(data["revision_authorities"][0])
        unused.update(id="unused-invalid", source_ref="synthetic-unused", approved=False)
        data["revision_authorities"].append(unused)
        self.blocked(data, "OFFSET_AUTHORITY_ASOF_SCOPE", "compare")

    def test_native_exact_fraction_and_raw_offset_timestamp_lineage(self):
        data = fixture()
        data["offset_authorities"][0]["amount"] = "1/3"
        data["future_earnings"][0]["amount"] = "1/2"
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(exact(result["results"]["comparison"]["payable_calculated"]), Fraction(1, 6))
        data = fixture()
        add_cash(data)
        data["future_earnings"][0].update(amount="10", observed_at="2026-04-02T23:59:59.999999999999Z")
        data["cash_recoveries"][0].update(received_at="2026-03-15T13:00:00+01:00", observed_at="2026-03-16T00:00:00.000Z")
        data["original_bundle"]["original"]["rate"] = "0.50"
        data["original_bundle"]["payment_snapshot"]["payments"][0]["paid_at"] = "2025-12-15T13:00:00+01:00"
        data["original_bundle"]["payment_snapshot"]["as_of"] = "2026-04-03T01:00:00+01:00"
        control(data, "complete_original_payment_population")["as_of"] = data["original_bundle"]["payment_snapshot"]["as_of"]
        pin_bundle(data)
        self.controls(data, self.run_fixture(data, "compare"))
        data["future_earnings"][0]["observed_at"] = data["cutoff"]
        self.blocked(data, "OFFSET_FACT_CUTOFF", "compare")

    def test_reference_partial_paid_and_original_population_controls(self):
        data = fixture()
        payment(data, "50")
        data["offset_authorities"] = []
        result = self.run_fixture(data)
        self.controls(data, result)
        self.assertEqual(result["results"]["comparison"]["original_outstanding"], "10")
        for change in [lambda d: d["original_bundle"]["payment_snapshot"].update(payments=[], applications=[]),
                       lambda d: d["original_bundle"]["payment_snapshot"]["applications"][0].update(amount="81"),
                       lambda d: control(d, "complete_original_payment_population").update(observed_at="2025-12-15T00:00:00Z")]:
            data = fixture()
            change(data)
            pin_bundle(data)
            self.blocked(data)

    def test_reference_duplicate_scope_receipt_upstream_and_population_errors(self):
        for key in ARRAYS:
            data = fixture()
            if not data[key]:
                add_cash(data)
            data[key].append(deepcopy(data[key][0]))
            self.blocked(data)
        for change in [lambda d: d["offset_authorities"][0]["scope"].update(pool_id="outside"),
                       lambda d: d["offset_authorities"][0].update(priority=1),
                       lambda d: d["reversals"][0].update(returned_basis="81"),
                       lambda d: d["future_earnings"].append({**deepcopy(d["future_earnings"][0]), "id": "alias", "sequence": 2, "source_ref": "other-source"}),
                       lambda d: d["cash_recoveries"].append({**deepcopy(d["cash_recoveries"][0]), "id": "alias", "source_ref": "other-source"}),
                       lambda d: d["recovery_applications"][0].update(amount="4"),
                       lambda d: d["cash_recoveries"][0].update(received_date="2026-03-16")]:
            data = fixture()
            add_cash(data)
            change(data)
            self.blocked(data)

    def test_reference_closed_principal_history_cutoff_and_actual_predecessor(self):
        original = fixture()
        first = self.run_fixture(original)
        self.controls(original, first)
        data, cells = self.carried(original, first)
        authority = deepcopy(original["offset_authorities"][0])
        authority.update(id="new-authority", claim_id="new-claim", sequence=2, source_ref="synthetic-new-authority", effective=deepcopy(data["period"]),
            eligible_from="2026-04-10", approved_date="2026-04-09", recorded_date="2026-04-09", observed_at="2026-04-10T00:00:00Z")
        data["offset_authorities"] = [authority]
        self.blocked(data, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY", cells=cells)
        for change in [lambda d: d.pop("prior_result"),
                       lambda d: d["opening_state"]["claims"][0].update(remaining="1"),
                       lambda d: d["future_earnings"][0].update(id=original["future_earnings"][0]["id"]),
                       lambda d: d["future_earnings"][0].update(upstream_ref=original["future_earnings"][0]["upstream_ref"]),
                       lambda d: next(row for row in d["evidence"] if row["id"] == "earnings-source").update(observed_at="2026-05-01T00:00:00Z")]:
            data, cells = self.carried(original, first)
            change(data)
            self.blocked(data, cells=cells)
        data, cells = self.carried(original, first)
        data["prior_result"]["result_ref"] = "result@sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "OFFSET_CANONICAL_PREDECESSOR_MISMATCH"):
            self.run_fixture(data, cells=cells)

    def test_reference_original_snapshot_and_recipe_remain_pinned(self):
        original = fixture()
        first = self.run_fixture(original)
        for change in [lambda d: d["original_bundle"]["original"].update(rate="0.50"),
                       lambda d: d["original_bundle"]["payment_snapshot"].update(as_of="2026-04-03T01:00:00+01:00"),
                       lambda d: d["policy"].update(priority_recipe="other_claim_first"),
                       lambda d: d["opening_state"].update(purpose="reserve")]:
            data, cells = self.carried(original, first)
            change(data)
            self.blocked(data, cells=cells)
        data = fixture()
        competing(data)
        expected = self.run_fixture(data)
        self.controls(data, expected)
        for key in ARRAYS:
            data[key].reverse()
        data["evidence"].reverse()
        replay = self.run_fixture(data)
        self.controls(data, replay)
        self.assertEqual(expected["results"], replay["results"])
        self.assertEqual(expected["closing_state"][0]["quantity"], replay["closing_state"][0]["quantity"])

    def test_adapter_only_transports_original_values_and_never_solves_priority(self):
        tree = ast.parse((ROOT / "cases/authorized-offsets/build_modules.py").read_text(encoding="utf-8"))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertFalse(any(name.startswith("oracles") for name in imports))
        package = offsets.authorized_offset_package(fixture(), reference=self.reference)
        self.assertFalse({"potential_overpayment", "original_actual_paid", "solved_claims", "current_earning_offsets", "payable_calculated"} & package["inputs"].keys())
        data = fixture()
        data["offset_authorities"][0]["priority"] = 7
        self.assertEqual(offsets.authorized_offset_package(data, reference=self.reference)["inputs"]["offset_authorities"][0]["priority"], "7")
        for amount in [0.5, True, "-1", "1e2"]:
            data = fixture()
            data["future_earnings"][0]["amount"] = amount
            with self.assertRaisesRegex(ValueError, "OFFSET_EXACT_NONNEGATIVE_VALUE"):
                self.run_fixture(data)
        data = fixture()
        data["future_earnings"][0]["upstream_ref"] = "whole-artifact-only"
        with self.assertRaisesRegex(ValueError, "OFFSET_ORIGINAL_LINE_REFERENCE"):
            self.run_fixture(data)


if __name__ == "__main__":
    unittest.main()
