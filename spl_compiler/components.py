"""Conservative dependency planning for existing, individually atomic SPL roots.

Profile completeness is trusted authoring metadata. No profile is inferred from
types, no finance is calculated here, and connected distinct roots are not run
as a pretend transaction.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json
import re
import tempfile

from .artifacts import (ArtifactPublication, PublicationError,
                        _file_hash, _load_completed_bundle, _read_bounded, _strict_json)
from .codecs import DataError, file_digest
from .modules import (_shape, _validate_document, module_identities, resolve_module, SCHEMA_ROOT,
                      run_module_package, validate_module_package)
from .run import identities

REQUEST = "spl-component-request/1"
PLAN = "spl-component-plan/1"
OUTCOMES = "spl-component-outcomes/1"
PUBLICATION = "spl-component-publication/1"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_PLAN_BYTES = 8 * 1024 * 1024
MAX_JOBS = 64
MAX_RESOURCES = 100000
MAX_RESOURCE_KEY_BYTES = 16384


def _need(condition, code):
    if not condition:
        raise DataError(code, code)


def _canonical(value):
    # Preserve original Text, including non-NFC spellings. This is structural
    # identity, not the canonical financial value codec.
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _path(root, locator):
    _need(type(locator) is str and locator and "\\" not in locator and ":" not in locator, "COMPONENT_PATH")
    relative = PurePosixPath(locator)
    _need(not relative.is_absolute() and all(part not in {"", ".", ".."} for part in relative.parts), "COMPONENT_PATH")
    target = Path(root).resolve() / Path(*relative.parts)
    _need(target.resolve().is_relative_to(Path(root).resolve()) and not target.is_symlink(), "COMPONENT_PATH")
    return target


def _reference(root, ref, *, maximum=MAX_FILE_BYTES):
    _need(type(ref) is dict and set(ref) == {"locator", "sha256"} and
          type(ref["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]), "COMPONENT_REFERENCE")
    raw = _read_bounded(_path(root, ref["locator"]), maximum)
    _need(sha256(raw).hexdigest() == ref["sha256"], "COMPONENT_REFERENCE_CHANGED")
    return raw


def _put(root, locator, raw):
    path = _path(root, locator)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _need(path.read_bytes() == raw, "COMPONENT_SNAPSHOT_COLLISION")
    else:
        path.write_bytes(raw)


def _capture(request, registry_root, trusted_profiles, destination):
    """Hash the same bytes copied into the private registry and then consumed."""
    _validate_document(request, "spl-component-request.schema.json")
    _need(len(request["jobs"]) <= MAX_JOBS, "COMPONENT_JOB_LIMIT")
    root, destination = Path(registry_root).resolve(), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    catalog_raw = _read_bounded(Path(trusted_profiles), MAX_PLAN_BYTES)
    catalog = _strict_json(catalog_raw)
    _validate_document(catalog, "spl-dependency-registry.schema.json")
    trusted = {_canonical(ref) for ref in catalog["profiles"]}
    _need(len(trusted) == len(catalog["profiles"]), "COMPONENT_DUPLICATE_PROFILE")
    records, total = [], 0
    jobs = [row["id"] for row in request["jobs"]]
    _need(len(set(jobs)) == len(jobs), "COMPONENT_DUPLICATE_JOB")
    for edge in request["additional_dependencies"]:
        _need(edge["left"] in jobs and edge["right"] in jobs, "COMPONENT_UNKNOWN_JOB")
    for job in sorted(request["jobs"], key=lambda row: row["id"]):
        raw = _reference(root, job["package_ref"])
        total += len(raw)
        _need(total <= MAX_PACKAGE_BYTES, "COMPONENT_PACKAGE_BYTE_LIMIT")
        package = _strict_json(raw)
        resolved = resolve_module(package["module_ref"], root)
        registry = destination / "registry"
        captured = []
        for entry in resolved.closure:
            for kind, expected in [("descriptor", entry["reference"]["sha256"]),
                                   ("source", entry["descriptor"]["source"]["sha256"]),
                                   ("policy", entry["descriptor"]["policy"]["readable"]["sha256"])]:
                source = entry[kind + "_path"]
                payload = _read_bounded(source, MAX_FILE_BYTES)
                _need(sha256(payload).hexdigest() == expected, "COMPONENT_CLOSURE_CHANGED")
                locator = source.relative_to(root).as_posix()
                _put(registry, locator, payload)
                captured.append({"locator": locator, "sha256": expected})
        profile = None
        ref = job.get("dependency_profile_ref")
        if ref is not None and _canonical(ref) in trusted:
            profile_raw = _reference(root, ref, maximum=MAX_PLAN_BYTES)
            profile = _strict_json(profile_raw)
            _validate_document(profile, "spl-component-dependencies.schema.json")
            for selector in profile["selectors"]:
                for path in [selector["rows"], *(field["path"] for field in selector["key"])]:
                    _need(all(type(part) is str or type(part) is int and part >= 0 for part in path), "COMPONENT_SELECTOR_PATH")
            _put(destination / "profiles", ref["locator"], profile_raw)
        _put(destination, "packages/job-" + job["id"] + ".json", raw)
        records.append({"id": job["id"], "package": package,
                        "package_ref": deepcopy(job["package_ref"]), "closure_files": captured,
                        "profile": profile, "profile_ref": deepcopy(ref)})
    _put(destination, "trusted-registry.json", catalog_raw)
    _put(destination, "request.json", (_canonical(request) + "\n").encode("utf-8"))
    return records, sha256(catalog_raw).hexdigest()


def _select(value, path):
    values = [value]
    for part in path:
        selected = []
        for item in values:
            if part == "*":
                _need(type(item) is list, "COMPONENT_SELECTOR_SHAPE")
                selected.extend(item)
            elif type(part) is int:
                _need(type(item) is list and 0 <= part < len(item), "COMPONENT_SELECTOR_SHAPE")
                selected.append(item[part])
            else:
                _need(type(item) is dict and part in item, "COMPONENT_SELECTOR_SHAPE")
                selected.append(item[part])
        values = selected
    return values


def _one(value, path):
    values = _select(value, path)
    _need(len(values) == 1, "COMPONENT_KEY_SHAPE")
    return values[0]


def _derive(request, records, registry_hash, registry):
    resource_jobs, resources, unknown, jobs = {}, {}, [], []
    resource_bytes = 0

    def add(job, kind, namespace, key):
        nonlocal resource_bytes
        resource = {"kind": kind, "namespace": namespace, "key": key}
        encoded = _canonical(resource)
        size = len(encoded.encode("utf-8"))
        _need(size <= MAX_RESOURCE_KEY_BYTES, "COMPONENT_KEY_BYTE_LIMIT")
        if encoded not in resources:
            resource_bytes += size
            _need(resource_bytes <= MAX_PLAN_BYTES, "COMPONENT_RESOURCE_BYTE_LIMIT")
        resources[encoded] = resource
        resource_jobs.setdefault(encoded, set()).add(job)
        _need(len(resources) <= MAX_RESOURCES, "COMPONENT_RESOURCE_LIMIT")

    for record in records:
        package = record["package"]
        resolved = resolve_module(package["module_ref"], registry)
        validate_module_package(package, resolved)
        compiler, runtime = module_identities()
        _need(package["manifest"]["compiler_build"] == compiler and
              package["manifest"]["runtime_build"] == runtime and
              package["manifest"]["module_closure"] == resolved.references, "COMPONENT_BUILD_CHANGED")
        job = record["id"]
        add(job, "pool", "canonical-scope/1", [package["scope"]["agreement_id"], package["scope"]["pool_id"]])
        for cell in package["state_cells"]:
            # Never include period/boundary: the same writer remains shared.
            add(job, "state", "canonical-state-key/1", [cell["state_key"]])
        profile = record["profile"]
        if profile is None:
            unknown.append(job)
        else:
            binding = {"module_ref": resolved.reference, "source_sha256": file_digest(resolved.source_path),
                       "policy_sha256": file_digest(resolved.policy_path), "module_closure": resolved.references}
            _need(_canonical(profile["binding"]) == _canonical(binding), "COMPONENT_PROFILE_OWNER_MISMATCH")
            for selector in profile["selectors"]:
                for row in _select(package, selector["rows"]):
                    key = [_one(row if field["from"] == "row" else package, field["path"])
                           for field in selector["key"]]
                    add(job, selector["kind"], selector["namespace"], key)
        jobs.append({"id": job, "package_ref": record["package_ref"],
                     "dependency_profile_ref": record["profile_ref"],
                     "footprint": "conservative_unknown" if profile is None else "registered_assumption",
                     "closure_files": record["closure_files"]})
    parent = {job["id"]: job["id"] for job in jobs}

    def find(job):
        while parent[job] != job:
            job = parent[job]
        return job

    def join(left, right):
        a, b = sorted((find(left), find(right)))
        parent[b] = a

    shared = []
    for encoded in sorted(resources):
        members = sorted(resource_jobs[encoded])
        for other in members[1:]:
            join(members[0], other)
        shared.append({**resources[encoded], "jobs": members})
    for edge in request["additional_dependencies"]:
        join(edge["left"], edge["right"])
    if unknown:
        for job in jobs[1:]:
            join(jobs[0]["id"], job["id"])
    groups = {}
    for job in jobs:
        groups.setdefault(find(job["id"]), []).append(job)
    components = []
    for group in sorted(groups.values(), key=lambda rows: rows[0]["id"]):
        members = sorted(row["id"] for row in group)
        roots = {row["package_ref"]["sha256"] for row in group}
        components.append({"id": "component-" + _digest(members), "members": members,
                           "root_job": members[0] if len(roots) == 1 else None,
                           "disposition": "ready" if len(roots) == 1 else "coordinator_required"})
    value = {"format": PLAN, "request": deepcopy(request), "trusted_registry_sha256": registry_hash,
             "engine": {"compiler_runtime": list(identities()), "module_runtime": list(module_identities())},
             "jobs": jobs, "resources": shared, "unknown_footprints": sorted(unknown), "components": components}
    _need(len(_canonical(value).encode("utf-8")) <= MAX_PLAN_BYTES, "COMPONENT_PLAN_BYTE_LIMIT")
    return {**value, "plan_digest": _digest(value)}


def plan_components(request, registry_root, *, trusted_profiles):
    """Derive a plan; the separately selected registry is a trust input."""
    request = deepcopy(request)
    with tempfile.TemporaryDirectory(prefix="spl-components-") as folder:
        records, registry_hash = _capture(request, registry_root, trusted_profiles, Path(folder))
        return _derive(request, records, registry_hash, Path(folder) / "registry")


class ComponentPublication(ArtifactPublication):
    format = PUBLICATION


def _verify_snapshot(plan, snapshot):
    _need(type(plan) is dict and plan.get("format") == PLAN, "COMPONENT_PLAN_FORMAT")
    semantic = {key: value for key, value in plan.items() if key != "plan_digest"}
    _need(plan.get("plan_digest") == _digest(semantic), "COMPONENT_PLAN_DIGEST")
    request = _strict_json(_read_bounded(snapshot / "request.json", MAX_PLAN_BYTES))
    _need(_canonical(request) == _canonical(plan["request"]), "COMPONENT_REQUEST_CHANGED")
    catalog_raw = _read_bounded(snapshot / "trusted-registry.json", MAX_PLAN_BYTES)
    _need(sha256(catalog_raw).hexdigest() == plan["trusted_registry_sha256"], "COMPONENT_REGISTRY_CHANGED")
    trusted = {_canonical(ref) for ref in _strict_json(catalog_raw)["profiles"]}
    for job in plan["jobs"]:
        _need(type(job["id"]) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", job["id"]), "COMPONENT_JOB_ID")
        raw = _read_bounded(_path(snapshot, "packages/job-" + job["id"] + ".json"), MAX_FILE_BYTES)
        _need(sha256(raw).hexdigest() == job["package_ref"]["sha256"], "COMPONENT_PACKAGE_CHANGED")
        for ref in job["closure_files"]:
            _reference(snapshot / "registry", ref)
        if job["footprint"] == "registered_assumption":
            _need(_canonical(job["dependency_profile_ref"]) in trusted, "COMPONENT_UNTRUSTED_PROFILE")
            _reference(snapshot / "profiles", job["dependency_profile_ref"], maximum=MAX_PLAN_BYTES)


def run_components(request, plan, registry_root, *, trusted_profiles, output, backend="compare",
                   audit_profile="compact-v2", workers=1):
    """Execute independent atomic roots only; never a multi-root transaction."""
    publication = ComponentPublication(output)
    _need(workers == 1 and type(workers) is int, "COMPONENT_WORKERS_UNSUPPORTED")
    from .compact_execution import require_profile
    require_profile(audit_profile, backend, output)
    request, plan = deepcopy(request), deepcopy(plan)
    snapshot = publication.work / "inputs"
    records, registry_hash = _capture(deepcopy(request), registry_root, trusted_profiles, snapshot)
    fresh = _derive(request, records, registry_hash, snapshot / "registry")
    _need(_canonical(plan) == _canonical(fresh), "COMPONENT_PLAN_CHANGED")
    # No live registry/package/profile reference is used after this boundary.
    jobs = {row["id"]: row for row in records}
    outcomes = []
    for index, component in enumerate(fresh["components"]):
        if component["disposition"] != "ready":
            outcomes.append({"id": component["id"], "members": component["members"], "status": "not_executed",
                             "diagnostics": [{"code": "COMPONENT_COORDINATOR_REQUIRED"}],
                             "diagnostic_codes": ["COMPONENT_COORDINATOR_REQUIRED"],
                             "trace_origin": None, "state_consumable": False})
            continue
        target = publication.work / "components" / f"{index:04d}"
        result = run_module_package(jobs[component["root_job"]]["package"], snapshot / "registry",
                                    backend=backend, artifact_dir=target, audit_profile=audit_profile)
        loaded = _canonical_result(target)
        _need(_canonical(loaded) == _canonical(result), "COMPONENT_RETURN_CHANGED")
        marker = _read_bounded(target / "completion.json", MAX_PLAN_BYTES)
        outcomes.append({"id": component["id"], "members": component["members"], "status": result["status"],
                         "diagnostic_codes": [row["code"] for row in result["diagnostics"]],
                         "trace_origin": result.get("trace_origin"),
                         "completion": {"path": (target / "completion.json").relative_to(publication.root).as_posix(),
                                        "sha256": sha256(marker).hexdigest()},
                         "state_consumable": result["status"] == "calculated" and
                                             result.get("manifest", {}).get("mode") == "final" and
                                             bool(result.get("closing_state"))})
    complete = all(row["status"] in {"calculated", "provisional"} for row in outcomes)
    value = {"format": OUTCOMES, "status": "completed" if complete else "partial", "requested_backend": backend,
             "audit_profile": audit_profile, "workers": workers, "plan": fresh,
             "components": outcomes, "diagnostics": []}
    _verify_snapshot(fresh, snapshot)
    publication.finish(value, {"outcomes.json": "components", "diagnostics.json": "diagnostics"})
    return load_component_outcomes(output)


def _canonical_result(folder):
    marker = _strict_json(_read_bounded(Path(folder) / "completion.json", MAX_PLAN_BYTES))
    _need(type(marker) is dict, "COMPONENT_COMPLETION_FORMAT")
    if marker.get("format") == "spl-artifact-publication/1":
        from .artifacts import load_completed_result
        return load_completed_result(folder)
    if marker.get("format") == "spl-artifact-publication/2":
        from .audited_artifacts import load_completed_audited_result
        return load_completed_audited_result(folder)
    raise PublicationError("COMPONENT_COMPLETION_FORMAT")


def _load_component_outcomes(output):
    """Validate metadata plus each whole component's existing canonical bundle."""
    root = Path(output).resolve()
    result, manifest, marker = _load_completed_bundle(root, publication_format=PUBLICATION)
    # Shape validation deliberately does not add check_text/NFC normalization
    # to already preserved structural resource identities.
    _shape(result, _strict_json(_read_bounded(SCHEMA_ROOT / "spl-component-outcomes.schema.json", MAX_PLAN_BYTES)))
    _need(result.get("format") == OUTCOMES, "COMPONENT_OUTCOMES_FORMAT")
    owned = root / ".runs" / manifest["invocation_id"]
    _verify_snapshot(result["plan"], owned / "inputs")
    planned = result["plan"]["components"]
    _need(type(result["components"]) is list and len(result["components"]) == len(planned), "COMPONENT_OUTCOMES_SHAPE")
    for index, component in enumerate(result["components"]):
        _need(component["trace_origin"] is None or type(component["trace_origin"]) is str, "COMPONENT_TRACE_ORIGIN")
        _need(component["id"] == planned[index]["id"] and component["members"] == planned[index]["members"], "COMPONENT_MEMBERS_CHANGED")
        if "completion" not in component:
            _need(planned[index]["disposition"] == "coordinator_required" and
                  component["status"] == "not_executed" and not component["state_consumable"], "COMPONENT_OUTCOME")
            continue
        _need(planned[index]["disposition"] == "ready", "COMPONENT_COORDINATOR_REQUIRED")
        ref = component["completion"]
        path = _path(root, ref["path"])
        _need(path == owned / "components" / f"{index:04d}" / "completion.json" and
              _file_hash(path) == ref["sha256"], "COMPONENT_COMPLETION_OWNERSHIP")
        value = _canonical_result(path.parent)
        _need(value["status"] == component["status"] and
              component["diagnostic_codes"] == [row["code"] for row in value["diagnostics"]] and
              component["trace_origin"] == value.get("trace_origin") and
              component["state_consumable"] == (value["status"] == "calculated" and value.get("manifest", {}).get("mode") == "final" and bool(value.get("closing_state"))),
              "COMPONENT_OUTCOME_CHANGED")
        child_marker = _strict_json(_read_bounded(path, MAX_PLAN_BYTES))
        consumed = path.parent / ".runs" / child_marker["invocation_id"] / "canonical-package.json"
        if consumed.exists():
            actual = _strict_json(_read_bounded(consumed, MAX_FILE_BYTES))
            expected = _strict_json(_read_bounded(owned / "inputs/packages" / ("job-" + planned[index]["root_job"] + ".json"), MAX_FILE_BYTES))
            _need(_canonical(actual) == _canonical(expected), "COMPONENT_ROOT_INPUT_CHANGED")
        else:
            _need(value["status"] == "blocked" and not value.get("results") and not value.get("closing_state"), "COMPONENT_ROOT_INPUT_REQUIRED")
    complete = all(row["status"] in {"calculated", "provisional"} for row in result["components"])
    _need(result["status"] == ("completed" if complete else "partial"), "COMPONENT_BATCH_STATUS_CHANGED")
    _need(_read_bounded(root / "completion.json", MAX_PLAN_BYTES) == marker, "COMPONENT_PUBLICATION_CHANGED")
    return result


def load_component_outcomes(output):
    """Load only a stable owned component summary and its genuine root bundles."""
    try:
        return _load_component_outcomes(output)
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError) as error:
        raise PublicationError("COMPONENT_OUTCOMES_INVALID: " + str(error)) from error
