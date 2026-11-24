"""Independent original-fact discriminators, prior to any SPL implementation."""
import ast
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest
from oracles.participation_bases import ParticipationBaseError, exact_json, participation_bases

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("gross_percent", "net_percent", "unit_rate", "unit_rate_then_participation")


def fixture(method="gross_percent"):
    data = json.loads((ROOT/"cases/participation-bases/neutral.json").read_text(encoding="utf-8"))
    data["method"] = method
    return data


def set_measure(data, kind, amount):
    data[kind][0]["amount"] = amount
    next(x for x in data["populations"] if x["kind"] == kind)["reported_total"] = amount
    return data


class ParticipationBaseOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaisesRegex(ParticipationBaseError, "^"+code+"$"):
            participation_bases(data)

    def test_four_original_fact_discriminators_and_visible_intermediates(self):
        results = [participation_bases(fixture(m)) for m in METHODS]
        self.assertEqual([r["earned"] for r in results], [25,20,150,75])
        self.assertEqual([r["selected_basis"] for r in results], [125,100,100,100])
        self.assertEqual([r["pre_participation"] for r in results], [25,20,150,150])
        self.assertEqual([r["applied_participation"] for r in results], [1,1,1,F(1,2)])
        self.assertEqual([r["rate_measure"] for r in results], ["Ratio","Ratio","USD/Download","USD/Download"])
        self.assertTrue(all((r["gross"],r["deductions"],r["net"],r["quantity"]) == (125,25,100,100) for r in results))
        self.assertTrue(all(r["issuance_status"] == "unissued" for r in results))

    def test_wrong_basis_and_double_share_are_amount_changing(self):
        gross,net,unit,shared = (participation_bases(fixture(m)) for m in METHODS)
        self.assertNotEqual(gross["earned"],net["earned"])
        self.assertNotEqual(shared["earned"],F(75,2))
        self.assertNotEqual(unit["earned"],shared["earned"])
        for name in METHODS[:2]:
            data=fixture(name);data["terms"]["participation_share"]="0"
            self.assertEqual(participation_bases(data)["earned"],25 if name=="gross_percent" else 20)

    def test_fractional_measures_and_exact_no_rounding(self):
        data=fixture("net_percent");set_measure(data,"receipts","1/3");set_measure(data,"deductions","1/6")
        self.assertEqual(participation_bases(data)["earned"],F(1,30))
        data["method"]="unit_rate_then_participation";set_measure(data,"usage","1/3")
        self.assertEqual(participation_bases(data)["earned"],F(1,4))
        self.assertEqual(exact_json(participation_bases(data))["quantity"],"1/3")

    def test_unit_money_and_quantity_spaces_are_independent(self):
        for name, expected, changed_quantity in [("unit_rate",150,120),("unit_rate_then_participation",75,60)]:
            data=fixture(name);set_measure(data,"deductions","45")
            result=participation_bases(data)
            self.assertEqual((result["net"],result["quantity"],result["earned"]),(80,100,expected))
            data=fixture(name);set_measure(data,"usage","80")
            result=participation_bases(data)
            self.assertEqual((result["net"],result["quantity"],result["earned"]),(100,80,changed_quantity))

    def test_known_empty_and_explicit_zero_populations(self):
        for name in METHODS:
            data=fixture(name)
            for kind in ("receipts","deductions","usage"):
                set_measure(data,kind,"0")
            self.assertEqual(participation_bases(data)["earned"],0)
            for kind in ("receipts","deductions","usage"):
                data[kind]=[]
            for pop in data["populations"]:pop["row_ids"]=[]
            self.assertEqual(participation_bases(data)["earned"],0)

    def test_genuine_zero_rate_and_participation_one(self):
        for name in METHODS:
            data=fixture(name);data["terms"].update(percentage="0",unit_rate="0",participation_share="0")
            self.assertEqual(participation_bases(data)["earned"],0)
        data=fixture("unit_rate_then_participation");data["terms"]["participation_share"]="1"
        self.assertEqual(participation_bases(data)["earned"],150)
        data["terms"]["participation_share"]="0"
        self.assertEqual(participation_bases(data)["earned"],0)

    def test_row_split_and_permutation_preserve_financial_amounts(self):
        for name in METHODS:
            data=fixture(name);before=participation_bases(data)
            a=deepcopy(data["receipts"][0]);a.update(id="receipt-2",original_ref="receipt-original-2",amount="100")
            data["receipts"][0]["amount"]="25";data["receipts"].append(a)
            data["populations"][0]["row_ids"].append("receipt-2")
            self.assertEqual(participation_bases(data),before)
            data["receipts"].reverse();data["populations"].reverse()
            self.assertEqual(participation_bases(data),before)

    def test_equal_contributors_remain_distinct_not_collapsed(self):
        data=fixture("gross_percent");a=deepcopy(data["receipts"][0]);a.update(id="r2",original_ref="o2")
        data["receipts"].append(a);data["populations"][0].update(row_ids=["receipt-1","r2"],reported_total="250")
        self.assertEqual(participation_bases(data)["earned"],50)
        a["id"]="receipt-1";self.reject(data,"BASE_ORIGINAL_REUSE")

    def test_complete_population_is_not_inferred_from_rows(self):
        for kind in ("receipts","deductions","usage"):
            for field,value,code in [("complete",False,"BASE_POPULATION_AUTHORITY"),("row_ids",[],"BASE_POPULATION_RECONCILIATION"),("reported_total","0","BASE_POPULATION_RECONCILIATION")]:
                data=fixture();pop=next(x for x in data["populations"]if x["kind"]==kind);pop[field]=value
                self.reject(data,code)
        data=fixture();data["populations"].pop();self.reject(data,"BASE_POPULATIONS")

    def test_unused_originals_are_still_validated(self):
        data=fixture("unit_rate");data["deductions"][0]["scope"]["pool_id"]="other"
        self.reject(data,"BASE_ROW_SCOPE")
        data=fixture("gross_percent");data["usage"][0]["amount"]="-1"
        self.reject(data,"BASE_NONNEGATIVE")

    def test_scope_currency_and_unit_near_misses(self):
        for field in fixture()["scope"]:
            data=fixture();data["terms"]["scope"][field]="other";self.reject(data,"BASE_TERMS_AUTHORITY")
        for currency in ("EUR","usd"):
            data=fixture();data["scope"]["currency"]=currency;self.reject(data,"BASE_CURRENCY")
        data=fixture();data["terms"]["unit"]="UsageMinute";self.reject(data,"BASE_UNIT")

    def test_half_open_period_and_authority_coverage(self):
        data=fixture();data["receipts"][0]["effective_date"]="2026-02-01";self.reject(data,"BASE_ROW_PERIOD")
        data=fixture();data["terms"]["effective"]["end"]="2026-01-31";self.reject(data,"BASE_TERMS_PERIOD")
        data=fixture();data["terms"]["approved"]=False;self.reject(data,"BASE_TERMS_AUTHORITY")

    def test_exact_cutoff_and_complete_population_observation(self):
        data=fixture();data["terms"]["observed_at"]=data["cutoff"];self.reject(data,"BASE_TERMS_CUTOFF")
        data=fixture();data["populations"][0]["observed_at"]=data["cutoff"];self.reject(data,"BASE_POPULATION_CUTOFF")
        data=fixture();data["populations"][0]["observed_at"]="2026-01-31T23:59:59Z";self.reject(data,"BASE_POPULATION_CUTOFF")
        data=fixture();data["populations"][0]["observed_at"]="2026-02-01T00:00:00Z"
        self.assertEqual(participation_bases(data)["earned"],25)

    def test_terms_and_economic_observation_order(self):
        data=fixture();data["terms"]["observed_at"]="2026-01-11T00:00:01Z";self.reject(data,"BASE_TERMS_NOT_KNOWN")
        for value in ("2026-01-09T23:59:59Z","2026-02-02T00:00:01Z"):
            data=fixture();data["receipts"][0]["observed_at"]=value;self.reject(data,"BASE_ROW_OBSERVATION")

    def test_aliases_negative_originals_and_net_loss_reject(self):
        data=fixture();data["deductions"][0]["original_ref"]=data["receipts"][0]["original_ref"];self.reject(data,"BASE_ORIGINAL_REUSE")
        for kind in ("receipts","deductions","usage"):
            data=fixture();set_measure(data,kind,"-1");self.reject(data,"BASE_NONNEGATIVE")
        data=fixture("net_percent");set_measure(data,"deductions","126");self.reject(data,"BASE_NET_LOSS_VARIANT_REQUIRED")

    def test_rate_ranges_and_strict_exact_representation(self):
        for field,value in [("percentage","-1/10"),("percentage","1.01"),("unit_rate","-1"),("participation_share","1.01")]:
            data=fixture();data["terms"][field]=value;self.reject(data,"BASE_RATE_RANGE")
        for value in (0.2,True,"NaN","1e3","1/0"," 1","1 "):
            data=fixture();data["terms"]["percentage"]=value;self.reject(data,"BASE_EXACT")

    def test_exact_fractional_timestamp_offsets_and_no_rounding(self):
        expected=participation_bases(fixture())
        for value in ("2026-01-11T00:00:00.000000001Z","2026-01-11T01:00:00+01:00","2026-01-10T23:00:00-01:00"):
            data=fixture();data["receipts"][0]["observed_at"]=value
            self.assertEqual(participation_bases(data),expected)
        data=fixture();data["populations"][0]["observed_at"]="2026-02-02T23:59:59.999999999Z"
        self.assertEqual(participation_bases(data)["earned"],25)
        data["populations"][0]["observed_at"]="2026-02-03T00:00:00.000000001Z"
        self.reject(data,"BASE_POPULATION_CUTOFF")

    def test_invalid_timestamps_reject_without_silent_repair(self):
        for value in ("2026-02-30T00:00:00Z","2026-01-11T24:00:00Z","2026-01-11T00:00:60Z","2026-01-11T00:00:00+24:00"):
            data=fixture();data["receipts"][0]["observed_at"]=value;self.reject(data,"BASE_INSTANT")

    def test_lowercase_timestamp_markers_preserve_known_instants(self):
        data=fixture();expected=participation_bases(data)
        data["cutoff"]=data["cutoff"].lower()
        for holder in [data["terms"],*data["populations"],*data["receipts"],*data["deductions"],*data["usage"]]:
            holder["observed_at"]=holder["observed_at"].lower()
        before=deepcopy(data)
        self.assertEqual(participation_bases(data),expected)
        self.assertEqual(data,before)

    def test_negative_zero_offset_keeps_known_UTC_and_original_label(self):
        data=fixture();expected=participation_bases(data)
        data["cutoff"]=data["cutoff"][:-1]+"-00:00"
        for holder in [data["terms"],*data["populations"],*data["receipts"],*data["deductions"],*data["usage"]]:
            holder["observed_at"]=holder["observed_at"][:-1]+"-00:00"
        before=deepcopy(data)
        self.assertEqual(participation_bases(data),expected)
        self.assertEqual(data,before)
        data["terms"]["observed_at"]="2025-12-01T00:00:00"
        self.reject(data,"BASE_INSTANT")

    def test_normalized_UTC_must_stay_in_Gregorian_year_domain(self):
        data=json.loads(json.dumps(fixture()).replace("2025-","0001-").replace("2026-","0001-").replace("2027-","0002-"))
        data["terms"]["observed_at"]="0001-01-01T00:00:00Z"
        self.assertEqual(participation_bases(data)["earned"],25)
        data["terms"]["observed_at"]="0001-01-01T00:00:00+23:59"
        self.reject(data,"BASE_INSTANT")
        data=fixture();data["cutoff"]="9999-12-31T23:59:59.999999999Z"
        self.assertEqual(participation_bases(data)["earned"],25)
        data["cutoff"]="9999-12-31T23:59:59-00:01"
        self.reject(data,"BASE_INSTANT")

    def test_original_bound_32_and_33(self):
        data=fixture()
        rows=[]
        for i in range(32):
            row=deepcopy(data["receipts"][0]);row.update(id=f"receipt-{i}",original_ref=f"original-{i}",amount="1")
            rows.append(row)
        data["receipts"]=rows;data["populations"][0].update(row_ids=[r["id"]for r in rows],reported_total="32")
        self.assertEqual(participation_bases(data)["earned"],F(32,5))
        extra=deepcopy(rows[0]);extra.update(id="receipt-33",original_ref="original-33");rows.append(extra)
        data["populations"][0].update(row_ids=[r["id"]for r in rows],reported_total="33")
        self.reject(data,"BASE_ROW_BOUND")

    def test_exact_unicode_scope_and_physical_order(self):
        data=fixture();identity="e\u0301-电影-\U0001f3ac"
        for holder in [data,data["terms"],*data["populations"],*data["receipts"],*data["deductions"],*data["usage"]]:
            holder["scope"]["participant_id"]=identity
        result=participation_bases(data);self.assertEqual(result["scope"]["participant_id"],identity)
        data["terms"]["scope"]["participant_id"]="é-电影-\U0001f3ac";self.reject(data,"BASE_TERMS_AUTHORITY")

    def test_malformed_methods_and_population_tags_are_controlled(self):
        for value in ([],{},1,"gross"):
            data=fixture();data["method"]=value;self.reject(data,"BASE_METHOD")
        data=fixture();data["populations"][0]["kind"]=[];self.reject(data,"BASE_POPULATIONS")

    def test_no_mutation_and_no_implementation_import(self):
        data=fixture();before=deepcopy(data);result=participation_bases(data)
        self.assertEqual(data,before);result["scope"]["pool_id"]="changed";self.assertEqual(data,before)
        tree=ast.parse((ROOT/"oracles/participation_bases.py").read_text(encoding="utf-8"))
        imports={n.module.split('.')[0]for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)}
        imports|={x.name.split('.')[0]for n in ast.walk(tree)if isinstance(n,ast.Import)for x in n.names}
        self.assertEqual(imports,{"copy","datetime","fractions","re"})


if __name__=="__main__":unittest.main()
