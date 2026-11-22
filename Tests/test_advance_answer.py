"""RR-01 checkpoints: actual funding, separate evidence and exact as-of selection."""
from copy import deepcopy
from fractions import Fraction
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import money, read_json
from spl_compiler.evaluator import evaluate
from spl_compiler.emitter import run_generated
from spl_compiler.instant import parse_instant
from spl_compiler.lean_tools import ROOT
from spl_compiler.mechanisms import run_mechanism
from spl_compiler.model import SPLException
from spl_compiler.parser import parse


def bindings():
    return read_json(ROOT / "cases/mechanisms/advance-issues-bindings.json")


def reference(values):
    source = ROOT / "cases/mechanisms/advance-issues.spl"
    return evaluate(check_schedule(parse(source.read_text(encoding="utf-8"))), **values).to_dict()


class AdvanceAnswerTests(unittest.TestCase):
    def assert_blocked(self, result, code):
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["emissions"], {})
        self.assertEqual(result["closing"], {})
        self.assertEqual(result["diagnostics"][0]["code"], code)

    def test_june_funding_observed_july_two_is_q2_before_july_three_cutoff(self):
        result = run_mechanism("advance-issues", bindings())
        line = result["emissions"]["advances"]
        self.assertEqual([line[k] for k in ["additions", "earned", "recovered", "payable", "closing_balance"]],
                         ["15000", "10000", "10000", "0", "5000"])
        row = result["emissions"]["advance_issue_audit"][0]
        self.assertEqual((row["issue_id"], row["disbursement_id"], row["source_title_id"]),
                         ("advance-1", "disbursement-1", "title-a"))
        self.assertTrue(row["included"])

    def test_actual_july_funding_is_q3_regardless_june_scheduled_due_date(self):
        values = bindings()
        # A scheduled due date is not an economic-date input in this policy.
        for key in ["issues", "evidence"]:
            values["inputs"][key][0]["funded_date"] = "2026-07-01"
        q2 = reference(values)
        self.assertEqual(q2["emissions"]["advances"]["additions"], "0")
        values["inputs"]["scope"]["period"] = {"start": "2026-07-01", "end": "2026-10-01"}
        q3 = run_mechanism("advance-issues", values)
        self.assertEqual(q3["emissions"]["advances"]["additions"], "15000")

    def test_both_observations_are_strictly_before_cutoff(self):
        for key, flag in [("issues", "issue_available"), ("evidence", "evidence_available")]:
            values = bindings()
            values["inputs"][key][0]["observed_at"] = "2026-07-03T02:00:00+02:00"
            result = run_mechanism("advance-issues", values)
            self.assertEqual(result["status"], "calculated")
            self.assertEqual(result["emissions"]["advances"]["additions"], "0")
            self.assertFalse(result["emissions"]["advance_issue_audit"][0][flag])

    def test_offsets_are_normalized_and_subseconds_are_exact(self):
        values = bindings()
        values["inputs"]["issues"][0]["observed_at"] = "2026-07-03T01:00:00+02:00"
        values["inputs"]["evidence"][0]["observed_at"] = "2026-07-03T00:00:00.00000000000000000001Z"
        excluded = run_mechanism("advance-issues", values)
        self.assertEqual(excluded["emissions"]["advances"]["additions"], "0")
        values["inputs"]["observation_cutoff"] = "2026-07-03T00:00:00.00000000000000000002Z"
        included = run_mechanism("advance-issues", values)
        self.assertEqual(included["emissions"]["advances"]["additions"], "15000")
        self.assertEqual(included["emissions"]["advance_issue_audit"][0]["issue_observed_at"], "2026-07-02T23:00:00Z")

    def test_late_issue_without_evidence_is_excluded_but_available_issue_requires_evidence(self):
        values = bindings()
        values["inputs"]["evidence"] = []
        self.assert_blocked(reference(values), "ADV_FUNDING_EVIDENCE_REQUIRED")
        values["inputs"]["issues"][0]["observed_at"] = values["inputs"]["observation_cutoff"]
        result = reference(values)
        self.assertEqual(result["status"], "calculated")
        self.assertEqual(result["emissions"]["advances"]["additions"], "0")

    def test_evidence_must_match_funding_identity_scope_currency_and_purpose(self):
        for key, value in [("issue_id", "another-issue"), ("disbursement_id", "another-payment"),
                           ("agreement_id", "another-deal"), ("participant_id", "another-person"),
                           ("pool_id", "another-pool"), ("source_title_id", "another-title"),
                           ("currency", "EUR"), ("balance_purpose", "acquisition_funding"),
                           ("amount", money("15001")), ("funded_date", "2026-06-29")]:
            with self.subTest(key=key):
                values = bindings()
                values["inputs"]["evidence"][0][key] = value
                self.assert_blocked(reference(values), "ADV_EVIDENCE_MISMATCH")
        for key, value in [("eligible", False), ("approved", False), ("authority_ref", "other")]:
            values = bindings()
            values["inputs"]["evidence"][0][key] = value
            self.assert_blocked(reference(values), "ADV_ELIGIBLE_EVIDENCE_REQUIRED")

    def test_duplicate_stable_issue_or_disbursement_does_not_apply_twice(self):
        for key, code in [("issue_id", "DUPLICATE_ISSUE_ID"), ("disbursement_id", "DUPLICATE_DISBURSEMENT_ID")]:
            values = bindings()
            second = deepcopy(values["inputs"]["issues"][0])
            second.update(event_id="new-envelope", issue_id="new-issue", disbursement_id="new-disbursement")
            second[key] = values["inputs"]["issues"][0][key]
            values["inputs"]["issues"].append(second)
            self.assert_blocked(reference(values), code)

    def test_pooling_retains_title_trace_and_does_not_depend_on_row_order(self):
        values = bindings()
        second = deepcopy(values["inputs"]["issues"][0])
        second.update(event_id="event-2", issue_id="advance-2", disbursement_id="disbursement-2",
                      source_title_id="title-b", evidence_ref="evidence-2", amount=money("5000"))
        support = {k: v for k, v in second.items() if k not in {"event_id", "evidence_ref"}}
        support.update(evidence_id="evidence-2", eligible=True)
        values["inputs"]["issues"].append(second)
        values["inputs"]["evidence"].append(support)
        values["openings"]["prepayment"] = money("1000")
        result = reference(values)
        self.assertEqual(result["emissions"]["advances"]["available"], "21000")
        self.assertEqual(result["closing"]["prepayment"], "11000")
        self.assertEqual({row["source_title_id"] for row in result["emissions"]["advance_issue_audit"]}, {"title-a", "title-b"})
        values["inputs"]["issues"].reverse()
        values["inputs"]["evidence"].reverse()
        self.assertEqual(reference(values)["closing"], result["closing"])

    def test_datetime_profile_rejects_dates_naive_unknown_zone_and_leap_seconds(self):
        for invalid in ["2026-07-03", "2026-07-03T00:00:00", "2026-07-03T00:00:00-00:00",
                        "2026-07-03T00:00:60Z", "2025-02-29T00:00:00Z"]:
            with self.assertRaises(SPLException):
                parse_instant(invalid)
        self.assertEqual(parse_instant("2026-07-03T00:00:00.00000000000000000001Z").seconds -
                         parse_instant("2026-07-03T00:00:00Z").seconds, Fraction(1, 10 ** 20))
        self.assertEqual(parse_instant("2024-03-01T00:30:00+01:00").canonical, "2024-02-29T23:30:00Z")

    def test_instant_builtin_and_python_emitter_preserve_type_and_canonical_transport(self):
        source = ('schedule Timestamp language "spl/0.1-draft" core "spl-core/0.1-draft" '
                  'schema "spl-data/0.1-draft" { input observed: Instant; '
                  'emit "included" = observed < instant("2026-07-03T00:00:00Z"); '
                  'emit "observed" = observed; }')
        checked = check_schedule(parse(source))
        observed = "2026-07-03T01:00:00+02:00"
        expected = evaluate(checked, {"observed": observed}, {}).to_dict()
        generated = run_generated(checked, {"observed": parse_instant(observed)}, {})
        self.assertEqual(generated["emissions"], expected["emissions"])
        self.assertEqual(generated["emissions"], {"included": True, "observed": "2026-07-02T23:00:00Z"})


if __name__ == "__main__":
    unittest.main()
