"""Reproduce the current C09 two-namespace profile with native publications."""
from __future__ import annotations

import argparse
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def lean_type(value):
    if value["name"] == "Record":
        fields = ", ".join(f"({json.dumps(k)}, {lean_type(v)})" for k, v in value["fields"])
        return f"(.record [{fields}])"
    args = ", ".join(map(lean_type, value.get("args", [])))
    return f"(.named {json.dumps(value['name'])} [{args}])"


def build_python_target(checked, folder):
    from scripts.spl_release_verification import write_json
    from spl_compiler.compact_execution import _compiler_inputs, _stage, _verify_pins
    from spl_compiler.emitter import emit_module

    def declarations(kind):
        rows = (d for d in checked.schedule["declarations"] if d["kind"] == kind)
        return "[" + ", ".join(f"({json.dumps(d['name'])}, {lean_type(d['type'])})" for d in rows) + "]"

    folder.mkdir()
    lean, c, obj, exe, rsp = (folder / ("Candidate" + suffix)
                             for suffix in (".lean", ".c", ".o", ".exe", ".rsp"))
    lean.write_text(
        "import SPL.Bindings\n" + emit_module(checked)
        + "\ndef main (args : List String) : IO UInt32 :=\n  SPL.Bindings.runMain "
        + declarations("input") + " " + declarations("opening") + " GeneratedSPL.settle args\n",
        encoding="utf-8", newline="\n",
    )
    toolbin, flags, libraries, pins = _compiler_inputs()
    rsp.write_text("\n".join(map(json.dumps, [str(obj), *libraries])), encoding="utf-8")
    _stage([toolbin / "lean.exe", "-DwarningAsError=true", "-R", folder, "-c", c, lean],
           folder / "cgen", compiler=True)
    _stage([toolbin / "clang.exe", "-c", "-o", obj, c, *flags], folder / "object", compiler=True)
    _stage([toolbin / "clang.exe", "-o", exe, "@" + str(rsp)], folder / "link", compiler=True)
    _verify_pins(pins)
    write_json(folder / "compiler-pins.json", pins)
    return exe, pins


def namespace_controls(stage, out, first_cells, successors):
    from scripts.spl_release_verification import reject_unless, write_json
    from spl_compiler.audited_artifacts import load_completed_audited_result
    from spl_compiler.modules import bind_module_package, run_module_package

    basis, holdback = first_cells
    reject_unless(basis[0]["scope"] == holdback[0]["scope"], "Namespace fixture scopes differ")
    reject_unless(basis[0]["state_key"] != holdback[0]["state_key"], "Reserve namespaces alias")
    reject_unless({basis[0]["purpose"], holdback[0]["purpose"]} == set(stage.PURPOSES.values()),
                  "Unexpected reserve purposes")
    write_json(out / "namespace-cells.json", first_cells)
    reports = []

    def blocked(name, package, code, *, generic=False):
        folder = out / name
        folder.mkdir()
        write_json(folder / "package.json", package)
        runner = run_module_package if generic else stage.run_reserve_stages_package
        result = runner(package, ROOT, backend="compare", artifact_dir=folder, audit_profile="compact-v2")
        reject_unless(load_completed_audited_result(folder) == result, f"{name}: reload mismatch")
        reject_unless(
            result["status"] == "blocked" and not result["results"] and not result["closing_state"]
            and result["trace"]["status"] == "unavailable" and result["diagnostics"][0]["code"] == code,
            f"{name}: {result['diagnostics']}",
        )
        reports.append({"case": name, "diagnostic": code,
                        "stage": "module admission" if generic else "original/prepared custody"})

    for i, own in enumerate(successors):
        other = successors[1 - i]
        swapped = deepcopy(own)
        swapped["state_cells"] = deepcopy(first_cells[1 - i])
        blocked(f"cells-{i}", swapped, "RS_PREPARED_PACKAGE_MISMATCH")
        swapped = deepcopy(own)
        swapped["module_ref"] = deepcopy(other["module_ref"])
        blocked(f"ref-{i}", swapped, "RS_PREPARED_PACKAGE_MISMATCH")
        swapped["decisions"] = deepcopy(other["decisions"])
        swapped = bind_module_package(swapped, ROOT)
        blocked(f"purpose-{i}", swapped, "MODULE_STATE_PURPOSE", generic=True)
        swapped["state_cells"][0].update(
            purpose=other["state_cells"][0]["purpose"], state_key=other["state_cells"][0]["state_key"],
        )
        blocked(f"descriptor-{i}", swapped, "MODULE_SCOPE_MISMATCH", generic=True)
    invalid = deepcopy(successors[0])
    context = stage.loads(invalid["inputs"]["source_context"])
    context["terms"]["release_schedule"][0]["fraction"] = None
    invalid["inputs"]["source_context"] = stage.context_raw(context)
    blocked("null-original", invalid, "RS_PREPARED_PACKAGE_MISMATCH")
    return reports


def run(out):
    from scripts.spl_release_verification import build_pins, capture, reject_unless, source_pins, write_json
    from Tests.test_reserve_stage_oracle import view
    from oracles.reserve_stages import exact_json, reserve_stages
    from spl_compiler.audited_artifacts import load_completed_audited_result
    from spl_compiler.codecs import canonical, file_digest, read_json
    from spl_compiler.compact_execution import _stage, _verify_pins, checked_head, metadata
    from spl_compiler.lean_tools import LIB, ROOT as lean_root, lean_environment
    from spl_compiler.modules import module_identities, resolve_module, validate_module_package

    stage = import_module("cases.reserve-stages.build_modules")
    reject_unless(stage.ROOT == lean_root == ROOT and LIB == ROOT / ".lake/build/lib/lean",
                  "Wrong compiler or registration root")
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] in {"Tests", "cases", "oracles", "spl_compiler"} and getattr(module, "__file__", None):
            reject_unless(Path(module.__file__).resolve().is_relative_to(ROOT), f"Wrong module origin: {name}")
    reject_unless(capture("git", "status", "--porcelain") == "", "Use a clean private checkout")
    reject_unless(not out.is_relative_to(ROOT), "Choose a new short output path outside the checkout")
    before, compiled = source_pins(ROOT), build_pins(ROOT)
    lean, env = lean_environment()
    version = capture(lean, "--version")
    expected_version = (ROOT / "lean-toolchain").read_text().strip().split(":v")[-1]
    reject_unless(f"version {expected_version}," in version, "Wrong Lean version")
    reject_unless(bool(compiled), "Build the pinned Lake targets before running")
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "pins.json", {
        "commit": capture("git", "rev-parse", "HEAD"), "lean": version, "lean_path": env["LEAN_PATH"],
        "identities": module_identities(), "source": before, "build": compiled,
    })
    pack = read_json(stage.FOLDER / "neutral.json")["scenarios"]
    first_cells, successors, observations = {}, {}, []
    python_target = None
    source_closure = None
    for scenario, case in pack.items():
        previous, cells = None, None
        for position in range(len(case["frames"])):
            data = view(case, position, previous)
            if cells:
                data["prior_result"]["result_ref"] = cells[0]["prior_result_ref"]
            expected = exact_json(reserve_stages(data))
            modes = ["final", "preview"] if position == len(case["frames"]) - 1 else ["final"]
            for mode in modes:
                template = stage.FOLDER / (scenario.replace("_", "-") + "-canonical-package.json")
                reference = read_json(template)["module_ref"]
                package = stage.reserve_stages_package(data, reference=reference, state_cells=cells, mode=mode)
                module = resolve_module(reference, ROOT)
                checked, _, _ = validate_module_package(package, module)
                closure = checked.schedule
                if python_target is None:
                    python_target, pins = build_python_target(checked, out / "py")
                    source_closure = closure
                reject_unless(closure == source_closure, "Stage methods use different checked programs")
                folder = out / f"{len(observations):02}"
                folder.mkdir()
                write_json(folder / "original.json", data)
                write_json(folder / "package.json", package)
                write_json(folder / "oracle.json", expected)
                result = stage.run_reserve_stages_package(
                    package, ROOT, backend="compare", artifact_dir=folder, audit_profile="compact-v2",
                )
                reject_unless(load_completed_audited_result(folder) == result, f"{scenario}: reload mismatch")
                status = "calculated" if mode == "final" else "provisional"
                reject_unless(result["status"] == status and result["issuance_status"] == "unissued",
                              f"{scenario}: {result['diagnostics']}")
                reject_unless(stage.neutral_result(result["results"]["comparison"]) ==
                              {k: v for k, v in expected.items() if k != "closing_state"}, scenario)
                closing = result["closing_state"]
                if mode == "final":
                    reject_unless(len(closing) == 1 and
                                  stage.neutral_state(closing[0]["quantity"]) == expected["closing_state"],
                                  f"{scenario}: closing state mismatch")
                    next_cells = deepcopy(closing)
                    for cell in next_cells:
                        cell.pop("movement")
                    if scenario.endswith("_stage") and position == 0:
                        first_cells[scenario] = next_cells
                    if scenario.endswith("_stage") and position == 1:
                        successors[scenario] = package
                else:
                    reject_unless(not closing, f"{scenario}: preview carries state")
                invocation = read_json(folder / "completion.json")["invocation_id"]
                native = folder / ".runs" / invocation
                target = _stage([python_target, native / "bindings.json"], folder / "py")
                reject_unless(
                    canonical(checked_head(metadata(target), checked))
                    == canonical(checked_head(metadata(native / "target-process/stdout.bin"), checked)),
                    f"{scenario}: independent emitted target mismatch",
                )
                observations.append({"folder": folder.name, "scenario": scenario, "period": position,
                                     "mode": mode, "status": status, "trace": result["trace"],
                                     "python_output_sha256": file_digest(target)})
                write_json(out / "progress.json", observations)
                print(f"{scenario} period {position + 1} {mode} passed", flush=True)
            previous, cells = expected, next_cells
    distinct = ("basis_reserve_stage", "producer_holdback_stage")
    blocked = namespace_controls(stage, out, [first_cells[k] for k in distinct], [successors[k] for k in distinct])
    _verify_pins(pins)
    reject_unless(before == source_pins(ROOT) and compiled == build_pins(ROOT)
                  and capture("git", "status", "--porcelain") == "", "Frozen sources or build drifted")
    write_json(out / "verification.json", {"status": "passed", "publications": observations, "blocked": blocked})


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New short output directory")
    args = parser.parse_args()
    destination = args.output.resolve()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    run(destination)
