"""Independent transport, mapping, controls and atomic-output acceptance checks."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from spl_compiler.adapter import rq07
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import (DataError, amount, exact, file_digest, loads, number,
                                  read_csv, read_json, write_csv, write_json)
from spl_compiler.evaluator import evaluate
from spl_compiler.fixtures import sv_package
from spl_compiler.parser import parse
from spl_compiler.run import ROOT, bind_package, project, run_package
from spl_compiler.schema import validate_package


SOURCE = ROOT / "cases/rq07/source"
SCHEDULE = ROOT / "cases/sv/rq07.spl"


def adapted():
    return rq07(SOURCE, observed_at="2026-04-03T00:00:00Z", ingested_at="2026-11-20T00:00:00Z")


class TransportTests(unittest.TestCase):
    def test_strict_json(self):
        for data in ['{"x":1,"x":2}', '{"x":"a","\\u0078":"b"}', '{"x":1.5}',
                     '{"x":NaN}', '{"x":null}', '\ufeff{}', '{}{}', '{"x":"\\ud800"}']:
            with self.subTest(data=data), self.assertRaises(DataError):
                loads(data)
        self.assertEqual(loads('{"zero":"0","missing":[]}'), {"zero": "0", "missing": []})

    def test_exact_serialization(self):
        for value, expected in [(Fraction(1, 3), {"numerator": "1", "denominator": "3"}),
                                (Fraction(-1, 200), "-0.005"), (Fraction(12345, 100), "123.45"), (Fraction(0), "0")]:
            self.assertEqual(number(value), expected)
            self.assertEqual(exact(expected), value)
        for value in ["01", "1e3", "+1", 0.1, {"numerator": "2", "denominator": "4"},
                      {"numerator": "0", "denominator": "2"}, {"numerator": "1", "denominator": "0"}]:
            with self.subTest(value=value), self.assertRaises(DataError):
                exact(value)

    def test_csv_roundtrip_and_headers(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "example.csv"
            rows = [{"id": "a", "note": 'Quoted "text", with\nnewline', "date": ""}]
            write_csv(path, rows, ["id", "note", "date"])
            self.assertEqual(read_csv(path, ["date", "note", "id"]), rows)
            for bad in ['id,id\na,b\n', 'id,note,date\na,b\n', 'id,note,date\na,"unterminated,\n', 'id,note,date\na,b"c,\n']:
                path.write_text(bad, encoding="utf-8")
                with self.assertRaises(DataError):
                    read_csv(path, ["id", "note", "date"])


class PackageTests(unittest.TestCase):
    def test_rq07_native_receipt_to_statement_and_lineage(self):
        p = bind_package(adapted(), SCHEDULE)
        validate_package(p)
        r = run_package(p, SCHEDULE)
        self.assertEqual(r["diagnostics"], [])
        self.assertEqual(r["statements"][0]["payable"], "18000")
        self.assertEqual(r["statements"][0]["earned"], "33000")
        self.assertEqual(r["statements"][0]["recouped"], "15000")
        self.assertEqual(r["closing_state"][0]["quantity"], "0")
        self.assertEqual({d["asset_id"]: d["cash"] for d in r["detail"]}, {"PIC-A": "100000", "PIC-B": "60000"})
        self.assertEqual(r["payment_evidence_status"], "no_event_supplied")
        self.assertNotIn("paid", r["statements"][0])
        self.assertTrue(any(x.get("allocation_id") for x in r["source_to_target_lineage"]))
        self.assertEqual(len(r["trace"]), len({node["node_id"] for node in r["trace"]}))
        controls = {b["batch_id"]: b["control_totals"][0]["signed_total"] for b in p["source_batches"]}
        self.assertEqual(controls, {"raw_invoice_lines": "210000", "raw_bank_receipts": "160000",
                                   "raw_cash_applications": "160000", "raw_cost_lines": "17500", "raw_acquisition_funding": "150000"})
        for f in p["financial_facts"]:
            if f["event_kind"] == "incurred_cost":
                self.assertNotIn("incurred_date", f["dates"])
                if f["asset_id"] == "PIC-B":
                    self.assertNotIn("paid_date", f["dates"])
        self.assertTrue(any(d["disposition"] == "excluded" and d["fact_id"] == "cost/COST-X:1" for d in r["input_dispositions"]))

    def test_independent_discriminators_detect_wrong_methodologies(self):
        inputs, openings, *_ = project(adapted())
        checked = check_schedule(parse(SCHEDULE.read_text()))
        def payable(values):
            out = evaluate(checked, values, openings)
            self.assertEqual(out.status, "calculated", out.diagnostics)
            return out.emissions["pool"]["payable"]
        billed = deepcopy(inputs)
        next(r for r in billed["receipts"] if r["fact_id"] == "receipt/APP-01")["amount"]["value"] = "110000"
        self.assertEqual(payable(billed), Fraction(25500))
        wrong_cost = deepcopy(inputs)
        wrong_cost["eligible_costs"].append({"fact_id": "wrong-cost", "asset_id": "PIC-B", "amount": {"value": "2000", "currency": "USD"},
                                              "recognition_date": "2026-03-30", "recognition_policy_ref": "wrong-policy", "eligibility_decision_id": "wrong-policy"})
        self.assertEqual(payable(wrong_cost), Fraction(17200))
        wrong_weights = deepcopy(inputs)
        for r in wrong_weights["receipts"]:
            if r["fact_id"].startswith("application/APP-02/"):
                r["amount"]["value"] = "50000"
        self.assertEqual(payable(wrong_weights), Fraction(15800))
        wrong_date = deepcopy(inputs)
        for r in wrong_date["receipts"]:
            r["cash_received_date"] = "2026-04-02"
        out = evaluate(checked, wrong_date, openings)
        self.assertEqual(out.status, "blocked")
        self.assertEqual(out.diagnostics[0]["code"], "SV_NEGATIVE_EARNINGS_OUTSIDE_PILOT")

    def test_same_total_cannot_authorize_changed_bundle_weights(self):
        p = adapted()
        for a in p["allocations"]:
            a["weight"] = "0.5"
        r = run_package(bind_package(p, SCHEDULE), SCHEDULE, backend="reference")
        self.assertEqual(r["status"], "blocked")
        self.assertEqual(r["diagnostics"][0]["code"], "ALLOCATION_AUTHORITY")
        self.assertEqual(r["closing_state"], [])

    def test_eligibility_cannot_be_changed_under_same_authority(self):
        p = adapted()
        p["parameters"]["cost_decisions"][-1]["eligible"] = True
        r = run_package(bind_package(p, SCHEDULE), SCHEDULE, backend="reference")
        self.assertEqual(r["diagnostics"][0]["code"], "COST_POLICY_MISMATCH")

    def test_unknown_fields_versions_duplicates_controls_and_hashes_block(self):
        changes = [lambda p: p.update(unreviewed_economic_extension="1"),
                   lambda p: p["manifest"].update(schema_version="future"),
                   lambda p: p["financial_facts"].append(deepcopy(p["financial_facts"][0])),
                   lambda p: p["source_batches"][0]["control_totals"][0].update(signed_total="999")]
        for change in changes:
            p = adapted()
            change(p)
            r = run_package(bind_package(p, SCHEDULE), SCHEDULE, backend="reference")
            self.assertEqual(r["status"], "blocked", r)
            self.assertEqual(r["statements"], [])
            self.assertEqual(r["closing_state"], [])
        p = bind_package(adapted(), SCHEDULE)
        p["parameters"]["cost_decisions"][0]["reason"] = "changed without repinning"
        r = run_package(p, SCHEDULE, backend="reference")
        self.assertEqual(r["diagnostics"][0]["code"], "MANIFEST_DIGEST_MISMATCH")

    def test_failed_rerun_clears_output_ports(self):
        source = ROOT / "cases/sv/sv01.spl"
        with tempfile.TemporaryDirectory() as d:
            good = run_package(bind_package(sv_package(), source), source, backend="reference", artifact_dir=d)
            self.assertEqual(good["status"], "calculated")
            broken = sv_package()
            broken["parameters"]["funding_snapshot"]["complete"] = False
            bad = run_package(bind_package(broken, source), source, backend="reference", artifact_dir=d)
            self.assertEqual(bad["status"], "blocked")
            self.assertEqual(read_json(Path(d) / "closing-state.json"), [])
            self.assertEqual(read_json(Path(d) / "statement.json"), [])

    def test_incurred_profile_cannot_consume_posting_only_costs(self):
        p = adapted()
        p["profile"] = "sv-incurred-v1"
        p["parameters"]["cost_date_basis"] = "incurred_date"
        source = ROOT / "cases/sv/sv01.spl"
        r = run_package(bind_package(p, source), source, backend="reference")
        self.assertEqual(r["diagnostics"][0]["code"], "REQUIRED_COST_DATE")

    def test_agreement_role_reference_and_state_scenario_closure(self):
        source = ROOT / "cases/sv/sv01.spl"
        mutations = [lambda p: p["agreements"][0].update(role_ids=[]),
                     lambda p: p["agreements"][0].update(interpretation_ref="unknown@1"),
                     lambda p: p["agreements"][0].update(effective={"start": "2026-01-01", "end": "2026-02-01"}),
                     lambda p: p["roles"][1].update(effective={"start": "2026-01-01", "end": "2026-02-01"}),
                     lambda p: p["state_cells"][0].update(scenario_id="unrelated-scenario")]
        for mutate in mutations:
            p = sv_package()
            mutate(p)
            r = run_package(bind_package(p, source), source, backend="reference")
            self.assertEqual(r["status"], "blocked", r)
            self.assertEqual(r["closing_state"], [])


if __name__ == "__main__":
    unittest.main()
