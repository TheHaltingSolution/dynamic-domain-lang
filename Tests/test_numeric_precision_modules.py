"""Full original-fact controls for typed ratio and USD statement precision."""
import ast
from copy import deepcopy
from fractions import Fraction as F
from importlib import import_module
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from cases.r1 import build_modules as registration
from oracles.numeric_precision import NumericPrecisionOracleError, numeric_precision, exact_json, MODES
from Tests.test_numeric_precision_oracle import fixture, bases, repin
from spl_compiler.artifacts import load_completed_result, PublicationError
from spl_compiler.audited_artifacts import load_completed_audited_result
from spl_compiler.codecs import DataError, digest, file_digest, read_json, write_json
from spl_compiler.compact_execution import _compiler_inputs, _stage, _verify_pins, metadata
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import evaluate, decode_value
from spl_compiler.lean_tools import ROOT
from spl_compiler.model import SPLException, encode_value
from spl_compiler.modules import resolve_module, validate_module_package
from spl_compiler.run import normalize_target, carry_state

precision = import_module("cases.numeric-precision.build_modules")
EVIDENCE_DIR = None
OBSERVATIONS = []


def completed(path):
    marker = read_json(Path(path) / "completion.json")
    if marker.get("format") == "spl-artifact-publication/1": return load_completed_result(path)
    if marker.get("format") == "spl-artifact-publication/2": return load_completed_audited_result(path)
    raise PublicationError("UNSUPPORTED_COMPLETION_FORMAT")


class NumericPrecisionModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/np-tests"; parent.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=parent); cls.root = Path(cls.temp.name)
        cls.addClassCleanup(cls.temp.cleanup); cls.addClassCleanup(cls.retain)
        cls.folder = cls.root / "cases/numeric-precision"; cls.folder.mkdir(parents=True)
        for name in ["ratio-rounding.spl", "money-rounding.spl", "numeric-precision.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/numeric-precision" / name, cls.folder / name)
        for owner, key, value in [(precision, "ROOT", cls.root), (precision, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            change = patch.object(owner, key, value); change.start(); cls.addClassCleanup(change.stop)
        cls.refs = precision.register_all(); cls.reference = cls.refs["numeric-precision"]; cls.sequence = 0

    @classmethod
    def retain(cls):
        if EVIDENCE_DIR is not None:
            with ZipFile(Path(EVIDENCE_DIR).with_suffix(".zip"), "x", compression=ZIP_DEFLATED, compresslevel=1) as archive:
                for path in sorted(cls.root.rglob("*")):
                    if path.is_file(): archive.write(path, arcname=path.relative_to(cls.root).as_posix())

    def work(self, kind):
        type(self).sequence += 1
        path = self.root / kind / str(type(self).sequence); path.mkdir(parents=True); return path

    def python_control(self, package):
        checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
        reference = evaluate(checked, inputs, openings)
        expected = {"status": reference.status, "emissions": encode_value(reference.emissions), "closing": encode_value(reference.closing)}
        work = self.work("p")
        source, c_file, obj, target = (work / name for name in ["Candidate.lean", "Candidate.c", "Candidate.o", "Candidate.exe"])
        source.write_text(emit_module(checked, {key: decode_value(value, checked.types[key]) for key, value in inputs.items()}, {}), encoding="utf-8", newline="\n")
        toolbin, flags, libraries, pins = _compiler_inputs(); response = work / "link.rsp"
        response.write_text("\n".join(json.dumps(arg) for arg in [str(obj), *libraries]), encoding="utf-8")
        write_json(work / "build-inputs.json", {"pins": pins, "source_sha256": file_digest(source), "c_flags": flags, "link_arguments": libraries,
            "compiler_profile": "compiler1g180", "runtime_profile": "runtime256"})
        for name, command in [("lean-codegen", [toolbin / "lean.exe", "-DwarningAsError=true", "-R", work, "-c", c_file, source]),
                ("c-object", [toolbin / "clang.exe", "-c", "-o", obj, c_file, *flags]), ("link", [toolbin / "clang.exe", "-o", target, "@" + str(response)])]:
            _stage(command, work / name, compiler=True)
        actual = normalize_target(metadata(_stage([target], work / "execution"))); _verify_pins(pins)
        for key in expected: self.assertEqual(actual[key], expected[key], key)
        self.assertEqual([item["code"] for item in actual["diagnostics"]], [item["code"] for item in reference.diagnostics])

    def run_case(self, data, *, mode="final", period=None, cutoff=precision.DEFAULT_CUTOFF):
        # Original controls run before projection, with no supplied solved values.
        original = deepcopy(data); expected = exact_json(numeric_precision(data))
        package = precision.numeric_precision_package(data, reference=self.reference, mode=mode, period=period, cutoff=cutoff)
        backend = getattr(self, "backend", "reference"); output = self.work("n" if backend == "compare" else "r")
        result = precision.run_numeric_precision_package(package, self.root, backend=backend, artifact_dir=output,
            audit_profile="compact-v2" if backend == "compare" else "array-v1")
        self.assertEqual(result["status"], "provisional" if mode == "preview" else "calculated", result["diagnostics"])
        self.assertFalse(result["diagnostics"]); self.assertEqual(completed(output), result)
        self.assertEqual(precision.neutral_result(result["results"]["comparison"]), expected)
        self.assertTrue(result["results"]["reconciliation"]); self.assertFalse(result["closing_state"])
        self.assertEqual(result["issuance_status"], "unissued"); self.assertEqual(data, original)
        if mode == "preview":
            with self.assertRaises(DataError) as error: carry_state(result)
            self.assertEqual(error.exception.code, "NONCONSUMABLE_STATE")
        if backend == "compare":
            self.assertEqual(result.get("trace_origin"), "native_ir_interpreter"); self.python_control(package)
        OBSERVATIONS.append({"case_id": data["case_id"], "policy_ref": data["policy_ref"], "mode": mode, "backend": backend,
            "output": str(output), "selected_total": expected["statement"]["selected_total"], "bridge": expected["statement"]["rounding_bridge"], "full_original_equal": True})
        return result

    def reject(self, data, *, stage="source"):
        with self.assertRaises(NumericPrecisionOracleError): numeric_precision(data)
        original = deepcopy(data)
        try: package = precision.numeric_precision_package(data, reference=self.reference)
        except (ValueError, DataError, SPLException):
            self.assertIn(stage, {"adapter", "admission"}); self.assertEqual(data, original); return
        backend = getattr(self, "backend", "reference"); output = self.work("bn" if backend == "compare" else "br")
        result = precision.run_numeric_precision_package(package, self.root, backend=backend, artifact_dir=output,
            audit_profile="compact-v2" if backend == "compare" else "array-v1")
        self.assertEqual(completed(output), result); self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
        self.assertNotIn("result_digest", result); self.assertEqual(data, original)
        if stage == "source":
            self.assertTrue(result["diagnostics"][0]["code"].startswith("PRECISION_"), result["diagnostics"])
            if backend == "compare": self.assertEqual(result.get("trace_origin"), "native_ir_interpreter"); self.python_control(package)
        else:
            self.assertNotEqual(result.get("trace_origin"), "native_ir_interpreter")
            with self.assertRaises((DataError, SPLException)): validate_module_package(package, resolve_module(self.reference, self.root))

    def native_group(self, name):
        with patch.object(self, "backend", "compare", create=True): getattr(self, name)()

    def test_reference_six_scenarios_and_previews(self):
        for name in read_json(ROOT / "cases/numeric-precision/neutral.json")["scenarios"]:
            data = fixture(name)
            for mode in ["final", "preview"]:
                with self.subTest(name=name, mode=mode): self.run_case(data, mode=mode)

    def test_reference_all_signed_ratio_modes_and_near_ties(self):
        for sign in ["12.345", "-12.345"]:
            for mode in MODES:
                data = fixture("ratio_half_even"); data["ratio_expression"]["expressed_value"] = sign; data["policy"]["ratio_mode"] = mode; repin(data)
                with self.subTest(value=sign, mode=mode): self.run_case(data)
        for value in ["12.355", "-12.355", "12.344999999999999999", "12.345000000000000001"]:
            data = fixture("ratio_half_even"); data["ratio_expression"]["expressed_value"] = value; self.run_case(data)

    def test_reference_all_signed_money_modes_and_points(self):
        for values, total in [(["0.01", "0.01"], "0.02"), (["-0.01", "-0.01"], "-0.02")]:
            for mode in MODES:
                for point in ["row", "aggregate"]:
                    data = bases(fixture(), values, total); data["policy"].update(money_mode=mode, money_point=point); repin(data)
                    with self.subTest(values=values, mode=mode, point=point): self.run_case(data)

    def test_reference_signed_cancellation_and_noncent_quantum(self):
        for mode in MODES:
            data = bases(fixture(), ["0.01", "-0.01"], "0"); data["policy"].update(money_mode=mode, money_point="aggregate"); repin(data); self.run_case(data)
        for value in ["0.03", "-0.03"]: self.run_case(bases(fixture(), [value], value))
        for mode in ["half_even", "half_away_from_zero"]:
            data = bases(fixture(), ["0.03"], "0.03"); data["policy"].update(money_mode=mode); data["policy"]["money_quantum"]["value"] = "0.03"; repin(data); self.run_case(data)

    def test_reference_every_precision_and_expression_unit(self):
        for unit in ["fraction", "percentage"]:
            for places in range(7):
                data = fixture("ratio_half_even"); data["policy"].update(ratio_expression_unit=unit, ratio_expressed_decimal_places=places)
                # Supplied original quantum, not a rounded result or source answer.
                denominator = 10 ** places * (100 if unit == "percentage" else 1)
                data["policy"]["ratio_quantum"]["value"] = {"numerator": "1", "denominator": str(denominator)}
                data["ratio_expression"].update(expressed_unit=unit, expressed_value="0.1234565" if unit == "fraction" else "12.3450005")
                repin(data); self.run_case(data)
        data = fixture("ratio_half_even"); first = self.run_case(data)
        data["ratio_expression"].update(expressed_unit="fraction", expressed_value="0.12345"); data["policy"].update(ratio_expression_unit="fraction", ratio_expressed_decimal_places=4); repin(data)
        second = self.run_case(data)
        self.assertEqual(first["results"]["comparison"]["statement"], second["results"]["comparison"]["statement"])

    def test_reference_rational_large_zero_empty_and_eight_lines(self):
        data = bases(fixture(), [{"numerator": "1", "denominator": "3"}], {"numerator": "1", "denominator": "3"}); self.run_case(data)
        data = bases(fixture(), ["1"], "1"); data["policy"]["money_quantum"]["value"] = {"numerator": "1", "denominator": "3"}; repin(data); self.run_case(data)
        for mode in ["half_even", "half_away_from_zero"]:
            data = bases(fixture(), ["10000000000000000000.01"], "10000000000000000000.01"); data["policy"]["money_mode"] = mode; repin(data); self.run_case(data)
        for mode in MODES:
            data = bases(fixture(), ["-0.000"], "0"); data["policy"]["money_mode"] = mode; repin(data); self.run_case(data)
            self.run_case(bases(data, [], "0"))
        self.run_case(bases(fixture(), ["0.01"] * 8, "0.08")); self.reject(bases(fixture(), ["0.01"] * 9, "0.09"))

    def test_reference_permutation_split_merge_and_execution_metadata(self):
        for point in ["row", "aggregate"]:
            data = fixture(); data["policy"]["money_point"] = point; repin(data); first = self.run_case(data)
            data["lines"].reverse(); data["population"]["row_ids"].reverse(); second = self.run_case(data)
            self.assertEqual(first["results"]["comparison"]["statement"], second["results"]["comparison"]["statement"])
            self.run_case(bases(data, ["0.02"], "0.02"))
        data = fixture(); a = self.run_case(data)
        b = self.run_case(data, period={"start": "2001-01-01", "end": "2001-02-01"}, cutoff="2001-02-02T00:00:00Z")
        self.assertEqual(a["results"], b["results"])

    def test_reference_policy_content_pins_and_explicit_same_label_repin(self):
        for key, value in [("money_point", "aggregate"), ("ratio_mode", "ceiling"), ("money_mode", "ceiling"), ("revision", "2")]:
            data = fixture(); data["policy"][key] = value; self.reject(data)
        data = fixture(); data["policy_ref"]["id"] = "other"; self.reject(data)
        data = fixture(); data["policy"]["money_point"] = "aggregate"; repin(data); self.run_case(data)
        data["policy"]["revision"] = "new-label"; repin(data); self.run_case(data)
        data["policy"]["revision"] = "1"; repin(data); self.run_case(data)
        data = fixture(); data["policy"]["money_quantum"]["value"] = "0.010"; self.reject(data); repin(data); self.run_case(data)

    def test_reference_nonpositive_quanta_modes_points_precision_and_populations(self):
        for key in ["ratio_quantum", "money_quantum"]:
            for value in ["0", "-0.000", "-0.01"]:
                data = fixture(); data["policy"][key]["value"] = value; repin(data); self.reject(data)
        data = bases(fixture(), [], "0"); data["policy"]["money_quantum"]["value"] = "0"; repin(data); self.reject(data)
        for key in ["ratio_mode", "money_mode"]:
            for value in ["half_up", "nearest"]:
                data = fixture(); data["policy"][key] = value; repin(data); self.reject(data)
        for key, value in [("ratio_point", "after_money"), ("money_point", "display_only"), ("bridge", "assign_first_row")]:
            data = fixture(); data["policy"][key] = value; repin(data); self.reject(data)
        for places in [-1, 7]:
            data = fixture(); data["policy"]["ratio_expressed_decimal_places"] = places; repin(data); self.reject(data)
        data = fixture("ratio_half_even"); data["policy"]["ratio_quantum"]["value"] = "0.01"; repin(data); self.reject(data)
        for field, value in [("complete", False), ("row_ids", []), ("row_ids", ["line-1", "line-1"]), ("basis_total", {"dimension": "Money", "currency": "USD", "value": "0"})]:
            data = fixture(); data["population"][field] = value; self.reject(data)
        for field in ["id", "original_ref"]:
            data = fixture(); data["lines"][1][field] = data["lines"][0][field]; self.reject(data)

    def test_reference_unicode_original_numbers_codec_and_authority(self):
        data = fixture(); identity = "participant:e\u0301/\u96ea:#\x00"
        for holder in [data, data["ratio_expression"], data["population"], *data["lines"]]: holder["scope"]["participant_id"] = identity
        data["lines"][0]["basis"]["value"] = "0.0100"; self.run_case(data)
        data["ratio_expression"]["scope"]["participant_id"] = identity.replace("e\u0301", "\u00e9"); self.reject(data, stage="admission")
        data = fixture(); data["ratio_expression"]["id"] = "different"; self.reject(data)
        data = fixture(); data["lines"][0]["ratio_expression_id"] = "different"; self.reject(data)

    def test_adapter_dimensions_exact_numbers_and_no_solved_answers(self):
        for value in [.5, True, "1e3", "0.5 ", "+0.5", "1/3", {"numerator": "2", "denominator": "4"}, {"numerator": "-0", "denominator": "1"}]:
            data = fixture(); data["ratio_expression"]["expressed_value"] = value; self.reject(data, stage="adapter")
        for field, value in [("ratio_quantum", {"dimension": "Money", "currency": "USD", "value": "0.0001"}), ("money_quantum", {"dimension": "Ratio", "value": "0.01"})]:
            data = fixture(); data["policy"][field] = value; repin(data); self.reject(data, stage="adapter")
        data = fixture(); data["lines"][0]["basis"] = {"dimension": "Quantity", "unit": "Download", "value": "0.01"}; self.reject(data, stage="adapter")
        data = fixture(); data["policy"]["money_quantum"]["currency"] = "EUR"; repin(data); self.reject(data, stage="adapter")
        for target, key in [("root", "selected_total"), ("line", "earned"), ("expression", "rounded_ratio")]:
            data = fixture(); holder = data if target == "root" else data["lines"][0] if target == "line" else data["ratio_expression"]; holder[key] = "0"; self.reject(data, stage="adapter")
        for value in ["", "0", "ff", "c080", "eda080", "f4908080", "6A"]:
            with self.assertRaises(ValueError): precision.decode_identity(value)
        tree = ast.parse((ROOT / "cases/numeric-precision/build_modules.py").read_text(encoding="utf-8"))
        self.assertFalse([node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("oracles")])
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"numeric_precision", "quantize", "round", "sum", "min", "max", "round_ratio", "round_money"})

    def test_reference_prepared_custody_and_atomic_rejection(self):
        # Reference-only preparation controls seed an array publication. The
        # native counterpart additionally seeds a real compact publication.
        for profile in ["array-v1", "compact-v2"]:
            seed = self.work("seed")
            previous = self.run_case(fixture())
            previous_output = Path(OBSERVATIONS[-1]["output"])
            shutil.copytree(previous_output, seed, dirs_exist_ok=True)
            before = digest(previous)
            for kind in ["basis_total", "ratio", "policy", "raw_document", "raw_policy", "raw_line", "raw_population", "scope", "cutoff", "state", "evidence", "scenario", "duplicate_json", "noncanonical_json"]:
                package = precision.numeric_precision_package(fixture(), reference=self.reference)
                inputs = package["inputs"]
                if kind == "basis_total":
                    inputs["lines"][0]["basis"]["value"] = "0.02"
                    inputs["population"]["basis_total"]["value"] = "0.03"
                elif kind == "ratio": inputs["expression"]["expressed_value"] = "0.6"
                elif kind == "policy": inputs["selected"]["money_point"] = "aggregate"
                elif kind == "raw_document":
                    raw = json.loads(inputs["originals"]["document"]); raw["lines"][0]["basis"]["value"] = "0.02"
                    inputs["originals"]["document"] = precision._raw(raw)
                elif kind == "raw_policy": inputs["original_policy"]["raw_original"] = "{}"
                elif kind == "raw_line": inputs["original_lines"][0]["raw_original"] = "{}"
                elif kind == "raw_population": inputs["original_population"]["id"] = precision.encode_identity("other")
                elif kind == "scope": package["scope"]["asset_ids"] = [precision.encode_identity("other")]
                elif kind == "cutoff": package["parameters"]["cutoff"] = "2026-01-04T00:00:00Z"
                elif kind == "state": package["state_cells"] = [{}]
                elif kind == "evidence": package["evidence"] = {"unexpected": []}
                elif kind == "scenario": package["manifest"]["scenario_id"] = precision.encode_identity("other")
                elif kind == "duplicate_json": inputs["originals"]["document"] = '{"same":0,"same":1}'
                else: inputs["originals"]["document"] += " "
                supplied = deepcopy(package)
                output = self.work("prep"); shutil.copytree(seed, output, dirs_exist_ok=True)
                with self.subTest(profile=profile, kind=kind):
                    with patch.object(precision, "run_module_package", side_effect=AssertionError("Rejected preparation must precede execution")):
                        result = precision.run_numeric_precision_package(package, self.root, backend="compare", artifact_dir=output, audit_profile=profile)
                    self.assertEqual(package, supplied); self.assertEqual(completed(output), result)
                    self.assertEqual([row["code"] for row in result["diagnostics"]], ["PRECISION_PREPARED_PACKAGE_MISMATCH"])
                    self.assertEqual(result["status"], "blocked"); self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
                    self.assertNotIn("result_digest", result); self.assertNotIn("trace_origin", result)
                    if profile == "array-v1": self.assertEqual(result["trace"], [])
                    else: self.assertEqual(result["trace"]["status"], "unavailable")
            self.assertEqual(digest(previous), before); self.assertEqual(completed(previous_output), previous)

    def test_reference_preparation_lifecycle_invalidates_previous_completion(self):
        from spl_compiler import compact_execution
        from spl_compiler.artifacts import ArtifactPublication
        from spl_compiler.audited_artifacts import AuditedPublication
        package = precision.numeric_precision_package(fixture(), reference=self.reference)
        before = digest(package)
        previous = self.run_case(fixture()); seed = Path(OBSERVATIONS[-1]["output"])
        for profile in ["array-v1", "compact-v2"]:
            for interruption in ["profile", "deepcopy", "validate", "unknown_profile", "non_native_profile", "publication"]:
                output = self.work("cancel"); shutil.copytree(seed, output, dirs_exist_ok=True)
                marker = read_json(output / "completion.json"); old_work = output / ".runs" / marker["invocation_id"]
                pins = {path.relative_to(old_work).as_posix(): file_digest(path) for path in old_work.rglob("*") if path.is_file()}
                with self.subTest(profile=profile, interruption=interruption):
                    if interruption in {"profile", "deepcopy", "validate"}:
                        target, key = (compact_execution, "require_profile") if interruption == "profile" else (precision, "deepcopy" if interruption == "deepcopy" else "validate_prepared_package")
                        with patch.object(target, key, side_effect=KeyboardInterrupt):
                            with self.assertRaises(KeyboardInterrupt): precision.run_numeric_precision_package(package, self.root, backend="compare", artifact_dir=output, audit_profile=profile)
                    elif interruption == "publication":
                        bad = deepcopy(package); bad["inputs"]["expression"]["expressed_value"] = "0.6"
                        publisher = ArtifactPublication if profile == "array-v1" else AuditedPublication
                        with patch.object(publisher, "finish", side_effect=PublicationError("injected publication failure")):
                            with self.assertRaises(PublicationError): precision.run_numeric_precision_package(bad, self.root, backend="compare", artifact_dir=output, audit_profile=profile)
                    else:
                        arguments = {"backend": "compare", "audit_profile": "unknown"} if interruption == "unknown_profile" else {"backend": "reference", "audit_profile": "compact-v2"}
                        with self.assertRaises(ValueError): precision.run_numeric_precision_package(package, self.root, artifact_dir=output, **arguments)
                    self.assertEqual(read_json(output / "completion.json")["status"], "running")
                    self.assertNotEqual(read_json(output / "completion.json")["invocation_id"], marker["invocation_id"])
                    self.assertFalse(read_json(output / "result.json")["results"])
                    with self.assertRaises(PublicationError): completed(output)
                    self.assertEqual(pins, {path.relative_to(old_work).as_posix(): file_digest(path) for path in old_work.rglob("*") if path.is_file()})
        self.assertEqual(digest(package), before); self.assertEqual(completed(seed), previous)

    def test_reference_publication_profile_admission(self):
        package = precision.numeric_precision_package(fixture(), reference=self.reference)
        for profile, backend, output in [("unknown", "compare", self.work("badprofile")), ("compact-v2", "reference", self.work("badbackend")), ("compact-v2", "compare", None)]:
            with self.subTest(profile=profile, backend=backend):
                with self.assertRaises(ValueError): precision.run_numeric_precision_package(package, self.root, backend=backend, artifact_dir=output, audit_profile=profile)

    def test_native_prepared_custody_and_lifecycle(self):
        self.native_group("test_reference_prepared_custody_and_atomic_rejection")
        self.native_group("test_reference_preparation_lifecycle_invalidates_previous_completion")

    def direct_native(self, package):
        # Deliberately bypass the case wrapper to measure the generic prepared
        # interface. Retained raw Text is not parsed by the financial program.
        output = self.work("direct")
        result = precision.run_module_package(package, self.root, backend="compare", artifact_dir=output, audit_profile="compact-v2")
        self.assertEqual(completed(output), result)
        self.assertEqual(result.get("trace_origin"), "native_ir_interpreter")
        self.python_control(package)
        return result

    def test_native_original_population_source_checks_and_trusted_boundary(self):
        numeric_precision(fixture())
        for kind in ["line_id", "empty_raw", "expression", "population", "policy_pin"]:
            package = precision.numeric_precision_package(fixture(), reference=self.reference)
            inputs = package["inputs"]
            if kind == "line_id": inputs["original_lines"][0]["id"] = precision.encode_identity("other")
            elif kind == "empty_raw": inputs["original_lines"][0]["raw_original"] = ""
            elif kind == "expression": inputs["original_expression"]["id"] = precision.encode_identity("other")
            elif kind == "population": inputs["original_population"]["id"] = precision.encode_identity("other")
            else: inputs["original_policy"]["sha256"] = "0" * 64
            with self.subTest(kind=kind):
                result = self.direct_native(package)
                self.assertEqual(result["status"], "blocked"); self.assertFalse(result["results"] or result["closing_state"])
                self.assertTrue(result["diagnostics"][0]["code"].startswith("PRECISION_"))
        package = precision.numeric_precision_package(fixture(), reference=self.reference)
        package["inputs"]["lines"][0]["basis"]["value"] = "0.02"
        package["inputs"]["population"]["basis_total"]["value"] = "0.03"
        rejected = precision.run_numeric_precision_package(package, self.root, backend="compare", artifact_dir=self.work("custody"), audit_profile="compact-v2")
        self.assertEqual(rejected["diagnostics"][0]["code"], "PRECISION_PREPARED_PACKAGE_MISMATCH")
        trusted = self.direct_native(package)
        self.assertEqual(trusted["status"], "calculated")
        self.assertEqual(precision.neutral_result(trusted["results"]["comparison"])["statement"]["selected_total"], "1/100")
        self.assertNotEqual(precision.neutral_result(trusted["results"]["comparison"]), exact_json(numeric_precision(fixture())))

    def test_native_wrong_dimensions_and_currency_are_binding_admission(self):
        with patch.object(self, "backend", "compare", create=True): self.run_case(fixture())
        output = Path(OBSERVATIONS[-1]["output"]); marker = read_json(output / "completion.json")
        work = output / ".runs" / marker["invocation_id"]
        baseline = read_json(work / "bindings.json")
        for kind, code in [("ratio_money", "UNKNOWN_OR_MISSING_FIELD"), ("money_ratio", "EXPECTED_OBJECT"), ("basis_quantity", "UNKNOWN_OR_MISSING_FIELD"), ("currency", "UNSUPPORTED_CURRENCY")]:
            bindings = deepcopy(baseline)
            if kind == "ratio_money": bindings["inputs"]["selected"]["ratio_quantum"] = {"currency": "USD", "value": "0.0001"}
            elif kind == "money_ratio": bindings["inputs"]["selected"]["money_quantum"] = "0.01"
            elif kind == "basis_quantity": bindings["inputs"]["lines"][0]["basis"] = {"unit": "Download", "value": "0.01"}
            else: bindings["inputs"]["selected"]["money_quantum"]["currency"] = "EUR"
            package = precision.numeric_precision_package(fixture(), reference=self.reference)
            package["inputs"]["selected"] = bindings["inputs"]["selected"]
            package["inputs"]["lines"] = bindings["inputs"]["lines"]
            with self.subTest(kind=kind):
                with self.assertRaises((DataError, SPLException)): validate_module_package(package, resolve_module(self.reference, self.root))
                check = self.work("binding"); path = check / "bindings.json"; write_json(path, bindings)
                commands = [("native-ir", [ROOT / ".lake/build/bin/spl.exe", "interpret", work / "consumed.source.spl", path, "--link", work / "consumed.link.json"]),
                            ("native-emitted", [work / "Settlement.exe", path])]
                for label, command in commands:
                    actual = normalize_target(metadata(_stage(command, check / label)))
                    self.assertEqual(actual["status"], "blocked"); self.assertFalse(actual["emissions"] or actual["closing"])
                    self.assertEqual([row["code"] for row in actual["diagnostics"]], [code])
                OBSERVATIONS.append({"case_id": "physical-binding-negative", "kind": kind, "stage": "canonical-and-native-binding-admission", "financial_source_credit": False})

    def test_native_six_scenarios_and_previews(self): self.native_group("test_reference_six_scenarios_and_previews")
    def test_native_signed_ratio_modes_and_near_ties(self): self.native_group("test_reference_all_signed_ratio_modes_and_near_ties")
    def test_native_signed_money_modes_and_points(self): self.native_group("test_reference_all_signed_money_modes_and_points")
    def test_native_cancellation_noncent(self): self.native_group("test_reference_signed_cancellation_and_noncent_quantum")
    def test_native_every_precision_and_expression_unit(self): self.native_group("test_reference_every_precision_and_expression_unit")
    def test_native_rational_large_zero_empty_eight_lines(self): self.native_group("test_reference_rational_large_zero_empty_and_eight_lines")
    def test_native_permutation_split_merge_execution_metadata(self): self.native_group("test_reference_permutation_split_merge_and_execution_metadata")
    def test_native_policy_content_pins_repin(self): self.native_group("test_reference_policy_content_pins_and_explicit_same_label_repin")
    def test_native_invalid_quanta_modes_points_populations(self): self.native_group("test_reference_nonpositive_quanta_modes_points_precision_and_populations")
    def test_native_unicode_original_numbers_authority(self): self.native_group("test_reference_unicode_original_numbers_codec_and_authority")
