"""Direct checked Quest source agreement and certificate mutation witnesses.

Set QUEST_REFERENCE_ONLY=1 while preparing fixtures without native execution.
Tests register their own temporary closure; issued or checked-in pins never move.
"""
from copy import deepcopy
from fractions import Fraction
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.quest import build_modules as quest
from cases.r1 import build_modules as r1
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, loads, read_json, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.linker import link_schedule
from spl_compiler.modules import linking_manifest, resolve_module
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target

REFERENCE_ONLY = os.environ.get("QUEST_REFERENCE_ONLY") == "1"


class QuestNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / ".lake" / "quest-native-tests"
        directory.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=directory)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases" / "quest"
        cls.folder.mkdir(parents=True)
        for name in ["power.spl", "charge.spl", "policy.md", "calendar-facts.json", "source-index.json", "neutral.json"]:
            shutil.copyfile(ROOT / "cases" / "quest" / name, cls.folder / name)
        with patch.object(quest, "ROOT", cls.root), patch.object(quest, "FOLDER", cls.folder), patch.object(r1, "ROOT", cls.root):
            cls.reference = quest.register_quest()
        cls.fixture = read_json(cls.folder / "neutral.json")
        cls.links = linking_manifest(resolve_module(cls.reference, cls.root))
        cls.link_path = cls.root / "link.json"
        write_json(cls.link_path, cls.links)
        cls.source = cls.folder / "charge.spl"
        cls.text = cls.source.read_text(encoding="utf-8")
        cls.program = check_schedule(link_schedule(parse(cls.text), cls.links))
        cls.target = None if REFERENCE_ONLY else compile_schedule(cls.source, cls.root / "Settlement.lean", link=cls.link_path)
        cls.serial = 0

    @classmethod
    def bindings(cls, fixture=None):
        with patch.object(quest, "ROOT", cls.root), patch.object(quest, "FOLDER", cls.folder), patch.object(r1, "ROOT", cls.root):
            return quest.quest_bindings(quest.quest_package(fixture or cls.fixture, reference=cls.reference))

    @classmethod
    def variant(cls, amount="1000", rate="0.20", due="2026-01-01", paid="2026-07-02"):
        fixture = deepcopy(cls.fixture)
        fixture["terms"]["annual_target"] = rate
        for name in ["obligations", "payments", "applications"]:
            fixture[name][0]["amount"] = amount
        fixture["obligations"][0]["due_date"] = due
        fixture["payments"][0]["paid_date"] = paid
        fixture["applications"][0]["effective_date"] = paid
        if paid >= "2027-01-01":
            fixture["period"] = {"start": "2026-01-01", "end": "2027-01-03"}
            fixture["cutoff"] = "2027-01-04T00:00:00Z"
            for name in ["obligations", "payments", "applications", "evidence"]:
                for row in fixture[name]:
                    row["observed_at"] = "2027-01-03T00:00:00Z"
        original = fixture["calendar"]["observations"]
        facts = {row["date"]: row["ordinal"] for row in read_json(cls.folder / "calendar-facts.json")["facts"]}
        fixture["calendar"]["observations"] = []
        for index, day in enumerate(dict.fromkeys([due, paid])):
            observation = deepcopy(original[index])
            observation.update(date=day, ordinal=facts[day])
            if paid >= "2027-01-01":
                observation["observed_at"] = "2027-01-03T00:00:00Z"
            fixture["calendar"]["observations"].append(observation)
        return cls.bindings(fixture)

    def compare(self, bindings, *, text=None):
        """Native IR and emitted execution share no reference evaluation call."""
        program, source, target = self.program, self.source, self.target
        self.__class__.serial += 1
        serial = self.serial
        if text is not None:
            program = check_schedule(link_schedule(parse(text), self.links))
            source = self.root / f"Mutation-{serial}.spl"
            source.write_text(text, encoding="utf-8", newline="\n")
            target = None if REFERENCE_ONLY else compile_schedule(source, self.root / f"Mutation-{serial}.lean", link=self.link_path)
        reference = normalize_target(evaluate(program, bindings["inputs"], bindings["openings"]).to_dict())
        results = {"reference": reference}
        if not REFERENCE_ONLY:
            path = self.root / f"bindings-{serial}.json"
            write_json(path, bindings)
            results["native_ir"] = normalize_target(interpret_schedule(source, path, link=self.link_path))
            results["native_emitted"] = normalize_target(loads(lean(["--run", target, path])))
            for backend, actual in results.items():
                with self.subTest(backend=backend):
                    for field in ["status", "emissions", "closing"]:
                        self.assertEqual(canonical(actual[field]), canonical(reference[field]), field)
                    self.assertEqual([d["code"] for d in actual["diagnostics"]], [d["code"] for d in reference["diagnostics"]])
            seen = set()
            for node in results["native_ir"]["trace"]:
                self.assertTrue(set(node["dependencies"]) <= seen)
                seen.add(node["node_id"])
        return results

    def assert_blocked(self, results, code):
        for actual in results.values():
            self.assertEqual(actual["status"], "blocked", actual.get("diagnostics"))
            self.assertEqual([d["code"] for d in actual["diagnostics"]], [code])
            self.assertEqual((actual["emissions"], actual["closing"]), ({}, {}))

    def assert_certificate(self, output, bindings):
        comparison, cert = output["comparison"], output["certificate"]
        principal = exact(bindings["inputs"]["payments"][0]["amount"]["value"])
        target_rate, days = exact(comparison["annual_target"]), exact(comparison["elapsed_days"])
        self.assertEqual(days.denominator, 1)
        target = (1 + target_rate) ** int(days)
        index = exact(cert["chosen_index"])
        self.assertEqual(index.denominator, 1)
        self.assertGreaterEqual(index, 0)
        self.assertEqual(cert["index_even"], int(index) % 2 == 0)
        self.assertEqual(exact(cert["target_power"]), target)
        self.assertEqual(exact(comparison["additional_charge"]), index / 100)
        lower = max(Fraction(0), (index - Fraction(1, 2)) / 100)
        upper = (index + Fraction(1, 2)) / 100
        self.assertEqual((exact(cert["lower_bound"]), exact(cert["upper_bound"])), (lower, upper))
        lower_power, upper_power = ((principal + lower) / principal) ** 365, ((principal + upper) / principal) ** 365
        self.assertEqual((exact(cert["lower_power"]), exact(cert["upper_power"])), (lower_power, upper_power))
        self.assertEqual(cert["lower_domain_boundary"], index == 0)
        if index == 0:
            self.assertGreaterEqual(target, 1)
        elif cert["index_even"]:
            self.assertLessEqual(lower_power, target)
        else:
            self.assertLess(lower_power, target)
        if cert["index_even"]:
            self.assertLessEqual(target, upper_power)
        else:
            self.assertLess(target, upper_power)
        minimum = exact(cert["minimum_charge"])
        self.assertEqual((minimum * 100).denominator, 1)
        self.assertGreaterEqual(((principal + minimum) / principal) ** 365, target)
        if minimum:
            self.assertLess(((principal + minimum - Fraction(1, 100)) / principal) ** 365, target)
        else:
            self.assertEqual(target, 1)
        for flag in ["lower_ok", "upper_ok", "minimum_ok", "predecessor_ok"]:
            self.assertTrue(cert[flag], flag)

    def test_original_dates_half_even_and_exact_certificates(self):
        cases = [
            ("1000", "0.20", "2026-01-01", "2026-07-02", "95.17", "95.18", "182"),
            ("0.01", "0.50", "2026-01-01", "2027-01-01", "0", "0.01", "365"),
            ("0.03", "0.50", "2026-01-01", "2027-01-01", "0.02", "0.02", "365"),
            ("1000", "0.20", "2026-01-01", "2026-01-01", "0", "0", "0"),
            ("1000", "0.20", "2026-01-01", "2027-01-01", "200", "200", "365"),
            ("500", "0.10", "2026-01-01", "2026-06-30", "24.06", "24.07", "180"),
            ("0.01", "0.499999", "2026-01-01", "2027-01-01", "0", "0.01", "365"),
            ("0.01", "0.500001", "2026-01-01", "2027-01-01", "0.01", "0.01", "365"),
            ("1000", "0.20", "2026-06-30", "2026-07-02", "1", "1", "2"),
            ("1000", "0", "2026-01-01", "2026-07-02", "0", "0", "182"),
        ]
        for amount, rate, due, paid, expected, minimum, days in cases:
            with self.subTest(principal=amount, rate=rate, due=due, paid=paid):
                bindings = self.variant(amount, rate, due, paid)
                results = self.compare(bindings)
                for actual in results.values():
                    self.assertEqual(actual["status"], "calculated", actual["diagnostics"])
                    output = actual["emissions"]
                    self.assertEqual(output["comparison"]["additional_charge"], expected)
                    self.assertEqual(output["comparison"]["actual_principal_paid"], amount)
                    self.assertEqual(output["comparison"]["elapsed_days"], days)
                    self.assertEqual(output["certificate"]["minimum_charge"], minimum)
                    self.assertEqual(output["observations"]["due_date"], due)
                    self.assertEqual(output["observations"]["paid_date"], paid)
                    self.assertEqual(actual["closing"], {})
                    self.assertEqual(output["comparison"]["scenario_status"], "calculated_unissued")
                    self.assertEqual(output["comparison"]["additional_payment_status"], "no_event_supplied")
                    self.assertEqual(output["comparison"]["monthly_status"], "not_computed")
                    self.assertEqual(output["comparison"]["combined_status"], "unresolved_not_computed")
                    self.assert_certificate(output, bindings)
                if due == "2026-06-30":
                    self.assertEqual(len(bindings["inputs"]["calendar"]), 2)
                    self.assertNotIn("2026-01-01", [row["calendar_date"] for row in bindings["inputs"]["calendar"]])

    def test_complete_flow_and_evidence_guards_on_direct_bindings(self):
        cases = []
        def altered(label, code, mutate):
            bindings = self.bindings()
            mutate(bindings["inputs"])
            cases.append((label, code, bindings))
        altered("scope", "QUEST_FLOW_SCOPE", lambda b: b["payments"][0]["scope"].update(asset_id="other-asset"))
        altered("currency", "QUEST_FLOW_CURRENCY", lambda b: b["payments"][0].update(currency="EUR"))
        altered("application link", "QUEST_APPLICATION_LINK", lambda b: b["applications"][0].update(payment_id="other-payment"))
        altered("extra obligation", "QUEST_FLOW_CARDINALITY", lambda b: b["obligations"].append({**deepcopy(b["obligations"][0]), "id": "extra-obligation"}))
        altered("duplicate payment event", "DUPLICATE_MAP_KEY", lambda b: b["payments"].append({**deepcopy(b["payments"][0]), "id": "extra-payment"}))
        altered("duplicate application", "DUPLICATE_MAP_KEY", lambda b: b["applications"].append(deepcopy(b["applications"][0])))
        altered("partial principal", "QUEST_FULL_PRINCIPAL_REQUIRED", lambda b: b["payments"][0]["amount"].update(value="999"))
        altered("missing evidence", "QUEST_FLOW_EVIDENCE", lambda b: b.update(evidence=[r for r in b["evidence"] if r["evidence_id"] != b["payments"][0]["evidence_id"]]))
        altered("late unused support", "QUEST_EVIDENCE_AFTER_CUTOFF", lambda b: b["evidence"].append({**deepcopy(b["evidence"][0]), "evidence_id": "unused-late", "observed_at": b["cutoff"]}))
        altered("late payment", "QUEST_FLOW_AFTER_CUTOFF", lambda b: b["payments"][0].update(observed_at=b["cutoff"]))
        altered("provenance mismatch", "QUEST_EVIDENCE_SOURCE", lambda b: b["payments"][0].update(source_ref="unlinked-source"))
        altered("effective date", "QUEST_FLOW_DATE", lambda b: b["applications"][0].update(effective_date="2026-07-01"))
        altered("wrong rounding", "QUEST_POLICY", lambda b: b.update(rounding="half_away_from_zero"))
        altered("principal domain", "QUEST_PRINCIPAL_DOMAIN", lambda b: b["obligations"][0]["amount"].update(value="0"))
        altered("rate domain", "QUEST_RATE_DOMAIN", lambda b: b.update(annual_target="-0.1"))
        altered("selected ID", "QUEST_PAYMENT_REQUIRED", lambda b: b.update(payment_id="unavailable-payment"))
        for label, code, bindings in cases:
            with self.subTest(case=label):
                self.assert_blocked(self.compare(bindings), code)

    def test_calendar_lookup_truth_and_bounded_domain_failures(self):
        cases = []
        def altered(label, code, mutate):
            bindings = self.bindings()
            mutate(bindings["inputs"])
            cases.append((label, code, bindings))
        altered("bad ordinal", "QUEST_CALENDAR_ORDINAL", lambda b: b["calendar"][1].update(ordinal="181"))
        altered("fractional ordinal", "QUEST_CALENDAR_ORDINAL", lambda b: b["calendar"][1].update(ordinal="182.5"))
        altered("contradictory truth", "QUEST_CALENDAR_TRUTH", lambda b: b["calendar_truth"][2].update(ordinal="181"))
        altered("missing endpoint", "QUEST_PAID_CALENDAR_REQUIRED", lambda b: b.update(calendar=b["calendar"][:1]))
        altered("duplicate date", "DUPLICATE_MAP_KEY", lambda b: b["calendar"].append({**deepcopy(b["calendar"][1]), "id": "other-calendar-id"}))
        altered("wrong calendar identity", "QUEST_CALENDAR_IDENTITY", lambda b: b["calendar"][1].update(version="2"))
        altered("calendar cutoff", "QUEST_CALENDAR_AFTER_CUTOFF", lambda b: b["calendar"][1].update(observed_at=b["cutoff"]))
        altered("calendar evidence", "QUEST_CALENDAR_EVIDENCE", lambda b: b["calendar"][1].update(evidence_id="missing-calendar-evidence"))
        too_long = self.variant("1000", "0.20", "2026-01-01", "2027-01-02")
        cases.append(("outside year", "QUEST_DAY_DOMAIN", too_long))
        too_large = self.variant("1000000", "1")
        cases.append(("search bracket", "QUEST_CENT_SEARCH_DOMAIN", too_large))
        for label, code, bindings in cases:
            with self.subTest(case=label):
                self.assert_blocked(self.compare(bindings), code)

    def test_half_away_and_round_terminal_mutations_fail_exact_certificate(self):
        half_away = '  define chosen_index = if minimum_index == 0.0 then 0.0 else (if target_power < pivot_power then minimum_index - 1.0 else minimum_index);\n'
        rounded_total = '  define chosen_index = (quantize(principal + principal * annual_target, quantum, "half_even") - principal) / quantum;\n'
        for name, replacement, amount in [("half_away", half_away, "0.01"), ("round_terminal", rounded_total, "0.03")]:
            with self.subTest(mutation=name):
                text, count = re.subn(r"  define chosen_index = [^\n]+\n", replacement, self.text)
                self.assertEqual(count, 1)
                self.assert_blocked(self.compare(self.variant(amount, "0.50", "2026-01-01", "2027-01-01"), text=text), "QUEST_HALF_EVEN_CERTIFICATE")

    def test_power_library_domain_and_zero_exponent(self):
        text = (self.folder / "power.spl").read_text(encoding="utf-8")
        self.assertNotIn("int_power", text)
        self.assertNotIn("pow(", text)
        text = text.rsplit("}", 1)[0] + 'emit "power" = result; }'
        program = check_schedule(parse(text))
        for base, exponent, expected, code in [("1.5", "0", Fraction(1), None),
                                                ("-2", "3", Fraction(-8), None),
                                                ("2", "365", Fraction(2) ** 365, None),
                                                ("1.5", "1.5", None, "QUEST_POWER_INTEGER"),
                                                ("1.5", "366", None, "QUEST_POWER_DOMAIN")]:
            result = evaluate(program, {"base": base, "exponent": exponent}, {}).to_dict()
            if code:
                self.assertEqual([d["code"] for d in result["diagnostics"]], [code])
                self.assertEqual(result["emissions"], {})
            else:
                self.assertEqual(result["status"], "calculated", result["diagnostics"])
                self.assertEqual(exact(result["emissions"]["power"]), expected)


if __name__ == "__main__":
    unittest.main()
