"""Validated atomic run wrapper around the authoritative native Lean compiler."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

from .codecs import (DataError, amount, canonical, day, digest, encode, exact, fail,
                     file_digest, instant_utc_day, loads, money, number, write_json)
from .lean_tools import ROOT, compile_schedule, export_ir, interpret_schedule, lean
from .schema import pin_manifest, ref, unique, validate_package


def build_identity(paths):
    return digest({str(Path(x).relative_to(ROOT)).replace("\\", "/"): file_digest(x) for x in paths})


def identities():
    # E1 runtime pin covers generated helper imports and their repository-local
    # transport/checker dependencies. Upstream Lean libraries are toolchain-pinned.
    runtime_sources = [ROOT / "SPL" / (name + ".lean") for name in
                       ["Runtime", "Core", "Fold", "Instant", "Calendar", "Dimensions", "Bindings", "Check", "Syntax"]]
    return (build_identity(sorted((ROOT / "SPL").glob("*.lean")) + sorted((ROOT / "spl_compiler").glob("*.py")) + [ROOT / "lean-toolchain", ROOT / "SPL.lean"]),
            build_identity(runtime_sources + [ROOT / "lean-toolchain"]))


def bind_package(package, schedule_path):
    if package.get("profile") == "spl-module/1":
        from .modules import bind_module_package
        return bind_module_package(package, schedule_path)
    from .policies import policy_closure
    p = deepcopy(package)
    source = Path(schedule_path).read_text(encoding="utf-8")
    p["incorporated_policies"] = policy_closure(source, str(schedule_path), p, ROOT)
    compiler, runtime = identities()
    pin_manifest(p, file_digest(schedule_path), compiler, runtime)
    return p


def _citations(value):
    found = set()
    if isinstance(value, dict):
        if value.get("citation"):
            found.add(value["citation"])
        for item in value.values():
            found |= _citations(item)
    elif isinstance(value, list):
        for item in value:
            found |= _citations(item)
    return found


def project(p):
    """Validated canonical records -> typed case views, with accounting lineage."""
    policy, params, manifest = p["parameters"]["policy"], p["parameters"], p["manifest"]
    members = sorted(next(a for a in p["agreements"] if a["agreement_id"] == policy["agreement_id"])["asset_ids"])
    pp = manifest["period"]
    decisions = {d["decision_id"] for i in p["interpretations"] for d in i["decisions"]}
    if p["profile"].startswith("sv-"):
        membership = [x for x in p["mappings"] if x["kind"] == "pool_membership" and x.get("pool_id") == policy["pool_id"] and
                      x.get("purpose") == "participation_prepayment" and x["effective"]["start"] <= pp["start"] and x["effective"]["end"] >= pp["end"]]
        if len(membership) != len(members) or sorted(x["target_ref"] for x in membership) != members:
            fail("POOL_MEMBERSHIP_REQUIRED", "Exactly one effective authorized membership per title required")
        if any(x.get("authority_ref") not in decisions for x in membership):
            fail("POOL_AUTHORITY_REQUIRED", "Pool authority decision missing")
    facts = {f["fact_id"]: f for f in p["financial_facts"]}
    allocations = defaultdict(list)
    for a in p["allocations"]:
        allocations[a["source_fact_id"]].append(a)
    receipts, lineage, dispositions = [], [], []
    selected_events = set()
    for f in sorted(facts.values(), key=lambda x: x["fact_id"]):
        fid = f["fact_id"]
        if f["event_kind"] != "cash_receipt":
            continue
        event = f.get("external_event_ref", fid)
        if event in selected_events:
            fail("DUPLICATE_ECONOMIC_EVENT", "Unallocated duplicated cash identity " + event)
        selected_events.add(event)
        if "cash_received_date" not in f["dates"]:
            fail("REQUIRED_CASH_DATE", fid)
        if p["profile"] == "sv-rq07-posted-v1":
            if "posting_date" not in f["dates"]:
                fail("REQUIRED_OBSERVATION_DATE", fid)
            if day(f["dates"]["posting_date"]) >= instant_utc_day(manifest["cutoff"]):
                fail("SOURCE_AFTER_CUTOFF", fid)
        if f["asset_id"] not in members and fid not in allocations:
            fail("POOL_SCOPE", "Out-of-pool cash cannot consume this advance")
        if fid in allocations:
            for allocation in sorted(allocations[fid], key=lambda a: a["allocation_id"]):
                targets = allocation["target_scope"].get("asset_ids", [])
                if len(targets) != 1 or targets[0] not in members or allocation["target_scope"]["agreement_id"] != policy["agreement_id"]:
                    fail("ALLOCATION_SCOPE", fid)
                if allocation["effective"]["start"] > pp["start"] or allocation["effective"]["end"] < pp["end"]:
                    fail("ALLOCATION_DATE", fid)
                child = allocation["allocation_id"]
                receipt = {"fact_id": child, "asset_id": targets[0], "amount": money(amount(f["amount"]) * exact(allocation["weight"])),
                           "cash_received_date": f["dates"]["cash_received_date"]}
                if p["profile"] == "lg-cleared-v1":
                    if f.get("channel") not in {"home_video", "other"}:
                        fail("REQUIRED_CHANNEL_MAPPING", fid)
                    receipt["is_home_video"] = f["channel"] == "home_video"
                receipts.append(receipt)
                lineage.append({"view_id": child, "fact_ids": [fid], "source_rows": [f["source_row"]],
                                "allocation_id": allocation["allocation_id"], "policy_ref": allocation["authority_ref"], "weight": allocation["weight"]})
        else:
            receipt = {k: f[k] for k in ["fact_id", "asset_id", "amount"]}
            receipt["cash_received_date"] = f["dates"]["cash_received_date"]
            if p["profile"] == "lg-cleared-v1":
                if f.get("channel") not in {"home_video", "other"}:
                    fail("REQUIRED_CHANNEL_MAPPING", fid)
                receipt["is_home_video"] = f["channel"] == "home_video"
            receipts.append(receipt)
            lineage.append({"view_id": fid, "fact_ids": [fid], "source_rows": [f["source_row"]]})
        in_period = pp["start"] <= f["dates"]["cash_received_date"] < pp["end"]
        dispositions.append({"fact_id": fid, "disposition": "included" if in_period else "excluded", "measure": "cash_receipts",
                             "reason": "Direct receipt or allocated parent consumed once" if in_period else "Cash date outside half-open period"})
    cost_decisions = {x["fact_id"]: x for x in params["cost_decisions"]}
    costs = []
    for f in sorted(facts.values(), key=lambda x: x["fact_id"]):
        if f["event_kind"] == "invoice":
            dispositions.append({"fact_id": f["fact_id"], "disposition": "excluded", "measure": "cash_receipts", "reason": "Invoice face is a separate amount space"})
        if f["event_kind"] != "incurred_cost":
            continue
        fid = f["fact_id"]
        if f["asset_id"] not in members:
            fail("POOL_SCOPE", "Out-of-pool cost")
        c = cost_decisions.get(fid)
        if c is None:
            fail("REQUIRED_COST_POLICY", fid)
        selector = params["cost_date_basis"]
        if selector not in f["dates"]:
            fail("REQUIRED_COST_DATE", "Missing " + selector + " for " + fid)
        in_period = pp["start"] <= f["dates"][selector] < pp["end"]
        dispositions.append({"fact_id": fid, "disposition": "included" if c["eligible"] and in_period else "excluded", "measure": "eligible_costs",
                             "reason": c["reason"] if in_period else "Selected cost date outside half-open period", "policy_ref": c["decision_id"]})
        if c["eligible"]:
            row = {k: f[k] for k in ["fact_id", "asset_id", "amount"]}
            if selector == "posting_date":
                row.update(recognition_date=f["dates"][selector], recognition_policy_ref=c["decision_id"])
            else:
                row["incurred_date"] = f["dates"][selector]
            if p["profile"] != "lg-cleared-v1":
                row["eligibility_decision_id"] = c["decision_id"]
            costs.append(row)
            lineage.append({"view_id": fid, "fact_ids": [fid], "source_rows": [f["source_row"]], "policy_ref": c["decision_id"], "date_selector": selector})
    inputs = {"receipts": receipts, "policy": policy}
    if p["profile"].startswith("sv-"):
        fs = params.get("funding_snapshot")
        agreement = next(a for a in p["agreements"] if a["agreement_id"] == policy["agreement_id"])
        parties = [r["party_id"] for r in p["roles"] if r["role_id"] in agreement["role_ids"] and
                   r["agreement_id"] == policy["agreement_id"] and r["role"] == "distributor" and
                   r["effective"]["start"] <= pp["start"] and r["effective"]["end"] >= pp["end"]]
        if len(parties) != 1:
            fail("FUNDING_SCOPE", "Exactly one named distributor required")
        funders = {policy["participant_id"], parties[0]}
        if (not fs or not fs["complete"] or set(fs["covered_assets"]) != set(members) or
                set(fs["covered_parties"]) != funders or fs["as_of"] != pp["start"]):
            fail("INCOMPLETE_FUNDING", "Need complete same-picture/party opening snapshot")
        totals = defaultdict(Fraction)
        for e in p["evidence_events"]:
            if e["kind"] != "funding":
                fail("UNSUPPORTED_EVIDENCE", "SV pilot supports funding evidence only")
            if e.get("party_id") not in funders or e.get("asset_id") not in members or day(e["effective_date"]) > day(fs["as_of"]):
                fail("FUNDING_SCOPE", e["event_id"])
            value = amount(e["amount"])
            if value < 0:
                fail("NEGATIVE_FUNDING", e["event_id"])
            totals[e["asset_id"], e["party_id"]] += value
        pictures = []
        for asset in members:
            part = totals[asset, policy["participant_id"]]
            total = part + totals[asset, parties[0]]
            contributed = part > 0
            if contributed and total <= 0:
                fail("ZERO_FUNDING_DENOMINATOR", asset)
            pictures.append({"asset_id": asset, "contribution_present": contributed, "funding_share": number(part / total if contributed else Fraction(0))})
            for c in params["cost_decisions"]:
                if facts[c["fact_id"]]["asset_id"] == asset and c["branch"] != ("funded" if contributed else "unfunded"):
                    fail("COST_BRANCH_MISMATCH", c["fact_id"])
        inputs.update(pictures=pictures, eligible_costs=costs)
    else:
        if params["cost_date_basis"] != "incurred_date":
            fail("UNSUPPORTED_COST_PROFILE", "LG requires explicit incurred dates")
        asset = policy.get("asset_id")
        if asset not in members or len(members) != 1:
            fail("LG_WORK_SCOPE", "LG-01 binds exactly one work")
        if any(exact(policy[k]) < 0 for k in ["video_proxy", "gross_rate", "net_rate"]):
            fail("LG_NEGATIVE_RATE", "Nonnegative rates required")
        ev = defaultdict(list)
        for e in p["evidence_events"]:
            ev[e["kind"]].append(e)
        for k in ["hurdle_attestation", "gate_history", "crossed_net_worksheet"]:
            if len(ev[k]) != 1:
                fail("LG_REQUIRED_EVIDENCE", "Need exactly one " + k)
        hurdle, gate, net = (ev[k][0] for k in ["hurdle_attestation", "gate_history", "crossed_net_worksheet"])
        if "satisfied" not in hurdle or "satisfied" not in gate or "amount" not in net:
            fail("LG_REQUIRED_EVIDENCE", "Attestation truth/worksheet amount must be explicitly supplied")
        if (hurdle.get("agreement_id") != policy["agreement_id"] or gate.get("agreement_id") != policy["agreement_id"] or
                net.get("agreement_id") != policy["agreement_id"]):
            fail("LG_EVIDENCE_SCOPE", "Attestation agreement differs")
        if gate.get("asset_id") != asset or gate.get("period") != pp:
            fail("LG_GATE_HISTORY_WRONG_PERIOD", "Work evidence scope/period differs")
        if net.get("pool_id") != policy["pool_id"] or net.get("period") != pp or set(net.get("member_ids", [])) != set(members):
            fail("LG_NET_WORKSHEET_SCOPE", "Net worksheet scope differs")
        inputs.update(actual_costs=costs, outside_hurdle={"agreement_id": hurdle["agreement_id"], "attained": hurdle.get("satisfied", False), "effective_date": hurdle["effective_date"]},
                      work_gate_history={"asset_id": asset, "period": pp, "cleared_throughout": gate["satisfied"]}, crossed_net_subtotal=net["amount"],
                      **{k: params[k] for k in ["producer_fee_offset", "payment_holdback_addition", "payment_holdback_release"]})
    states = {s["state_key"]: s for s in p["state_cells"]}
    openings = {a["alias"]: money(exact(states[a["state_key"]]["quantity"])) for a in p["opening_aliases"]}
    return inputs, openings, lineage, dispositions


def semantic_digest(p, inputs, openings):
    # Logical views are sorted by stable ID. Physical row locations/ingestion/path
    # remain in audit metadata but do not alter the semantic identity.
    def logical(value):
        if isinstance(value, dict):
            # Raw source fingerprints have their own physical snapshot identity.
            omitted = {"source_row", "snapshot_locator", "ingested_at", "sha256", "source_digest"}
            return {k: logical(v) for k, v in value.items() if k not in omitted}
        if isinstance(value, list):
            items = [logical(x) for x in value]
            # In these bounded package records all arrays are mathematical sets;
            # ordered collection values in `inputs` retain their separate order.
            return sorted(items, key=canonical)
        return value
    closure = {k: logical(v) for k, v in p.items() if k != "manifest"}
    # Policy document bytes define the reviewed economic method, unlike physical
    # transport fingerprints. Their complete pins belong to semantic identity.
    closure["incorporated_policies"] = deepcopy(p["incorporated_policies"])
    return digest({"logical_dependency_closure": closure, "profile": p["profile"], "schedule": p["manifest"]["schedule_ref"],
                   "versions": [p["manifest"][x] for x in ["schema_version", "surface_version", "core_version"]],
                   "scenario": p["manifest"]["scenario_id"], "cutoff": p["manifest"]["cutoff"],
                   "mode": p["manifest"]["mode"], "input_mode": p["manifest"]["input_mode"], "output_currency": p["manifest"]["output_currency"],
                   "resource_limits": p["manifest"]["resource_limits"],
                   "inputs": inputs, "openings": openings,
                   "compiler": p["manifest"]["compiler_build"], "runtime": p["manifest"]["runtime_build"]})


def normalize_target(value):
    if isinstance(value, dict):
        if set(value) == {"numerator", "denominator"}:
            return number(exact(value))
        return {k: normalize_target(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_target(x) for x in value]
    return value


def run_package(package, schedule_path, *, backend="compare", artifact_dir=None, audit_profile="array-v1"):
    """Default final path: native Lean compilation/execution AND oracle comparison."""
    if isinstance(package, dict) and package.get("profile") == "spl-module/1":
        from .modules import run_module_package
        return run_module_package(package, schedule_path, backend=backend, artifact_dir=artifact_dir, audit_profile=audit_profile)
    from .checker import check_schedule
    from .evaluator import evaluate
    from .model import SPLException
    from .parser import parse
    from .readable import is_readable, parse_readable
    from .policies import policy_review
    from .artifacts import ArtifactPublication
    p = deepcopy(package)
    result = {"status": "blocked", "statements": [], "detail": [], "closing_state": [], "trace": [],
              "diagnostics": [], "reconciliation": {}, "payment_evidence_status": "no_event_supplied",
              "issuance_status": "unissued", "manifest": p.get("manifest", {}) if isinstance(p, dict) else {}}
    from .compact_execution import require_profile
    from .audited_artifacts import AuditedPublication, unavailable_trace
    if audit_profile not in {"array-v1", "compact-v2"}:
        raise ValueError("UNSUPPORTED_AUDIT_PROFILE")
    compact = audit_profile == "compact-v2"
    publication = (AuditedPublication if compact else ArtifactPublication)(artifact_dir) if artifact_dir else None
    require_profile(audit_profile, backend, artifact_dir)
    if compact:
        result["trace"] = unavailable_trace()
    def publish():
        if publication:
            fields = {"statement.json": "statements", "detail.json": "detail",
                "trace.json": "trace", "closing-state.json": "closing_state", "diagnostics.json": "diagnostics",
                "reconciliation.json": "reconciliation"}
            if "policy_review" in result:
                fields["policy-review.json"] = "policy_review"
            return publication.finish(result, fields)
        return result
    try:
        if backend not in {"compare", "reference", "lean"}:
            fail("UNSUPPORTED_BACKEND", backend)
        validate_package(p)
        bound = bind_package(p, schedule_path)
        for name in ["schedule_ref", "interpretation_ref", "parameter_ref", "opening_state_ref", "mapping_refs", "batch_refs", "reference_refs", "policy_refs", "calendar_ref", "compiler_build", "runtime_build"]:
            if p["manifest"][name] != bound["manifest"][name]:
                fail("MANIFEST_DIGEST_MISMATCH", "Unpinned or changed dependency: " + name)
        if p["incorporated_policies"] != bound["incorporated_policies"]:
            fail("POLICY_CLOSURE_MISMATCH", "Incorporated policy documents or registry changed; create a new reviewed snapshot")
        source = Path(schedule_path).read_text(encoding="utf-8")
        readable = is_readable(source)
        checked = check_schedule(parse_readable(source, str(Path(schedule_path).name)) if readable else parse(source, str(Path(schedule_path).name)))
        result["source_format"] = "spl-readable/0.1-dev" if readable else "spl/0.1-draft"
        result["policy_review"] = policy_review(source, str(schedule_path), p, ROOT)
        decisions = {d["decision_id"] for i in p["interpretations"] for d in i["decisions"]}
        if not _citations(checked.schedule) <= decisions:
            fail("REQUIRED_POLICY", "Schedule citation missing from interpretation closure")
        cost_decl = next((d for d in checked.schedule["declarations"] if d["kind"] == "input" and d["name"] == "eligible_costs"), None)
        posting = bool(cost_decl and cost_decl["type"] == {"name": "List", "args": [{"name": "SVPostingCost", "args": []}]})
        if posting != (p["profile"] == "sv-rq07-posted-v1"):
            fail("SCHEDULE_PROFILE_MISMATCH", "Posting-date profile must use the separately typed schedule")
        inputs, openings, lineage, dispositions = project(p)
        # State aliases resolve once to the schedule's lexical opening ports.
        aliases_to_names = {d["alias"]: d["name"] for d in checked.schedule["declarations"] if d["kind"] == "opening"}
        if set(openings) != set(aliases_to_names):
            fail("OPENING_BINDING_MISMATCH", "State aliases differ from schedule ports")
        openings = {aliases_to_names[k]: v for k, v in openings.items()}
        semantic = semantic_digest(p, inputs, openings)
        result["semantic_run_digest"] = semantic
        result["input_dispositions"] = dispositions
        result["source_to_target_lineage"] = lineage
        work = publication.work if publication else ROOT / ".lake/spl" / semantic
        work.mkdir(parents=True, exist_ok=True)
        write_json(work / "canonical-package.json", p)
        write_json(work / "policy-review.json", result["policy_review"])
        # Retain the authored review material as bytes, in addition to its pins.
        # A later edit to the repository must not rewrite an earlier run package.
        (work / "source.spl").write_bytes(Path(schedule_path).read_bytes())
        retained = {}
        for policy in p["incorporated_policies"]:
            for dependency in [policy["document"], policy["registry"]]:
                retained[dependency["locator"]] = dependency["sha256"]
        for locator, expected_sha in retained.items():
            dependency_path = ROOT / locator
            if file_digest(dependency_path) != expected_sha:
                fail("POLICY_CLOSURE_MISMATCH", "Policy changed during run: " + locator)
            destination = work / "review-sources" / locator
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(dependency_path.read_bytes())
        write_json(work / "bindings.json", {"inputs": inputs, "openings": openings})
        if compact:
            from .compact_execution import execute_compact
            observed, pins, audit_summary = execute_compact(work / "source.spl", work, checked)
            if pins["source_sha256"] != p["manifest"]["schedule_ref"].split(":")[-1]:
                fail("AUDIT_SOURCE_CHANGED", "Consumed source differs from reviewed source")
            trace, _ = publication.attach(work / "audit.native.jsonl", bindings=pins, view={
                "format": "spl-legacy-qualified-trace/1", "source_sha256": pins["source_sha256"],
                "scope": {key: p["parameters"]["policy"][key] for key in ["agreement_id", "participant_id", "pool_id", "period"]}})
            result.update(trace=trace, trace_origin="native_ir_interpreter", trace_format="spl-trace-dag/0.1")
        else:
            reference = evaluate(checked, inputs, openings)
            observed = reference.to_dict()
            reference_trace = observed["trace"]
            trace_origin = "independent_reference_evaluator"
            if backend in {"compare", "lean"}:
                if readable:
                    lean(["--run", ROOT / "SPL/Main.lean", "expand", schedule_path, work / "expanded.spl"])
                export_ir(schedule_path, work / "typed-ir.json")
                interpreted = normalize_target(interpret_schedule(schedule_path, work / "bindings.json"))
                if (interpreted["status"] == "blocked" and interpreted.get("diagnostics") and
                        interpreted["diagnostics"][0]["code"] == "RESOURCE_LIMIT"):
                    result.update(trace=interpreted.get("trace", []), diagnostics=interpreted["diagnostics"],
                                  trace_origin=interpreted.get("trace_origin", "native_ir_interpreter"),
                                  trace_format=interpreted.get("trace_format", "spl-trace-dag/0.1"),
                                  verification={"backend": backend, "required_audit_completed": False})
                    return publish()
                generated = compile_schedule(schedule_path, work / "Settlement.lean")
                native = normalize_target(loads(lean(["--run", generated, work / "bindings.json"])))
                write_json(work / "lean-result.json", native)
                write_json(work / "native-ir-result.json", interpreted)
                for field in ["status", "emissions", "closing"]:
                    if canonical(native[field]) != canonical(interpreted[field]):
                        fail("NATIVE_IR_DIFFERENTIAL_MISMATCH", field)
                if native["status"] == "blocked" and [d["code"] for d in native["diagnostics"]] != [d["code"] for d in interpreted["diagnostics"]]:
                    fail("NATIVE_IR_DIFFERENTIAL_MISMATCH", "diagnostics")
                if backend in {"compare", "lean"}:
                    for field in ["status", "emissions", "closing"]:
                        if canonical(native[field]) != canonical(observed[field]):
                            fail("COMPILER_DIFFERENTIAL_MISMATCH", field)
                    if native["status"] == "blocked" and [d["code"] for d in native["diagnostics"]] != [d["code"] for d in observed["diagnostics"]]:
                        fail("COMPILER_DIFFERENTIAL_MISMATCH", "diagnostics")
                observed = {**native, "trace": interpreted["trace"]}
                trace_origin = interpreted["trace_origin"]
                result["trace_format"] = interpreted["trace_format"]
                write_json(work / "reference-trace.json", reference_trace)
            result["trace"] = observed["trace"]
            seen = set()
            for node in result["trace"]:
                if trace_origin == "native_ir_interpreter":
                    if not all(dependency in seen for dependency in node["dependencies"]):
                        fail("TRACE_DAG_INVALID", "Trace dependency is absent or out of topological order")
                    seen.add(node["node_id"])
                    node["dependencies"] = [p["manifest"]["schedule_ref"].split(":")[-1] + ":" + d for d in node["dependencies"]]
                    def qualify_references(value):
                        if isinstance(value, dict):
                            return {k: (p["manifest"]["schedule_ref"].split(":")[-1] + ":" + v
                                        if k in {"predicate_node", "skipped_node", "decision_node"} and isinstance(v, str)
                                        else qualify_references(v)) for k, v in value.items()}
                        if isinstance(value, list):
                            return [qualify_references(v) for v in value]
                        return value
                    if "detail" in node:
                        node["detail"] = qualify_references(node["detail"])
                node["node_id"] = p["manifest"]["schedule_ref"].split(":")[-1] + ":" + node["node_id"]
                node["scope"] = {k: p["parameters"]["policy"][k] for k in ["agreement_id", "participant_id", "pool_id", "period"]}
            unique(result["trace"], "node_id", "DUPLICATE_TRACE_NODE")
            result["trace_origin"] = trace_origin
        result["diagnostics"] = observed["diagnostics"]
        result["verification"] = {"backend": backend, "reference_agrees": backend in {"compare", "lean"},
                                  "proof_scope": "SPL.Proofs supported expression lowering only; parser/checker/emitter/IO not proved"}
        if observed["status"] == "blocked":
            return publish()
        emissions = observed["emissions"]
        statement = emissions.get("pool", emissions.get("settlement"))
        if not isinstance(statement, dict):
            fail("OUTPUT_SCOPE_REQUIRED", "Profile needs pool or settlement output")
        required = p["parameters"]["policy"]
        for key in ["agreement_id", "participant_id", "period"]:
            if statement.get(key) != required[key]:
                fail("OUTPUT_SCOPE_MISMATCH", key)
        if statement.get("pool_id", statement.get("net_pool_id")) != required["pool_id"]:
            fail("OUTPUT_SCOPE_MISMATCH", "pool")
        if exact(statement["earned"]) < 0 or exact(statement["payable"]) < 0:
            fail("NEGATIVE_RESULT", "Unsupported negative settlement")
        state_by_key = {s["state_key"]: s for s in p["state_cells"]}
        aliases = {a["alias"]: a["state_key"] for a in p["opening_aliases"]}
        opening_decls = {d["name"]: d["alias"] for d in checked.schedule["declarations"] if d["kind"] == "opening"}
        closing = []
        for name, value in observed["closing"].items():
            cell = deepcopy(state_by_key[aliases[opening_decls[name]]])
            opening_quantity = exact(cell["quantity"])
            cell.update(boundary=required["period"]["end"], quantity=value, prior_result_ref="result@sha256:" + semantic)
            cell["movement"] = {"opening": number(opening_quantity), "net_change": number(exact(value) - opening_quantity), "closing": value}
            closing.append(cell)
        mode = p["manifest"]["mode"]
        result.update(status="provisional" if mode == "preview" else ("calculated_zero" if exact(statement["payable"]) == 0 else "calculated"),
                      statements=[{**statement, "currency": "USD", "scenario_id": p["manifest"]["scenario_id"], "run_id": p["manifest"]["run_id"]}],
                      detail=emissions.get("titles", [emissions["comparison"]] if "comparison" in emissions else []),
                      closing_state=closing if mode == "final" else [],
                      reconciliation={"settlement": {"earned": statement["earned"], "payable": statement["payable"],
                                                      "pool_recovered": statement.get("recouped", "0")},
                                      "source_controls": [{"batch_id": b["batch_id"], "controls": b["control_totals"]} for b in p["source_batches"]],
                                      "state": [c["movement"] for c in closing], "amount_spaces_are_separate": True})
        result["result_digest"] = digest({k: v for k, v in result.items() if k not in {"manifest", "result_digest"}})
        if not publication:
            write_json(work / "statement.json", result["statements"])
            write_json(work / "detail.json", result["detail"])
            write_json(work / "trace.json", result["trace"])
            write_json(work / "closing-state.json", result["closing_state"])
            write_json(work / "reconciliation.json", result["reconciliation"])
            write_json(work / "diagnostics.json", result["diagnostics"])
            write_json(work / "result.json", result)
        return publish()
    except DataError as exc:
        result["diagnostics"] = [exc.diagnostic()]
    except SPLException as exc:
        result["diagnostics"] = [d.to_dict() for d in exc.diagnostics]
    except OSError as exc:
        result["diagnostics"] = [{"code": "IO_ERROR", "message": str(exc)}]
    result.update(status="blocked", statements=[], detail=[], closing_state=[], reconciliation={})
    result.pop("result_digest", None)
    return publish()


def carry_state(result):
    """Export canonical next opening cells only from a final successful result."""
    if result["status"] not in {"calculated", "calculated_zero"}:
        fail("NONCONSUMABLE_STATE", "Blocked/preview state cannot be carried")
    return [{k: v for k, v in c.items() if k != "movement"} for c in deepcopy(result["closing_state"])]
