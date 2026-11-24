"""Five explicit canonical escalation methods versus independent original facts."""
import ast
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.escalation import build_modules as escalation_module
from cases.r1 import build_modules as registration
from oracles.escalation import EscalationOracleError, escalation, exact_json
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import exact, read_json, write_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.run import normalize_target
from Tests.test_escalation_oracle import fixture, genesis, with_predecessor, replace_events, METHOD_RESULTS


class EscalationModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/escalation-module-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/escalation"
        cls.folder.mkdir(parents=True)
        for name in ["escalation.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/escalation" / name, cls.folder / name)
        for owner, name, value in [(escalation_module, "ROOT", cls.root), (escalation_module, "FOLDER", cls.folder),
                                   (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = escalation_module.register_escalation()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        package = escalation_module.escalation_package(data, reference=self.reference, state_cells=cells)
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
        expected = escalation(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        values = result["results"]
        self.same(values["comparison"], {key: expected[key] for key in values["comparison"]})
        self.same(escalation_module.neutral_value(values["rows"]), expected["rows"])
        self.assertEqual(escalation_module.neutral_state(result["closing_state"][0]["quantity"]), exact_json(expected["closing_state"]))
        histories = expected["closing_state"]["period_history"]
        self.assertEqual(len(values["period_replays"]), len(histories))
        # Independently execute each original historical prefix, including every
        # row's selected rate/slices and recognized-before/after intermediates.
        for index, (record, replay) in enumerate(zip(histories, values["period_replays"])):
            d = deepcopy(data)
            d.pop("prior_result", None)
            d.update(case_id=record["source_case_id"], period=deepcopy(record["period"]), events=exact_json(record["events"]))
            d["opening_state"] = exact_json({**expected["closing_state"], "boundary": record["period"]["start"],
                "origin": "genesis" if index == 0 else "supplied_history", "source_case_id": "genesis" if index == 0 else histories[index - 1]["source_case_id"],
                "cumulative_basis": record["opening_basis"], "recognized_entitlement": record["opening_recognized"], "period_history": histories[:index]})
            oracle_replay = escalation(d)
            self.same(escalation_module.neutral_value(replay), {key: oracle_replay[key] for key in replay})
        self.assertTrue(values["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertFalse({"actual_paid", "issued", "payable"} & values["comparison"].keys())
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None):
        with self.assertRaises(EscalationOracleError):
            escalation(data)
        result = self.run_fixture(data, backend, cells=cells)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code)
        for field in ["results", "detail", "statements", "closing_state"]:
            self.assertFalse(result[field])
        return result

    def carried(self, original, previous):
        data = with_predecessor(escalation(original))
        path = self.root / "serialized-actual-escalation-history.json"
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = escalation_module.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        return data, [cell]

    def test_native_all_five_distinct_original_baselines(self):
        for method, expected in METHOD_RESULTS.items():
            with self.subTest(method=method), tempfile.TemporaryDirectory(dir=self.root) as output:
                data = fixture(method)
                result = self.run_fixture(data, "compare", output=output)
                self.controls(data, result)
                self.assertEqual(exact(result["results"]["comparison"]["current_result"]), expected)
                self.assertTrue(result["verification"]["reference_agrees"])
                self.assertTrue((Path(output) / "typed-ir.json").is_file())
                self.assertTrue((Path(output) / "Settlement.lean").is_file())
                self.assertEqual(read_json(Path(output) / "result.json"), result)
                self.assertEqual(load_completed_result(output), result)

    def test_native_actual_genesis80_then_adjacent_period_for_all_methods(self):
        for method, expected in METHOD_RESULTS.items():
            with self.subTest(method=method):
                original = genesis(method)
                first = self.run_fixture(original, "compare")
                self.controls(original, first)
                self.assertEqual(first["results"]["comparison"]["current_result"], "8")
                data, cells = self.carried(original, first)
                second = self.run_fixture(data, "compare", cells=cells)
                self.controls(data, second)
                self.assertEqual(exact(second["results"]["comparison"]["current_result"]), expected)
                self.assertEqual(len(second["closing_state"][0]["quantity"]["period_history"]), 2)

    def test_native_lower_inclusive_threshold_distinguishes_marginal_and_ending(self):
        for method, expected in [("prospective_split", "10"), ("row_ending_rate", "20")]:
            data = genesis(method, ("100",))
            result = self.run_fixture(data, "compare")
            self.controls(data, result)
            self.assertEqual(result["results"]["comparison"]["current_result"], expected)
            self.assertEqual(exact(result["results"]["comparison"]["ending_rate"]), Fraction(1, 5))

    def test_native_original_sequence_changes_whole_row_rates(self):
        data = fixture("row_opening_rate")
        data["events"][0]["sequence"], data["events"][1]["sequence"] = 2, 1
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(result["results"]["comparison"]["current_result"], "10")
        self.assertEqual([row["basis"] for row in result["results"]["rows"]], ["40", "30"])

    def test_native_raw_offset_timestamp_lineage_and_actual_carry(self):
        original = genesis()
        original["bracket_table"]["observed_at"] = "2025-09-29T19:00:00-05:00"
        original["opening_state"]["bracket_table"] = deepcopy(original["bracket_table"])
        original["events"][0]["observed_at"] = "2025-11-16T00:00:00.000Z"
        first = self.run_fixture(original, "compare")
        self.controls(original, first)
        neutral = escalation_module.neutral_state(first["closing_state"][0]["quantity"])
        self.assertEqual(neutral["bracket_table"]["observed_at"], original["bracket_table"]["observed_at"])
        self.assertEqual(neutral["period_history"][0]["events"][0]["observed_at"], original["events"][0]["observed_at"])
        data, cells = self.carried(original, first)
        data["bracket_table"] = deepcopy(data["opening_state"]["bracket_table"])
        data["events"][0]["observed_at"] = "2026-03-11T01:00:00+01:00"
        second = self.run_fixture(data, "compare", cells=cells)
        self.controls(data, second)
        cutoff_data = deepcopy(data)
        cutoff_data["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        cutoff_data["events"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        self.controls(cutoff_data, self.run_fixture(cutoff_data, "compare", cells=cells))
        cutoff_data["events"][0]["observed_at"] = cutoff_data["cutoff"]
        self.blocked(cutoff_data, "ESCALATION_FACT_CUTOFF", cells=cells)
        data["bracket_table"]["observed_at"] = "2025-09-30T00:00:00Z"
        # Exact same Instant, different original table text: ordinary amendment.
        self.blocked(data, "ESCALATION_BRACKET_AMENDMENT", cells=cells)

    def test_native_exact_fractional_width_and_reprice_subtracts_once(self):
        data = fixture()
        replace_events(data, ("1/3",))
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(exact(result["results"]["comparison"]["current_result"]), Fraction(1, 30))
        data = fixture("cumulative_reprice_delta")
        result = self.run_fixture(data)
        self.controls(data, result)
        self.assertEqual([row["current_result"] for row in result["results"]["rows"]], ["14", "8"])
        self.assertEqual(result["results"]["comparison"]["current_result"], "22")

    def test_native_invalid_partition_history_and_consumed_original_are_atomic(self):
        for code, change in [
                ("ESCALATION_BRACKET_PARTITION", lambda d: d["bracket_table"]["brackets"][1].update(lower="101")),
                ("ESCALATION_HISTORY_RECONCILIATION", lambda d: d["opening_state"]["period_history"][0].update(current_result="9")),
                ("ESCALATION_EVENT_ALREADY_RECOGNIZED", lambda d: d["events"][0].update(id="basis-original-80"))]:
            data = fixture()
            change(data)
            with self.subTest(code=code):
                result = self.blocked(data, code, "compare")
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_reference_partition_laws_are_method_specific(self):
        expected = {"prospective_split": (12, 12), "current_period_ending_rate": (14, 14),
                    "row_opening_rate": (7, 7), "row_ending_rate": (14, 13), "cumulative_reprice_delta": (22, 22)}
        for method, amounts in expected.items():
            for events, amount in zip([("70",), ("10", "60")], amounts):
                data = fixture(method)
                replace_events(data, events)
                result = self.run_fixture(data)
                self.controls(data, result)
                self.assertEqual(exact(result["results"]["comparison"]["current_result"]), amount)

    def test_reference_zero_empty_original_lexemes_and_permutation_replay(self):
        for method in METHOD_RESULTS:
            for amounts in [(), ("0",)]:
                data = fixture(method)
                replace_events(data, amounts)
                result = self.run_fixture(data)
                self.controls(data, result)
                self.assertEqual(result["results"]["comparison"]["current_result"], "0")
        data = fixture()
        data["bracket_table"]["brackets"][0].update(lower="0.00", upper="100.0", rate="0.10")
        data["opening_state"]["bracket_table"] = deepcopy(data["bracket_table"])
        data["opening_state"]["period_history"][0].update(current_result="8.0", closing_recognized="8.00")
        data["events"][0]["basis"] = "30.00"
        first = self.run_fixture(data)
        self.controls(data, first)
        for field in ["events", "evidence"]:
            data[field].reverse()
        data["bracket_table"]["brackets"].reverse()
        second = self.run_fixture(data)
        self.controls(data, second)
        self.assertEqual(first["results"], second["results"])
        self.assertEqual(first["closing_state"][0]["quantity"], second["closing_state"][0]["quantity"])

    def test_reference_scope_evidence_cutoff_asof_and_fixed_table_availability(self):
        for change in [lambda d: d["events"][0]["scope"].update(pool_id="outside"),
                       lambda d: d["evidence"][0]["scope"].update(pool_id="outside"),
                       lambda d: d["events"][0].update(observed_at=d["cutoff"]),
                       lambda d: d["events"][0].update(effective_date=d["period"]["end"]),
                       lambda d: d.update(as_of="2025-09-29")]:
            data = fixture()
            change(data)
            self.blocked(data)
        for change in [lambda t: t.update(observed_at="2025-10-01T00:00:00Z"),
                       lambda t: t.update(recorded_date="2025-10-02"),
                       lambda t: t["effective"].update(start="2025-10-02")]:
            data = fixture()
            change(data["bracket_table"])
            data["opening_state"]["bracket_table"] = deepcopy(data["bracket_table"])
            self.blocked(data)
        data = fixture()
        data["as_of"] = "2025-09-30"
        self.controls(data, self.run_fixture(data))

    def test_reference_full_history_table_method_and_actual_predecessor_are_pinned(self):
        original = genesis()
        first = self.run_fixture(original)
        for change in [lambda d: d["policy"].update(method="row_ending_rate"),
                       lambda d: d["bracket_table"]["brackets"][1].update(rate="0.25"),
                       lambda d: d["bracket_table"]["brackets"][1].update(source_ref="amended-source"),
                       lambda d: d["bracket_table"].update(version="2"),
                       lambda d: d["opening_state"].update(period_history=[]),
                       lambda d: d["prior_result"]["period"].update(end="2025-12-31"),
                       lambda d: d.pop("prior_result")]:
            data, cells = self.carried(original, first)
            change(data)
            self.blocked(data, cells=cells)
        data, cells = self.carried(original, first)
        data["prior_result"]["result_ref"] = "result@sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "ESCALATION_CANONICAL_PREDECESSOR_MISMATCH"):
            self.run_fixture(data, cells=cells)

    def test_reference_brackets_identities_sources_and_order_are_validated(self):
        for change in [lambda d: d["events"].append(deepcopy(d["events"][0])),
                       lambda d: d["events"][1].update(sequence=1),
                       lambda d: d["events"][0].update(source_ref="synthetic-original-basis80"),
                       lambda d: d["bracket_table"]["brackets"][1].update(upper="200"),
                       lambda d: d["bracket_table"]["brackets"][1].update(rate="0.05"),
                       lambda d: d["bracket_table"]["brackets"][1].update(rate="1.1"),
                       lambda d: d["bracket_table"].update(brackets=[])]:
            data = fixture()
            change(data)
            self.blocked(data)

    def test_adapter_transports_no_solved_finance_and_pins_exact_source_numbers(self):
        tree = ast.parse((ROOT / "cases/escalation/build_modules.py").read_text(encoding="utf-8"))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertFalse(any(name.startswith("oracles") for name in imports))
        package = escalation_module.escalation_package(fixture(), reference=self.reference)
        self.assertFalse({"ending_rate", "rows", "period_basis", "current_result", "period_replays"} & package["inputs"].keys())
        self.assertEqual(package["inputs"]["opening_utc"], "2026-01-01T00:00:00Z")
        for value in [30.0, True, "3e1", "-1"]:
            data = fixture()
            data["events"][0]["basis"] = value
            with self.assertRaisesRegex(ValueError, "ESCALATION_EXACT_NONNEGATIVE_VALUE"):
                self.run_fixture(data)


if __name__ == "__main__":
    unittest.main()
