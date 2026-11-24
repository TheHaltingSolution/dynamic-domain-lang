"""Finite RR-03 development workloads from original SV records, not bindings.

Only standard-library construction is used. This module supplies explicit
synthetic facts/authorities and physical controls; it does not solve settlement.
The 5% lineage bracket is represented by actual invoice financial facts linked
from cash receipts. Invoice face values are a separate amount space.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "cases/sv/neutral-oracle.json"


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def exact_number(value):
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _money(value):
    return {"currency": "USD", "value": exact_number(value)}


def generate_mixed(records=100, *, pictures=None, seed=20261123):
    if type(records) is not int or records not in {100, 1000, 10000}:
        raise ValueError("Mixed cohorts are exactly 100, 1000 or 10000 original records")
    expected_pictures = {100: 2, 1000: 8, 10000: 40}[records]
    pictures = expected_pictures if pictures is None else pictures
    if type(pictures) is not int or pictures != expected_pictures or type(seed) is not int:
        raise ValueError("Mixed 100/1000/10000 cohorts require 2/8/40 pictures and an integer seed")
    neutral = json.loads(FIXTURE.read_text(encoding="utf-8"))
    package = neutral["package"]
    period = package["manifest"]["period"]
    scenario = f"RR03-MIXED-{records}-{seed}"
    package["manifest"].update(scenario_id=scenario, run_id=scenario + "-run", cutoff="2026-04-03T00:00:00Z")
    for name in ("schedule_ref", "interpretation_ref", "parameter_ref", "opening_state_ref", "calendar_ref", "compiler_build", "runtime_build"):
        package["manifest"][name] = "unbound"
    for name in ("mapping_refs", "batch_refs", "reference_refs", "policy_refs"):
        package["manifest"][name] = []
    assets = [f"mixed-picture-{index:04d}" for index in range(pictures)]
    package["assets"] = [{"asset_id": asset, "kind": "picture"} for asset in assets] + [{"asset_id": "mixed-bundle", "kind": "bundle"}]
    package["agreements"][0]["asset_ids"] = assets
    prototype = package["mappings"][0]
    package["mappings"] = [{**deepcopy(prototype), "mapping_id": "member-" + asset,
                            "source_code": asset, "target_ref": asset} for asset in assets]
    policy = package["parameters"]["policy"]
    participant = policy["participant_id"]
    package["parameters"]["funding_snapshot"].update(complete=True, as_of=period["start"], covered_assets=assets,
                                                    covered_parties=[participant, "distributor"])
    for state in package["state_cells"]:
        state.update(scenario_id=scenario, quantity="250")
    decisions = package["interpretations"][0]["decisions"]
    for decision in decisions:
        decision["discriminating_case_ref"] = scenario
    cash_decision = next(d for d in decisions if d["decision_id"] == "SV-8-CASH")
    cost_decision = next(d for d in decisions if d["decision_id"] == "SV-8-COST-SCHEDULE")
    receipt_count, cost_count, event_count, lineage_count = records * 60 // 100, records * 30 // 100, records // 20, records // 20
    allocated_parent_count = receipt_count // 10
    split_weights = ["0.1", "0.2", "0.3", "0.4"] if records == 10000 else ["0.4", "0.6"]
    batch_ref = {"source_system": "mixed-synthetic", "batch_id": "authored", "version": "1"}

    def fact(identity, kind, asset, amount, day, date_kind, **extra):
        return {"fact_id": identity, "batch_ref": deepcopy(batch_ref), "source_row": identity,
                "event_kind": kind, "asset_id": asset, "amount": _money(amount),
                "temporal_basis": {"kind": date_kind, "date": day}, "dates": {date_kind: day}, **extra}

    facts, allocations, authorities = [], [], []
    for index in range(receipt_count):
        identity = f"mixed-cash-{index:06d}"
        split = index < allocated_parent_count
        extra = {"external_event_ref": f"mixed-bank-event-{index:06d}"}
        if index < lineage_count:
            parent = f"mixed-invoice-{index:06d}"
            extra["parent_fact_id"] = parent
            facts.append(fact(parent, "invoice", "mixed-bundle", 150 + index % 11, "2026-01-10", "invoice_date"))
        facts.append(fact(identity, "cash_receipt", "mixed-bundle" if split else assets[index % pictures],
                          100 + index % 7, "2026-02-15", "cash_received_date", **extra))
        if split:
            targets = [assets[(index + slot) % pictures] for slot in range(len(split_weights))]
            weights = [{"asset_id": target, "weight": weight} for target, weight in zip(targets, split_weights)]
            decision_id = f"RR03-ALLOCATION-{index:06d}"
            selection = {**deepcopy(cash_decision), "decision_id": decision_id,
                         "question": "Selected four-title original-parent allocation" if records == 10000 else "Selected two-title original-parent allocation",
                         "adopted_policy": "Synthetic separately supplied exact 0.1/0.2/0.3/0.4 allocation" if records == 10000 else "Synthetic separately supplied exact 0.4/0.6 allocation",
                         "allocation_terms": deepcopy(weights)}
            decisions.append(selection)
            authority = {"source_fact_id": identity, "allocation_group_id": f"mixed-allocation-group-{index:06d}",
                         "method": "exact_weight", "method_version": "1", "authority_ref": decision_id,
                         "policy_ref": decision_id, "scenario_id": scenario, "effective": deepcopy(period),
                         "weights": deepcopy(weights)}
            authorities.append(authority)
            for slot, target in enumerate(targets):
                allocations.append({"allocation_id": f"mixed-allocation-{index:06d}-{slot}",
                                    "allocation_group_id": authority["allocation_group_id"], "source_fact_id": identity,
                                    "method": "exact_weight", "method_version": "1", "authority_ref": decision_id,
                                    "policy_ref": decision_id, "scenario_id": scenario, "effective": deepcopy(period),
                                    "target_scope": {"agreement_id": policy["agreement_id"], "pool_id": policy["pool_id"],
                                                     "participant_id": participant, "asset_ids": [target]},
                                    "weight": split_weights[slot]})
    cost_choices = []
    for index in range(cost_count):
        identity, asset = f"mixed-cost-{index:06d}", assets[index % pictures]
        facts.append(fact(identity, "incurred_cost", asset, 1 + index % 3, "2026-02-10", "incurred_date", category="selected_distribution" if index % 5 != 4 else "unselected_publicity"))
        cost_choices.append({"fact_id": identity, "decision_id": "SV-8-COST-SCHEDULE", "eligible": index % 5 != 4,
                             "branch": "funded" if index % pictures % 2 else "unfunded",
                             "reason": "Explicit mixed synthetic eligible cost" if index % 5 != 4 else "Explicit mixed synthetic exclusion"})
    cost_decision["cost_terms"] = [{key: row[key] for key in ("fact_id", "eligible", "branch")} for row in cost_choices]
    package["parameters"]["cost_decisions"] = cost_choices
    pairs = [(asset, "distributor") for asset in assets]
    pairs += [(asset, participant) for index, asset in enumerate(assets) if index % 2]
    occurrences = Counter(pairs[index % len(pairs)] for index in range(event_count))
    events = []
    for index in range(event_count):
        asset, party = pairs[index % len(pairs)]
        total = 600 if party == "distributor" else 400
        events.append({"event_id": f"mixed-funding-{index:06d}", "kind": "funding", "subject_ref": asset,
                       "effective_date": period["start"], "observed_at": period["start"] + "T00:00:00Z",
                       "evidence_ref": "fixture-observation@1", "approval_ref": "SV-8-SHARE",
                       "amount": _money(Fraction(total, occurrences[asset, party])), "asset_id": asset, "party_id": party})
    randomizer = random.Random(seed)
    for rows in (facts, allocations, events):
        randomizer.shuffle(rows)
    package["financial_facts"], package["allocations"], package["evidence_events"] = facts, allocations, events
    totals = {kind: sum(Fraction(row["amount"]["value"]) for row in facts if row["event_kind"] == kind)
              for kind in ("cash_receipt", "incurred_cost", "invoice")}
    batch_sha = hashlib.sha256(canonical_bytes(facts)).hexdigest()
    package["source_batches"] = [{**batch_ref, "snapshot_locator": "generated-source-batch.json", "sha256": batch_sha,
                                  "format": "json", "adapter_version": "rr03-mixed/1", "ingested_at": "2026-04-03T00:00:00Z",
                                  "row_count": len(facts), "control_totals": [{"amount_kind": kind, "currency": "USD",
                                      "signed_total": exact_number(total), "absolute_total": exact_number(total)} for kind, total in totals.items()]}]
    source_records = {"financial_facts": facts, "evidence_events": events, "allocations": allocations}
    package["adapter"].update(adapter_id="rr03-original-mixed", version="1", source_fixture=scenario,
                              source_digest=hashlib.sha256(canonical_bytes(source_records)).hexdigest())
    neutral["allocation_authorities"] = authorities
    counts = {"raw_original_records": records, "receipt_parents": receipt_count, "cost_facts": cost_count,
              "funding_evidence_events": event_count, "invoice_lineage_facts": lineage_count,
              "financial_facts": len(facts), "canonical_guard_objects": len(facts) + len(events),
              "source_batch_rows": len(facts), "allocation_parent_groups": allocated_parent_count,
              "allocation_rows": len(allocations), "independent_allocation_authorities": len(authorities),
              "projected_receipt_cardinality": receipt_count + allocated_parent_count * (len(split_weights) - 1),
              "projected_eligible_cost_cardinality": sum(row["eligible"] for row in cost_choices),
              "explicitly_excluded_costs": sum(not row["eligible"] for row in cost_choices),
              "picture_metadata": pictures, "bundle_metadata": 1, "pool_membership_mappings": len(package["mappings"]),
              "interpretation_decisions": len(decisions)}
    return {"format": "spl-mixed-original-records/1", "seed": seed, "counts": counts, "neutral": neutral,
            "source_records": source_records, "amount_space_controls": {key: exact_number(value) for key, value in totals.items()},
            "count_scope": "60/30/5/5 cash parents/incurred costs/funding events/invoice lineage facts; allocations and authority/metadata rows reported separately",
            "limitations": ["Synthetic development mix, not a measured industry distribution.",
                            "Lineage bracket is invoice financial facts with actual parent_fact_id links; invoice face is never cash.",
                            "Financial facts are supplied full-snapshot records without invented observation timestamps.",
                            "Single pool, one calendar quarter, complete opening funding snapshot; no distributed capacity claim."]}
