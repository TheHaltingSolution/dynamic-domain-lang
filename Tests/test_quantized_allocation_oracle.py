"""Independent hand controls for quantized original-parent allocation."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.quantized_allocation import QuantizedAllocationOracleError, exact_json, quantized_allocation


ROOT = Path(__file__).resolve().parents[1]


def fixture(amount="0.01", weights=("1", "1")):
    data = json.loads((ROOT / "cases/quantized-allocation/neutral.json").read_text(encoding="utf-8"))
    data["parents"][0]["amount"] = amount
    for row, weight in zip(data["authorities"][0]["terms"], weights):
        row["weight"] = weight
    return data


def supplied(data, amounts=("0", "0.01")):
    data["policy"]["method"] = "authorized_supplied_cents"
    data["opening_state"]["policy"] = deepcopy(data["policy"])
    authority = data["authorities"][0]
    authority["method"] = data["policy"]["method"]
    authority["supplied_allocation_ids"] = ["allocation-X", "allocation-Y"]
    data["supplied_allocations"] = [{"id": "allocation-" + recipient, "parent_id": data["parents"][0]["id"], "recipient_id": recipient,
                                      "scope": deepcopy(data["scope"]), "amount": amount, "observed_at": "2026-02-02T00:00:00Z",
                                      "source_ref": "synthetic-authorized-amount-" + recipient, "evidence_ref": "authority-source"}
                                     for recipient, amount in zip(("X", "Y"), amounts)]


def successor(previous, previous_input, amount="0.03"):
    data = deepcopy(previous_input)
    data.update(case_id="quantized-allocation-q2", period={"start": previous["period"]["end"], "end": "2026-07-01"},
                as_of="2026-06-30", cutoff="2026-07-03T00:00:00Z")
    data["opening_state"] = exact_json(previous["closing_state"])
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
    parent = deepcopy(data["parents"][0])
    parent.update(id="parent-q2", amount=amount, effective_date="2026-05-01", observed_at="2026-05-02T00:00:00Z",
                  source_ref="synthetic-parent-q2", upstream_ref="synthetic:parent-ledger-q2#line-1", authority_id="authority-q2")
    authority = deepcopy(data["authorities"][0])
    authority.update(id="authority-q2", parent_id=parent["id"], parent_upstream_ref=parent["upstream_ref"], effective=deepcopy(data["period"]),
                     approved_date="2026-04-01", recorded_date="2026-04-01", observed_at="2026-04-02T00:00:00Z", source_ref="synthetic-authority-q2")
    data["parents"], data["authorities"] = [parent], [authority]
    return data


class QuantizedAllocationOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(QuantizedAllocationOracleError) as raised:
            quantized_allocation(data)
        self.assertEqual(str(raised.exception), code)

    def amounts(self, result, field="selected_amount"):
        return [row[field] for row in result["allocations"][0]["children"]]

    def test_single_cent_equal_weights_authorized_ascii_tie(self):
        result = quantized_allocation(fixture())
        allocation = result["allocations"][0]
        self.assertEqual(self.amounts(result), [Fraction(1, 100), 0])
        self.assertEqual(allocation["ranked_recipient_ids"], ["X", "Y"])
        self.assertEqual(allocation["residual_cents"], 1)
        self.assertEqual([row["fractional_cent_remainder"] for row in allocation["children"]], [Fraction(1, 2)] * 2)
        self.assertEqual([row["rank"] for row in allocation["children"]], [1, 2])
        self.assertEqual([row["weighted_residual_cent"] for row in allocation["children"]], [1, 0])
        self.assertEqual(result["child_allocation_total"], Fraction(1, 100))
        self.assertEqual(result["recognized_amount_space"], "selected_children_only")
        self.assertEqual(result["payment_status"], "not_a_payment_measure")

    def test_half_even_parent_ties_are_exact_and_once(self):
        for original, cents in (("0.005", 0), ("0.015", 2), ("0.025", 2), ("0.035", 4)):
            with self.subTest(original=original):
                result = quantized_allocation(fixture(original))
                self.assertEqual(result["rounded_target_total"], Fraction(cents, 100))
                self.assertEqual(result["child_allocation_total"], Fraction(cents, 100))
                self.assertEqual(result["parent_rounding_delta_total"], Fraction(cents, 100) - Fraction(original))

    def test_fractional_original_distinguishes_target_quota_from_allocate_first(self):
        result = quantized_allocation(fixture("0.015", ("1", "2")))
        rows = result["allocations"][0]["children"]
        self.assertEqual([row["original_parent_exact_quota"] for row in rows], [Fraction(1, 200), Fraction(1, 100)])
        self.assertEqual([row["target_exact_share"] for row in rows], [Fraction(1, 150), Fraction(1, 75)])
        self.assertEqual(self.amounts(result), [Fraction(1, 100), Fraction(1, 100)])
        # Original quota X=.005 would independently half-even round to zero.
        self.assertEqual(result["child_allocation_total"], Fraction(1, 50))
        self.assertNotEqual(self.amounts(result), [0, Fraction(1, 100)])
        self.assertEqual(result["parent_rounding_delta_total"], Fraction(1, 200))

    def test_descending_remainder_precedes_id_and_retains_exact_fractions(self):
        result = quantized_allocation(fixture("0.07", ("1/3", "1/6")))
        allocation = result["allocations"][0]
        self.assertEqual(allocation["weight_denominator"], Fraction(1, 2))
        self.assertEqual(self.amounts(result), [Fraction(5, 100), Fraction(2, 100)])
        self.assertEqual([row["floor_base_cents"] for row in allocation["children"]], [4, 2])
        self.assertEqual([row["fractional_cent_remainder"] for row in allocation["children"]], [Fraction(2, 3), Fraction(1, 3)])
        result = quantized_allocation(fixture("0.01", ("1", "2")))
        self.assertEqual(result["allocations"][0]["ranked_recipient_ids"], ["Y", "X"])
        self.assertEqual(self.amounts(result), [0, Fraction(1, 100)])

    def test_zero_weight_and_zero_parent_do_not_create_fallback_allocations(self):
        result = quantized_allocation(fixture("0.01", ("0", "1")))
        self.assertEqual(self.amounts(result), [0, Fraction(1, 100)])
        result = quantized_allocation(fixture("0"))
        self.assertEqual(self.amounts(result), [0, 0])
        self.assertEqual(result["allocations"][0]["residual_cents"], 0)
        self.reject(fixture("0", ("0", "0")), "QA_ZERO_WEIGHT_DENOMINATOR")

    def test_whole_cent_equality_needs_no_residual(self):
        result = quantized_allocation(fixture("2", ("1", "3")))
        self.assertEqual(self.amounts(result), [Fraction(1, 2), Fraction(3, 2)])
        self.assertEqual(result["allocations"][0]["residual_cents"], 0)
        self.assertEqual(result["parent_rounding_delta_total"], 0)

    def test_multiple_residual_cents_and_finite_recipient_bound(self):
        data = fixture("0.03")
        registry_template = data["recipient_registry"][0]
        term_template = data["authorities"][0]["terms"][0]
        data["recipient_registry"] = []
        data["authorities"][0]["terms"] = []
        identities = ["R" + str(index) for index in range(8)]
        for identity in identities:
            row = deepcopy(registry_template)
            row.update(id=identity, source_ref="synthetic-recipient-" + identity)
            data["recipient_registry"].append(row)
            term = deepcopy(term_template)
            term.update(id="weight-" + identity, recipient_id=identity, source_ref="synthetic-weight-" + identity)
            data["authorities"][0]["terms"].append(term)
        data["authorities"][0]["recipient_ids"] = identities
        data["opening_state"]["recipient_registry"] = deepcopy(data["recipient_registry"])
        result = quantized_allocation(data)
        self.assertEqual(self.amounts(result), [Fraction(1, 100)] * 3 + [0] * 5)
        self.assertEqual(result["allocations"][0]["residual_cents"], 3)
        extra = deepcopy(registry_template)
        extra["id"] = "R8"
        data["recipient_registry"].append(extra)
        self.reject(data, "QA_RECIPIENT_BOUND")

    def test_each_original_parent_rounds_separately_without_parent_child_doublecount(self):
        data = fixture("0.005")
        parent = deepcopy(data["parents"][0])
        parent.update(id="second-parent", source_ref="synthetic-second-parent", upstream_ref="synthetic:second#line-1", authority_id="second-authority")
        authority = deepcopy(data["authorities"][0])
        authority.update(id="second-authority", parent_id=parent["id"], parent_upstream_ref=parent["upstream_ref"])
        data["parents"].append(parent)
        data["authorities"].append(authority)
        result = quantized_allocation(data)
        self.assertEqual(result["original_parent_total"], Fraction(1, 100))
        self.assertEqual(result["rounded_target_total"], 0)
        self.assertEqual(result["child_allocation_total"], 0)
        self.assertEqual(result["parent_count"], 2)
        self.assertEqual(quantized_allocation(fixture())["child_allocation_total"], Fraction(1, 100))

    def test_explicit_supplied_amounts_can_disagree_with_weight_method(self):
        data = fixture()
        supplied(data)
        result = quantized_allocation(data)
        self.assertEqual(self.amounts(result), [0, Fraction(1, 100)])
        self.assertEqual(self.amounts(result, "weighted_amount"), [Fraction(1, 100), 0])
        self.assertEqual(result["method"], "authorized_supplied_cents")
        self.assertEqual(result["child_allocation_total"], result["rounded_target_total"])

    def test_supplied_allocations_require_cent_integrality_completeness_and_conservation(self):
        data = fixture()
        supplied(data, ("0.005", "0.005"))
        self.reject(data, "QA_SUPPLIED_MINOR_UNIT")
        data = fixture()
        supplied(data, ("0.01", "0.01"))
        self.reject(data, "QA_SUPPLIED_TARGET_CONSERVATION")
        data = fixture()
        supplied(data)
        data["authorities"][0]["supplied_allocation_ids"].pop()
        self.reject(data, "QA_COMPLETE_SUPPLIED_ALLOCATIONS")
        data = fixture()
        supplied(data)
        data["supplied_allocations"][1]["recipient_id"] = "X"
        self.reject(data, "QA_SUPPLIED_RECIPIENT_REFERENCE")

    def test_weight_method_rejects_unmatched_supplied_child_amounts(self):
        data = fixture()
        supplied(data)
        data["policy"]["method"] = data["authorities"][0]["method"] = "exact_weights_largest_remainder"
        data["opening_state"]["policy"] = deepcopy(data["policy"])
        self.reject(data, "QA_UNEXPECTED_SUPPLIED_ALLOCATIONS")
        data["authorities"][0]["supplied_allocation_ids"] = []
        self.reject(data, "QA_UNMATCHED_SUPPLIED_ALLOCATION")

    def test_physical_permutations_do_not_change_finance_or_canonicalized_history(self):
        data = fixture()
        expected = exact_json(quantized_allocation(data))
        data["recipient_registry"].reverse()
        data["authorities"][0]["terms"].reverse()
        data["authorities"][0]["recipient_ids"].reverse()
        data["evidence"].reverse()
        self.assertEqual(exact_json(quantized_allocation(data)), expected)

    def test_stable_ascii_id_lexical_order_is_case_sensitive(self):
        data = fixture()
        data["recipient_registry"][1]["id"] = "a"
        data["opening_state"]["recipient_registry"] = deepcopy(data["recipient_registry"])
        data["authorities"][0]["recipient_ids"] = ["a", "X"]
        data["authorities"][0]["terms"][1]["recipient_id"] = "a"
        result = quantized_allocation(data)
        self.assertEqual(result["allocations"][0]["ranked_recipient_ids"], ["X", "a"])
        data["recipient_registry"][0]["id"] = "é"
        self.reject(data, "QA_ASCII_ID")

    def test_empty_current_parent_population_is_explicit_zero(self):
        data = fixture()
        data["parents"] = data["authorities"] = []
        result = quantized_allocation(data)
        self.assertEqual(result["allocations"], [])
        self.assertEqual(result["child_allocation_total"], 0)
        self.assertEqual(result["closing_state"]["consumed_parent_ids"], [])
        data["recipient_registry"] = []
        self.reject(data, "QA_RECIPIENT_BOUND")

    def test_missing_duplicate_and_unknown_recipient_terms_fail(self):
        data = fixture()
        data["authorities"][0]["recipient_ids"] = ["X"]
        self.reject(data, "QA_COMPLETE_RECIPIENTS")
        data = fixture()
        data["authorities"][0]["recipient_ids"] = ["X", "X"]
        self.reject(data, "QA_DUPLICATE_RECIPIENT_OR_REFERENCE")
        data = fixture()
        data["authorities"][0]["terms"].pop()
        self.reject(data, "QA_COMPLETE_WEIGHT_TERMS")
        for recipient in ("Z", "X"):
            data = fixture()
            data["authorities"][0]["terms"][1]["recipient_id"] = recipient
            self.reject(data, "QA_WEIGHT_RECIPIENT_REFERENCE")

    def test_parent_and_authority_identity_scope_and_unused_records_fail(self):
        data = fixture()
        data["parents"][0]["authority_id"] = "missing"
        self.reject(data, "QA_PARENT_AUTHORITY_REQUIRED")
        data = fixture()
        data["authorities"][0]["parent_upstream_ref"] = "synthetic:unknown#line-1"
        self.reject(data, "QA_AUTHORITY_PARENT_SCOPE")
        data = fixture()
        data["authorities"][0]["scope"]["pool_id"] = "other-pool"
        self.reject(data, "QA_FACT_SCOPE")
        data = fixture()
        extra = deepcopy(data["authorities"][0])
        extra.update(id="unused-invalid-authority", approved=False)
        data["authorities"].append(extra)
        self.reject(data, "QA_AUTHORITY_CARDINALITY")

    def test_original_parent_alias_under_new_row_id_does_not_create_more_value(self):
        data = fixture()
        alias = deepcopy(data["parents"][0])
        alias.update(id="alias", source_ref="renamed-parent-source", authority_id="alias-authority")
        data["parents"].append(alias)
        authority = deepcopy(data["authorities"][0])
        authority.update(id="alias-authority", parent_id=alias["id"])
        data["authorities"].append(authority)
        self.reject(data, "QA_PARENT_SOURCE_ALREADY_CONSUMED")
        data = fixture()
        data["parents"].append(deepcopy(data["parents"][0]))
        self.reject(data, "QA_DUPLICATE_ID")

    def test_exact_cutoff_authorization_asof_and_support_are_required(self):
        data = fixture()
        data["parents"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "QA_FACT_CUTOFF")
        data["parents"][0]["observed_at"] = "2026-04-02T23:59:59.999999999999Z"
        self.assertEqual(quantized_allocation(data)["child_allocation_total"], Fraction(1, 100))
        data = fixture()
        data["as_of"] = "2025-12-31"
        self.reject(data, "QA_AUTHORITY_ASOF")
        data = fixture()
        data["authorities"][0]["approved"] = False
        self.reject(data, "QA_AUTHORITY_ASOF")
        data = fixture()
        data["evidence"] = [row for row in data["evidence"] if row["id"] != "authority-source"]
        self.reject(data, "QA_EVIDENCE_REQUIRED")

    def test_actual_serialized_adjacent_state_preserves_originals_and_fresh_amounts(self):
        data = fixture()
        first = json.loads(json.dumps(exact_json(quantized_allocation(data))))
        following = successor(first, data)
        result = quantized_allocation(following)
        self.assertEqual(self.amounts(result), [Fraction(2, 100), Fraction(1, 100)])
        self.assertEqual(result["child_allocation_total"], Fraction(3, 100))
        self.assertEqual(result["closing_state"]["consumed_parent_ids"], ["parent-q1", "parent-q2"])
        self.assertEqual(result["closing_state"]["history"][0]["parents"][0], data["parents"][0])
        self.assertEqual(len(result["closing_state"]["history"]), 2)

    def test_history_predecessor_replay_and_cross_scope_carry_fail(self):
        data = fixture()
        first = quantized_allocation(data)
        following = successor(first, data)
        following.pop("prior_result")
        self.reject(following, "QA_PREDECESSOR_REQUIRED")
        following = successor(first, data)
        following["parents"][0]["upstream_ref"] = data["parents"][0]["upstream_ref"]
        following["authorities"][0]["parent_upstream_ref"] = following["parents"][0]["upstream_ref"]
        self.reject(following, "QA_PARENT_SOURCE_ALREADY_CONSUMED")
        following = successor(first, data)
        following["parents"][0]["id"] = "parent-q1"
        self.reject(following, "QA_ALREADY_CONSUMED_ID")
        following = successor(first, data)
        following["opening_state"]["scope"]["pool_id"] = "other-pool"
        self.reject(following, "QA_OPENING_SCOPE")
        following = successor(first, data)
        following["opening_state"]["consumed_parent_ids"] = []
        following["prior_result"]["closing_state"] = deepcopy(following["opening_state"])
        self.reject(following, "QA_OPENING_HISTORY_RECONCILIATION")

    def test_pinned_policy_and_original_historical_cutoff_cannot_be_rewritten(self):
        data = fixture()
        first = quantized_allocation(data)
        following = successor(first, data)
        following["policy"]["method"] = "authorized_supplied_cents"
        self.reject(following, "QA_PINNED_TERMS")
        following = successor(first, data)
        next(row for row in following["evidence"] if row["id"] == "parent-source")["observed_at"] = "2026-05-01T00:00:00Z"
        self.reject(following, "QA_EVIDENCE_CUTOFF")

    def test_negative_float_and_source_solved_amount_fields_are_rejected(self):
        for value in ("-0.01", 0.01):
            self.reject(fixture(value), "QA_EXACT_NONNEGATIVE_VALUE")
        data = fixture()
        data["authorities"][0]["terms"][0]["weight"] = "-1"
        self.reject(data, "QA_EXACT_NONNEGATIVE_VALUE")
        data = fixture()
        data["parents"][0]["solved_target"] = "0.01"
        self.reject(data, "QA_RECORD_FIELDS")

    def test_no_compiler_imports_and_finite_bounds_are_explicit(self):
        source = (ROOT / "oracles/quantized_allocation.py").read_text(encoding="utf-8")
        imports = [node for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertEqual({node.module if isinstance(node, ast.ImportFrom) else alias.name for node in imports
                          for alias in (node.names if isinstance(node, ast.Import) else [None])}, {"datetime", "fractions", "re"})
        data = fixture()
        data["policy"]["limits"]["recipients"] = 999
        self.reject(data, "QA_POLICY")

    def test_declared_parent_and_history_population_limits_are_enforced(self):
        data = fixture()
        parent_template, authority_template = deepcopy(data["parents"][0]), deepcopy(data["authorities"][0])
        data["parents"] = []
        data["authorities"] = []
        for index in range(4):
            parent = deepcopy(parent_template)
            parent.update(id="parent-" + str(index), source_ref="synthetic-parent-" + str(index),
                          upstream_ref="synthetic:parents#line-" + str(index), authority_id="authority-" + str(index))
            authority = deepcopy(authority_template)
            authority.update(id=parent["authority_id"], parent_id=parent["id"], parent_upstream_ref=parent["upstream_ref"])
            data["parents"].append(parent)
            data["authorities"].append(authority)
        self.assertEqual(quantized_allocation(data)["child_allocation_total"], Fraction(4, 100))
        parent_template.update(id="fifth-parent")
        authority_template.update(id="fifth-authority")
        data["parents"].append(parent_template)
        data["authorities"].append(authority_template)
        self.reject(data, "QA_PARENT_BOUND")
        data = fixture()
        data["opening_state"]["history"] = [{}] * 9
        self.reject(data, "QA_HISTORY_BOUND")


if __name__ == "__main__":
    unittest.main()
