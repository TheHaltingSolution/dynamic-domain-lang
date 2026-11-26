"""Check comparative certificates for the tracked case corpus.

Run from the checkout root after the pinned Lake build with
`python -m scripts.spl_verification_census --output REPORT.json`.
Each passing kernel claim covers all decoded inputs for its selected artifact.
The finite selection measures certificate availability for this corpus.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import tempfile

from spl_compiler.certification import PILOT, default_link
from spl_compiler.codecs import DataError, file_digest, loads, read_json, write_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import linking_manifest, resolve_module
from spl_compiler.verification import certify


def _tracked(pattern):
    paths = subprocess.check_output(["git", "ls-files", "-z", "--", pattern], cwd=ROOT)
    return [Path(name) for name in paths.decode("utf-8").split("\0") if name]


def _catalog():
    registered = {}
    for descriptor_path in _tracked("cases/**/*.json"):
        payload = (ROOT / descriptor_path).read_bytes()
        if b'"spl-module-descriptor/1"' not in payload:
            continue
        descriptor = loads(payload)
        if not isinstance(descriptor, dict) or descriptor.get("schema_version") != "spl-module-descriptor/1":
            continue
        source = Path(descriptor["source"]["locator"])
        registered[descriptor_path] = source
    registered_sources = set(registered.values())
    standalone = {path: path for path in _tracked("cases/**/*.spl") if path not in registered_sources}
    return sorted((registered | standalone).items(), key=lambda item: item[0].as_posix())


def _check(item, mode):
    selector, relative = item
    source = ROOT / relative
    record = {"selector": selector.as_posix(), "source": relative.as_posix()}
    try:
        manifest = None
        if selector != relative:
            descriptor_path = ROOT / selector
            descriptor = read_json(descriptor_path)
            ref = {"id": descriptor["id"], "revision": descriptor["revision"],
                   "locator": selector.as_posix(), "sha256": file_digest(descriptor_path)}
            manifest = linking_manifest(resolve_module(ref, ROOT))
            record["descriptor_sha256"] = ref["sha256"]
        elif source.parent == PILOT:
            manifest = default_link()

        with tempfile.TemporaryDirectory(prefix="spl-census-") as temporary:
            work = Path(temporary)
            link = None
            if manifest and (manifest["imports"] or manifest["modules"]):
                link = work / "Link.json"
                write_json(link, manifest)
            receipt = certify(source, work / "certificate", link=link, mode=mode)
        return {**record, "status": "checked", "receipt": receipt}
    except DataError as error:
        return {**record, "status": "blocked", "diagnostic": error.diagnostic()}
    except (OSError, ValueError, RecursionError) as error:
        return {**record, "status": "blocked", "diagnostic": {"code": type(error).__name__, "message": str(error)}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--mode", choices=("single", "series"), default="single")
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs expects a positive worker count")
    items = _catalog()
    if not items:
        parser.error("No tracked SPL selectors were found")
    with ThreadPoolExecutor(max_workers=args.jobs) as workers:
        observed = list(workers.map(lambda item: _check(item, args.mode), items))
    blocked = [row for row in observed if row["status"] == "blocked"]
    write_json(args.output, {"format": "spl-verification-census/1", "mode": args.mode,
                            "coverage": "tracked case registrations and unregistered case sources",
                            "checked": len(observed) - len(blocked), "blocked": len(blocked),
                            "observations": observed})
    for row in blocked:
        print(row["selector"], row["diagnostic"]["code"])
    print(f"Checked {len(observed) - len(blocked)} of {len(observed)} case selectors")
    return int(bool(blocked))


if __name__ == "__main__":
    raise SystemExit(main())
