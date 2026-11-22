"""Bounded real-native archival probe; native trace production is unchanged."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.spl_benchmark import receipt_probe, assert_expected
from scripts.spl_trace_transport import Limits, canonical_json, loads, pack, unpack
from spl_compiler.codecs import file_digest, write_json
from spl_compiler.lean_tools import lean_environment
from spl_compiler.run import identities


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--rows', choices=[10, 100], type=int, default=100,
                     help='Bounded probe; larger native audits need a separate resource experiment')
    cli.add_argument('--output', type=Path,
                     default=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/m1-audit-transport'))
    args = cli.parse_args()
    exe = ROOT / '.lake/build/bin' / ('spl.exe' if sys.platform == 'win32' else 'spl')
    if not exe.is_file():
        cli.error('Build the native CLI first: lake build spl')
    folder = args.output / ('receipts-' + str(args.rows))
    folder.mkdir(parents=True, exist_ok=True)
    bindings = folder / 'bindings.json'
    write_json(bindings, receipt_probe(args.rows, 2))
    schedule = ROOT / 'cases/sv/sv01.spl'
    inputs = {'schedule_sha256': file_digest(schedule), 'bindings_sha256': file_digest(bindings),
              'native_executable_sha256': file_digest(exe)}
    before = identities()
    _, env = lean_environment()
    command = [str(exe), 'interpret', str(schedule), str(bindings)]
    started = time.perf_counter()
    process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=180)
    native_seconds = time.perf_counter() - started
    if process.returncode:
        raise SystemExit(process.stderr.decode('utf-8', errors='replace'))
    interpreted = loads(process.stdout)
    assert_expected(interpreted, args.rows)
    trace = interpreted['trace']
    original = canonical_json(trace).encode('utf-8')
    (folder / 'trace.json').write_bytes(original)
    started = time.perf_counter()
    packed = pack(trace, Limits())
    pack_seconds = time.perf_counter() - started
    encoded = canonical_json(packed).encode('utf-8')
    (folder / 'trace-compact.json').write_bytes(encoded)
    started = time.perf_counter()
    restored = unpack(loads(encoded), Limits())
    unpack_seconds = time.perf_counter() - started
    if canonical_json(restored).encode('utf-8') != original:
        raise SystemExit('Logical trace reconstruction differs')
    if identities() != before:
        raise SystemExit('Compiler/runtime changed during the probe')
    if inputs != {'schedule_sha256': file_digest(schedule), 'bindings_sha256': file_digest(bindings),
                  'native_executable_sha256': file_digest(exe)}:
        raise SystemExit('Probe inputs or native binary changed during the measurement')
    result = {'format': 'spl-trace-transport-observation/1', 'rows': args.rows,
        'compiler_build': before[0], 'runtime_build': before[1],
        **inputs, 'command': command,
        'native_build_precondition': 'Run lake build spl first; source/binary correspondence relies on that build, not this source fingerprint check.',
        'native_stdout_bytes': len(process.stdout), 'native_seconds': format(native_seconds, '.6f'),
        'trace_nodes': len(trace), 'trace_edges': sum(len(node['dependencies']) for node in trace),
        'logical_trace_bytes': len(original), 'compact_bytes': len(encoded),
        'bytes_saved': len(original) - len(encoded), 'payloads': len(packed['payloads']),
        'pack_seconds': format(pack_seconds, '.6f'), 'unpack_seconds': format(unpack_seconds, '.6f'),
        'logical_sha256': packed['logical_sha256'], 'exact_roundtrip': True,
        'limitations': ['Post-generation archival compaction only; native emission and its memory are unchanged.',
                        'One bounded receipt-only observation during concurrent validation; no capacity or latency percentile claim.',
                        'Packing and reconstruction still hold expanded Python objects; memory was not measured.']}
    write_json(folder / 'measurement.json', result)
    print('Native nodes: ' + str(result['trace_nodes']) + '; logical bytes: ' + str(len(original)) +
          '; compact bytes: ' + str(len(encoded)) + '; exact roundtrip: passed')


if __name__ == '__main__':
    main()
