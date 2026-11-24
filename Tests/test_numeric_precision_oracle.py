"""Independent hand controls from original basis facts and explicit policy."""
import ast
from copy import deepcopy
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import unittest

from oracles.numeric_precision import NumericPrecisionOracleError, MODES, numeric_precision, exact_json, registration

ROOT = Path(__file__).resolve().parents[1]


def fixture(name="money_half_even_row"):
    return json.loads((ROOT / "cases/numeric-precision/neutral.json").read_text(encoding="utf-8"))["scenarios"][name]


def repin(data):
    data["policy_ref"] = registration(data["policy"])
    return data


def bases(data, values, total):
    template = fixture()["lines"][0]
    data["lines"] = []
    for index, value in enumerate(values):
        row = deepcopy(template); row.update(id="line-" + str(index), original_ref="original-basis#" + str(index), scope=deepcopy(data["scope"])); row["basis"]["value"] = value
        data["lines"].append(row)
    data["population"].update(row_ids=[row["id"] for row in data["lines"]], basis_total={"dimension": "Money", "currency": "USD", "value": total})
    return data


class NumericPrecisionOracleTests(unittest.TestCase):
    def reject(self, data, code=None):
        before = deepcopy(data)
        with self.assertRaises(NumericPrecisionOracleError) as caught: numeric_precision(data)
        if code is not None: self.assertEqual(str(caught.exception), code)
        self.assertEqual(data, before)

    def check(self, data):
        result = numeric_precision(data); statement = result["statement"]
        self.assertEqual(statement["sum_rounded_detail"] + statement["rounding_bridge"], statement["selected_total"])
        self.assertEqual(statement["exact_before_ratio_rounding"] + statement["ratio_rounding_effect_total"] + statement["money_rounding_delta"], statement["selected_total"])
        self.assertEqual(statement["total_adjustment"], statement["selected_total"] - statement["exact_before_ratio_rounding"])
        self.assertEqual(result["issuance_status"], "unissued_calculation")
        self.assertEqual(result["payment_evidence_status"], "not_part_of_profile")
        self.assertFalse(result["bank_movement_created"])
        self.assertEqual(result["ratio_precision"]["measure"], "Ratio")
        self.assertEqual(statement["money_measure"], "USD")
        return result

    def test_six_supplied_policies_and_hand_statement_bridges(self):
        for name, amount, bridge in (("ratio_half_even", F(1234), F()), ("ratio_half_away", F(1235), F()),
                ("money_half_even_row", F(), F()), ("money_half_even_aggregate", F(1, 100), F(1, 100)),
                ("money_half_away_row", F(1, 50), F()), ("money_half_away_aggregate", F(1, 100), F(-1, 100))):
            result = self.check(fixture(name))
            self.assertEqual((result["statement"]["selected_total"], result["statement"]["rounding_bridge"]), (amount, bridge))

    def test_ratio_quantum_separate_from_usd_quantum_and_ratio_money_effects(self):
        for name, rounded, delta, money in (("ratio_half_even", F(617, 5000), F(-1, 20000), F(-1, 2)), ("ratio_half_away", F(247, 2000), F(1, 20000), F(1, 2))):
            result = self.check(fixture(name)); ratio, statement = result["ratio_precision"], result["statement"]
            self.assertEqual((ratio["exact_ratio"], ratio["ratio_quantum"], ratio["rounded_ratio"], ratio["ratio_rounding_delta"]), (F(2469, 20000), F(1, 10000), rounded, delta))
            self.assertEqual((statement["money_quantum"], statement["exact_before_ratio_rounding"], statement["ratio_rounding_effect_total"]), (F(1, 100), F(2469, 2), money))

    def test_percentage_two_and_fraction_four_precision_preserve_original_units(self):
        data = fixture("ratio_half_even"); first = self.check(data)
        data["ratio_expression"].update(expressed_unit="fraction", expressed_value="0.12345")
        data["policy"].update(ratio_expression_unit="fraction", ratio_expressed_decimal_places=4); repin(data)
        second = self.check(data)
        self.assertEqual(first["statement"]["selected_total"], second["statement"]["selected_total"])
        self.assertEqual(first["ratio_precision"]["rounded_ratio"], second["ratio_precision"]["rounded_ratio"])
        self.assertNotEqual(first["ratio_precision"]["original"], second["ratio_precision"]["original"])
        self.assertEqual(second["ratio_precision"]["declared_decimal_places"], 4)

    def test_two_original_bases_derive_half_cents_without_supplied_earnings(self):
        result = self.check(fixture())
        self.assertEqual([row["basis"] for row in result["line_details"]], [F(1, 100), F(1, 100)])
        self.assertEqual([row["exact_after_ratio_rounding"] for row in result["line_details"]], [F(1, 200), F(1, 200)])
        self.assertEqual(result["statement"]["exact_after_ratio_rounding"], F(1, 100))
        self.assertEqual([row["displayed_rounded"] for row in result["line_details"]], [0, 0])

    def test_all_five_ratio_modes_at_positive_signed_tie(self):
        expected = {"floor": F(617, 5000), "ceiling": F(247, 2000), "toward_zero": F(617, 5000), "half_even": F(617, 5000), "half_away_from_zero": F(247, 2000)}
        self.assertEqual(set(MODES), set(expected))
        for mode, amount in expected.items():
            data = fixture("ratio_half_even"); data["policy"]["ratio_mode"] = mode; repin(data)
            self.assertEqual(self.check(data)["ratio_precision"]["rounded_ratio"], amount)

    def test_all_five_ratio_modes_at_negative_signed_tie(self):
        expected = {"floor": F(-247, 2000), "ceiling": F(-617, 5000), "toward_zero": F(-617, 5000), "half_even": F(-617, 5000), "half_away_from_zero": F(-247, 2000)}
        for mode, amount in expected.items():
            data = fixture("ratio_half_even"); data["ratio_expression"]["expressed_value"] = "-12.345"; data["policy"]["ratio_mode"] = mode; repin(data)
            self.assertEqual(self.check(data)["ratio_precision"]["rounded_ratio"], amount)

    def test_half_even_odd_neighbor_and_near_ties_without_float(self):
        for expressed, expected in (("12.355", F(309, 2500)), ("-12.355", F(-309, 2500)),
                ("12.344999999999999999", F(617, 5000)), ("12.345000000000000001", F(247, 2000))):
            data = fixture("ratio_half_even"); data["ratio_expression"]["expressed_value"] = expressed
            self.assertEqual(self.check(data)["ratio_precision"]["rounded_ratio"], expected)

    def test_all_five_money_modes_positive_ties_row_and_aggregate(self):
        expected = {"floor": F(), "ceiling": F(1, 50), "toward_zero": F(), "half_even": F(), "half_away_from_zero": F(1, 50)}
        for mode, row_total in expected.items():
            data = fixture(); data["policy"]["money_mode"] = mode; repin(data)
            self.assertEqual(self.check(data)["statement"]["selected_total"], row_total)
            data["policy"]["money_point"] = "aggregate"; repin(data)
            statement = self.check(data)["statement"]
            self.assertEqual((statement["selected_total"], statement["rounding_bridge"]), (F(1, 100), F(1, 100) - row_total))

    def test_all_five_money_modes_negative_ties_row_and_aggregate(self):
        expected = {"floor": F(-1, 50), "ceiling": F(), "toward_zero": F(), "half_even": F(), "half_away_from_zero": F(-1, 50)}
        for mode, row_total in expected.items():
            data = bases(fixture(), ["-0.01", "-0.01"], "-0.02"); data["policy"]["money_mode"] = mode; repin(data)
            self.assertEqual(self.check(data)["statement"]["selected_total"], row_total)
            data["policy"]["money_point"] = "aggregate"; repin(data)
            statement = self.check(data)["statement"]
            self.assertEqual((statement["selected_total"], statement["rounding_bridge"]), (F(-1, 100), F(-1, 100) - row_total))

    def test_signed_cancellation_has_explicit_directed_rounding_bridges(self):
        expected = {"floor": F(-1, 100), "ceiling": F(1, 100), "toward_zero": F(), "half_even": F(), "half_away_from_zero": F()}
        for mode, row_total in expected.items():
            data = bases(fixture(), ["0.01", "-0.01"], "0"); data["policy"].update(money_mode=mode, money_point="aggregate"); repin(data)
            statement = self.check(data)["statement"]
            self.assertEqual((statement["exact_after_ratio_rounding"], statement["sum_rounded_detail"], statement["selected_total"], statement["rounding_bridge"]), (0, row_total, 0, -row_total))

    def test_money_odd_parity_ties_and_noncent_quantum_are_explicit(self):
        for value, expected in (("0.03", F(1, 50)), ("-0.03", F(-1, 50))):
            data = bases(fixture(), [value], value)
            self.assertEqual(self.check(data)["statement"]["selected_total"], expected)
        for mode, expected in (("half_even", F()), ("half_away_from_zero", F(3, 100))):
            data = bases(fixture(), ["0.03"], "0.03"); data["policy"]["money_quantum"]["value"] = "0.03"; data["policy"]["money_mode"] = mode; repin(data)
            self.assertEqual(self.check(data)["statement"]["selected_total"], expected)

    def test_fractional_originals_and_rational_money_quantum(self):
        data = bases(fixture(), [{"numerator": "1", "denominator": "3"}], {"numerator": "1", "denominator": "3"})
        result = self.check(data)
        self.assertEqual((result["statement"]["exact_after_ratio_rounding"], result["statement"]["selected_total"]), (F(1, 6), F(17, 100)))
        data = bases(fixture(), ["1"], "1"); data["policy"]["money_quantum"]["value"] = {"numerator": "1", "denominator": "3"}; repin(data)
        self.assertEqual(self.check(data)["statement"]["selected_total"], F(2, 3))

    def test_large_values_keep_exact_half_cent_parity(self):
        data = bases(fixture(), ["10000000000000000000.01"], "10000000000000000000.01")
        self.assertEqual(self.check(data)["statement"]["selected_total"], 5000000000000000000)
        data["policy"]["money_mode"] = "half_away_from_zero"; repin(data)
        self.assertEqual(self.check(data)["statement"]["selected_total"], F(500000000000000000001, 100))

    def test_zero_and_complete_empty_keep_quantum_validation(self):
        for mode in MODES:
            data = bases(fixture(), ["-0.000"], "0"); data["policy"]["money_mode"] = mode; repin(data)
            result = self.check(data); self.assertEqual(result["statement"]["selected_total"], 0); self.assertEqual(result["line_details"][0]["original"]["basis"]["value"], "-0.000")
            data = bases(data, [], "0"); self.assertEqual(self.check(data)["statement"]["selected_total"], 0)
        data["policy"]["money_quantum"]["value"] = "0"; repin(data); self.reject(data, "PRECISION_POSITIVE_QUANTUM")

    def test_zero_and_negative_quanta_reject_both_dimensions(self):
        for key in ("ratio_quantum", "money_quantum"):
            for value in ("0", "-0.000", "-0.01"):
                data = fixture(); data["policy"][key]["value"] = value; repin(data); self.reject(data, "PRECISION_POSITIVE_QUANTUM")

    def test_wrong_quantum_and_basis_dimensions_never_cast(self):
        data = fixture(); data["policy"]["ratio_quantum"] = {"dimension": "Money", "currency": "USD", "value": "0.0001"}; repin(data); self.reject(data, "PRECISION_RATIO_QUANTUM_DIMENSION")
        data = fixture(); data["policy"]["money_quantum"] = {"dimension": "Ratio", "value": "0.01"}; repin(data); self.reject(data, "PRECISION_MONEY_QUANTUM_DIMENSION")
        data = fixture(); data["lines"][0]["basis"] = {"dimension": "Quantity", "unit": "Download", "value": "0.01"}; self.reject(data, "PRECISION_BASIS_DIMENSION")

    def test_declared_precision_quantum_and_expression_unit_must_agree(self):
        data = fixture("ratio_half_even"); data["policy"]["ratio_quantum"]["value"] = "0.01"; repin(data); self.reject(data, "PRECISION_RATIO_QUANTUM_PRECISION")
        data = fixture("ratio_half_even"); data["ratio_expression"]["expressed_unit"] = "fraction"; self.reject(data, "PRECISION_EXPRESSION_AUTHORITY")
        for places in (-1, 7, True, "2"):
            data = fixture(); data["policy"]["ratio_expressed_decimal_places"] = places; repin(data); self.reject(data, "PRECISION_EXPRESSION_PRECISION")
        data = fixture("ratio_half_even"); data["policy"]["ratio_expressed_decimal_places"] = 0; data["policy"]["ratio_quantum"]["value"] = "0.01"; repin(data)
        self.assertEqual(self.check(data)["ratio_precision"]["rounded_ratio"], F(3, 25))

    def test_all_precisions_include_the_declared_upper_boundary(self):
        quanta = ("1", "0.1", "0.01", "0.001", "0.0001", "0.00001", "0.000001")
        expected = (F(), F(1, 10), F(3, 25), F(123, 1000), F(247, 2000), F(6173, 50000), F(1929, 15625))
        for places, quantum, rounded in zip(range(7), quanta, expected):
            data = fixture("ratio_half_even"); data["policy"].update(ratio_expression_unit="fraction", ratio_expressed_decimal_places=places); data["policy"]["ratio_quantum"]["value"] = quantum; data["ratio_expression"].update(expressed_unit="fraction", expressed_value="0.1234565"); repin(data)
            self.assertEqual(self.check(data)["ratio_precision"]["rounded_ratio"], rounded)

    def test_unsupported_modes_and_points_are_controlled_errors(self):
        for key in ("ratio_mode", "money_mode"):
            for value in ("half_up", "nearest", [], 1, False):
                data = fixture(); data["policy"][key] = value; repin(data); self.reject(data, "PRECISION_MODE")
        for key, value in (("ratio_point", "after_money"), ("money_point", "display_only"), ("bridge", "silently_assign_first_row")):
            data = fixture(); data["policy"][key] = value; repin(data); self.reject(data, "PRECISION_POINT")

    def test_currency_and_every_original_scope_are_explicit(self):
        for target in ("expression", "line", "population"):
            for key in fixture()["scope"]:
                data = fixture(); holder = data["ratio_expression"] if target == "expression" else data["lines"][0] if target == "line" else data["population"]
                holder["scope"][key] = "other"; self.reject(data)
        data = fixture(); data["scope"]["currency"] = "EUR"; self.reject(data, "PRECISION_CURRENCY")
        data = fixture(); data["policy"]["money_quantum"]["currency"] = "EUR"; repin(data); self.reject(data, "PRECISION_CURRENCY")

    def test_missing_completeness_ids_and_signed_basis_control_reject(self):
        for field, value in (("complete", False), ("complete", None), ("row_ids", []), ("row_ids", ["line-1", "line-1"]), ("basis_total", {"dimension": "Money", "currency": "USD", "value": "0"})):
            data = fixture(); data["population"][field] = value; self.reject(data)
        data = fixture(); del data["population"]; self.reject(data, "PRECISION_FIELDS")

    def test_duplicate_originals_reject_and_equal_contributors_stay_distinct(self):
        result = self.check(fixture("money_half_away_row")); self.assertEqual(len(result["line_details"]), 2); self.assertEqual(result["statement"]["selected_total"], F(1, 50))
        for field in ("id", "original_ref"):
            data = fixture(); data["lines"][1][field] = data["lines"][0][field]; self.reject(data, "PRECISION_ORIGINAL_REUSE")

    def test_eight_row_bound_and_ninth_row_rejection(self):
        data = bases(fixture(), ["0.01"] * 8, "0.08"); self.assertEqual(self.check(data)["statement"]["selected_total"], 0)
        data = bases(data, ["0.01"] * 9, "0.09"); self.reject(data, "PRECISION_ROW_BOUND")

    def test_policy_document_changes_under_old_pin_reject(self):
        for key, value in (("money_point", "aggregate"), ("ratio_mode", "half_away_from_zero"), ("money_mode", "ceiling"), ("revision", "2")):
            data = fixture(); data["policy"][key] = value; self.reject(data, "PRECISION_POLICY_PIN")
        data = fixture(); data["policy_ref"]["id"] = "another"; self.reject(data, "PRECISION_POLICY_PIN")

    def test_explicit_policy_repin_changes_result_without_version_history_claim(self):
        data = fixture(); first = self.check(data); old = deepcopy(data["policy_ref"])
        data["policy"].update(revision="new-explicit-configuration", money_point="aggregate"); repin(data); second = self.check(data)
        self.assertNotEqual(old, data["policy_ref"]); self.assertEqual((first["statement"]["selected_total"], second["statement"]["selected_total"]), (0, F(1, 100)))
        data["policy"]["revision"] = old["revision"]; repin(data)
        self.assertEqual(self.check(data)["statement"]["selected_total"], F(1, 100))
        # A stateless supplied-content pin has no absent previous registry to
        # compare. Reused revision authenticity/immutability is outside this API.

    def test_policy_hash_is_exact_document_correspondence_not_numeric_normalization(self):
        data = fixture(); expected = sha256(json.dumps(data["policy"], sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(data["policy_ref"]["sha256"], expected)
        before = self.check(data)["statement"]["selected_total"]
        data["policy"]["money_quantum"]["value"] = "0.010"; self.reject(data, "PRECISION_POLICY_PIN"); repin(data)
        self.assertEqual(self.check(data)["statement"]["selected_total"], before)

    def test_permutation_and_split_merge_invariance_are_policy_conditional(self):
        for point in ("row", "aggregate"):
            data = fixture(); data["policy"]["money_point"] = point; repin(data); before = self.check(data)
            data["lines"].reverse(); data["population"]["row_ids"].reverse(); after = self.check(data)
            self.assertEqual(before["statement"], after["statement"])
            merged = bases(deepcopy(data), ["0.02"], "0.02"); result = self.check(merged)
            if point == "aggregate": self.assertEqual(result["statement"]["selected_total"], before["statement"]["selected_total"])
            else: self.assertNotEqual(result["statement"]["selected_total"], before["statement"]["selected_total"])

    def test_unicode_original_lexemes_and_exact_output_serialization(self):
        data = fixture(); identity = "participant:e\u0301/\u96ea:#\x00"
        for holder in (data, data["ratio_expression"], data["population"], *data["lines"]): holder["scope"]["participant_id"] = identity
        data["lines"][0]["basis"]["value"] = "0.0100"
        result = self.check(data); self.assertEqual(result["scope"]["participant_id"], identity); self.assertEqual(result["line_details"][0]["original"]["basis"]["value"], "0.0100")
        self.assertEqual(exact_json(result)["line_details"][0]["exact_after_ratio_rounding"], "1/200")
        data["ratio_expression"]["scope"]["participant_id"] = identity.replace("e\u0301", "\u00e9"); self.reject(data, "PRECISION_EXPRESSION_AUTHORITY")

    def test_strict_exact_numbers_and_no_precomputed_answers(self):
        for value in (.5, True, "1e3", "0.5 ", "+0.5", "1/3", {"numerator": "2", "denominator": "4"}, {"numerator": "-0", "denominator": "1"}):
            data = fixture(); data["ratio_expression"]["expressed_value"] = value; self.reject(data)
        for target, key in (("root", "selected_total"), ("line", "earned"), ("expression", "rounded_ratio")):
            data = fixture(); holder = data if target == "root" else data["lines"][0] if target == "line" else data["ratio_expression"]; holder[key] = "0"; self.reject(data, "PRECISION_FIELDS")

    def test_no_mutation_or_implementation_dependencies(self):
        data = fixture("ratio_half_away"); before = deepcopy(data); result = self.check(data); self.assertEqual(data, before)
        result["policy"]["ratio_mode"] = "floor"; result["ratio_precision"]["original"]["scope"]["asset_id"] = "changed"; self.assertEqual(data, before)
        tree = ast.parse((ROOT / "oracles/numeric_precision.py").read_text(encoding="utf-8"))
        imports = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} | {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertEqual(imports, {"copy", "fractions", "hashlib", "json", "re"})
        self.assertFalse({node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)} & {"open", "eval", "exec", "__import__"})


if __name__ == "__main__": unittest.main()
