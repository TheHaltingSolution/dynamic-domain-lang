"""Canonical fixed-term methods against independent original-population controls."""
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
from oracles.term_guarantees import TermGuaranteeOracleError, exact_json, term_guarantees
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import exact, read_json, write_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import resolve_module, validate_module_package
from spl_compiler.run import normalize_target
from Tests.test_term_guarantee_oracle import fixture, extend_term, successor

terms = import_module("cases.term-guarantees.build_modules")


class TermGuaranteeModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/term-guarantee-module-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/term-guarantees"
        cls.folder.mkdir(parents=True)
        for name in ["term-guarantees.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/term-guarantees" / name, cls.folder / name)
        for owner, name, value in [(terms, "ROOT", cls.root), (terms, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = terms.register_term_guarantees()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        package = terms.term_guarantee_package(data, reference=self.reference, state_cells=cells)
        result = terms.run_term_guarantee_package(package, self.root, backend=backend, artifact_dir=output)
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
        expected = term_guarantees(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        values = result["results"]
        self.same(values["comparison"], {key: expected[key] for key in values["comparison"]})
        closing = terms.neutral_state(result["closing_state"][0]["quantity"])
        self.assertEqual(closing, exact_json(expected["closing_state"]))
        current_facts = expected["closing_state"]["period_history"][-1]
        self.assertEqual(terms.neutral_value(values["current_facts"]), exact_json({key: current_facts[key] for key in ["earnings", "fundings"]}))
        history = expected["closing_state"]["period_history"]
        self.assertEqual(len(values["period_replays"]), len(history))
        previous = None
        for record, replay in zip(history, values["period_replays"]):
            d = deepcopy(data)
            d.pop("prior_result", None)
            d.update(case_id=record["source_case_id"], period=deepcopy(record["period"]),
                     earnings=exact_json(record["earnings"]), fundings=exact_json(record["fundings"]))
            if previous is None:
                d["opening_state"] = exact_json({**expected["closing_state"], "origin": "genesis", "source_case_id": "genesis",
                    "boundary": record["period"]["start"], **{key: "0" for key in terms.MONEY_METERS}, "term_closed": False, "period_history": []})
            else:
                d["opening_state"] = exact_json(previous["closing_state"])
                d["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
            previous = term_guarantees(d)
            self.same(replay["opening_meters"], previous["opening_meters"])
            self.same(replay["stages"], {key: previous[key] for key in replay["stages"]})
            self.assertEqual(replay["source_case_id"], record["source_case_id"])
            self.assertEqual(replay["period"], record["period"])
            self.assertEqual(replay["funding_population_status"], previous["funding_population_status"])
        self.assertTrue(values["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertEqual(values["comparison"]["settlement_payment_evidence_status"], "no_event_supplied")
        self.assertNotIn("actual_paid", values["comparison"])
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None, output=None):
        with self.assertRaises(TermGuaranteeOracleError):
            term_guarantees(data)
        result = self.run_fixture(data, backend, cells=cells, output=output)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code)
        for field in ["results", "detail", "statements", "closing_state"]:
            self.assertFalse(result[field])
        self.assertNotIn("result_digest", result)
        return result

    def carried(self, original, previous, earned="40", funding=None):
        data = successor(term_guarantees(original), original, earned, funding)
        path = self.root / "serialized-actual-term-history.json"
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = terms.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        return data, [cell]

    def test_native_all_seven_methods_and_every_stage(self):
        expected = {"term_cap": (80, 0, 80, 0), "term_floor_at_end": (100, 0, 100, 0),
            "actual_funded_advance": (80, 80, 0, 70), "floor_cap_advance_including_topup": (90, 90, 0, 60),
            "floor_cap_advance_earned_only": (90, 80, 10, 70), "cap_floor_advance_including_topup": (100, 100, 0, 50),
            "cap_floor_advance_earned_only": (100, 80, 20, 70)}
        for method, controls in expected.items():
            with self.subTest(method=method), tempfile.TemporaryDirectory(dir=self.root) as output:
                data = fixture(method)
                result = self.run_fixture(data, "compare", output=output)
                self.controls(data, result)
                c = result["results"]["comparison"]
                self.assertEqual(tuple(exact(c[key]) for key in ["entitlement", "recovered", "payable_calculated"]) + (exact(c["closing_meters"]["prepayment"]),), controls)
                self.assertTrue(result["verification"]["reference_agrees"])
                self.assertTrue((Path(output) / "typed-ir.json").is_file())
                self.assertTrue((Path(output) / "Settlement.lean").is_file())
                self.assertEqual(read_json(Path(output) / "result.json"), result)
                self.assertEqual(load_completed_result(output), result)

    def test_native_actual_interim_floor40_final60_and_nonreset_cap60_40(self):
        for method, amount, expected in [("term_floor_at_end", "40", ("40", "60")), ("term_cap", "60", ("60", "40"))]:
            original = fixture(method, earned=amount)
            extend_term(original)
            first = self.run_fixture(original, "compare")
            self.controls(original, first)
            data, cells = self.carried(original, first, earned=amount)
            second = self.run_fixture(data, "compare", cells=cells)
            self.controls(data, second)
            self.assertEqual((first["results"]["comparison"]["entitlement"], second["results"]["comparison"]["entitlement"]), expected)
            self.assertTrue(second["results"]["comparison"]["closing_meters"]["term_closed"])

    def test_native_actual_funding100_then50_and_six_meter_replay(self):
        original = fixture(earned="80", funding="100", face="150")
        extend_term(original)
        first = self.run_fixture(original, "compare")
        self.controls(original, first)
        data, cells = self.carried(original, first, earned="40", funding="50")
        second = self.run_fixture(data, "compare", cells=cells)
        self.controls(data, second)
        c = second["results"]["comparison"]
        self.assertEqual((first["results"]["comparison"]["closing_meters"]["prepayment"], c["new_actual_funding"], c["available_prepayment"], c["recovered"], c["closing_meters"]["prepayment"]), ("20", "50", "70", "40", "30"))
        self.assertEqual((c["closing_meters"]["total_funded"], c["closing_meters"]["total_recovered"]), ("150", "120"))

    def test_native_floor_meter_counts_entitlement_before_advance_recovery(self):
        original = fixture("cap_floor_advance_including_topup", earned="40", funding="100", floor="100", cap="200", face="100")
        extend_term(original)
        first = self.run_fixture(original, "compare")
        self.controls(original, first)
        data, cells = self.carried(original, first, earned="40")
        second = self.run_fixture(data, "compare", cells=cells)
        self.controls(data, second)
        c = second["results"]["comparison"]
        self.assertEqual((c["floor_topup_before_cap"], c["entitlement"], c["recovered"], c["payable_calculated"]), ("20", "60", "60", "0"))

    def test_native_floor_cap_precedence_with_funded50(self):
        for method, entitlement, payable, consumed, unmet in [
                ("floor_cap_advance_including_topup", "90", "40", "90", "10"),
                ("cap_floor_advance_including_topup", "100", "50", "80", "0")]:
            data = fixture(method, funding="50")
            result = self.run_fixture(data, "compare")
            self.controls(data, result)
            c = result["results"]["comparison"]
            self.assertEqual((c["entitlement"], c["payable_calculated"], c["closing_meters"]["term_cap_consumed"], c["unmet_floor_at_term_end"]), (entitlement, payable, consumed, unmet))

    def test_native_complete_empty_and_missing_population_are_distinct(self):
        data = fixture(funding=None, face="150")
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual((result["results"]["comparison"]["funding_population_status"], result["results"]["comparison"]["payable_calculated"]), ("complete_no_events", "80"))
        for funding in [None, "150"]:
            data = fixture(funding=funding)
            data["evidence"] = [row for row in data["evidence"] if row["kind"] != "complete_funding_population"]
            with tempfile.TemporaryDirectory(dir=self.root) as output:
                result = self.blocked(data, "TERM_FUNDING_POPULATION_REQUIRED", "compare", output=output)
                self.assertEqual(result["funding_evidence_status"], "no_event_supplied")
                self.assertEqual(read_json(Path(output) / "result.json"), result)
                self.assertEqual(load_completed_result(output), result)
                self.assertNotIn("actual_paid", result)

    def test_native_fractional_amount_and_original_offset_funding_utc_date(self):
        data = fixture(earned="1/3", funding="1/7")
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(exact(result["results"]["comparison"]["payable_calculated"]), Fraction(4, 21))
        data = fixture()
        period = {"start": "2026-04-01", "end": "2026-07-01"}
        data.update(period=period, as_of="2026-06-30", cutoff="2026-07-03T00:00:00Z")
        data["term"]["period"] = deepcopy(period)
        data["term"]["observed_at"] = "2025-12-30T01:00:00+01:00"
        data["opening_state"].update(boundary=period["start"], term=deepcopy(data["term"]))
        data["earnings"][0].update(effective_date="2026-05-15", amount="80.00")
        data["fundings"][0].update(funded_date="2026-06-30", funded_at="2026-07-01T00:30:00+01:00", observed_at="2026-07-02T00:00:00.000Z")
        data["evidence"][2]["observed_at"] = "2026-07-02T00:00:00Z"
        data["evidence"][3].update(period=deepcopy(period), observed_at="2026-07-02T12:00:00Z")
        self.controls(data, self.run_fixture(data, "compare"))

    def test_native_population_drop_wrong_utc_and_unfunded_approval_are_atomic(self):
        for code, change in [("TERM_FUNDING_POPULATION_CONTROL", lambda d: d.update(fundings=[])),
                ("TERM_FUNDED_UTC_DATE", lambda d: d["fundings"][0].update(funded_date="2026-01-11")),
                ("TERM_ACTUAL_FUNDING_REQUIRED", lambda d: d["fundings"][0].update(approved=False))]:
            data = fixture()
            change(data)
            result = self.blocked(data, code, "compare")
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_reference_actual_predecessor_term_method_scope_and_meters_pinned(self):
        original = fixture(funding="100", face="150")
        extend_term(original)
        first = self.run_fixture(original)
        for change in [lambda d: d["opening_state"].update(method="term_cap"),
                       lambda d: d["term"].update(recoupable_minimum_face="200"),
                       lambda d: d["term"].update(source_ref="amended-source"),
                       lambda d: d["opening_state"].update(purpose="reserve"),
                       lambda d: d["prior_result"]["period"].update(end="2026-03-31"),
                       lambda d: d.pop("prior_result")]:
            data, cells = self.carried(original, first)
            change(data)
            self.blocked(data, cells=cells)
        for meter in terms.MONEY_METERS:
            data, cells = self.carried(original, first)
            data["opening_state"][meter] = "999"
            data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
            self.blocked(data, "TERM_OPENING_SNAPSHOT", cells=cells)
        data, cells = self.carried(original, first)
        data["prior_result"]["result_ref"] = "result@sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "TERM_CANONICAL_PREDECESSOR_MISMATCH"):
            self.run_fixture(data, cells=cells)

    def test_reference_populations_history_duplicates_scope_and_source_aliases(self):
        for field in ["earnings", "fundings", "evidence"]:
            data = fixture()
            data[field].append(deepcopy(data[field][0]))
            self.blocked(data)
        for change in [lambda d: d["fundings"].append({**deepcopy(d["fundings"][0]), "id": "aliased-id", "source_ref": "other-source"}),
                       lambda d: d["fundings"][0]["scope"].update(pool_id="outside"),
                       lambda d: d["evidence"][2].update(kind="planned_funding"),
                       lambda d: d["evidence"][3].update(funding_ids=[]),
                       lambda d: d["fundings"][0].update(amount="100"),
                       lambda d: d["fundings"][0].update(observed_at=d["cutoff"])]:
            data = fixture()
            change(data)
            self.blocked(data)
        original = fixture(funding="100", face="150")
        extend_term(original)
        first = self.run_fixture(original)
        data, cells = self.carried(original, first)
        data["evidence"] = [row for row in data["evidence"] if row["id"] != "complete-q1"]
        result = self.blocked(data, "TERM_FUNDING_POPULATION_REQUIRED", cells=cells)
        self.assertEqual(result["funding_evidence_status"], "no_event_supplied")
        data, cells = self.carried(original, first, funding="50")
        data["fundings"][0]["disbursement_id"] = original["fundings"][0]["disbursement_id"]
        self.blocked(data, "TERM_DISBURSEMENT_ALREADY_RECOGNIZED", cells=cells)
        data, cells = self.carried(original, first)
        data["earnings"][0]["id"] = "earned-q1"
        self.blocked(data, "TERM_EARNING_ALREADY_RECOGNIZED", cells=cells)

    def test_reference_nonadvance_zero_empty_term_end_and_permutation(self):
        data = fixture("term_floor_at_end")
        data["earnings"] = []
        result = self.run_fixture(data)
        self.controls(data, result)
        self.assertEqual(result["results"]["comparison"]["entitlement"], "100")
        data = fixture("term_cap", earned="0", cap="0")
        self.controls(data, self.run_fixture(data))
        data = fixture("term_cap")
        data["fundings"] = deepcopy(fixture()["fundings"])
        self.blocked(data, "TERM_ADVANCE_OUTSIDE_METHOD")
        data = fixture()
        first = self.run_fixture(data)
        self.controls(data, first)
        for field in ["evidence", "earnings", "fundings"]:
            data[field].reverse()
        second = self.run_fixture(data)
        self.controls(data, second)
        self.assertEqual(first["results"], second["results"])
        self.assertEqual(first["closing_state"][0]["quantity"], second["closing_state"][0]["quantity"])

    def test_adapter_only_transports_sources_and_explicit_utc_metadata(self):
        tree = ast.parse((ROOT / "cases/term-guarantees/build_modules.py").read_text(encoding="utf-8"))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertFalse(any(name.startswith("oracles") for name in imports))
        package = terms.term_guarantee_package(fixture(), reference=self.reference)
        self.assertFalse({"entitlement", "recovered", "payable_calculated", "closing_meters", "period_replays"} & package["inputs"].keys())
        self.assertEqual(package["inputs"]["fundings"][0]["funded_utc_date"], "2026-01-10")
        for amount in [0.1, True, "-1", "1e2"]:
            data = fixture()
            data["earnings"][0]["amount"] = amount
            with self.assertRaisesRegex(ValueError, "TERM_EXACT_NONNEGATIVE_VALUE"):
                self.run_fixture(data)


if __name__ == "__main__":
    unittest.main()
