"""Retain actual three-period canonical settlement carry and neutral controls."""
from copy import deepcopy
from fractions import Fraction
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cases.settlement.build_modules import FOLDER, neutral_state, register_settlement, settlement_package, run_settlement_package
from oracles.settlement_adjustments import exact_json, settlement_adjustments
from spl_compiler.codecs import exact, write_json


def successor(previous, result, *, third=False):
    """Transport actual state; new event amounts are supplied synthetic facts."""
    data = deepcopy(previous)
    suffix = "q3" if third else "q2"
    data["case_id"] = "settlement-" + suffix
    data["period"] = {"start": "2026-07-01" if third else "2026-04-01", "end": "2026-10-01" if third else "2026-07-01"}
    data["cutoff"] = "2026-10-03T00:00:00Z" if third else "2026-07-03T00:00:00Z"
    date = "2026-09-29" if third else "2026-06-29"
    source_id = "source-" + suffix
    common = {"scope": deepcopy(data["scope"]), "observed_at": date + "T12:00:00Z", "source_ref": "synthetic-" + suffix, "evidence_ref": source_id}
    data["earned"] = [{**common, "id": "earned-" + suffix, "amount": "20" if third else "10", "effective_date": date}]
    data["issued"], data["payments"], data["applications"] = [], [], []
    if third:
        data["issued"] = [{**common, "id": "issue-q3", "amount": "27", "issued_date": date}]
        data["payments"] = [{**common, "id": "payment-q3", "amount": "20", "paid_date": date}]
        data["applications"] = [{**common, "id": "application-q3-" + target, "payment_id": "payment-q3", "issued_id": target, "amount": "10"}
                                for target in ["issue-q1", "issue-q3"]]
    data["evidence"] = [row for row in data["evidence"] if row["kind"] != "complete_settlement_population"]
    data["evidence"] += [{"id": source_id, "kind": "synthetic_source_record", "scope": deepcopy(data["scope"]), "observed_at": date + "T12:00:00Z"},
                         {"id": "complete-" + suffix, "kind": "complete_settlement_population", "scope": deepcopy(data["scope"]), "period": deepcopy(data["period"]), "observed_at": ("2026-10-02" if third else "2026-07-02") + "T13:00:00Z"}]
    cells = [{k: deepcopy(v) for k, v in cell.items() if k != "movement"} for cell in result["closing_state"]]
    data["opening_state"] = neutral_state(cells[0]["quantity"])
    data["prior_result"] = {"source_case_id": previous["case_id"], "period": deepcopy(previous["period"]),
                            "closing_state": deepcopy(data["opening_state"]), "result_ref": cells[0]["prior_result_ref"]}
    return data, cells


def verify(result, control):
    if result["status"] != "calculated":
        raise ValueError(str(result["diagnostics"]))
    for key, actual in result["results"]["comparison"].items():
        expected = control[key]
        if (exact(actual) if isinstance(expected, Fraction) else actual) != expected:
            raise ValueError("Independent control mismatch: " + key)
    if neutral_state(result["closing_state"][0]["quantity"]) != exact_json(control["closing_state"]):
        raise ValueError("Independent closing-state mismatch")
    for actual, expected in zip(result["results"]["obligations"], control["obligations"], strict=True):
        for key, value in expected.items():
            if (exact(actual[key]) if isinstance(value, Fraction) else actual[key]) != value:
                raise ValueError("Independent obligation mismatch: " + key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    reference = register_settlement()
    files = [Path(__file__).resolve(), FOLDER / "build_modules.py", ROOT / "oracles/settlement_adjustments.py",
             *[FOLDER / name for name in ["amounts.spl", "settlement.spl", "policy.md", "amounts-module.json", "settlement-module.json"]]]
    pins = {}
    for path in files:
        payload = path.read_bytes()
        relative = path.relative_to(ROOT).as_posix()
        pins[relative] = hashlib.sha256(payload).hexdigest()
        target = args.output / "source-freeze" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    data = json.loads((FOLDER / "neutral.json").read_text(encoding="utf-8"))
    cells, rows = None, []
    for index in range(3):
        work = args.output / f"period-{index + 1}"
        write_json(work / "neutral.json", data)
        control = settlement_adjustments(data)
        write_json(work / "independent-control.json", exact_json(control))
        package = settlement_package(data, reference=reference, state_cells=cells)
        write_json(work / "canonical-package.json", package)
        result = run_settlement_package(package, ROOT, backend="compare", artifact_dir=work)
        verify(result, control)
        rows.append({"case_id": data["case_id"], "new_eligible_due": result["results"]["comparison"]["new_eligible_due"],
                     "closing_unpaid": result["results"]["comparison"]["closing_unpaid"], "status": "passed", "artifact": work.name})
        if index < 2:
            data, cells = successor(data, result, third=index == 1)
    changed = [name for name, pin in pins.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != pin]
    write_json(args.output / "summary.json", {"status": "failed" if changed else "passed", "backend": "compare", "cases": rows,
        "source_pins": pins, "changed_sources": changed,
        "scope": "Synthetic supplied withholding, original issued obligations and actual payments; no tax applicability or payment execution."})
    if changed:
        raise ValueError("Source changed during the review: " + str(changed))
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
