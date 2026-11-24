"""Physical schema for the bounded compiler profile, plus semantic validation.

This implements a strict subset of JSON Schema 2020-12 without dependencies.
Broader draft records are intentionally rejected until their policies exist.
"""
from __future__ import annotations

from .codecs import (DataError, amount, check_text, day, digest, exact, fail,
                     instant, period)


def obj(required, optional=None):
    return {"type": "object", "properties": {**required, **(optional or {})},
            "required": list(required), "additionalProperties": False}


def arr(item):
    return {"type": "array", "items": item}


def enum(*values):
    return {"enum": list(values)}


S = {"type": "string", "minLength": 1}
B = {"type": "boolean"}
N = {"type": "integer", "minimum": 0}
NUM = {"oneOf": [{"type": "string", "pattern": r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$"},
                 obj({"numerator": S, "denominator": S})]}
MONEY = obj({"value": NUM, "currency": enum("USD")})
PERIOD = obj({"start": S, "end": S})
REF = obj({"source_system": S, "batch_id": S, "version": S})
SCOPE = obj({"agreement_id": S}, {"participant_id": S, "pool_id": S, "asset_ids": arr(S)})
CONTROL = obj({"amount_kind": S, "currency": enum("USD"), "signed_total": NUM, "absolute_total": NUM})
DECISION = obj({"decision_id": S, "clause_ref": S, "document_ref": S,
                "question": S, "evidence_label": enum("research_assumption", "explicit_clause"),
                "adopted_policy": S, "alternatives": arr(S), "scope": SCOPE,
                "effective": PERIOD, "review_status": enum("proposed", "reviewed", "approved"),
                "discriminating_case_ref": S},
               {"allocation_terms": arr(obj({"asset_id": S, "weight": NUM})),
                "cost_terms": arr(obj({"fact_id": S, "eligible": B, "branch": enum("funded", "unfunded", "lg")}))})
STATE = obj({"state_key": S, "balance_kind": enum("participation_prepayment", "cumulative_gross", "cumulative_cost", "synthetic_payment_holdback"),
             "agreement_id": S, "scope": SCOPE, "boundary": S, "unit": enum("USD"),
             "quantity": NUM, "provenance_ref": S, "policy_lineage": arr(S),
             "participant_id": S, "pool_id": S, "scenario_id": S}, {"prior_result_ref": S})
FACT = obj({"fact_id": S, "batch_ref": REF, "source_row": S,
            "event_kind": enum("cash_receipt", "invoice", "incurred_cost"), "amount": MONEY,
            "temporal_basis": obj({"kind": enum("cash_received_date", "posting_date", "incurred_date", "invoice_date"), "date": S}),
            "asset_id": S, "dates": obj({}, {x: S for x in ["cash_received_date", "posting_date", "incurred_date", "invoice_date", "paid_date", "license_date"]})},
           {"territory": S, "category": S, "external_event_ref": S, "parent_fact_id": S,
            "counterparty_id": S, "channel": enum("home_video", "other")})
EVIDENCE = obj({"event_id": S, "kind": enum("funding", "hurdle_attestation", "gate_history", "crossed_net_worksheet"),
                "subject_ref": S, "effective_date": S, "observed_at": S,
                "evidence_ref": S, "approval_ref": S},
               {"amount": MONEY, "asset_id": S, "party_id": S, "batch_ref": REF,
                "source_row": S, "satisfied": B, "period": PERIOD,
                "agreement_id": S, "pool_id": S, "member_ids": arr(S)})
MANIFEST = obj({**{x: S for x in ["run_id", "schema_version", "surface_version", "core_version", "schedule_ref", "interpretation_ref", "parameter_ref", "opening_state_ref", "calendar_ref", "compiler_build", "runtime_build", "cutoff", "scenario_id"]},
                "mapping_refs": arr(S), "batch_refs": arr(S), "reference_refs": arr(S), "policy_refs": arr(S),
                "period": PERIOD, "output_currency": enum("USD"), "mode": enum("final", "preview"),
                "input_mode": enum("full_snapshot"),
                "resource_limits": obj({"source_scalars": N, "source_tokens": N, "parser_depth": N,
                                        "lean_timeout_seconds": N, "max_facts": N})},
               {"report_date": S, "issue_date": S})
PARAMETERS = obj({"policy": obj({"agreement_id": S, "participant_id": S, "pool_id": S, "period": PERIOD},
                                {"asset_id": S, "video_proxy": NUM, "gross_rate": NUM, "net_rate": NUM}),
                  "cost_date_basis": enum("incurred_date", "posting_date"),
                  "cost_decisions": arr(obj({"fact_id": S, "decision_id": S, "eligible": B,
                                             "branch": enum("funded", "unfunded", "lg"), "reason": S}))},
                 {"funding_snapshot": obj({"complete": B, "as_of": S, "covered_assets": arr(S),
                                            "covered_parties": arr(S), "evidence_ref": S}),
                  "producer_fee_offset": MONEY, "payment_holdback_addition": MONEY,
                  "payment_holdback_release": MONEY})

INCORPORATED_POLICY = obj({"policy_id": S, "profile": S,
                           "document": obj({"locator": S, "sha256": S}),
                           "registry": obj({"locator": S, "sha256": S, "entry_sha256": S})})

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:spl:bounded-package:0.1.0-dev",
    "title": "SPL bounded synthetic run closure (not the entire draft schema)",
    **obj({"profile": enum("sv-incurred-v1", "sv-rq07-posted-v1", "lg-cleared-v1"), "manifest": MANIFEST,
           "assets": arr(obj({"asset_id": S, "kind": enum("picture", "bundle")})),
           "parties": arr(obj({"party_id": S, "name": S})),
           "roles": arr(obj({"role_id": S, "party_id": S, "agreement_id": S,
                             "role": enum("distributor", "participant", "funder"), "effective": PERIOD})),
           "agreements": arr(obj({"agreement_id": S, "version": S, "document_refs": arr(S),
                                  "interpretation_ref": S, "effective": PERIOD, "asset_ids": arr(S),
                                  "role_ids": arr(S), "calendar_ref": S})),
           "interpretations": arr(obj({"interpretation_id": S, "version": S, "decisions": arr(DECISION)})),
           "incorporated_policies": arr(INCORPORATED_POLICY),
           "mappings": arr(obj({"mapping_version": S, "mapping_id": S,
                                "kind": enum("asset_alias", "territory", "cost_category", "pool_membership"),
                                "source_namespace": S, "source_code": S, "target_ref": S, "effective": PERIOD},
                               {"purpose": S, "pool_id": S, "authority_ref": S})),
           "source_batches": arr(obj({**{x: S for x in ["source_system", "batch_id", "version", "snapshot_locator", "sha256", "format", "adapter_version", "ingested_at"]},
                                      "row_count": N, "control_totals": arr(CONTROL)})),
           "financial_facts": arr(FACT),
           "allocations": arr(obj({"allocation_id": S, "allocation_group_id": S, "source_fact_id": S,
                                   "target_scope": SCOPE, "method": S, "method_version": S,
                                   "authority_ref": S, "policy_ref": S, "scenario_id": S,
                                   "effective": PERIOD, "weight": NUM})),
           "evidence_events": arr(EVIDENCE), "state_cells": arr(STATE),
           "opening_aliases": arr(obj({"alias": S, "state_key": S})),
           "references": arr(obj({"reference_id": S, "kind": enum("calendar", "source", "synthetic_observation_policy"), "description": S})),
           "parameters": PARAMETERS,
           "adapter": obj({"adapter_id": S, "version": S, "observation_policy_ref": S,
                           "source_fixture": S, "source_digest": S})})}


def validate_shape(value, schema=SCHEMA, pointer=""):
    if "oneOf" in schema:
        successes = 0
        for option in schema["oneOf"]:
            try:
                validate_shape(value, option, pointer)
                successes += 1
            except DataError:
                pass
        if successes != 1:
            fail("SCHEMA_TYPE", "Expected exactly one allowed shape", pointer)
        return
    if "enum" in schema and value not in schema["enum"]:
        fail("UNSUPPORTED_ENUM", f"Unsupported value {value!r}", pointer)
    t = schema.get("type")
    good = {"object": isinstance(value, dict), "array": isinstance(value, list),
            "string": isinstance(value, str), "boolean": type(value) is bool,
            "integer": type(value) is int}.get(t, True)
    if not good:
        fail("SCHEMA_TYPE", f"Expected {t}", pointer)
    if t == "object":
        missing = set(schema["required"]) - value.keys()
        unknown = value.keys() - schema["properties"].keys()
        if missing:
            fail("MISSING_FIELD", f"Missing {sorted(missing)}", pointer)
        if unknown:
            fail("UNKNOWN_FIELD", f"Unknown fields {sorted(unknown)}", pointer)
        for key, item in value.items():
            validate_shape(item, schema["properties"][key], pointer + "/" + key)
    elif t == "array":
        for i, item in enumerate(value):
            validate_shape(item, schema["items"], pointer + "/" + str(i))
    elif t == "string":
        import re
        if len(value) < schema.get("minLength", 0):
            fail("EMPTY_IDENTIFIER", "Empty string", pointer)
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            fail("SCHEMA_PATTERN", "Invalid exact decimal", pointer)
    elif t == "integer" and value < schema.get("minimum", value):
        fail("SCHEMA_RANGE", "Value below minimum", pointer)


def unique(rows, key, code="DUPLICATE_ID"):
    result = {}
    for row in rows:
        k = key(row) if callable(key) else row[key]
        if k in result:
            fail(code, f"Duplicate identity {k!r}")
        result[k] = row
    return result


def ref(kind, value):
    return f"{kind}@1#sha256:{digest(value)}"


def pin_manifest(package, schedule_digest, compiler_build, runtime_build):
    m = package["manifest"]
    m.update(schedule_ref=f"schedule@1#sha256:{schedule_digest}",
             interpretation_ref=ref("interpretation", package["interpretations"]),
             mapping_refs=[ref("mapping", x) for x in sorted(package["mappings"], key=lambda x: x["mapping_id"])],
             batch_refs=[ref("batch", x) for x in sorted(package["source_batches"], key=lambda x: x["batch_id"])],
             reference_refs=[ref("reference", x) for x in sorted(package["references"], key=lambda x: x["reference_id"])],
             policy_refs=[ref("policy", x) for x in package["incorporated_policies"]],
             parameter_ref=ref("parameters", package["parameters"]),
             opening_state_ref=ref("opening", sorted(package["state_cells"], key=lambda x: x["state_key"])),
             calendar_ref=ref("calendar", [x for x in package["references"] if x["kind"] == "calendar"]),
             compiler_build=compiler_build, runtime_build=runtime_build)


def validate_package(p):
    check_text(p)
    validate_shape(p)
    m, params = p["manifest"], p["parameters"]
    for name in ["schema_version", "surface_version", "core_version"]:
        if m[name] != "0.1-draft":
            fail("UNSUPPORTED_VERSION", name + " must be 0.1-draft")
    period(m["period"])
    cutoff = instant(m["cutoff"], "/manifest/cutoff")
    for field in ("report_date", "issue_date"):
        if field in m:
            day(m[field], "/manifest/" + field)
    expected_limits = {"source_scalars": 1000000, "source_tokens": 200000, "parser_depth": 128, "lean_timeout_seconds": 180, "max_facts": 100000}
    if m["resource_limits"] != expected_limits:
        fail("UNSUPPORTED_RESOURCE_PROFILE", "This prototype uses the fixed documented resource limits")
    if len(p["financial_facts"]) + len(p["evidence_events"]) > m["resource_limits"]["max_facts"]:
        fail("RESOURCE_LIMIT", "Fact limit exceeded; no truncated calculation")
    if params["policy"]["period"] != m["period"]:
        fail("PERIOD_MISMATCH", "Policy and run period differ")
    assets = unique(p["assets"], "asset_id")
    parties = unique(p["parties"], "party_id")
    roles = unique(p["roles"], "role_id")
    agreements = unique(p["agreements"], "agreement_id")
    unique(p["interpretations"], "interpretation_id")
    unique(p["incorporated_policies"], "policy_id")
    mappings = unique(p["mappings"], "mapping_id")
    facts = unique(p["financial_facts"], "fact_id")
    events = unique(p["evidence_events"], "event_id")
    states = unique(p["state_cells"], "state_key")
    unique(p["allocations"], "allocation_id")
    references = unique(p["references"], "reference_id")
    unique(p["opening_aliases"], "alias")
    decisions = unique([d for i in p["interpretations"] for d in i["decisions"]], "decision_id")
    batches = unique(p["source_batches"], lambda b: (b["source_system"], b["batch_id"], b["version"]))
    if not batches:
        fail("SOURCE_DELIVERY", "An explicitly empty delivery needs a zero-row SourceBatch")
    if p["profile"] == "sv-rq07-posted-v1" and {b["batch_id"] for b in batches.values()} != {
            "raw_invoice_lines", "raw_bank_receipts", "raw_cash_applications", "raw_cost_lines", "raw_acquisition_funding"}:
        fail("SOURCE_DELIVERY", "RQ-07 requires all five declared complete source spaces")
    policy = params["policy"]
    def required_fields(value, fields, code="MISSING_FIELD"):
        missing = set(fields) - value.keys()
        if missing:
            fail(code, "Missing conditionally required fields: " + ", ".join(sorted(missing)))
    if p["profile"] == "lg-cleared-v1":
        required_fields(policy, ["asset_id", "video_proxy", "gross_rate", "net_rate"])
        required_fields(params, ["producer_fee_offset", "payment_holdback_addition", "payment_holdback_release"])
        for key in ["video_proxy", "gross_rate", "net_rate"]:
            exact(policy[key])
        for key in ["producer_fee_offset", "payment_holdback_addition", "payment_holdback_release"]:
            amount(params[key])
    else:
        required_fields(params, ["funding_snapshot"], "INCOMPLETE_FUNDING")
        if params["funding_snapshot"]["evidence_ref"] not in references:
            fail("UNRESOLVED_REFERENCE", "Funding snapshot evidence missing")
        day(params["funding_snapshot"]["as_of"])
    expected_cost_basis = "posting_date" if p["profile"] == "sv-rq07-posted-v1" else "incurred_date"
    if params["cost_date_basis"] != expected_cost_basis:
        fail("SCHEDULE_PROFILE_MISMATCH", "Cost selector differs from named profile")
    if policy["agreement_id"] not in agreements or policy["participant_id"] not in parties:
        fail("UNRESOLVED_REFERENCE", "Policy agreement or participant missing")
    agreement = agreements[policy["agreement_id"]]
    if len(agreements) != 1:
        fail("UNSUPPORTED_SCOPE_PROFILE", "Bounded run profiles bind one agreement")
    period(agreement["effective"])
    if agreement["effective"]["start"] > m["period"]["start"] or agreement["effective"]["end"] < m["period"]["end"]:
        fail("AGREEMENT_EFFECTIVE_SCOPE", "Selected agreement does not cover the run period")
    interpretation_refs = {i["interpretation_id"] + "@" + i["version"] for i in p["interpretations"]}
    if (agreement["interpretation_ref"] not in interpretation_refs or
            not set(agreement["document_refs"]) <= references.keys() or agreement["calendar_ref"] not in references):
        fail("UNRESOLVED_REFERENCE", "Agreement interpretation/document/calendar missing")
    members = set(agreement["asset_ids"])
    if len(members) != len(agreement["asset_ids"]):
        fail("DUPLICATE_MEMBER", "Agreement asset members must be unique")
    if not members <= assets.keys() or not set(agreement["role_ids"]) <= roles.keys():
        fail("UNRESOLVED_REFERENCE", "Agreement asset or role missing")
    for r in roles.values():
        if r["party_id"] not in parties or r["agreement_id"] not in agreements:
            fail("UNRESOLVED_REFERENCE", "Role has missing dependency")
        period(r["effective"])
    active_roles = [roles[rid] for rid in agreement["role_ids"] if roles[rid]["agreement_id"] == policy["agreement_id"] and
                    roles[rid]["effective"]["start"] <= m["period"]["start"] and roles[rid]["effective"]["end"] >= m["period"]["end"]]
    if (len([r for r in active_roles if r["role"] == "participant" and r["party_id"] == policy["participant_id"]]) != 1 or
            len([r for r in active_roles if r["role"] == "distributor"]) != 1):
        fail("ROLE_SCOPE", "Need one effective scoped participant and distributor role")
    for d in decisions.values():
        period(d["effective"])
        ds = d["scope"]
        if (ds["agreement_id"] != policy["agreement_id"] or
                ds.get("pool_id", policy["pool_id"]) != policy["pool_id"] or
                ds.get("participant_id", policy["participant_id"]) != policy["participant_id"] or
                not set(ds.get("asset_ids", list(members))) <= members or
                d["effective"]["start"] > m["period"]["start"] or d["effective"]["end"] < m["period"]["end"]):
            fail("POLICY_SCOPE", "Decision belongs to another agreement")
        if d["document_ref"] not in references:
            fail("UNRESOLVED_REFERENCE", "Decision document reference missing")
    # All material schedule citations must resolve; wrapper additionally checks syntax citations.
    if not decisions:
        fail("REQUIRED_POLICY", "No interpretation decisions supplied")
    for mapping in mappings.values():
        period(mapping["effective"])
        if mapping["kind"] == "pool_membership":
            if mapping.get("purpose") != "participation_prepayment" or mapping.get("pool_id") != policy["pool_id"]:
                fail("POOL_SCOPE", "Membership purpose/pool differs from recovery scope")
            if mapping["target_ref"] not in members:
                fail("POOL_SCOPE", "Out-of-agreement member")
        if mapping["kind"] == "asset_alias" and mapping["target_ref"] not in assets:
            fail("UNRESOLVED_REFERENCE", "Asset alias target missing")
        if mapping["kind"] == "territory" and mapping["target_ref"] != "US":
            fail("UNSUPPORTED_ENUM", "Only the supplied US territory dictionary is supported")
    for f in facts.values():
        amount(f["amount"])
        if amount(f["amount"]) < 0:
            fail("UNSUPPORTED_CORRECTION_POLICY", "Signed facts need a separate correction profile")
        b = f["batch_ref"]
        if (b["source_system"], b["batch_id"], b["version"]) not in batches:
            fail("UNRESOLVED_REFERENCE", "Financial fact source batch missing")
        if f["asset_id"] not in assets:
            fail("UNMAPPED_ASSET", f["asset_id"])
        for d in f["dates"].values():
            day(d)
        t = f["temporal_basis"]
        day(t["date"])
        if f["dates"].get(t["kind"]) != t["date"]:
            fail("TEMPORAL_BASIS_MISMATCH", f["fact_id"])
        if "parent_fact_id" in f and f["parent_fact_id"] not in facts:
            fail("UNRESOLVED_REFERENCE", "Missing parent fact")
        if f.get("parent_fact_id") == f["fact_id"]:
            fail("CYCLIC_REFERENCE", "Self parent")
        seen, current = set(), f
        while "parent_fact_id" in current:
            if current["fact_id"] in seen:
                fail("CYCLIC_REFERENCE", "Cyclic financial fact parents")
            seen.add(current["fact_id"])
            current = facts[current["parent_fact_id"]]
    for index, e in enumerate(events.values()):
        day(e["effective_date"])
        observed_at = instant(e["observed_at"], f"/evidence_events/{index}/observed_at")
        if observed_at >= cutoff:
            fail("EVIDENCE_AFTER_CUTOFF", e["event_id"])
        if e["approval_ref"] not in decisions:
            fail("REQUIRED_POLICY", "Evidence decision missing")
        if e["evidence_ref"] not in references:
            fail("UNRESOLVED_REFERENCE", "Evidence reference missing")
        kind = e["kind"]
        supported_events = {"funding"} if p["profile"].startswith("sv-") else {"hurdle_attestation", "gate_history", "crossed_net_worksheet"}
        if kind not in supported_events:
            fail("UNSUPPORTED_EVIDENCE", "Event kind is outside the selected profile")
        fields = {"funding": ["amount", "asset_id", "party_id"],
                  "hurdle_attestation": ["agreement_id", "satisfied"],
                  "gate_history": ["agreement_id", "asset_id", "period", "satisfied"],
                  "crossed_net_worksheet": ["agreement_id", "pool_id", "period", "member_ids", "amount"]}[kind]
        required_fields(e, fields)
        expected_subject = e["asset_id"] if kind in {"funding", "gate_history"} else e["agreement_id"] if kind == "hurdle_attestation" else e["pool_id"]
        if e["subject_ref"] != expected_subject:
            fail("EVIDENCE_SCOPE", "Subject reference disagrees with typed evidence scope")
        if "period" in e:
            period(e["period"])
        if "party_id" in e and e["party_id"] not in parties:
            fail("UNRESOLVED_REFERENCE", "Evidence party missing")
        if "batch_ref" in e:
            b = e["batch_ref"]
            if (b["source_system"], b["batch_id"], b["version"]) not in batches or "source_row" not in e:
                fail("UNRESOLVED_REFERENCE", "Evidence source batch/row missing")
        if "amount" in e:
            amount(e["amount"])
        if "asset_id" in e and e["asset_id"] not in members:
            fail("EVIDENCE_SCOPE", e["event_id"])
    for s in states.values():
        if (s["agreement_id"] != policy["agreement_id"] or s["participant_id"] != policy["participant_id"] or
                s["pool_id"] != policy["pool_id"] or s["scope"].get("pool_id") != policy["pool_id"] or
                s["scope"]["agreement_id"] != policy["agreement_id"]):
            fail("STATE_SCOPE", "Opening scope differs from settlement")
        if s["boundary"] != m["period"]["start"]:
            fail("STATE_BOUNDARY", "Opening boundary must equal period start")
        if s["scenario_id"] != m["scenario_id"]:
            fail("STATE_SCENARIO_LINEAGE", "Synthetic state cannot cross scenario lineages")
        if exact(s["quantity"]) < 0:
            fail("NEGATIVE_STATE", "Opening magnitude is negative")
        if not s["policy_lineage"] or not set(s["policy_lineage"]) <= decisions.keys():
            fail("STATE_LINEAGE", "Opening policy lineage missing")
        if s["provenance_ref"] not in references:
            fail("STATE_LINEAGE", "Opening provenance missing")
    for alias in p["opening_aliases"]:
        if alias["state_key"] not in states:
            fail("UNRESOLVED_REFERENCE", "Opening alias not found")
    if len({a["state_key"] for a in p["opening_aliases"]}) != len(p["opening_aliases"]):
        fail("DUPLICATE_STATE_CONSUMPTION", "Two aliases consume the same cell")
    if set(a["state_key"] for a in p["opening_aliases"]) != states.keys():
        fail("UNBOUND_STATE", "Every supplied state cell must have one typed port")
    expected_ports = {"sv/participant-prepayment/main-pool": "participation_prepayment"} if p["profile"].startswith("sv-") else {
        "lg/work-D/true-cash/cumulative-gross": "cumulative_gross", "lg/work-D/true-cash/cumulative-cost": "cumulative_cost",
        "synthetic/work-D/payment-holdback": "synthetic_payment_holdback"}
    if set(a["alias"] for a in p["opening_aliases"]) != expected_ports.keys():
        fail("STATE_PORT_PROFILE", "State aliases differ from supported case profile")
    for alias in p["opening_aliases"]:
        cell = states[alias["state_key"]]
        if cell["balance_kind"] != expected_ports[alias["alias"]]:
            fail("STATE_PURPOSE", "State kind differs from declared opening port")
        if p["profile"] == "lg-cleared-v1" and cell["scope"].get("asset_ids") != [policy.get("asset_id")]:
            fail("STATE_WORK_SCOPE", "LG state must bind its declared work")
    unique(params["cost_decisions"], "fact_id")
    for c in params["cost_decisions"]:
        if c["fact_id"] not in facts or c["decision_id"] not in decisions:
            fail("REQUIRED_COST_POLICY", "Cost decision dependency missing")
        terms = decisions[c["decision_id"]].get("cost_terms", [])
        if terms and {k: c[k] for k in ["fact_id", "eligible", "branch"]} not in terms:
            fail("COST_POLICY_MISMATCH", "Selection differs from pinned decision terms")
    groups = {}
    for allocation in p["allocations"]:
        if (allocation["source_fact_id"] not in facts or allocation["authority_ref"] not in decisions or
                allocation["policy_ref"] not in decisions):
            fail("ALLOCATION_AUTHORITY", "Allocation parent/authority missing")
        if allocation["scenario_id"] != m["scenario_id"] or allocation["target_scope"].get("asset_ids", []) == []:
            fail("ALLOCATION_SCOPE", "Allocation scenario/target missing")
        groups.setdefault(allocation["source_fact_id"], []).append(allocation)
    for source, rows in groups.items():
        if len({x["allocation_group_id"] for x in rows}) != 1:
            fail("ALTERNATIVE_ALLOCATION_GROUPS", source)
        targets = [tuple(x["target_scope"]["asset_ids"]) for x in rows]
        if len(set(targets)) != len(targets):
            fail("DUPLICATE_ALLOCATION_TARGET", source)
        if any(exact(x["weight"]) < 0 for x in rows) or sum(exact(x["weight"]) for x in rows) != 1:
            fail("ALLOCATION_CONSERVATION", source)
        authorities = {x["authority_ref"] for x in rows}
        if len(authorities) != 1:
            fail("ALLOCATION_AUTHORITY", "One authority per selected group required")
        terms = decisions[next(iter(authorities))].get("allocation_terms")
        if terms is None:
            fail("ALLOCATION_AUTHORITY", "Explicit target/weight authority terms required")
        selected = sorted((tuple(x["target_scope"]["asset_ids"]), exact(x["weight"])) for x in rows)
        approved = sorted(((x["asset_id"],), exact(x["weight"])) for x in terms)
        if selected != approved:
            fail("ALLOCATION_AUTHORITY", "Conserved allocation differs from approved weights")
    # Recompute controls of the declared complete source profile from normalized
    # parent facts/evidence. Allocated children are views, never extra receipts.
    for index, b in enumerate(p["source_batches"]):
        import re
        if not re.fullmatch(r"[0-9a-f]{64}", b["sha256"]):
            fail("INVALID_DIGEST", "Source digest must be lowercase SHA-256")
        instant(b["ingested_at"], f"/source_batches/{index}/ingested_at")
        if b["format"] == "json" and b["batch_id"] == "authored":
            fact_rows = [f for f in facts.values() if f["batch_ref"]["batch_id"] == b["batch_id"]]
            if b["row_count"] != len(fact_rows):
                fail("SOURCE_ROW_COUNT", "Authored fixture delivery row count mismatch")
        for control in b["control_totals"]:
            exact(control["signed_total"])
            exact(control["absolute_total"])
        if b["adapter_version"] == "1.0.0" and p["profile"] == "sv-rq07-posted-v1":
            name = b["batch_id"]
            rows = [f for f in facts.values() if f["batch_ref"]["batch_id"] == name]
            values = [amount(f["amount"]) for f in rows]
            if name == "raw_acquisition_funding":
                values = [amount(e["amount"]) for e in events.values() if e.get("batch_ref", {}).get("batch_id") == name]
            if name == "raw_bank_receipts":
                values = [amount(f["amount"]) for f in facts.values() if f["batch_ref"]["batch_id"] == "raw_cash_applications"]
            if len(b["control_totals"]) != 1 or b["control_totals"][0]["amount_kind"] != name:
                fail("SOURCE_CONTROL_MISMATCH", "Exactly one control per raw amount space required")
            c = b["control_totals"][0]
            if exact(c["signed_total"]) != sum(values) or exact(c["absolute_total"]) != sum(abs(x) for x in values):
                fail("SOURCE_CONTROL_MISMATCH", name)
    return p
