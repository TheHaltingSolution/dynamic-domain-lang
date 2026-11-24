"""Independent original-fact comparisons for the separately authored C02 SPL."""
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
from oracles.participation_bases import ParticipationBaseError, participation_bases, exact_json
from Tests.test_participation_base_oracle import fixture, set_measure, METHODS
from spl_compiler.artifacts import load_completed_result
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import read_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.model import SPLException
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target

bases = import_module("cases.participation-bases.build_modules")


class ParticipationBaseModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/participation-base-tests"; parent.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=parent); cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name); cls.folder = cls.root / "cases/participation-bases"; cls.folder.mkdir(parents=True)
        for name in ("participation-bases.spl", "policy.md", "neutral.json"):
            shutil.copyfile(ROOT / "cases/participation-bases" / name, cls.folder / name)
        for owner, key, value in ((bases, "ROOT", cls.root), (bases, "FOLDER", cls.folder), (registration, "ROOT", cls.root)):
            change = patch.object(owner, key, value); change.start(); cls.addClassCleanup(change.stop)
        cls.reference = bases.register_participation_bases()

    def run_fixture(self, data, *, backend="reference", output=None, mode="final"):
        package = bases.participation_base_package(data, reference=self.reference, mode=mode)
        result = bases.run_participation_base_package(package, self.root, backend=backend, artifact_dir=output)
        if output is not None:
            self.assertEqual(load_completed_result(output), result)
            self.assertEqual(read_json(Path(output) / "result.json"), result)
        if backend == "compare":
            self.assertEqual(result.get("trace_origin"), "native_ir_interpreter", result["diagnostics"])
            checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
            expected = normalize_target(evaluate(checked, inputs, openings).to_dict())
            emitted = normalize_target(run_generated(checked,
                {key: decode_value(value, checked.types[key]) for key, value in inputs.items()},
                {key: decode_value(value, checked.types[key]) for key, value in openings.items()}))
            for field in ("status", "emissions", "closing"): self.assertEqual(emitted[field], expected[field], field)
            self.assertEqual([x["code"] for x in emitted["diagnostics"]], [x["code"] for x in expected["diagnostics"]])
        return result

    def controls(self, data, result, *, preview=False):
        self.assertEqual(result["status"], "provisional" if preview else "calculated", result["diagnostics"])
        self.assertFalse(result["diagnostics"] or result["closing_state"])
        actual = bases.neutral_result(result["results"]["comparison"])
        self.assertEqual(actual, exact_json(participation_bases(data)))
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertTrue(result["results"]["reconciliation"])
        detail = result["results"]["original_detail"]
        self.assertEqual(json.loads(detail["originals"]["raw_original"]), data)
        self.assertEqual(detail["payment_evidence_status"], "not_part_of_profile")
        self.assertFalse(detail["bank_movement_created"])
        return actual

    def blocked(self, data):
        with self.assertRaises(ParticipationBaseError): participation_bases(data)
        result = self.run_fixture(data)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
        self.assertNotIn("result_digest", result)
        return result

    def test_reference_four_policies_full_intermediates_and_dimensioned_options(self):
        for method, earned in zip(METHODS, ("25", "20", "150", "75")):
            data = fixture(method); result = self.run_fixture(data)
            actual = self.controls(data, result)
            self.assertEqual(actual["earned"], earned)
            physical = result["results"]["comparison"]
            monetary = method in METHODS[:2]
            self.assertEqual("some" in physical["selected_money_basis"], monetary)
            self.assertEqual("some" in physical["selected_quantity_basis"], not monetary)
            self.assertEqual("some" in physical["selected_percentage"], monetary)
            self.assertEqual("some" in physical["selected_unit_rate"], not monetary)
            self.assertEqual(physical["quantity"]["unit"], "Download")
            if not monetary:
                self.assertEqual(physical["selected_unit_rate"]["some"]["per_unit"], "Download")
                self.assertEqual(physical["selected_unit_rate"]["some"]["currency"], "USD")

    def test_reference_asymmetric_monetary_net_and_quantity(self):
        for method, first, second in (("unit_rate", "150", "120"), ("unit_rate_then_participation", "75", "60")):
            data = fixture(method); set_measure(data, "deductions", "45")
            actual = self.controls(data, self.run_fixture(data))
            self.assertEqual((actual["net"], actual["quantity"], actual["earned"]), ("80", "100", first))
            data = fixture(method); set_measure(data, "usage", "80")
            actual = self.controls(data, self.run_fixture(data))
            self.assertEqual((actual["net"], actual["quantity"], actual["earned"]), ("100", "80", second))

    def test_reference_exact_fractions_known_zero_and_complete_empty(self):
        data = fixture("net_percent"); set_measure(data, "receipts", "1/3"); set_measure(data, "deductions", "1/6")
        self.assertEqual(self.controls(data, self.run_fixture(data))["earned"], "1/30")
        data["method"] = "unit_rate_then_participation"; set_measure(data, "usage", "1/3")
        self.assertEqual(self.controls(data, self.run_fixture(data))["earned"], "1/4")
        for method in METHODS:
            data = fixture(method)
            for kind in ("receipts", "deductions", "usage"): set_measure(data, kind, "0")
            self.assertEqual(self.controls(data, self.run_fixture(data))["earned"], "0")
            for kind in ("receipts", "deductions", "usage"): data[kind] = []
            for population in data["populations"]: population["row_ids"] = []
            self.assertEqual(self.controls(data, self.run_fixture(data))["earned"], "0")

    def test_reference_share_once_and_unused_rate_independence(self):
        for method in METHODS:
            data = fixture(method)
            if method in METHODS[:2]: data["terms"].update(participation_share="0", unit_rate="0")
            else: data["terms"]["percentage"] = "0"
            self.controls(data, self.run_fixture(data))
        for share, earned in (("0", "0"), ("1", "150"), ("1/3", "50")):
            data = fixture("unit_rate_then_participation"); data["terms"]["participation_share"] = share
            self.assertEqual(self.controls(data, self.run_fixture(data))["earned"], earned)

    def test_reference_distinct_equal_contributors_split_and_permutation(self):
        for method in METHODS:
            data = fixture(method)
            second = deepcopy(data["receipts"][0]); second.update(id="receipt-second", original_ref="original-second", amount="100")
            data["receipts"][0]["amount"] = "25"; data["receipts"].append(second); data["populations"][0]["row_ids"].append(second["id"])
            expected = self.controls(data, self.run_fixture(data))
            data["receipts"].reverse(); data["populations"].reverse()
            self.assertEqual(self.controls(data, self.run_fixture(data)), expected)
        data = fixture(); second = deepcopy(data["receipts"][0]); second.update(id="second", original_ref="second-original")
        data["receipts"].append(second); data["populations"][0].update(row_ids=["receipt-1", "second"], reported_total="250")
        self.assertEqual(self.controls(data, self.run_fixture(data))["earned"], "50")

    def test_reference_scope_authority_currency_and_unused_rows(self):
        for table in ("receipts", "deductions", "usage", "populations"):
            for field in bases.SCOPE:
                data = fixture("unit_rate"); data[table][0]["scope"][field] = "other"
                self.blocked(data)
        for field in bases.SCOPE:
            data = fixture(); data["terms"]["scope"][field] = "other"; self.blocked(data)
        data = fixture(); data["scope"]["currency"] = "EUR"; self.blocked(data)
        data = fixture(); data["terms"]["unit"] = "UsageMinute"; self.blocked(data)
        data = fixture(); data["terms"]["approved"] = False; self.blocked(data)

    def test_reference_populations_missing_incomplete_total_and_identity(self):
        for kind in ("receipts", "deductions", "usage"):
            for field, value in (("complete", False), ("row_ids", []), ("row_ids", ["receipt-1", "receipt-1"]), ("reported_total", "0")):
                data = fixture(); next(pop for pop in data["populations"] if pop["kind"] == kind)[field] = value; self.blocked(data)
        data = fixture(); data["populations"].pop(); self.blocked(data)
        data = fixture(); data["populations"][2]["kind"] = "receipts"; self.blocked(data)

    def test_reference_original_alias_duplicate_negative_and_loss_policy(self):
        data = fixture(); data["deductions"][0]["original_ref"] = data["receipts"][0]["original_ref"]; self.blocked(data)
        data = fixture(); data["usage"][0]["id"] = data["receipts"][0]["id"]; self.blocked(data)
        for kind in ("receipts", "deductions", "usage"):
            data = fixture("gross_percent"); set_measure(data, kind, "-1"); self.blocked(data)
        for method in METHODS:
            data = fixture(method); set_measure(data, "deductions", "126"); self.blocked(data)
        for field, value in (("percentage", "-1/10"), ("percentage", "1.01"), ("unit_rate", "-1"), ("participation_share", "1.01")):
            data = fixture(); data["terms"][field] = value; self.blocked(data)

    def test_reference_half_open_economic_knowledge_population_and_cutoff(self):
        mutations = [lambda d: d["receipts"][0].update(effective_date=d["period"]["end"]),
            lambda d: d["terms"]["effective"].update(end="2026-01-31"),
            lambda d: d["terms"].update(observed_at=d["cutoff"]),
            lambda d: d["terms"].update(observed_at="2026-01-11T00:00:00.000000001Z"),
            lambda d: d["receipts"][0].update(observed_at="2026-01-09T23:59:59.999999999Z"),
            lambda d: d["receipts"][0].update(observed_at="2026-02-02T00:00:00.000000001Z"),
            lambda d: d["populations"][0].update(observed_at=d["cutoff"]),
            lambda d: d["populations"][0].update(observed_at="2026-01-31T23:59:59.999999999Z")]
        for mutation in mutations:
            data = fixture(); mutation(data); self.blocked(data)
        data = fixture(); data["populations"][0]["observed_at"] = "2026-02-01T00:00:00Z"
        self.controls(data, self.run_fixture(data))

    def test_reference_fractional_offset_instants_unicode_and_raw_lexemes(self):
        identity = "e\u0301-\u7535\u5f71-\U0001f3ac:#\x00"
        data = fixture()
        for holder in (data, data["terms"], *data["populations"], *data["receipts"], *data["deductions"], *data["usage"]): holder["scope"]["participant_id"] = identity
        data["receipts"][0]["amount"] = "+00125.000"
        data["receipts"][0]["observed_at"] = "2026-01-11T01:00:00.000000001+01:00"
        self.controls(data, self.run_fixture(data))
        data["terms"]["scope"]["participant_id"] = "\u00e9-\u7535\u5f71-\U0001f3ac:#\x00"; self.blocked(data)
        for stamp in ("2026-01-10T23:00:00-01:00", "2026-01-11T00:00:00.000000001Z"):
            data = fixture(); data["receipts"][0]["observed_at"] = stamp; self.controls(data, self.run_fixture(data))
        data = fixture(); data["populations"][0]["observed_at"] = "2026-02-02T23:59:59.999999999Z"; self.controls(data, self.run_fixture(data))
        data["populations"][0]["observed_at"] = "2026-02-03T00:00:00.000000001Z"; self.blocked(data)

    def test_reference_declared_32_row_boundary(self):
        data = fixture(); original = data["receipts"][0]
        data["receipts"] = [{**deepcopy(original), "id": str(i), "original_ref": "original:" + str(i), "amount": "1"} for i in range(32)]
        data["populations"][0].update(row_ids=[row["id"] for row in data["receipts"]], reported_total="32")
        self.assertEqual(self.controls(data, self.run_fixture(data))["earned"], "32/5")
        data["receipts"].append({**deepcopy(original), "id": "33", "original_ref": "original:33", "amount": "1"})
        data["populations"][0].update(row_ids=[row["id"] for row in data["receipts"]], reported_total="33")
        self.blocked(data)

    def test_reference_direct_physical_dimension_population_and_identity_checks(self):
        # Generic binding/reference controls deliberately bypass the selected
        # wrapper's raw-original custody check; no native credit is implied.
        for kind in ("unit", "pop_dimension", "raw_ids", "unused_negative"):
            package = bases.participation_base_package(fixture("gross_percent"), reference=self.reference)
            if kind == "unit": package["inputs"]["usage"][0]["amount"]["unit"] = "UsageMinute"
            elif kind == "pop_dimension":
                pop = package["inputs"]["populations"][2]; pop["money_total"] = {"some": {"value": "100", "currency": "USD"}}; pop["quantity_total"] = {"none": True}
            elif kind == "raw_ids": package["inputs"]["originals"]["usage_ids"] = []
            else: package["inputs"]["usage"][0]["amount"]["value"] = "-1"
            result = run_module_package(package, self.root, backend="reference")
            self.assertEqual(result["status"], "blocked", result["diagnostics"])
            self.assertFalse(result["results"] or result["closing_state"])

    def test_checker_keeps_money_quantity_ratio_and_per_unit_rate_distinct(self):
        prefix = 'schedule Dimensions language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" { input m:Money<USD>; input q:Quantity<Download>; input r:Rate<Download,USD>; input p:Ratio; '
        for expression in ("m + q", "m * r", "q - m", "r + p"):
            with self.assertRaises(SPLException): check_schedule(parse(prefix + 'emit "invalid" = ' + expression + '; }'))
        checked = check_schedule(parse(prefix + 'emit "earned" = q * r; }'))
        self.assertEqual(str(checked.schedule["declarations"][-1]["expr"]["_type"]), "Money<USD>")

    def test_adapter_transport_roundtrip_shape_codec_and_no_oracle_or_totals(self):
        data = fixture(); before = deepcopy(data); typed = bases.transport(data); bases.validate_original_transport(typed); self.assertEqual(data, before)
        typed["receipts"][0]["amount"]["value"] = "999"
        with self.assertRaisesRegex(ValueError, "BASE_TYPED_RAW_MISMATCH"): bases.validate_original_transport(typed)
        for key in ("net", "selected_basis", "earned", "solved_total"):
            data = fixture(); data[key] = "1"
            with self.assertRaises(ValueError): bases.participation_base_package(data, reference=self.reference)
        for scalar in (True, .2, "1e3", " 1", "1/0"):
            data = fixture(); data["terms"]["percentage"] = scalar
            with self.assertRaises(ValueError): bases.participation_base_package(data, reference=self.reference)
        for stamp in ("2026-02-30T00:00:00Z", "2026-01-11T24:00:00Z", "2026-01-11T00:00:60Z", "2026-01-11T00:00:00+24:00"):
            data = fixture(); data["receipts"][0]["observed_at"] = stamp
            with self.assertRaises((ValueError, SPLException)): bases.participation_base_package(data, reference=self.reference)
        values = ["a", "aa", "e\u0301", "\u00e9", "\u7535\u5f71", "\U0001f3ac", "x:#\x00"]
        self.assertEqual(sorted(values), [bases.decode_identity(x) for x in sorted(map(bases.encode_identity, values))])
        for value in ("", "6A", "0", "ff", "c080", "eda080"):
            with self.assertRaises(ValueError): bases.decode_identity(value)
        tree = ast.parse((ROOT / "cases/participation-bases/build_modules.py").read_text())
        self.assertFalse(any(node.module and node.module.startswith("oracles") for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)))
        calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"sum", "min", "max", "participation_bases"})
        for name in ("build_modules.py", "participation-bases.spl"): self.assertNotIn(b"\r", (ROOT / "cases/participation-bases" / name).read_bytes())

    def test_reference_validated_stateless_bundle_and_same_complete_preview(self):
        data = fixture("unit_rate_then_participation")
        result = self.run_fixture(data, output=self.root / "final"); self.controls(data, result)
        package = bases.participation_base_package(data, reference=self.reference)
        self.assertFalse(package["state_cells"])
        preview = self.run_fixture(data, mode="preview", output=self.root / "preview"); self.controls(data, preview, preview=True)
        self.assertEqual(result["results"], preview["results"])

    def test_public_wrapper_rechecks_prepared_originals_and_atomically_replaces_prior_success(self):
        destination = self.root / "public-preparation"
        self.controls(fixture(), self.run_fixture(fixture(), output=destination))
        invocation = read_json(destination / "completion.json")["invocation_id"]
        for kind in ("receipt_and_total", "method", "cutoff", "scope", "period", "project", "state", "malformed_raw", "duplicate_raw_key"):
            package = bases.participation_base_package(fixture(), reference=self.reference)
            if kind == "receipt_and_total":
                package["inputs"]["receipts"][0]["amount"]["value"] = "250"
                package["inputs"]["populations"][0]["money_total"]["some"]["value"] = "250"
                # Generic execution trusts prepared typed bindings. It does not
                # parse/authenticate the selected profile's raw JSON envelope.
                generic = run_module_package(package, self.root, backend="reference")
                self.assertEqual(generic["status"], "calculated")
                self.assertEqual(bases.neutral_result(generic["results"]["comparison"])["earned"], "50")
            elif kind == "method": package["parameters"]["method"] = "unit_rate"
            elif kind == "cutoff":
                package["parameters"]["cutoff"] = "2026-02-04T00:00:00Z"; package["manifest"]["cutoff"] = "2026-02-04T00:00:00Z"
            elif kind == "scope": package["scope"]["purpose"] = "another-purpose"
            elif kind == "period": package["manifest"]["period"] = {"start": "2026-01-01", "end": "2026-02-02"}
            elif kind == "project": package["inputs"]["project"] = bases.encode_identity("another-title")
            elif kind == "state": package["state_cells"] = [{"invented": True}]
            elif kind == "malformed_raw": package["inputs"]["originals"]["raw_original"] = "{"
            else: package["inputs"]["originals"]["raw_original"] = '{"case_id":"duplicate",' + package["inputs"]["originals"]["raw_original"][1:]
            before = deepcopy(package)
            with patch.object(bases, "run_module_package") as executor:
                result = bases.run_participation_base_package(package, self.root, backend="reference", artifact_dir=destination)
                executor.assert_not_called()
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["diagnostics"][0]["code"], "BASE_PREPARED_PACKAGE_MISMATCH")
            self.assertFalse(result["results"] or result["statements"] or result["detail"] or result["closing_state"])
            self.assertNotIn("result_digest", result)
            self.assertEqual(load_completed_result(destination), result)
            self.assertEqual(read_json(destination / "result.json"), result)
            next_invocation = read_json(destination / "completion.json")["invocation_id"]
            self.assertNotEqual(next_invocation, invocation); invocation = next_invocation
            self.assertEqual(package, before)

    def test_adapter_known_utc_unknown_local_offset_and_range_boundaries(self):
        data = fixture()
        data["cutoff"] = "2026-02-03t00:00:00-00:00"
        data["terms"]["observed_at"] = "2025-12-01t00:00:00-00:00"
        for kind in ("receipts", "deductions", "usage", "populations"):
            for row in data[kind]: row["observed_at"] = row["observed_at"].replace("T", "t").replace("Z", "-00:00")
        result = self.run_fixture(data); self.controls(data, result)
        detail = result["results"]["original_detail"]
        self.assertEqual(detail["originals"]["unknown_local_offset_paths"], ["cutoff", "terms.observed_at", "receipts.0.observed_at", "deductions.0.observed_at", "usage.0.observed_at", "populations.0.observed_at", "populations.1.observed_at", "populations.2.observed_at"])
        self.assertEqual(detail["unknown_local_offset_meaning"], "UTC_known_local_offset_unknown_no_local_zone_inferred")
        self.assertEqual(json.loads(detail["originals"]["raw_original"]), data)
        data = fixture(); data["receipts"][0]["observed_at"] = "2026-01-11t00:00:00z"; self.controls(data, self.run_fixture(data))
        for stamp in ("2026-01-11T00:00:00", "0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"):
            with self.assertRaises((ValueError, SPLException)): bases.stamp(stamp)
            data = fixture(); data["terms"]["observed_at"] = stamp
            with self.assertRaises(ParticipationBaseError): participation_bases(data)

    def test_native_four_policies_and_asymmetric_dimension_controls(self):
        for method in METHODS:
            data = fixture(method); self.controls(data, self.run_fixture(data, backend="compare", output=self.root / ("native-" + method)))
        for kind, amount in (("deductions", "45"), ("usage", "80")):
            data = fixture("unit_rate_then_participation"); set_measure(data, kind, amount)
            self.controls(data, self.run_fixture(data, backend="compare", output=self.root / ("native-" + kind)))
