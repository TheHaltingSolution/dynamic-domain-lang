"""Rebuild the bounded synthetic review bundles; Python stdlib only."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spl_compiler.adapter import rq07
from spl_compiler.codecs import exact, file_digest, number, write_json
from spl_compiler.fixtures import lg_package, sv_package
from spl_compiler.run import bind_package, identities, project, run_package
from spl_compiler.schema import SCHEMA
from spl_compiler.mechanisms import run_mechanism
from spl_compiler.codecs import read_json


def main():
    cli = argparse.ArgumentParser()
    external = Path("C:/Projects/Film_TV_participation_dynamic_DSL/artifacts")
    cli.add_argument("--output", type=Path, default=external / "spl/research-reconciliation" if external.parent.exists() else ROOT / ".lake/spl/research-review")
    cli.add_argument("--refresh-snapshots", action="store_true")
    cli.add_argument("--skip-baseline", action="store_true", help="Compatibility flag: skip the legacy review record; this helper never publishes the implementation baseline")
    args = cli.parse_args()
    cases = [
        ("sv", "cases/sv/sv01.spl", sv_package(), {"earned": "33000", "recouped": "15000", "payable": "18000"}),
        ("lg", "cases/lg/lg01.spl", lg_package(), {"earned": "35", "payable": "35"}),
        ("rq07", "cases/sv/rq07.spl", rq07(ROOT / "cases/rq07/source", observed_at="2026-04-03T00:00:00Z", ingested_at="2026-11-20T00:00:00Z"),
         {"earned": "33000", "recouped": "15000", "payable": "18000"}),
    ]
    cases += [(name + "-readable", source.replace(".spl", "-readable.spl"), package, expected)
              for name, source, package, expected in list(cases)]
    summaries = []
    for name, source, package, expected in cases:
        package = bind_package(package, ROOT / source)
        result = run_package(package, ROOT / source, artifact_dir=args.output / name)
        if result["status"] != "calculated" or any(result["statements"][0][k] != v for k, v in expected.items()):
            raise SystemExit(f"{name} failed independent acceptance: {result['diagnostics']}")
        print(name + ": payable " + result["statements"][0]["payable"] + "; native/reference agree")
        summaries.append({"case": name, "semantic_run_digest": result["semantic_run_digest"], "result_digest": result["result_digest"],
                          "independent_expected": expected, "statement": result["statements"][0], "artifact_subdirectory": name})
        if args.refresh_snapshots:
            base_name = name.removesuffix("-readable")
            folder = ROOT / "cases" / base_name
            if name.endswith("-readable"):
                folder = folder / "readable"
            generated_name = {"sv": "SV", "lg": "LG", "rq07": "RQ07"}[base_name] + ("Readable" if name.endswith("-readable") else "")
            generated_target = ROOT / "Demos" / (generated_name + ".lean")
            generated_target.parent.mkdir(parents=True, exist_ok=True)
            generated_target.write_text((args.output / name / "Settlement.lean").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            write_json(folder / "canonical-package.json", package)
            inputs, openings, *_ = project(package)
            if base_name in {"sv", "rq07"}:
                openings = {"prepayment": next(iter(openings.values()))}
            else:
                aliases = {"lg/work-D/true-cash/cumulative-gross": "gate_gross", "lg/work-D/true-cash/cumulative-cost": "gate_cost", "synthetic/work-D/payment-holdback": "payment_holdback"}
                openings = {aliases[k]: v for k, v in openings.items()}
            write_json(folder / "bindings.json", {"inputs": inputs, "openings": openings})
            for filename, field in [("statement", "statements"), ("closing-state", "closing_state"), ("lineage", "source_to_target_lineage")]:
                write_json(folder / (filename + ".json"), result[field])
        if name == "rq07":
            c = {b["batch_id"]: exact(b["control_totals"][0]["signed_total"]) for b in package["source_batches"]}
            eligible = sum(exact(t["allowed_cost"]) for t in result["detail"])
            actual = {"billed": c["raw_invoice_lines"], "uncollected": c["raw_invoice_lines"] - c["raw_bank_receipts"],
                      "bank_cash": c["raw_bank_receipts"], "applications": c["raw_cash_applications"],
                      "allocated_title_receipts": sum(exact(t["cash"]) for t in result["detail"]),
                      "raw_gl_cost": c["raw_cost_lines"], "eligible_cost": eligible, "excluded_cost": c["raw_cost_lines"] - eligible,
                      "separate_funding": c["raw_acquisition_funding"], **{k: exact(result["statements"][0][k]) for k in ["earned", "recouped", "payable"]},
                      "closing_prepayment": exact(result["closing_state"][0]["quantity"])}
            expected_controls = {"billed": 210000, "uncollected": 50000, "bank_cash": 160000, "applications": 160000,
                                 "allocated_title_receipts": 160000, "raw_gl_cost": 17500, "eligible_cost": 15500, "excluded_cost": 2000,
                                 "separate_funding": 150000, "earned": 33000, "recouped": 15000, "payable": 18000, "closing_prepayment": 0}
            comparison = {k: {"expected": str(v), "actual": number(actual[k]), "matches": actual[k] == v} for k, v in expected_controls.items()}
            if not all(x["matches"] for x in comparison.values()):
                raise SystemExit("RQ-07 independent control comparison failed")
            write_json(args.output / name / "control-comparison.json", comparison)
            if args.refresh_snapshots:
                write_json(ROOT / "cases/rq07/control-comparison.json", comparison)
    write_json(args.output / "summary.json", summaries)
    mechanism_summaries = []
    checkpoints = {"advance-issues": ("advances", "closing_balance", "5000"),
                   "reserve-vintage": ("reserve_ledger", "closing_balance", "20"),
                   "correction-payments": ("obligation_reconciliation", "remaining_obligation", "10")}
    for name, (port, field, expected) in checkpoints.items():
        result = run_mechanism(name, read_json(ROOT / "cases/mechanisms" / (name + "-bindings.json")),
                               artifact_dir=args.output / "mechanisms" / name)
        if result["status"] != "calculated" or result["emissions"][port][field] != expected:
            raise SystemExit("Mechanism independent checkpoint failed: " + name)
        mechanism_summaries.append({"case": name, "scenario_class": result["scenario_class"],
                                    "emissions": result["emissions"], "closing": result["closing"],
                                    "source_sha256": result["source_sha256"], "binding_digest": result["binding_digest"],
                                    "expected_checkpoint": {field: expected}})
        print(name + ": " + field + " " + expected + "; all three execution paths agree")
    write_json(args.output / "mechanisms-summary.json", mechanism_summaries)
    if args.refresh_snapshots:
        write_json(ROOT / "schemas/spl-bounded-package.schema.json", SCHEMA)
        write_json(ROOT / "cases/mechanisms/results-summary.json", mechanism_summaries)
        if args.skip_baseline:
            print("Review bundle: " + str(args.output.resolve()))
            return
        files = (sorted((ROOT / "docs/spl").glob("*.md")) + sorted((ROOT / "docs/spl/policies").glob("*"))
                 + sorted(p for p in (ROOT / "cases").rglob("*") if p.is_file() and p.suffix in {".spl", ".json", ".csv"})
                 + sorted((ROOT / "Demos").glob("*.lean"))
                 + [ROOT / "lean-toolchain", ROOT / "schemas/spl-bounded-package.schema.json", Path(__file__).resolve()])
        implementation, runtime = identities()
        pinned = {str(p.relative_to(ROOT)).replace("\\", "/"): file_digest(p) for p in files}
        # A legacy-only review must never replace the broader release record.
        write_json(args.output / "legacy-review.json", {
            "format": "spl-legacy-review/1", "readable_surface": "spl-readable/0.1-dev",
            "ir_format": "spl-ir/0.1", "trace_format": "spl-trace-dag/0.1", "date": "2026-11-21", "toolchain": "leanprover/lean4:v4.35.0",
            "compiler_wrapper_reference_build": implementation, "runtime_build": runtime,
            "scope": "Readable and original SV/RQ-07/LG, whole-program typed IR, native audit; separately labelled advance/correction/reserve mechanism cases",
            "trace_origin": "native_ir_interpreter, compared with emitted execution and independent Python reference",
            "pinned_files": pinned,
            "source_scenario_sha256": file_digest(ROOT / "cases/rq07/source/scenario.json"), "cases": summaries,
            "mechanisms": mechanism_summaries,
            "release_coverage": "Legacy subset only. See docs/spl/implementation-baseline.json for the separately issued implementation release record."})
    print("Review bundle: " + str(args.output.resolve()))


if __name__ == "__main__":
    main()
