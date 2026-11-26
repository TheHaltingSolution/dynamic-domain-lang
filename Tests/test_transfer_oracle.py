"""Independent coordinator controls for scoped, conserved entitlement transfers."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.contract_transfers import TransferOracleError, contract_transfers, exact_json


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/transfers/neutral.json").read_text(encoding="utf-8"))


def add_account(data, identity):
    scope = {"agreement_id": "agreement-" + identity, "participant_id": "participant-" + identity,
             "pool_id": "pool-" + identity, "currency": "USD"}
    data["accounts"].append({"id": identity, "scope": scope, "source_ref": "synthetic-account-" + identity, "evidence_ref": "scope-authority"})
    data["opening_state"]["account_scopes"].append({"id": identity, "scope": deepcopy(scope)})
    for row in data["evidence"]:
        if row["id"] in ("scope-authority", "transfer-authority"):
            row["account_ids"].append(identity)


def add_edge(data, identity, source, target, amount="20", sequence=2):
    scopes = {row["id"]: row["scope"] for row in data["accounts"]}
    auth = deepcopy(fixture()["authorizations"][0])
    auth.update(id="auth-" + identity, source_account=source, target_account=target, source_scope=deepcopy(scopes[source]),
                target_scope=deepcopy(scopes[target]), sequence=sequence, maximum_amount=amount,
                effective=deepcopy(data["period"]), source_ref="synthetic-authorization-" + identity)
    transfer = deepcopy(fixture()["transfers"][0])
    transfer.update(id="transfer-" + identity, authorization_id=auth["id"], source_account=source, target_account=target,
                    source_scope=deepcopy(scopes[source]), target_scope=deepcopy(scopes[target]), amount=amount,
                    source_ref="synthetic-transaction-" + identity)
    data["authorizations"].append(auth)
    data["transfers"].append(transfer)


def successor(previous, new_entitlement=None, new_transfer=None):
    data = fixture()
    data.update(case_id="transfers-q2", period={"start": "2026-04-01", "end": "2026-07-01"},
                as_of="2026-06-20", cutoff="2026-07-03T00:00:00Z")
    data["opening_state"] = exact_json(previous["closing_state"])
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
    for row in data["evidence"]:
        row["observed_at"] = "2026-06-21T00:00:00Z"
    if new_entitlement is None:
        data["entitlements"] = []
    else:
        data["entitlements"][0].update(id="entitlement-source-q2", amount=new_entitlement, effective_date="2026-06-01",
                                       observed_at="2026-06-21T00:00:00Z", source_ref="synthetic-source-entitlement-q2",
                                       upstream_result_ref="synthetic:source-entitlement-period-2#line-source")
    if new_transfer is None:
        data["authorizations"], data["transfers"] = [], []
    else:
        data["authorizations"][0].update(id="authorization-q2", effective=deepcopy(data["period"]), maximum_amount=new_transfer,
                                        approved_date="2026-06-19", recorded_date="2026-06-20", observed_at="2026-06-21T00:00:00Z")
        data["transfers"][0].update(id="transfer-q2", authorization_id="authorization-q2", amount=new_transfer,
                                   recognition_date="2026-06-25", observed_at="2026-06-26T00:00:00Z")
    return data


class TransferOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(TransferOracleError) as raised:
            contract_transfers(data)
        self.assertEqual(str(raised.exception), code)

    def test_baseline_real_scopes_70_30_without_new_cash(self):
        result = contract_transfers(fixture())
        self.assertEqual([row["final_entitlement"] for row in result["accounts"]], [70, 30])
        self.assertEqual([row["original_entitlement"] for row in result["accounts"]], [100, 0])
        self.assertEqual([row["scope"]["agreement_id"] for row in result["accounts"]], ["agreement-source", "agreement-target"])
        self.assertEqual((result["original_entitlement_total"], result["final_entitlement_total"], result["transferred_total"], result["external_cash_added"]), (100, 100, 30, 0))
        line = result["transfers"][0]
        self.assertEqual((line["source_before"], line["source_after"], line["target_before"], line["target_after"]), (100, 70, 0, 30))
        self.assertEqual(result["closing_state"]["last_period"][0]["entitlement_facts"][0]["upstream_result_ref"],
                         "synthetic:source-entitlement-period-1#line-source")
        self.assertNotIn("actual_paid", result)
        self.assertNotIn("payable", result)

    def test_incoming_credit_funds_downstream_in_topological_order(self):
        data = fixture(); add_account(data, "third"); add_edge(data, "downstream", "target", "third", sequence=0)
        result = contract_transfers(data)
        self.assertEqual(result["topological_accounts"], ["source", "target", "third"])
        self.assertEqual([row["final_entitlement"] for row in result["accounts"]], [70, 10, 20])
        self.assertEqual([row["sequence"] for row in result["transfers"]], [1, 0])
        downstream = result["transfers"][1]
        self.assertEqual((downstream["source_before"], downstream["source_after"]), (30, 10))
        self.assertEqual(result["transferred_total"], 50)
        self.assertEqual(result["original_entitlement_total"], result["final_entitlement_total"])
        self.assertEqual(result["external_cash_added"], 0)

    def test_outgoing_authorized_sequence_controls_intermediates(self):
        data = fixture(); add_account(data, "third"); add_edge(data, "second-outgoing", "source", "third", amount="60", sequence=2)
        first = contract_transfers(data)
        self.assertEqual([(row["id"], row["source_before"], row["source_after"]) for row in first["transfers"]],
                         [("transfer-q1", 100, 70), ("transfer-second-outgoing", 70, 10)])
        data["authorizations"][1]["sequence"] = 0
        second = contract_transfers(data)
        self.assertEqual([(row["id"], row["source_before"], row["source_after"]) for row in second["transfers"]],
                         [("transfer-second-outgoing", 100, 40), ("transfer-q1", 40, 10)])
        self.assertEqual(first["accounts"], second["accounts"])

    def test_graph_cycle_self_edge_unknown_and_scope_fail(self):
        data = fixture(); add_account(data, "third"); add_edge(data, "two", "target", "third", sequence=2); add_edge(data, "cycle", "third", "source", amount="1", sequence=3)
        self.reject(data, "TRANSFER_GRAPH_CYCLE")
        data = fixture(); data["authorizations"][0]["target_account"] = "source"
        self.reject(data, "TRANSFER_SELF_EDGE")
        data = fixture(); data["authorizations"][0]["target_account"] = "missing"
        self.reject(data, "TRANSFER_UNKNOWN_ACCOUNT")
        data = fixture(); data["authorizations"][0]["target_scope"]["pool_id"] = "outside"
        self.reject(data, "TRANSFER_ENDPOINT_SCOPE")
        data = fixture(); data["accounts"][1]["scope"] = deepcopy(data["accounts"][0]["scope"])
        self.reject(data, "TRANSFER_DUPLICATE_ECONOMIC_ACCOUNT")

    def test_same_agreement_and_currency_are_not_hidden_as_crossing(self):
        data = fixture()
        for scope in (data["accounts"][1]["scope"], data["opening_state"]["account_scopes"][1]["scope"],
                      data["authorizations"][0]["target_scope"], data["transfers"][0]["target_scope"]):
            scope["agreement_id"] = "agreement-source"
        self.reject(data, "TRANSFER_CROSS_AGREEMENT_REQUIRED")
        data = fixture(); data["accounts"][1]["scope"]["currency"] = "EUR"
        self.reject(data, "TRANSFER_CURRENCY")

    def test_overdraw_and_authorized_amount_limits_block_atomically(self):
        data = fixture(); data["transfers"][0]["amount"] = "31"
        self.reject(data, "TRANSFER_AUTHORIZED_AMOUNT")
        data = fixture(); data["transfers"][0]["amount"] = "101"; data["authorizations"][0]["maximum_amount"] = "101"
        self.reject(data, "TRANSFER_SOURCE_OVERDRAW")
        data = fixture(); add_account(data, "third"); add_edge(data, "too-much", "source", "third", amount="80", sequence=2)
        before = deepcopy(data)
        self.reject(data, "TRANSFER_SOURCE_OVERDRAW")
        self.assertEqual(data, before)
        data = fixture(); data["transfers"][0]["amount"] = "0"
        self.reject(data, "TRANSFER_AUTHORIZED_AMOUNT")

    def test_asof_equality_and_unused_invalid_authorizations_are_checked(self):
        data = fixture(); data["authorizations"][0]["approved_date"] = "2026-03-20"
        self.assertEqual(contract_transfers(data)["transferred_total"], 30)
        data["as_of"] = "2026-03-19"
        self.reject(data, "TRANSFER_AUTHORIZATION_ASOF")
        data = fixture(); data["transfers"] = []; data["authorizations"][0]["approved"] = False
        self.reject(data, "TRANSFER_AUTHORIZATION_ASOF")
        data = fixture(); data["authorizations"][0]["effective"]["end"] = "2026-03-31"
        self.reject(data, "TRANSFER_AUTHORIZATION_PERIOD")
        data = fixture(); data["authorizations"][0]["approved_date"] = "2026-03-21"
        self.reject(data, "TRANSFER_AUTHORIZATION_ASOF")

    def test_duplicate_ids_authority_reuse_and_sequence_ties(self):
        for field in ("accounts", "entitlements", "authorizations", "transfers", "evidence"):
            data = fixture(); data[field].append(deepcopy(data[field][0]))
            self.reject(data, "TRANSFER_DUPLICATE_ID")
        data = fixture(); data["transfers"].append({**deepcopy(data["transfers"][0]), "id": "other-transaction"})
        self.reject(data, "TRANSFER_AUTHORIZATION_REFERENCE_OR_REUSE")
        data = fixture(); add_account(data, "third"); add_edge(data, "sequence-tie", "source", "third", sequence=1)
        self.reject(data, "TRANSFER_AUTHORIZED_SEQUENCE")
        data = fixture(); data["authorizations"][0]["sequence"] = True
        self.reject(data, "TRANSFER_AUTHORIZED_SEQUENCE")

    def test_upstream_line_alias_and_source_view_cannot_duplicate_entitlement(self):
        data = fixture()
        alias = deepcopy(data["entitlements"][0]); alias.update(id="aliased-id", source_ref="aliased-source")
        data["entitlements"].append(alias)
        self.reject(data, "TRANSFER_UPSTREAM_ALREADY_CONSUMED")
        data = fixture(); alias = deepcopy(data["entitlements"][0]); alias.update(id="aliased-id", upstream_result_ref="artifact#different-line")
        data["entitlements"].append(alias)
        self.reject(data, "TRANSFER_DUPLICATE_SOURCE_VIEW")
        data = fixture(); data["entitlements"][0]["upstream_result_ref"] = "whole-artifact-only"
        self.reject(data, "TRANSFER_UPSTREAM_LINE_REFERENCE")
        data = fixture(); alias = deepcopy(data["entitlements"][0]); alias.update(id="other-line", source_ref="other-source", amount="20", upstream_result_ref="synthetic:source-entitlement-period-1#line-other")
        data["entitlements"].append(alias)
        self.assertEqual(contract_transfers(data)["original_entitlement_total"], 120)

    def test_serialized_next_period_has_fresh_funds_not_previous_70_30(self):
        first_data = fixture(); first = contract_transfers(first_data)
        empty = contract_transfers(successor(first))
        self.assertEqual([row["original_entitlement"] for row in empty["accounts"]], [0, 0])
        self.assertEqual([row["final_entitlement"] for row in empty["accounts"]], [0, 0])
        second_data = successor(first, new_entitlement="30", new_transfer="10")
        second = contract_transfers(second_data)
        self.assertEqual([row["final_entitlement"] for row in second["accounts"]], [20, 10])
        self.assertEqual(second["original_entitlement_total"], 30)
        self.assertEqual(second["closing_state"]["consumed_transfer_ids"], ["transfer-q1", "transfer-q2"])
        self.assertEqual(len(second["closing_state"]["consumed_upstream_refs"]), 2)

    def test_consumed_transaction_authority_entitlement_and_upstream_replay(self):
        first = contract_transfers(fixture())
        data = successor(first, "30", "10"); data["transfers"][0]["id"] = "transfer-q1"
        self.reject(data, "TRANSFER_ALREADY_CONSUMED")
        data = successor(first, "30", "10"); data["authorizations"][0]["id"] = "authorization-q1"
        self.reject(data, "TRANSFER_AUTHORIZATION_ALREADY_CONSUMED")
        data = successor(first, "30", "10"); data["entitlements"][0]["id"] = "entitlement-source-q1"
        self.reject(data, "TRANSFER_ENTITLEMENT_ALREADY_CONSUMED")
        data = successor(first, "30", "10"); data["entitlements"][0]["upstream_result_ref"] = fixture()["entitlements"][0]["upstream_result_ref"]
        self.reject(data, "TRANSFER_UPSTREAM_ALREADY_CONSUMED")

    def test_actual_predecessor_scope_boundary_and_audit_history(self):
        original = successor(contract_transfers(fixture()), "30", "10")
        changes = [("TRANSFER_PREDECESSOR_REQUIRED", lambda d: d.pop("prior_result")),
                   ("TRANSFER_OPENING_BOUNDARY", lambda d: d["opening_state"].update(boundary="2026-04-02")),
                   ("TRANSFER_PREDECESSOR_BOUNDARY", lambda d: d["prior_result"]["period"].update(end="2026-03-31")),
                   ("TRANSFER_PREDECESSOR_MISMATCH", lambda d: d["prior_result"].update(source_case_id="other")),
                   ("TRANSFER_PREDECESSOR_MISMATCH", lambda d: d["opening_state"]["consumed_transfer_ids"].clear()),
                   ("TRANSFER_OPENING_SCOPE", lambda d: d["opening_state"]["account_scopes"][0]["scope"].update(pool_id="outside"))]
        for code, change in changes:
            data = deepcopy(original); change(data); self.reject(data, code)
        data = deepcopy(original)
        data["opening_state"]["last_period"][0]["accounts"][0]["final_entitlement"] = "71"
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        self.reject(data, "TRANSFER_PRIOR_AUDIT")

    def test_period_recognition_observation_and_evidence_scope(self):
        for day in ("2025-12-31", "2026-04-01"):
            data = fixture(); data["entitlements"][0]["effective_date"] = day
            self.reject(data, "TRANSFER_ENTITLEMENT_PERIOD")
            data = fixture(); data["transfers"][0]["recognition_date"] = day
            self.reject(data, "TRANSFER_RECOGNITION_PERIOD")
        data = fixture(); data["transfers"][0]["observed_at"] = "2026-03-20T00:00:00Z"
        self.reject(data, "TRANSFER_OBSERVATION_ORDER")
        data = fixture(); data["evidence"][-1]["account_ids"] = ["source"]
        self.reject(data, "TRANSFER_EVIDENCE_REQUIRED")
        data = fixture(); data["evidence"][-1]["coordinator_id"] = "other"
        self.reject(data, "TRANSFER_EVIDENCE_SCOPE")
        data = fixture(); data["transfers"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "TRANSFER_FACT_CUTOFF")
        data = fixture(); data["evidence"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "TRANSFER_EVIDENCE_CUTOFF")
        data = fixture(); data["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        data["transfers"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        self.assertEqual(contract_transfers(data)["transferred_total"], 30)

    def test_exact_fractional_amounts_no_implicit_rounding_and_resource_bound(self):
        data = fixture(); data["entitlements"][0]["amount"] = "1/3"; data["authorizations"][0]["maximum_amount"] = "1/7"; data["transfers"][0]["amount"] = "1/7"
        result = contract_transfers(data)
        self.assertEqual([row["final_entitlement"] for row in result["accounts"]], [Fraction(4, 21), Fraction(1, 7)])
        for value in (0.3, True, "1e2", "-1"):
            data = fixture(); data["entitlements"][0]["amount"] = value
            self.reject(data, "TRANSFER_EXACT_NONNEGATIVE_VALUE")
        data = fixture()
        for index in range(15):
            add_account(data, f"extra-{index}")
        self.reject(data, "TRANSFER_RESOURCE_BOUND")

    def test_independent_node_order_permutation_and_original_replay(self):
        data = fixture(); add_account(data, "alpha")
        original = deepcopy(data)
        result = contract_transfers(data)
        self.assertEqual(result["topological_accounts"], ["alpha", "source", "target"])
        self.assertEqual(data, original)
        for field in ("accounts", "entitlements", "authorizations", "transfers", "evidence"):
            data[field].reverse()
        self.assertEqual(contract_transfers(data), result)
        self.assertEqual(contract_transfers(original), result)
        self.assertEqual(json.loads(json.dumps(exact_json(result)))["external_cash_added"], "0")

    def test_oracle_only_imports_standard_library(self):
        tree = ast.parse((ROOT / "oracles/contract_transfers.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
