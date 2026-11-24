"""Original-fact controls for the separately authored native burden source."""
import ast
from copy import deepcopy
from fractions import Fraction
from importlib import import_module
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from oracles.contract_burdens import ContractBurdenOracleError, contract_burdens, exact_json
from spl_compiler.artifacts import ArtifactPublication, PublicationError, load_completed_result
from spl_compiler.audited_artifacts import AuditedPublication, load_completed_audited_result
from spl_compiler.codecs import DataError, digest, file_digest, read_json, write_json
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.compact_execution import _compiler_inputs, _stage, _verify_pins, metadata, WORKER
from spl_compiler.model import encode_value
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.run import carry_state, normalize_target
from Tests.test_contract_burden_oracle import fixture, paid_method, remove_payments, successor, accounts, add_supported

burdens = import_module("cases.entitlement-burdens.build_modules")


def completed_result(path):
    """Select only an explicitly recognized completed-publication loader."""
    from spl_compiler.artifacts import _read_bounded, _strict_json, MAX_MANIFEST_BYTES, PublicationError
    marker = _strict_json(_read_bounded(Path(path) / "completion.json", MAX_MANIFEST_BYTES))
    if type(marker) is not dict:
        raise PublicationError("UNSUPPORTED_COMPLETION_FORMAT")
    if marker.get("format") == "spl-artifact-publication/1":
        return load_completed_result(path)
    if marker.get("format") == "spl-artifact-publication/2":
        return load_completed_audited_result(path)
    raise PublicationError("UNSUPPORTED_COMPLETION_FORMAT")


def graph_fixture():
    data = fixture()
    third = deepcopy(data["accounts"][1]); third["id"] = "third"
    third["scope"] = {key: "USD" if key == "currency" else value.replace("burdened", "third") for key, value in third["scope"].items()}
    data["accounts"].append(add_supported(data, third, "account_scope", ["third"]))
    term = deepcopy(data["terms"][1]); term.update(id="terms:third", account_id="third", scope=third["scope"], original_ref="original-contract#third")
    data["terms"].append(add_supported(data, term, "participation_terms", ["third"]))
    receipt = deepcopy(data["receipts"][1]); receipt.update(id="receipt:third:q1", account_id="third", scope=third["scope"], amount="600", term_id=term["id"], original_ref="original-receipts#third", entitlement_line_ref="participation#third")
    data["receipts"].append(add_supported(data, receipt, "original_receipt_basis", ["third"]))
    population = deepcopy(data["receipt_populations"][1]); population.update(id="population:third", account_id="third", scope=third["scope"], receipt_ids=[receipt["id"]], gross_total="600")
    data["receipt_populations"].append(add_supported(data, population, "complete_receipt_population", ["third"]))
    authority = deepcopy(data["authorizations"][0]); authority.update(id="authority:second", claimant_account="burdened", burdened_account="third", claimant_scope=data["accounts"][1]["scope"], burdened_scope=third["scope"], sequence=2, burden_rate="0.1", cap="30", original_ref="original-authority#second")
    data["authorizations"].append(add_supported(data, authority, "cross_contract_authority", ["burdened", "third"]))
    request = deepcopy(data["requests"][0]); request.update(id="request:second", authorization_id=authority["id"], claimant_account="burdened", burdened_account="third", claimant_scope=authority["claimant_scope"], burdened_scope=third["scope"], basis_receipt_ids=[data["receipts"][1]["id"]], original_ref="original-request#second")
    data["requests"].append(add_supported(data, request, "original_burden_request", ["burdened", "third"]))
    return data


class ContractBurdenModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/burden-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/entitlement-burdens"
        cls.folder.mkdir(parents=True)
        for name in ["entitlement-burdens.spl", "neutral.json", "policy.md"]:
            shutil.copyfile(ROOT / "cases/entitlement-burdens" / name, cls.folder / name)
        for owner, key, value in [(burdens, "ROOT", cls.root), (burdens, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            changed = patch.object(owner, key, value)
            changed.start(); cls.addClassCleanup(changed.stop)
        cls.reference = burdens.register_entitlement_burdens()
        cls.transport_sequence = 0

    def next_work(self, kind):
        type(self).transport_sequence += 1
        work = self.root / kind / str(type(self).transport_sequence)
        work.mkdir(parents=True)
        return work

    def python_emitter_control(self, checked, inputs, openings):
        """Unmodified independent emission; compiler/runtime budgets stay distinct."""
        work = self.next_work("p")
        source, c_file, obj, executable = (work / name for name in ("Candidate.lean", "Candidate.c", "Candidate.o", "Candidate.exe"))
        source.write_text(emit_module(checked,
            {key: decode_value(value, checked.types[key]) for key, value in inputs.items()},
            {key: decode_value(value, checked.types[key]) for key, value in openings.items()}), encoding="utf-8", newline="\n")
        toolbin, flags, libraries, pins = _compiler_inputs()
        response = work / "link.rsp"
        response.write_text("\n".join(json.dumps(arg) for arg in [str(obj), *libraries]), encoding="utf-8")
        write_json(work / "build-inputs.json", {"pins": pins, "source_sha256": file_digest(source),
                   "c_flags": flags, "link_arguments": libraries, "compiler_profile": "compiler1g180", "runtime_profile": "runtime256"})
        for name, command in [
            ("lean-codegen", [toolbin / "lean.exe", "-DwarningAsError=true", "-R", work, "-c", c_file, source]),
            ("c-object", [toolbin / "clang.exe", "-c", "-o", obj, c_file, *flags]),
            ("link", [toolbin / "clang.exe", "-o", executable, "@" + str(response)])]:
            _stage(command, work / name, compiler=True)
        outcome = metadata(_stage([executable], work / "execution"))
        _verify_pins(pins)
        return outcome

    def native_audit_control(self, binding):
        work = self.next_work("r")
        wire = _stage([ROOT / ".lake/build/bin/spl_audit.exe", self.folder / "entitlement-burdens.spl", binding,
                       work / "typed-ir.json", work / "Native.lean"], work / "audit")
        return metadata(_stage([sys.executable, WORKER, "validate", wire], work / "reader"))["head"]

    def run_fixture(self, data, backend="reference", *, cells=None, output=None, mode="final"):
        package = burdens.entitlement_burden_package(data, reference=self.reference, state_cells=cells, mode=mode)
        if backend == "compare" and output is None:
            output = self.next_work("n")
        result = burdens.run_entitlement_burden_package(package, self.root, backend=backend, artifact_dir=output,
            audit_profile="compact-v2" if backend == "compare" else "array-v1")
        if backend == "compare":
            self.assertEqual(result.get("trace_origin"), "native_ir_interpreter", result["diagnostics"])
            checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
            reference = evaluate(checked, inputs, openings)
            expected = {"status": reference.status, "emissions": encode_value(reference.emissions),
                        "closing": encode_value(reference.closing), "diagnostics": reference.diagnostics}
            emitted = normalize_target(self.python_emitter_control(checked, inputs, openings))
            for key in ["status", "emissions", "closing"]:
                self.assertEqual(emitted[key], expected[key], key)
            self.assertEqual([item["code"] for item in emitted["diagnostics"]], [item["code"] for item in expected["diagnostics"]])
        if output is not None:
            self.assertEqual(completed_result(output), result)
            self.assertEqual(read_json(Path(output) / "result.json"), result)
            if not hasattr(self, "locations"): self.locations = {}
            if "result_digest" in result: self.locations[result["result_digest"]] = output
        return result

    def controls(self, data, result, *, preview=False):
        expected = exact_json(contract_burdens(data))
        self.assertEqual(result["status"], "provisional" if preview else "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        actual = burdens.neutral_result(result["results"]["comparison"])
        self.assertEqual(actual, {key: value for key, value in expected.items() if key != "closing_state"})
        if preview:
            self.assertFalse(result["closing_state"])
            with self.assertRaises(DataError) as caught: carry_state(result)
            self.assertEqual(caught.exception.code, "NONCONSUMABLE_STATE")
        else:
            self.assertEqual(len(result["closing_state"]), 1)
            self.assertEqual(burdens.neutral_state(result["closing_state"][0]["quantity"]), expected["closing_state"])
        self.assertTrue(result["results"]["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertFalse(actual["bank_movement_created"])
        self.assertEqual(actual["reconciliation"], "adjusted_total_equals_original_total_minus_burdens")
        return actual

    def blocked(self, data, backend="reference", *, cells=None, output=None):
        with self.assertRaises(ContractBurdenOracleError): contract_burdens(data)
        result = self.run_fixture(data, backend, cells=cells, output=output)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
        self.assertNotIn("result_digest", result)
        return result

    def carried(self, original, previous, quarter):
        before = digest(previous)
        path = self.root / "serialized-closing.json"
        write_json(path, previous["closing_state"])
        cells = read_json(path)
        for cell in cells: cell.pop("movement", None)
        self.assertEqual(cells, [{key: value for key, value in row.items() if key != "movement"} for row in previous["closing_state"]])
        plain = burdens.neutral_result(previous["results"]["comparison"])
        plain["closing_state"] = burdens.neutral_state(cells[0]["quantity"])
        data = successor(original, plain, quarter)
        data["prior_result"]["result_ref"] = cells[0]["prior_result_ref"]
        self.assertEqual(digest(previous), before)
        self.assertEqual(completed_result(self.locations[previous["result_digest"]]), previous)
        return data, cells

    def test_native_baseline_and_linked_paid_are_distinct_original_measurements(self):
        for method, expected in [(fixture(), "170"), (paid_method(fixture()), "182")]:
            actual = self.controls(method, self.run_fixture(method, "compare", output=self.root / expected))
            a = accounts(actual)
            self.assertEqual((a["claimant"]["original_gross_basis"], a["claimant"]["original_accrued"], a["claimant"]["actual_paid"]), ("200", "100", "60"))
            self.assertEqual(a["burdened"]["adjusted_entitlement"], expected)
            self.assertEqual(a["claimant"]["adjusted_entitlement"], "100")
            self.assertEqual(actual["burden_details"][0]["claimant_credit_added"], "0")

    def test_native_actual_three_period_cap_carry_and_immutable_replay(self):
        original = fixture()
        data, cells, previous = original, None, None
        for quarter, applied, adjusted in [(1, "30", "170"), (2, "15", "185"), (3, "0", "200")]:
            if previous is not None: data, cells = self.carried(original, previous, quarter)
            result = self.run_fixture(data, "compare", cells=cells, output=self.root / ("q" + str(quarter)))
            actual = self.controls(data, result)
            self.assertEqual((actual["applied_burden_total"], accounts(actual)["burdened"]["adjusted_entitlement"]), (applied, adjusted))
            self.assertEqual(actual["burden_details"][0]["cap_excess_not_carried"], ["0", "15", "30"][quarter - 1])
            if quarter == 2:
                replay = self.run_fixture(deepcopy(data), "reference", cells=deepcopy(cells))
                self.assertEqual(replay["results"], result["results"])
                self.assertEqual(replay["closing_state"], result["closing_state"])
                forged = deepcopy(data)
                forged["opening_state"]["cap_usage"][0]["consumed"] = "0"
                # successor shares neutral predecessor/opening state: this
                # changes both coherently. Mechanical preparation must not
                # replace native financial replay of the forged cap usage.
                blocked = self.blocked(forged, "compare")
                self.assertEqual(blocked["diagnostics"][0]["code"], "BURDEN_OPENING_RECONCILIATION")
            previous = result
        self.assertEqual(len(burdens.neutral_state(previous["closing_state"][0]["quantity"])["history"]), 3)

    def test_native_unknown_payment_complete_empty_and_empty_originals(self):
        data = remove_payments(fixture())
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertIsNone(accounts(actual)["claimant"]["actual_paid"])
        self.assertEqual(accounts(actual)["claimant"]["payment_evidence_status"], "no_event_supplied")
        data = paid_method(data)
        result = self.blocked(data, "compare", output=self.root / "unknown-paid")
        self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
        data = paid_method(remove_payments(fixture(), complete_empty=True))
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((accounts(actual)["claimant"]["actual_paid"], actual["applied_burden_total"]), ("0", "0"))
        self.assertEqual(burdens.neutral_state(self.run_fixture(data)["closing_state"][0]["quantity"])["consumed"]["request_ids"], ["request:q1"])
        data = remove_payments(fixture(), complete_empty=True); data["receipts"] = []; data["requests"] = []
        for row in data["receipt_populations"]: row.update(receipt_ids=[], gross_total="0")
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((actual["original_entitlement_total"], actual["adjusted_entitlement_total"]), ("0", "0"))

    def test_native_exact_fraction_threshold_cap_and_availability_order(self):
        data = remove_payments(fixture(), complete_empty=True)
        data["receipts"][0]["amount"] = "2/3"; data["receipt_populations"][0]["gross_total"] = "2/3"
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((actual["burden_details"][0]["basis"], actual["applied_burden_total"]), ("1/3", "1/10"))
        for minimum, amount in [("100", "30"), ("100.0000000001", "0")]:
            data = fixture(); data["authorizations"][0]["minimum_basis"] = minimum
            self.assertEqual(self.controls(data, self.run_fixture(data, "compare"))["applied_burden_total"], amount)
        data = fixture(); data["authorizations"][0]["cap"] = "29"
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((actual["applied_burden_total"], actual["burden_details"][0]["cap_excess_not_carried"]), ("29", "1"))
        data = fixture(); data["receipts"][1]["amount"] = "40"; data["receipt_populations"][1]["gross_total"] = "40"
        self.blocked(data, "compare")
        data["authorizations"][0]["cap"] = "10"
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual((actual["applied_burden_total"], accounts(actual)["burdened"]["adjusted_entitlement"]), ("10", "10"))

    def test_native_original_pre_burden_dag_and_unused_cycle(self):
        data = graph_fixture()
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual([row["basis"] for row in actual["burden_details"]], ["100", "200"])
        self.assertEqual([row["applied"] for row in actual["burden_details"]], ["30", "20"])
        self.assertEqual(accounts(actual)["third"]["adjusted_entitlement"], "280")
        data = fixture(); reverse = deepcopy(data["authorizations"][0]); reverse.update(id="reverse", sequence=2, original_ref="authority#reverse", claimant_account="burdened", burdened_account="claimant", claimant_scope=data["accounts"][1]["scope"], burdened_scope=data["accounts"][0]["scope"])
        data["authorizations"].append(add_supported(data, reverse, "cross_contract_authority", ["claimant", "burdened"]))
        self.blocked(data, "compare")

    def test_native_unicode_original_identity_offset_lexemes_and_permutation(self):
        data = remove_payments(fixture(), complete_empty=True)
        first = deepcopy(data["receipts"][0]); second = deepcopy(first)
        first.update(id="Ã©", amount="100.00", original_ref="original#Ã©", entitlement_line_ref="participation#Ã©")
        second.update(id="e\u0301", amount="100", original_ref="original#e\u0301", entitlement_line_ref="participation#e\u0301")
        data["receipts"] = [first, second, data["receipts"][1]]
        data["receipt_populations"][0]["receipt_ids"] = ["Ã©", "e\u0301"]; data["requests"][0]["basis_receipt_ids"] = ["Ã©", "e\u0301"]
        raw = "2026-04-01T17:00:00.0000000001-07:00"
        data["requests"][0]["observed_at"] = raw
        actual = self.controls(data, self.run_fixture(data, "compare"))
        self.assertEqual(actual["burden_details"][0]["request"]["observed_at"], raw)
        for key in burdens.ARRAYS: data[key].reverse()
        self.assertEqual(actual, self.controls(data, self.run_fixture(data, "compare")))
        # Genuine inner endpoint identities may also contain delimiters/Unicode.
        data = fixture()
        old, new = "agreement-claimant", "å¥‘ç´„:e\u0301:# claimant"
        def replace(value):
            if isinstance(value, dict): return {key: replace(item) for key, item in value.items()}
            if isinstance(value, list): return [replace(item) for item in value]
            return new if value == old else value
        data = replace(data)
        self.controls(data, self.run_fixture(data, "reference"))

    def test_native_raw_binding_slots_and_original_references_are_checked(self):
        for kind in ["unknown", "misbound", "duplicate", "range", "unused_bad", "duplicate_id", "old_codec", "old_raw_profile", "old_raw_layout", "old_ports_profile", "raw_population", "case_population", "raw_period"]:
            package = burdens.entitlement_burden_package(fixture(), reference=self.reference)
            frame = package["inputs"]["frames"][0]
            raw_tables = package["inputs"]["original_frames"][0]["originals"]
            if kind == "unknown": frame["receipts"][0]["evidence_slot"] = "-1"
            elif kind == "misbound": frame["receipts"][0]["evidence_slot"] = frame["accounts"][0]["evidence_slot"]
            elif kind == "duplicate":
                frame["evidence"][0]["slot"] = frame["evidence"][1]["slot"]
                raw_tables["evidence"][0]["slot"] = frame["evidence"][0]["slot"]
            elif kind == "range":
                frame["evidence"][0]["slot"] = str(len(frame["evidence"]))
                raw_tables["evidence"][0]["slot"] = frame["evidence"][0]["slot"]
            elif kind == "duplicate_id":
                frame["evidence"][1]["id"] = frame["evidence"][0]["id"]
                raw_tables["evidence"][1]["id"] = frame["evidence"][1]["id"]
            elif kind == "raw_population": raw_tables["receipts"][0]["id"] = burdens.encode_identity("wrong raw original")
            elif kind == "case_population": package["inputs"]["original_frames"][0]["id"] = burdens.encode_identity("wrong source case")
            elif kind == "raw_period": package["inputs"]["original_frames"][0]["period"]["start"] = "2026-01-02"
            elif kind == "old_ports_profile":
                for state in [package["inputs"]["supplied_opening"], package["state_cells"][0]["quantity"]]:
                    state["transport_profile"] = "entitlement-burdens-original-json/4"
            elif kind == "old_codec":
                for state in [package["inputs"]["supplied_opening"], package["state_cells"][0]["quantity"]]:
                    state.update(transport_profile="entitlement-burdens-original-json/1", identity_codec="unicode-scalars-hex6/1")
            elif kind == "old_raw_layout":
                for state in [package["inputs"]["supplied_opening"], package["state_cells"][0]["quantity"]]:
                    state["transport_profile"] = "entitlement-burdens-original-json/3"
            elif kind == "old_raw_profile":
                for state in [package["inputs"]["supplied_opening"], package["state_cells"][0]["quantity"]]:
                    state["transport_profile"] = "entitlement-burdens-original-json/2"
            else:
                original = json.loads(raw_tables["evidence"][-1]["raw_original"])
                original.update(id="unused", approved=False)
                row = burdens._fact(original, "evidence", {"unused": len(frame["evidence"])})
                raw_tables["evidence"].append({"id": row["id"], "slot": row["slot"], "raw_original": row.pop("raw_original")})
                # /5 execution fields use the same projection as every builder
                # row; helper-only source_observed_at is not a native input.
                projected = {**deepcopy(frame), "evidence": [row]}
                frame["evidence"].append(burdens._execution_frame(projected)["evidence"][0])
            with self.subTest(kind=kind):
                output = self.next_work("n")
                # Deliberately untrusted typed bindings exercise source guards,
                # separately from the public wrapper's preparation boundary.
                result = run_module_package(package, self.root, backend="compare", artifact_dir=output, audit_profile="compact-v2")
                self.assertEqual(completed_result(output), result)
                self.assertEqual(result["status"], "blocked", result["diagnostics"])
                self.assertEqual(result.get("trace_origin"), "native_ir_interpreter")
                self.assertFalse(result["results"] or result["closing_state"])
                if kind == "unused_bad": self.assertEqual(result["diagnostics"][0]["code"], "BURDEN_EVIDENCE_APPROVAL_CUTOFF")
        package = burdens.entitlement_burden_package(fixture(), reference=self.reference)
        checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
        self.assertIn("0", [row["slot"] for row in inputs["frames"][0]["evidence"]])
        inputs["frames"][0]["receipts"][0]["evidence_ref"] = burdens.encode_identity("wrong original evidence")
        binding = self.root / "misbound-original-ref.json"
        write_json(binding, {"inputs": inputs, "openings": openings})
        actual = normalize_target(self.native_audit_control(binding))
        self.assertEqual(actual["diagnostics"][0]["code"], "BURDEN_EVIDENCE_AUTHORITY")
        self.assertFalse(actual["emissions"] or actual["closing"])

    def test_prepared_boundary_reprojects_every_original_row_table_and_order(self):
        original = burdens.entitlement_burden_package(fixture(), reference=self.reference)
        for kind in ["money", "row_order", "raw_table", "raw_frame", "extra_row", "coordinator", "policy", "research", "scope", "manifest"]:
            package = deepcopy(original)
            inputs = package["inputs"]
            if kind == "money":
                inputs["frames"][0]["receipts"][0]["amount"] = burdens.money(300)
                inputs["frames"][0]["receipt_populations"][0]["gross_total"] = burdens.money(300)
            elif kind == "row_order": inputs["frames"][0]["evidence"].reverse()
            elif kind == "raw_table": inputs["original_frames"][0]["originals"]["evidence"].reverse()
            elif kind == "raw_frame": inputs["original_frames"][0]["raw_original"] += " "
            elif kind == "extra_row": inputs["frames"][0]["payments"].append(deepcopy(inputs["frames"][0]["payments"][0]))
            elif kind == "coordinator": inputs["coordinator"]["id"] = burdens.encode_identity("other")
            elif kind == "policy": package["parameters"]["policy"]["revision"] = "changed"
            elif kind == "research": inputs["research"]["review_locator"] = "changed"
            elif kind == "scope": inputs["scope"]["pool_id"] = "other"
            else: package["manifest"]["cutoff"] = "2027-01-01T00:00:00Z"
            before = digest(package)
            with self.subTest(kind=kind), patch.object(burdens, "run_module_package", side_effect=AssertionError("execution must not start")):
                result = burdens.run_entitlement_burden_package(package, self.root, backend="reference")
                self.assertEqual(result["diagnostics"][0]["code"], "BURDEN_PREPARED_PACKAGE_MISMATCH")
                self.assertFalse(result["results"] or result["closing_state"] or result["trace"])
                self.assertNotIn("result_digest", result)
            self.assertEqual(before, digest(package))
        burdens.validate_prepared_package(original)

    def test_prepared_boundary_checks_actual_opening_history_and_predecessor(self):
        original = fixture()
        previous = self.run_fixture(original, output=self.root / "boundary-seed")
        previous_digest = digest(previous)
        data, cells = self.carried(original, previous, 2)
        valid = burdens.entitlement_burden_package(data, reference=self.reference, state_cells=cells)
        burdens.validate_prepared_package(valid)
        for kind in ["actual_opening", "history", "predecessor", "predecessor_period", "prior_ref", "state_scope", "extra_cell"]:
            package = deepcopy(valid)
            if kind == "actual_opening": package["state_cells"][0]["quantity"]["detail"]["some"]["cap_usage"][0]["consumed"] = burdens.money(0)
            elif kind == "history": package["inputs"]["original_frames"][0]["raw_original"] += " "
            elif kind == "predecessor": package["inputs"]["predecessor"]["some"]["closing_state"]["detail"]["some"]["cap_usage"][0]["consumed"] = burdens.money(0)
            elif kind == "predecessor_period": package["inputs"]["predecessor"]["some"]["period"]["start"] = "2026-01-02"
            elif kind == "prior_ref": package["state_cells"][0]["prior_result_ref"] = "fabricated"
            elif kind == "state_scope": package["state_cells"][0]["scope"]["pool_id"] = "other"
            else: package["state_cells"].append(deepcopy(package["state_cells"][0]))
            before = digest(package)
            with self.subTest(kind=kind), patch.object(burdens, "run_module_package", side_effect=AssertionError("execution must not start")):
                result = burdens.run_entitlement_burden_package(package, self.root, backend="reference")
                self.assertEqual(result["diagnostics"][0]["code"], "BURDEN_PREPARED_PACKAGE_MISMATCH")
                self.assertFalse(result["results"] or result["closing_state"])
            self.assertEqual(before, digest(package))
        self.assertEqual(digest(previous), previous_digest)
        self.assertEqual(completed_result(self.locations[previous["result_digest"]]), previous)
        # The case wrapper and the SPL consistency predicate are independent
        # boundaries. Bypass preparation explicitly to test the latter too.
        direct = deepcopy(valid)
        direct["inputs"]["supplied_opening"]["detail"]["some"]["cap_usage"][0]["consumed"] = burdens.money(0)
        guarded = burdens.run_entitlement_burden_package(direct, self.root, backend="reference")
        self.assertEqual(guarded["diagnostics"][0]["code"], "BURDEN_PREPARED_PACKAGE_MISMATCH")
        output = self.next_work("opening")
        native = run_module_package(direct, self.root, backend="compare", artifact_dir=output, audit_profile="compact-v2")
        self.assertEqual(native.get("trace_origin"), "native_ir_interpreter", native["diagnostics"])
        self.assertEqual(native["diagnostics"][0]["code"], "BURDEN_CANONICAL_OPENING_MISMATCH")
        self.assertFalse(native["results"] or native["closing_state"])
        self.assertEqual(completed_result(output), native)
        checked, inputs, openings = validate_module_package(direct, resolve_module(self.reference, self.root))
        reference = evaluate(checked, inputs, openings)
        emitted = normalize_target(self.python_emitter_control(checked, inputs, openings))
        self.assertEqual([item["code"] for item in reference.diagnostics], ["BURDEN_CANONICAL_OPENING_MISMATCH"])
        self.assertEqual([item["code"] for item in emitted["diagnostics"]], ["BURDEN_CANONICAL_OPENING_MISMATCH"])
        self.assertFalse(emitted["emissions"] or emitted["closing"])

    def test_prepared_boundary_atomic_both_formats_stale_failure_and_unchanged_prior(self):
        original = burdens.entitlement_burden_package(fixture(), reference=self.reference)
        malformed = deepcopy(original)
        malformed["inputs"]["frames"][0]["receipts"][0]["amount"] = burdens.money(300)
        malformed["inputs"]["frames"][0]["receipt_populations"][0]["gross_total"] = burdens.money(300)
        original_digest = digest(original)
        for profile, backend in [("array-v1", "reference"), ("compact-v2", "compare")]:
            output = self.next_work("boundary")
            previous = burdens.run_entitlement_burden_package(original, self.root, backend=backend, artifact_dir=output, audit_profile=profile)
            self.assertEqual(previous["status"], "calculated", previous["diagnostics"])
            old_marker = read_json(output / "completion.json")
            old_work = output / ".runs" / old_marker["invocation_id"]
            prior_pins = {str(path.relative_to(old_work)): file_digest(path) for path in old_work.rglob("*") if path.is_file()}
            before = digest(malformed)
            result = burdens.run_entitlement_burden_package(malformed, self.root, backend=backend, artifact_dir=output, audit_profile=profile)
            self.assertEqual(completed_result(output), result)
            self.assertEqual(result["diagnostics"][0]["code"], "BURDEN_PREPARED_PACKAGE_MISMATCH")
            self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
            self.assertNotIn("result_digest", result)
            self.assertNotIn("trace_origin", result)
            if profile == "compact-v2": self.assertEqual(result["trace"]["status"], "unavailable")
            self.assertNotEqual(read_json(output / "completion.json")["invocation_id"], old_marker["invocation_id"])
            self.assertEqual(before, digest(malformed))
            self.assertEqual(prior_pins, {str(path.relative_to(old_work)): file_digest(path) for path in old_work.rglob("*") if path.is_file()})
            publisher = AuditedPublication if profile == "compact-v2" else ArtifactPublication
            with patch.object(publisher, "finish", side_effect=PublicationError("injected publication failure")):
                with self.assertRaises(PublicationError):
                    burdens.run_entitlement_burden_package(malformed, self.root, backend=backend, artifact_dir=output, audit_profile=profile)
            with self.assertRaises(PublicationError): completed_result(output)
            for interrupted in ["deepcopy", "validate_prepared_package"]:
                fresh = burdens.run_entitlement_burden_package(original, self.root, backend=backend, artifact_dir=output, audit_profile=profile)
                self.assertEqual(fresh["status"], "calculated", fresh["diagnostics"])
                with patch.object(burdens, interrupted, side_effect=KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        burdens.run_entitlement_burden_package(original, self.root, backend=backend, artifact_dir=output, audit_profile=profile)
                with self.assertRaises(PublicationError): completed_result(output)
            fresh = burdens.run_entitlement_burden_package(original, self.root, backend=backend, artifact_dir=output, audit_profile=profile)
            self.assertEqual(fresh["status"], "calculated", fresh["diagnostics"])
            with self.assertRaisesRegex(ValueError, "COMPACT_AUDIT_REQUIRES_NATIVE_PUBLICATION"):
                burdens.run_entitlement_burden_package(original, self.root, backend="reference", artifact_dir=output, audit_profile="compact-v2")
            with self.assertRaises(PublicationError): completed_result(output)
        self.assertEqual(original_digest, digest(original))

    def test_native_duplicate_alias_relabelled_charge_and_endpoint_authority(self):
        for kind in ["receipt_id", "receipt_ref", "entitlement_ref", "request", "authority", "scope", "unknown", "self"]:
            data = fixture()
            if kind in {"receipt_id", "receipt_ref", "entitlement_ref"}:
                row = deepcopy(data["receipts"][0])
                if kind != "receipt_id": row["id"] = "new-original"
                if kind == "entitlement_ref": row["original_ref"] = "new-original#different-line"
                data["receipts"].append(row)
            elif kind == "request": data["requests"].append({**deepcopy(data["requests"][0]), "id": "relabeled", "measurement_id": "other-label", "original_ref": "other-request#new"})
            elif kind == "authority": data["authorizations"].append({**deepcopy(data["authorizations"][0]), "id": "different", "sequence": 2})
            elif kind == "scope": data["authorizations"][0]["burdened_scope"]["agreement_id"] = "unknown-contract"
            elif kind == "unknown": data["requests"][0]["authorization_id"] = "unknown"
            else: data["authorizations"][0]["burdened_account"] = "claimant"
            with self.subTest(kind=kind): self.blocked(data, "compare")

    def test_native_payment_application_limits_chronology_and_population(self):
        for kind in ["overpaid", "unapplied", "lineage", "date", "receipt_population", "payment_population", "incomplete"]:
            data = fixture()
            if kind == "overpaid":
                data["payments"][0]["amount"] = "101"; data["applications"][0]["amount"] = "101"; data["payment_populations"][0]["paid_total"] = "101"
            elif kind == "unapplied": data["applications"][0]["amount"] = "59"
            elif kind == "lineage": data["applications"][0]["entitlement_line_ref"] = data["receipts"][0]["original_ref"]
            elif kind == "date": data["applications"][0]["application_date"] = "2026-03-09"
            elif kind == "receipt_population": data["receipt_populations"] = []
            elif kind == "payment_population": data["payment_populations"] = []
            else: data["payment_populations"][0]["complete"] = False
            with self.subTest(kind=kind): self.blocked(data, "compare")

    def test_native_cutoff_effective_boundaries_and_approval_equality(self):
        for kind in ["cutoff", "missing", "end", "future", "population_observation"]:
            data = fixture()
            if kind == "cutoff": data["requests"][0]["observed_at"] = data["cutoff"]
            elif kind == "missing": data["receipts"][0]["evidence_ref"] = "missing"
            elif kind == "end": data["authorizations"][0]["effective"]["end"] = "2026-03-31"
            elif kind == "future": data["authorizations"][0]["approved_date"] = "2026-04-01"
            else:
                row = data["receipt_populations"][0]; row["observed_at"] = "2026-03-01T00:00:00Z"
                next(ev for ev in data["evidence"] if ev["id"] == row["evidence_ref"])["observed_at"] = row["observed_at"]
            with self.subTest(kind=kind): self.blocked(data, "compare")
        data = fixture(); data["authorizations"][0].update(approved_date="2026-03-31", recorded_date="2026-03-31", observed_at="2026-04-01T00:00:00Z")
        self.controls(data, self.run_fixture(data, "compare"))

    def test_native_complete_checkpoint_preview_has_no_consumable_state(self):
        data = fixture()
        self.controls(data, self.run_fixture(data, "compare", mode="preview", output=self.root / "preview"), preview=True)

    def test_reference_actual_opening_financial_replay_registry_and_predecessor(self):
        original = fixture()
        first = self.run_fixture(original, output=self.root / "history-seed")
        self.controls(original, first)
        for kind in ["missing", "predecessor", "cap", "financial", "raw", "registry"]:
            data, cells = self.carried(original, first, 2)
            if kind == "missing": del data["prior_result"]
            elif kind == "predecessor": data["prior_result"]["source_case_id"] = "wrong"
            elif kind == "cap": data["opening_state"]["cap_usage"][0]["consumed"] = "0"
            elif kind == "financial": data["opening_state"]["history"][0]["result"]["applied_burden_total"] = "0"
            elif kind == "raw": data["opening_state"]["history"][0]["facts"]["receipts"][0]["amount"] = "201"
            else: data["authorizations"][0]["cap"] = "60"
            # Opening mutations use a separately transported cell so source replay
            # (rather than a generic cell-vs-input mismatch) checks the forgery.
            self.blocked(data)

    def test_reference_prior_original_aliases_late_payment_and_genesis(self):
        original = fixture()
        first = self.run_fixture(original, output=self.root / "alias-seed")
        for table in ["receipts", "payments", "requests"]:
            data, cells = self.carried(original, first, 2)
            data[table][0]["original_ref"] = original[table][0]["original_ref"]
            with self.subTest(table=table): self.blocked(data)
        original = paid_method(fixture())
        first = self.run_fixture(original, output=self.root / "paid-seed")
        data, cells = self.carried(original, first, 2)
        data["applications"][0]["receipt_id"] = original["receipts"][0]["id"]
        self.blocked(data)
        data, cells = self.carried(original, first, 2)
        data["opening_state"] = {"origin": "genesis", "boundary": data["period"]["start"], "source_case_id": "genesis", "history": []}; del data["prior_result"]
        self.blocked(data)

    def test_reference_population_controls_sequences_and_no_silent_scope_merging(self):
        for kind in ["gross", "ids", "measurement", "sequence", "same_agreement"]:
            data = fixture()
            if kind == "gross": data["receipt_populations"][0]["gross_total"] = "201"
            elif kind == "ids": data["receipt_populations"][0]["receipt_ids"].append(data["receipts"][0]["id"])
            elif kind == "measurement": data["requests"][0]["basis_receipt_ids"] = []
            elif kind == "sequence": data["authorizations"][0]["sequence"] = -1
            else:
                def change(value):
                    if isinstance(value, dict): return {key: change(item) for key, item in value.items()}
                    if isinstance(value, list): return [change(item) for item in value]
                    return "agreement-claimant" if value == "agreement-burdened" else value
                data = change(data)
            with self.subTest(kind=kind): self.blocked(data)

    def test_adapter_reversible_unicode_raw_consistency_and_no_solved_finance(self):
        originals = ["Ã©", "e\u0301", "a:#\x00", "å¥‘ç´„", "ðŸ™‚", "\U0010ffff", "a", "aa", "z"]
        self.assertEqual([burdens.decode_identity(burdens.encode_identity(value)) for value in originals], originals)
        self.assertEqual(sorted(originals), [burdens.decode_identity(value) for value in sorted(map(burdens.encode_identity, originals))])
        for bad in ["", "0", "f4908080", "eda080", "c080", "ff", "6A"]:
            with self.assertRaises(ValueError): burdens.decode_identity(bad)
        old_profile = burdens._state(fixture()["opening_state"], fixture())
        old_profile.update(transport_profile="entitlement-burdens-original-json/1", identity_codec="unicode-scalars-hex6/1")
        with self.assertRaisesRegex(ValueError, "BURDEN_STATE_TRANSPORT"): burdens.neutral_state(old_profile)
        old_profile.update(transport_profile="entitlement-burdens-original-json/2", identity_codec="unicode-utf8-hex/1")
        with self.assertRaisesRegex(ValueError, "BURDEN_STATE_TRANSPORT"): burdens.neutral_state(old_profile)
        old_profile["transport_profile"] = "entitlement-burdens-original-json/3"
        with self.assertRaisesRegex(ValueError, "BURDEN_STATE_TRANSPORT"): burdens.neutral_state(old_profile)
        old_profile["transport_profile"] = "entitlement-burdens-original-json/4"
        with self.assertRaisesRegex(ValueError, "BURDEN_STATE_TRANSPORT"): burdens.neutral_state(old_profile)
        original = fixture()["receipts"][0]
        encoded = burdens._fact(original, "receipts")
        encoded["amount"]["value"] = "201"
        # This is a canonical adapter/restore assertion, not a native JSON parser.
        with self.assertRaisesRegex(ValueError, "BURDEN_TYPED_RAW_MISMATCH"): burdens.neutral_fact(encoded | {"source_amount": "201"})
        for key in ["basis", "requested", "permitted"]:
            data = fixture(); data["requests"][0][key] = "30"
            with self.assertRaisesRegex(ValueError, "BURDEN_RECORD_FIELDS"): burdens.entitlement_burden_package(data, reference=self.reference)
        tree = ast.parse((ROOT / "cases/entitlement-burdens/build_modules.py").read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith("oracles") for name in imports))
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"sum", "min", "max", "contract_burdens"})
        for name in ["build_modules.py", "entitlement-burdens.spl"]:
            self.assertNotIn(b"\r", (ROOT / "cases/entitlement-burdens" / name).read_bytes())
