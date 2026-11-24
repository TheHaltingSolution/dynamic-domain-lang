"""Original-fact controls for the independently implemented C13 SPL program."""
import ast
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from oracles.dependent_replay import DependentReplayOracleError, dependent_replay, exact_json
from Tests.test_dependent_replay_oracle import fixture, successor
from spl_compiler.artifacts import load_completed_result
from spl_compiler.audited_artifacts import load_completed_audited_result
from spl_compiler.codecs import digest, file_digest, read_json, write_json
from spl_compiler.compact_execution import _compiler_inputs, _stage, _verify_pins, metadata
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.model import encode_value
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.run import normalize_target

replay = import_module("cases.dependent-replay.build_modules")
EVIDENCE_DIR = None


def completed_result(path):
    """Load only the explicitly identified v1 or v2 completed publication."""
    from spl_compiler.artifacts import _read_bounded, _strict_json, MAX_MANIFEST_BYTES, PublicationError
    marker = _strict_json(_read_bounded(Path(path) / "completion.json", MAX_MANIFEST_BYTES))
    if type(marker) is not dict:
        raise PublicationError("UNSUPPORTED_COMPLETION_FORMAT")
    if marker.get("format") == "spl-artifact-publication/1":
        return load_completed_result(path)
    if marker.get("format") == "spl-artifact-publication/2":
        return load_completed_audited_result(path)
    raise PublicationError("UNSUPPORTED_COMPLETION_FORMAT")


class DependentReplayModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/dependent-replay-tests"; parent.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=parent); cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name); cls.folder = cls.root / "cases/dependent-replay"; cls.folder.mkdir(parents=True)
        cls.addClassCleanup(cls.retain_evidence)
        for name in ("dependent-replay.spl", "neutral.json", "policy.md"): shutil.copyfile(ROOT / "cases/dependent-replay" / name, cls.folder / name)
        for owner, key, value in ((replay, "ROOT", cls.root), (replay, "FOLDER", cls.folder), (registration, "ROOT", cls.root)):
            change = patch.object(owner, key, value); change.start(); cls.addClassCleanup(change.stop)
        cls.reference = replay.register_dependent_replay()
        cls.transport_sequence = 0

    @classmethod
    def retain_evidence(cls):
        if EVIDENCE_DIR is not None:
            shutil.copytree(cls.root, Path(EVIDENCE_DIR))

    def next_work(self, kind):
        type(self).transport_sequence += 1
        path = self.root / kind / str(type(self).transport_sequence)
        path.mkdir(parents=True)
        return path

    def python_emitter_control(self, checked, inputs, openings):
        """Independently emit, compile and run under the unchanged fixed guards."""
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

    def independent_python_control(self, package):
        checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
        reference = evaluate(checked, inputs, openings)
        expected = {"status": reference.status, "emissions": encode_value(reference.emissions),
            "closing": encode_value(reference.closing), "diagnostics": reference.diagnostics}
        emitted = normalize_target(self.python_emitter_control(checked, inputs, openings))
        for field in ("status", "emissions", "closing"):
            self.assertEqual(emitted[field], expected[field], field)
        self.assertEqual([row["code"] for row in emitted["diagnostics"]], [row["code"] for row in expected["diagnostics"]])

    def run_fixture(self, data, backend="reference", *, cells=None, output=None, mode="final"):
        package = replay.dependent_replay_package(data, reference=self.reference, state_cells=cells, mode=mode)
        if backend == "compare" and output is None:
            output = self.next_work("n")
        result = replay.run_dependent_replay_package(package, self.root, backend=backend, artifact_dir=output,
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

    def controls(self, data, result, *, preview=False):
        expected = exact_json(dependent_replay(data))
        self.assertEqual(result["status"], "provisional" if preview else "calculated", result["diagnostics"])
        self.assertFalse(result["diagnostics"])
        actual = replay.neutral_result(result["results"]["comparison"])
        self.assertEqual(actual, {key: value for key, value in expected.items() if key != "closing_state"})
        if preview: self.assertFalse(result["closing_state"])
        else:
            self.assertEqual(len(result["closing_state"]), 1)
            self.assertEqual(replay.neutral_state(result["closing_state"][0]["quantity"]), expected["closing_state"])
        self.assertTrue(result["results"]["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertEqual(actual["issuance_status"], "unissued_calculation")
        self.assertFalse(actual["bank_movement_created"] or actual["adjustment_issued_or_paid"])
        self.assertEqual(actual["actual_current_cash"], "0")
        return actual

    def blocked(self, data):
        with self.assertRaises(DependentReplayOracleError): dependent_replay(data)
        result = self.run_fixture(data)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
        self.assertNotIn("result_digest", result)
        return result

    def carried(self, original, previous):
        before = digest(previous)
        location = self.root / "serialized-closing-cells.json"
        write_json(location, previous["closing_state"]); cells = read_json(location)
        for cell in cells: cell.pop("movement", None)
        self.assertEqual(cells, [{key: value for key, value in cell.items() if key != "movement"} for cell in previous["closing_state"]])
        complete = {**replay.neutral_result(previous["results"]["comparison"]), "closing_state": replay.neutral_state(cells[0]["quantity"])}
        data = successor(original, complete)
        data["predecessor_result_ref"] = cells[0]["prior_result_ref"]
        data["prior_result"]["result_ref"] = cells[0]["prior_result_ref"]
        self.assertEqual(digest(previous), before)
        self.assertEqual(completed_result(self.locations[previous["result_digest"]]), previous)
        return data, cells

    def test_reference_four_scenarios_all_material_controls_and_original_issued_paid(self):
        for name, amount in (("simple", "40"), ("dependent", "18")):
            for route in ("restatement", "prospective"):
                data = fixture(name, route); result = self.controls(data, self.run_fixture(data))
                self.assertEqual(result["outstanding"], amount)
                self.assertEqual(result["actual_original_paid"], "80")
                self.assertEqual(result["original_issued_artifacts"], data["registry"]["issued_artifacts"])
                if name == "dependent":
                    original = result["original_period_controls"][1]["receipt_details"][0]
                    revised = result["replayed_period_controls"][1]["receipt_details"][0]
                    self.assertEqual((original["opening_cumulative_basis"], original["lower_basis"], original["upper_basis"], original["earned"]), ("200", "20", "40", "10"))
                    self.assertEqual((revised["opening_cumulative_basis"], revised["lower_basis"], revised["upper_basis"], revised["earned"]), ("180", "40", "20", "8"))
                    self.assertEqual(result["closing_cumulative_basis"], "240")

    def test_reference_routes_have_same_economics_and_distinct_signed_period_attribution(self):
        for name, issued, unpaid, credit, first_lines, second_lines in (("simple", "100", "20", "-10", ["90", "30"], ["100", "20"]), ("dependent", "110", "30", "-12", ["90", "8", "0"], ["100", "10", "-12"])):
            first_data = fixture(name); second_data = fixture(name, "prospective")
            first = self.controls(first_data, self.run_fixture(first_data)); second = self.controls(second_data, self.run_fixture(second_data))
            self.assertEqual(first["replayed_period_controls"], second["replayed_period_controls"])
            self.assertEqual([row["recognized_entitlement"] for row in first["period_lines"]], first_lines)
            self.assertEqual([row["recognized_entitlement"] for row in second["period_lines"]], second_lines)
            for result in (first, second): self.assertEqual((result["original_issued_total"], result["original_issued_unpaid"], result["authorized_correction_credit"]), (issued, unpaid, credit))
            self.assertFalse(first["prospective_adjustments"] or second["restatement_records"])

    def test_reference_actual_serialized_successors_do_not_repeat_either_correction(self):
        for name, amount in (("simple", "40"), ("dependent", "18")):
            for route in ("restatement", "prospective"):
                original = fixture(name, route)
                first = self.run_fixture(original, output=self.root / (name + route + "-first")); self.controls(original, first)
                data, cells = self.carried(original, first)
                second = self.run_fixture(data, cells=cells, output=self.root / (name + route + "-next"))
                result = self.controls(data, second)
                self.assertEqual((result["outstanding"], result["current_recognized"], result["current_posted_adjustment"]), (amount, "0", "0"))
                self.assertFalse(result["source_changes"] or result["restatement_records"] or result["prospective_adjustments"])
                self.assertEqual(result["consumed_correction_ids"], ["request:p1"])
                self.assertEqual(result["actual_original_paid"], "80")
                self.assertEqual(replay.neutral_state(second["closing_state"][0]["quantity"])["history"][0]["result"], replay.neutral_result(first["results"]["comparison"]))

    def test_reference_noop_and_complete_empty_corrections_are_distinct(self):
        data = fixture(route="prospective"); data["replacements"][0]["base_amount"] = "200"
        result = self.controls(data, self.run_fixture(data)); self.assertEqual((result["outstanding"], result["current_posted_adjustment"]), ("50", "0")); self.assertEqual(result["consumed_correction_ids"], ["request:p1"])
        data = fixture(); data["replacements"] = []; data["authorities"] = []; data["requests"] = []
        data["correction_population"].update(request_ids=[], replacement_ids=[], authority_ids=[])
        result = self.controls(data, self.run_fixture(data)); self.assertEqual((result["outstanding"], result["authorized_correction_credit"]), ("50", "0")); self.assertFalse(result["consumed_correction_ids"])

    def test_reference_dependent_threshold_fraction_and_upward_signed_revision(self):
        for basis, expected, credit in (("160", "6", "-24"), ("179", "87/5", "-63/5"), ("220", "42", "12")):
            data = fixture("dependent", "prospective"); data["replacements"][0]["base_amount"] = basis
            result = self.controls(data, self.run_fixture(data))
            self.assertEqual((result["outstanding"], result["authorized_correction_credit"]), (expected, credit))
            if basis == "160": self.assertEqual(result["replayed_period_controls"][1]["receipt_details"][0]["upper_basis"], "0")
        data = fixture(); data["replacements"][0]["base_amount"] = "140"; self.blocked(data)

    def test_reference_original_issued_controls_known_views_and_dependencies(self):
        for field, value in (("earned", "90"), ("opening_cumulative_basis", "1"), ("complete", False)):
            data = fixture(); data["registry"]["issued_artifacts"][0][field] = value; self.blocked(data)
        data = fixture(); data["registry"]["receipts"][0]["base_amount"] = "180"; self.blocked(data)
        data = fixture(); data["registry"]["receipts"][0]["observed_at"] = "2026-04-03T00:00:00Z"; self.blocked(data)
        data = fixture("dependent"); data["registry"]["periods"][1]["predecessor_period_id"] = "missing"; self.blocked(data)
        data = fixture("dependent"); data["registry"]["issued_artifacts"][1]["predecessor_issue_id"] = None; self.blocked(data)

    def test_reference_actual_paid_complete_population_and_bank_application_controls(self):
        data = fixture(); data["registry"]["payment_population"]["complete"] = False; self.blocked(data)
        data = fixture(); data["registry"]["payments"] = []; data["registry"]["applications"] = []; data["registry"]["payment_population"].update(payment_ids=[], application_ids=[], paid_total="0")
        result = self.controls(data, self.run_fixture(data)); self.assertEqual((result["actual_original_paid"], result["original_issued_total"], result["outstanding"]), ("0", "100", "120"))
        for field, value in (("amount", "79"), ("approved", False), ("original_entitlement_ref", "original-entitlement#other")):
            data = fixture(); data["registry"]["applications"][0][field] = value; self.blocked(data)
        data = fixture(); bank = deepcopy(data["registry"]["payments"][0]); bank["id"] = "relabelled-bank"; data["registry"]["payments"].append(bank); self.blocked(data)
        data = fixture(); data["registry"]["payments"][0]["recipient_id"] = "distributor"; self.blocked(data)

    def test_reference_authority_entire_suffix_and_all_original_links(self):
        for ids in (["p1"], ["p2", "p1"]):
            data = fixture("dependent"); data["authorities"][0]["dependent_period_ids"] = ids; self.blocked(data)
        for field, value in (("original_issue_id", "issue:other"), ("replacement_id", "replacement:other"), ("original_receipt_id", "receipt:other"), ("predecessor_result_ref", "result#other"), ("approved", False), ("apply_revised_basis_to_future", False), ("route", "prospective"), ("recorded_date", "2026-07-01")):
            data = fixture(); data["authorities"][0][field] = value; self.blocked(data)
        data = fixture(); data["authorities"][0].update(approved_date="2026-01-17", recorded_date="2026-01-17"); self.blocked(data)
        for field, value in (("original_basis_ref", "original-basis#other"), ("effective_date", "2026-01-16"), ("original_receipt_id", "missing")):
            data = fixture(); data["replacements"][0][field] = value; self.blocked(data)

    def test_reference_cash_and_correction_population_unknowns_are_not_zero(self):
        data = fixture(); data["cash_population"]["complete"] = False
        result = self.blocked(data); self.assertEqual(result["payment_evidence_status"], "not_assessed")
        data = fixture(); data["cash_population"].update(event_ids=["bank-new"], total="1"); self.blocked(data)
        data = fixture(); data["correction_population"]["complete"] = False; self.blocked(data)
        data = fixture(); data["correction_population"]["request_ids"] = []; self.blocked(data)
        data = fixture(); data["requests"] = []; data["correction_population"]["request_ids"] = []; self.blocked(data)
        data = fixture(); data["population"]["gross_basis_total"] = "0"; self.blocked(data)

    def test_reference_current_cutoff_scope_and_unused_evidence(self):
        data = fixture(); data["replacements"][0]["observed_at"] = data["cutoff"]; self.blocked(data)
        data = fixture(); data["evidence"][0]["observed_at"] = data["cutoff"]; self.blocked(data)
        data = fixture(); extra = deepcopy(data["evidence"][0]); extra.update(id="unused-future", observed_at="2027-01-01T00:00:00Z"); data["evidence"].append(extra); self.blocked(data)
        for key in ("agreement_id", "pool_id", "asset_id", "participant_id"):
            data = fixture(); data["authorities"][0]["scope"][key] = "other"; self.blocked(data)
        data = fixture(); data["registry"]["evidence"][-1]["observed_at"] = data["cutoff"]; self.blocked(data)

    def test_reference_duplicate_relabelled_corrections_and_amount_space_aliases(self):
        data = fixture(); data["requests"].append(deepcopy(data["requests"][0])); self.blocked(data)
        data = fixture(); replacement = deepcopy(data["replacements"][0]); replacement.update(id="replacement:relabel", original_ref="original-replacement#relabel")
        authority = deepcopy(data["authorities"][0]); authority.update(id="authority:relabel", replacement_id=replacement["id"], original_ref="authority#relabel")
        request = deepcopy(data["requests"][0]); request.update(id="request:relabel", authority_id=authority["id"], replacement_id=replacement["id"], sequence=1)
        data["replacements"].append(replacement); data["authorities"].append(authority); data["requests"].append(request)
        data["correction_population"].update(request_ids=[row["id"] for row in data["requests"]], replacement_ids=[row["id"] for row in data["replacements"]], authority_ids=[row["id"] for row in data["authorities"]]); self.blocked(data)
        data = fixture(); data["receipts"][0]["original_ref"] = data["replacements"][0]["original_ref"]; self.blocked(data)
        data = fixture(); data["receipts"][0]["entitlement_ref"] = data["registry"]["receipts"][0]["entitlement_ref"]; self.blocked(data)

    def test_reference_complete_receipt_order_keys_and_future_dates(self):
        data = fixture(); second = deepcopy(data["receipts"][0]); second.update(id="receipt:second", original_ref="original-sales#second", entitlement_ref="original-entitlement#second")
        data["receipts"].append(second); data["population"].update(receipt_ids=[row["id"] for row in data["receipts"]], gross_basis_total="120")
        self.blocked(data)
        second["sequence"] = 1
        expected = self.controls(data, self.run_fixture(data)); data["receipts"].reverse()
        self.assertEqual(self.controls(data, self.run_fixture(data)), expected)
        data = fixture(); data["authorities"][0]["recorded_date"] = "9999-12-31"; self.blocked(data)
        data = fixture(); data["receipts"][0]["effective_date"] = data["period"]["end"]; self.blocked(data)

    def test_reference_prior_financial_history_consumption_route_and_summary_tampering(self):
        original = fixture(); first = self.run_fixture(original, output=self.root / "tamper-first"); self.controls(original, first)
        for kind in ("recognized", "consumed", "history_result", "predecessor_case", "predecessor_ref", "period_link", "route"):
            data, cells = self.carried(original, first)
            if kind == "recognized": data["opening_state"]["recognized_entitlement"] = "999"
            elif kind == "consumed": data["opening_state"]["consumed_correction_ids"] = []
            elif kind == "history_result": data["opening_state"]["history"][0]["result"]["current_recognized"] = "0"
            elif kind == "predecessor_case": data["prior_result"]["source_case_id"] = "wrong"
            elif kind == "predecessor_ref": data["predecessor_result_ref"] = "wrong"
            elif kind == "period_link": data["predecessor_period_id"] = "wrong"
            else: data["policy"] = fixture(route="prospective")["policy"]
            if kind in {"recognized", "consumed", "history_result"}: data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
            self.blocked(data)

    def test_reference_permutations_unicode_and_exact_original_numeric_time_lexemes(self):
        data = fixture("dependent", "prospective")
        expected = self.controls(data, self.run_fixture(data))
        for value in data["registry"].values():
            if isinstance(value, list): value.reverse()
        data["evidence"].reverse()
        self.assertEqual(self.controls(data, self.run_fixture(data)), expected)
        data = fixture(); data["receipts"][0]["base_amount"] = "60.000"; data["receipts"][0]["observed_at"] = "2026-05-16t01:00:00.000000000001+01:00"; data["population"]["gross_basis_total"] = "60/1"
        def rename(value):
            if isinstance(value, dict): return {key: rename(item) for key, item in value.items()}
            if isinstance(value, list): return [rename(item) for item in value]
            return {"participant": "participant:e\u0301/\u96ea:#\x00", "distributor": "distributor:\u00e9"}.get(value, value) if isinstance(value, str) else value
        data = rename(data); result = self.run_fixture(data); self.controls(data, result)
        restored = replay.neutral_state(result["closing_state"][0]["quantity"])
        self.assertEqual(restored["history"][0]["facts"]["receipts"], data["receipts"])
        self.assertEqual(restored["registry"]["payments"], data["registry"]["payments"])

    def test_reference_direct_generic_evidence_slots_refs_and_unused_native_guards(self):
        # Deliberately bypass selected custody validation to exercise generic
        # typed bindings/reference guards. These are not native witnesses.
        for kind in ("slot_missing", "slot_other", "slot_duplicate", "scope", "unused_bad"):
            package = replay.dependent_replay_package(fixture(), reference=self.reference)
            frame = package["inputs"]["frames"][0]
            if kind == "slot_missing": frame["replacements"][0]["evidence_slot"] = "-1"
            elif kind == "slot_other": frame["replacements"][0]["evidence_slot"] = frame["requests"][0]["evidence_slot"]
            elif kind == "slot_duplicate": frame["evidence"][1]["slot"] = frame["evidence"][0]["slot"]
            elif kind == "scope": frame["authorities"][0]["scope"]["participant_id"] = replay.encode_identity("payer")
            else: package["inputs"]["registry"]["evidence"][-1]["approved"] = False
            result = run_module_package(package, self.root, backend="reference")
            self.assertEqual(result["status"], "blocked", result["diagnostics"])
            self.assertFalse(result["results"] or result["closing_state"])

    def test_public_wrapper_mechanical_correspondence_and_reused_artifact_atomicity(self):
        destination = self.root / "public-preparation"
        data = fixture(); self.controls(data, self.run_fixture(data, output=destination))
        previous = read_json(destination / "completion.json")["invocation_id"]
        for kind in ("replacement", "paid", "scope", "cutoff", "history_raw", "state", "context"):
            package = replay.dependent_replay_package(fixture(), reference=self.reference)
            if kind == "replacement": package["inputs"]["frames"][0]["replacements"][0]["base_amount"]["value"] = "200"
            elif kind == "paid": package["inputs"]["registry"]["payments"][0]["amount"]["value"] = "0"
            elif kind == "scope": package["scope"]["purpose"] = "another-purpose"
            elif kind == "cutoff": package["parameters"]["cutoff"] = "2026-07-04T00:00:00Z"
            elif kind == "history_raw": package["inputs"]["original_frames"][0]["raw_original"] = "{}"
            elif kind == "state": package["state_cells"][0]["quantity"]["source_case_id"] = replay.encode_identity("changed")
            else: package["inputs"]["source_context"] = '{"scope":{},"scope":{}}'
            before = deepcopy(package)
            with patch.object(replay, "run_module_package") as executor:
                result = replay.run_dependent_replay_package(package, self.root, backend="reference", artifact_dir=destination)
                executor.assert_not_called()
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["diagnostics"][0]["code"], "REPLAY_PREPARED_PACKAGE_MISMATCH")
            self.assertFalse(result["results"] or result["closing_state"] or result.get("result_digest"))
            self.assertEqual(load_completed_result(destination), result); self.assertEqual(read_json(destination / "result.json"), result)
            invocation = read_json(destination / "completion.json")["invocation_id"]; self.assertNotEqual(previous, invocation); previous = invocation
            self.assertEqual(package, before)

    def test_adapter_strict_transport_roundtrip_and_no_financial_oracle_computation(self):
        data = fixture("dependent", "prospective"); before = deepcopy(data)
        typed, originals = replay.frame({key: data[key] for key in replay.FRAME}); replay.validate_frame_transport(typed, originals)
        self.assertEqual(data, before)
        typed["replacements"][0]["base_amount"]["value"] = "200"
        with self.assertRaisesRegex(ValueError, "REPLAY_TYPED_RAW_MISMATCH"): replay.validate_frame_transport(typed, originals)
        for scalar in ("40.0", "-0", "01"):
            with self.assertRaisesRegex(ValueError, "REPLAY_(?:DERIVED_NUMBER_CANONICAL|EXACT_TRANSPORT)"): replay.derived_money(scalar)
        for value in ("", "ff", "6A", "0", "c080", "eda080"):
            with self.assertRaises(ValueError): replay.decode_identity(value)
        identities = ["a", "aa", "e\u0301", "\u00e9", "\u96ea", "a:#\x00"]
        self.assertEqual(sorted(identities), [replay.decode_identity(item) for item in sorted(map(replay.encode_identity, identities))])
        tree = ast.parse((ROOT / "cases/dependent-replay/build_modules.py").read_text())
        self.assertFalse(any(node.module and node.module.startswith("oracles") for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)))
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"sum", "min", "max", "dependent_replay", "compute"})
        for name in ("build_modules.py", "dependent-replay.spl"): self.assertNotIn(b"\r", (ROOT / "cases/dependent-replay" / name).read_bytes())

    def test_reference_same_complete_checkpoint_preview_has_no_consumable_state(self):
        data = fixture("dependent", "prospective")
        result = self.run_fixture(data, mode="preview", output=self.root / "preview")
        actual = self.controls(data, result, preview=True)
        self.assertEqual((actual["outstanding"], actual["current_recognized"]), ("18", "-12"))

    def native_reference_control(self, name):
        """Run the original-fact discriminator through both emitted backends."""
        original = self.run_fixture
        # A full unittest method name in this path exceeds Windows MAX_PATH
        # once owned closure descriptors and their SHA256 names are appended.
        prefix = self.next_work("controls")
        write_json(prefix / "control.json", {"method": name})
        def native(data, backend="reference", **options):
            if options.get("output") is not None:
                options["output"] = prefix / Path(options["output"]).relative_to(self.root)
            return original(data, "compare", **options)
        with patch.object(self, "run_fixture", side_effect=native):
            getattr(self, name)()

    def test_native_four_scenarios_all_material_controls_and_original_issued_paid(self):
        self.native_reference_control("test_reference_four_scenarios_all_material_controls_and_original_issued_paid")

    def test_native_routes_same_economics_distinct_signed_period_attribution(self):
        self.native_reference_control("test_reference_routes_have_same_economics_and_distinct_signed_period_attribution")

    def test_native_actual_serialized_successors_do_not_repeat_either_correction(self):
        self.native_reference_control("test_reference_actual_serialized_successors_do_not_repeat_either_correction")

    def test_native_noop_and_complete_empty_corrections_are_distinct(self):
        self.native_reference_control("test_reference_noop_and_complete_empty_corrections_are_distinct")

    def test_native_dependent_threshold_fraction_and_upward_signed_revision(self):
        self.native_reference_control("test_reference_dependent_threshold_fraction_and_upward_signed_revision")

    def test_native_original_issued_controls_known_views_and_dependencies(self):
        self.native_reference_control("test_reference_original_issued_controls_known_views_and_dependencies")

    def test_native_actual_paid_complete_population_and_bank_application_controls(self):
        self.native_reference_control("test_reference_actual_paid_complete_population_and_bank_application_controls")

    def test_native_authority_entire_suffix_and_all_original_links(self):
        self.native_reference_control("test_reference_authority_entire_suffix_and_all_original_links")

    def test_native_cash_and_correction_population_unknowns_are_not_zero(self):
        self.native_reference_control("test_reference_cash_and_correction_population_unknowns_are_not_zero")

    def test_native_current_cutoff_scope_and_unused_evidence(self):
        self.native_reference_control("test_reference_current_cutoff_scope_and_unused_evidence")

    def test_native_duplicate_relabelled_corrections_and_amount_space_aliases(self):
        self.native_reference_control("test_reference_duplicate_relabelled_corrections_and_amount_space_aliases")

    def test_native_complete_receipt_order_keys_and_future_dates(self):
        self.native_reference_control("test_reference_complete_receipt_order_keys_and_future_dates")

    def test_native_prior_financial_history_consumption_route_and_summary_tampering(self):
        self.native_reference_control("test_reference_prior_financial_history_consumption_route_and_summary_tampering")

    def test_native_permutations_unicode_and_exact_original_numeric_time_lexemes(self):
        self.native_reference_control("test_reference_permutations_unicode_and_exact_original_numeric_time_lexemes")

    def test_native_same_complete_checkpoint_preview_has_no_consumable_state(self):
        self.native_reference_control("test_reference_same_complete_checkpoint_preview_has_no_consumable_state")

    def test_native_direct_generic_evidence_slots_refs_and_unused_guards(self):
        # Deliberate generic typed-binding tests bypass the public raw custody
        # guard. Financial admission is credited only with actual native origin.
        for kind in ("slot_missing", "slot_other", "slot_duplicate", "scope", "unused_bad"):
            package = replay.dependent_replay_package(fixture(), reference=self.reference)
            frame = package["inputs"]["frames"][0]
            if kind == "slot_missing": frame["replacements"][0]["evidence_slot"] = "-1"
            elif kind == "slot_other": frame["replacements"][0]["evidence_slot"] = frame["requests"][0]["evidence_slot"]
            elif kind == "slot_duplicate": frame["evidence"][1]["slot"] = frame["evidence"][0]["slot"]
            elif kind == "scope": frame["authorities"][0]["scope"]["participant_id"] = replay.encode_identity("payer")
            else: package["inputs"]["registry"]["evidence"][-1]["approved"] = False
            with self.subTest(kind=kind):
                destination = self.next_work("physical")
                result = run_module_package(package, self.root, backend="compare", artifact_dir=destination, audit_profile="compact-v2")
                self.assertEqual(result.get("trace_origin"), "native_ir_interpreter", result["diagnostics"])
                self.assertEqual(completed_result(destination), result)
                self.independent_python_control(package)
                self.assertEqual(result["status"], "blocked", result["diagnostics"])
                self.assertFalse(result["results"] or result["closing_state"] or result.get("result_digest"))

    def test_public_wrapper_v1_v2_replaces_success_atomically_and_preserves_originals(self):
        data = fixture()
        for profile, backend in (("array-v1", "reference"), ("compact-v2", "compare")):
            destination = self.root / "public-profiles" / profile
            good = replay.dependent_replay_package(data, reference=self.reference)
            prior = deepcopy(good)
            success = replay.run_dependent_replay_package(good, self.root, backend=backend,
                artifact_dir=destination, audit_profile=profile)
            self.controls(data, success)
            self.assertEqual(completed_result(destination), success)
            self.assertEqual(good, prior)
            previous = read_json(destination / "completion.json")["invocation_id"]
            for kind in ("replacement", "paid", "scope", "cutoff", "history_raw", "state", "context"):
                package = deepcopy(good)
                if kind == "replacement": package["inputs"]["frames"][0]["replacements"][0]["base_amount"]["value"] = "200"
                elif kind == "paid": package["inputs"]["registry"]["payments"][0]["amount"]["value"] = "0"
                elif kind == "scope": package["scope"]["purpose"] = "another-purpose"
                elif kind == "cutoff": package["parameters"]["cutoff"] = "2026-07-04T00:00:00Z"
                elif kind == "history_raw": package["inputs"]["original_frames"][0]["raw_original"] = "{}"
                elif kind == "state": package["state_cells"][0]["quantity"]["source_case_id"] = replay.encode_identity("changed")
                else: package["inputs"]["source_context"] = '{"scope":{},"scope":{}}'
                before = deepcopy(package)
                with self.subTest(profile=profile, kind=kind), patch.object(replay, "run_module_package") as executor:
                    result = replay.run_dependent_replay_package(package, self.root, backend=backend,
                        artifact_dir=destination, audit_profile=profile)
                    executor.assert_not_called()
                    self.assertEqual(result["diagnostics"][0]["code"], "REPLAY_PREPARED_PACKAGE_MISMATCH")
                    self.assertFalse(result["results"] or result["closing_state"] or result.get("result_digest"))
                    self.assertEqual(completed_result(destination), result)
                    invocation = read_json(destination / "completion.json")["invocation_id"]
                    self.assertNotEqual(previous, invocation)
                    previous = invocation
                    self.assertEqual(package, before)
                    self.assertEqual(good, prior)

    def test_preparation_interrupt_invalid_profile_and_publication_failure_invalidate_old_success(self):
        from spl_compiler.artifacts import ArtifactPublication, PublicationError
        from spl_compiler.audited_artifacts import AuditedPublication
        package = replay.dependent_replay_package(fixture(), reference=self.reference)
        original = deepcopy(package)
        for profile, backend in (("array-v1", "reference"), ("compact-v2", "compare")):
            destination = self.next_work("lifecycle")
            def fresh():
                result = replay.run_dependent_replay_package(package, self.root, backend=backend,
                    artifact_dir=destination, audit_profile=profile)
                self.controls(fixture(), result)
                self.assertEqual(completed_result(destination), result)
                if profile == "compact-v2":
                    self.assertEqual(result.get("trace_origin"), "native_ir_interpreter")
                return result
            fresh()
            marker = read_json(destination / "completion.json")
            old_work = destination / ".runs" / marker["invocation_id"]
            prior_pins = {str(path.relative_to(old_work)): file_digest(path) for path in old_work.rglob("*") if path.is_file()}
            for interrupted in ("deepcopy", "validate_prepared_package"):
                with self.subTest(profile=profile, interrupted=interrupted):
                    fresh()
                    with patch.object(replay, interrupted, side_effect=KeyboardInterrupt):
                        with self.assertRaises(KeyboardInterrupt):
                            replay.run_dependent_replay_package(package, self.root, backend=backend,
                                artifact_dir=destination, audit_profile=profile)
                    with self.assertRaisesRegex(PublicationError, "PUBLICATION_NOT_COMPLETED"):
                        completed_result(destination)
            for requested_profile, requested_backend in (("unsupported", backend), ("compact-v2", "reference")):
                with self.subTest(profile=profile, requested_profile=requested_profile, requested_backend=requested_backend):
                    fresh()
                    with self.assertRaises(ValueError):
                        replay.run_dependent_replay_package(package, self.root, backend=requested_backend,
                            artifact_dir=destination, audit_profile=requested_profile)
                    with self.assertRaisesRegex(PublicationError, "PUBLICATION_NOT_COMPLETED"):
                        completed_result(destination)
            fresh()
            malformed = deepcopy(package)
            malformed["inputs"]["frames"][0]["replacements"][0]["base_amount"]["value"] = "200"
            before = deepcopy(malformed)
            publisher = AuditedPublication if profile == "compact-v2" else ArtifactPublication
            with patch.object(publisher, "finish", side_effect=PublicationError("injected publication failure")):
                with self.assertRaisesRegex(PublicationError, "injected publication failure"):
                    replay.run_dependent_replay_package(malformed, self.root, backend=backend,
                        artifact_dir=destination, audit_profile=profile)
            with self.assertRaisesRegex(PublicationError, "PUBLICATION_NOT_COMPLETED"):
                completed_result(destination)
            self.assertEqual(malformed, before)
            self.assertEqual(prior_pins, {str(path.relative_to(old_work)): file_digest(path) for path in old_work.rglob("*") if path.is_file()})
            self.assertEqual(package, original)
