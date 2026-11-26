"""Original-fact and actual serialized controls for the ordered-gate source."""
import ast
from copy import deepcopy
from fractions import Fraction
from importlib import import_module
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from cases.r1 import build_modules as registration
from oracles.ordered_gates import OrderedGateOracleError, ordered_gates, exact_json, policy
from spl_compiler.artifacts import load_completed_result
from spl_compiler.audited_artifacts import load_completed_audited_result
from spl_compiler.codecs import DataError, digest, file_digest, read_json, write_json
from spl_compiler.compact_execution import _compiler_inputs, _stage, _verify_pins, metadata
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.model import encode_value
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.run import carry_state, normalize_target
from Tests.test_ordered_gate_oracle import fixture, sync, genesis, carry, q3

gates = import_module("cases.ordered-gates.build_modules")
EVIDENCE_DIR = None


def completed_result(path):
    """Recognize only the two explicitly supported completed-publication formats."""
    from spl_compiler.artifacts import _read_bounded, _strict_json, MAX_MANIFEST_BYTES, PublicationError
    marker = _strict_json(_read_bounded(Path(path) / "completion.json", MAX_MANIFEST_BYTES))
    if type(marker) is not dict:
        raise PublicationError("UNSUPPORTED_COMPLETION_FORMAT")
    if marker.get("format") == "spl-artifact-publication/1":
        return load_completed_result(path)
    if marker.get("format") == "spl-artifact-publication/2":
        return load_completed_audited_result(path)
    raise PublicationError("UNSUPPORTED_COMPLETION_FORMAT")


def add_reduction(data, *, amount="5", original_ref="original-reductions#rebate"):
    cost = next(row for row in data["rows"] if row["kind"] == "cost")
    item = {key: deepcopy(cost[key]) for key in gates.COMMON}
    item.update(id="original-rebate", original_ref=original_ref, source_ref="original-source:rebate", evidence_ref="evidence:rebate", category="rebate", amount=amount)
    cost["reductions"].append(item)
    data["evidence"].append({"id": item["evidence_ref"], "scope": deepcopy(data["scope"]), "kind": "cost_reduction", "source_ref": "original-evidence#rebate", "observed_at": item["observed_at"], "approved": True})
    return data


class OrderedGateModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/ordered-gate-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.addClassCleanup(cls.retain_evidence)
        cls.folder = cls.root / "cases/ordered-gates"
        cls.folder.mkdir(parents=True)
        for name in ["ordered-gates.spl", "neutral.json", "policy.md"]:
            shutil.copyfile(ROOT / "cases/ordered-gates" / name, cls.folder / name)
        for owner, key, value in [(gates, "ROOT", cls.root), (gates, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            change = patch.object(owner, key, value); change.start(); cls.addClassCleanup(change.stop)
        cls.reference = gates.register_ordered_gates()
        cls.transport_sequence = 0

    @classmethod
    def retain_evidence(cls):
        if EVIDENCE_DIR is not None:
            destination = Path(EVIDENCE_DIR).with_suffix(".zip")
            with ZipFile(destination, "x", compression=ZIP_DEFLATED, compresslevel=1) as archive:
                for path in sorted(cls.root.rglob("*")):
                    if path.is_file():
                        archive.write(path, arcname=path.relative_to(cls.root).as_posix())

    def next_work(self, kind):
        type(self).transport_sequence += 1
        path = self.root / kind / str(type(self).transport_sequence)
        path.mkdir(parents=True)
        return path

    def python_emitter_control(self, checked, inputs, openings):
        """Compile the independent Python emitter with unchanged separate budgets."""
        work = self.next_work("p")
        source, c_file, obj, executable = (work / name for name in ("Candidate.lean", "Candidate.c", "Candidate.o", "Candidate.exe"))
        source.write_text(emit_module(checked,
            {key: decode_value(value, checked.types[key]) for key, value in inputs.items()},
            {key: decode_value(value, checked.types[key]) for key, value in openings.items()}), encoding="utf-8", newline="\n")
        toolbin, flags, libraries, pins = _compiler_inputs()
        response = work / "link.rsp"
        response.write_text("\n".join(json.dumps(arg) for arg in [str(obj), *libraries]), encoding="utf-8")
        write_json(work / "build-inputs.json", {"pins": pins, "source_sha256": file_digest(source), "c_flags": flags,
                   "link_arguments": libraries, "compiler_profile": "compiler1g180", "runtime_profile": "runtime256"})
        for name, command in [
            ("lean-codegen", [toolbin / "lean.exe", "-DwarningAsError=true", "-R", work, "-c", c_file, source]),
            ("c-object", [toolbin / "clang.exe", "-c", "-o", obj, c_file, *flags]),
            ("link", [toolbin / "clang.exe", "-o", executable, "@" + str(response)])]:
            _stage(command, work / name, compiler=True)
        result = metadata(_stage([executable], work / "execution"))
        _verify_pins(pins)
        return result

    def run_fixture(self, data, backend="reference", *, cells=None, output=None, mode="final"):
        package = gates.ordered_gate_package(data, reference=self.reference, state_cells=cells, mode=mode)
        if backend == "compare" and output is None:
            output = self.next_work("n")
        result = gates.run_ordered_gate_package(package, self.root, backend=backend, artifact_dir=output,
            audit_profile="compact-v2" if backend == "compare" else "array-v1")
        if backend == "compare":
            self.assertEqual(result.get("trace_origin"), "native_ir_interpreter", result["diagnostics"])
            self.independent_python_control(package)
        if output is not None:
            self.assertEqual(completed_result(output), result)
            self.assertEqual(read_json(Path(output) / "result.json"), result)
            if not hasattr(self, "locations"): self.locations = {}
            if "result_digest" in result: self.locations[result["result_digest"]] = Path(output)
        return result

    def independent_python_control(self, package):
        checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
        reference = evaluate(checked, inputs, openings)
        expected = {"status": reference.status, "emissions": encode_value(reference.emissions),
                    "closing": encode_value(reference.closing), "diagnostics": reference.diagnostics}
        emitted = normalize_target(self.python_emitter_control(checked, inputs, openings))
        for field in ["status", "emissions", "closing"]:
            self.assertEqual(emitted[field], expected[field], field)
        self.assertEqual([row["code"] for row in emitted["diagnostics"]], [row["code"] for row in expected["diagnostics"]])

    def direct_physical_native(self, package, output):
        """Explicitly exercise the generic trusted-preparation API, not the case guard."""
        result = run_module_package(package, self.root, backend="compare", artifact_dir=output, audit_profile="compact-v2")
        self.assertEqual(result.get("trace_origin"), "native_ir_interpreter", result["diagnostics"])
        self.assertEqual(completed_result(output), result)
        self.independent_python_control(package)
        return result

    def controls(self, data, result, *, preview=False):
        expected = exact_json(ordered_gates(data))
        self.assertEqual(result["status"], "provisional" if preview else "calculated", result["diagnostics"])
        self.assertFalse(result["diagnostics"])
        actual = gates.neutral_result(result["results"]["comparison"])
        self.assertEqual(actual, {key: value for key, value in expected.items() if key != "closing_state"})
        if preview:
            self.assertFalse(result["closing_state"])
            with self.assertRaises(DataError) as caught: carry_state(result)
            self.assertEqual(caught.exception.code, "NONCONSUMABLE_STATE")
        else:
            self.assertEqual(len(result["closing_state"]), 1)
            self.assertEqual(gates.neutral_state(result["closing_state"][0]["quantity"]), expected["closing_state"])
        self.assertTrue(result["results"]["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertEqual(actual["payment_evidence_status"], "not_part_of_profile")
        self.assertFalse(actual["bank_movement_created"])
        self.assertEqual(result["results"]["stage_summary"]["fee_offset"], "0")
        self.assertEqual(result["results"]["stage_summary"]["reserve_movements"], "0")
        return actual

    def blocked(self, data, backend="reference", *, cells=None, output=None):
        with self.assertRaises(OrderedGateOracleError): ordered_gates(data)
        result = self.run_fixture(data, backend, cells=cells, output=output)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
        self.assertNotIn("result_digest", result)
        return result

    def carried(self, original, previous, frame=None):
        before = digest(previous)
        path = self.root / "serialized-closing-cells.json"
        write_json(path, previous["closing_state"])
        cells = read_json(path)
        for cell in cells: cell.pop("movement", None)
        self.assertEqual(cells, [{key: value for key, value in cell.items() if key != "movement"} for cell in previous["closing_state"]])
        plain = {**gates.neutral_result(previous["results"]["comparison"]), "closing_state": gates.neutral_state(cells[0]["quantity"])}
        data = carry(original, plain, frame=frame)
        data["prior_result"]["result_ref"] = cells[0]["prior_result_ref"]
        self.assertEqual(digest(previous), before)
        self.assertEqual(completed_result(self.locations[previous["result_digest"]]), previous)
        return data, cells

    def test_reference_seven_methods_and_branch_zero_status(self):
        expected = {"split_reopen": "6", "split_latch": "8", "full_cross_reopen": "7", "next_row_reopen": "4", "opening_gate": "0", "closing_gate": "11", "continuous_history": "0"}
        for method, amount in expected.items():
            data = fixture(); data["policy"] = policy(method)
            with self.subTest(method=method):
                actual = self.controls(data, self.run_fixture(data))
                self.assertEqual(actual["gross_candidate"], amount)
                self.assertEqual((actual["closing_receipts"], actual["closing_costs"]), ("150", "130"))
                if method in {"opening_gate", "continuous_history"}:
                    self.assertEqual((actual["gross_status"], actual["net_status"], actual["selected_branch"]), ("inapplicable", "computed_zero", "net"))

    def test_reference_authorized_reversal_and_economic_sequence_not_position(self):
        data = fixture(); data["rows"][1]["sequence"] = 2; data["rows"][2]["sequence"] = 1; sync(data)
        actual = self.controls(data, self.run_fixture(data))
        self.assertEqual(actual["gross_candidate"], "4")
        data["rows"].reverse(); data["ordering_authority"]["keys"].reverse(); data["evidence"].reverse()
        again = self.controls(data, self.run_fixture(data))
        self.assertEqual(actual["path"], again["path"])
        self.assertEqual(actual["gross_candidate"], again["gross_candidate"])

    def test_reference_below_equal_above_and_positive_equality_latch(self):
        for amount, gross, status in [("19", "0", "inapplicable"), ("20", "0", "computed_zero"), ("21", "1/5", "computed_positive")]:
            data = fixture(); data["rows"] = [data["rows"][0]]; data["rows"][0]["amount"] = amount; sync(data)
            actual = self.controls(data, self.run_fixture(data))
            self.assertEqual((actual["gross_candidate"], actual["gross_status"]), (gross, status))
            if amount == "20": self.assertTrue(actual["closing_latch"])

    def test_reference_zero_genesis_receipt_and_exact_fraction(self):
        data = genesis(fixture()); data["rows"] = [next(row for row in data["rows"] if row["kind"] == "receipt")]
        data["rows"][0]["amount"] = "0"; sync(data)
        actual = self.controls(data, self.run_fixture(data))
        self.assertFalse(actual["closing_latch"])
        self.assertEqual((actual["gross_candidate"], actual["gross_status"]), ("0", "computed_zero"))
        data["rows"][0]["amount"] = "1/3"; sync(data)
        actual = self.controls(data, self.run_fixture(data))
        self.assertEqual((actual["closing_receipts"], actual["gross_candidate"]), ("1/3", "1/15"))
        self.assertTrue(actual["closing_latch"])

    def test_reference_video_proxy_changes_payout_without_changing_full_gate(self):
        for proxy, gross in [("0", "4"), ("0.5", "6"), ("1", "8")]:
            data = fixture(); data["registry"]["terms"]["video_proxy"] = proxy
            actual = self.controls(data, self.run_fixture(data))
            self.assertEqual((actual["closing_receipts"], actual["closing_costs"], actual["gross_candidate"]), ("150", "130", gross))

    def test_reference_continuous_uses_current_prefix_not_endpoints_or_all_past(self):
        data = fixture(); data["policy"] = policy("continuous_history")
        history = data["opening_state"]["frames"][0]
        next(row for row in history["rows"] if row["kind"] == "receipt")["amount"] = "110"
        sync(history)
        data["rows"] = [data["rows"][2], data["rows"][-1]]
        data["rows"][1]["amount"] = "40"; sync(data)
        actual = self.controls(data, self.run_fixture(data))
        self.assertEqual((actual["opening_receipts"], actual["opening_costs"], actual["closing_receipts"], actual["closing_costs"]), ("110", "100", "150", "130"))
        self.assertFalse(actual["continuous_current_history"])
        self.assertEqual(actual["gross_status"], "inapplicable")
        closing = deepcopy(data); closing["policy"] = policy("closing_gate")
        self.assertEqual(self.controls(closing, self.run_fixture(closing))["gross_candidate"], "8")
        # Same endpoints; authorized economic order now has receipt before cost.
        cost = data["rows"][0]
        cost.update(incurred_at="2008-06-20T12:00:00Z", observed_at="2008-06-21T00:00:00Z")
        next(ev for ev in data["evidence"] if ev["id"] == cost["evidence_ref"])["observed_at"] = cost["observed_at"]
        sync(data)
        actual = self.controls(data, self.run_fixture(data))
        self.assertTrue(actual["continuous_current_history"])
        self.assertEqual((actual["closing_receipts"], actual["closing_costs"], actual["gross_candidate"]), ("150", "130", "8"))

    def test_reference_exact_offset_recognition_and_submicrosecond_order(self):
        data = fixture(); row = data["rows"][0]
        row.update(received_at="2008-04-10T06:00:00-07:00", earned_at="2008-04-10T12:00:00Z")
        next(key for key in data["ordering_authority"]["keys"] if key["event_id"] == row["id"])["occurred_at"] = "2008-04-10T13:00:00Z"
        actual = self.controls(data, self.run_fixture(data))
        self.assertEqual(Fraction(actual["path"][0]["occurred_at_exact"]), gates._ordinal_instant("2008-04-10T13:00:00Z"))
        self.assertEqual(actual["path"][0]["original"]["received_at"], row["received_at"])
        data = fixture(); row = data["rows"][1]; row["earned_at"] = "2008-04-20T12:00:00.0000000001Z"
        next(key for key in data["ordering_authority"]["keys"] if key["event_id"] == row["id"])["occurred_at"] = row["earned_at"]
        self.assertEqual(self.controls(data, self.run_fixture(data))["gross_candidate"], "4")

    def test_reference_cost_reduction_exclusions_and_original_line_double_use(self):
        data = add_reduction(fixture())
        actual = self.controls(data, self.run_fixture(data))
        self.assertEqual((actual["closing_costs"], actual["gross_candidate"]), ("125", "7"))
        bad = add_reduction(fixture(), original_ref=fixture()["rows"][0]["original_ref"]); self.blocked(bad)
        data = fixture(); data["rows"][0]["decision"]["eligible"] = False; data["rows"][0]["nonrefundable"] = False
        actual = self.controls(data, self.run_fixture(data))
        self.assertEqual(actual["gross_candidate"], "3")
        self.assertEqual((actual["path"][0]["selected_full_amount"], actual["path"][0]["reason"]), ("0", "explicitly_excluded_receipt"))
        data = fixture(); data["rows"][2]["decision"]["eligible"] = False; data["rows"][2]["actual_third_party"] = False
        self.assertEqual(self.controls(data, self.run_fixture(data))["gross_candidate"], "8")

    def test_reference_missing_populations_unknown_net_aggregate_and_unused_evidence(self):
        for kind in ["population", "incomplete", "ids", "total", "net", "aggregate", "unused", "missing_evidence"]:
            data = fixture()
            if kind == "population": data["populations"] = []
            elif kind == "incomplete": data["populations"][0]["complete"] = False
            elif kind == "ids": data["populations"][0]["event_ids"] = []
            elif kind == "total": data["populations"][0]["raw_total"] = "999"
            elif kind == "net": data["net_worksheet"]["amount"] = "1"
            elif kind == "aggregate": data["aggregate_hurdle"]["attained"] = False
            elif kind == "unused": data["evidence"].append({**deepcopy(data["evidence"][0]), "id": "unused"})
            else: data["rows"][0]["evidence_ref"] = "missing"
            with self.subTest(kind=kind): self.blocked(data)

    def test_reference_cutoffs_distinct_scope_hurdle_and_historical_terms(self):
        for kind in ["cutoff", "old", "hurdle", "net_scope", "terms", "work", "population_time"]:
            data = fixture()
            if kind == "cutoff": data["rows"][0]["observed_at"] = data["cutoff"]
            elif kind == "old": data["opening_state"]["frames"][0]["evidence"][0]["observed_at"] = data["opening_state"]["frames"][0]["cutoff"]
            elif kind == "hurdle": data["aggregate_hurdle"]["effective_date"] = data["period"]["start"]
            elif kind == "net_scope": data["net_worksheet"]["scope"]["pool_id"] = data["scope"]["pool_id"]
            elif kind == "terms": data["registry"]["terms"]["effective_start"] = data["period"]["start"]
            elif kind == "work": data["registry"]["work"]["observed_at"] = data["period"]["start"] + "T00:00:00Z"
            else: data["rows"][0]["observed_at"] = "2008-07-02T00:00:00Z"
            with self.subTest(kind=kind): self.blocked(data)

    def test_reference_alias_classification_and_unresolved_economic_keys(self):
        for kind in ["duplicate", "classification", "alias", "tie", "order", "channel", "reduction"]:
            data = fixture()
            if kind == "duplicate": data["rows"].append(deepcopy(data["rows"][0]))
            elif kind == "classification": data["rows"][1]["decision"]["id"] = data["rows"][0]["decision"]["id"]
            elif kind == "alias": data["rows"][1]["original_ref"] = data["rows"][0]["original_ref"]
            elif kind == "tie": data["rows"][2]["sequence"] = data["rows"][1]["sequence"]; sync(data)
            elif kind == "order": data["ordering_authority"]["keys"][0]["occurred_at"] = "2008-04-11T00:00:00Z"
            elif kind == "channel": data["rows"][1]["decision"]["channel"] = "ordinary"
            else: add_reduction(data, amount="31")
            with self.subTest(kind=kind): self.blocked(data)

    def test_reference_actual_three_period_serialized_carry_and_cumulative8(self):
        original = fixture()
        first_data = genesis(original)
        first = self.run_fixture(first_data, output=self.root / "actual-q1"); self.controls(first_data, first)
        second_data, cells = self.carried(original, first)
        second = self.run_fixture(second_data, cells=cells, output=self.root / "actual-q2"); self.controls(second_data, second)
        third_data, cells = self.carried(original, second, frame=q3(original))
        third = self.run_fixture(third_data, cells=cells, output=self.root / "actual-q3")
        actual = self.controls(third_data, third)
        self.assertEqual((actual["opening_receipts"], actual["opening_costs"], actual["closing_receipts"], actual["closing_costs"], actual["gross_candidate"]), ("150", "130", "170", "160", "2"))
        state = gates.neutral_state(third["closing_state"][0]["quantity"])
        self.assertEqual(state["recognized_entitlement"], "8")
        self.assertEqual([record["result"]["gross_candidate"] for record in state["history"]], ["0", "6", "2"])
        replay = self.run_fixture(deepcopy(third_data), cells=deepcopy(cells))
        self.assertEqual(replay["results"], third["results"])
        self.assertEqual(replay["closing_state"], third["closing_state"])

    def test_reference_predecessor_full_history_context_and_amount_tampering(self):
        original = fixture(); first_data = genesis(original)
        first = self.run_fixture(first_data, output=self.root / "tamper-seed")
        for kind in ["amount", "result", "policy", "registry", "predecessor", "missing"]:
            data, cells = self.carried(original, first)
            if kind == "amount": data["opening_state"]["receipts"] = "81"
            elif kind == "result": data["opening_state"]["history"][0]["result"]["gross_candidate"] = "1"
            elif kind == "policy": data["policy"] = policy("closing_gate")
            elif kind == "registry": data["registry"]["terms"]["gross_rate"] = "0.3"
            elif kind == "predecessor": data["prior_result"]["source_case_id"] = "wrong"
            else: del data["prior_result"]
            with self.subTest(kind=kind): self.blocked(data)

    def test_reference_preview_full_checkpoint_no_state_and_disclosed_history(self):
        data = fixture()
        result = self.run_fixture(data, mode="preview", output=self.root / "preview")
        actual = self.controls(data, result, preview=True)
        self.assertEqual(actual["gross_candidate"], "6")
        package = gates.ordered_gate_package(data, reference=self.reference)
        self.assertNotIn("prior_result_ref", package["state_cells"][0])
        self.assertEqual(package["inputs"]["supplied_opening"]["origin"], "original_history")

    def test_reference_unicode_raw_lexemes_and_transient_row_slots(self):
        data = fixture(); data["rows"][0]["original_ref"] = "original-e\u0301#é A"; data["rows"][0]["decision"]["event_ref"] = data["rows"][0]["original_ref"]
        data["rows"][0]["decision"]["reason"] = "original e\u0301 reason"
        data["rows"][0]["amount"] = "10.00"
        actual = self.controls(data, self.run_fixture(data))
        self.assertEqual(actual["path"][0]["original"]["amount"], "10.00")
        data["rows"].reverse(); data["evidence"].reverse(); data["ordering_authority"]["keys"].reverse()
        self.assertEqual(actual["path"], self.controls(data, self.run_fixture(data))["path"])
        # These case-wrapper preparation negatives have no native execution
        # credit. Separate direct-physical native tests exercise source checks.
        for kind in ["row_slot", "evidence_slot", "net_pool"]:
            package = gates.ordered_gate_package(fixture(), reference=self.reference)
            frame = package["inputs"]["frames"][-1]
            if kind == "row_slot": frame["receipts"][0]["row_slot"] = frame["costs"][0]["row_slot"]
            elif kind == "evidence_slot": frame["receipts"][0]["evidence_slot"] = "-1"
            else: frame["net_worksheets"][0]["scope"]["pool_id"] = {"some": package["inputs"]["fact_scope"]["pool_id"]}
            result = gates.run_ordered_gate_package(package, self.root, backend="reference")
            self.assertEqual(result["status"], "blocked", result["diagnostics"])
            self.assertFalse(result["results"] or result["closing_state"])

    def test_adapter_only_original_transport_strict_codec_and_exact_time_epoch(self):
        values = ["é", "e\u0301", "a:#\x00", "契約", "🙂", "\U0010ffff", "a", "aa"]
        self.assertEqual(values, [gates.decode_identity(gates.encode_identity(value)) for value in values])
        self.assertEqual(sorted(values), [gates.decode_identity(value) for value in sorted(map(gates.encode_identity, values))])
        for bad in ["", "0", "ff", "c080", "eda080", "f4908080", "6A"]:
            with self.assertRaises(ValueError): gates.decode_identity(bad)
        self.assertEqual(gates._ordinal_instant("0001-01-01T00:00:00Z"), 86400)
        for stamp in ["2008-04-20T12:00:00.0000000001Z", "2008-04-20T05:00:00.0000000001-07:00"]:
            self.assertEqual(gates._ordinal_instant(gates._from_ordinal(str(gates._ordinal_instant(stamp)))), gates._ordinal_instant(stamp))
        data = fixture(); typed, raw = gates._frame({key: data[key] for key in gates.FRAME}, data["registry"])
        typed["receipts"][0]["amount"]["value"] = "999"
        with self.assertRaisesRegex(ValueError, "GATE_TYPED_RAW_MISMATCH"): gates._validate_frame_transport(typed, raw, data["registry"])
        for key in ["solved_payout", "admitted_amount", "economic_rank"]:
            data = fixture(); data["rows"][0][key] = "6"
            with self.assertRaisesRegex(ValueError, "GATE_RECORD_FIELDS"): gates.ordered_gate_package(data, reference=self.reference)
        tree = ast.parse((ROOT / "cases/ordered-gates/build_modules.py").read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith("oracles") for name in imports))
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"sum", "min", "max", "ordered_gates", "sync"})
        for name in ["build_modules.py", "ordered-gates.spl"]: self.assertNotIn(b"\r", (ROOT / "cases/ordered-gates" / name).read_bytes())

    def test_native_baseline_full_original_history_all_material_fields(self):
        data = fixture()
        self.controls(data, self.run_fixture(data, "compare", output=self.root / "native-baseline"))

    def native_reference_control(self, name):
        """Execute the unchanged original-fact discriminator through all backends."""
        original = self.run_fixture
        def native(data, backend="reference", **options):
            if options.get("output") is not None:
                requested = Path(options["output"]).relative_to(self.root).as_posix()
                options["output"] = self.next_work("nc")
                write_json(options["output"] / "control.json", {"reference_method": name, "requested_output": requested})
            return original(data, "compare", **options)
        with patch.object(self, "run_fixture", side_effect=native):
            getattr(self, name)()

    def test_native_seven_methods_and_branch_zero_status(self):
        self.native_reference_control("test_reference_seven_methods_and_branch_zero_status")

    def test_native_authorized_reversal_and_economic_sequence_not_position(self):
        self.native_reference_control("test_reference_authorized_reversal_and_economic_sequence_not_position")

    def test_native_below_equal_above_and_positive_equality_latch(self):
        self.native_reference_control("test_reference_below_equal_above_and_positive_equality_latch")

    def test_native_zero_genesis_receipt_and_exact_fraction(self):
        self.native_reference_control("test_reference_zero_genesis_receipt_and_exact_fraction")

    def test_native_video_proxy_changes_payout_without_changing_full_gate(self):
        self.native_reference_control("test_reference_video_proxy_changes_payout_without_changing_full_gate")

    def test_native_continuous_uses_current_prefix_not_endpoints_or_all_past(self):
        self.native_reference_control("test_reference_continuous_uses_current_prefix_not_endpoints_or_all_past")

    def test_native_exact_offset_recognition_and_submicrosecond_order(self):
        self.native_reference_control("test_reference_exact_offset_recognition_and_submicrosecond_order")

    def test_native_cost_reduction_exclusions_and_original_line_double_use(self):
        self.native_reference_control("test_reference_cost_reduction_exclusions_and_original_line_double_use")

    def test_native_missing_populations_unknown_net_aggregate_and_unused_evidence(self):
        self.native_reference_control("test_reference_missing_populations_unknown_net_aggregate_and_unused_evidence")

    def test_native_cutoffs_distinct_scope_hurdle_and_historical_terms(self):
        self.native_reference_control("test_reference_cutoffs_distinct_scope_hurdle_and_historical_terms")

    def test_native_alias_classification_and_unresolved_economic_keys(self):
        self.native_reference_control("test_reference_alias_classification_and_unresolved_economic_keys")

    def test_native_actual_three_period_serialized_carry_and_cumulative8(self):
        original = fixture()
        first_data = genesis(original)
        first = self.run_fixture(first_data, "compare", output=self.root / "native-actual-q1")
        self.controls(first_data, first)
        second_data, cells = self.carried(original, first)
        second = self.run_fixture(second_data, "compare", cells=cells, output=self.root / "native-actual-q2")
        self.controls(second_data, second)
        third_data, cells = self.carried(original, second, frame=q3(original))
        third = self.run_fixture(third_data, "compare", cells=cells, output=self.root / "native-actual-q3")
        actual = self.controls(third_data, third)
        self.assertEqual((actual["opening_receipts"], actual["opening_costs"], actual["closing_receipts"], actual["closing_costs"], actual["gross_candidate"]),
                         ("150", "130", "170", "160", "2"))
        state = gates.neutral_state(third["closing_state"][0]["quantity"])
        self.assertEqual(state["recognized_entitlement"], "8")
        self.assertEqual([row["result"]["gross_candidate"] for row in state["history"]], ["0", "6", "2"])
        old = [(value, digest(value), self.locations[value["result_digest"]]) for value in [first, second, third]]
        preview = self.run_fixture(deepcopy(third_data), "compare", cells=deepcopy(cells), mode="preview", output=self.root / "native-actual-preview-q3")
        self.controls(third_data, preview, preview=True)
        self.assertEqual(preview["results"], third["results"])
        replay = self.run_fixture(deepcopy(third_data), "compare", cells=deepcopy(cells), output=self.root / "native-actual-replay-q3")
        self.assertEqual(replay["results"], third["results"])
        self.assertEqual(replay["closing_state"], third["closing_state"])
        for value, before, original_location in old:
            self.assertEqual(digest(value), before)
            self.assertEqual(completed_result(original_location), value)

    def test_native_preview_full_checkpoint_no_state_and_disclosed_history(self):
        self.native_reference_control("test_reference_preview_full_checkpoint_no_state_and_disclosed_history")

    def test_native_unicode_raw_lexemes_and_transient_row_slots(self):
        # This also retains the case-wrapper preparation negatives. Explicit
        # direct-physical controls below supply separate native source credit.
        self.native_reference_control("test_reference_unicode_raw_lexemes_and_transient_row_slots")

    def test_native_direct_physical_slots_original_populations_and_net_scope(self):
        for kind in ["row_slot", "evidence_slot", "evidence_id", "raw_population", "raw_case", "net_pool"]:
            package = gates.ordered_gate_package(fixture(), reference=self.reference)
            frame = package["inputs"]["frames"][-1]
            raw = package["inputs"]["original_frames"][-1]
            if kind == "row_slot": frame["receipts"][0]["row_slot"] = frame["costs"][0]["row_slot"]
            elif kind == "evidence_slot": frame["receipts"][0]["evidence_slot"] = "-1"
            elif kind == "evidence_id": frame["receipts"][0]["evidence_ref"] = gates.encode_identity("wrong original support")
            elif kind == "raw_population": raw["originals"]["receipts"][0]["id"] = gates.encode_identity("wrong raw original")
            elif kind == "raw_case": raw["id"] = gates.encode_identity("wrong raw frame")
            else: frame["net_worksheets"][0]["scope"]["pool_id"] = {"some": package["inputs"]["fact_scope"]["pool_id"]}
            with self.subTest(kind=kind):
                result = self.direct_physical_native(package, self.next_work("direct"))
                self.assertEqual(result["status"], "blocked", result["diagnostics"])
                self.assertFalse(result["results"] or result["closing_state"])
                self.assertNotIn("result_digest", result)

    def test_native_direct_prior_cell_replay_context_and_predecessor_tampering(self):
        original = fixture()
        first = self.run_fixture(genesis(original), "compare", output=self.root / "native-prior-seed")
        before = digest(first)
        for kind in ["predecessor", "predecessor_state", "replayed_result", "amount", "policy", "registry"]:
            data, cells = self.carried(original, first)
            package = gates.ordered_gate_package(data, reference=self.reference, state_cells=cells)
            inputs = package["inputs"]
            if kind == "predecessor": inputs["predecessor"]["some"]["source_case_id"] = gates.encode_identity("wrong predecessor")
            elif kind == "predecessor_state": inputs["predecessor"]["some"]["closing_state"]["detail"]["some"]["receipts"]["value"] = "81"
            elif kind == "replayed_result": inputs["supplied_opening"]["detail"]["some"]["history"][0]["result"]["gross_candidate"]["value"] = "1"
            elif kind == "amount":
                for state in [inputs["supplied_opening"], inputs["predecessor"]["some"]["closing_state"], package["state_cells"][0]["quantity"]]:
                    state["detail"]["some"]["receipts"]["value"] = "81"
            elif kind == "policy": package["parameters"]["policy"] = policy("closing_gate")
            else: inputs["registry"]["terms"]["gross_rate"] = "0.3"
            with self.subTest(kind=kind):
                result = self.direct_physical_native(package, self.next_work("direct-prior"))
                self.assertEqual(result["status"], "blocked", result["diagnostics"])
                self.assertFalse(result["results"] or result["closing_state"])
                self.assertNotIn("result_digest", result)
        self.assertEqual(digest(first), before)
        self.assertEqual(completed_result(self.locations[first["result_digest"]]), first)

    def test_prepared_wrapper_rechecks_originals_and_invalidates_reused_publications(self):
        for profile in ["array-v1", "compact-v2"]:
            output = self.root / ("prepared-" + profile)
            baseline = self.run_fixture(fixture(), "compare" if profile == "compact-v2" else "reference", output=output)
            self.controls(fixture(), baseline)
            before = digest(baseline)
            for kind in ["amount_total", "raw_frame", "raw_table", "history", "cell", "registry", "research", "row_slot", "cutoff", "scope", "duplicate_json", "noncanonical_json"]:
                package = gates.ordered_gate_package(fixture(), reference=self.reference)
                inputs = package["inputs"]
                frame, raw = inputs["frames"][-1], inputs["original_frames"][-1]
                if kind == "amount_total":
                    frame["receipts"][0]["amount"]["value"] = "60"
                    next(row for row in frame["populations"] if row["kind"] == "receipt")["raw_total"]["value"] = "120"
                elif kind == "raw_frame":
                    value = json.loads(raw["raw_original"]); value["rows"][0]["amount"] = "60"; raw["raw_original"] = gates._raw(value)
                elif kind == "raw_table": raw["originals"]["receipts"][0]["id"] = gates.encode_identity("different original")
                elif kind == "history":
                    value = json.loads(inputs["supplied_opening"]["original_frames"][0]["raw_original"])
                    value["rows"][1]["amount"] = "81"
                    inputs["supplied_opening"]["original_frames"][0]["raw_original"] = gates._raw(value)
                elif kind == "cell": package["state_cells"][0]["quantity"]["boundary"] = "2008-04-02"
                elif kind == "registry": inputs["registry"]["terms"]["gross_rate"] = "0.3"
                elif kind == "research": inputs["research"]["references"][0]["locator"] = gates.encode_identity("different locator")
                elif kind == "row_slot": frame["receipts"][0]["row_slot"] = frame["costs"][0]["row_slot"]
                elif kind == "cutoff": package["parameters"]["cutoff"] = "2008-07-06T00:00:00Z"
                elif kind == "scope": package["scope"]["pool_id"] = gates.encode_identity("different work pool")
                elif kind == "duplicate_json": inputs["registry_original"] = '{"duplicate":0,"duplicate":1}'
                else: inputs["registry_original"] += " "
                supplied = deepcopy(package)
                with self.subTest(profile=profile, kind=kind):
                    with patch.object(gates, "run_module_package", side_effect=AssertionError("Preparation rejection must precede execution")):
                        result = gates.run_ordered_gate_package(package, self.root, backend="compare", artifact_dir=output, audit_profile=profile)
                    self.assertEqual(package, supplied)
                    self.assertEqual(completed_result(output), result)
                    self.assertEqual(result["status"], "blocked")
                    self.assertEqual([row["code"] for row in result["diagnostics"]], ["GATE_PREPARED_PACKAGE_MISMATCH"])
                    self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
                    self.assertNotIn("result_digest", result)
                    self.assertNotIn("trace_origin", result)
                    if profile == "compact-v2":
                        self.assertEqual(result["trace"].get("status"), "unavailable")
                    else:
                        self.assertEqual(result["trace"], [])
            self.assertEqual(digest(baseline), before)

    def test_prepared_wrapper_rechecks_actual_prior_cell_history_and_predecessor(self):
        original = fixture()
        first = self.run_fixture(genesis(original), output=self.root / "prepared-prior-seed")
        before = digest(first)
        for kind in ["predecessor", "predecessor_state", "cell", "history"]:
            data, cells = self.carried(original, first)
            package = gates.ordered_gate_package(data, reference=self.reference, state_cells=cells)
            inputs = package["inputs"]
            if kind == "predecessor": inputs["predecessor"]["some"]["source_case_id"] = gates.encode_identity("different predecessor")
            elif kind == "predecessor_state": inputs["predecessor"]["some"]["closing_state"]["detail"]["some"]["receipts"]["value"] = "81"
            elif kind == "cell": package["state_cells"][0]["quantity"]["detail"]["some"]["receipts"]["value"] = "81"
            else:
                for state in [inputs["supplied_opening"], inputs["predecessor"]["some"]["closing_state"], package["state_cells"][0]["quantity"]]:
                    value = json.loads(state["detail"]["some"]["history"][0]["facts"])
                    value["rows"][1]["amount"] = "81"
                    state["detail"]["some"]["history"][0]["facts"] = gates._raw(value)
            with self.subTest(kind=kind):
                output = self.next_work("prepared-prior")
                with patch.object(gates, "run_module_package", side_effect=AssertionError("Preparation rejection must precede execution")):
                    result = gates.run_ordered_gate_package(package, self.root, backend="compare", artifact_dir=output, audit_profile="compact-v2")
                self.assertEqual(completed_result(output), result)
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["diagnostics"][0]["code"], "GATE_PREPARED_PACKAGE_MISMATCH")
                self.assertFalse(result["results"] or result["closing_state"])
        self.assertEqual(digest(first), before)
        self.assertEqual(completed_result(self.locations[first["result_digest"]]), first)

    def test_prepared_wrapper_requires_explicit_supported_publication_profile(self):
        package = gates.ordered_gate_package(fixture(), reference=self.reference)
        for profile, backend, destination in [("unknown", "compare", self.root / "bad-profile"),
                ("compact-v2", "reference", self.root / "non-native"), ("compact-v2", "compare", None)]:
            with self.subTest(profile=profile, backend=backend, destination=destination):
                with self.assertRaises(ValueError):
                    gates.run_ordered_gate_package(package, self.root, backend=backend, artifact_dir=destination, audit_profile=profile)

    def test_prepared_wrapper_cancellation_and_invalid_profile_invalidate_prior_success(self):
        from spl_compiler import compact_execution
        from spl_compiler.artifacts import PublicationError
        package = gates.ordered_gate_package(fixture(), reference=self.reference)
        original_digest = digest(package)
        for profile in ["array-v1", "compact-v2"]:
            seed = self.next_work("seed")
            previous = self.run_fixture(fixture(), "compare" if profile == "compact-v2" else "reference", output=seed)
            self.controls(fixture(), previous)
            for interruption in ["profile", "deepcopy", "validate", "unknown_profile", "non_native_profile", "publication"]:
                output = self.next_work("cancel")
                shutil.copytree(seed, output, dirs_exist_ok=True)
                self.assertEqual(completed_result(output), previous)
                old_marker = read_json(output / "completion.json")
                old_work = output / ".runs" / old_marker["invocation_id"]
                pins = {path.relative_to(old_work).as_posix(): file_digest(path) for path in old_work.rglob("*") if path.is_file()}
                with self.subTest(profile=profile, interruption=interruption):
                    if interruption in {"profile", "deepcopy", "validate"}:
                        target, attribute = (compact_execution, "require_profile") if interruption == "profile" else (gates, "deepcopy" if interruption == "deepcopy" else "validate_prepared_package")
                        with patch.object(target, attribute, side_effect=KeyboardInterrupt):
                            with self.assertRaises(KeyboardInterrupt):
                                gates.run_ordered_gate_package(package, self.root, backend="compare", artifact_dir=output, audit_profile=profile)
                    elif interruption == "publication":
                        from spl_compiler.artifacts import ArtifactPublication
                        from spl_compiler.audited_artifacts import AuditedPublication
                        bad = deepcopy(package)
                        bad["inputs"]["frames"][-1]["receipts"][0]["amount"]["value"] = "60"
                        publisher = AuditedPublication if profile == "compact-v2" else ArtifactPublication
                        with patch.object(publisher, "finish", side_effect=PublicationError("injected publication failure")):
                            with self.assertRaises(PublicationError):
                                gates.run_ordered_gate_package(bad, self.root, backend="compare", artifact_dir=output, audit_profile=profile)
                    else:
                        arguments = {"backend": "compare", "audit_profile": "unknown"} if interruption == "unknown_profile" else {"backend": "reference", "audit_profile": "compact-v2"}
                        with self.assertRaises(ValueError):
                            gates.run_ordered_gate_package(package, self.root, artifact_dir=output, **arguments)
                    self.assertEqual(read_json(output / "completion.json")["status"], "running")
                    self.assertNotEqual(read_json(output / "completion.json")["invocation_id"], old_marker["invocation_id"])
                    self.assertFalse(read_json(output / "result.json")["results"])
                    with self.assertRaises(PublicationError):
                        completed_result(output)
                    self.assertEqual(pins, {path.relative_to(old_work).as_posix(): file_digest(path) for path in old_work.rglob("*") if path.is_file()})
            self.assertEqual(completed_result(seed), previous)
        self.assertEqual(digest(package), original_digest)

    def test_native_generic_preparation_boundary_is_distinct_from_case_original_guard(self):
        package = gates.ordered_gate_package(fixture(), reference=self.reference)
        frame = package["inputs"]["frames"][-1]
        frame["receipts"][0]["amount"]["value"] = "60"
        next(row for row in frame["populations"] if row["kind"] == "receipt")["raw_total"]["value"] = "120"
        rejected = gates.run_ordered_gate_package(package, self.root, backend="compare",
            artifact_dir=self.next_work("guard-boundary"), audit_profile="compact-v2")
        self.assertEqual([row["code"] for row in rejected["diagnostics"]], ["GATE_PREPARED_PACKAGE_MISMATCH"])
        self.assertFalse(rejected["results"] or rejected["closing_state"])
        # The generic API trusts its prepared typed facts. It does not parse or
        # authenticate retained raw JSON. This explicit negative boundary probe
        # must not be described as an original-fact-qualified case result.
        trusted = self.direct_physical_native(package, self.next_work("trusted-boundary"))
        self.assertEqual(trusted["status"], "calculated", trusted["diagnostics"])
        actual = gates.neutral_result(trusted["results"]["comparison"])
        self.assertEqual(actual["gross_candidate"], "17")
        self.assertNotEqual(actual, {key: value for key, value in exact_json(ordered_gates(fixture())).items() if key != "closing_state"})
