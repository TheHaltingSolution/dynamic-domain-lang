"""Author the new synthetic registry artifacts; does not calculate answer keys."""
from pathlib import Path

from spl_compiler.codecs import file_digest, write_json


ROOT = Path(__file__).resolve().parents[3]
PREFIX = "cases/modules/priority-rates/"


def typ(name, *args):
    return {"name": name, "args": list(args)}


def build_descriptor():
    def pin(filename):
        return {"locator": PREFIX + filename, "sha256": file_digest(ROOT / PREFIX / filename)}

    def port(name, role, type_, dimensions=(), domain=None):
        return {"name": name, "role": role, "type": type_, "dimensions": list(dimensions), "domain": domain or {}}

    ratio, usd = typ("Ratio"), typ("Money", typ("USD"))
    identity = lambda kind: typ("Id", typ(kind))
    terms = {"minimum": "0", "maximum": "1", "methodology": False}
    ports = [port("agreement", "input", identity("Agreement"), ["agreement"]),
             port("pool", "input", identity("Pool"), ["pool", "purpose"]),
             port("asset", "input", identity("Asset"), ["asset"]),
             port("participant_a", "input", identity("Participant"), ["participant"]),
             port("participant_b", "input", identity("Participant"), ["participant"]),
             port("source_date", "input", typ("Date"), ["period"]),
             port("territory", "input", typ("Text")),
             port("cash", "input", usd, ["currency", "agreement", "asset"], {"minimum": "0"}),
             port("effective", "parameter", typ("Period"), ["period"]),
             *[port(name, "parameter", ratio, domain=terms) for name in ["ordinary_rate", "canada_rate", "share_a", "share_b"]],
             port("competing_canada", "parameter", typ("Bool"), domain={"choices": [False, True], "methodology": True}),
             port("statements", "result", typ("List", typ("ParticipantStatement")),
                  ["agreement", "participant", "pool", "purpose", "asset", "currency"]),
             port("rate_detail", "detail", typ("RateDetail"), ["currency"]),
             port("reconciliation", "reconciliation", typ("Bool"))]
    constraints = []
    for source, target, kind in [("agreement", "agreement_id", "equals"), ("pool", "pool_id", "equals"),
                                  ("asset", "asset_ids", "member_of"), ("participant_a", "participant_ids", "member_of"),
                                  ("participant_b", "participant_ids", "member_of")]:
        constraints.append({"kind": kind, "path": "inputs." + source, "fields": [], "target": "scope." + target, "value": ""})
    return {"schema_version": "spl-module-descriptor/1", "id": "cedar:priority-rates", "revision": "1",
            "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.1",
                              "package": "spl-module/1", "toolchain": "leanprover/lean4:v4.35.0",
                              "codecs": ["spl-exact/1", "spl-instant/1"], "capabilities": ["spl.core/1", "spl.priority/1"]},
            "source": pin("priority-rates.spl"), "imports": [],
            "interface": {"ports": ports, "exports": [], "dictionaries": {}, "schemas": [
                {"name": "ParticipantStatement", "fields": {"agreement_id": identity("Agreement"), "participant_id": identity("Participant"),
                    "pool_id": identity("Pool"), "asset_id": identity("Asset"), "earned": usd}},
                {"name": "RateDetail", "fields": {"rate": ratio, "total": usd}}]},
            "policy": {"id": "cedar:priority-policy", "revision": "1", "readable": pin("policy.md"),
                       "decision_ids": ["CEDAR-PRIORITY"], "evidence_class": "synthetic", "review_status": "proposed",
                       "discriminating_cases": ["US20", "CA40", "FR0", "tie", "no-rule", "effective-end", "two-participants"]},
            "constraints": constraints, "state": []}


def build_package(descriptor_sha):
    return {"profile": "spl-module/1", "module_ref": {"id": "cedar:priority-rates", "revision": "1",
                "locator": PREFIX + "descriptor.json", "sha256": descriptor_sha},
            "manifest": {"run_id": "cedar-priority-CA", "scenario_id": "CEDAR-SYNTHETIC", "mode": "final",
                         "period": {"start": "2026-04-01", "end": "2026-07-01"}, "cutoff": "2026-07-03T00:00:00Z",
                         "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
                         "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
            "scope": {"agreement_id": "cedar-distribution", "participant_ids": ["oak-participant", "pine-participant"],
                      "pool_id": "willow-screen-trust", "purpose": "synthetic-priority-entitlement", "asset_ids": ["cedar-film"]},
            "inputs": {"agreement": "cedar-distribution", "pool": "willow-screen-trust", "asset": "cedar-film",
                       "participant_a": "oak-participant", "participant_b": "pine-participant", "source_date": "2026-05-01",
                       "territory": "CA", "cash": {"value": "100", "currency": "USD"}},
            "parameters": {"effective": {"start": "2026-04-01", "end": "2026-07-01"}, "ordinary_rate": "0.2",
                           "canada_rate": "0.4", "share_a": "0.5", "share_b": "0.5", "competing_canada": False},
            "evidence": {}, "state_cells": [], "decisions": [{"decision_id": "CEDAR-PRIORITY", "policy_id": "cedar:priority-policy",
                "policy_revision": "1", "status": "proposed", "evidence_ref": "cedar-synthetic-policy-selection"}]}


if __name__ == "__main__":
    write_json(ROOT / PREFIX / "descriptor.json", build_descriptor())
    write_json(ROOT / PREFIX / "package.json", build_package(file_digest(ROOT / PREFIX / "descriptor.json")))
