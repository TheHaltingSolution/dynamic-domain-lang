"""Quest checks against original neutral facts, without compiler imports."""
import ast
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.quest import QuestOracleError, exact_json, quest_two_flow

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/quest/neutral.json").read_text(encoding="utf-8"))


def variant(principal="1000", rate="0.20", paid_date="2026-07-02", due_date="2026-01-01"):
    """Modify original facts only; no elapsed-day or financial answer binding."""
    facts = fixture()
    facts["terms"]["annual_target"] = rate
    facts["obligations"][0].update(amount=principal, due_date=due_date)
    facts["payments"][0].update(amount=principal, paid_date=paid_date)
    facts["applications"][0].update(amount=principal, effective_date=paid_date)
    payment_day = date.fromisoformat(paid_date)
    facts["period"] = {"start": due_date, "end": (payment_day + timedelta(days=1)).isoformat()}
    observed = (payment_day + timedelta(days=1)).isoformat() + "T00:00:00Z"
    facts["cutoff"] = (payment_day + timedelta(days=2)).isoformat() + "T00:00:00Z"
    origin = date(2026, 1, 1)
    calendar = facts["calendar"]["observations"]
    calendar[0].update(date=due_date, ordinal=str((date.fromisoformat(due_date) - origin).days))
    calendar[1].update(date=paid_date, ordinal=str((payment_day - origin).days))
    if due_date == paid_date:
        calendar.pop()
    for group in ("obligations", "payments", "applications", "evidence"):
        for row in facts[group]:
            row["observed_at"] = observed
    for row in calendar:
        row["observed_at"] = observed
    return facts


class QuestOracleTests(unittest.TestCase):
    def blocked(self, mutate, code=None):
        facts = fixture()
        mutate(facts)
        with self.assertRaises(QuestOracleError) as raised:
            quest_two_flow(facts)
        if code:
            self.assertEqual(raised.exception.code, code)

    def test_baseline_exact_cent_certificate_and_separate_actual_payment(self):
        facts = fixture()
        original = deepcopy(facts)
        out = quest_two_flow(facts)
        self.assertEqual((out["additional_charge"], out["minimum_charge"], out["actual_principal_paid"], out["elapsed_days"]),
                         (Fraction("95.17"), Fraction("95.18"), Fraction(1000), Fraction(182)))
        self.assertEqual(out["target_power"], Fraction(6, 5) ** 182)
        self.assertEqual(out["chosen_index"], 9517)
        self.assertFalse(out["index_even"])
        self.assertFalse(out["lower_domain_boundary"])
        self.assertEqual((out["lower_bound"], out["upper_bound"]), (Fraction("95.165"), Fraction("95.175")))
        self.assertLess(out["lower_power"], out["target_power"])
        self.assertLess(out["target_power"], out["upper_power"])
        self.assertTrue(all(out[key] for key in ("lower_ok", "upper_ok", "minimum_ok", "predecessor_ok")))
        self.assertEqual(out["observations"]["payments"][0]["amount"], "1000")
        self.assertEqual(out["additional_payment_status"], "no_event_supplied")
        self.assertEqual(out["monthly_status"], "not_computed")
        self.assertEqual(out["combined_status"], "unresolved_not_computed")
        self.assertNotIn("additional_paid", out)
        self.assertNotIn("combined_charge", out)
        self.assertEqual(facts, original)

    def test_policy_status_and_economic_identities_preserved(self):
        out = quest_two_flow(fixture())
        self.assertEqual((out["policy_id"], out["policy_revision"], out["policy_status"], out["evidence_class"]),
                         ("DYN02-QUEST-TWOFLOW-NEAREST-EVEN", "1", "proposed", "research_assumption"))
        self.assertEqual(out["scenario_status"], "calculated_unissued")
        self.assertEqual({key: out[key] for key in ("obligation_id", "payment_id", "application_id")}, fixture()["selected"])

    def test_exact_ties_reject_half_away_and_rounding_terminal_total(self):
        for principal, charge, minimum in [("0.01", "0", "0.01"), ("0.03", "0.02", "0.02")]:
            out = quest_two_flow(variant(principal, "0.5", "2027-01-01"))
            self.assertEqual(out["additional_charge"], Fraction(charge))
            self.assertEqual(out["minimum_charge"], Fraction(minimum))
            self.assertTrue(out["index_even"])
            self.assertTrue(out["lower_ok"] and out["upper_ok"])
            if principal == "0.01":
                self.assertTrue(out["lower_domain_boundary"])
                self.assertEqual(out["lower_bound"], 0)
                self.assertEqual(out["upper_power"], out["target_power"])
                self.assertNotEqual(out["additional_charge"], Fraction("0.01"))
            else:
                self.assertFalse(out["lower_domain_boundary"])
                self.assertEqual(out["lower_power"], out["target_power"])
                self.assertNotEqual(out["additional_charge"], Fraction("0.01"))

    def test_near_ties_are_decided_by_exact_certificate(self):
        denominator = 10 ** 110
        for principal, rate_numerator, expected in [
            ("0.01", denominator // 2 - 1, "0"), ("0.01", denominator // 2 + 1, "0.01"),
            ("0.03", denominator // 2 - 1, "0.01"), ("0.03", denominator // 2 + 1, "0.02")]:
            rate = Fraction(rate_numerator, denominator)
            raw = {"numerator": str(rate.numerator), "denominator": str(rate.denominator)}
            out = quest_two_flow(variant(principal, raw, "2027-01-01"))
            self.assertEqual(out["additional_charge"], Fraction(expected))
            self.assertTrue(out["lower_ok"] and out["upper_ok"])

    def test_zero_days_zero_rate_full_year_and_alternate_facts(self):
        for facts, expected, days in [(variant(paid_date="2026-01-01"), "0", 0),
                                      (variant(rate="0"), "0", 182),
                                      (variant(paid_date="2027-01-01"), "200", 365),
                                      (variant("500", "0.1", "2026-06-30"), "24.06", 180)]:
            out = quest_two_flow(facts)
            self.assertEqual(out["additional_charge"], Fraction(expected))
            self.assertEqual(out["elapsed_days"], days)
        zero = quest_two_flow(variant(paid_date="2026-01-01"))
        self.assertTrue(zero["lower_domain_boundary"])
        self.assertEqual(zero["target_power"], 1)
        self.assertEqual(zero["minimum_charge"], 0)

    def test_non_origin_due_date_derives_elapsed_from_both_records(self):
        facts = variant(due_date="2026-06-30", paid_date="2026-07-02")
        self.assertEqual([row["ordinal"] for row in facts["calendar"]["observations"]], ["180", "182"])
        self.assertEqual(len(facts["calendar"]["observations"]), 2)
        result = quest_two_flow(facts)
        self.assertEqual(result["elapsed_days"], 2)
        self.assertEqual(result["additional_charge"], Fraction("1.00"))
        self.assertEqual(result["target_power"], Fraction(6, 5) ** 2)
        self.assertNotEqual(result["additional_charge"], Fraction("95.17"))

    def test_minimum_return_is_detail_not_selected_nearest_result(self):
        out = quest_two_flow(fixture())
        p = out["actual_principal_paid"]
        chosen, minimum, k = out["additional_charge"], out["minimum_charge"], out["target_power"]
        self.assertLess(((p + chosen) / p) ** 365, k)
        self.assertGreaterEqual(((p + minimum) / p) ** 365, k)
        self.assertLess(((p + minimum - Fraction(1, 100)) / p) ** 365, k)
        # Simple daily proration and hypothetical monthly-credit alternatives
        # deliberately produce different numbers from this selected component.
        self.assertNotEqual(chosen, Fraction("99.73"))
        self.assertNotEqual(chosen, Fraction("85.17"))

    def test_input_numeric_codec_is_exact_and_strict(self):
        for malformed in [1, True, 1.0, None, "1/2", "01", "1e2", "NaN", "Infinity",
                          {"numerator": "2", "denominator": "4"}, {"numerator": "1", "denominator": "0"},
                          {"numerator": "-0", "denominator": "1"}, {"numerator": 1, "denominator": "2"}]:
            with self.subTest(value=malformed):
                self.blocked(lambda data, value=malformed: data["terms"].update(annual_target=value), "INVALID_EXACT_NUMBER")
        raw = fixture()
        raw["terms"]["annual_target"] = {"numerator": "1", "denominator": "5"}
        self.assertEqual(quest_two_flow(raw)["additional_charge"], Fraction("95.17"))

    def test_selected_terms_and_pinned_clause_identity(self):
        for field, value in [("rounding", "half_away_from_zero"), ("day_count", "ACT/360"),
                             ("policy_id", "other-policy"), ("revision", "2")]:
            self.blocked(lambda data, field=field, value=value: data["terms"].update({field: value}), "SELECTED_POLICY_REQUIRED")
        for value in ["0", "0.1", "-0.01"]:
            self.blocked(lambda data, value=value: data["terms"].update(quantum=value), "TERM_DOMAIN")
        self.blocked(lambda data: data["terms"].update(annual_target="-0.01"), "TERM_DOMAIN")
        for field in ("source_ref", "locator", "component"):
            self.blocked(lambda data, field=field: data["clause"].update({field: "wrong"}), "CLAUSE_IDENTITY")

    def test_all_economic_scope_links_currency_and_full_amounts(self):
        for group in ("obligations", "payments", "applications"):
            for dimension in fixture()["scope"]:
                self.blocked(lambda data, group=group, dimension=dimension: data[group][0]["scope"].update({dimension: "foreign"}), "ECONOMIC_SCOPE")
            self.blocked(lambda data, group=group: data[group][0].update(currency="EUR"), "UNSUPPORTED_CURRENCY")
        self.blocked(lambda data: data["scope"].update(currency="EUR"), "UNSUPPORTED_CURRENCY")
        for group in ("payments", "applications"):
            self.blocked(lambda data, group=group: data[group][0].update(amount="999.99"), "FULL_PRINCIPAL_PAYMENT_REQUIRED")
        for field in ("obligation_id", "payment_id"):
            self.blocked(lambda data, field=field: data["applications"][0].update({field: "foreign"}), "APPLICATION_LINK")
        for field in ("obligation_id", "payment_id", "application_id"):
            self.blocked(lambda data, field=field: data["selected"].update({field: "foreign"}), "SELECTED_RECORD_REQUIRED")

    def test_all_actual_records_count_no_silent_allocation_or_payment(self):
        for group in ("obligations", "payments", "applications"):
            self.blocked(lambda data, group=group: data.update({group: []}), "UNSUPPORTED_CARDINALITY")
            self.blocked(lambda data, group=group: data[group].append(deepcopy(data[group][0])), "DUPLICATE_ECONOMIC_RECORD")
            def extra(data, group=group):
                row = deepcopy(data[group][0])
                row["id"] += "-extra"
                data[group].append(row)
            self.blocked(extra, "UNSUPPORTED_CARDINALITY")
        self.blocked(lambda data: data["payments"][0].update(economic_event_id=""), "SOURCE_OR_ID_REQUIRED")

    def test_all_observations_and_unused_evidence_strictly_before_cutoff(self):
        for group in ("obligations", "payments", "applications"):
            self.blocked(lambda data, group=group: data[group][0].update(observed_at=data["cutoff"]), "OBSERVATION_AFTER_CUTOFF")
        self.blocked(lambda data: data["calendar"]["observations"][0].update(observed_at=data["cutoff"]), "OBSERVATION_AFTER_CUTOFF")
        self.blocked(lambda data: data["evidence"][0].update(observed_at=data["cutoff"]), "EVIDENCE_AFTER_CUTOFF")
        self.blocked(lambda data: data["evidence"].append({"id": "unused", "observed_at": data["cutoff"], "source_ref": "unused-source"}), "EVIDENCE_AFTER_CUTOFF")
        self.blocked(lambda data: data["evidence"].append(deepcopy(data["evidence"][0])), "DUPLICATE_EVIDENCE")
        self.blocked(lambda data: data.update(evidence=[]), "EVIDENCE_REQUIRED")
        for group in ("obligations", "payments", "applications"):
            self.blocked(lambda data, group=group: data[group][0].update(evidence_id="missing"), "EVIDENCE_REQUIRED")
            self.blocked(lambda data, group=group: data[group][0].update(source_ref="foreign"), "SOURCE_IDENTITY")

    def test_calendar_identity_endpoint_truth_and_duplicates(self):
        for field in ("id", "version", "origin", "source_ref"):
            self.blocked(lambda data, field=field: data["calendar"].update({field: "foreign"}), "CALENDAR_IDENTITY")
        self.blocked(lambda data: data["calendar"].update(observations=[]), "CALENDAR_ENDPOINT_REQUIRED")
        self.blocked(lambda data: data["calendar"]["observations"].pop(), "CALENDAR_ENDPOINT_REQUIRED")
        self.blocked(lambda data: data["calendar"]["observations"][1].update(ordinal="180"), "CALENDAR_TRUTH")
        self.blocked(lambda data: data["calendar"]["observations"][0].update(ordinal="1"), "CALENDAR_TRUTH")
        for value in ["-1", "0.5"]:
            self.blocked(lambda data, value=value: data["calendar"]["observations"][0].update(ordinal=value), "CALENDAR_ORDINAL_DOMAIN")
        self.blocked(lambda data: data["calendar"]["observations"].append(deepcopy(data["calendar"]["observations"][0])), "DUPLICATE_CALENDAR_ID")
        self.blocked(lambda data: data["calendar"]["observations"][1].update(date="2026-01-01"), "DUPLICATE_CALENDAR_DATE")
        self.blocked(lambda data: data["calendar"]["observations"][1].update(date="2026-07-01", ordinal="181"), "CALENDAR_TRUTH")

    def test_original_date_domain_and_application_date(self):
        self.blocked(lambda data: data["payments"][0].update(paid_date="2026-02-30"), "INVALID_DATE")
        self.blocked(lambda data: data["applications"][0].update(effective_date="2026-07-01"), "APPLICATION_DATE")
        self.blocked(lambda data: data["period"].update(end="2026-07-02"), "PAYMENT_OUTSIDE_PERIOD")
        self.blocked(lambda data: data["obligations"][0].update(due_date="2026-07-03"), "ELAPSED_DAY_DOMAIN")
        too_long = variant(paid_date="2027-01-02")
        with self.assertRaises(QuestOracleError) as raised:
            quest_two_flow(too_long)
        self.assertEqual(raised.exception.code, "ELAPSED_DAY_DOMAIN")

    def test_explicit_principal_and_search_domains(self):
        for amount in ["0", "-1", "0.001"]:
            with self.assertRaises(QuestOracleError) as raised:
                quest_two_flow(variant(principal=amount))
            self.assertEqual(raised.exception.code, "PRINCIPAL_DOMAIN")
        for amount in ["167772.16", "167772.151"]:
            with self.assertRaises(QuestOracleError) as raised:
                quest_two_flow(variant(principal=amount, rate="1", paid_date="2026-01-01"))
            self.assertEqual(raised.exception.code, "SEARCH_DOMAIN")
        out = quest_two_flow(variant(principal="167772.15", rate="1", paid_date="2026-01-01"))
        self.assertEqual(out["additional_charge"], 0)

    def test_fields_missing_sources_and_unallowed_solved_inputs(self):
        self.blocked(lambda data: data.update(additional_charge="95.17"), "INVALID_FIELDS")
        self.blocked(lambda data: data.update(elapsed_days="182"), "INVALID_FIELDS")
        self.blocked(lambda data: data["terms"].update(target_power="answer"), "INVALID_FIELDS")
        for group in ("obligations", "payments", "applications"):
            self.blocked(lambda data, group=group: data[group][0].update(source_ref=""), "SOURCE_OR_ID_REQUIRED")
            self.blocked(lambda data, group=group: data[group][0].pop("evidence_id"))
        self.blocked(lambda data: data["evidence"][0].update(source_ref=""), "SOURCE_OR_ID_REQUIRED")
        self.blocked(lambda data: data["calendar"]["observations"][0].update(source_ref=""), "SOURCE_OR_ID_REQUIRED")

    def test_permutation_identifier_and_numeric_notation_metamorphisms(self):
        original = fixture()
        expected = quest_two_flow(original)
        altered = deepcopy(original)
        altered["evidence"].reverse()
        altered["calendar"]["observations"].reverse()
        altered["terms"]["annual_target"] = "0.2000"
        for group in ("obligations", "payments", "applications"):
            altered[group][0]["amount"] = {"numerator": "1000", "denominator": "1"}
        for group, key in [("obligations", "obligation_id"), ("payments", "payment_id"), ("applications", "application_id")]:
            altered[group][0]["id"] += "-renamed"
            altered["selected"][key] = altered[group][0]["id"]
        altered["applications"][0].update(obligation_id=altered["selected"]["obligation_id"], payment_id=altered["selected"]["payment_id"])
        actual = quest_two_flow(altered)
        for key in ("additional_charge", "minimum_charge", "target_power", "elapsed_days", "certificate"):
            self.assertEqual(actual[key], expected[key])
        self.assertEqual(actual["payment_id"], "QP-1-renamed")

    def test_equivalent_instants_and_malformed_timestamps(self):
        altered = fixture()
        altered["cutoff"] = "2026-07-03T17:00:00-07:00"
        self.assertEqual(quest_two_flow(altered)["additional_charge"], Fraction("95.17"))
        for value in ["2026-07-04", "2026-07-04T00:00:00-00:00", "2026-07-04T24:00:00Z", True]:
            self.blocked(lambda data, value=value: data.update(cutoff=value), "INVALID_INSTANT")

    def test_output_copy_and_exact_json(self):
        facts = fixture()
        result = quest_two_flow(facts)
        result["observations"]["payments"][0]["amount"] = "0"
        self.assertEqual(facts["payments"][0]["amount"], "1000")
        transport = exact_json(quest_two_flow(facts))
        self.assertEqual(transport["additional_charge"], {"numerator": "9517", "denominator": "100"})
        self.assertEqual(transport["elapsed_days"], {"numerator": "182", "denominator": "1"})
        json.dumps(transport)

    def test_oracle_has_no_compiler_import_or_shared_numeric_search(self):
        source = (ROOT / "oracles/quest.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and (name.startswith("spl_compiler") or name.startswith("cases.quest")) for name in imports))
        self.assertIn(".ln()", source)
        self.assertIn(".exp()", source)
        self.assertNotIn("binary_search", source)


if __name__ == "__main__":
    unittest.main()
