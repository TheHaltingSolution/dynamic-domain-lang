"""Typed, explicitly synthetic mechanism demos, separate from final case profiles.

These inputs select scenario authority. They are not new canonical run profiles
or an adapter for historical obligations, payments or contractual reserve bases.
"""
from pathlib import Path

from .checker import check_schedule
from .codecs import DataError, canonical, digest, fail, file_digest, loads, write_json
from .evaluator import evaluate
from .lean_tools import ROOT, compile_schedule, export_ir, interpret_schedule, lean
from .parser import parse
from .run import normalize_target

CASES = {"advance-issues", "reserve-vintage", "correction-payments"}


def run_mechanism(case, bindings, *, artifact_dir=None):
    if case not in CASES:
        fail("UNSUPPORTED_MECHANISM", case)
    source = ROOT / "cases/mechanisms" / (case + ".spl")
    checked = check_schedule(parse(source.read_text(encoding="utf-8"), source.name))
    if not isinstance(bindings, dict) or set(bindings) != {"inputs", "openings"}:
        fail("INVALID_BINDING_ENVELOPE", "Expected inputs and openings")
    reference = evaluate(checked, bindings["inputs"], bindings["openings"]).to_dict()
    work = Path(artifact_dir) if artifact_dir else ROOT / ".lake/mechanisms" / digest({"case": case, "bindings": bindings})
    work.mkdir(parents=True, exist_ok=True)
    write_json(work / "bindings.json", bindings)
    export_ir(source, work / "typed-ir.json")
    interpreted = normalize_target(interpret_schedule(source, work / "bindings.json"))
    target = compile_schedule(source, work / "Settlement.lean")
    native = normalize_target(loads(lean(["--run", target, work / "bindings.json"])))
    for other in [reference, interpreted]:
        for field in ["status", "emissions", "closing"]:
            if canonical(native[field]) != canonical(other[field]):
                fail("MECHANISM_DIFFERENTIAL_MISMATCH", case + ": " + field)
        if [d["code"] for d in native["diagnostics"]] != [d["code"] for d in other["diagnostics"]]:
            fail("MECHANISM_DIFFERENTIAL_MISMATCH", case + ": diagnostics")
    result = {**native, "trace": interpreted["trace"], "trace_origin": interpreted["trace_origin"],
              "trace_format": interpreted["trace_format"], "scenario_class": "synthetic_mechanism",
              "issuance_status": "unissued", "state_consumption": "typed_mechanism_only",
              "source_sha256": file_digest(source), "binding_digest": digest(bindings)}
    write_json(work / "result.json", result)
    return result
