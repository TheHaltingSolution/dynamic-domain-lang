"""Hand calculations and bounded histories for the independent M1a oracle.

These tests construct neutral facts themselves and import no compiler or
canonical projection. Native/canonical comparison is a separate test layer.
"""
from copy import deepcopy
from fractions import Fraction
import itertools
import unittest

from oracles.ordinary_royalties import OracleError, exact_json, ordinary_royalties


def neutral(method="period_marginal", amounts=("150",), opening="0"):
    scope = {"contract_id": "synthetic-m1", "participant_id": "participant-a",
             "pool_id": "pool-a", "asset_id": "asset-a", "currency": "USD"}
    period = {"start": "2025-04-01", "end": "2025-07-01"}
    return {
        "schema_version": "m1-neutral/1",
        "scope": scope, "period": period, "cutoff": "2025-07-02T00:00:00Z",
        "policy": {"method": method, "tiers": [
            {"id": "first", "sequence": 1, "lower": "0", "upper": "100", "rate": "1/10"},
            {"id": "second", "sequence": 2, "lower": "100", "upper": None, "rate": "1/5"}],
            "cap": "100", "floor": "100", "reset_period_cap": False,
            "rounding": "exact_no_rounding", "negative_basis": "reject",
            "threshold_equality": "lower_inclusive"},
        "opening_state": {"scope": dict(scope), "method": method, "balance": opening,
                          "period": dict(period)},
        "evidence": [{"id": "ledger", "observed_at": "2025-07-01T00:00:00Z"}],
        "facts": [{"id": "fact-" + str(i), "amount": amount,
                   "effective_date": "2025-05-01", "observed_at": "2025-07-01T00:00:00Z",
                   "evidence_id": "ledger"} for i, amount in enumerate(amounts)]}


class M1OracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaisesRegex(OracleError, "^" + code + "$"):
            ordinary_royalties(data)

    def test_neutral_schema_is_explicit_and_versioned(self):
        for version in ["m1-neutral/99", None, 1, True]:
            data = neutral()
            data["schema_version"] = version
            self.reject(data, "unsupported_neutral_schema")
        data = neutral()
        del data["schema_version"]
        self.reject(data, "malformed_neutral_fact")

    def test_manual_period_marginal_and_whole_base_discriminator(self):
        result = ordinary_royalties(neutral())
        self.assertEqual((result["basis"], result["uncapped"], result["entitlement"], result["closing_balance"]), (150, 20, 20, 0))
        self.assertEqual(ordinary_royalties(neutral("period_whole_base"))["entitlement"], 30)
        for basis, marginal, whole in [(0, 0, 0), (50, 5, 5), (100, 10, 20), (150, 20, 30), (200, 30, 40)]:
            with self.subTest(basis=basis):
                self.assertEqual(ordinary_royalties(neutral(amounts=(basis,)))["entitlement"], marginal)
                self.assertEqual(ordinary_royalties(neutral("period_whole_base", (basis,)))["entitlement"], whole)

    def test_manual_cumulative_marginal_and_carried_state(self):
        data = neutral("cumulative_marginal", ("70",), "80")
        result = ordinary_royalties(data)
        self.assertEqual((result["basis"], result["uncapped"], result["entitlement"], result["closing_balance"]), (70, 12, 12, 150))
        data["period"] = {"start": "2025-07-01", "end": "2025-10-01"}
        data["opening_state"] = exact_json(result["closing_state"])
        data["facts"][0].update(amount="50", effective_date="2025-07-01")
        self.assertEqual((ordinary_royalties(data)["entitlement"], ordinary_royalties(data)["closing_balance"]), (10, 200))

    def test_manual_cumulative_cap_and_exact_equality(self):
        data = neutral("cumulative_cap", ("80",), "70")
        result = ordinary_royalties(data)
        self.assertEqual((result["uncapped"], result["entitlement"], result["opening_consumed"], result["closing_balance"]), (80, 30, 70, 100))
        data["opening_state"] = exact_json(result["closing_state"])
        self.assertEqual(ordinary_royalties(data)["entitlement"], 0)
        for amount, expected in [(0, 0), (30, 30), (31, 30)]:
            self.assertEqual(ordinary_royalties(neutral("cumulative_cap", (amount,), "70"))["entitlement"], expected)

    def test_period_cap_requires_explicit_reset_and_boundary(self):
        data = neutral("period_cap", ("80",), "70")
        self.assertEqual(ordinary_royalties(data)["entitlement"], 30)
        data["opening_state"]["period"] = {"start": "2025-01-01", "end": "2025-04-01"}
        self.reject(data, "period_cap_reset_required")
        data["policy"]["reset_period_cap"] = True
        result = ordinary_royalties(data)
        self.assertEqual((result["entitlement"], result["opening_consumed"], result["closing_balance"]), (80, 0, 80))
        data["opening_state"] = exact_json(result["closing_state"])
        self.reject(data, "invalid_reset_boundary")
        data["policy"]["reset_period_cap"] = False
        data["facts"][0]["amount"] = "30"
        self.assertEqual(ordinary_royalties(data)["entitlement"], 20)
        data["policy"]["reset_period_cap"] = True
        data["opening_state"]["period"] = {"start": "2025-03-01", "end": "2025-05-01"}
        self.reject(data, "invalid_reset_boundary")

    def test_nonrecoupable_floor_is_entitlement_and_no_advance_state(self):
        for amounts, earned, entitlement, topup in [(("80",), 80, 100, 20), (("100",), 100, 100, 0), (("120",), 120, 120, 0), ((), 0, 100, 100)]:
            result = ordinary_royalties(neutral("period_floor", amounts))
            self.assertEqual((result["uncapped"], result["entitlement"], result["floor_topup"], result["closing_balance"]), (earned, entitlement, topup, 0))

    def test_tiers_then_cap_has_both_manual_intermediates(self):
        data = neutral("tiers_then_cap")
        data["policy"]["cap"] = "15"
        result = ordinary_royalties(data)
        self.assertEqual((result["basis"], result["uncapped"], result["entitlement"], result["closing_balance"]), (150, 20, 15, 0))
        # Finite pairwise cases cross threshold, cap equality and zero cap.
        for (basis, earned), cap in itertools.product([(0, 0), (50, 5), (100, 10), (150, 20), (200, 30)], [0, 5, 15, 30]):
            data = neutral("tiers_then_cap", (basis,))
            data["policy"]["cap"] = cap
            result = ordinary_royalties(data)
            self.assertEqual((result["uncapped"], result["entitlement"]), (earned, min(earned, cap)))

    def test_zero_empty_and_fractional_arithmetic(self):
        for method in ["period_marginal", "period_whole_base", "cumulative_marginal", "period_cap", "cumulative_cap", "tiers_then_cap"]:
            for amounts in [(), ("0",)]:
                result = ordinary_royalties(neutral(method, amounts))
                self.assertEqual((result["basis"], result["uncapped"], result["entitlement"], result["closing_balance"]), (0, 0, 0, 0))
        data = neutral(amounts=("1/3", "1/6"))
        self.assertEqual(ordinary_royalties(data)["entitlement"], Fraction(1, 20))
        data = neutral("cumulative_marginal", ("1/3",), "299/3")
        self.assertEqual((ordinary_royalties(data)["entitlement"], ordinary_royalties(data)["closing_balance"]), (Fraction(1, 30), 100))
        self.assertEqual(exact_json(ordinary_royalties(data))["entitlement"], "1/30")

    def test_split_merge_and_physical_permutation(self):
        for method in ["period_marginal", "period_whole_base", "cumulative_marginal", "period_cap", "cumulative_cap", "period_floor", "tiers_then_cap"]:
            opening = "80" if method == "cumulative_marginal" else "70" if method in {"cumulative_cap", "period_cap"} else "0"
            combined = ordinary_royalties(neutral(method, ("70",), opening))
            for first in range(0, 71, 7):
                data = neutral(method, (first, 70 - first), opening)
                split = ordinary_royalties(data)
                for key in ["basis", "uncapped", "entitlement", "closing_balance"]:
                    self.assertEqual(split[key], combined[key])
                data["facts"].reverse()
                data["policy"]["tiers"].reverse()
                self.assertEqual(ordinary_royalties(data), split)

    def test_bounded_cumulative_histories_and_carry(self):
        data = neutral("cumulative_marginal", (), "0")
        total_earned = Fraction()
        for amount, expected_earned, expected_balance in [(30, 3, 30), (50, 5, 80), (70, 12, 150), (20, 4, 170)]:
            data["facts"] = neutral(amounts=(amount,))["facts"]
            result = ordinary_royalties(data)
            self.assertEqual((result["entitlement"], result["closing_balance"]), (expected_earned, expected_balance))
            total_earned += result["entitlement"]
            data["opening_state"] = exact_json(result["closing_state"])
        self.assertEqual(total_earned, 24)
        # Every two-step history over this bounded set telescopes exactly.
        for first, second in itertools.product([0, 25, 80, 100, 150], repeat=2):
            one = ordinary_royalties(neutral("cumulative_marginal", (first,)))
            data = neutral("cumulative_marginal", (second,))
            data["opening_state"] = exact_json(one["closing_state"])
            two = ordinary_royalties(data)
            together = ordinary_royalties(neutral("cumulative_marginal", (first, second)))
            self.assertEqual(one["entitlement"] + two["entitlement"], together["entitlement"])
            self.assertEqual(two["closing_balance"], first + second)

    def test_bounded_cap_histories_never_reuse_capacity(self):
        for first, second in itertools.product([0, 20, 30, 80, 100], repeat=2):
            data = neutral("cumulative_cap", (first,), "70")
            one = ordinary_royalties(data)
            data["opening_state"] = exact_json(one["closing_state"])
            data["facts"] = neutral(amounts=(second,))["facts"]
            two = ordinary_royalties(data)
            self.assertEqual(one["entitlement"] + two["entitlement"], min(first + second, 30))
            self.assertEqual(two["closing_balance"], 70 + min(first + second, 30))

    def test_half_open_effective_period_and_strict_exact_cutoff(self):
        data = neutral(amounts=("50",))
        data["facts"][0]["effective_date"] = "2025-04-01"
        result = ordinary_royalties(data)
        self.assertEqual((result["basis"], result["included_ids"], result["excluded_ids"]), (50, ["fact-0"], []))
        for outside in ["2025-07-01", "2025-03-31"]:
            invalid = deepcopy(data)
            invalid["facts"][0]["effective_date"] = outside
            self.reject(invalid, "fact_outside_selected_period")
        data["cutoff"] = "2025-07-02T00:00:00.0000000002Z"
        data["facts"][0]["observed_at"] = "2025-07-02T01:00:00.0000000001+01:00"
        self.assertEqual(ordinary_royalties(data)["basis"], 50)
        data["facts"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "fact_after_cutoff")
        data = neutral()
        data["evidence"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "evidence_after_cutoff")

    def test_invalid_tiers_gap_overlap_lower_bounds_and_ids(self):
        changes = [
            ("noncontiguous_tiers", lambda d: d["policy"]["tiers"][0].update(lower="1")),
            ("noncontiguous_tiers", lambda d: d["policy"]["tiers"][1].update(lower="101")),
            ("noncontiguous_tiers", lambda d: d["policy"]["tiers"][1].update(lower="99")),
            ("invalid_tier_bounds", lambda d: d["policy"]["tiers"][0].update(upper="0")),
            ("unbounded_final_tier_required", lambda d: d["policy"]["tiers"][0].update(upper=None)),
            ("unbounded_final_tier_required", lambda d: d["policy"]["tiers"][1].update(upper="200")),
            ("duplicate_identity", lambda d: d["policy"]["tiers"][1].update(id="first")),
            ("duplicate_tier_sequence", lambda d: d["policy"]["tiers"][1].update(sequence=1)),
            ("tier_sequence_required", lambda d: d["policy"]["tiers"][1].update(sequence=True)),
            ("rate_domain", lambda d: d["policy"]["tiers"][0].update(rate="101/100")),
            ("tiers_required", lambda d: d["policy"].update(tiers=[])),
        ]
        for code, mutate in changes:
            with self.subTest(code=code):
                data = neutral()
                mutate(data)
                self.reject(data, code)

    def test_scope_currency_duplicate_and_evidence_guards(self):
        changes = [
            ("state_scope_mismatch", lambda d: d["opening_state"]["scope"].update(pool_id="other")),
            ("state_method_mismatch", lambda d: d["opening_state"].update(method="period_cap")),
            ("fact_scope_mismatch", lambda d: d["facts"][0].update(scope={**d["scope"], "asset_id": "other"})),
            ("unsupported_currency", lambda d: d["scope"].update(currency="EUR")),
            ("duplicate_identity", lambda d: d["facts"].append(deepcopy(d["facts"][0]))),
            ("duplicate_identity", lambda d: d["evidence"].append(deepcopy(d["evidence"][0]))),
            ("missing_evidence", lambda d: d["facts"][0].update(evidence_id="missing")),
            ("identity_required", lambda d: d["facts"][0].update(id="")),
        ]
        for code, mutate in changes:
            with self.subTest(code=code):
                data = neutral()
                mutate(data)
                self.reject(data, code)

    def test_nonnegative_case_rule_and_exact_transport(self):
        for method in ["period_marginal", "period_whole_base", "cumulative_marginal", "period_cap", "cumulative_cap", "period_floor", "tiers_then_cap"]:
            # A net-positive sum does not license an individually negative fact.
            self.reject(neutral(method, ("150", "-1")), "negative_amount")
        for amount in [1.5, True, "1e2", "1/0", "NaN", " 1", None]:
            self.reject(neutral(amounts=(amount,)), "exact_number_required")
        data = neutral("cumulative_cap", (), "101")
        self.reject(data, "cap_consumption_exceeds_limit")
        data = neutral(opening="1")
        self.reject(data, "carry_outside_selected_method")

    def test_no_implicit_policy_choices_or_malformed_defaults(self):
        for key in ["method", "tiers", "cap", "floor", "reset_period_cap", "rounding", "negative_basis", "threshold_equality"]:
            data = neutral()
            del data["policy"][key]
            self.reject(data, "malformed_neutral_fact")
        for key, value, code in [
            ("method", "historical_whole_base", "unsupported_method"),
            ("rounding", "cents", "selected_policy_required"),
            ("negative_basis", "floor_zero", "selected_policy_required"),
            ("threshold_equality", "upper_inclusive", "selected_policy_required"),
            ("reset_period_cap", "false", "explicit_cap_reset_required"),
            ("reset_period_cap", True, "reset_outside_period_cap"),
        ]:
            data = neutral()
            data["policy"][key] = value
            self.reject(data, code)
        data = neutral()
        data["facts"][0]["effective_date"] = "2025-02-30"
        self.reject(data, "invalid_date")
        data = neutral()
        data["cutoff"] = "2025-07-02T00:00:00"
        self.reject(data, "invalid_instant")
        data = neutral()
        data["opening_state"]["period"] = {"start": "2025-06-01", "end": "2025-08-01"}
        self.reject(data, "state_period_mismatch")


if __name__ == "__main__":
    unittest.main()
