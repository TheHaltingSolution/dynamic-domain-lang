"""Versioned, deliberately bounded RQ-07 raw CSV adapter.

Raw receipts/costs/funding stay distinct; allocation and cost eligibility remain
explicit scenario decisions. No incurred dates or historical observations are
fabricated. Source hashes are verified before any rows are projected.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from .codecs import (amount, day, digest, exact, fail, file_digest, instant, instant_utc_day,
                     money, number, read_csv, read_json)
from .fixtures import add_state, base_package

HEADERS = {
    "raw_invoice_lines": "invoice_id,line_no,invoice_date,buyer_ref,item_code,market_code,billed_amount,ccy,license_event_date",
    "raw_bank_receipts": "bank_ref,value_date,payer_ref,deposit_amount,ccy",
    "raw_cash_applications": "application_ref,bank_ref,invoice_id,line_no,posted_on,applied_amount,ccy",
    "raw_cost_lines": "invoice_ref,line_no,gl_code,asset_code,invoice_date,posted_on,paid_on,amount,ccy",
    "raw_acquisition_funding": "funding_ref,asset_code,funder_ref,funded_on,amount,ccy",
}
AMOUNTS = {"raw_invoice_lines": "billed_amount", "raw_bank_receipts": "deposit_amount", "raw_cash_applications": "applied_amount", "raw_cost_lines": "amount", "raw_acquisition_funding": "amount"}


def rq07(source, *, observed_at, ingested_at):
    """Observation time MUST be supplied as a named synthetic policy input."""
    from .schema import unique
    source = Path(source)
    s = read_json(source / "scenario.json")
    if file_digest(source / "scenario.json") != "28470ae6aff0ad1e3916cdc4bf5d140d86eda794a3c5080d8ab76317de717455":
        fail("UNSUPPORTED_SOURCE_SNAPSHOT", "Adapter 1.0.0 is pinned to the delivered synthetic scenario bytes; changed scenarios need a new source profile")
    # Version 1 is an exact supported source envelope. Future changes need a new adapter.
    if set(s) != {"package_version", "fixture_id", "evidence_class", "approval", "deal", "run", "reference_data", "policy", "source_batches"}:
        fail("UNSUPPORTED_SOURCE_STRUCTURE", "Unknown or missing RQ-07 scenario fields")
    if s["package_version"] != "1.0.0" or s["fixture_id"] != "SPL-RQ07-SV-BUNDLE-01":
        fail("UNSUPPORTED_ADAPTER_VERSION", "Expected RQ-07 bundle 1.0.0")
    instant(observed_at)
    instant(ingested_at)
    approval, deal, run, refs, policy = (s[k] for k in ["approval", "deal", "run", "reference_data", "policy"])
    if approval["scope"] != "scenario_only" or approval["status"] != "approved_in_scenario":
        fail("REQUIRED_POLICY", "Scenario approval is missing")
    if set(b["batch_id"] for b in s["source_batches"]) != set(HEADERS) or len(s["source_batches"]) != 5:
        fail("SOURCE_DELIVERY", "Require all five complete raw source batches")
    rows = {}
    for b in s["source_batches"]:
        name = b["batch_id"]
        if b["snapshot_locator"] != name + ".csv":
            fail("SOURCE_LOCATOR", "Only declared local fixture filenames supported")
        path = source / b["snapshot_locator"]
        if file_digest(path) != b["sha256"]:
            fail("SOURCE_HASH_MISMATCH", name)
        rows[name] = read_csv(path, HEADERS[name].split(","))
        if len(rows[name]) != b["row_count"]:
            fail("SOURCE_ROW_COUNT", name)
        for r in rows[name]:
            if r["ccy"] != "USD" or exact(r[AMOUNTS[name]]) < 0:
                fail("SOURCE_AMOUNT", "Positive USD amount required")
    p = base_package("sv-rq07-posted-v1", agreement=deal["id"], participant=deal["participant_id"],
                     pool=policy["opening_state"]["pool_id"], assets=deal["asset_ids"],
                     start=run["period"]["start"], end=run["period"]["end"], scenario=s["fixture_id"])
    p["manifest"].update(run_id=run["id"], cutoff=run["cutoff"])
    p["adapter"] = {"adapter_id": "spl-rq07-raw", "version": "1.0.0", "observation_policy_ref": "fixture-observation@1",
                    "source_fixture": s["fixture_id"], "source_digest": file_digest(source / "scenario.json")}
    p["references"][-1]["description"] = "Explicit synthetic recorded time " + observed_at + "; applications have date precision and are available when posting_date < UTC cutoff date"
    # Rename the synthetic distributor without manufacturing party identity.
    p["parties"][1]["party_id"] = deal["distributor_id"]
    p["roles"][1]["party_id"] = deal["distributor_id"]
    p["parties"].append({"party_id": deal["buyer_id"], "name": "Synthetic license buyer"})
    p["parameters"]["cost_date_basis"] = "posting_date"
    decision = dict(p["interpretations"][0]["decisions"][0])
    decision.update(decision_id=approval["id"], clause_ref="RQ07-scenario", question="Source normalization and allocation authority",
                    adopted_policy="Bank value cash; GL-posted costs; approved 2/5:3/5 collected bundle allocation; complete funding snapshot; scenario-only authority")
    p["interpretations"][0]["decisions"].append(decision)
    p["source_batches"] = []
    for b in s["source_batches"]:
        total = sum(exact(r[AMOUNTS[b["batch_id"]]]) for r in rows[b["batch_id"]])
        p["source_batches"].append({**b, "format": "csv", "adapter_version": "1.0.0", "ingested_at": ingested_at,
                                    "control_totals": [{"amount_kind": b["batch_id"], "currency": "USD", "signed_total": number(total), "absolute_total": number(total)}]})
    aliases = refs["invoice_asset_aliases"]
    assets = set(deal["asset_ids"])

    def asset(code):
        if code not in aliases or aliases[code] not in assets:
            fail("UNMAPPED_ASSET", code)
        return aliases[code]

    for code, target in aliases.items():
        p["mappings"].append({"mapping_version": refs["mapping_version"], "mapping_id": "alias-" + code,
                              "kind": "asset_alias", "source_namespace": "synthetic-screen", "source_code": code,
                              "target_ref": target, "effective": run["period"]})
    for code, target in refs["territory_codes"].items():
        p["mappings"].append({"mapping_version": refs["mapping_version"], "mapping_id": "territory-" + code,
                              "kind": "territory", "source_namespace": "synthetic-screen", "source_code": code,
                              "target_ref": target, "effective": run["period"]})

    def batch(name):
        return {k: next(b for b in s["source_batches"] if b["batch_id"] == name)[k] for k in ["source_system", "batch_id", "version"]}

    def fact(name, i, fid, aid, value, kind, selector, dates, **extra):
        p["financial_facts"].append({"fact_id": fid, "batch_ref": batch(name), "source_row": name + ".csv:record-" + str(i),
                                     "event_kind": kind, "amount": money(value), "asset_id": aid,
                                     "temporal_basis": {"kind": selector, "date": dates[selector]}, "dates": dates, **extra})

    invoice_rows = rows["raw_invoice_lines"]
    invoices = unique(invoice_rows, lambda r: r["invoice_id"] + ":" + r["line_no"])
    banks = unique(rows["raw_bank_receipts"], "bank_ref")
    apps = unique(rows["raw_cash_applications"], "application_ref")
    bundle = refs["bundle_id"]
    p["assets"].append({"asset_id": bundle, "kind": "bundle"})
    for i, r in enumerate(invoice_rows, 1):
        if not r["line_no"].isdigit() or int(r["line_no"]) < 1:
            fail("INVALID_SOURCE_KEY", "Invoice line must be positive integer")
        dates = {"invoice_date": r["invoice_date"]}
        if r["license_event_date"]:
            dates["license_date"] = r["license_event_date"]
        aid = bundle if r["item_code"] == refs["bundle_source_code"] else asset(r["item_code"])
        if r["market_code"] not in refs["territory_codes"]:
            fail("UNMAPPED_TERRITORY", r["market_code"])
        fact("raw_invoice_lines", i, "invoice/" + r["invoice_id"] + ":" + r["line_no"], aid, exact(r["billed_amount"]), "invoice", "invoice_date", dates)
    used_bank, used_invoice = defaultdict(Fraction), defaultdict(Fraction)
    allocation = refs["allocation"]
    if allocation["approval_id"] != approval["id"]:
        fail("ALLOCATION_AUTHORITY", "Bundle approval does not resolve")
    weights = [(r["asset_id"], Fraction(r["numerator"], r["denominator"])) for r in allocation["shares"]]
    p["interpretations"][0]["decisions"][-1]["allocation_terms"] = [{"asset_id": a, "weight": number(w)} for a, w in weights]
    if len(set(a for a, _ in weights)) != len(weights) or any(a not in assets or w < 0 for a, w in weights) or sum(w for _, w in weights) != 1:
        fail("ALLOCATION_CONSERVATION", "Invalid bundle weights")
    cutoff_date = instant_utc_day(run["cutoff"])
    for i, r in enumerate(rows["raw_cash_applications"], 1):
        key = r["invoice_id"] + ":" + r["line_no"]
        if r["bank_ref"] not in banks or key not in invoices:
            fail("UNRESOLVED_APPLICATION", r["application_ref"])
        bank, invoice = banks[r["bank_ref"]], invoices[key]
        if r["ccy"] != bank["ccy"] or r["ccy"] != invoice["ccy"] or bank["payer_ref"] != invoice["buyer_ref"]:
            fail("APPLICATION_PARTY_CURRENCY", r["application_ref"])
        used_bank[r["bank_ref"]] += exact(r["applied_amount"])
        used_invoice[key] += exact(r["applied_amount"])
        if day(r["posted_on"]) >= cutoff_date:
            fail("SOURCE_AFTER_CUTOFF", "Applications unavailable under selected snapshot")
        dates = {"cash_received_date": bank["value_date"], "posting_date": r["posted_on"], "invoice_date": invoice["invoice_date"]}
        if invoice["item_code"] == refs["bundle_source_code"]:
            if key != allocation["source_key"]:
                fail("ALLOCATION_AUTHORITY", "Wrong source invoice for approved allocation")
            parent = "application/" + r["application_ref"]
            fact("raw_cash_applications", i, parent, bundle, exact(r["applied_amount"]), "cash_receipt", "cash_received_date", dates,
                 external_event_ref=r["application_ref"], parent_fact_id="invoice/" + key)
            for aid, weight in weights:
                p["allocations"].append({"allocation_id": parent + "/" + aid, "allocation_group_id": allocation["id"], "source_fact_id": parent,
                                           "target_scope": {"agreement_id": deal["id"], "asset_ids": [aid]}, "method": "exact_weight", "method_version": "1",
                                           "authority_ref": approval["id"], "policy_ref": approval["id"], "scenario_id": s["fixture_id"],
                                           "effective": run["period"], "weight": number(weight)})
        else:
            fact("raw_cash_applications", i, "receipt/" + r["application_ref"], asset(invoice["item_code"]), exact(r["applied_amount"]), "cash_receipt", "cash_received_date", dates,
                 external_event_ref=r["application_ref"], parent_fact_id="invoice/" + key,
                 territory=refs["territory_codes"][invoice["market_code"]])
    if any(v > exact(banks[k]["deposit_amount"]) for k, v in used_bank.items()) or any(v > exact(invoices[k]["billed_amount"]) for k, v in used_invoice.items()):
        fail("OVERAPPLICATION", "Applications exceed bank cash or invoice face")
    if any(used_bank[k] != exact(r["deposit_amount"]) for k, r in banks.items()):
        fail("UNAPPLIED_BANK_CASH", "This bounded source profile requires complete application")
    cost_mappings = unique(policy["cost_mappings"], "source_key")
    unique(rows["raw_cost_lines"], lambda r: r["invoice_ref"] + ":" + r["line_no"])
    for i, r in enumerate(rows["raw_cost_lines"], 1):
        key = r["invoice_ref"] + ":" + r["line_no"]
        if key not in cost_mappings:
            fail("REQUIRED_COST_POLICY", key)
        c = cost_mappings[key]
        aid = asset(r["asset_code"])
        if c["gl_code"] != r["gl_code"] or c["asset_id"] != aid or c["eligibility"] not in {"deduct", "exclude"}:
            fail("COST_POLICY_MISMATCH", key)
        dates = {"invoice_date": r["invoice_date"], "posting_date": r["posted_on"]}
        if r["paid_on"]:
            dates["paid_date"] = r["paid_on"]
        fid = "cost/" + key
        p["mappings"].append({"mapping_version": refs["mapping_version"], "mapping_id": "category-" + key,
                              "kind": "cost_category", "source_namespace": "synthetic-screen", "source_code": r["gl_code"],
                              "target_ref": c["kind"], "effective": run["period"]})
        fact("raw_cost_lines", i, fid, aid, exact(r["amount"]), "incurred_cost", "posting_date", dates, category=c["kind"])
        p["parameters"]["cost_decisions"].append({"fact_id": fid, "decision_id": "SV-8-COST-SCHEDULE", "eligible": c["eligibility"] == "deduct",
                                                    "branch": "unfunded" if aid == deal["asset_ids"][0] else "funded", "reason": c["reason"]})
    next(d for d in p["interpretations"][0]["decisions"] if d["decision_id"] == "SV-8-COST-SCHEDULE")["cost_terms"] = [
        {k: c[k] for k in ["fact_id", "eligible", "branch"]} for c in p["parameters"]["cost_decisions"]]
    fs = policy["funding_snapshot"]
    if fs["complete_as_of"] != run["period"]["start"] or not fs["population"] or not fs["absent_part_funding_for_pic_a"]:
        fail("INCOMPLETE_FUNDING", "Explicit complete opening funding population is required")
    p["parameters"]["funding_snapshot"] = {"complete": True, "as_of": fs["complete_as_of"], "covered_assets": deal["asset_ids"],
                                                "covered_parties": [deal["participant_id"], deal["distributor_id"]], "evidence_ref": "fixture-observation@1"}
    unique(rows["raw_acquisition_funding"], "funding_ref")
    for i, r in enumerate(rows["raw_acquisition_funding"], 1):
        if r["funder_ref"] not in p["parameters"]["funding_snapshot"]["covered_parties"] or day(r["funded_on"]) > day(fs["complete_as_of"]):
            fail("FUNDING_SCOPE", r["funding_ref"])
        p["evidence_events"].append({"event_id": r["funding_ref"], "kind": "funding", "subject_ref": asset(r["asset_code"]),
                                     "effective_date": r["funded_on"], "observed_at": observed_at,
                                     "evidence_ref": "fixture-observation@1", "approval_ref": "SV-8-SHARE", "amount": money(exact(r["amount"])),
                                     "asset_id": asset(r["asset_code"]), "party_id": r["funder_ref"], "batch_ref": batch("raw_acquisition_funding"),
                                     "source_row": "raw_acquisition_funding.csv:record-" + str(i)})
    opening = policy["opening_state"]
    add_state(p, "main", "sv/participant-prepayment/main-pool", "participation_prepayment", opening["quantity"])
    p["state_cells"][0]["state_key"] = opening["state_key"]
    p["state_cells"][0]["provenance_ref"] = opening["provenance_ref"]
    p["references"].append({"reference_id": opening["provenance_ref"], "kind": "source", "description": opening["support_status"]})
    p["opening_aliases"][0]["state_key"] = opening["state_key"]
    return p
