"""Small authored synthetic input builders; never computes expected results."""
from __future__ import annotations

from .codecs import digest, money


SV_RULES = ["SV-8-CASH", "SV-8-COST-SCHEDULE", "SV-8-FEE", "SV-8-BASIS", "SV-8-SHARE", "SV-7-POOL-RECOVERY"]
LG_RULES = ["LG-OUTSIDE-HURDLE", "LG-GATE-HISTORY", "LG-TRUE-CASH", "LG-TRUE-CASH-COST",
            "LG-GROSS-VIDEO-PROXY", "LG-GROSS-BRANCH", "LG-NET-BRANCH", "LG-GREATER-OF", "SYNTHETIC-PAYMENT-HOLDBACK"]


def base_package(profile, agreement="sv", participant="skouras", pool="pool-1", assets=None,
                 start="2026-01-01", end="2026-04-01", scenario="SV-01"):
    assets = assets or ["picture-a", "picture-b"]
    period = {"start": start, "end": end}
    policy = {"agreement_id": agreement, "participant_id": participant, "pool_id": pool, "period": period}
    scope = {"agreement_id": agreement, "pool_id": pool}
    rules = LG_RULES if profile == "lg-cleared-v1" else SV_RULES
    decisions = [{"decision_id": rule, "clause_ref": "synthetic-selected-provision",
                  "document_ref": "public-development-contract", "question": rule,
                  "evidence_label": "research_assumption", "adopted_policy": "Bounded synthetic " + scenario + ": " + rule,
                  "alternatives": ["Broader coverage requires separate policy"], "scope": scope,
                  "effective": period, "review_status": "proposed", "discriminating_case_ref": scenario}
                 for rule in rules]
    package = {"profile": profile,
            "manifest": {**{x: "unbound" for x in ["schedule_ref", "interpretation_ref", "parameter_ref", "opening_state_ref", "calendar_ref", "compiler_build", "runtime_build"]},
                         "run_id": scenario + "-run", "scenario_id": scenario,
                         "schema_version": "0.1-draft", "surface_version": "0.1-draft", "core_version": "0.1-draft",
                         "mapping_refs": [], "batch_refs": [], "reference_refs": [], "policy_refs": [], "period": period,
                         "output_currency": "USD", "mode": "final", "input_mode": "full_snapshot", "cutoff": "2026-12-31T00:00:00Z",
                         "resource_limits": {"source_scalars": 1000000, "source_tokens": 200000, "parser_depth": 128,
                                             "lean_timeout_seconds": 180, "max_facts": 100000}},
            "assets": [{"asset_id": a, "kind": "picture"} for a in assets],
            "parties": [{"party_id": participant, "name": "Synthetic participant"}, {"party_id": "distributor", "name": "Synthetic distributor"}],
            "roles": [{"role_id": "participant-role", "party_id": participant, "agreement_id": agreement, "role": "participant", "effective": period},
                      {"role_id": "distributor-role", "party_id": "distributor", "agreement_id": agreement, "role": "distributor", "effective": period}],
            "agreements": [{"agreement_id": agreement, "version": "synthetic-v1", "document_refs": ["public-development-contract"],
                            "interpretation_ref": "synthetic-interpretation@1", "effective": period, "asset_ids": assets,
                            "role_ids": ["participant-role", "distributor-role"], "calendar_ref": "calendar-quarter@1"}],
            "interpretations": [{"interpretation_id": "synthetic-interpretation", "version": "1", "decisions": decisions}],
            "incorporated_policies": [],
            "mappings": [{"mapping_version": "1", "mapping_id": "member-" + a, "kind": "pool_membership",
                          "source_namespace": "synthetic", "source_code": a, "target_ref": a, "effective": period,
                          "purpose": "participation_prepayment", "pool_id": pool, "authority_ref": rules[-1]} for a in assets],
            "source_batches": [], "financial_facts": [], "allocations": [], "evidence_events": [], "state_cells": [], "opening_aliases": [],
            "references": [{"reference_id": "calendar-quarter@1", "kind": "calendar", "description": "Explicit Gregorian half-open period"},
                           {"reference_id": "synthetic-approved-opening", "kind": "source", "description": "Explicit synthetic opening snapshot; no historical ledger claim"},
                           {"reference_id": "public-development-contract", "kind": "source", "description": "Selected public provision; synthetic inputs and unapproved wider policies"},
                           {"reference_id": "fixture-observation@1", "kind": "synthetic_observation_policy", "description": "Synthetic supplied observation instants; not historical capture dates"}],
            "parameters": {"policy": policy, "cost_date_basis": "incurred_date", "cost_decisions": []},
            "adapter": {"adapter_id": "authored-fixture", "version": "1", "observation_policy_ref": "fixture-observation@1",
                        "source_fixture": scenario, "source_digest": digest({"scenario": scenario, "profile": profile})}}
    # JSON fixtures do not share mutable dictionaries between manifest, policy
    # and decision dates; keep the programmatic authoring helper equally clear.
    import json
    return json.loads(json.dumps(package))


def add_state(p, name, alias, kind, quantity, asset_ids=None):
    policy = p["parameters"]["policy"]
    key = "/".join([policy["agreement_id"], policy["participant_id"], kind, policy["pool_id"], name, "USD"])
    scope = {"agreement_id": policy["agreement_id"], "pool_id": policy["pool_id"]}
    if asset_ids:
        scope["asset_ids"] = asset_ids
    p["state_cells"].append({"state_key": key, "balance_kind": kind, "agreement_id": policy["agreement_id"],
                             "scope": scope, "boundary": policy["period"]["start"], "unit": "USD", "quantity": str(quantity),
                             "provenance_ref": "synthetic-approved-opening", "policy_lineage": [p["interpretations"][0]["decisions"][-1]["decision_id"]],
                             "participant_id": policy["participant_id"], "pool_id": policy["pool_id"], "scenario_id": p["manifest"]["scenario_id"]})
    p["opening_aliases"].append({"alias": alias, "state_key": key})


def authored_batch(p):
    p["source_batches"].append({"source_system": "synthetic", "batch_id": "authored", "version": "1",
                                "snapshot_locator": "authored-fixture", "sha256": digest(p["financial_facts"]),
                                "format": "json", "adapter_version": "1", "ingested_at": "2026-04-03T00:00:00Z",
                                "row_count": len(p["financial_facts"]), "control_totals": []})


def add_fact(p, fact_id, asset_id, value, kind, date_kind, when, **kwargs):
    p["financial_facts"].append({"fact_id": fact_id, "batch_ref": {"source_system": "synthetic", "batch_id": "authored", "version": "1"},
                                 "source_row": fact_id, "event_kind": kind, "amount": money(value), "asset_id": asset_id,
                                 "temporal_basis": {"kind": date_kind, "date": when}, "dates": {date_kind: when}, **kwargs})


def sv_package(opening="15000", cash_a="100000", cash_b="60000", cost_a="10000", cost_b="5500", **kwargs):
    p = base_package("sv-incurred-v1", **kwargs)
    period, policy = p["manifest"]["period"], p["parameters"]["policy"]
    a, b = p["agreements"][0]["asset_ids"]
    when = period["start"]
    add_fact(p, "receipt-a", a, cash_a, "cash_receipt", "cash_received_date", when)
    add_fact(p, "receipt-b", b, cash_b, "cash_receipt", "cash_received_date", when)
    add_fact(p, "cost-a", a, cost_a, "incurred_cost", "incurred_date", when)
    add_fact(p, "cost-b", b, cost_b, "incurred_cost", "incurred_date", when)
    p["parameters"]["cost_decisions"] = [
        {"fact_id": "cost-a", "decision_id": "SV-8-COST-SCHEDULE", "eligible": True, "branch": "unfunded", "reason": "Synthetic approved A cost"},
        {"fact_id": "cost-b", "decision_id": "SV-8-COST-SCHEDULE", "eligible": True, "branch": "funded", "reason": "Synthetic approved B cost"}]
    p["parameters"]["funding_snapshot"] = {"complete": True, "as_of": when, "covered_assets": [a, b],
                                                "covered_parties": [policy["participant_id"], "distributor"], "evidence_ref": "fixture-observation@1"}
    for event, asset, party, value in [("fund-a", a, "distributor", "50000"), ("fund-b-part", b, policy["participant_id"], "40000"), ("fund-b-dist", b, "distributor", "60000")]:
        p["evidence_events"].append({"event_id": event, "kind": "funding", "subject_ref": asset, "effective_date": when,
                                     "observed_at": "2026-01-01T00:00:00Z", "evidence_ref": "fixture-observation@1",
                                     "approval_ref": "SV-8-SHARE", "amount": money(value), "asset_id": asset, "party_id": party})
    add_state(p, "main", "sv/participant-prepayment/main-pool", "participation_prepayment", opening)
    authored_batch(p)
    return p


def lg_package(subtotal="175", hurdle_date="2025-12-31"):
    p = base_package("lg-cleared-v1", agreement="lg", participant="seller-group", pool="crossed-group", assets=["work-D"], scenario="LG-01")
    policy = p["parameters"]["policy"]
    policy.update(asset_id="work-D", video_proxy="0.25", gross_rate="0.20", net_rate="0.20")
    for key, value in [("producer_fee_offset", "12"), ("payment_holdback_addition", "0"), ("payment_holdback_release", "0")]:
        p["parameters"][key] = money(value)
    add_fact(p, "lg-other", "work-D", "180", "cash_receipt", "cash_received_date", "2026-02-01", channel="other")
    add_fact(p, "lg-video", "work-D", "120", "cash_receipt", "cash_received_date", "2026-03-01", channel="home_video")
    for name, alias, kind, value in [("gross", "lg/work-D/true-cash/cumulative-gross", "cumulative_gross", "100"),
                                    ("cost", "lg/work-D/true-cash/cumulative-cost", "cumulative_cost", "100"),
                                    ("hold", "synthetic/work-D/payment-holdback", "synthetic_payment_holdback", "0")]:
        add_state(p, name, alias, kind, value, ["work-D"])
    common = {"observed_at": "2026-01-01T00:00:00Z", "evidence_ref": "fixture-observation@1", "agreement_id": "lg"}
    p["evidence_events"] = [
        {**common, "event_id": "outside-hurdle", "kind": "hurdle_attestation", "subject_ref": "lg", "effective_date": hurdle_date,
         "approval_ref": "LG-OUTSIDE-HURDLE", "satisfied": True},
        {**common, "event_id": "work-history", "kind": "gate_history", "subject_ref": "work-D", "effective_date": "2026-01-01",
         "approval_ref": "LG-GATE-HISTORY", "asset_id": "work-D", "period": policy["period"], "satisfied": True},
        {**common, "event_id": "net-worksheet", "kind": "crossed_net_worksheet", "subject_ref": "crossed-group", "effective_date": "2026-01-01",
         "approval_ref": "LG-NET-BRANCH", "pool_id": "crossed-group", "member_ids": ["work-D"], "period": policy["period"], "amount": money(subtotal)}]
    authored_batch(p)
    return p
