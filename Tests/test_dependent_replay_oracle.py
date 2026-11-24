"""Requirement-first C13 controls; no compiler, SPL or adapter imports."""
import ast
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest

from oracles.dependent_replay import DependentReplayOracleError, dependent_replay, exact_json

ROOT=Path(__file__).resolve().parents[1]

def fixture(name='simple',route='restatement'):
    return json.loads((ROOT/'cases/dependent-replay/neutral.json').read_text(encoding='utf-8'))['scenarios'][name+'_'+route]

def successor(original,previous):
    data=deepcopy(original);old=data['period_id'];n=int(old[1:])+1;pid='p'+str(n)
    spans={3:({'start':'2026-07-01','end':'2026-10-01'},'2026-09-30','2026-10-03T00:00:00Z','2026-10-02T12:00:00Z'),4:({'start':'2026-10-01','end':'2027-01-01'},'2026-12-31','2027-01-03T00:00:00Z','2027-01-02T12:00:00Z')}
    span,asof,cutoff,observed=spans[n];data.update(case_id=original['case_id']+'-next',period_id=pid,period=span,as_of=asof,cutoff=cutoff,predecessor_period_id=old,predecessor_result_ref='supplied-neutral-result#'+previous['source_case_id'])
    data['receipts']=[];data['replacements']=[];data['authorities']=[];data['requests']=[]
    data['evidence']=[]
    for key,kind in [('population','complete_current_receipt_population'),('cash_population','complete_current_cash_population'),('correction_population','complete_correction_population')]:
        row=data[key];row.update(id=key+':'+pid,period=deepcopy(span),observed_at=observed,source_ref='original-source:'+key+':'+pid,evidence_ref='evidence:'+key+':'+pid)
        if key=='population':row.update(receipt_ids=[],gross_basis_total='0')
        if key=='correction_population':row.update(request_ids=[],replacement_ids=[],authority_ids=[])
        data['evidence'].append({'id':row['evidence_ref'],'scope':deepcopy(data['scope']),'kind':kind,'approved':True,'observed_at':observed,'source_ref':'original-evidence:'+key+':'+pid})
    serialized=json.loads(json.dumps(exact_json(previous)));data['opening_state']=serialized['closing_state'];data['prior_result']={'source_case_id':serialized['source_case_id'],'period':serialized['period'],'closing_state':deepcopy(serialized['closing_state']),'result_ref':data['predecessor_result_ref']}
    return data

class DependentReplayOracleTests(unittest.TestCase):
    def reject(self,data,code):
        before=deepcopy(data)
        with self.assertRaisesRegex(DependentReplayOracleError,'^'+code+'$'):dependent_replay(data)
        self.assertEqual(data,before)

    def assert_bridge(self,result):
        self.assertEqual(result['original_issued_unpaid']+result['calculated_unissued_earnings']+result['authorized_correction_credit'],result['outstanding'])
        self.assertEqual(result['cumulative_economic_entitlement']-result['actual_original_paid'],result['outstanding'])
        self.assertEqual(result['cumulative_recognized_entitlement'],result['cumulative_economic_entitlement'])
        self.assertEqual(result['actual_original_paid'],80)
        self.assertFalse(result['bank_movement_created']or result['adjustment_issued_or_paid'])
        self.assertEqual(result['issuance_status'],'unissued_calculation')
        self.assertEqual(result['actual_current_cash'],0)

    def test_simple_restatement90_plus30_less80_is40(self):
        data=fixture();r=dependent_replay(data);self.assert_bridge(r)
        self.assertEqual([x['recognized_entitlement']for x in r['period_lines']],[90,30])
        self.assertEqual((r['original_issued_total'],r['original_issued_unpaid'],r['revised_original_issued_economic_unpaid'],r['calculated_unissued_earnings'],r['authorized_correction_credit'],r['outstanding']),(100,20,10,30,-10,40))
        self.assertEqual(r['current_recognized'],30);self.assertEqual(r['current_posted_adjustment'],0)
        self.assertEqual([x['delta']for x in r['restatement_records']],[-10]);self.assertEqual(r['prospective_adjustments'],[])
        self.assertEqual(r['original_issued_artifacts'],data['registry']['issued_artifacts'])

    def test_simple_prospective_original100_current30_and_credit_minus10(self):
        data=fixture(route='prospective');r=dependent_replay(data);self.assert_bridge(r)
        self.assertEqual([x['recognized_entitlement']for x in r['period_lines']],[100,20])
        self.assertEqual((r['current_economic_earned'],r['current_posted_adjustment'],r['current_recognized'],r['outstanding']),(30,-10,20,40))
        self.assertEqual([x['delta']for x in r['prospective_adjustments']],[-10]);self.assertEqual(r['restatement_records'],[])
        self.assertEqual(r['original_issued_artifacts'],data['registry']['issued_artifacts'])

    def test_routes_share_economics_but_differ_in_period_attribution(self):
        a=dependent_replay(fixture());b=dependent_replay(fixture(route='prospective'))
        self.assertEqual(a['replayed_period_controls'],b['replayed_period_controls'])
        self.assertEqual(a['original_period_controls'],b['original_period_controls'])
        self.assertEqual(a['outstanding'],b['outstanding']);self.assertNotEqual(a['period_lines'],b['period_lines'])
        self.assertEqual((a['calculated_restatement_credit'],a['calculated_prospective_credit'],b['calculated_restatement_credit'],b['calculated_prospective_credit']),(-10,0,0,-10))

    def test_true_dependency_original10_replayed8_not_independent10(self):
        data=fixture('dependent');r=dependent_replay(data);self.assert_bridge(r)
        self.assertEqual([x['earned']for x in r['original_period_controls']],[100,10])
        self.assertEqual([x['earned']for x in r['replayed_period_controls']],[90,8,0])
        second=r['replayed_period_controls'][1]['receipt_details'][0]
        self.assertEqual((second['opening_cumulative_basis'],second['lower_basis'],second['upper_basis'],second['earned']),(180,40,20,8))
        self.assertEqual((r['original_issued_total'],r['original_issued_unpaid'],r['authorized_correction_credit'],r['outstanding'],r['closing_cumulative_basis']),(110,30,-12,18,240))
        self.assertNotEqual(r['outstanding'],20)
        self.assertEqual([x['delta']for x in r['restatement_records']],[-10,-2])

    def test_dependent_prospective_keeps_issued100_10_posts_minus10_minus2(self):
        data=fixture('dependent','prospective');r=dependent_replay(data);self.assert_bridge(r)
        self.assertEqual([x['recognized_entitlement']for x in r['period_lines']],[100,10,-12])
        self.assertEqual([x['delta']for x in r['prospective_adjustments']],[-10,-2])
        self.assertEqual((r['current_economic_earned'],r['current_recognized'],r['outstanding']),(0,-12,18))
        self.assertEqual([x['earned']for x in r['original_issued_artifacts']],['100','10'])

    def test_serialized_successor_consumes_simple_correction_once_both_routes(self):
        for route in ['restatement','prospective']:
            data=fixture(route=route);first=dependent_replay(data);before=deepcopy(first);next_data=successor(data,first);second=dependent_replay(next_data)
            self.assert_bridge(second);self.assertEqual(second['outstanding'],40);self.assertEqual(second['current_recognized'],0);self.assertEqual(second['source_changes'],[]);self.assertEqual(second['restatement_records'],[]);self.assertEqual(second['prospective_adjustments'],[])
            self.assertEqual(second['authorized_correction_credit'],-10);self.assertEqual(second['consumed_correction_ids'],['request:p1']);self.assertEqual(first,before)
            self.assertEqual(second['closing_state']['history'][0]['result'],exact_json({k:v for k,v in first.items()if k!='closing_state'}))
            self.assertEqual(second['closing_state']['history'][0]['facts'],{k:data[k]for k in second['closing_state']['history'][0]['facts']})

    def test_serialized_true_chain_successor_preserves_three_old_original_spaces(self):
        for route in ['restatement','prospective']:
            data=fixture('dependent',route);first=dependent_replay(data);before=deepcopy(first);next_data=successor(data,first);second=dependent_replay(next_data)
            self.assert_bridge(second);self.assertEqual((second['original_issued_total'],second['actual_original_paid'],second['authorized_correction_credit'],second['outstanding']),(110,80,-12,18))
            self.assertEqual(second['current_posted_adjustment'],0);self.assertEqual(second['closing_cumulative_basis'],240);self.assertEqual(first,before)
            self.assertEqual(second['closing_state']['registry']['issued_artifacts'],first['closing_state']['registry']['issued_artifacts'])
            self.assertEqual(len(second['period_lines']),4)

    def test_complete_old_bank_population_is_not_issued_entitlement(self):
        data=fixture();data['registry']['payment_population']['complete']=False;self.reject(data,'REPLAY_COMPLETE_PAID_POPULATION')
        data=fixture();data['registry']['payments']=[];data['registry']['applications']=[];data['registry']['payment_population'].update(payment_ids=[],application_ids=[],paid_total='0');r=dependent_replay(data)
        self.assertEqual((r['actual_original_paid'],r['outstanding']),(0,120));self.assertEqual(r['original_issued_total'],100)

    def test_original_payment_application_conservation(self):
        data=fixture();data['registry']['applications'][0]['amount']='79';self.reject(data,'REPLAY_PAYMENT_CONSERVATION')
        data=fixture();data['registry']['applications'][0]['approved']=False;self.reject(data,'REPLAY_PAYMENT_APPLICATION_AUTHORITY')
        data=fixture();data['registry']['applications'][0]['original_entitlement_ref']='original-entitlement#other';self.reject(data,'REPLAY_PAYMENT_APPLICATION_AUTHORITY')

    def test_original_bank_line_alias(self):
        data=fixture();r=deepcopy(data['registry']['payments'][0]);r['id']='relabelled-bank-row';data['registry']['payments'].append(r);self.reject(data,'REPLAY_BANK_LINE_ALIAS')

    def test_issue_values_recomputed_from_originals_not_trusted(self):
        for change in [lambda d:d['registry']['issued_artifacts'][0].update(earned='90'),lambda d:d['registry']['issued_artifacts'][0].update(opening_cumulative_basis='1'),lambda d:d['registry']['receipts'][0].update(base_amount='180')]:
            data=fixture();change(data);self.reject(data,'REPLAY_ORIGINAL_ISSUE_RECONCILIATION')

    def test_issue_receipt_completeness_and_original_known_view(self):
        data=fixture();data['registry']['issued_artifacts'][0]['complete']=False;self.reject(data,'REPLAY_COMPLETE_ORIGINAL_ISSUE')
        data=fixture();data['registry']['receipts'][0]['observed_at']='2026-04-03T00:00:00Z';self.reject(data,'REPLAY_ORIGINAL_KNOWN_VIEW')

    def test_original_period_and_issue_predecessor_links(self):
        data=fixture('dependent');data['registry']['periods'][1]['predecessor_period_id']='missing';self.reject(data,'REPLAY_BROKEN_DEPENDENCY')
        data=fixture('dependent');data['registry']['issued_artifacts'][1]['predecessor_issue_id']=None;self.reject(data,'REPLAY_BROKEN_ISSUE_PREDECESSOR')

    def test_complete_dependent_suffix_cannot_omit_following_tier_period(self):
        data=fixture('dependent');data['authorities'][0]['dependent_period_ids']=['p1'];self.reject(data,'REPLAY_COMPLETE_DEPENDENT_CHAIN')
        data=fixture('dependent');data['authorities'][0]['dependent_period_ids']=['p2','p1'];self.reject(data,'REPLAY_COMPLETE_DEPENDENT_CHAIN')

    def test_authority_requires_exact_original_issue_replacement_and_predecessor(self):
        for key,value in [('original_issue_id','issue:other'),('replacement_id','replacement:other'),('original_receipt_id','receipt:p2'),('predecessor_result_ref','supplied-issued-result#wrong')]:
            data=fixture();data['authorities'][0][key]=value;self.reject(data,'REPLAY_CORRECTION_LINK')

    def test_authority_scope_route_and_date(self):
        data=fixture();data['authorities'][0]['scope']['pool_id']='other';self.reject(data,'REPLAY_FACT_SCOPE')
        for change in [lambda a:a.update(route='prospective'),lambda a:a.update(approved=False),lambda a:a.update(apply_revised_basis_to_future=False),lambda a:a.update(recorded_date='2026-07-01')]:
            data=fixture();change(data['authorities'][0]);self.reject(data,'REPLAY_CORRECTION_AUTHORITY')

    def test_future_and_exact_cutoff_evidence_are_atomic(self):
        for change,code in [(lambda d:d['replacements'][0].update(observed_at=d['cutoff']),'REPLAY_SOURCE_OBSERVATION'),(lambda d:d['evidence'][0].update(observed_at=d['cutoff']),'REPLAY_EVIDENCE_SCOPE_APPROVAL_CUTOFF')]:
            data=fixture();change(data);self.reject(data,code)
        data=fixture();row=deepcopy(data['evidence'][0]);row.update(id='unused-future',observed_at='2027-01-01T00:00:00Z');data['evidence'].append(row);self.reject(data,'REPLAY_EVIDENCE_SCOPE_APPROVAL_CUTOFF')

    def test_original_replacement_identity_and_date_links(self):
        data=fixture();data['replacements'][0]['original_basis_ref']='original-sales#missing';self.reject(data,'REPLAY_REPLACEMENT_LINK')
        data=fixture();data['replacements'][0]['effective_date']='2026-01-16';self.reject(data,'REPLAY_REPLACEMENT_LINK')
        data=fixture();data['replacements'][0]['original_receipt_id']='unknown';self.reject(data,'REPLAY_REPLACEMENT_ORIGINAL_REQUIRED')

    def test_current_cash_unknown_or_nonempty_is_not_zero(self):
        data=fixture();data['cash_population']['complete']=False;self.reject(data,'REPLAY_CURRENT_CASH_UNKNOWN')
        data=fixture();data['cash_population'].update(event_ids=['bank-new'],total='1');self.reject(data,'REPLAY_NONEMPTY_CURRENT_CASH_VARIANT_REQUIRED')

    def test_correction_population_missing_unknown_or_nonbijective(self):
        data=fixture();data['correction_population']['complete']=False;self.reject(data,'REPLAY_COMPLETE_CORRECTION_POPULATION')
        data=fixture();data['correction_population']['request_ids']=[];self.reject(data,'REPLAY_COMPLETE_CORRECTION_POPULATION')
        data=fixture();data['requests']=[];data['correction_population']['request_ids']=[];self.reject(data,'REPLAY_CORRECTION_REFERENCE_POPULATION')

    def test_duplicate_and_relabelled_original_correction_reject(self):
        data=fixture();data['requests'].append(deepcopy(data['requests'][0]));self.reject(data,'REPLAY_DUPLICATE_ID')
        data=fixture();repl=deepcopy(data['replacements'][0]);repl.update(id='replacement:p1-relabel',original_ref='original-replacement#relabel');a=deepcopy(data['authorities'][0]);a.update(id='authority:relabel',replacement_id=repl['id'],original_ref='authority#relabel');req=deepcopy(data['requests'][0]);req.update(id='request:relabel',authority_id=a['id'],replacement_id=repl['id'],sequence=1)
        data['replacements'].append(repl);data['authorities'].append(a);data['requests'].append(req)
        data['correction_population'].update(request_ids=[x['id']for x in data['requests']],replacement_ids=[x['id']for x in data['replacements']],authority_ids=[x['id']for x in data['authorities']]);self.reject(data,'REPLAY_CORRECTION_ALREADY_CONSUMED')

    def test_replacement_basis_cannot_be_fresh_current_receipt_basis(self):
        data=fixture();data['receipts'][0]['original_ref']=data['replacements'][0]['original_ref'];self.reject(data,'REPLAY_CORRECTION_LINE_ALIAS')

    def test_positive_balance_scope_rejects_overpayment_without_floor(self):
        data=fixture();data['replacements'][0]['base_amount']='140';self.reject(data,'REPLAY_OVERPAYMENT_RECOVERY_VARIANT_REQUIRED')
        data=fixture('dependent');data['replacements'][0]['base_amount']='160';r=dependent_replay(data)
        self.assertEqual((r['replayed_period_controls'][1]['closing_cumulative_basis'],r['replayed_period_controls'][1]['earned'],r['outstanding']),(220,6,6))
        self.assertEqual(r['replayed_period_controls'][1]['receipt_details'][0]['upper_basis'],0)

    def test_exact_fraction_and_submicrosecond_offset_lexemes(self):
        data=fixture('dependent');data['replacements'][0]['base_amount']='179';r=dependent_replay(data);self.assertEqual(r['outstanding'],F(87,5));self.assertEqual(r['authorized_correction_credit'],F(-63,5))
        data=fixture();data['receipts'][0]['base_amount']='60.000';data['receipts'][0]['observed_at']='2026-05-16t01:00:00.000000000001+01:00';data['population']['gross_basis_total']='60/1';r=dependent_replay(data)
        self.assertEqual(r['outstanding'],40);self.assertEqual(r['closing_state']['history'][0]['facts']['receipts'],data['receipts'])

    def test_noop_replacement_is_consumed_with_zero_adjustment(self):
        data=fixture(route='prospective');data['replacements'][0]['base_amount']='200';r=dependent_replay(data)
        self.assertEqual((r['outstanding'],r['current_posted_adjustment']),(50,0));self.assertEqual(r['consumed_correction_ids'],['request:p1'])
        self.assertEqual(dependent_replay(successor(data,r))['authorized_correction_credit'],0)

    def test_serialized_state_financial_and_consumption_tampering(self):
        original=fixture();first=dependent_replay(original)
        for change,code in [(lambda d:d['opening_state'].update(recognized_entitlement='999'),'REPLAY_OPENING_RECONCILIATION'),(lambda d:d['opening_state'].update(consumed_correction_ids=[]),'REPLAY_OPENING_RECONCILIATION'),(lambda d:d['opening_state']['history'][0]['result'].update(current_recognized='0'),'REPLAY_HISTORY_FINANCIAL_REPLAY')]:
            data=successor(original,first);change(data);data['prior_result']['closing_state']=deepcopy(data['opening_state']);self.reject(data,code)

    def test_current_predecessor_actual_summary_and_registry_pins(self):
        original=fixture();first=dependent_replay(original)
        data=successor(original,first);del data['prior_result'];self.reject(data,'REPLAY_PREDECESSOR_REQUIRED')
        data=successor(original,first);data['prior_result']['source_case_id']='wrong';self.reject(data,'REPLAY_PREDECESSOR_MISMATCH')
        data=successor(original,first);data['predecessor_period_id']='wrong';self.reject(data,'REPLAY_BROKEN_DEPENDENCY')
        data=successor(original,first);data['predecessor_result_ref']='wrong';self.reject(data,'REPLAY_OPENING_RECONCILIATION')
        data=successor(original,first);data['registry']['terms'][0]['flat_rate']='0.4';self.reject(data,'REPLAY_ORIGINAL_ISSUE_RECONCILIATION')

    def test_route_cannot_change_during_carry(self):
        original=fixture();first=dependent_replay(original);data=successor(original,first);data['policy']=fixture(route='prospective')['policy'];self.reject(data,'REPLAY_PINNED_ORIGINALS_OR_ROUTE')

    def test_physical_permutations_preserve_every_reported_financial_value(self):
        data=fixture('dependent','prospective');first=dependent_replay(data);other=deepcopy(data)
        for value in other['registry'].values():
            if isinstance(value,list):value.reverse()
        other['evidence'].reverse();second=dependent_replay(other)
        self.assertEqual({k:v for k,v in first.items()if k!='closing_state'},{k:v for k,v in second.items()if k!='closing_state'})

    def test_unicode_original_identities_are_lossless_and_distinct(self):
        data=fixture();names={'participant':'participant:e\u0301/\u96ea','distributor':'distributor:\u00e9'}
        def rename(value):
            if isinstance(value,dict):return {k:rename(v)for k,v in value.items()}
            if isinstance(value,list):return [rename(v)for v in value]
            return names.get(value,value)if isinstance(value,str)else value
        data=rename(data);r=dependent_replay(data);self.assertEqual(r['outstanding'],40);self.assertEqual(r['closing_state']['scope'],data['scope']);self.assertEqual(r['closing_state']['registry']['payments'],data['registry']['payments'])

    def test_upward_revision_is_a_signed_calculation_not_a_new_payment(self):
        data=fixture('dependent','prospective');data['replacements'][0]['base_amount']='220';r=dependent_replay(data);self.assert_bridge(r)
        self.assertEqual([x['economic_earned']for x in r['period_lines']],[110,12,0]);self.assertEqual((r['authorized_correction_credit'],r['current_recognized'],r['outstanding']),(12,12,42))

    def test_complete_empty_corrections_do_not_invent_a_revision(self):
        data=fixture();data['replacements']=[];data['authorities']=[];data['requests']=[];data['correction_population'].update(request_ids=[],replacement_ids=[],authority_ids=[]);r=dependent_replay(data)
        self.assertEqual((r['authorized_correction_credit'],r['outstanding']),(0,50));self.assertEqual(r['consumed_correction_ids'],[])

    def test_authority_cannot_reference_an_issue_that_did_not_yet_exist(self):
        data=fixture();data['authorities'][0].update(approved_date='2026-01-17',recorded_date='2026-01-17');self.reject(data,'REPLAY_AUTHORITY_PRECEDES_ISSUE')

    def test_current_entitlement_line_cannot_alias_old_receipt_line(self):
        data=fixture();data['receipts'][0]['entitlement_ref']=data['registry']['receipts'][0]['entitlement_ref'];self.reject(data,'REPLAY_ENTITLEMENT_LINE_ALIAS')

    def test_independence_and_no_input_or_previous_result_mutation(self):
        data=fixture('dependent','prospective');before=deepcopy(data);r=dependent_replay(data);self.assertEqual(data,before);r_before=deepcopy(r);dependent_replay(successor(data,r));self.assertEqual(r,r_before)
        tree=ast.parse((ROOT/'oracles/dependent_replay.py').read_text(encoding='utf-8'));imports={n.module.split('.')[0]for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)}|{a.name.split('.')[0]for n in ast.walk(tree)if isinstance(n,ast.Import)for a in n.names};self.assertEqual(imports,{'copy','datetime','fractions','re'})

if __name__=='__main__':unittest.main()
