"""Independent complete-calendar, amended-term and daily-proration controls."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.calendar_terms import CalendarTermsOracleError, calendar_terms, exact_json, validate_calendar


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/calendar-terms/neutral.json").read_text(encoding="utf-8"))


class CalendarTermsOracleTests(unittest.TestCase):
    def reject(self, data, code, mechanical=False):
        with self.assertRaises(CalendarTermsOracleError) as raised:
            (validate_calendar if mechanical else calendar_terms)(data)
        self.assertEqual(str(raised.exception), code)

    def test_original_daily_population_derives_30_10_100(self):
        data = fixture()
        result = calendar_terms(data)
        self.assertEqual((result["eligible_day_count"], result["active_eligible_day_count"], result["amount"]), (30, 10, 100))
        self.assertEqual((result["period"]["start"], result["period"]["end"]), ("2026-04-06", "2026-05-06"))
        self.assertEqual(sum(row["selection"] == "inactive_zero" for row in result["day_lines"]), 20)
        self.assertEqual((result["term_lines"][0]["term_id"], result["term_lines"][0]["predecessor_id"], result["term_lines"][0]["monthly_amount"]),
                         ("term-v2", "term-v1", 300))
        self.assertEqual(len(data["days"]), 40)
        self.assertTrue(all("denominator" not in row and "amount" not in row for row in data["days"]))
        self.assertNotIn("eligible_day_count", data)
        self.assertNotIn("rolled_deadline", data["deadline"])

    def test_date_asof_recorded_and_signed_equality(self):
        for as_of, amount, term in (("2026-04-09", 0, None), ("2026-04-10", 80, "term-v1"),
                                    ("2026-04-19", 80, "term-v1"), ("2026-04-20", 100, "term-v2")):
            data = fixture(); data["as_of"] = as_of
            result = calendar_terms(data)
            self.assertEqual(result["amount"], amount)
            self.assertEqual([row["term_id"] for row in result["term_lines"]], [] if term is None else [term])
        data = fixture(); data["terms"][1]["signed_date"] = "2026-04-20"
        self.assertEqual(calendar_terms(data)["amount"], 100)
        data["terms"][1]["signed_date"] = "2026-04-21"
        self.reject(data, "CALENDAR_SIGNED_RECORDED_ORDER")
        data = fixture(); data["as_of"] = "2026-04-20T00:00:00Z"
        self.reject(data, "CALENDAR_DATE")

    def test_effective_start_included_end_excluded(self):
        result = calendar_terms(fixture())
        days = {row["date"]: row for row in result["day_lines"]}
        self.assertEqual(days["2026-04-25"]["selection"], "inactive_zero")
        self.assertEqual(days["2026-04-26"]["term_id"], "term-v2")
        self.assertEqual(days["2026-05-05"]["term_id"], "term-v2")
        data = fixture()
        for term in data["terms"]:
            term["effective"]["end"] = "2026-05-05"
        result = calendar_terms(data)
        self.assertEqual((result["active_eligible_day_count"], result["amount"]), (9, 90))
        self.assertEqual(result["day_lines"][-1]["selection"], "inactive_zero")

    def test_partial_amendment_uses_per_day_selected_amounts(self):
        data = fixture()
        amendment = deepcopy(data["terms"][1])
        amendment.update(id="term-v3", revision=3, predecessor_id="term-v2", monthly_amount="600",
                         effective={"start": "2026-05-01", "end": "2026-05-06"}, source_ref="synthetic-amendment-3")
        data["terms"].append(amendment)
        result = calendar_terms(data)
        self.assertEqual((result["active_eligible_day_count"], result["amount"]), (10, 150))
        self.assertEqual([(row["term_id"], row["eligible_days"], row["amount"]) for row in result["term_lines"]],
                         [("term-v2", 5, 50), ("term-v3", 5, 100)])

    def test_competing_highest_amendments_tie_even_equal_money(self):
        data = fixture()
        data["terms"].append({**deepcopy(data["terms"][1]), "id": "competing-v2"})
        self.reject(data, "CALENDAR_AMBIGUOUS_AMENDMENT")
        data["terms"][-1]["recorded_date"] = "2026-04-21"
        self.assertEqual(calendar_terms(data)["amount"], 100)
        data["as_of"] = "2026-04-21"
        self.reject(data, "CALENDAR_AMBIGUOUS_AMENDMENT")
        data = fixture()
        data["terms"].append({**deepcopy(data["terms"][0]), "id": "other-v1"})
        self.assertEqual(calendar_terms(data)["amount"], 100)
        data["as_of"] = "2026-04-19"
        self.reject(data, "CALENDAR_AMBIGUOUS_AMENDMENT")

    def test_predecessor_chain_missing_cycles_and_revisions(self):
        changes = [lambda d: d["terms"][1].update(predecessor_id="missing"),
                   lambda d: d["terms"][0].update(predecessor_id="term-v2"),
                   lambda d: d["terms"][1].update(revision=1),
                   lambda d: d["terms"][1].update(predecessor_id=""),
                   lambda d: d["terms"][0].update(recorded_date="2026-04-22")]
        for change in changes:
            data = fixture(); change(data)
            self.reject(data, "CALENDAR_PREDECESSOR")
        data = fixture(); data["terms"][1]["revision"] = True
        self.reject(data, "CALENDAR_TERM_REVISION")

    def test_following_preceding_and_open_day_equality(self):
        data = fixture()
        self.assertEqual(calendar_terms(data)["rolled_deadline"], "2026-05-04")
        data["deadline"]["roll"] = "preceding"
        self.assertEqual(calendar_terms(data)["rolled_deadline"], "2026-04-30")
        for roll in ("following", "preceding"):
            data["deadline"].update(date="2026-04-30", roll=roll)
            self.assertEqual(calendar_terms(data)["rolled_deadline"], "2026-04-30")
        data["deadline"]["roll"] = "modified_following"
        self.reject(data, "CALENDAR_ROLL_POLICY")

    def test_business_calendar_has_finite_margin_and_no_invented_day(self):
        data = fixture(); data["deadline"]["date"] = "2026-05-09"
        self.reject(data, "CALENDAR_BUSINESS_RELATION_UNAVAILABLE")
        data = fixture(); data["deadline"]["date"] = "2026-05-11"
        self.reject(data, "CALENDAR_DEADLINE_OUTSIDE_COVERAGE")
        data = fixture(); data["calendar"]["closed_weekdays"] = list(range(1, 8))
        for row in data["days"]:
            row["closed"] = True
        validate_calendar(data)
        self.reject(data, "CALENDAR_BUSINESS_RELATION_UNAVAILABLE")

    def test_closed_flags_are_supplied_while_proration_is_separate(self):
        data = fixture()
        result = calendar_terms(data)
        holiday = next(row for row in result["day_lines"] if row["date"] == "2026-05-01")
        self.assertEqual((holiday["closed"], holiday["proration_eligible"], holiday["amount"]), (True, True, 10))
        data["calendar"]["closed_weekdays"] = []
        for row in data["days"]:
            row["closed"] = row["holiday_closed"]
        self.assertEqual(calendar_terms(data)["rolled_deadline"], "2026-05-02")
        self.assertEqual(calendar_terms(data)["amount"], 100)
        data = fixture()
        for row in data["days"]:
            if row["date"] == "2026-05-01":
                row["holiday_closed"] = row["closed"] = False
        self.assertEqual(calendar_terms(data)["rolled_deadline"], "2026-05-01")

    def test_finance_derives_eligible_counts_from_original_flags(self):
        data = fixture()
        next(row for row in data["days"] if row["date"] == "2026-04-06")["proration_eligible"] = False
        result = calendar_terms(data)
        self.assertEqual((result["eligible_day_count"], result["active_eligible_day_count"], result["amount"]), (29, 10, Fraction(3000, 29)))
        data = fixture()
        next(row for row in data["days"] if row["date"] == "2026-04-26")["proration_eligible"] = False
        result = calendar_terms(data)
        self.assertEqual((result["eligible_day_count"], result["active_eligible_day_count"], result["amount"]), (29, 9, Fraction(2700, 29)))
        for row in data["days"]:
            row["proration_eligible"] = False
        validate_calendar(data)
        self.reject(data, "CALENDAR_ZERO_ELIGIBLE_DAYS")

    def test_zero_active_terms_and_zero_amount_have_distinct_lineage(self):
        data = fixture(); data["terms"] = []
        result = calendar_terms(data)
        self.assertEqual((result["amount"], result["active_eligible_day_count"]), (0, 0))
        self.assertTrue(all(row["selection"] == "inactive_zero" for row in result["day_lines"]))
        data = fixture(); data["terms"][1]["monthly_amount"] = "0"
        result = calendar_terms(data)
        self.assertEqual((result["amount"], result["active_eligible_day_count"]), (0, 10))
        self.assertEqual(result["term_lines"][0]["term_id"], "term-v2")

    def test_complete_population_missing_duplicate_and_wrong_dates(self):
        data = fixture(); data["days"].pop()
        self.reject(data, "CALENDAR_INCOMPLETE_POPULATION", mechanical=True)
        data = fixture(); data["days"].append(deepcopy(data["days"][0]))
        self.reject(data, "CALENDAR_DUPLICATE_ID", mechanical=True)
        data = fixture(); duplicate = deepcopy(data["days"][0]); duplicate["id"] = "other-id"
        data["days"].append(duplicate)
        self.reject(data, "CALENDAR_DUPLICATE_DATE", mechanical=True)
        data = fixture(); data["days"][0]["date"] = "2026-02-29"
        self.reject(data, "CALENDAR_DATE", mechanical=True)
        data = fixture(); data["calendar"]["coverage"]["end"] = "2028-05-11"
        self.reject(data, "CALENDAR_COVERAGE_LIMIT", mechanical=True)

    def test_gregorian_metadata_and_flags_are_independently_checked(self):
        for field, value, code in (("ordinal", 1, "CALENDAR_ORDINAL"), ("weekday", 7, "CALENDAR_WEEKDAY"),
                                    ("closed", True, "CALENDAR_CLOSED_FLAGS"), ("holiday_closed", 0, "CALENDAR_BOOLEAN_FLAGS")):
            data = fixture(); data["days"][0][field] = value
            self.reject(data, code, mechanical=True)
        data = fixture(); data["calendar"]["ordinal_epoch"] = "unix_days"
        self.reject(data, "CALENDAR_ORDINAL_EPOCH", mechanical=True)
        for weekdays in ([0], [8], [True], [6, 6]):
            data = fixture(); data["calendar"]["closed_weekdays"] = weekdays
            self.reject(data, "CALENDAR_WEEKDAY_POLICY", mechanical=True)

    def test_fiscal_population_overlap_gap_and_missing_reference(self):
        data = fixture(); data["fiscal_periods"][1]["period"]["start"] = "2026-04-05"
        self.reject(data, "CALENDAR_FISCAL_OVERLAP", mechanical=True)
        data = fixture(); data["fiscal_periods"].pop(0)
        self.reject(data, "CALENDAR_FISCAL_GAP", mechanical=True)
        data = fixture(); data["selected_period_id"] = "missing"
        self.reject(data, "CALENDAR_SELECTED_FISCAL_PERIOD", mechanical=True)
        data = fixture(); data["fiscal_periods"][0]["period"]["start"] = "2026-03-31"
        self.reject(data, "CALENDAR_FISCAL_BOUNDS", mechanical=True)

    def test_calendar_version_scope_and_original_evidence(self):
        for field in ("days", "fiscal_periods"):
            data = fixture(); data[field][0]["calendar_version"] = "2"
            self.reject(data, "CALENDAR_ID_VERSION", mechanical=True)
            data = fixture(); data[field][0]["scope"]["asset_id"] = "other"
            self.reject(data, "CALENDAR_FACT_SCOPE", mechanical=True)
            data = fixture(); data[field][0]["evidence_ref"] = "missing"
            self.reject(data, "CALENDAR_EVIDENCE_REQUIRED", mechanical=True)
        data = fixture(); data["terms"][0]["scope"]["pool_id"] = "other"
        self.reject(data, "CALENDAR_TERM_SCOPE")
        data = fixture(); data["evidence"][0]["scope"]["participant_id"] = "other"
        self.reject(data, "CALENDAR_EVIDENCE_SCOPE", mechanical=True)
        data = fixture(); data["scope"]["currency"] = "EUR"
        self.reject(data, "CALENDAR_CURRENCY", mechanical=True)

    def test_exact_observation_cutoff_is_independent_of_civil_asof(self):
        data = fixture(); data["cutoff"] = "2026-05-12T00:00:00.0000002Z"
        data["terms"][1]["observed_at"] = "2026-05-12T01:00:00.0000001+01:00"
        self.assertEqual(calendar_terms(data)["amount"], 100)
        data["terms"][1]["observed_at"] = data["cutoff"]
        self.reject(data, "CALENDAR_TERM_CUTOFF")
        data = fixture(); data["evidence"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "CALENDAR_EVIDENCE_CUTOFF", mechanical=True)
        # A signed/recorded as-of is not an observed-knowledge historical replay.
        data = fixture(); data["terms"][1]["observed_at"] = "2026-05-11T00:00:00Z"
        self.assertEqual(calendar_terms(data)["amount"], 100)

    def test_mechanical_validation_does_not_solve_financial_terms(self):
        data = fixture(); data["terms"][1]["monthly_amount"] = "-1"
        checked = validate_calendar(data)
        self.assertEqual(set(checked), {"calendar_id", "calendar_version", "days", "fiscal_periods", "evidence"})
        self.assertNotIn("amount", checked)
        self.assertNotIn("eligible_day_count", checked)
        self.reject(data, "CALENDAR_EXACT_NONNEGATIVE_MONEY")
        for value in (300.0, True, "3e2"):
            data = fixture(); data["terms"][1]["monthly_amount"] = value
            self.reject(data, "CALENDAR_EXACT_NONNEGATIVE_MONEY")
        data = fixture(); data["terms"][1]["monthly_amount"] = "1/7"
        self.assertEqual(calendar_terms(data)["amount"], Fraction(1, 21))

    def test_original_population_permutation_and_exact_neutral_serialization(self):
        data = fixture(); original = deepcopy(data)
        result = calendar_terms(data)
        self.assertEqual(data, original)
        for field in ("days", "fiscal_periods", "terms", "evidence"):
            data[field].reverse()
        self.assertEqual(calendar_terms(data), result)
        self.assertEqual(json.loads(json.dumps(exact_json(result)))["amount"], "100")
        tree = ast.parse((ROOT / "oracles/calendar_terms.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
