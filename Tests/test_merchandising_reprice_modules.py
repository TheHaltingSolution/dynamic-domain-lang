"""Original as-known merchandising recognition through registered native SPL."""
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
from oracles.merchandising_reprice import MerchandisingRepriceOracleError, merchandising_reprice
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import DataError, exact, read_json, write_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT, interpret_schedule
from spl_compiler.modules import resolve_module, validate_module_package
from spl_compiler.run import carry_state, normalize_target
from Tests.test_merchandising_reprice_oracle import fixture, prefix, preview, population, add_fact, extend_q4

merch = import_module("cases.merchandising-reprice.build_modules")


class MerchandisingRepriceModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/mr-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/merchandising-reprice"
        cls.folder.mkdir(parents=True)
        for name in ["merchandising-reprice.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/merchandising-reprice" / name, cls.folder / name)
        for owner, key, value in [(merch, "ROOT", cls.root), (merch, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            control = patch.object(owner, key, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = merch.register_merchandising_reprice()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None, python_emitted=True):
        package = merch.merchandising_reprice_package(data, reference=self.reference, state_cells=cells)
        result = merch.run_merchandising_reprice_package(package, self.root, backend=backend, artifact_dir=output)
        if backend == "compare" and python_emitted and result.get("trace_origin") == "native_ir_interpreter":
            checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
            reference = normalize_target(evaluate(checked, inputs, openings).to_dict())
            generated = normalize_target(run_generated(checked,
                {key: decode_value(value, checked.types[key]) for key, value in inputs.items()},
                {key: decode_value(value, checked.types[key]) for key, value in openings.items()}))
            for field in ["status", "emissions", "closing"]:
                self.assertEqual(generated[field], reference[field], field)
            self.assertEqual([row["code"] for row in generated["diagnostics"]], [row["code"] for row in reference["diagnostics"]])
        if output is not None:
            self.assertEqual(read_json(Path(output) / "result.json"), result)
            self.assertEqual(load_completed_result(output), result)
        return result

    def same(self, actual, expected):
        if type(expected) in {int, Fraction}:
            self.assertEqual(Fraction(actual) if isinstance(actual, (str, int)) else exact(actual), expected)
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
        expected = merchandising_reprice(data)
        self.assertEqual(result["status"], "calculated" if expected["consumable_state"] else "provisional", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        values = result["results"]
        comparison = merch.neutral_value(values["comparison"])
        self.same(comparison, {key: expected[key] for key in comparison})
        self.same(merch.neutral_value(values["as_known_snapshots"]), expected["as_known_snapshots"])
        self.same(merch.neutral_value(values["recognition_history"]), expected["recognition_history"])
        if expected["consumable_state"]:
            self.assertEqual(len(result["closing_state"]), 1)
            self.same(merch.neutral_state(result["closing_state"][0]["quantity"]), expected["closing_state"])
        else:
            self.assertEqual(result["closing_state"], [])
            with self.assertRaises(DataError) as blocked:
                carry_state(result)
            self.assertEqual(blocked.exception.code, "NONCONSUMABLE_STATE")
        self.assertTrue(values["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        return expected

    def blocked(self, data, backend="reference", *, output=None):
        with self.assertRaises(MerchandisingRepriceOracleError):
            merchandising_reprice(data)
        result = self.run_fixture(data, backend, output=output)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        for key in ["results", "detail", "statements", "closing_state"]:
            self.assertFalse(result[key])
        self.assertNotIn("result_digest", result)
        return result

    def carried(self, data, previous):
        data = deepcopy(data)
        path = self.root / "serialized-actual-merchandising-state.json"
        write_json(path, previous["closing_state"])
        cells = read_json(path)
        for cell in cells:
            cell.pop("movement", None)  # Output reconciliation is not an input field.
        opening = merch.neutral_state(cells[0]["quantity"])
        data["opening_state"] = opening
        data["prior_result"] = {"source_case_id": opening["source_case_id"], "period": previous["results"]["comparison"]["period"],
            "closing_state": deepcopy(opening), "result_ref": cells[0]["prior_result_ref"]}
        return data, cells

    def test_native_all_intermediates_original_issues_paid_and_completed_publication(self):
        data = fixture()
        result = self.run_fixture(data, "compare", output=self.root / "baseline")
        expected = self.controls(data, result)
        self.assertEqual(expected["thresholds"], [77000000, 87000000, 107000000])
        self.assertEqual([expected[key] for key in ["catchup", "new_recognition_candidate", "actual_paid", "issued_outstanding", "candidate_total_unpaid"]],
                         [210, Fraction(945, 2), 1310, 55, Fraction(1055, 2)])
        self.assertEqual([row["amount"] for row in data["issues"]], ["455", "910"])
        for wrong in [Fraction(635, 2), Fraction(1475, 2), Fraction(1165, 2)]:
            self.assertNotEqual(expected["candidate_total_unpaid"], wrong)

    def test_native_actual_serialized_q1_q2_q3_q4_carry_recognizes210_once(self):
        original = fixture()
        first = prefix(original, 1)
        first["opening_state"] = {"scope": deepcopy(first["scope"]), "purpose": "first_dollar_merchandising", "policy": deepcopy(first["policy"]),
            "boundary": "2006-01-01", "origin": "genesis", "source_case_id": "genesis"}
        r1 = self.run_fixture(first, "compare", output=self.root / "first")
        e1 = self.controls(first, r1)
        self.assertEqual(e1["actual_paid"], 0)
        second, c1 = self.carried(prefix(original, 2), r1)
        r2 = self.run_fixture(second, "compare", cells=c1, output=self.root / "second")
        e2 = self.controls(second, r2)
        self.assertEqual((e2["known_issued"], e2["actual_paid"]), (455, 400))
        third, c2 = self.carried(prefix(original, 3), r2)
        r3 = self.run_fixture(third, "compare", cells=c2, output=self.root / "third")
        e3 = self.controls(third, r3)
        fourth = extend_q4(third, {"closing_state": merch.neutral_state(r3["closing_state"][0]["quantity"]),
            "source_case_id": third["case_id"], "period": original["periods"][-1]["period"]})
        fourth, c3 = self.carried(fourth, r3)
        r4 = self.run_fixture(fourth, "compare", cells=c3, output=self.root / "fourth")
        e4 = self.controls(fourth, r4)
        self.assertEqual((e3["catchup"], e4["catchup"], e4["recognized_this_run"]), (210, 0, 0))
        self.assertEqual(e4["candidate_total_unpaid"], Fraction(1055, 2))
        self.assertEqual(len(e4["recognition_history"]), 4)

    def test_native_pretrigger_preview_is_partial_and_has_no_consumable_state(self):
        data = preview()
        expected = self.controls(data, self.run_fixture(data, "compare", output=self.root / "preview"))
        self.assertEqual((expected["current_earnings"], expected["recognized_this_run"], expected["recognized_cumulative"]), (Fraction(455, 2), 0, 1365))
        self.assertEqual(expected["candidate_total_unpaid"], Fraction(565, 2))
        changed = preview()
        changed["run"]["mode"] = "final"
        changed["views"][-1].update(mode="final", recognition_id="fake-full-recognition")
        self.blocked(changed, "compare")

    def test_native_threshold_equality_exact_fraction_and_original_raw_lexemes(self):
        below = fixture()
        below["box_office"][-1]["gross"] = "86999999.99"
        expected = self.controls(below, self.run_fixture(below, "compare"))
        self.assertEqual((expected["rate"], expected["catchup"]), (Fraction(13, 200), 0))
        high = fixture()
        high["box_office"][-1]["gross"] = "107000000"
        highest = self.controls(high, self.run_fixture(high, "compare"))
        self.assertEqual(highest["rate"], Fraction(7, 80))
        self.assertEqual(highest["candidate_total_unpaid"], Fraction(3335, 4))
        before_high = fixture()
        before_high["box_office"][-1]["gross"] = "106999999.99"
        self.assertEqual(self.controls(before_high, self.run_fixture(before_high, "compare"))["rate"], Fraction(3, 40))
        unsupported = fixture()
        unsupported["box_office"][0]["gross"] = "76999999.99"
        self.blocked(unsupported, "compare")
        data = fixture()
        data["receipts"][-1].update(amount="5000.00", observed_at="2006-10-02T23:59:59.999999999999Z")
        data["receipts"][-1]["id"] = "license-" + chr(0x5C71)
        population(data)["receipt_ids"][-1] = data["receipts"][-1]["id"]
        data["views"][-1]["cutoff"] = "2006-10-03T01:00:00+01:00"
        population(data)["observed_at"] = data["receipts"][-1]["observed_at"]
        next(row for row in data["evidence"] if row["id"] == population(data)["evidence_ref"])["observed_at"] = population(data)["observed_at"]
        self.controls(data, self.run_fixture(data, "compare"))
        data["receipts"][-1]["observed_at"] = "2006-10-03T00:00:00Z"
        self.blocked(data, "compare")

    def test_native_extra_cash_payment_changes_arrears_not_recognition(self):
        data = fixture()
        payment = add_fact(data, "extra-payment", "actual_participant_disbursement", "2006-09-02T00:00:00Z", bank_disbursement_id="extra-bank", amount="55", paid_date="2006-09-01")
        application = add_fact(data, "extra-application", "actual_payment_application", "2006-09-03T00:00:00Z", payment_id="extra-payment", issue_id="issue-q1", amount="55", applied_date="2006-09-02")
        data["payments"].append(payment)
        data["applications"].append(application)
        control = population(data)
        control["payment_ids"].append(payment["id"])
        control["disbursement_ids"].append(payment["bank_disbursement_id"])
        control["application_ids"].append(application["id"])
        control["payment_total"] = control["application_total"] = "1365"
        expected = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((expected["catchup"], expected["actual_paid"], expected["issued_outstanding"], expected["candidate_total_unpaid"]), (210, 1365, 0, Fraction(945, 2)))

    def test_native_missing_population_blocks_unknown_payment_before_publication(self):
        data = fixture()
        data["populations"] = [row for row in data["populations"] if row["view_id"] != "view-q3"]
        result = self.blocked(data, "compare", output=self.root / "missing-population")
        self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
        self.assertNotIn("actual_paid", result)
        self.assertEqual(result["diagnostics"][0]["code"], "MR_COMPLETE_POPULATION_REQUIRED")

    def test_native_original_alias_metric_unknown_application_and_issue_change_are_atomic(self):
        for kind in ["alias", "metric", "application", "issue"]:
            data = fixture()
            if kind == "alias":
                row = deepcopy(data["receipts"][-1])
                row.update(id="renamed-license", source_ref="renamed-source")
                data["receipts"].append(row)
            elif kind == "metric":
                data["box_office"][-1]["metric"] = "worldwide-estimate"
            elif kind == "application":
                data["applications"][-1]["issue_id"] = "unknown-original-issue"
            else:
                data["issues"][0]["amount"] = "525"
            with self.subTest(kind=kind):
                result = self.blocked(data, "compare")
                self.assertEqual(result.get("trace_origin"), "native_ir_interpreter")

    def test_native_original_evidence_slots_are_checked_after_mechanical_adapter(self):
        for kind in ["unknown", "misbound", "duplicate", "range", "missing", "unused_bad"]:
            package = merch.merchandising_reprice_package(fixture(), reference=self.reference)
            evidence = package["evidence"]["evidence"]
            if kind == "unknown":
                package["inputs"]["receipts"][-1]["evidence_slot"] = "-1"
            elif kind == "misbound":
                original = package["inputs"]["receipts"][-1]["evidence_ref"]
                package["inputs"]["receipts"][-1]["evidence_slot"] = next(row["slot"] for row in evidence if row["id"] != original)
            elif kind == "duplicate":
                evidence[0]["slot"] = evidence[1]["slot"]
            elif kind == "range":
                evidence[0]["slot"] = str(len(evidence))
            elif kind == "missing":
                evidence.pop(0)
            else:
                evidence[-1]["approved"] = False
            # Intentional raw physical-binding mutation bypasses the adapter.
            with self.subTest(kind=kind):
                result = merch.run_merchandising_reprice_package(package, self.root, backend="compare")
                self.assertEqual(result["status"], "blocked", result["diagnostics"])
                self.assertEqual(result.get("trace_origin"), "native_ir_interpreter")
                self.assertFalse(result["results"] or result["closing_state"])
                self.assertNotIn("result_digest", result)
        package = merch.merchandising_reprice_package(fixture(), reference=self.reference)
        checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
        self.assertIn("0", [row["slot"] for row in inputs["evidence"]])
        inputs["evidence"][1]["id"] = inputs["evidence"][0]["id"]
        # Bypass descriptor uniqueness to observe the native source guard itself.
        binding = self.root / "duplicate-original-evidence-bindings.json"
        write_json(binding, {"inputs": inputs, "openings": openings})
        reference = normalize_target(evaluate(checked, inputs, openings).to_dict())
        native = normalize_target(interpret_schedule(self.folder / "merchandising-reprice.spl", binding))
        self.assertEqual(native["status"], reference["status"])
        self.assertEqual(native["diagnostics"][0]["code"], "MR_DUPLICATE_ID")
        self.assertFalse(native["emissions"] or native["closing"])
        data = fixture()
        for key in merch.ARRAYS:
            data[key].reverse()
        # Slots renumber original positions; all restored original state agrees.
        self.controls(data, self.run_fixture(data, "compare"))

    def test_reference_cb_qualification_default_and_unsupported_variants(self):
        changes = [("cb_switch", "complete", False), ("cb_switch", "prior_credit_total", "1"),
                   ("cb_switch", "receipt_ids", []), ("qualifications", "graphic_units", "24999"),
                   ("qualifications", "feature_released", False), ("policy", "method", "amend_and_catchup")]
        for group, key, value in changes:
            data = fixture()
            data[group][key] = value
            with self.subTest(group=group, key=key):
                self.blocked(data)
        data = fixture()
        data["no_default"][-1]["not_in_material_default"] = False
        self.blocked(data)

    def test_reference_zero_nonqualifying_empty_and_fractional_current_cash(self):
        for amount in ["0", "1", "1/3"]:
            data = fixture()
            data["receipts"][-1]["amount"] = amount
            population(data)["receipt_total"] = str(30000 + Fraction(amount))
            self.controls(data, self.run_fixture(data))
        data = fixture()
        data["receipts"][-1]["qualifying"] = False
        self.controls(data, self.run_fixture(data))
        data = fixture()
        data["receipts"].pop()
        population(data)["receipt_ids"].remove("license-q3")
        population(data)["receipt_total"] = "30000"
        self.controls(data, self.run_fixture(data))

    def test_reference_original_cutoffs_populations_scope_and_source_order(self):
        for kind in ["historical", "evidence", "scope", "population", "bank", "application"]:
            data = fixture()
            if kind == "historical": data["receipts"][0]["observed_at"] = "2006-05-01T00:00:00Z"
            elif kind == "evidence": next(row for row in data["evidence"] if row["id"] == "license-q1-evidence")["observed_at"] = "2006-05-01T00:00:00Z"
            elif kind == "scope": data["receipts"][-1]["scope"]["asset_id"] = "other-picture"
            elif kind == "population": population(data)["payment_total"] = "0"
            elif kind == "bank": data["payments"][-1]["bank_disbursement_id"] = data["payments"][0]["bank_disbursement_id"]
            else:
                data["applications"][-1]["amount"] = "909"
                population(data)["application_total"] = "1309"
            with self.subTest(kind=kind): self.blocked(data)

    def test_reference_original_history_cannot_be_forged_or_retimed(self):
        for kind in ["recognized", "raw", "issuance"]:
            data = fixture()
            if kind == "recognized": data["opening_state"]["recognized_rows"][0]["amount"] = "400"
            elif kind == "raw": data["opening_state"]["sources"]["receipts"][0]["amount"] = "9999"
            else: data["issues"][0].update(issued_date="2006-04-02", observed_at="2006-04-02T12:00:00Z")
            with self.subTest(kind=kind): self.blocked(data)
        data = fixture()
        for key in merch.ARRAYS: data[key].reverse()
        self.controls(data, self.run_fixture(data))

    def test_adapter_transports_only_original_facts_and_rejects_solved_inputs(self):
        source = (ROOT / "cases/merchandising-reprice/build_modules.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith("oracles") for name in imports))
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"sum", "min", "max", "merchandising_reprice"})
        for key in ["catchup", "target_entitlement", "withholding_rate"]:
            data = fixture()
            data[key] = "0.1"
            with self.assertRaisesRegex(ValueError, "MR_RECORD_FIELDS"):
                merch.merchandising_reprice_package(data, reference=self.reference)
        data = fixture()
        data["opening_state"]["recognized_rows"][0]["unrecognized_extra_field"] = "400"
        with self.assertRaisesRegex(ValueError, "MR_RECORD_FIELDS"):
            merch.merchandising_reprice_package(data, reference=self.reference)
        data = fixture()
        data["receipts"][-1]["receipt_ref"] = "not-an-artifact-line"
        with self.assertRaisesRegex(ValueError, "MR_ORIGINAL_LINE_REFERENCE"):
            merch.merchandising_reprice_package(data, reference=self.reference)
        for name in ["merchandising-reprice.spl", "build_modules.py"]:
            self.assertNotIn(b"\r", (ROOT / "cases/merchandising-reprice" / name).read_bytes())
