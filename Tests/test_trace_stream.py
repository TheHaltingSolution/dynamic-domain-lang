"""Streaming transport preserves complete legacy native interpreter JSON."""
import os
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.spl_benchmark import receipt_probe
from spl_compiler.codecs import canonical, loads, write_json
from spl_compiler.lean_tools import ROOT, lean_environment
from scripts.spl_native_trace_transport import NativeLimits, read_compact
from scripts.spl_mixed_benchmark import validate_profile
from scripts.spl_trace_transport import TransportError, canonical_json


HEADER = 'schedule StreamCheck language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


def raw_top_level_value(raw, field):
    """Locate an actual JSON value byte span without reserializing its strings."""
    text, decoder = raw.decode("utf-8"), json.JSONDecoder()
    position = text.index("{") + 1
    while True:
        while text[position].isspace() or text[position] == ",":
            position += 1
        if text[position] == "}":
            raise AssertionError("Missing native output field: " + field)
        key, position = decoder.raw_decode(text, position)
        while text[position].isspace():
            position += 1
        if text[position] != ":":
            raise AssertionError("Malformed native output object")
        position += 1
        while text[position].isspace():
            position += 1
        start = position
        _, position = decoder.raw_decode(text, position)
        if key == field:
            return text[start:position].encode("utf-8")


class TraceStreamTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        suffix = ".exe" if os.name == "nt" else ""
        self.frontend = ROOT / ".lake/build/bin" / ("spl" + suffix)
        self.stream = self.frontend.with_name("spl_trace_stream" + suffix)
        self.assertTrue(self.stream.is_file(), "Build lake build spl_trace_stream first")
        _, self.env = lean_environment()

    def compare(self, source, bindings, link=None):
        link_args = ["--link", str(link)] if link else []
        legacy = subprocess.run([str(self.frontend), "interpret", str(source), str(bindings), *link_args],
                                cwd=ROOT, env=self.env, capture_output=True, timeout=30)
        streamed = subprocess.run([str(self.stream), str(source), str(bindings), *link_args],
                                  cwd=ROOT, env=self.env, capture_output=True, timeout=30)
        self.assertEqual(streamed.returncode, legacy.returncode, streamed.stderr)
        self.assertEqual(streamed.stderr, b"")
        self.profile_pair(source, bindings, [], link_args, streamed)
        self.assertEqual(canonical(loads(streamed.stdout)), canonical(loads(legacy.stdout)))
        original = loads(legacy.stdout)
        for flag, version in (("--compact", "0.1"), ("--compact-v2", "0.2")):
            compact = subprocess.run([str(self.stream), str(source), str(bindings), flag, *link_args],
                                     cwd=ROOT, env=self.env, capture_output=True, timeout=30)
            self.assertEqual(compact.returncode, legacy.returncode, compact.stderr)
            self.assertEqual(compact.stderr, b"")
            profile = self.profile_pair(source, bindings, [flag], link_args, compact)
            if "trace" in original:
                compact_path = self.work / ("compact-" + version + ".jsonl")
                compact_path.write_bytes(compact.stdout)
                restored = read_compact(compact_path, reconstruct=True)
                self.assertEqual(restored["format"], "spl-native-trace-stream/" + version)
                self.assertEqual(restored["outcome"], original)
                self.assertEqual(restored["expanded_trace_bytes"], len(raw_top_level_value(legacy.stdout, "trace")))
                self.assertEqual(restored["logical_sha256"], hashlib.sha256(canonical_json(original["trace"]).encode()).hexdigest())
                if restored["node_count"]:
                    validate_profile(profile, restored["node_count"], restored["payload_count"])
            else:
                self.assertEqual(loads(compact.stdout), original)
        return loads(streamed.stdout)

    def profile_pair(self, source, bindings, flags, link_args, baseline):
        profiled = subprocess.run([str(self.stream), str(source), str(bindings), *flags, "--profile-stages", *link_args],
                                  cwd=ROOT, env=self.env, capture_output=True, timeout=30)
        self.assertEqual(profiled.returncode, baseline.returncode, profiled.stderr)
        self.assertEqual(profiled.stdout, baseline.stdout, "profiling must preserve exact native wire bytes")
        # Missing files are handled by the outer exception path and produce no
        # complete profile. A resource/IO failure must never receive completion.
        if not source.exists():
            self.assertEqual(profiled.stderr, b"")
            return None
        profile = loads(profiled.stderr)
        self.assertEqual(profile["format"], "spl-native-audit-profile/1")
        self.assertEqual(profile["status"], "completed" if profiled.returncode == 0 else "blocked")
        return profile

    def fragment(self, body, inputs=None):
        source = self.work / "Source.spl"
        source.write_text(HEADER + body + "}", encoding="utf-8")
        bindings = self.work / "bindings.json"
        write_json(bindings, {"inputs": inputs or {}, "openings": {}})
        return self.compare(source, bindings)

    def test_full_receipt_graphs_match_legacy_at_empty_and_ten_rows(self):
        for rows in (0, 10):
            with self.subTest(rows=rows):
                bindings = self.work / "bindings.json"
                write_json(bindings, receipt_probe(rows, 2))
                result = self.compare(ROOT / "cases/sv/sv01.spl", bindings)
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")
                self.assertTrue(result["trace"])

    def test_lazy_branch_zero_and_complete_discarded_graph_match(self):
        result = self.fragment('define x = if true then 0 else 1.0 / 0.0; emit "x" = x;')
        self.assertTrue(any(n["status"] == "not_evaluated" for n in result["trace"]))
        result = self.fragment('emit "first" = 1; emit "second" = 1.0 / 0.0;')
        self.assertTrue(any(n["kind"] == "emit" and n["status"] == "discarded" for n in result["trace"]))
        self.assertEqual(result["emissions"], {})

    def test_selection_tie_and_binding_failure_match(self):
        result = self.fragment('define x = choose unique { when true => 1; when true => 2; }; emit "x" = x;')
        self.assertEqual(result["diagnostics"][0]["code"], "AMBIGUOUS_RULE")
        source = self.work / "Source.spl"
        source.write_text(HEADER + 'input x: Bool; emit "x" = x;}', encoding="utf-8")
        bindings = self.work / "bindings.json"
        bindings.write_text('{"inputs":{},"openings":{},"unknown":1}', encoding="utf-8")
        result = self.compare(source, bindings)
        self.assertEqual(result["trace"], [])

    def test_frontend_and_invalid_link_diagnostics_match(self):
        source = self.work / "Source.spl"
        bindings = self.work / "bindings.json"
        write_json(bindings, {"inputs": {}, "openings": {}})
        source.write_text(HEADER + 'define x = USD 1 * USD 2;}', encoding="utf-8")
        self.compare(source, bindings)
        source.write_text(HEADER + 'emit "x" = 1;}', encoding="utf-8")
        link = self.work / "links.json"
        link.write_text('{', encoding="utf-8")
        self.compare(source, bindings, link)

    def test_valid_linked_library_readable_source_and_io_error_match(self):
        from Tests.test_linking import importing, library

        source = self.work / "Source.spl"
        source.write_text(HEADER + 'emit "x"=compute(3);}', encoding="utf-8")
        bindings = self.work / "bindings.json"
        write_json(bindings, {"inputs": {}, "openings": {}})
        module = library("arithmetic", 'input a:Int; define result=a+2;',
                         parameters=[{"name": "a", "type": {"name": "Int", "args": []}}])
        link = self.work / "links.json"
        write_json(link, {"modules": [module], "imports": [importing("arithmetic")]})
        result = self.compare(source, bindings, link)
        self.assertEqual(result["status"], "calculated")
        self.compare(ROOT / "cases/sv/sv01-readable.spl", ROOT / "cases/sv/readable/bindings.json")
        self.compare(self.work / "missing.spl", bindings)

    def test_compact_opaque_ref_strings_unicode_and_control_escaping_match(self):
        text = 'opaque $ref inline shared payloads \\" / café 雪 \n\t\u0000' + "x" * 400
        # SPL's JSON-compatible quoted string retains these literal user values;
        # transport wrappers must never interpret keys/words inside the value.
        result = self.fragment('define x=' + json.dumps(text, ensure_ascii=False) + '; emit "first"=x; emit "second"=x;')
        self.assertEqual(result["status"], "calculated")

    def test_profile_flag_is_single_and_incomplete_timings_cannot_receive_credit(self):
        source = self.work / "Source.spl"
        source.write_text(HEADER + 'emit "x"=1;}', encoding="utf-8")
        bindings = self.work / "bindings.json"
        write_json(bindings, {"inputs": {}, "openings": {}})
        process = subprocess.run([str(self.stream), str(source), str(bindings), "--compact-v2", "--profile-stages"],
                                 cwd=ROOT, env=self.env, capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        wire = self.work / "wire.jsonl"
        wire.write_bytes(process.stdout)
        result, profile = read_compact(wire), loads(process.stderr)
        validate_profile(profile, result["node_count"], result["payload_count"])
        mutations = [lambda p: p.update(status="blocked"), lambda p: p.update(clock_pairs=0),
                     lambda p: p["intervals"].pop(), lambda p: p["intervals"].append(p["intervals"][0]),
                     lambda p: p["intervals"][0].update(elapsed_ns=True),
                     lambda p: p["intervals"][0].update(elapsed_ns=p["run_elapsed_ns"] + 1),
                     lambda p: p["empty_clock_probe"].update(pair_span_ns=p["empty_clock_probe"]["elapsed_ns"] + 1)]
        for mutate in mutations:
            changed = deepcopy(profile)
            mutate(changed)
            with self.assertRaises(ValueError):
                validate_profile(changed, result["node_count"], result["payload_count"])
        duplicate = subprocess.run([str(self.stream), str(source), str(bindings), "--profile-stages", "--profile-stages"],
                                   cwd=ROOT, env=self.env, capture_output=True, timeout=30)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertEqual(loads(duplicate.stdout)["diagnostics"][0]["code"], "USAGE")
        self.assertEqual(duplicate.stderr, b"")

    def test_complete_node_json_matches_frozen_legacy_fact_collection(self):
        """Use public Value/Node directly; no persistent .olean is produced."""
        source = self.work / "FactIdEquivalence.lean"
        source.write_text(r'''import SPL
open Lean SPL

private partial def oldFactIds : Value → List String
  | .obj fields => fields.flatMap fun (name, value) =>
      (match name, value with | "fact_id", .text id => [id] | _, _ => []) ++ oldFactIds value
  | .seq values | .tuple values | .map values => values.flatMap oldFactIds
  | .present value => oldFactIds value
  | _ => []

-- Frozen complete formatter from before the optimization, not projected answers.
private def oldNodeJson (node : Trace.Node) : Json := Json.mkObj ([
  ("node_id", .str node.id), ("kind", .str node.kind), ("rule_id", .str node.rule),
  ("instance_scope", .str node.scope), ("value_type", IR.typeJson node.valueType),
  ("fact_ids", toJson (((node.operands ++ node.result.toList).flatMap oldFactIds).eraseDups.mergeSort (· ≤ ·))),
  ("source_span", Json.mkObj [("start", toJson node.span.start), ("stop", toJson node.span.stop),
    ("line", toJson node.span.line), ("column", toJson node.span.column)]),
  ("status", .str node.status),
  ("outcome", .str (if node.status == "not_evaluated" then "not_evaluated"
    else if node.status == "failed" then "blocked"
    else if node.status == "discarded" then "discarded"
    else match node.result with
      | some (.num value) | some (.quantity _ value) | some (.rate _ _ value) =>
        if value == 0 then "calculated_zero" else "calculated"
      | some _ => "calculated" | none => "decision")),
  ("dependencies", toJson node.dependencies), ("operands", .arr (node.operands.map valueJson).toArray)] ++
  (node.citation.toList.map fun citation => ("citation", .str citation)) ++
  (node.result.toList.map fun result => ("result", valueJson result)) ++
  (if node.detail == .null then [] else [("detail", node.detail)]))

private def nested : Value := .obj [
  ("fact_id", .text "z"), ("alias", .text "fact_id"),
  ("nested", .seq [
    .obj [("fact_id", .text "a"), ("fact_id", .text "z")],
    .tuple [.present (.obj [("fact_id", .text "é"), ("fact_id", .text "雪")])],
    .map [.obj [("key", .text "ignored"), ("fact_id", .text "")]],
    .present (.obj [("fact_id", .text "control\n\t\"")]),
    .obj [("fact_id", .num 42), ("nested", .absent)]])]

def main : IO Unit := do
  let base : Trace.Node := {
    id := "opaque-ref", kind := "reference", rule := "rule", scope := "scope",
    span := { start := 3, stop := 12, line := 2, column := 7 }, citation := some "source",
    valueType := .list (.atom "Text"), dependencies := ["prior-1", "prior-2"],
    operands := [nested], result := some nested,
    detail := Json.mkObj [("predicate_node", .str "prior-1"), ("id", .str "not-a-fact")] }
  let expected := ["", "a", "control\n\t\"", "z", "é", "雪"]
  unless ((Trace.nodeJson base).getObjValAs? (List String) "fact_ids").toOption == some expected do
    throw (IO.userError "nested exact fact identities changed")
  let values : List Value := [nested, .seq [nested, nested], .tuple [nested, .absent],
    .map [nested], .present nested, .absent, .text "not-a-fact", .num 0,
    .quantity "ticket" 0, .rate "ticket" "USD" 1, .instant 0 "2026-01-01T00:00:00Z", .flag false,
    .obj [("fact_id", .text "only-result")], .obj [("fact_id", .flag true)]]
  for status in ["evaluated", "failed", "not_evaluated", "discarded", "passed"] do
    for value in values do
      for operands in [[], [value], [nested, value, nested], [value, nested]] do
        for result in [none, some value] do
          let node := { base with status, operands, result }
          let actual := Trace.nodeJson node
          let expected := oldNodeJson node
          unless actual == expected && actual.compress == expected.compress do
            throw (IO.userError "full old/new node JSON mismatch")
  IO.println "Complete legacy node JSON equivalence passed"
''', encoding="utf-8")
        lean, env = lean_environment()
        process = subprocess.run([lean, "--run", str(source)], cwd=ROOT, env=env,
                                 capture_output=True, timeout=60)
        self.assertEqual(process.returncode, 0, process.stdout.decode("utf-8", errors="replace") + process.stderr.decode("utf-8", errors="replace"))
        self.assertIn(b"Complete legacy node JSON equivalence passed", process.stdout)
        self.assertFalse(source.with_suffix(".olean").exists())


class NativeCompactReaderTests(unittest.TestCase):
    def records(self):
        payload = [{"$ref": "opaque", "inline": {"shared": None}, "value": "x" * 300}]
        nodes = [{"node_id": "n0", "dependencies": [], "kind": "literal", "status": "evaluated", "result": payload},
                 {"node_id": "n1", "dependencies": ["n0"], "kind": "emit", "status": "evaluated", "result": payload}]
        head = {"status": "calculated", "emissions": {}, "closing": {}, "diagnostics": [],
                "trace_origin": "native_ir_interpreter", "trace_format": "spl-trace-dag/0.1"}
        records = [{"record": "header", "format": "spl-native-trace-stream/0.1", "logical_format": "spl-trace-dag/0.1", "head": head},
                   {"record": "payload", "id": "p0", "value": payload}]
        records += [{"record": "node", "inline": {k: v for k, v in node.items() if k != "result"}, "shared": {"result": "p0"}} for node in nodes]
        records += [{"record": "complete", "node_count": 2, "payload_count": 1, "expanded_bytes": len(canonical_json(nodes).encode())}]
        return records, nodes

    def read(self, records, **kwargs):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "wire.jsonl"
            path.write_bytes(b"".join(canonical_json(r).encode() + b"\n" for r in records))
            return read_compact(path, **kwargs)

    def test_complete_summary_hash_and_bounded_deep_reconstruction(self):
        records, nodes = self.records()
        summary = self.read(records)
        self.assertNotIn("outcome", summary)
        self.assertEqual(summary["node_count"], 2)
        self.assertEqual(summary["edge_count"], 1)
        self.assertEqual(summary["logical_sha256"], hashlib.sha256(canonical_json(nodes).encode()).hexdigest())
        reconstructed = self.read(records, reconstruct=True)["outcome"]["trace"]
        self.assertEqual(reconstructed, nodes)
        reconstructed[0]["result"][0]["value"] = "changed"
        self.assertEqual(reconstructed[1]["result"][0]["value"], "x" * 300)
        with self.assertRaisesRegex(TransportError, "RECONSTRUCTION_BYTE_LIMIT"):
            self.read(records, reconstruct=True, limits=NativeLimits(max_reconstruction_bytes=100))

    def test_closed_records_references_completion_dag_and_budgets_reject_tampering(self):
        base, _ = self.records()
        variants = [base[:-1], base + [base[-1]], [base[0], base[2], base[1], *base[3:]]]
        changes = [lambda r: r[1].update(id="p1"),
                   lambda r: r[0].update(format="spl-native-trace-stream/99"),
                   lambda r: r[0]["head"].update(trace_format="wrong-logical-format"),
                   lambda r: r[3]["inline"].update(node_id="n0"),
                   lambda r: r[2]["inline"].update(dependencies=["n1"]),
                   lambda r: r[2]["shared"].update(result="missing"),
                   lambda r: r[2]["shared"].update(custom="p0"),
                   lambda r: r[2]["inline"].update(result=None),
                   lambda r: r[-1].update(node_count=3),
                   lambda r: r[-1].update(expanded_bytes=1),
                   lambda r: r[-1].update(extra=True),
                   lambda r: r[2]["inline"].update(detail={"predicate_node": "n0"}),
                   lambda r: r.insert(2, deepcopy(r[1]))]
        for change in changes:
            changed = deepcopy(base)
            change(changed)
            variants.append(changed)
        unused = deepcopy(base)
        unused.insert(-1, {"record": "payload", "id": "p1", "value": "unused"})
        unused[-1]["payload_count"] = 2
        variants.append(unused)
        for records in variants:
            with self.subTest(records=records), self.assertRaises(TransportError):
                self.read(records)
        for limits in (NativeLimits(max_expanded_bytes=10), NativeLimits(max_payload_bytes=10),
                       NativeLimits(max_input_bytes=100), NativeLimits(max_nodes=1), NativeLimits(max_record_bytes=100),
                       NativeLimits(max_depth=2)):
            with self.subTest(limits=limits), self.assertRaises(TransportError):
                self.read(base, limits=limits)
        with self.assertRaisesRegex(TransportError, "FILE_HASH_MISMATCH"):
            self.read(base, expected_sha256="0" * 64)

    def test_strict_json_duplicate_keys_nonfinite_tokens_and_truncation_rejected(self):
        bad = [b'{"record":"header","record":"header"}\n', b'{"record":"payload","value":NaN}\n',
               b'{"record":"payload","value":1.0}\n', b'{"record":"header"}', b'\n']
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.jsonl"
            for raw in bad:
                path.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(TransportError):
                    read_compact(path)

    def test_reader_cli_summarizes_without_expansion_and_checks_external_file_hash(self):
        records, _ = self.records()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "wire.jsonl"
            raw = b"".join(canonical_json(r).encode() + b"\n" for r in records)
            path.write_bytes(raw)
            command = [sys.executable, str(ROOT / "scripts/spl_native_trace_transport.py"), str(path),
                       "--expected-sha256", hashlib.sha256(raw).hexdigest()]
            process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            summary = loads(process.stdout)
            self.assertEqual(summary["node_count"], 2)
            self.assertNotIn("outcome", summary)
            process = subprocess.run([*command[:-1], "0" * 64], cwd=ROOT, capture_output=True, timeout=10)
            self.assertEqual(process.returncode, 2)
            self.assertIn(b"FILE_HASH_MISMATCH", process.stderr)


class NativeCompactV2ReaderTests(NativeCompactReaderTests):
    def records(self):
        records, nodes = super().records()
        records[0]["format"] = "spl-native-trace-stream/0.2"
        positions = {node["node_id"]: index for index, node in enumerate(nodes)}
        for record in records:
            if record["record"] == "node":
                record["dependencies"] = [positions[identity] for identity in record["inline"].pop("dependencies")]
        return records, nodes

    def test_indices_are_prior_integer_nodes_and_dependency_order_is_exact(self):
        base, _ = self.records()
        for indices in ([-1], [True], ["0"], [1], [2], [999999], None, {"index": 0}):
            changed = deepcopy(base)
            changed[3]["dependencies"] = indices
            with self.subTest(indices=indices), self.assertRaisesRegex(TransportError, "INVALID_DEPENDENCY_INDEX"):
                self.read(changed)
        records, nodes = self.records()
        records[3]["dependencies"] = [0, 0]
        nodes[1]["dependencies"] = ["n0", "n0"]
        records[-1]["expanded_bytes"] = len(canonical_json(nodes).encode())
        result = self.read(records, reconstruct=True)
        self.assertEqual(result["outcome"]["trace"], nodes)
        self.assertEqual(result["edge_count"], 2)

    def test_versions_and_dependency_representations_cannot_be_mixed(self):
        base, _ = self.records()
        changes = [lambda r: r[0].update(format="spl-native-trace-stream/0.1"),
                   lambda r: r[3].pop("dependencies"),
                   lambda r: r[3]["inline"].update(dependencies=["n0"]),
                   lambda r: r[3]["shared"].update(dependencies="p0"),
                   lambda r: r[0].update(format=[])]
        for mutate in changes:
            changed = deepcopy(base); mutate(changed)
            with self.subTest(records=changed), self.assertRaises(TransportError):
                self.read(changed)


if __name__ == "__main__":
    unittest.main()
