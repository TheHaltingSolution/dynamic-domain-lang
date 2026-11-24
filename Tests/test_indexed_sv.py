"""Explicit experimental source: financial controls, not old/new trace identity.

Original-fact SV controls are calculated before projection. Direct typed-view
cases separately preserve the old compiler's empty/duplicate/order behavior.
Native methods require root's prebuilt current spl_sv/spl_sv_indexed targets
and never rebuild. Both use the current memoizing emitter; the old compiler's
executables are separately qualified historical archives.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from oracles.skouras import SkourasOracleError, skouras
from scripts.spl_benchmark import receipt_probe
from scripts.spl_mixed_benchmark import check_projection, check_target, target_expected
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import DataError, exact, loads, number, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT, lean_environment
from spl_compiler.parser import parse
from spl_compiler.run import bind_package, project, normalize_target
from spl_compiler.schema import validate_package
from Tests import test_skouras_oracle as original_fixtures
from validation.mixed_workloads import canonical_bytes, generate_mixed


LEGACY = ROOT / "cases/sv/sv01.spl"
INDEXED = ROOT / "cases/sv/sv01-indexed.spl"
OLD_SOURCE_SHA = "0ecd2b31d1be9e8e3764cacc8e1135422fb32786bae8f8a3a1833db9615d6cec"
OBSERVATIONS = []
EVIDENCE_DIR = None  # Optional external launcher destination, never a test bypass.


def financial(outcome):
    outcome = normalize_target(outcome)
    return {"status": outcome["status"], "emissions": outcome["emissions"], "closing": outcome["closing"],
            "diagnostics": [row["code"] for row in outcome["diagnostics"]]}


def checked(path):
    return check_schedule(parse(path.read_text(encoding="utf-8")))


def refresh_source_controls(data):
    """Mechanical source-byte/count/amount metadata only; never earning answers."""
    package = data["package"]
    for batch in package["source_batches"]:
        key = {name: batch[name] for name in ("source_system", "batch_id", "version")}
        rows = [row for row in package["financial_facts"] if row["batch_ref"] == key]
        batch.update(row_count=len(rows), sha256=hashlib.sha256(canonical_bytes(rows)).hexdigest())
        kinds = sorted({row["event_kind"] for row in rows})
        batch["control_totals"] = [{"amount_kind": kind, "currency": "USD",
                                   "signed_total": number(sum(exact(row["amount"]["value"]) for row in rows if row["event_kind"] == kind)),
                                   "absolute_total": number(sum(abs(exact(row["amount"]["value"])) for row in rows if row["event_kind"] == kind))}
                                  for kind in kinds]
    return data


def original_cases():
    baseline = original_fixtures.fixture()
    yield "original", baseline
    allocated = original_fixtures.bundle_fixture()
    authority = allocated["allocation_authorities"][0]
    decision = next(row for item in allocated["package"]["interpretations"] for row in item["decisions"]
                    if row["decision_id"] == authority["authority_ref"])
    decision["allocation_terms"] = deepcopy(authority["weights"])
    yield "allocated-parent-with-invoice", refresh_source_controls(allocated)
    fractions = deepcopy(baseline)
    package = fractions["package"]
    package["financial_facts"][0]["amount"]["value"] = {"numerator": "1", "denominator": "3"}
    package["financial_facts"][2]["amount"]["value"] = "0"
    package["state_cells"][0]["quantity"] = "0"
    next(row for row in package["evidence_events"] if row["event_id"] == "fund-b-dist")["amount"]["value"] = "20000"
    yield "exact-fraction-funding", refresh_source_controls(fractions)
    cutoff = deepcopy(baseline)
    cutoff["package"]["manifest"]["cutoff"] = "2026-04-03T00:00:00.0000002Z"
    cutoff["package"]["evidence_events"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
    yield "exact-subsecond-cutoff", cutoff
    for day in ("2025-12-31", "2026-01-01", "2026-03-31", "2026-04-01"):
        dates = deepcopy(baseline)
        for row in dates["package"]["financial_facts"]:
            if row["asset_id"] == "picture-a":
                field = row["temporal_basis"]["kind"]
                row["dates"][field] = day
                row["temporal_basis"]["date"] = day
        yield "date-" + day, refresh_source_controls(dates)
    yield "mixed100-with-exclusions", generate_mixed(100)["neutral"]


def project_original(data):
    untouched = deepcopy(data)
    oracle = skouras(data)  # This must precede bind/project.
    bound = bind_package(data["package"], INDEXED)
    validate_package(bound)
    inputs, aliases, lineage, dispositions = project(bound)
    openings = {"prepayment": aliases["sv/participant-prepayment/main-pool"]}
    check_projection({"neutral": data}, oracle, inputs, openings, lineage, dispositions)
    if data != untouched:
        raise AssertionError("Original neutral facts changed during oracle/projection")
    return ({"inputs": inputs, "openings": openings}, target_expected(oracle),
            {"canonical_package": bound, "source_to_target_lineage": lineage, "input_dispositions": dispositions})


def raw_cases():
    initial = receipt_probe(4, 3)
    yield "three-titles-one-without-cash", initial
    empty = deepcopy(initial)
    empty["inputs"]["pictures"] = []
    empty["openings"]["prepayment"]["value"] = "7"
    yield "empty-universe-retains-advance", empty
    duplicate = deepcopy(initial)
    duplicate["inputs"]["pictures"].append(deepcopy(duplicate["inputs"]["pictures"][0]))
    yield "duplicate-picture-preserves-old-multiplicity", duplicate
    reordered = deepcopy(initial)
    reordered["inputs"]["pictures"].reverse()
    reordered["inputs"]["receipts"].reverse()
    yield "supplied-picture-and-source-order", reordered
    unrelated = deepcopy(initial)
    unrelated["inputs"]["receipts"][0]["asset_id"] = "outside-universe"
    yield "unrelated-asset-not-an-output-title", unrelated
    both = deepcopy(initial)
    both["openings"]["prepayment"]["value"] = "-1"
    both["inputs"]["pictures"][0]["funding_share"] = "2"
    yield "opening-error-before-share", both
    invalid = deepcopy(initial)
    invalid["inputs"]["pictures"][0]["funding_share"] = "2"
    yield "first-invalid-share", invalid
    negative = deepcopy(initial)
    first_id = negative["inputs"]["pictures"][0]["asset_id"]
    negative["inputs"]["eligible_costs"] = [{"fact_id": "large-cost", "asset_id": first_id,
                                              "amount": {"value": "100", "currency": "USD"},
                                              "incurred_date": "2026-02-01", "eligibility_decision_id": "selected"}]
    negative["inputs"]["pictures"][1]["funding_share"] = "2"
    yield "first-negative-before-later-invalid-share", negative
    malformed = deepcopy(empty)
    malformed["inputs"]["receipts"][0]["cash_received_date"] = "2026-02-30"
    yield "typed-decode-invalid-unused-date", malformed


class IndexedSVReferenceTests(unittest.TestCase):
    def test_original_source_bytes_and_explicit_experimental_name_are_preserved(self):
        self.assertEqual(hashlib.sha256(LEGACY.read_bytes()).hexdigest(), OLD_SOURCE_SHA)
        self.assertNotEqual(checked(LEGACY).schedule["name"], checked(INDEXED).schedule["name"])

    def test_original_fact_controls_precede_projection_for_all_financial_cases(self):
        for label, data in original_cases():
            with self.subTest(case=label):
                values, expected, _ = project_original(data)
                for path in (LEGACY, INDEXED):
                    actual = evaluate(checked(path), values["inputs"], values["openings"]).to_dict()
                    check_target(actual, expected)
                OBSERVATIONS.append({"case": label, "scope": "original-fact oracle before projection", "backend": "both-source Python reference", "status": "passed"})

    def test_zero_order_and_business_failures_preserve_old_source_observations(self):
        errors = {"opening-error-before-share": "NEGATIVE_OPENING_ADVANCE", "first-invalid-share": "INVALID_FUNDING_SHARE",
                  "first-negative-before-later-invalid-share": "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT",
                  "typed-decode-invalid-unused-date": "INVALID_DATE"}
        for label, values in raw_cases():
            with self.subTest(case=label):
                old = evaluate(checked(LEGACY), values["inputs"], values["openings"]).to_dict()
                new = evaluate(checked(INDEXED), values["inputs"], values["openings"]).to_dict()
                self.assertEqual(financial(new), financial(old))
                if label in errors:
                    self.assertEqual(new["diagnostics"][0]["code"], errors[label])
                    self.assertEqual(new["emissions"], {})
                    self.assertEqual(new["closing"], {})
                if label == "empty-universe-retains-advance":
                    self.assertEqual(new["emissions"]["titles"], [])
                    self.assertEqual(new["closing"]["prepayment"], "7")
                    groups = [row for row in new["trace"] if row["kind"] == "group_by"]
                    self.assertTrue(groups)
                    self.assertTrue(all(row["occurrences"] == [] and row["result"] == [] for row in groups))

    def test_equal_cutoff_is_rejected_before_financial_projection_or_emitted_credit(self):
        data = original_fixtures.fixture()
        data["package"]["evidence_events"][0]["observed_at"] = data["package"]["manifest"]["cutoff"]
        with self.assertRaisesRegex(SkourasOracleError, "SV_FUNDING_CUTOFF"):
            skouras(data)
        bound = bind_package(data["package"], INDEXED)
        with self.assertRaises(DataError):
            validate_package(bound)
        OBSERVATIONS.append({"case": "funding-at-cutoff", "backend": "independent original-fact oracle + canonical admission",
                             "status": "blocked_before_projection", "native_financial_execution": "not_executed"})


class IndexedSVNativeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        suffix = ".exe" if os.name == "nt" else ""
        self.frontend = ROOT / ".lake/build/bin" / ("spl" + suffix)
        self.old_target = self.frontend.with_name("spl_sv" + suffix)
        self.new_target = self.frontend.with_name("spl_sv_indexed" + suffix)
        self.assertTrue(self.new_target.is_file(), "Root must build spl_sv_indexed before native checks")
        _, self.env = lean_environment()

    def invoke(self, command, evidence=None):
        result = subprocess.run(list(map(str, command)), cwd=ROOT, env=self.env, capture_output=True, timeout=45)
        self.assertEqual(result.stderr, b"")
        outcome = loads(result.stdout)
        self.assertIn(result.returncode, (0, 1))
        if evidence is not None:
            evidence.write_bytes(result.stdout)
        return outcome

    def compare(self, label, values, expected=None):
        bindings = self.work / "bindings.json"
        write_json(bindings, values)
        destination = Path(EVIDENCE_DIR) / "native" / label if EVIDENCE_DIR is not None else None
        if destination is not None:
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "bindings.json").write_bytes(bindings.read_bytes())
            if expected is not None:
                write_json(destination / "independent-expected.json", expected)
        outcomes = {}
        commands = {"old_target": [self.old_target, bindings], "new_target": [self.new_target, bindings],
                    "old_ir": [self.frontend, "interpret", LEGACY, bindings],
                    "new_ir": [self.frontend, "interpret", INDEXED, bindings]}
        for backend, command in commands.items():
            outcomes[backend] = self.invoke(command, destination / (backend + ".json") if destination is not None else None)
        for backend, outcome in outcomes.items():
            with self.subTest(case=label, backend=backend):
                self.assertEqual(financial(outcome), financial(outcomes["old_target"]))
                if expected is not None:
                    check_target(outcome, expected)
        self.assertEqual(outcomes["new_ir"]["trace_origin"], "native_ir_interpreter")
        if label == "empty-universe-retains-advance":
            self.assertFalse(any(node["kind"] == "instance" for node in outcomes["new_ir"]["trace"]))
            self.assertEqual(normalize_target(outcomes["new_target"])["closing"], {"prepayment": "7"})
        if label in {"supplied-picture-and-source-order", "duplicate-picture-preserves-old-multiplicity"}:
            self.assertEqual([row["asset_id"] for row in outcomes["new_target"]["emissions"]["titles"]],
                             [row["asset_id"] for row in values["inputs"]["pictures"]])
        seen = set()
        for node in outcomes["new_ir"]["trace"]:
            self.assertTrue(set(node["dependencies"]) <= seen)
            self.assertNotIn(node["node_id"], seen)
            seen.add(node["node_id"])
        OBSERVATIONS.append({"case": label, "backend": "old/new emitted + old/new native IR",
                             "status": outcomes["new_ir"]["status"], "diagnostics": [d["code"] for d in outcomes["new_ir"]["diagnostics"]],
                             "bindings_sha256": hashlib.sha256(bindings.read_bytes()).hexdigest(),
                             "financial_outcome": financial(outcomes["new_target"]),
                             "new_trace_nodes": len(outcomes["new_ir"]["trace"]), "old_trace_nodes": len(outcomes["old_ir"]["trace"]),
                             "trace_relation": "different program graphs; complete financial/error/state comparison only"})
        return outcomes

    def test_generated_demo_is_exact_fresh_native_emission(self):
        for source, emission in ((LEGACY, "Demos/SV.lean"), (INDEXED, "Demos/SVIndexed.lean")):
            generated = self.work / "Generated.lean"
            result = subprocess.run([str(self.frontend), "compile", str(source), str(generated)],
                                    cwd=ROOT, env=self.env, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(generated.read_bytes(), (ROOT / emission).read_bytes())

    def test_original_fact_financials_match_both_compiled_targets_and_native_audits(self):
        for label, data in original_cases():
            values, expected, metadata = project_original(data)
            if EVIDENCE_DIR is not None:
                destination = Path(EVIDENCE_DIR) / "native" / label
                destination.mkdir(parents=True, exist_ok=True)
                write_json(destination / "original-neutral.json", data)
                for name, value in metadata.items():
                    write_json(destination / (name + ".json"), value)
            self.compare(label, values, expected)

    def test_empty_order_duplicate_and_error_precedence_match_without_trace_identity_claim(self):
        for label, values in raw_cases():
            self.compare(label, values)


if __name__ == "__main__":
    unittest.main()
