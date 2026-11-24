"""Complete independent mixed-claim controls through registered SPL boundaries."""
import ast
from copy import deepcopy
from fractions import Fraction
from importlib import import_module
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from cases.r1 import build_modules as registration
from oracles.mixed_claims import MixedClaimOracleError, exact_json, mixed_claims
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import DataError, digest, read_json, write_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import resolve_module, validate_module_package
from spl_compiler.run import carry_state, normalize_target
from Tests.test_mixed_claim_oracle import fixture, method, two_claims, capacity, successor

mixed=import_module('cases.mixed-waterfall.build_modules')

def retain_artifacts(source,destination):
    # Reference work hashes can exceed Windows MAX_PATH after adding the long
    # external evidence prefix. Archive that subtree without altering members.
    shutil.copytree(source,destination,ignore=shutil.ignore_patterns('.lake'))
    if (source/'.lake').exists():shutil.make_archive(str(destination/'reference-work'),'zip',root_dir=source/'.lake')


class MixedClaimModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent=ROOT/'.lake/mc';parent.mkdir(parents=True,exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(dir=parent);cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name);cls.folder=cls.root/'cases/mixed-waterfall';cls.folder.mkdir(parents=True)
        for name in ['claim-registry.spl','claim-period.spl','mixed-claims.spl','policy.md','neutral.json']:
            shutil.copyfile(ROOT/'cases/mixed-waterfall'/name,cls.folder/name)
        for owner,key,value in [(mixed,'ROOT',cls.root),(mixed,'FOLDER',cls.folder),(registration,'ROOT',cls.root)]:
            p=patch.object(owner,key,value);p.start();cls.addClassCleanup(p.stop)
        cls.reference=mixed.register_mixed_claims();cls.paths={};cls.observation_count=0
        if getattr(cls,'evidence_destination',None):cls.addClassCleanup(retain_artifacts,cls.root,cls.evidence_destination)

    def run_fixture(self,data,backend='reference',*,cells=None,output=None,mode='final'):
        package=mixed.mixed_claim_package(data,reference=self.reference,state_cells=cells,mode=mode)
        return self.run_package(package,backend,output=output)

    def run_package(self,package,backend='reference',*,output=None):
        result=mixed.run_mixed_claim_package(package,self.root,backend=backend,artifact_dir=output)
        type(self).observation_count+=1
        observations=self.root/'observations';observations.mkdir(exist_ok=True)
        write_json(observations/(str(type(self).observation_count)+'.json'),result)
        if backend=='compare' and result.get('trace_origin')=='native_ir_interpreter':
            checked,inputs,openings=validate_module_package(package,resolve_module(self.reference,self.root))
            reference=normalize_target(evaluate(checked,inputs,openings).to_dict())
            emitted=normalize_target(run_generated(checked,{k:decode_value(v,checked.types[k])for k,v in inputs.items()},{k:decode_value(v,checked.types[k])for k,v in openings.items()},output_path=self.root/('py'+str(type(self).observation_count)+'.lean')))
            for field in ['status','emissions','closing']:self.assertEqual(emitted[field],reference[field],field)
            self.assertEqual([r['code']for r in emitted['diagnostics']],[r['code']for r in reference['diagnostics']])
        if output is not None:
            self.assertEqual(load_completed_result(output),result)
            self.assertEqual(read_json(Path(output)/'result.json'),result)
            if 'result_digest'in result:self.paths[result['result_digest']]=Path(output)
        return result

    def controls(self,data,result,*,preview=False):
        expected=exact_json(mixed_claims(data))
        self.assertEqual(result['status'],'provisional'if preview else'calculated',result['diagnostics'])
        self.assertEqual(result['diagnostics'],[])
        self.assertEqual(mixed.neutral_result(result['results']['comparison'],data),{k:v for k,v in expected.items()if k!='closing_state'})
        self.assertTrue(result['results']['reconciliation'])
        if preview:
            self.assertFalse(result['closing_state'])
            with self.assertRaises(DataError)as e:carry_state(result)
            self.assertEqual(e.exception.code,'NONCONSUMABLE_STATE')
        else:
            self.assertEqual(len(result['closing_state']),1)
            self.assertEqual(mixed.neutral_state(result['closing_state'][0]['quantity']),expected['closing_state'])
        self.assertEqual(result['issuance_status'],'unissued')
        return expected

    def blocked(self,data,code,backend='reference'):
        with self.assertRaises(MixedClaimOracleError):mixed_claims(data)
        result=self.run_fixture(data,backend)
        self.assertEqual(result['status'],'blocked',result['diagnostics'])
        self.assertIn(code,[x['code']for x in result['diagnostics']])
        self.assertFalse(result['results']or result['detail']or result['closing_state'])
        self.assertNotIn('result_digest',result)
        return result

    def carried(self,data,previous):
        before=digest(previous);prior_path=self.paths[previous['result_digest']]
        write_json(self.root/'carry.json',previous['closing_state']);cells=read_json(self.root/'carry.json')
        for cell in cells:cell.pop('movement',None)
        self.assertEqual(cells,[{k:v for k,v in x.items()if k!='movement'}for x in previous['closing_state']])
        opening=mixed.neutral_state(cells[0]['quantity']);data=deepcopy(data)
        data['opening_state']=opening
        data['prior_result']={'source_case_id':opening['source_case_id'],'period':previous['results']['comparison']['period'],'closing_state':deepcopy(opening),'result_ref':cells[0]['prior_result_ref']}
        self.assertEqual(digest(previous),before);self.assertEqual(load_completed_result(prior_path),previous)
        return data,cells

    def test_native_actual_all_kind_two_period_carry(self):
        data=fixture();first=self.run_fixture(data,'compare',output=self.root/'a1');self.controls(data,first)
        next_data=successor(data,mixed_claims(data));next_data,cells=self.carried(next_data,first)
        second=self.run_fixture(next_data,'compare',cells=cells,output=self.root/'a2');expected=self.controls(next_data,second)
        led={x['kind']:x for x in expected['claim_ledger']}
        self.assertEqual([led[k]['remaining']for k in ['fee','approved_correction','capital','advance']],['0','0','0','35'])
        self.assertEqual(expected['original_correction_controls'][0]['actual_original_paid'],'80')
        preview=self.run_fixture(next_data,'compare',cells=cells,mode='preview',output=self.root/'ap');self.controls(next_data,preview,preview=True)
        package=mixed.mixed_claim_package(next_data,reference=self.reference,state_cells=cells)
        package['inputs']['registry']['claim_authorities'][0]['source_ref']=mixed.encode_identity('unchanged-finance-different-original-authority')
        blocked=self.run_package(package,'compare',output=self.root/'tamper')
        self.assertEqual(blocked['status'],'blocked',blocked['diagnostics'])
        self.assertIn('MIXED_REGISTRY_AMENDMENT_OR_NEW_CLAIM',[x['code']for x in blocked['diagnostics']])
        self.assertFalse(blocked['results']or blocked['closing_state'])

    def test_native_actual_capital_advance_two_period_carry(self):
        data=two_claims(fixture());first=self.run_fixture(data,'compare',output=self.root/'c1');self.controls(data,first)
        data=successor(data,mixed_claims(data));data,cells=self.carried(data,first)
        second=self.run_fixture(data,'compare',cells=cells,output=self.root/'c2');expected=self.controls(data,second)
        self.assertEqual(expected['residual_entitlement'],'10')
        self.assertEqual(len(expected['closing_state']['history']),2)

    def test_native_fee_correction_priority_and_exact_prorata(self):
        variants=[capacity(fixture(),'30'),method(capacity(fixture(),'30'),'priority_correction_first'),method(fixture(),'pro_rata_eligible_balances'),method(two_claims(fixture()),'pro_rata_eligible_balances')]
        for i,data in enumerate(variants):
            with self.subTest(i=i):self.controls(data,self.run_fixture(data,'compare',output=self.root/('m'+str(i))))

    def test_native_empty_zero_and_excess_residual(self):
        variants=[capacity(fixture(),'0'),capacity(fixture(),'270'),capacity(two_claims(fixture()),'1/3')]
        data=fixture();data['earnings']=[];data['earning_population'].update(earning_ids=[],gross_basis_total='0');variants.append(data)
        data=fixture();data['registry']['claim_authorities']=[];variants.append(data)
        for i,data in enumerate(variants):
            with self.subTest(i=i):self.controls(data,self.run_fixture(data,'compare',output=self.root/('z'+str(i))))

    def test_original_financial_spaces_reference(self):
        data=fixture();expected=self.controls(data,self.run_fixture(data))
        self.assertEqual([expected[k]for k in ['capacity','recoupment_credits','earning_offsets','residual_entitlement']],['120','75','45','0'])

    def test_roster_required_for_zero(self):
        for mutate in [lambda r:r['residual_weights'].pop(),lambda r:[x.update(weight='0')for x in r['residual_weights']],lambda r:r['roster_authority'].update(complete=False)]:
            d=capacity(fixture(),'0');mutate(d['registry']);self.blocked(d,'MIXED_RESIDUAL_WEIGHT_POPULATION'if d['registry']['roster_authority']['complete']else'MIXED_COMPLETE_RESIDUAL_ROSTER')

    def test_zero_weight_member_retained(self):
        d=capacity(fixture(),'270');d['registry']['residual_weights'][0]['weight']='0';self.controls(d,self.run_fixture(d))

    def test_current_cash_completeness_and_nonempty(self):
        d=fixture();d['cash_settlement_population']['complete']=False;self.blocked(d,'MIXED_CURRENT_CASH_SETTLEMENT_UNKNOWN')
        d=fixture();d['cash_settlement_population'].update(event_ids=['bank-event'],total='5');self.blocked(d,'MIXED_NONEMPTY_CASH_SETTLEMENT_VARIANT_REQUIRED')

    def test_missing_funding_population(self):
        d=fixture();d['registry']['funding_populations']=[x for x in d['registry']['funding_populations']if x['kind']=='capital'];self.blocked(d,'MIXED_COMPLETE_FUNDING_POPULATION_REQUIRED')

    def test_missing_payment_population(self):
        d=fixture();d['registry']['historical_payment_populations']=[];self.blocked(d,'MIXED_COMPLETE_ORIGINAL_PAYMENT_POPULATION_REQUIRED')

    def test_actual_payment_conservation(self):
        d=fixture();d['registry']['historical_applications'][0]['amount']='79';self.blocked(d,'MIXED_ORIGINAL_PAYMENT_CONSERVATION')

    def test_principal_requires_original_source_capacity(self):
        d=fixture();next(x for x in d['registry']['claim_authorities']if x['kind']=='approved_correction')['authorized_principal']='21';self.blocked(d,'MIXED_AUTHORIZED_PRINCIPAL_EXCEEDS_SOURCE')

    def test_bank_and_source_aliases(self):
        d=fixture();d['registry']['advance_fundings'][0]['original_ref']=d['registry']['capital_fundings'][0]['original_ref'];self.blocked(d,'MIXED_BANK_LINE_ALIAS')
        d=fixture();d['registry']['fee_bases'][0]['original_ref']=d['registry']['correction_sources'][0]['return_ref'];self.blocked(d,'MIXED_FEE_CORRECTION_LINE_ALIAS')

    def test_fund_amount_space_overlap(self):
        d=fixture();d['earnings'][0]['original_ref']=d['registry']['fee_bases'][0]['original_ref'];self.blocked(d,'MIXED_FUND_SOURCE_AMOUNT_SPACE_OVERLAP')

    def test_priority_and_earning_ties(self):
        d=fixture();x=deepcopy(d['earnings'][0]);x.update(id='other',original_ref='original#other');d['earnings'].append(x);self.blocked(d,'MIXED_UNRESOLVED_EARNING_ORDER')
        d=fixture();x=deepcopy(d['registry']['claim_authorities'][0]);x.update(id='other',original_ref='authority#other');d['registry']['claim_authorities'].append(x);self.blocked(d,'MIXED_UNRESOLVED_CLAIM_ORDER')

    def test_cutoff_scope_approval(self):
        d=fixture();d['earnings'][0]['observed_at']=d['cutoff'];self.blocked(d,'MIXED_SOURCE_OBSERVATION_AUTHORITY')
        d=fixture();d['earnings'][0]['scope']['pool_id']='other';self.blocked(d,'MIXED_FACT_SCOPE')
        d=fixture();d['registry']['claim_authorities'][0]['approved']=False;self.blocked(d,'MIXED_PROSPECTIVE_AUTHORITY')

    def test_reciprocal_and_funding_beneficiaries(self):
        d=fixture();next(x for x in d['registry']['claim_authorities']if x['kind']=='fee')['beneficiary']='capital-owner';self.blocked(d,'MIXED_RECIPROCAL_OFFSET_AUTHORITY')
        d=fixture();next(x for x in d['registry']['claim_authorities']if x['kind']=='capital')['beneficiary']='advance-owner';self.blocked(d,'MIXED_CLAIM_FUNDING_AUTHORITY')

    def test_physical_permutation(self):
        d=fixture()
        for x in d['registry'].values():
            if isinstance(x,list):x.reverse()
        self.controls(d,self.run_fixture(d))

    def test_native_unicode_scopes_and_exact_lexemes(self):
        d=fixture()
        names={'debtor-group':'group:e\u0301/\u96ea','capital-owner':'member:\u00e9','advance-owner':'member:e\u0301','synthetic-film':'film:\u96ea'}
        def rename(v):
            if isinstance(v,dict):return {k:rename(x)for k,x in v.items()}
            if isinstance(v,list):return [rename(x)for x in v]
            return names.get(v,v) if isinstance(v,str) else v
        d=rename(d);old=d['earnings'][0]['id'];new='earning:e\u0301/\u96ea';d['earnings'][0]['id']=new;d['earning_population']['earning_ids']=[new]
        d['earnings'][0].update(base_amount='240.000',observed_at='2026-03-31T12:00:00.00000000001Z');d['earning_population']['gross_basis_total']='240.00'
        d['registry']['earning_terms']['share']='1/2'
        self.controls(d,self.run_fixture(d,'compare',output=self.root/'unicode'))
        self.assertNotEqual(mixed.encode_identity('e\u0301'),mixed.encode_identity('\u00e9'))
        for x in ['e\u0301','\u00e9','\u96ea',chr(0x10ffff),'a#b:c']:
            self.assertEqual(mixed.decode_identity(mixed.encode_identity(x)),x)

    def test_strict_identity_decoder(self):
        for x in ['', 'A0','a','c080','eda080','f4908080','ff','00ff']:
            with self.subTest(x=x),self.assertRaises(ValueError):mixed.decode_identity(x)

    def test_wrapper_malformed_originals(self):
        for change in [lambda d:d['earnings'][0].update(extra='bad'),lambda d:d['earnings'][0].update(base_amount='-1'),lambda d:d['earnings'][0].update(id='\ud800')]:
            d=fixture();change(d)
            with self.assertRaises(ValueError):mixed.mixed_claim_package(d,reference=self.reference)

    def reference_carry(self,original,first):
        data=successor(original,mixed_claims(original));cells=json.loads(json.dumps(first['closing_state']))
        for cell in cells:cell.pop('movement',None)
        opening=mixed.neutral_state(cells[0]['quantity']);data['opening_state']=opening
        data['prior_result']={'source_case_id':opening['source_case_id'],'period':first['results']['comparison']['period'],'closing_state':deepcopy(opening),'result_ref':cells[0]['prior_result_ref']}
        return data,cells

    def test_future_eligibility_remains_prospective(self):
        data=fixture();next(x for x in data['registry']['claim_authorities']if x['kind']=='capital')['eligible_from']='2026-04-01'
        self.controls(data,self.run_fixture(data))

    def test_native_event_order_and_known_authority(self):
        data=fixture();early=deepcopy(data['earnings'][0]);late=deepcopy(early)
        early.update(id='earning:early',base_amount='60',effective_date='2026-02-20',observed_at='2026-02-21T00:00:00Z',original_ref='original-earning#early')
        late.update(id='earning:late',base_amount='60',original_ref='original-earning#late')
        next(x for x in data['evidence']if x['id']==early['evidence_ref'])['observed_at']=early['observed_at']
        data['earnings']=[late,early];data['earning_population'].update(earning_ids=[early['id'],late['id']],gross_basis_total='120')
        self.controls(data,self.run_fixture(data,'compare',output=self.root/'event-order'))
        data=fixture();data['registry']['claim_authorities'][0]['observed_at']='2026-04-01T00:00:00Z'
        self.blocked(data,'MIXED_AUTHORITY_NOT_KNOWN_AT_EARNING','compare')

    def test_native_original_population_and_legacy_profile_rejections(self):
        for variant,code in [('registry','MIXED_ORIGINAL_REGISTRY_POPULATION'),('frame','MIXED_ORIGINAL_FRAME_POPULATION'),('legacy1','MIXED_TRANSPORT_PROFILE'),('legacy2','MIXED_TRANSPORT_PROFILE')]:
            package=mixed.mixed_claim_package(fixture(),reference=self.reference)
            if variant=='registry':package['inputs']['original_registry_ids'][0]['ids']=[]
            elif variant=='frame':package['inputs']['original_frames'][0]['earning_ids']=[]
            else:
                version='mixed-claims-original-json/'+('1' if variant=='legacy1' else '2')
                package['inputs']['supplied_opening']['transport_profile']=version
                package['state_cells'][0]['quantity']['transport_profile']=version
            result=self.run_package(package,'compare')
            self.assertEqual(result['status'],'blocked',result['diagnostics']);self.assertIn(code,[x['code']for x in result['diagnostics']]);self.assertFalse(result['results']or result['closing_state'])

    def test_nonmonotone_cutoffs_preserve_full_unused_registry_validation(self):
        original=fixture();original['cutoff']='2027-01-03T00:00:00Z'
        first=self.run_fixture(original);self.controls(original,first)
        data,cells=self.reference_carry(original,first);self.controls(data,self.run_fixture(data,cells=cells))
        extra=deepcopy(original['registry']['evidence'][0]);extra.update(id='unused-late-evidence',observed_at='2026-08-01T00:00:00Z')
        original['registry']['evidence'].append(extra)
        first=self.run_fixture(original);self.controls(original,first)
        data,cells=self.reference_carry(original,first);self.blocked(data,'MIXED_EVIDENCE_SCOPE_APPROVAL_CUTOFF')

    def test_actual_reference_history_and_balance_tampering(self):
        original=fixture();first=self.run_fixture(original);self.controls(original,first)
        for target,code in [('balance','MIXED_OPENING_RECONCILIATION'),('history','MIXED_HISTORY_FINANCIAL_REPLAY')]:
            data,cells=self.reference_carry(original,first)
            if target=='balance':data['opening_state']['claim_ledger'][0]['remaining']='0'
            else:data['opening_state']['history'][0]['result']['recoupment_credits']='0'
            data['prior_result']['closing_state']=deepcopy(data['opening_state'])
            self.blocked(data,code)

    def test_admitted_reference_claim_and_evidence_bounds(self):
        data=fixture();data['registry']['claim_authorities']=[]
        base=fixture()['registry']['claim_authorities'][0];fund=deepcopy(data['registry']['capital_fundings'][0])
        data['registry']['capital_fundings']=[]
        for index in range(8):
            source=deepcopy(fund);source.update(id='fund:'+str(index),amount='25/2',original_ref='original-bank#'+str(index));data['registry']['capital_fundings'].append(source)
            claim=deepcopy(base);claim.update(id='claim:'+str(index),source_ids=[source['id']],authorized_principal='25/2',sequence=index,original_ref='original-authority#'+str(index));data['registry']['claim_authorities'].append(claim)
        pop=next(x for x in data['registry']['funding_populations']if x['kind']=='capital');pop['funding_ids']=[x['id']for x in data['registry']['capital_fundings']]
        self.controls(data,self.run_fixture(data))
        other=deepcopy(data['registry']['claim_authorities'][0]);other.update(id='claim:9',sequence=9,original_ref='original-authority#9');data['registry']['claim_authorities'].append(other);self.blocked(data,'MIXED_CLAIM_BOUND')
        data=fixture()
        while len(data['registry']['evidence'])<32:
            row=deepcopy(data['registry']['evidence'][0]);row['id']='unused:'+str(len(data['registry']['evidence']));data['registry']['evidence'].append(row)
        self.controls(data,self.run_fixture(data))
        row=deepcopy(data['registry']['evidence'][0]);row['id']='unused:33';data['registry']['evidence'].append(row);self.blocked(data,'MIXED_FINITE_ROWS')

    def test_native_maximum_future_eligibility_and_utc_day_transport(self):
        data=fixture();next(x for x in data['registry']['claim_authorities']if x['kind']=='capital')['eligible_from']='9999-12-31'
        result=self.run_fixture(data,'compare',output=self.root/'date-max');expected=self.controls(data,result)
        self.assertEqual(next(x for x in expected['claim_ledger']if x['kind']=='capital')['remaining'],'100')
        self.assertEqual(next(x for x in expected['claim_ledger']if x['kind']=='advance')['recoupment_credit'],'75')
        data=fixture();data['registry']['capital_fundings'][0]['funded_at']='2026-01-02T00:59:59.999999999999+01:00'
        self.controls(data,self.run_fixture(data,'compare',output=self.root/'utc-boundary'))
        data=fixture();data['registry']['capital_fundings'][0]['funded_at']='2026-01-02T00:00:00Z'
        self.blocked(data,'MIXED_SOURCE_ELIGIBILITY','compare')

    def test_zero_original_sources_do_not_manufacture_claim_capacity(self):
        data=fixture();registry=data['registry'];registry['advance_fundings']=[]
        next(x for x in registry['funding_populations']if x['kind']=='advance').update(funding_ids=[],total='0')
        authority=next(x for x in registry['claim_authorities']if x['kind']=='advance');authority['source_ids']=[]
        self.blocked(data,'MIXED_AUTHORIZED_PRINCIPAL_EXCEEDS_SOURCE')
        authority['authorized_principal']='0';self.controls(data,self.run_fixture(data))
        data=fixture();registry=data['registry'];registry['historical_payments']=[];registry['historical_applications']=[]
        registry['historical_payment_populations'][0].update(payment_ids=[],application_ids=[],paid_total='0')
        next(x for x in registry['claim_authorities']if x['kind']=='approved_correction')['authorized_principal']='0'
        self.controls(data,self.run_fixture(data))

    def test_strict_raw_and_state_restoration(self):
        for value in ['{"x":1,"x":1}', '{"x": NaN}', '{ "x":1}', '[] ']:
            with self.assertRaises(ValueError):mixed._unraw(value)
        data=fixture();data['opening_state']['history']=[{}]
        with self.assertRaisesRegex(ValueError,'MIXED_GENESIS'):mixed.mixed_claim_package(data,reference=self.reference)
        result=self.run_fixture(fixture());state=deepcopy(result['closing_state'][0]['quantity'])
        for version in ['mixed-claims-original-json/1','mixed-claims-original-json/2']:
            state['transport_profile']=version
            with self.assertRaisesRegex(ValueError,'MIXED_TRANSPORT_PROFILE'):mixed.neutral_state(state)
        state=deepcopy(result['closing_state'][0]['quantity']);state['detail']['some']['registry']['earning_terms']['share']=mixed.number(Fraction(1,3))
        with self.assertRaisesRegex(ValueError,'MIXED_TYPED_REGISTRY_TRANSPORT'):mixed.neutral_state(state)

    def test_no_oracle_import_and_unchanged_input(self):
        tree=ast.parse((ROOT/'cases/mixed-waterfall/build_modules.py').read_text(encoding='utf-8-sig'))
        imports={n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)}
        self.assertFalse(any(x and x.startswith(('oracles','Tests'))for x in imports))
        d=fixture();before=deepcopy(d);self.controls(d,self.run_fixture(d));self.assertEqual(d,before)

if __name__=='__main__':unittest.main()
