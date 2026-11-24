"""Qualification preflight controls; no benchmark/native execution credit."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.spl_compact_publication_probe import qualify_baseline, BASE_COMPILER, BASE_RUNTIME, probe
from spl_compiler.codecs import file_digest


class CompactProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Source.spl"
        self.source.write_bytes(b"source bytes\n")
        (self.root / "neutral-original.json").write_text('{"original":"bytes"}', encoding="utf-8")
        (self.root / "audit-00").mkdir()
        self.wire = self.root / "audit-00/stdout.bin"
        self.wire.write_bytes(b"pinned wire\n")
        self.report = {"status": "passed", "unchanged_dependency_pins": True,
                       "kernel_identities": [BASE_COMPILER, BASE_RUNTIME], "seed": 7,
                       "counts": {"raw_original_records": 100}, "implementation": "legacy",
                       "transport": "compact-v2", "required_audit_completed": True,
                       "native_samples": [{"status": "passed", "trace_validation": {
                           "transport_sha256": file_digest(self.wire), "wire_bytes": self.wire.stat().st_size}}]}

    def qualify(self, value):
        path = self.root / "summary.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return qualify_baseline(path, 100, 7, self.source, b'{"original":"bytes"}')

    def test_current_baseline_identity_and_every_gate_must_match(self):
        self.assertEqual(self.qualify(self.report)[0], self.report)
        for field, changed in (("status", "failed"), ("unchanged_dependency_pins", False),
                               ("kernel_identities", ["old20ea", BASE_RUNTIME]), ("seed", 8),
                               ("required_audit_completed", False), ("transport", "compact-v1"),
                               ("implementation", "indexed"), ("native_samples", [])):
            value = deepcopy(self.report)
            value[field] = changed
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.qualify(value)

    def test_changed_original_input_and_wire_are_rejected(self):
        (self.root / "neutral-original.json").write_text('{"original":"changed"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_ORIGINAL_INPUT"):
            self.qualify(self.report)
        (self.root / "neutral-original.json").write_text('{"original":"bytes"}', encoding="utf-8")
        self.wire.write_bytes(b"changed wire\n")
        with self.assertRaisesRegex(ValueError, "WIRE_CHANGED"):
            self.qualify(self.report)

    def test_no_10k_probe_or_implicit_host_load_assumption(self):
        for records, note in ((10000, "known load"), (100, "")):
            with self.subTest(records=records), self.assertRaises(ValueError):
                probe(self.root / "forbidden", records=records, baseline=self.root / "summary.json", host_load_note=note)
            self.assertFalse((self.root / "forbidden").exists())

    def test_actual_original_fact_projection_reaches_canonical_boundary(self):
        # Real generator/oracle/binding/source-opening projection. Only the
        # following native execution boundary is replaced; no backend credit.
        from scripts import spl_compact_publication_probe as runner
        with patch.object(runner, "qualify_baseline", return_value=({}, {})), \
             patch.object(runner, "run_package", side_effect=RuntimeError("PREPARATION_COMPLETED")):
            result = probe(self.root / "preparation", records=100, baseline=self.root / "summary.json", host_load_note="preflight only")
        self.assertEqual(result["stages"]["oracle_before_projection"]["status"], "passed")
        self.assertEqual(result["stages"]["projection"]["status"], "passed")
        self.assertEqual(result["error"]["message"], "PREPARATION_COMPLETED")
