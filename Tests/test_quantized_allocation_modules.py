"""Registered parent-first allocation against immutable original-fact controls.

Native-named tests request compare explicitly; other groups are reference or
physical shape checks. Helpers are imported without reexporting oracle tests.
"""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import importlib
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from oracles.quantized_allocation import QuantizedAllocationOracleError, exact_json, quantized_allocation
from spl_compiler.codecs import digest, exact, read_json, write_json
from spl_compiler.lean_tools import ROOT
from Tests.test_quantized_allocation_oracle import fixture, supplied, successor

allocation = importlib.import_module("cases.quantized-allocation.build_modules")
OBSERVATIONS = []


def eight_recipients(data):
    recipient, term = deepcopy(data["recipient_registry"][0]), deepcopy(data["authorities"][0]["terms"][0])
    data["recipient_registry"] = []
    data["authorities"][0]["terms"] = []
    for index in range(8):
        identity = "R" + str(index)
        data["recipient_registry"].append({**deepcopy(recipient), "id": identity, "source_ref": "synthetic-recipient-" + identity})
        data["authorities"][0]["terms"].append({**deepcopy(term), "id": "weight-" + identity, "recipient_id": identity, "source_ref": "synthetic-weight-" + identity})
    data["opening_state"]["recipient_registry"] = deepcopy(data["recipient_registry"])
    data["authorities"][0]["recipient_ids"] = [row["id"] for row in data["recipient_registry"]]
    return data


class QuantizedAllocationModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Keep complete canonical closure filenames below Windows MAX_PATH.
        parent = ROOT / ".lake/qam"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/quantized-allocation"
        cls.folder.mkdir(parents=True)
        for name in ("allocation.spl", "quantized-allocation.spl", "policy.md", "neutral.json"):
            shutil.copyfile(ROOT / "cases/quantized-allocation" / name, cls.folder / name)
        for owner, name, value in ((allocation, "ROOT", cls.root), (allocation, "FOLDER", cls.folder), (registration, "ROOT", cls.root)):
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = allocation.register_quantized_allocation()
        cls.native_runs = 0

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        # Author the complete original-fact control before adapter projection.
        try:
            control = exact_json(quantized_allocation(data))
        except QuantizedAllocationOracleError as error:
            control = {"blocked": str(error)}
        if backend == "compare" and output is None:
            type(self).native_runs += 1
            output = self.root / ("native-" + str(type(self).native_runs))
        package = allocation.quantized_allocation_package(data, reference=self.reference, state_cells=cells)
        result = allocation.run_quantized_allocation_package(package, self.root, backend=backend, artifact_dir=output)
        OBSERVATIONS.append({"backend": backend, "original": deepcopy(data), "original_fact_control": control, "package": package,
                             "result": {key: deepcopy(value) for key, value in result.items() if key != "trace"},
                             "trace_node_count": len(result.get("trace", [])), "artifact_dir": str(output) if output else None})
        return result

    def same(self, actual, expected):
        if isinstance(expected, Fraction) or type(expected) is int:
            self.assertEqual(actual if type(actual) is int else exact(actual), expected)
        elif isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key, value in expected.items():
                with self.subTest(field=key):
                    self.same(actual[key], value)
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for observed, wanted in zip(actual, expected):
                self.same(observed, wanted)
        else:
            self.assertEqual(actual, expected)

    def controls(self, data, result):
        expected = quantized_allocation(data)
        self.assertEqual(result["status"], "calculated", result.get("diagnostics"))
        self.assertEqual(result["diagnostics"], [])
        self.same(result["results"]["comparison"], {key: value for key, value in expected.items() if key not in {"allocations", "closing_state"}})
        self.same(result["results"]["allocations"], expected["allocations"])
        self.assertEqual(allocation.neutral_state(result["closing_state"][0]["quantity"]), exact_json(expected["closing_state"]))
        self.assertTrue(result["results"]["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None):
        with self.assertRaises(QuantizedAllocationOracleError):
            quantized_allocation(data)
        result = self.run_fixture(data, backend, cells=cells)
        self.assertEqual(result["status"], "blocked", result.get("diagnostics"))
        self.assertTrue(result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code, result["diagnostics"])
        for field in ("results", "statements", "detail", "closing_state"):
            self.assertFalse(result[field], field)
        return result

    def carried(self, previous_data, previous, amount="0.03"):
        data = successor(quantized_allocation(previous_data), previous_data, amount)
        path = self.root / "actual-parent-state.json"
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = allocation.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        return data, [cell]

    def test_native_parent_first_fractional_quota_and_single_cent(self):
        for data in (fixture(), fixture("0.015", ("1", "2"))):
            with self.subTest(amount=data["parents"][0]["amount"]), tempfile.TemporaryDirectory(dir=self.root) as output:
                result = self.run_fixture(data, "compare", output=output)
                self.controls(data, result)
                self.assertTrue(result["verification"]["reference_agrees"])
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")
                self.assertTrue((Path(output) / "typed-ir.json").is_file())
                self.assertTrue((Path(output) / "Settlement.lean").is_file())
                self.assertEqual(result["result_digest"], digest({key: value for key, value in result.items() if key != "result_digest"}))

    def test_native_half_even_original_parents_round_separately(self):
        data = fixture("0.005")
        for index, amount in enumerate(("0.015", "0.025", "0.035"), 2):
            parent = {**deepcopy(data["parents"][0]), "id": "parent-" + str(index), "amount": amount, "source_ref": "synthetic-parent-" + str(index), "upstream_ref": "synthetic:ledger#line-" + str(index), "authority_id": "authority-" + str(index)}
            authority = {**deepcopy(data["authorities"][0]), "id": parent["authority_id"], "parent_id": parent["id"], "parent_upstream_ref": parent["upstream_ref"]}
            data["parents"].append(parent); data["authorities"].append(authority)
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual([exact(row["target_cents"]) for row in result["results"]["allocations"]], [2, 2, 4, 0])

    def test_native_supplied_authority_is_distinct_from_weights(self):
        data = fixture(); supplied(data)
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        children = result["results"]["allocations"][0]["children"]
        self.assertEqual([row["selected_amount"] for row in children], ["0", "0.01"])
        self.assertEqual([row["weighted_amount"] for row in children], ["0.01", "0"])

    def test_native_eight_recipient_residual_and_ascii_tie_permutation(self):
        data = eight_recipients(fixture("0.03"))
        data["recipient_registry"].reverse(); data["authorities"][0]["terms"].reverse(); data["authorities"][0]["recipient_ids"].reverse()
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual([row["selected_amount"] for row in result["results"]["allocations"][0]["children"]], ["0.01"] * 3 + ["0"] * 5)

    def test_native_exact_fraction_weights_and_case_sensitive_identity(self):
        data = fixture("0.07", ("1/3", "1/6"))
        data["recipient_registry"][1]["id"] = "a"
        data["opening_state"]["recipient_registry"] = deepcopy(data["recipient_registry"])
        data["authorities"][0]["recipient_ids"] = ["a", "X"]
        data["authorities"][0]["terms"][1]["recipient_id"] = "a"
        self.controls(data, self.run_fixture(data, "compare"))
        data = fixture(); data["recipient_registry"][1]["id"] = "a"; data["opening_state"]["recipient_registry"] = deepcopy(data["recipient_registry"])
        data["authorities"][0]["recipient_ids"] = ["a", "X"]; data["authorities"][0]["terms"][1]["recipient_id"] = "a"
        result = self.run_fixture(data)
        self.controls(data, result)
        self.assertEqual(result["results"]["allocations"][0]["ranked_recipient_ids"], ["X", "a"])

    def test_native_actual_adjacent_carry_preserves_original_lexemes_and_sources(self):
        data = fixture("0.0100", ("1.00", "1/1"))
        data["cutoff"] = "2026-04-03T01:00:00.0000000000000001+01:00"
        data["parents"][0]["observed_at"] = "2026-02-02T01:00:00+01:00"
        first = self.run_fixture(data, "compare")
        self.controls(data, first)
        following, cells = self.carried(data, first)
        second = self.run_fixture(following, "compare", cells=cells)
        self.controls(following, second)
        restored = allocation.neutral_state(second["closing_state"][0]["quantity"])
        self.assertEqual(restored["history"][0]["parents"][0]["amount"], "0.0100")
        self.assertEqual(restored["history"][0]["parents"][0]["observed_at"], data["parents"][0]["observed_at"])
        self.assertEqual(restored["consumed_parent_ids"], ["parent-q1", "parent-q2"])
        self.assertEqual(second["results"]["comparison"]["child_allocation_total"], "0.03")

    def test_native_business_errors_leave_no_finance_or_state(self):
        zero = fixture("0", ("0", "0"))
        missing = fixture(); missing["authorities"][0]["recipient_ids"].pop()
        unapproved = fixture(); unapproved["authorities"][0]["approved"] = False
        for data, code in ((zero, "QA_ZERO_WEIGHT_DENOMINATOR"), (missing, "QA_COMPLETE_RECIPIENTS"), (unapproved, "QA_AUTHORITY_ASOF")):
            with self.subTest(code=code):
                result = self.blocked(data, code, "compare")
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_native_empty_and_zero_parent_are_explicit(self):
        zero = fixture("0", ("0", "1"))
        empty = fixture(); empty["parents"] = []; empty["authorities"] = []
        for data in (zero, empty):
            self.controls(data, self.run_fixture(data, "compare"))

    def test_native_supplied_minor_unit_and_exact_cutoff_fail_atomically(self):
        cents = fixture(); supplied(cents, ("0.005", "0.005"))
        cutoff = fixture(); cutoff["parents"][0]["observed_at"] = cutoff["cutoff"]
        for data, code in ((cents, "QA_SUPPLIED_MINOR_UNIT"), (cutoff, "QA_FACT_CUTOFF")):
            self.blocked(data, code, "compare")

    def test_reference_all_parent_half_even_ties_and_zero(self):
        for amount, weights in (("0.005", ("1", "1")), ("0.015", ("1", "1")), ("0.025", ("1", "1")), ("0.035", ("1", "1")), ("0", ("0", "1")), ("2", ("1", "3"))):
            data = fixture(amount, weights)
            self.controls(data, self.run_fixture(data))

    def test_reference_empty_parent_population_is_explicit_zero(self):
        data = fixture(); data["parents"] = []; data["authorities"] = []
        result = self.run_fixture(data)
        self.controls(data, result)
        self.assertEqual(result["results"]["allocations"], [])
        data["recipient_registry"] = []; data["opening_state"]["recipient_registry"] = []
        self.blocked(data, "QA_RECIPIENT_BOUND")

    def test_reference_supplied_cents_integrality_completeness_and_conservation(self):
        for amounts, code in ((("0.005", "0.005"), "QA_SUPPLIED_MINOR_UNIT"), (("0.01", "0.01"), "QA_SUPPLIED_TARGET_CONSERVATION")):
            data = fixture(); supplied(data, amounts); self.blocked(data, code)
        data = fixture(); supplied(data); data["authorities"][0]["supplied_allocation_ids"].pop()
        self.blocked(data)
        data = fixture(); supplied(data); data["supplied_allocations"][1]["recipient_id"] = "X"
        self.blocked(data, "QA_SUPPLIED_RECIPIENT_REFERENCE")

    def test_reference_unmatched_authority_and_supplied_populations_block(self):
        data = fixture(); supplied(data); data["policy"]["method"] = data["authorities"][0]["method"] = "exact_weights_largest_remainder"; data["opening_state"]["policy"] = deepcopy(data["policy"])
        self.blocked(data)
        data["authorities"][0]["supplied_allocation_ids"] = []
        self.blocked(data, "QA_UNMATCHED_SUPPLIED_ALLOCATION")
        data = fixture(); data["authorities"].append({**deepcopy(data["authorities"][0]), "id": "unused"})
        self.blocked(data, "QA_AUTHORITY_CARDINALITY")

    def test_reference_complete_recipient_and_weight_registry(self):
        for mutate in (lambda d: d["authorities"][0]["recipient_ids"].append("X"), lambda d: d["authorities"][0]["terms"].pop(), lambda d: d["authorities"][0]["terms"][1].update(recipient_id="Z"), lambda d: d["authorities"][0]["terms"][1].update(recipient_id="X")):
            data = fixture(); mutate(data); self.blocked(data)

    def test_reference_original_parent_alias_and_ids_cannot_be_reconsumed(self):
        data = fixture()
        parent = {**deepcopy(data["parents"][0]), "id": "alias", "source_ref": "new-label", "authority_id": "alias-authority"}
        authority = {**deepcopy(data["authorities"][0]), "id": "alias-authority", "parent_id": "alias"}
        data["parents"].append(parent); data["authorities"].append(authority)
        self.blocked(data, "QA_PARENT_SOURCE_ALREADY_CONSUMED")
        data = fixture(); first = self.run_fixture(data); following, cells = self.carried(data, first)
        following["parents"][0]["upstream_ref"] = data["parents"][0]["upstream_ref"]
        following["authorities"][0]["parent_upstream_ref"] = following["parents"][0]["upstream_ref"]
        self.blocked(following, "QA_PARENT_SOURCE_ALREADY_CONSUMED", cells=cells)

    def test_reference_scope_cutoff_authorization_and_parent_period(self):
        for mutate in (lambda d: d["parents"][0].update(observed_at=d["cutoff"]), lambda d: d["authorities"][0].update(approved=False), lambda d: d["parents"][0].update(effective_date=d["period"]["end"]), lambda d: d["authorities"][0]["scope"].update(pool_id="other"), lambda d: d["evidence"].pop()):
            data = fixture(); mutate(data); self.blocked(data)
        data = fixture(); data["as_of"] = "2025-12-31"; self.blocked(data, "QA_AUTHORITY_ASOF")
        data = fixture(); data["parents"][0]["observed_at"] = "2026-04-02T23:59:59.999999999999Z"
        self.controls(data, self.run_fixture(data))

    def test_reference_policy_registry_predecessor_and_historical_cutoff_pins(self):
        data = fixture(); first = self.run_fixture(data)
        following, cells = self.carried(data, first)
        following["policy"]["method"] = "authorized_supplied_cents"
        self.blocked(following, "QA_PINNED_TERMS", cells=cells)
        following, cells = self.carried(data, first)
        next(row for row in following["evidence"] if row["id"] == "parent-source")["observed_at"] = "2026-05-01T00:00:00Z"
        self.blocked(following, "QA_EVIDENCE_REQUIRED", cells=cells)
        following, cells = self.carried(data, first)
        following["opening_state"]["consumed_parent_ids"] = []
        following["prior_result"]["closing_state"] = deepcopy(following["opening_state"])
        cells[0]["quantity"] = allocation._state(following["opening_state"])
        self.blocked(following, "QA_OPENING_HISTORY_RECONCILIATION", cells=cells)

    def test_physical_adapter_rejects_solved_fields_nonexact_negative_and_nonascii(self):
        for amount in ("-0.01", 0.01):
            with self.assertRaisesRegex(ValueError, "QA_EXACT_NONNEGATIVE_VALUE"):
                allocation.quantized_allocation_package(fixture(amount), reference=self.reference)
        data = fixture(); data["parents"][0]["solved_target"] = "0.01"
        with self.assertRaisesRegex(ValueError, "QA_RECORD_FIELDS"):
            allocation.quantized_allocation_package(data, reference=self.reference)
        for identity in ("\u00e9", "_X", "X" * 65):
            data = fixture(); data["recipient_registry"][0]["id"] = identity
            with self.assertRaisesRegex(ValueError, "QA_ASCII_ID"):
                allocation.quantized_allocation_package(data, reference=self.reference)

    def test_reference_adapter_does_not_compute_or_import_solved_controls(self):
        source = (ROOT / "cases/quantized-allocation/build_modules.py").read_text(encoding="utf-8")
        self.assertNotIn("from oracles", source)
        data = fixture("0.015", ("1", "2"))
        package = allocation.quantized_allocation_package(data, reference=self.reference)
        self.assertEqual(package["inputs"]["parents"][0]["amount_source"], "0.015")
        self.assertEqual(package["inputs"]["authorities"][0]["terms"][1]["weight_source"], "2")
        self.assertFalse({"rank", "residual_cents", "quota", "rounded_target"} & set(package["inputs"]["parents"][0]))
        self.controls(data, self.run_fixture(data))

    def test_reference_four_parent_bound_and_ninth_historical_opening_boundary(self):
        data = fixture()
        for index in range(2, 6):
            parent = {**deepcopy(data["parents"][0]), "id": "parent-" + str(index), "authority_id": "authority-" + str(index), "source_ref": "synthetic-parent-" + str(index), "upstream_ref": "synthetic:ledger#line-" + str(index)}
            authority = {**deepcopy(data["authorities"][0]), "id": parent["authority_id"], "parent_id": parent["id"], "parent_upstream_ref": parent["upstream_ref"]}
            data["parents"].append(parent); data["authorities"].append(authority)
        self.blocked(data, "QA_PARENT_BOUND")
        data = fixture(); data["parents"] = []; data["authorities"] = []
        previous = self.run_fixture(data)
        self.controls(data, previous)
        for index in range(2, 11):
            cell = deepcopy(previous["closing_state"][0]); cell.pop("movement")
            following = deepcopy(data)
            start = date.fromisoformat(data["period"]["end"])
            end = date(start.year + (start.month == 10), 1 if start.month == 10 else start.month + 3, 1)
            following.update(case_id="empty-close-" + str(index), period={"start": start.isoformat(), "end": end.isoformat()}, as_of=(end - timedelta(days=1)).isoformat(), cutoff=end.isoformat() + "T00:00:01Z")
            following["opening_state"] = allocation.neutral_state(cell["quantity"])
            following["prior_result"] = {"source_case_id": data["case_id"], "period": deepcopy(data["period"]), "closing_state": deepcopy(following["opening_state"]), "result_ref": cell["prior_result_ref"]}
            if index == 10:
                self.blocked(following, "QA_HISTORY_BOUND", cells=[cell])
            else:
                previous = self.run_fixture(following, cells=[cell])
                self.controls(following, previous)
                self.assertEqual(len(previous["closing_state"][0]["quantity"]["history"]), index)
                data = following
