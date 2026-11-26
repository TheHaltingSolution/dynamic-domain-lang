"""Original-fact generation/guard controls; native chain credit is separate."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from oracles.skouras import SkourasOracleError,skouras
from scripts import spl_audited_stage_chain as chain
from spl_compiler.codecs import write_json
from spl_compiler.run import bind_package
from spl_compiler.schema import validate_package
from validation.mixed_workloads import canonical_bytes,generate_mixed


def generation_head(oracle):
    # An explicitly synthetic generator unit control, not actual native carry.
    value=oracle['pool']['closing_prepayment']
    return {"status":"calculated","diagnostics":[],"closing":{"prepayment":{"numerator":str(value.numerator),"denominator":str(value.denominator)}},
            "emissions":{"pool":{key:deepcopy(oracle['pool'][key]) for key in ('period','agreement_id','participant_id','pool_id')}}}


class AuditedStageChainTests(unittest.TestCase):
    def test_original_single_quarter_authority_is_not_waived(self):
        base=generate_mixed(100)
        changed=chain.successor_workload(base,generation_head(skouras(base['neutral'])),'a'*64,2)
        with self.assertRaisesRegex(SkourasOracleError,'SV_AGREEMENT_PERIOD'):
            skouras(changed['neutral'])

    def test_explicit_chain_authority_is_pinned_from_first_close(self):
        base=generate_mixed(1000);before=canonical_bytes(base)
        extended=chain.chain_profile(base)
        authority=extended['stage_chain_authority']
        self.assertEqual(authority['document']['profile'],'rr03-stage-chain/1')
        self.assertEqual(authority['document']['observed_at'],'2025-12-15T00:00:00Z')
        self.assertTrue(authority['document']['approved'])
        p=extended['neutral']['package']
        for row in p['agreements']+p['roles']+p['mappings']:
            self.assertEqual(row['effective'],{'start':'2026-01-01','end':'2027-01-01'})
        self.assertEqual(p['agreements'][0]['version'],'synthetic-stage-chain-v1')
        self.assertEqual(p['parameters'],base['neutral']['package']['parameters'])
        self.assertEqual(canonical_bytes(base),before)
        self.assertEqual(canonical_bytes(generate_mixed(1000)),before)
        validate_package(bind_package(p,chain.ROOT/'cases/sv/sv01.spl'))

    def test_four_generated_snapshots_have3850_distinct_originals_and_once_funding(self):
        base=chain.chain_profile(generate_mixed(1000))
        original_events=deepcopy(base['neutral']['package']['evidence_events'])
        oracle=skouras(base['neutral'])
        funding=chain.funding_control(base,oracle,original_events)
        identities=set();recovered=[]
        for index in range(1,5):
            current=base if index==1 else chain.successor_workload(base,generation_head(oracle),'a'*64,index)
            oracle=skouras(current['neutral'])
            recovered.append(oracle['pool']['recovered'])
            self.assertEqual(chain.funding_control(current,oracle,original_events),funding)
            package=current['neutral']['package']
            self.assertEqual(package['evidence_events'],original_events)
            fact_ids={row['fact_id'] for row in package['financial_facts']}
            self.assertFalse(identities & fact_ids)
            identities.update(fact_ids)
            counts=chain.close_counts(current,index)
            self.assertEqual(counts['canonical_guard_objects'],1000)
            self.assertEqual(counts['new_financial_originals'],950)
            self.assertEqual(counts['reused_funding_originals'],0 if index==1 else 50)
            validate_package(bind_package(package,chain.ROOT/'cases/sv/sv01.spl'))
        identities.update(row['event_id'] for row in original_events)
        self.assertEqual(len(identities),3850)
        self.assertEqual(sum(recovered),250)
        self.assertEqual(recovered[1:],[0,0,0])

    def test_predecessor_boundary_hash_shape_and_blocked_outputs_rejected(self):
        base=chain.chain_profile(generate_mixed(100))
        head=generation_head(skouras(base['neutral']))
        for altered,identity,index in (({**head,'status':'blocked'},'a'*64,2),(head,'bad',2),(head,'a'*64,5),
                                        ({**head,'closing':{}},'a'*64,2),(head,'a'*64,3)):
            with self.assertRaises(ValueError):chain.successor_workload(base,altered,identity,index)

    def test_old_funding_cannot_be_renamed_or_duplicated_as_fresh(self):
        base=chain.chain_profile(generate_mixed(100))
        original=deepcopy(base['neutral']['package']['evidence_events'])
        changed=deepcopy(base);changed['neutral']['package']['evidence_events'][0]['event_id']='fresh-funding'
        with self.assertRaisesRegex(ValueError,'FUNDING_CHANGED'):
            chain.funding_control(changed,skouras(changed['neutral']),original)

    def test_failed_audit_stops_all_successor_execution_and_state(self):
        with tempfile.TemporaryDirectory() as temp:
            prerequisite=Path(temp)/'prerequisite.json';write_json(prerequisite,{})
            with patch.object(chain.protocol,'validate_mixed_report'),patch.object(chain.protocol,'mixed_pins',return_value={}), \
                 patch.object(chain,'run_close',return_value={'status':'failed','audited_head':{},'audited_closing_state':[]}) as run:
                report=chain.run_chain(Path(temp)/'chain',1000,4,{},prerequisite=prerequisite)
            self.assertEqual(run.call_count,1)
            self.assertEqual(report['status'],'failed')
            self.assertFalse(report['canonical_close_credit'])
            for row in report['closes'][1:]:
                self.assertEqual(row['status'],'not_executed')
                self.assertEqual(row['audited_closing_state'],[])


if __name__=='__main__':unittest.main()
