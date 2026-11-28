"""Review, approve, certify and run the bounded Readable SPL royalties profile."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile

from . import certification
from .artifacts import ArtifactPublication, PublicationError, _atomic_bytes, load_completed_result
from .codecs import DataError, amount, canonical, digest, exact, fail, loads, money, number, read_json
from .lean_tools import ROOT, interpret_schedule, lean


FIXTURES = ROOT / "cases/certification"
PROFILE = "spl-royalties-tool/1"
SOURCE = "agreement.spl"
REVIEW = "review.json"
APPROVAL = "approval.json"
COMPILED = "compiled.json"
MAX_RECEIPT_BYTES = 65536


def _write(path, value):
    _atomic_bytes(path, (canonical(value) + "\n").encode("utf-8"))


def _receipt_bytes(path):
    with Path(path).open("rb") as stream:
        payload = stream.read(MAX_RECEIPT_BYTES + 1)
    if len(payload) > MAX_RECEIPT_BYTES:
        fail("RECEIPT_RESOURCE_LIMIT", "The receipt file exceeds 64 KiB")
    return payload


def _receipts(package):
    if type(package) is not dict or set(package) != {"receipts"}:
        fail("EXPECTED_RECEIPTS", "Supply one receipts array", "/receipts")
    rows = package["receipts"]
    if type(rows) is not list or len(rows) != 2:
        fail("EXPECTED_TWO_RECEIPTS", "Supply two receipt records", "/receipts")
    values, ids = [], set()
    for index, row in enumerate(rows):
        pointer = f"/receipts/{index}"
        if type(row) is not dict or set(row) != {"id", "amount"}:
            fail("INVALID_RECEIPT", "Each receipt needs an id and an exact USD amount", pointer)
        identifier = row["id"]
        if type(identifier) is not str or not identifier or not identifier.isascii():
            fail("INVALID_RECEIPT_ID", "Receipt id must be nonempty ASCII text", pointer + "/id")
        if identifier in ids:
            fail("DUPLICATE_RECEIPT_ID", "Original receipt ids must be distinct", pointer + "/id")
        ids.add(identifier)
        try:
            value = exact(row["amount"], pointer + "/amount")
            values.append((identifier, number(value), value))
        except DataError:
            raise
        except ValueError as exc:
            fail("RECEIPT_RESOURCE_LIMIT", str(exc), pointer + "/amount")
    return values


def _originals(values):
    return [{"id": identifier, "amount": amount} for identifier, amount, _ in values]


def _example(values, profile):
    """Independent worked example using exact fractions and Python half-even."""
    shares = [value / 2 for _, _, value in values]
    rounded_cents = {"aggregate": round(sum(shares) * 100),
                     "row": sum(round(share * 100) for share in shares)}
    return {"receipts": _originals(values), "exact_shares": [money(share) for share in shares],
            "half_even_usd_cents": rounded_cents,
            "interpreted_participation": money(exact(str(rounded_cents[profile])) / 100)}


def _admit(receipts_file):
    admission = loads(lean(["-DwarningAsError=true", "--run", ROOT / "SPL/RoyaltiesAdmission.lean", receipts_file]))
    if admission["status"] == "blocked":
        code = admission["diagnostics"][0]["code"]
        pointer = "/receipts/1/id" if code == "DUPLICATE_RECEIPT_ID" else "/receipts"
        fail(code, "Original receipt ids must be distinct" if code == "DUPLICATE_RECEIPT_ID"
             else "Supply two original IDs and their exact USD amounts", pointer)
    bindings = admission["bindings"]
    try:
        values = [amount(bindings["inputs"][name]) for name in ("first_receipt", "second_receipt")]
        originals = [(identifier, number(value), value)
                     for identifier, value in zip(admission["receipt_ids"], values, strict=True)]
    except DataError:
        raise
    except ValueError as exc:
        fail("RECEIPT_RESOURCE_LIMIT", str(exc), "/receipts")
    return bindings, originals


def _draft(workspace):
    source = Path(workspace) / SOURCE
    try:
        with source.open("rb") as stream:
            draft = stream.read(certification.MAX_SOURCE_BYTES + 1)
    except FileNotFoundError:
        fail("DRAFT_REQUIRED", f"Initialize the workspace with {SOURCE}")
    if len(draft) > certification.MAX_SOURCE_BYTES:
        fail("DRAFT_RESOURCE_LIMIT", "The draft exceeds the certification source limit")
    return draft


def _review(source, profile, link_sha256, examples):
    return {"profile": PROFILE, "rounding_point": profile,
            "source_sha256": sha256(source).hexdigest(),
            "linked_policy_manifest_sha256": link_sha256,
            "terms": {"currency": "USD", "share": "0.5", "rounding": "half_even",
                      "quantum": "0.01", "opening_state": "none", "policy": "money-rounding@1"},
            "examples": examples}


def init(workspace, *, rounding="aggregate"):
    if rounding not in {"aggregate", "row"}:
        fail("UNSUPPORTED_ROUNDING_POINT", str(rounding))
    source = FIXTURES / f"{rounding}-readable.spl"
    certification.identify(source)
    workspace = Path(workspace)
    workspace.mkdir(parents=True)
    _atomic_bytes(workspace / SOURCE, source.read_bytes())
    return {"status": "draft", "source": str(workspace / SOURCE), "rounding_point": rounding}


def preview(workspace, samples):
    workspace = Path(workspace)
    source = _draft(workspace)
    if not samples:
        fail("SAMPLE_REQUIRED", "Provide at least one worked example for review")
    with tempfile.TemporaryDirectory(prefix="spl-review-") as directory:
        work = Path(directory)
        authored = work / SOURCE
        authored.write_bytes(source)
        profile = certification.identify(authored)
        manifest = canonical(certification.default_link()).encode("utf-8")
        link = work / "Link.json"
        link.write_bytes(manifest)
        examples = []
        for sample in samples:
            payload = _receipt_bytes(sample)
            staged = work / "receipts.json"
            _atomic_bytes(staged, payload)
            admitted_bindings, admitted = _admit(staged)
            values = _receipts(loads(payload))
            if values != admitted:
                fail("PREVIEW_ADMISSION_MISMATCH", "The admitted receipt identities or amounts differ from the sample")
            example = _example(values, profile)
            bindings = work / "bindings.json"
            _write(bindings, admitted_bindings)
            outcome = interpret_schedule(authored, bindings, link=link)
            observed = _calculation(outcome)["results"]["participation"]
            if observed != example["interpreted_participation"]:
                fail("PREVIEW_RECONCILIATION", "The SPL preview and independent worked example differ")
            example["interpreted_participation"] = observed
            examples.append(example)
    review = _review(source, profile, sha256(manifest).hexdigest(), examples)
    if _draft(workspace) != source:
        fail("DRAFT_CHANGED", "The draft changed while preparing its review")
    _write(workspace / REVIEW, review)
    return {"status": "preview", "review_sha256": digest(review), **review}


def _validate_review(workspace, review):
    source = _draft(workspace)
    link_sha256 = digest(certification.default_link())
    if (type(review) is not dict or review.get("source_sha256") != sha256(source).hexdigest()
            or review.get("linked_policy_manifest_sha256") != link_sha256):
        fail("STALE_REVIEW", "Source or linked policy changed after preview")
    profile = certification.identify(workspace / SOURCE)
    samples = review.get("examples")
    if type(samples) is not list or not samples or any(type(example) is not dict for example in samples):
        fail("INVALID_REVIEW", "Review must include its worked examples")
    examples = [_example(_receipts({"receipts": item.get("receipts")}), profile) for item in samples]
    if review != _review(source, profile, link_sha256, examples) or _draft(workspace) != source:
        fail("STALE_REVIEW", "The review differs from the current draft, policy, or worked examples")
    return source


def approve(workspace, review_sha256):
    workspace = Path(workspace)
    try:
        review = read_json(workspace / REVIEW)
    except FileNotFoundError:
        fail("REVIEW_REQUIRED", "Preview the draft with worked examples first")
    _validate_review(workspace, review)
    current = digest(review)
    if review_sha256 != current:
        fail("REVIEW_DIGEST_MISMATCH", "Approve the exact review shown to the participant")
    approval = {"profile": PROFILE, "review_sha256": current}
    _write(workspace / APPROVAL, {**approval, "review": review})
    return {"status": "approved", **approval}


def _approved(workspace):
    try:
        approval = read_json(workspace / APPROVAL)
    except FileNotFoundError:
        fail("APPROVAL_REQUIRED", "Record explicit participant approval before compilation or execution")
    if type(approval) is not dict or set(approval) != {"profile", "review_sha256", "review"} or approval["profile"] != PROFILE:
        fail("INVALID_APPROVAL", "The approval record is invalid")
    source = _validate_review(workspace, approval["review"])
    current = digest(approval["review"])
    if approval["review_sha256"] != current:
        fail("INVALID_APPROVAL", "The approval does not match its reviewed draft and examples")
    return source, current


def compile_approved(workspace):
    workspace = Path(workspace).resolve()
    source, review_sha256 = _approved(workspace)
    builds = workspace / "builds"
    builds.mkdir(exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix="build-", dir=builds))
    _atomic_bytes(build / SOURCE, source)
    identity = certification.certify(build / SOURCE, build / "Settlement.lean", build / "certificate.json")
    if _approved(workspace) != (source, review_sha256):
        fail("STALE_APPROVAL", "The approval changed while certifying the artifact")
    record = {"profile": PROFILE, "source_sha256": sha256(source).hexdigest(), "build": build.name}
    _write(workspace / COMPILED, record)
    return {"status": "certified", **record, "review_sha256": review_sha256, "certificate": identity}


def _compiled(workspace, source):
    try:
        record = read_json(workspace / COMPILED)
    except FileNotFoundError:
        fail("CERTIFICATE_REQUIRED", "Compile the approved draft first")
    if type(record) is not dict or set(record) != {"profile", "source_sha256", "build"} or record["profile"] != PROFILE:
        fail("INVALID_BUILD_RECORD", "The compiled workspace record is invalid")
    if record["source_sha256"] != sha256(source).hexdigest():
        fail("STALE_CERTIFICATE", "Compile and certify the current approval")
    name = record["build"]
    if type(name) is not str or re.fullmatch(r"build-[a-z0-9_]+", name) is None:
        fail("INVALID_BUILD_RECORD", "The compiled build directory is invalid")
    build = workspace / "builds" / name
    try:
        if (build / SOURCE).read_bytes() != source:
            fail("CERTIFIED_DRAFT_MISMATCH", "Compiled source differs from the approved draft")
    except FileNotFoundError:
        fail("CERTIFICATE_REQUIRED", "The compiled source is missing")
    return build


def run(workspace, receipts, output):
    workspace = Path(workspace).resolve()
    publication = ArtifactPublication(output)
    result = {"profile": PROFILE, "status": "blocked", "results": {}, "closing_state": [],
              "diagnostics": [], "issuance_status": "unissued"}
    try:
        source, review_sha256 = _approved(workspace)
        build = _compiled(workspace, source)
        receipts_file = publication.work / "receipts.json"
        receipt_payload = _receipt_bytes(receipts)
        _atomic_bytes(receipts_file, receipt_payload)
        admitted_bindings, inputs = _admit(receipts_file)
        bindings = publication.work / "bindings.json"
        _write(bindings, admitted_bindings)
        authored = publication.work / SOURCE
        _atomic_bytes(authored, source)
        outcome = certification.run_certified(authored, build / "Settlement.lean",
                                              build / "certificate.json", bindings, include_certificate=True)
        result.update(_calculation(outcome))
        result.update(review_sha256=review_sha256, receipts=_originals(inputs), certificate=outcome["certificate"])
    except (ValueError, OSError, RecursionError) as exc:
        result["diagnostics"] = [_diagnostic(exc)]
    return publication.finish(result, {"closing-state.json": "closing_state", "diagnostics.json": "diagnostics"})


def _calculation(outcome):
    if outcome.get("status") == "blocked" and outcome.get("diagnostics"):
        diagnostic = outcome["diagnostics"][0]
        fail(diagnostic["code"], diagnostic.get("message", "SPL blocked the calculation"))
    if (outcome.get("status") != "calculated" or set(outcome.get("emissions", {})) != {"participation"}
            or outcome.get("closing") != {} or outcome.get("diagnostics") != []):
        fail("UNEXPECTED_SETTLEMENT_OUTCOME", "The certified calculation returned an unexpected outcome")
    participation = outcome["emissions"]["participation"]
    try:
        value = money(exact(participation))
    except DataError:
        raise
    except ValueError as exc:
        fail("RESULT_RESOURCE_LIMIT", str(exc))
    return {"status": "calculated", "results": {"participation": value}}


def reload(output):
    result = load_completed_result(output)
    if result.get("profile") != PROFILE:
        fail("UNSUPPORTED_RESULT_PROFILE", "Expected a royalties tool publication")
    return result


def _diagnostic(error):
    if isinstance(error, DataError):
        return error.diagnostic()
    if isinstance(error, PublicationError):
        code = str(error).split(":", 1)[0]
    elif isinstance(error, OSError):
        code = "IO_ERROR"
    else:
        code = "ROYALTIES_RESOURCE_LIMIT"
    return {"code": code, "message": str(error)}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m spl_compiler.royalties")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("init", help="Start a new workspace from a supported Readable SPL draft")
    command.add_argument("workspace", type=Path)
    command.add_argument("--rounding", choices=["aggregate", "row"], default="aggregate")
    command = commands.add_parser("preview", help="Show independently calculated examples for participant review")
    command.add_argument("workspace", type=Path)
    command.add_argument("samples", nargs="+", type=Path)
    command = commands.add_parser("approve", help="Record an explicit approval of the exact review shown")
    command.add_argument("workspace", type=Path)
    command.add_argument("review_sha256")
    commands.add_parser("compile", help="Compile and certify the approved draft").add_argument("workspace", type=Path)
    command = commands.add_parser("run", help="Check the certificate and calculate from a fresh receipt file")
    command.add_argument("workspace", type=Path)
    command.add_argument("receipts", type=Path)
    command.add_argument("output", type=Path)
    commands.add_parser("reload", help="Read a completed publication").add_argument("output", type=Path)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    handlers = {"init": init, "preview": preview, "approve": approve,
                "compile": compile_approved, "run": run, "reload": reload}
    try:
        result = handlers[command](**args)
    except (ValueError, PublicationError, OSError, RecursionError) as exc:
        result = {"status": "blocked", "diagnostics": [_diagnostic(exc)]}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return int(result["status"] == "blocked")


if __name__ == "__main__":
    raise SystemExit(main())
