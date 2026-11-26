"""Independent original-fact controls for the registered within-vintage slice."""
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
from oracles.basis_reserves import BasisReserveOracleError, basis_reserves
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import DataError, digest, exact, read_json, write_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT, interpret_schedule
from spl_compiler.modules import resolve_module, validate_module_package
from spl_compiler.run import carry_state, normalize_target
from Tests.test_basis_reserve_oracle import original_facts, view, chain, replace_amount, second_return

reserves = import_module("cases.basis-reserves.build_modules")


def supplied(facts, index):
    """A separately labeled oracle-controlled HISTORICAL opening fixture only."""
    if index == 0:
        return view(facts, index)
    previous = chain({**deepcopy(facts), "checkpoints": deepcopy(facts["checkpoints"][:index])})[-1]
    data = view(facts, index, previous)
    data.pop("prior_result")
    data["opening_state"]["origin"] = "supplied_history"
    return data


def single_spanning_receipt(day="2009-04-30", end="2009-11-01"):
    """Original date/observation/control mutation; no due date is supplied."""
    data = view(original_facts(), 0)
    cp = data["checkpoints"][0]
    cp.update(as_of="2009-10-31", cutoff="2009-11-03T00:00:00Z", observed_at="2009-11-02T00:00:00Z")
    cp["period"]["end"] = end
    receipt, election = data["receipts"][0], data["elections"][0]
    receipt.update(receipt_date=day, observed_at="2009-09-02T00:00:00Z")
    election.update(election_date=day, approved_date=day, observed_at="2009-09-01T00:00:00Z")
    for key in ["populations", "clearances"]:
        data[key][0]["observed_at"] = "2009-11-02T12:00:00Z"
    for row in data["evidence"]:
        if row["id"] in {cp["evidence_ref"], data["populations"][0]["evidence_ref"], data["clearances"][0]["evidence_ref"]}:
            row["observed_at"] = "2009-11-02T00:00:00Z"
        elif row["id"] == receipt["evidence_ref"]:
            row["observed_at"] = receipt["observed_at"]
        elif row["id"] == election["evidence_ref"]:
            row["observed_at"] = election["observed_at"]
    return data


class BasisReserveModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/br-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/basis-reserves"
        cls.folder.mkdir(parents=True)
        for name in ["basis-reserves.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/basis-reserves" / name, cls.folder / name)
        for owner, key, value in [(reserves, "ROOT", cls.root), (reserves, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            change = patch.object(owner, key, value)
            change.start()
            cls.addClassCleanup(change.stop)
        cls.reference = reserves.register_basis_reserves()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None, mode="final"):
        package = reserves.basis_reserve_package(data, reference=self.reference, state_cells=cells, mode=mode)
        result = reserves.run_basis_reserve_package(package, self.root, backend=backend, artifact_dir=output)
        if backend == "compare" and result.get("trace_origin") == "native_ir_interpreter":
            checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
            expected = normalize_target(evaluate(checked, inputs, openings).to_dict())
            emitted = normalize_target(run_generated(checked,
                {key: decode_value(value, checked.types[key]) for key, value in inputs.items()},
                {key: decode_value(value, checked.types[key]) for key, value in openings.items()}))
            for field in ["status", "emissions", "closing"]:
                self.assertEqual(emitted[field], expected[field], field)
            self.assertEqual([row["code"] for row in emitted["diagnostics"]], [row["code"] for row in expected["diagnostics"]])
        if output is not None:
            self.assertEqual(load_completed_result(output), result)
            self.assertEqual(read_json(Path(output) / "result.json"), result)
            if not hasattr(self, "completed_paths"):
                self.completed_paths = {}
            if "result_digest" in result:
                self.completed_paths[result["result_digest"]] = Path(output)
        return result

    def same(self, actual, expected):
        if type(expected) in {Fraction, int}:
            self.assertEqual(Fraction(actual) if isinstance(actual, (str, int)) else exact(actual), expected)
        elif isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key, value in expected.items():
                with self.subTest(field=key): self.same(actual[key], value)
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected): self.same(left, right)
        else:
            self.assertEqual(actual, expected)

    def controls(self, data, result, *, preview=False):
        expected = basis_reserves(data)
        self.assertEqual(result["status"], "provisional" if preview else "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        values = result["results"]
        comparison = reserves.neutral_value(values["comparison"])
        self.same(comparison, {key: expected[key] for key in comparison})
        for key in ["checkpoint_results", "vintages", "movements"]:
            self.same(reserves.neutral_value(values[key]), expected[key])
        if preview:
            self.assertFalse(result["closing_state"])
            with self.assertRaises(DataError) as blocked: carry_state(result)
            self.assertEqual(blocked.exception.code, "NONCONSUMABLE_STATE")
        else:
            self.assertEqual(len(result["closing_state"]), 1)
            self.same(reserves.neutral_state(result["closing_state"][0]["quantity"]), expected["closing_state"])
        self.assertTrue(values["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertEqual(comparison["payment_status"], "not_assessed_no_bank_payment_measure")
        self.assertFalse({"paid", "payable", "bank_refund"} & comparison.keys())
        return expected

    def blocked(self, data, backend="reference", *, output=None):
        with self.assertRaises(BasisReserveOracleError): basis_reserves(data)
        result = self.run_fixture(data, backend, output=output)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
        self.assertNotIn("result_digest", result)
        return result

    def carried(self, data, previous):
        before = digest(previous)
        data = deepcopy(data)
        path = self.root / "actual-reserve-state.json"
        write_json(path, previous["closing_state"])
        cells = read_json(path)
        for cell in cells: cell.pop("movement", None)
        self.assertEqual(cells, [{key: value for key, value in cell.items() if key != "movement"} for cell in previous["closing_state"]])
        opening = reserves.neutral_state(cells[0]["quantity"])
        data["opening_state"] = opening
        data["prior_result"] = {"source_case_id": opening["source_case_id"], "period": previous["results"]["comparison"]["period"],
            "closing_state": deepcopy(opening), "result_ref": cells[0]["prior_result_ref"]}
        self.assertEqual(digest(previous), before)
        self.assertEqual(load_completed_result(self.completed_paths[previous["result_digest"]]), previous)
        return data, cells

    def test_native_actual_five_period_carry_and_full_original_reconciliation(self):
        facts = original_facts()
        prior = None
        for index in range(5):
            data = view(facts, index)
            data, cells = self.carried(data, prior) if prior else (data, None)
            result = self.run_fixture(data, "compare", cells=cells, output=self.root / ("period-" + str(index)))
            expected = self.controls(data, result)
            self.assertEqual(expected["net_receipts"], [800, 640, 0, 140, 160][index])
            if index == 0:
                self.assertEqual((expected["fee"], expected["allocation"]), (80, 720))
                self.assertNotEqual((expected["fee"], expected["allocation"]), (100, 700))
            prior = result
        self.assertEqual([expected["cumulative"][key] for key in ["gross", "applied_returns", "net_receipts", "fee", "allocation"]], [1800, 60, 1740, 174, 1566])
        self.assertNotEqual(expected["cumulative"]["net_receipts"], 1680)
        self.assertEqual([row["released"] for row in expected["vintages"]], [140, 160])
        missing = deepcopy(data); missing.pop("prior_result")
        self.blocked(missing)
        wrong = deepcopy(data); wrong["prior_result"]["source_case_id"] = "other-predecessor"
        self.blocked(wrong)

    def test_native_positive_non_election_zero_empty_and_exact_fraction(self):
        facts = original_facts(); facts["elections"][0]["elected"] = False
        result = self.controls(view(facts, 0), self.run_fixture(view(facts, 0), "compare"))
        self.assertEqual((result["added"], result["net_receipts"], result["fee"], result["allocation"]), (0, 1000, 100, 900))
        for amount in ["0", "1/3"]:
            facts = original_facts(); replace_amount(facts, "receipts", "receipt:1", amount)
            self.controls(view(facts, 0), self.run_fixture(view(facts, 0), "compare"))
        data = view(original_facts(), 0)
        data["receipts"] = []; data["elections"] = []
        data["populations"][0].update(receipt_ids=[], election_ids=[], receipt_total="0")
        self.controls(data, self.run_fixture(data, "compare"))

    def test_native_calendar_deadline_clamp_spanning_window_and_text_id_bijection(self):
        data = single_spanning_receipt()
        identity = "receipt:" + chr(0x96EA) + "#original:part"
        vintage = "V:" + chr(0x96EA) + "#original:part"
        data["receipts"][0]["id"] = identity
        data["elections"][0].update(receipt_id=identity, vintage_id=vintage)
        data["populations"][0]["receipt_ids"] = [identity]
        result = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual(result["vintages"][0]["due_date"], "2009-10-30")
        self.assertEqual(result["vintages"][0]["release_ids"], ["due-release:" + vintage])
        self.assertEqual([row["id"] for row in result["movements"]], ["addition:" + identity, "due-release:" + vintage])
        data = single_spanning_receipt("2009-08-31")
        result = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual(result["vintages"][0]["due_date"], "2010-02-28")
        self.assertEqual(result["released"], 0)

    def test_native_day_before_due_and_derived_releases_inside_later_window(self):
        facts = original_facts()
        facts["checkpoints"][3].update(as_of="2009-07-14")
        facts["checkpoints"][3]["period"]["end"] = "2009-07-15"
        facts["checkpoints"][4]["period"]["start"] = "2009-07-15"
        for index, released in [(3, 0), (4, 300)]:
            data = supplied(facts, index)
            result = self.controls(data, self.run_fixture(data, "compare"))
            self.assertEqual(result["released"], released)

    def test_native_due_date_return_precedes_release_and_exact_remaining_return(self):
        facts = original_facts()
        facts["returns"][0].update(return_date="2009-07-15", observed_at="2009-07-15T13:00:00Z")
        facts["return_authorities"][0].update(approved_date="2009-07-15", observed_at="2009-07-15T12:00:00Z")
        for row in facts["evidence"]:
            for fact in [facts["returns"][0], facts["return_authorities"][0]]:
                if row["id"] == fact["evidence_ref"]: row["observed_at"] = fact["observed_at"]
        facts["populations"][2].update(return_ids=[], authority_ids=[], return_total="0")
        data = supplied(facts, 3)
        result = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((result["applied_returns"], result["released"]), (60, 140))
        self.assertEqual([row["kind"] for row in result["movements"]], ["matched_actual_return", "calculated_due_unused_release"])
        facts = original_facts(); second_return(facts, "140")
        data = supplied(facts, 3)
        result = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((result["applied_returns"], result["released"]), (140, 0))

    def test_native_excess_nonborrow_and_after_liquidation_remain_unsupported(self):
        for kind in ["excess", "borrow", "after", "non_elected"]:
            facts = original_facts(); index = 2
            if kind == "excess": replace_amount(facts, "returns", "return:1", "201")
            elif kind == "borrow": second_return(facts, "150"); index = 3
            elif kind == "after": second_return(facts, "1", "2009-10-15"); index = 4
            else: facts["elections"][0]["elected"] = False
            with self.subTest(kind=kind):
                result = self.blocked(supplied(facts, index), "compare")
                self.assertEqual(result.get("trace_origin"), "native_ir_interpreter")
                self.assertIn(result["diagnostics"][0]["code"], ["BR_EXCESS_RETURN_VARIANT_REQUIRED", "BR_RETURN_AFTER_LIQUIDATION_VARIANT_REQUIRED"])

    def test_native_population_clearance_unknown_and_positive_claims_block_atomically(self):
        for kind in ["missing", "false", "clearance", "claim"]:
            data = view(original_facts(), 0)
            if kind == "missing": data["populations"] = []
            elif kind == "false": data["populations"][0]["complete"] = False
            elif kind == "clearance": data["clearances"] = []
            else: data["clearances"][0]["expense_remaining"] = "1"
            with self.subTest(kind=kind):
                result = self.blocked(data, "compare", output=self.root / ("blocked-" + kind))
                self.assertNotIn("paid", result)
                self.assertNotIn("net_receipts", result)

    def test_native_complete_checkpoint_preview_has_no_consumable_state(self):
        data = supplied(original_facts(), 4)
        result = self.run_fixture(data, "compare", mode="preview", output=self.root / "preview")
        expected = self.controls(data, result, preview=True)
        self.assertEqual(expected["cumulative"]["net_receipts"], 1740)
        self.assertEqual(expected["allocation"], 144)

    def test_native_evidence_slots_validate_original_refs_after_adapter(self):
        for kind in ["unknown", "misbound", "duplicate", "range", "unused_bad"]:
            package = reserves.basis_reserve_package(view(original_facts(), 0), reference=self.reference)
            evidence = package["evidence"]["evidence"]
            if kind == "unknown": package["inputs"]["receipts"][0]["evidence_slot"] = "-1"
            elif kind == "misbound":
                original = package["inputs"]["receipts"][0]["evidence_ref"]
                package["inputs"]["receipts"][0]["evidence_slot"] = next(row["slot"] for row in evidence if row["id"] != original)
            elif kind == "duplicate": evidence[0]["slot"] = evidence[1]["slot"]
            elif kind == "range": evidence[0]["slot"] = str(len(evidence))
            else: evidence[-1]["approved"] = False
            with self.subTest(kind=kind):
                result = reserves.run_basis_reserve_package(package, self.root, backend="compare")
                self.assertEqual(result["status"], "blocked", result["diagnostics"])
                self.assertEqual(result.get("trace_origin"), "native_ir_interpreter")
                self.assertFalse(result["results"] or result["closing_state"])
        package = reserves.basis_reserve_package(view(original_facts(), 0), reference=self.reference)
        checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
        self.assertIn("0", [row["slot"] for row in inputs["evidence"]])
        inputs["evidence"][1]["id"] = inputs["evidence"][0]["id"]
        path = self.root / "duplicate-evidence.json"
        write_json(path, {"inputs": inputs, "openings": openings})
        actual = normalize_target(interpret_schedule(self.folder / "basis-reserves.spl", path))
        self.assertEqual(actual["diagnostics"][0]["code"], "BR_DUPLICATE_ID")
        self.assertFalse(actual["emissions"] or actual["closing"])
        data = view(original_facts(), 0)
        data["receipts"][0]["amount"] = "1000.00"
        data["evidence"][0]["observed_at"] = "2009-01-16T23:59:59.999999999999Z"
        for key in reserves.ARRAYS: data[key].reverse()
        self.controls(data, self.run_fixture(data, "compare"))

    def test_native_cash_alias_claim_alias_sequence_and_unknown_vintage(self):
        for kind in ["cash_alias", "claim_alias", "sequence", "vintage"]:
            facts = original_facts(); index = 2
            if kind == "cash_alias": facts["receipts"][1]["cash_line_ref"] = facts["receipts"][0]["cash_line_ref"]; index = 1
            elif kind in ["claim_alias", "sequence"]:
                second_return(facts, "10", "2009-05-15")
                if kind == "claim_alias": facts["returns"][-1]["claim_id"] = facts["returns"][0]["claim_id"]
            else: facts["returns"][0]["vintage_id"] = "unknown-vintage"
            with self.subTest(kind=kind): self.blocked(supplied(facts, index), "compare")

    def test_reference_scope_purpose_original_authority_and_cutoff_controls(self):
        for kind in ["scope", "purpose", "authority", "future", "old", "election"]:
            facts = original_facts(); index = 0
            if kind == "scope": facts["receipts"][0]["scope"]["asset_id"] = "other"
            elif kind == "purpose": facts["elections"][0]["purpose"] = "other"
            elif kind == "authority": facts["authority"]["fee_rate"] = "1/5"
            elif kind == "future": facts["evidence"][0]["observed_at"] = facts["checkpoints"][0]["cutoff"]
            elif kind == "old":
                data = supplied(facts, 4); data["receipts"][0]["observed_at"] = "2009-02-01T00:00:00Z"
                self.blocked(data); continue
            else: facts["elections"][0]["approved"] = False
            with self.subTest(kind=kind): self.blocked(view(facts, index))

    def test_reference_actual_opening_pins_overdue_and_missing_authorities(self):
        for kind in ["amount", "raw", "overdue", "unused", "unknown"]:
            facts = original_facts(); data = supplied(facts, 4)
            if kind == "amount": data["opening_state"]["vintages"][1]["available"] = "161"
            elif kind == "raw": data["opening_state"]["sources"]["receipts"][0]["amount"] = "1001"
            elif kind == "overdue": data["opening_state"]["vintages"][0]["available"] = "1"
            elif kind == "unused": data["return_authorities"][0]["return_id"] = "unknown"
            else: data["returns"][0]["authority_id"] = "unknown"
            with self.subTest(kind=kind): self.blocked(data)
        facts = original_facts()
        data = supplied(facts, 4)
        data["evidence"][0]["observed_at"] = "2009-10-16T23:59:59.999999999999Z"
        # Its original historic evidence is intentionally pinned; retiming old
        # evidence cannot be smuggled into a later opening.
        self.blocked(data)

    def test_reference_original_order_and_complete_population_reconciliation(self):
        data = supplied(original_facts(), 4)
        for key in reserves.ARRAYS: data[key].reverse()
        self.controls(data, self.run_fixture(data))
        data = view(original_facts(), 0)
        data["populations"][0]["receipt_total"] = "999"
        self.blocked(data)
        data = view(original_facts(), 0)
        data["populations"][0]["receipt_ids"].append(data["receipts"][0]["id"])
        self.blocked(data)

    def test_adapter_only_transports_originals_and_source_derives_calendar(self):
        source = (ROOT / "cases/basis-reserves/build_modules.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith("oracles") for name in imports))
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"sum", "min", "max", "basis_reserves", "add_calendar_months", "_add_six_months"})
        for key in ["release_amount", "net_receipts", "due_date"]:
            data = view(original_facts(), 0)
            data["receipts"][0][key] = "200"
            with self.assertRaisesRegex(ValueError, "BR_RECORD_FIELDS"):
                reserves.basis_reserve_package(data, reference=self.reference)
        self.assertIn("add_calendar_months(row.receipt_date, 6, policy.invalid_day)", (ROOT / "cases/basis-reserves/basis-reserves.spl").read_text())
        for name in ["basis-reserves.spl", "build_modules.py"]:
            self.assertNotIn(b"\r", (ROOT / "cases/basis-reserves" / name).read_bytes())
