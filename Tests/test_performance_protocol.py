"""Bounded protocol guards and genuine temporary AOT compilation control."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts import spl_performance_protocol as protocol
from scripts import spl_mixed_benchmark as mixed

EVIDENCE_DIR=None


def retain(name,root):
    if EVIDENCE_DIR is not None:
        shutil.copytree(root,Path(EVIDENCE_DIR)/name)


class PerformanceProtocolTests(unittest.TestCase):
    def test_full_and_smoke_plans_keep_fixed_guards_and_scopes(self):
        full = protocol.make_plan(host_load_note="Host load recorded by caller")
        self.assertTrue(full["full_repetition_protocol"])
        self.assertEqual(len(protocol.sample_labels(full)), 33)
        self.assertEqual(full["worker_count"], 1)
        self.assertEqual(full["budgets"]["stdout_bytes"], 67108864)
        self.assertEqual(full["budgets"]["sampled_child_working_set_bytes"], 268435456)
        self.assertEqual(full["budgets"]["logical_expanded_trace_bytes"], 1073741824)
        self.assertEqual(full["budgets"]["native_ir_observations"], 100000)
        self.assertFalse(protocol.make_plan(first_samples=1, warm_samples=0, records=(100,), host_load_note="smoke")["full_repetition_protocol"])
        self.assertFalse(full["canonical_close_credit"])
        full["budgets"]["stdout_bytes"] = 1
        self.assertEqual(protocol.BUDGETS["stdout_bytes"], 67108864)

    def test_protocol_rejects_unapproved_scale_order_samples_and_missing_load(self):
        for kwargs in ({"first_samples":True}, {"first_samples":4}, {"warm_samples":31}, {"records":(1000,)}, {"records":(100,10000)}, {"host_load_note":""}, {"compiler_profile":"larger"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                protocol.make_plan(**{"host_load_note":"disclosed", **kwargs})

    def test_compiler_only_named_profile_cannot_raise_runtime_guards(self):
        plan=protocol.make_plan(compiler_profile='compiler1g180',host_load_note='documented new compile profile')
        self.assertEqual(plan['compiler_profile']['sampled_child_working_set_bytes'],1073741824)
        self.assertEqual(plan['compiler_profile']['timeout_seconds'],180)
        self.assertEqual(plan['budgets'],protocol.BUDGETS)
        with patch.object(protocol,'run_process',return_value={'status':'passed'}) as process:
            protocol.measured(['tool'],'output',{},compiler_profile=plan['compiler_profile'])
            self.assertEqual(process.call_args.kwargs['max_working_set_bytes'],1073741824)
            self.assertEqual(process.call_args.kwargs['timeout'],180)
            protocol.measured(['target'],'runtime-output',{})
            self.assertEqual(process.call_args.kwargs['max_working_set_bytes'],268435456)
            self.assertEqual(process.call_args.kwargs['timeout'],60)

    def test_statistics_retain_censoring_and_use_exact_successful_order(self):
        result = protocol.observations([{"status":"passed","wall_seconds":"0.1"}, {"status":"failed","reason":"memory"},
                                        {"status":"passed","wall_seconds":"0.3"}, {"status":"not_executed","reason":"predecessor"}])
        self.assertEqual(result["samples"],4)
        self.assertEqual(result["successful_samples"],2)
        self.assertEqual(len(result["failures_or_unexecuted"]),2)
        self.assertEqual(Fraction(result["p95_seconds_successful_only"]),Fraction(3,10))
        self.assertEqual(Fraction(result["p50_seconds_successful_only"]),Fraction(1,10))
        self.assertNotIn("p95_seconds_successful_only",protocol.observations([{"status":"failed"}]))
        for row in ({"status":"passed","wall_seconds":0.1},{"status":"passed","wall_seconds":"-1"},{"status":"successful","wall_seconds":"0"}):
            with self.assertRaises(ValueError):protocol.observations([row])

    def test_pinned_c_trace_flags_reject_ambiguous_or_wrong_driver(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'trace.json';toolbin=Path(temp)
            message='.> '+str(toolbin/'clang.exe')+' -c -o object.o source/SV.c -O3 -DNDEBUG'
            path.write_text(json.dumps({'log':[{'level':'trace','message':message}]}))
            self.assertEqual(protocol.c_compile_flags(path,toolbin),['-O3','-DNDEBUG'])
            for changed in (message.replace('clang.exe','other.exe'),message.replace('SV.c','Other.c'),'',message+' "unsupported quoted path"'):
                path.write_text(json.dumps({'log':[{'level':'trace','message':changed}]}))
                with self.assertRaises(ValueError):protocol.c_compile_flags(path,toolbin)

    def test_stale_or_partially_checked_mixed_summary_cannot_authorize_repeats(self):
        pins={'selected':'pin'}
        report={'format':'spl-mixed-performance/1','status':'passed','counts':{'raw_original_records':100},'required_audit_completed':True,'seed':20261123,
                'transport':'compact-v2','profile_stages':False,'target_generation':mixed.TARGET_GENERATION,'implementation':'legacy','dependency_pins':pins,
                'budgets':{'child_timeout_seconds':60,'child_stdout_bytes':67108864,'child_sampled_working_set_bytes':268435456},
                'native_samples':[{'status':'passed','target':{'status':'passed','independent_control':'passed'},'audit':{'status':'passed','independent_control':'passed'},'reader':{'status':'passed'},
                                   'trace_validation':{'format':'spl-native-trace-stream/0.2','transport_sha256':'a'*64,'node_count':1,'expanded_trace_bytes':100}}],
                'reference_control':'passed','original_neutral_unchanged':True,'unchanged_dependency_pins':True,'native_emission':{'status':'passed'}}
        protocol.validate_mixed_report(report,pins,100,20261123)
        mutations=[lambda r:r.update(reference_control='not_executed'),lambda r:r.update(seed=1),lambda r:r.update(dependency_pins={}),
                   lambda r:r['native_samples'][0]['audit'].update(independent_control='not_checked'),lambda r:r['native_samples'][0]['reader'].update(status='not_executed'),
                   lambda r:r.update(target_generation='historical'),lambda r:r.update(unchanged_dependency_pins=False),lambda r:r['native_samples'][0].pop('trace_validation')]
        for mutate in mutations:
            changed=deepcopy(report);mutate(changed)
            with self.assertRaises(ValueError):protocol.validate_mixed_report(changed,pins,100,20261123)

    def test_changed_closure_fails_before_execution(self):
        with patch.object(protocol,'dependency_pins',return_value={'source':'changed'}):
            with self.assertRaisesRegex(ValueError,'CLOSURE_CHANGED'):
                protocol.require_pins({'source':'original'})

    def test_metadata_decoder_allows_optional_null_without_weakening_json_guards(self):
        from scripts.spl_trace_transport import TransportError
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.json';path.write_text('{"prerequisite":null,"status":"passed"}')
            self.assertIsNone(protocol.load_report(path)['prerequisite'])
            for text in ('{"x":1,"x":2}','{"x":NaN}','{"x":1.2}','{"x":1e999}'):
                path.write_text(text)
                with self.assertRaises(TransportError):protocol.load_report(path)
            path.write_text('{"long":"xxxxxxxxxxxxxxxx"}')
            with self.assertRaises(TransportError):protocol.load_report(path,max_bytes=8)

    def test_pure_repetition_report_requires30_verified_warm_batches(self):
        process={'status':'passed','independent_control':{'status':'passed'},'observation':{'samples':[{}]*10,'resolution_span_reached':True}}
        cohort={'records':100,'status':'passed','control_status':'passed','inner_sample_count':30,'timer_span_reached_all':True,'processes':[deepcopy(process) for _ in range(3)]}
        report={'format':'spl-pure-performance/1','status':'passed','unchanged_dependency_pins':True,'cohorts':[cohort]}
        protocol.validate_pure_report(report,[100])
        for mutate in (lambda r:r['cohorts'][0].update(inner_sample_count=29),lambda r:r['cohorts'][0]['processes'][0]['independent_control'].update(status='not_checked'),lambda r:r['cohorts'][0]['processes'][0]['observation'].update(resolution_span_reached=False)):
            changed=deepcopy(report);mutate(changed)
            with self.assertRaises(ValueError):protocol.validate_pure_report(changed,[100])

    def test_incomplete_ir_publication_cannot_create_completed_marker_or_state(self):
        from spl_compiler.artifacts import load_completed_result,PublicationError
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);wire=root/'wire.jsonl';wire.write_text('{}\n');expected=root/'expected.json';expected.write_text('{}')
            report=protocol.publication_worker(wire,expected,root/'publication')
            self.assertEqual(report['status'],'failed')
            self.assertEqual(report['first_failure'],'reconstruction')
            self.assertEqual(report['stages']['publication']['status'],'not_executed')
            self.assertEqual(report['financial_outputs'],{})
            self.assertEqual(report['closing_state'],[])
            with self.assertRaises(PublicationError):load_completed_result(root/'publication')

    def test_native_generic_ir_publication_preserves_actual_shape(self):
        from scripts.spl_native_trace_transport import read_compact
        from spl_compiler.lean_tools import lean_environment
        from spl_compiler.artifacts import load_completed_result
        parent=protocol.ROOT/'.lake/pp';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            root=Path(temp);source=root/'Source.spl';bindings=root/'bindings.json';expected=root/'expected.json'
            source.write_text('schedule PublicationControl language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" { input x:Ratio; emit "answer"=x*2.0; }')
            bindings.write_text('{"inputs":{"x":"0.75"},"openings":{}}')
            expected.write_text('{"status":"calculated","emissions":{"answer":"1.5"},"closing":{},"diagnostic_codes":[]}')
            _,env=lean_environment()
            measured=protocol.measured([protocol.ROOT/'.lake/build/bin/spl_trace_stream.exe',source,bindings,'--compact-v2'],root/'native',env)
            self.assertEqual(measured['status'],'passed',measured)
            wire=root/'native/stdout.bin';actual=read_compact(wire,reconstruct=True)
            report=protocol.publication_worker(wire,expected,root/'published',actual['transport_sha256'])
            self.assertEqual(report['status'],'passed',report)
            loaded=load_completed_result(root/'published')
            self.assertEqual(loaded,actual['outcome'])
            self.assertNotIn('statements',loaded)
            self.assertNotIn('result_digest',loaded)
            self.assertFalse(report['canonical_close_credit'])
            retain('generic-ir-publication',root)

    def test_failed_compilation_stops_later_stages_and_samples(self):
        plan=protocol.make_plan(first_samples=1,warm_samples=1,records=(100,),host_load_note='mocked control')
        with tempfile.TemporaryDirectory() as temp, patch.object(protocol,'require_pins'), patch.object(protocol,'measured',return_value={'status':'failed','wall_seconds':'0.01'}) as measured:
            result=protocol.compile_samples(Path(temp)/'compilation',plan,{}, {}, {})
        self.assertEqual(measured.call_count,1)
        self.assertEqual(result['first_failure'],{'sample':1,'stage':'frontend_to_lean'})
        self.assertEqual(result['samples'][0]['stages']['native_link']['status'],'not_executed')
        self.assertEqual(result['samples'][1]['status'],'not_executed')

    def test_native_temporary_aot_respects_guard_or_matches_complete_controls(self):
        from oracles.skouras import skouras
        from spl_compiler.run import bind_package,project
        from spl_compiler.schema import validate_package
        from validation.mixed_workloads import generate_mixed
        workload=generate_mixed(100)
        oracle=skouras(workload['neutral'])
        expected=mixed.target_expected(oracle)
        bound=bind_package(workload['neutral']['package'],protocol.ROOT/'cases/sv/sv01.spl');validate_package(bound)
        inputs,aliases,lineage,dispositions=project(bound)
        openings={'prepayment':aliases['sv/participant-prepayment/main-pool']}
        mixed.check_projection(workload,oracle,inputs,openings,lineage,dispositions)
        parent=protocol.ROOT/'.lake/pp';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            pins=protocol.dependency_pins()
            plan=protocol.make_plan(first_samples=1,warm_samples=0,records=(100,),host_load_note='Focused native control; background load uncontrolled')
            result=protocol.compile_samples(Path(temp)/'compilation',plan,pins,{'inputs':inputs,'openings':openings},expected)
            row=result['samples'][0]
            if result['status']=='failed':
                # This environment's full SV elaboration exceeds the unchanged
                # 256MiB profile. Credit only that measured resource boundary,
                # never an arbitrary compiler/control failure.
                self.assertEqual(result['first_failure'],{'sample':1,'stage':'lean_elaboration_codegen'},result)
                self.assertTrue(row['stages']['lean_elaboration_codegen']['working_set_budget_exceeded'])
                self.assertEqual(row['stages']['compiled_financial_control']['status'],'not_executed')
            else:
                self.assertEqual(row['stages']['compiled_financial_control']['independent_control'],'passed')
                self.assertEqual(len(row['artifacts']),5)
            protocol.require_pins(pins)
            retain('runtime256-aot-control',Path(temp))


if __name__=='__main__':unittest.main()
