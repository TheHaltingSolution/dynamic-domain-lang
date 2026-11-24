"""Run frozen independent controls against the separate SPL implementation.

The inherited expectation methods remain the original author's tests. The
hook runs the oracle and SPL independently and compares every result/state
field before returning the original Fraction result to those expectations.
"""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import Tests.test_reserve_stage_oracle as original
from oracles.reserve_stages import ReserveStageOracleError, reserve_stages, exact_json
from spl_compiler.artifacts import load_completed_result
from spl_compiler.modules import run_module_package
from cases.r1 import build_modules as registration

stage=import_module('cases.reserve-stages.build_modules')

class ReserveStageModuleTests(original.ReserveStageOracleTests):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='c09t-',dir='C:/')
        cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name); folder=root/'cases/reserve-stages'; folder.mkdir(parents=True)
        for name in ('reserve-stages.spl','policy.md','neutral.json'):
            shutil.copyfile(stage.FOLDER/name,folder/name)
        for owner,key,value in ((stage,'ROOT',root),(stage,'FOLDER',folder),(registration,'ROOT',root)):
            changed=patch.object(owner,key,value); changed.start(); cls.addClassCleanup(changed.stop)
        cls.reference=stage.register_reserve_stages()

    def setUp(self):
        changed=patch.object(original,'reserve_stages',self.run_original_control)
        changed.start(); self.addCleanup(changed.stop)

    def run_original_control(self,data):
        before=deepcopy(data)
        try: expected=reserve_stages(data)
        except ReserveStageOracleError:
            try:
                prepared=deepcopy(data)
                if 'prior_result' in prepared: prepared['prior_result']['result_ref']='result@sha256:'+'a'*64
                package=stage.reserve_stages_package(prepared,reference=self.reference)
                result=stage.run_reserve_stages_package(package,backend='reference')
                self.assertEqual(result['status'],'blocked',result['diagnostics'])
                self.assertFalse(result['results'] or result['closing_state'])
            except (ValueError,KeyError,TypeError,OverflowError): pass
            self.assertEqual(data,before)
            raise
        prepared=deepcopy(data)
        if 'prior_result' in prepared: prepared['prior_result']['result_ref']='result@sha256:'+'a'*64
        result=stage.run_reserve_stages_package(stage.reserve_stages_package(prepared,reference=self.reference),backend='reference')
        self.assertEqual(result['status'],'calculated',result['diagnostics'])
        expected=exact_json(expected)
        self.assertEqual(stage.neutral_result(result['results']['comparison']),{k:v for k,v in expected.items() if k!='closing_state'})
        self.assertEqual(stage.neutral_state(result['closing_state'][0]['quantity']),expected['closing_state'])
        self.assertEqual(data,before)
        return reserve_stages(data)

    def test_prepared_raw_context_and_state_transport_mismatches_block(self):
        base=stage.reserve_stages_package(original.view(original.fixture()),reference=self.reference)
        mutations=[lambda p:p['inputs']['terms'].__setitem__('fixed_fee',{'value':'9','currency':'USD'}),lambda p:p['inputs']['frames'][0]['receipts'][0].__setitem__('gross',{'value':'999','currency':'USD'}),lambda p:p['inputs']['registry_evidence'][0].__setitem__('approved',False),lambda p:p['state_cells'][0]['quantity'].__setitem__('source_case_id',stage.identity('other'))]
        for change in mutations:
            package=deepcopy(base); change(package)
            result=stage.run_reserve_stages_package(package,backend='reference')
            self.assertEqual(result['status'],'blocked'); self.assertEqual(result['diagnostics'][0]['code'],'RS_PREPARED_PACKAGE_MISMATCH')

    def test_explicit_null_original_fraction_is_not_omission(self):
        data=original.view(original.fixture('basis_reserve_stage'))
        data['terms']['release_schedule'][0]['fraction']=None
        with self.assertRaises(ReserveStageOracleError): reserve_stages(data)
        with self.assertRaises(ValueError): stage.reserve_stages_package(data,reference=self.reference)
        package=stage.reserve_stages_package(original.view(original.fixture('basis_reserve_stage')),reference=self.reference)
        context=stage.loads(package['inputs']['source_context'])
        context['terms']['release_schedule'][0]['fraction']=None
        package['inputs']['source_context']=stage.context_raw(context)
        result=stage.run_reserve_stages_package(package,backend='reference')
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['diagnostics'][0]['code'],'RS_PREPARED_PACKAGE_MISMATCH')
        self.assertFalse(result['results'] or result['closing_state'])

    def test_direct_prepared_binding_source_negative_controls(self):
        base=stage.reserve_stages_package(original.view(original.fixture()),reference=self.reference)
        mutations=[lambda p:p['inputs']['terms'].__setitem__('fixed_fee',{'value':'1000','currency':'USD'}),lambda p:p['inputs']['frames'][0]['elections'][0].__setitem__('approved',False),lambda p:p['inputs']['frames'][0]['evidence'][0].__setitem__('approved',False),lambda p:p['inputs']['terms'].__setitem__('reserve_measure','producer_entitlement_USD'),lambda p:p['inputs']['frames'][0]['population'].__setitem__('complete',False)]
        for change in mutations:
            package=deepcopy(base); change(package)
            # Deliberately bypass the public original/typed custody guard.
            result=run_module_package(package,stage.ROOT,backend='reference')
            self.assertEqual(result['status'],'blocked',result['diagnostics'])
            self.assertTrue(result['diagnostics'][0]['code'].startswith('RS_'),result['diagnostics'])
            self.assertNotEqual(result['diagnostics'][0]['code'],'RS_PREPARED_PACKAGE_MISMATCH')
            self.assertFalse(result['results'] or result['closing_state'])

    def test_reused_publication_invalidates_preparation_cancel_and_bad_profile(self):
        parent=stage.ROOT/'.lake'/'c09'; parent.mkdir(parents=True,exist_ok=True)
        base=stage.reserve_stages_package(original.view(original.fixture()),reference=self.reference)
        with tempfile.TemporaryDirectory(dir=parent) as location:
            root=Path(location)
            for failure in ('mismatch','cancel','profile'):
                good=stage.run_reserve_stages_package(base,backend='reference',artifact_dir=root)
                self.assertEqual(load_completed_result(root),good)
                if failure=='mismatch':
                    bad=deepcopy(base); bad['inputs']['terms']['fixed_fee']={'value':'9','currency':'USD'}
                    blocked=stage.run_reserve_stages_package(bad,backend='reference',artifact_dir=root)
                    self.assertEqual(load_completed_result(root),blocked); self.assertEqual(blocked['status'],'blocked')
                elif failure=='cancel':
                    with patch.object(stage,'validate_prepared_package',side_effect=KeyboardInterrupt):
                        with self.assertRaises(KeyboardInterrupt): stage.run_reserve_stages_package(base,backend='reference',artifact_dir=root)
                    with self.assertRaises(Exception): load_completed_result(root)
                else:
                    with self.assertRaises(ValueError): stage.run_reserve_stages_package(base,backend='reference',artifact_dir=root,audit_profile='bad')
                    with self.assertRaises(Exception): load_completed_result(root)

    def test_six_actual_loaded_serialized_chains_and_preview(self):
        parent=stage.ROOT/'.lake'/'c09'; parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as location:
            root=Path(location)
            for ci,(name,case) in enumerate(stage.loads((stage.FOLDER/'neutral.json').read_text())['scenarios'].items()):
                previous=None
                for position in range(len(case['frames'])):
                    data=original.view(case,position,previous)
                    cells=None
                    if previous is not None:
                        data['prior_result']['result_ref']=prior['closing_state'][0]['prior_result_ref']
                        cells=json.loads(json.dumps(prior['closing_state']))
                        for cell in cells: cell.pop('movement',None)
                    folder=root/str(ci)/str(position)
                    package=stage.reserve_stages_package(data,reference=self.reference,state_cells=cells)
                    result=stage.run_reserve_stages_package(package,backend='reference',artifact_dir=folder)
                    prior=load_completed_result(folder); self.assertEqual(prior,result)
                    self.assertEqual(result['status'],'calculated',result['diagnostics'])
                    expected=exact_json(reserve_stages(data))
                    actual={**stage.neutral_result(result['results']['comparison']),'closing_state':stage.neutral_state(result['closing_state'][0]['quantity'])}
                    self.assertEqual(actual,expected); previous=actual
                    if position==len(case['frames'])-1:
                        package=stage.reserve_stages_package(data,reference=self.reference,state_cells=cells,mode='preview')
                        preview=stage.run_reserve_stages_package(package,backend='reference',artifact_dir=root/str(ci)/'p')
                        self.assertEqual(preview['status'],'provisional',preview['diagnostics']); self.assertFalse(preview['closing_state'])
                        self.assertEqual(stage.neutral_result(preview['results']['comparison']),{k:v for k,v in expected.items() if k!='closing_state'})

if __name__=='__main__': unittest.main()
