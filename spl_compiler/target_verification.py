"""Kernel comparison of a native SPL artifact and a checked source reference.

The source reference uses the independently written Python frontend and Lean
emitter supplied with SPL. Both terms interpret their primitives through the
same Lean runtime. The theorem therefore checks the native translation relative
to that source reference, including lazy demand and error order, without
sampling input values. Correctness of the source reference frontend and
emitter and agreement of shared primitives with the language reference remain
separate obligations.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .codecs import DataError, fail
from .emitter import _list, _pair, _string, emit_module
from .lean_tools import lean


CLAIM = "spl-comparative-target-proof/1"
THEOREMS = ("SPLTranslation.settlement_equivalent", "SPLTranslation.entry_equivalent")


def _lean_type(checked_type):
    if checked_type.name == "Record":
        fields = _list(_pair(key, _lean_type(field)) for key, field in checked_type.fields)
        return f"(.record {fields})"
    arguments = _list(_lean_type(argument) for argument in checked_type.args)
    return f"(.named {_string(checked_type.name)} {arguments})"


def _ports(checked, kind):
    return _list(_pair(decl["name"], _lean_type(checked.types[decl["name"]]))
                 for decl in checked.schedule["declarations"] if decl["kind"] == kind)


def _runner(checked, mode):
    if mode == "series" or (checked.meanings and checked.meanings.features):
        owner = _list(map(_string, checked.admission.features))
        meanings = _list(map(_string, checked.meanings.features))
        runner = "runSeriesWith" if mode == "series" else "runMainWith"
        return (f"SPL.Bindings.{runner} ({{ features := {owner} }} : SPL.Dimensions.Admission) "
                f"({{ features := {meanings} }} : SPL.Dimensions.Meanings)")
    return "SPL.Bindings.runMain"


def _statement(checked, mode):
    inputs = _ports(checked, "input")
    openings = _ports(checked, "opening")
    apply_entry = f"({_runner(checked, mode)} {inputs} {openings})"
    dimension_context = ""
    if checked.meanings and checked.meanings.features:
        schedule_namespace = "GeneratedSPL.S" + "".join(f"_{ord(char)}" for char in checked.schedule["name"])
        dimension_context = f"      unfold {schedule_namespace}._spl_dimension_meanings\n"
    axiom_targets = ", ".join(f"`{name}" for name in THEOREMS)
    return f"""import NativeTarget
import SourceReference
import Lean.Elab.Command
import Lean.Util.CollectAxioms

set_option maxRecDepth 32768
set_option maxHeartbeats 8000000

namespace SPLTranslation

theorem settlement_equivalent : GeneratedSPL.settle = SourceReference.settle := rfl

private def sourceRunner :
    (SPL.Env → SPL.Env → SPL.Eval SPL.Settlement) → List String → IO UInt32 :=
  {apply_entry}

theorem entry_equivalent : main = sourceRunner SourceReference.settle := by
  calc
    main = sourceRunner GeneratedSPL.settle := by
      unfold main sourceRunner
{dimension_context}      with_reducible rfl
    _ = sourceRunner SourceReference.settle := congrArg sourceRunner settlement_equivalent

open Lean Elab Command in
run_cmd do
  for name in [{axiom_targets}] do
    for dependency in (← Lean.collectAxioms name) do
      unless dependency == `propext || dependency == `Quot.sound || dependency == `Classical.choice do
        throwError "Unexpected theorem assumption {{dependency}} in {{name}}"

end SPLTranslation
"""


def _reference(checked):
    # The exported reference has no executable main. Rename only its fixed
    # namespace delimiter lines, leaving authored labels and strings intact.
    return (emit_module(checked)
            .replace("\nnamespace GeneratedSPL\n", "\nnamespace SourceReference\n", 1)
            .replace("\nend GeneratedSPL\n", "\nend SourceReference\n", 1))


def check_target(work, fresh_artifact, checked, *, mode="single"):
    """Check trusted fresh emission in an invocation-owned directory.

    Lean loads imported modules as executable compiler code. The caller supplies
    the result of normal native emission in private staging, never an unchecked
    external Lean file. A caller verifying saved bytes first compares them with
    that fresh emission and executes only its same private snapshot.
    """
    if mode not in {"single", "series"}:
        fail("INVALID_TARGET_MODE", f"Unsupported artifact execution mode {mode!r}")
    work = Path(work).resolve()
    work.mkdir()
    artifact = Path(fresh_artifact).read_bytes()
    reference = _reference(checked).encode("utf-8")
    proof = _statement(checked, mode).encode("utf-8")
    modules = (("NativeTarget", artifact), ("SourceReference", reference))
    for name, content in [*modules, ("TranslationProof", proof)]:
        (work / f"{name}.lean").write_bytes(content)
    options = ["-DwarningAsError=true", f"--root={work}"]
    try:
        for name, _ in modules:
            lean([*options, "-o", work / f"{name}.olean", work / f"{name}.lean"])
        lean([*options, work / "TranslationProof.lean"], search_paths=(work,))
    except DataError as error:
        if error.code in {"LEAN_NOT_FOUND", "LEAN_RESOURCE_LIMIT"}:
            raise
        fail("TARGET_PROOF_FAILED", str(error))
    return {"format": CLAIM, "mode": mode, "theorems": list(THEOREMS),
            "artifact_sha256": sha256(artifact).hexdigest(),
            "reference_sha256": sha256(reference).hexdigest(),
            "proof_sha256": sha256(proof).hexdigest()}
