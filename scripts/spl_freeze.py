"""Preserve a runnable source baseline before a disclosed language extension."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ["SPL", "spl_compiler", "oracles", "Tests", "cases", "Demos", "schemas",
                "Participation", "Generated", "docs", "scripts", ".github", ".vscode"]
SUFFIXES = {".lean", ".py", ".md", ".json", ".spl", ".csv", ".toml", ".yml", ".yaml", ".ps1", ".cmd", ".txt"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_files():
    files = {p for name in SOURCE_ROOTS for p in (ROOT / name).rglob('*')
             if p.is_file() and p.suffix.lower() in SUFFIXES and '__pycache__' not in p.parts}
    files.update(p for p in ROOT.iterdir() if p.is_file() and
                 (p.suffix.lower() in SUFFIXES or p.name in {'lean-toolchain', '.gitattributes', '.gitignore'}))
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--checks', required=True, type=Path, help='Completed verification record, not predicted results')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--absence-probe', type=Path, help='Executed unsupported-capability probe to preserve with E0')
    args = parser.parse_args()
    if not args.name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-' for c in args.name):
        parser.error('name must be a simple artifact label')
    checks = json.loads(args.checks.read_text(encoding='utf-8'))
    folder = args.output / args.name
    if folder.exists():
        raise SystemExit('Freeze destination already exists; preserve it and choose a new identity')
    files = source_files()
    payloads = {path.relative_to(ROOT).as_posix(): path.read_bytes() for path in files}
    probe = json.loads(args.absence_probe.read_text(encoding='utf-8')) if args.absence_probe else {}
    if probe:
        if (probe.get('status') != 'blocked' or not probe.get('diagnostics') or
                probe['diagnostics'][0].get('code') != 'UNSUPPORTED_BUILTIN'):
            raise SystemExit('Absence probe does not establish an unsupported source operation')
        if sha(payloads[probe['source']]) != probe['source_sha256']:
            raise SystemExit('Absence probe source changed before freeze')
        if any(sha(payloads[path]) != fingerprint for path, fingerprint in probe['compiler_source_pins'].items()):
            raise SystemExit('Compiler source changed after the absence probe')
    folder.mkdir(parents=True)
    archive = folder / 'source.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for relative, content in payloads.items():
            # Fixed archive timestamp makes bytes independent of host file mtimes.
            entry = zipfile.ZipInfo(relative, date_time=(2026, 11, 21, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(entry, content)
    pins = {relative: sha(content) for relative, content in payloads.items()}
    with zipfile.ZipFile(archive) as zipped:
        assert {name: sha(zipped.read(name)) for name in zipped.namelist()} == pins
    manifest = {'format': 'spl-source-freeze/1', 'name': args.name,
        'source_tree_sha256': sha(json.dumps(pins, sort_keys=True, separators=(',', ':')).encode('utf-8')),
        'archive_sha256': sha(archive.read_bytes()), 'source_files': pins,
        'toolchain': payloads['lean-toolchain'].decode('utf-8').strip(), 'verification': checks,
        'absence_probe': probe,
        'deliberate_omission': 'Unsupported operation recorded by the executed probe; supplied Date facts remain supported.' if probe else 'No capability omission asserted by this freeze.',
        'experiment': 'Disclosed engineering extension; no unseen held-out or domain-approval claim.',
        'reproduce': ['Extract source.zip into a new workspace.', 'Install the pinned Lean toolchain and Python 3.12+.',
                      'Run lake build, lake exe smoke, lake exe spl_smoke.',
                      'Run python scripts/spl_check.py (pins imports to the extracted checkout).',
                      'Use the documented fixture builders to bind a deliberate new local run; keep the frozen packages unchanged.']}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print(str(folder.resolve()))
    print('Frozen files: ' + str(len(pins)) + '; tree SHA-256 ' + manifest['source_tree_sha256'])


if __name__ == '__main__':
    main()
