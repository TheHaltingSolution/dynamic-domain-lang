"""Versioned policy closure, real used-expression checks and review navigation."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from spl_compiler.adapter import rq07
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import DataError, digest, file_digest, loads, read_json, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.fixtures import lg_package, sv_package
from spl_compiler.policies import policy_closure, policy_review, REGISTRY
from spl_compiler.readable import parse_readable
from spl_compiler.run import bind_package, project, run_package, normalize_target, semantic_digest
from spl_compiler.lean_tools import compile_schedule, interpret_schedule, lean


ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding='utf-8')


def dual_date_packages():
    """Projected discriminator views; not an issued RQ-07 raw-source package."""
    incurred = sv_package()
    for fact in incurred['financial_facts']:
        fact['dates']['posting_date'] = '2026-02-01'
        if fact['fact_id'] == 'cost-a':
            fact['dates']['incurred_date'] = '2026-04-01'
            fact['temporal_basis']['date'] = '2026-04-01'
    posted = deepcopy(incurred)
    posted['profile'] = 'sv-rq07-posted-v1'
    posted['parameters']['cost_date_basis'] = 'posting_date'
    return [('cases/sv/sv01-readable.spl', incurred, '20000'),
            ('cases/sv/rq07-readable.spl', posted, '18000')]


class PolicyTests(unittest.TestCase):
    def assert_policy_error(self, code, text, package=None, root=ROOT):
        with self.assertRaises(DataError) as raised:
            policy_closure(text, 'authored.spl', package or sv_package(), root)
        self.assertEqual(code, raised.exception.code)
        return raised.exception

    def test_three_profiles_resolve_real_document_and_registry_pins(self):
        rq = rq07(ROOT / 'cases/rq07/source', observed_at='2026-04-03T00:00:00Z',
                  ingested_at='2026-11-20T00:00:00Z')
        for path, package, policy_id in [
            ('cases/sv/sv01-readable.spl', sv_package(), 'sv-incurred@1'),
            ('cases/sv/rq07-readable.spl', rq, 'rq07-posted@1'),
            ('cases/lg/lg01-readable.spl', lg_package(), 'lg-cleared@1'),
        ]:
            with self.subTest(policy_id=policy_id):
                closure = policy_closure(source(path), path, package, ROOT)
                self.assertEqual(1, len(closure))
                pin = closure[0]
                self.assertEqual(policy_id, pin['policy_id'])
                self.assertEqual(package['profile'], pin['profile'])
                self.assertEqual(file_digest(ROOT / pin['document']['locator']), pin['document']['sha256'])
                self.assertEqual(file_digest(ROOT / REGISTRY), pin['registry']['sha256'])
                registry = json.loads(source(REGISTRY))
                self.assertEqual(digest(registry['policies'][policy_id]), pin['registry']['entry_sha256'])

    def test_original_source_has_no_policy_dependency_or_registry_read(self):
        self.assertEqual([], policy_closure(source('cases/sv/sv01.spl'), 'original.spl', {}, ROOT / 'missing-repository'))

    def test_readable_requires_resolved_profile_specific_policy(self):
        text = source('cases/sv/sv01-readable.spl')
        self.assert_policy_error('POLICY_REQUIRED', text.replace('Incorporate policy "sv-incurred@1".\n', ''))
        unknown = self.assert_policy_error('POLICY_UNKNOWN', text.replace('sv-incurred@1', 'unknown-policy@1'))
        self.assertEqual(3, unknown.span['line'])
        self.assert_policy_error('POLICY_PROFILE', text, lg_package())

    def test_display_renames_whitespace_and_unused_bindings_preserve_used_program(self):
        text = source('cases/sv/sv01-readable.spl')
        renamed = text.replace('Skouras', 'Orion').replace('Ventura', 'Lyra')
        renamed = renamed.replace('c.asset_id == picture.asset_id', 'c.asset_id  ==  picture.asset_id')
        renamed += '  Bind "Unused Technical Alias" to USD 123.\n'
        baseline = policy_closure(text, 'before.spl', sv_package(), ROOT)
        self.assertEqual(baseline, policy_closure(renamed, 'after.spl', sv_package(), ROOT))

    def test_date_selection_change_and_unused_good_alias_spoof_fail(self):
        text = source('cases/sv/sv01-readable.spl')
        changed = text.replace('in_period(c.incurred_date, accounting_period)', 'true')
        error = self.assert_policy_error('POLICY_CORE_MISMATCH', changed)
        self.assertIsNotNone(error.span)
        # Keep the old, correct selector in unused bindings. Membership in the
        # footer is insufficient: only the expressions used by the real program
        # can satisfy the expected core signatures.
        spoofed = changed + (
            '  Bind "Unused Correct Costs" to sum(filter(eligible_costs, c => '
            'c.asset_id == picture.asset_id and in_period(c.incurred_date, accounting_period)), c => c.amount).\n'
        )
        self.assert_policy_error('POLICY_CORE_MISMATCH', spoofed)

    def test_main_method_guards_scope_and_output_wiring_are_pinned(self):
        text = source('cases/lg/lg01-readable.spl')
        for changed in [
            text.replace('Gross Participation Rate of Gross Payout Base less Producer Fee Offset',
                         'Gross Participation Rate of Gross Payout Base'),
            text.replace('Net Participation Rate of Crossed Net Subtotal',
                         'Net Participation Rate of Crossed Net Subtotal less Producer Fee Offset'),
            text.replace('Outside Hurdle Effective Date < Quarter Start',
                         'Outside Hurdle Effective Date <= Quarter Start'),
            text.replace('the greater of USD 0 and (Gross Participation Rate',
                         'the greater of USD 1 and (Gross Participation Rate'),
            text.replace('Report "settlement": Agreement', 'Report "changed-settlement": Agreement'),
            text.replace('Settle "the Participant" with policy.participant_id.',
                         'Settle "the Participant" with policy.pool_id.'),
        ]:
            with self.subTest(changed=changed):
                self.assert_policy_error('POLICY_CORE_MISMATCH', changed, lg_package())
        self.assert_policy_error('POLICY_CORE_MISMATCH',
                                 source('cases/sv/sv01-readable.spl').replace('25%', '30%'))

    def test_parameter_values_and_main_footer_origins_are_reviewable(self):
        text = source('cases/lg/lg01-readable.spl')
        report = policy_review(text, 'readable-lg.spl', lg_package(), ROOT)
        policy = report['policies'][0]
        self.assertEqual(3, policy['incorporation_span']['line'])
        values = {item['path']: item['value'] for item in policy['parameters']}
        self.assertEqual('0.25', values['parameters.policy']['video_proxy'])
        self.assertEqual('0.20', values['parameters.policy']['gross_rate'])
        self.assertEqual('12', values['parameters.producer_fee_offset']['value'])
        rule = next(item for item in report['rules'] if item['text'].startswith('Gross Payout Base is '))
        support = next(item for item in rule['supporting_expressions'] if item['label'] == 'the current receipts adjusted by the supplied video proxy')
        self.assertIn('if r.is_home_video then policy.video_proxy else 1', support['expression'])
        self.assertGreater(support['span']['line'], rule['span']['line'])
        self.assertEqual('readable-lg.spl', support['span']['source'])
        self.assertIn('not a proof', report['limitation'])
        # Review values are copies, not mutable aliases into the canonical input.
        package = lg_package()
        changed = policy_review(text, 'lg.spl', package, ROOT)
        changed['policies'][0]['parameters'][0]['value']['gross_rate'] = '9'
        self.assertEqual('0.20', package['parameters']['policy']['gross_rate'])

    def test_missing_required_parameter_blocks_before_review(self):
        package = sv_package()
        del package['parameters']['funding_snapshot']
        self.assert_policy_error('POLICY_PARAMETER', source('cases/sv/sv01-readable.spl'), package)

    def test_document_and_registry_bytes_change_dependency_pins_and_bad_locators_fail(self):
        text = source('cases/sv/sv01-readable.spl')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / 'docs/spl/policies', root / 'docs/spl/policies')
            before = policy_closure(text, 'sv.spl', sv_package(), root)
            document = root / before[0]['document']['locator']
            document.write_text(document.read_text(encoding='utf-8') + '\nReviewed version note.\n', encoding='utf-8')
            after = policy_closure(text, 'sv.spl', sv_package(), root)
            self.assertNotEqual(before[0]['document']['sha256'], after[0]['document']['sha256'])
            self.assertEqual(before[0]['registry'], after[0]['registry'])
            registry_path = root / REGISTRY
            registry = json.loads(registry_path.read_text(encoding='utf-8'))
            registry_path.write_text(json.dumps(registry, indent=3), encoding='utf-8')
            reformatted = policy_closure(text, 'sv.spl', sv_package(), root)
            self.assertNotEqual(after[0]['registry']['sha256'], reformatted[0]['registry']['sha256'])
            self.assertEqual(after[0]['registry']['entry_sha256'], reformatted[0]['registry']['entry_sha256'])
            registry['policies']['sv-incurred@1']['document'] = '../outside.md'
            registry_path.write_text(json.dumps(registry), encoding='utf-8')
            self.assert_policy_error('POLICY_LOCATOR', text, root=root)
            registry_path.write_text('{"version":"1","version":"2","policies":{}}', encoding='utf-8')
            self.assert_policy_error('POLICY_REGISTRY', text, root=root)

    def test_malformed_registry_and_missing_policy_document_have_policy_errors(self):
        text = source('cases/sv/sv01-readable.spl')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / 'docs/spl/policies', root / 'docs/spl/policies')
            registry_path = root / REGISTRY
            original = json.loads(registry_path.read_text(encoding='utf-8'))
            for mutate in [
                lambda entry: entry.update(core_signatures={'format': 'unknown'}),
                lambda entry: entry.update(parameter_paths=[{}]),
                lambda entry: entry.update(bindings=[]),
            ]:
                registry = deepcopy(original)
                mutate(registry['policies']['sv-incurred@1'])
                registry_path.write_text(json.dumps(registry), encoding='utf-8')
                self.assert_policy_error('POLICY_REGISTRY', text, root=root)
            original['policies']['sv-incurred@1']['document'] = 'docs/spl/policies/missing.md'
            registry_path.write_text(json.dumps(original), encoding='utf-8')
            self.assert_policy_error('POLICY_DOCUMENT', text, root=root)

    def test_incurred_posted_dates_in_different_quarters_discriminate(self):
        # A deliberately dual-date synthetic fact distinguishes selector policy.
        # These are projected/reference views, not an issued RQ-07 raw package.
        outcomes = []
        for path, package, expected in dual_date_packages():
            text = source(path)
            self.assertEqual(1, len(policy_closure(text, path, package, ROOT)))
            inputs, openings, _, _ = project(package)
            # The projection uses technical opening alias names; the evaluator
            # accepts those as well as declaration names.
            outcome = evaluate(check_schedule(parse_readable(text)), inputs, openings)
            self.assertEqual('calculated', outcome.status, outcome.diagnostics)
            outcomes.append(outcome.emissions['pool']['payable'])
        self.assertEqual([Fraction(20000), Fraction(18000)], outcomes)

    def test_native_incurred_posted_crossperiod_discriminator_agrees_three_paths(self):
        directory = ROOT / '.lake/policy-tests'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            for index, (path, package, expected) in enumerate(dual_date_packages()):
                inputs, openings, _, _ = project(package)
                reference = evaluate(check_schedule(parse_readable(source(path))), inputs, openings).to_dict()
                bindings = Path(temporary) / f'bindings-{index}.json'
                write_json(bindings, {'inputs': inputs, 'openings': {'prepayment': next(iter(openings.values()))}})
                interpreted = normalize_target(interpret_schedule(ROOT / path, bindings))
                target = compile_schedule(ROOT / path, Path(temporary) / f'Settlement-{index}.lean')
                emitted = normalize_target(loads(lean(['--run', target, bindings])))
                for result in [reference, interpreted, emitted]:
                    self.assertEqual([], result['diagnostics'])
                    self.assertEqual(expected, result['emissions']['pool']['payable'])
                    self.assertEqual(reference['closing'], result['closing'])

    def test_wrapper_blocks_tampered_policy_document_pin_atomically(self):
        path = ROOT / 'cases/sv/sv01-readable.spl'
        package = bind_package(sv_package(), path)
        package['incorporated_policies'][0]['document']['sha256'] = '0' * 64
        result = run_package(package, path, backend='reference')
        self.assertEqual('blocked', result['status'])
        self.assertEqual('POLICY_CLOSURE_MISMATCH', result['diagnostics'][0]['code'])
        self.assertEqual([], result['statements'])
        self.assertEqual([], result['closing_state'])

    def test_wrapper_requires_closure_and_manifest_policy_references(self):
        path = ROOT / 'cases/sv/sv01-readable.spl'
        baseline = bind_package(sv_package(), path)
        for field in ['incorporated_policies', 'policy_refs']:
            package = deepcopy(baseline)
            del (package if field == 'incorporated_policies' else package['manifest'])[field]
            result = run_package(package, path, backend='reference')
            self.assertEqual('blocked', result['status'])
            self.assertEqual('MISSING_FIELD', result['diagnostics'][0]['code'])
            self.assertEqual([], result['statements'])
            self.assertEqual([], result['closing_state'])

    def test_reference_wrapper_retains_authored_bytes_policies_and_dual_origins(self):
        path = ROOT / 'cases/sv/sv01-readable.spl'
        package = bind_package(sv_package(), path)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            result = run_package(package, path, artifact_dir=output, backend='reference')
            self.assertEqual([], result['diagnostics'])
            self.assertEqual('18000', result['statements'][0]['payable'])
            self.assertEqual(path.read_bytes(), (output / 'source.spl').read_bytes())
            self.assertEqual(file_digest(path), file_digest(output / 'source.spl'))
            self.assertEqual('schedule@1#sha256:' + file_digest(output / 'source.spl'), package['manifest']['schedule_ref'])
            for policy in package['incorporated_policies']:
                for dependency in [policy['document'], policy['registry']]:
                    retained = output / 'review-sources' / dependency['locator']
                    self.assertEqual(dependency['sha256'], file_digest(retained))
                    self.assertEqual((ROOT / dependency['locator']).read_bytes(), retained.read_bytes())
            review = read_json(output / 'policy-review.json')
            rule = next(item for item in review['rules'] if item['text'].startswith('Allowed Deductions are'))
            support = next(item for item in rule['supporting_expressions'] if item['label'] == 'the deductions allowed by the Net Profits Schedule')
            self.assertIn('c.incurred_date', support['expression'])
            self.assertGreater(support['span']['line'], rule['span']['line'])
            self.assertEqual(str(path), support['span']['source'])

    def test_policy_content_pins_affect_semantic_identity_but_fact_permutation_does_not(self):
        path = ROOT / 'cases/sv/sv01-readable.spl'
        baseline = bind_package(sv_package(), path)
        inputs, openings, _, _ = project(baseline)
        expected = semantic_digest(baseline, inputs, openings)
        # Policy SHA-256 values identify the economic review package, even
        # though transport/source-batch SHA-256 fields are physical metadata.
        for dependency in ['document', 'registry']:
            changed = deepcopy(baseline)
            changed['incorporated_policies'][0][dependency]['sha256'] = '0' * 64
            self.assertNotEqual(expected, semantic_digest(changed, inputs, openings))
        reordered = deepcopy(baseline)
        for field in ['financial_facts', 'evidence_events', 'mappings']:
            reordered[field].reverse()
        reordered['parameters']['cost_decisions'].reverse()
        reordered_inputs, reordered_openings, _, _ = project(reordered)
        self.assertEqual(expected, semantic_digest(reordered, reordered_inputs, reordered_openings))


if __name__ == '__main__':
    unittest.main()
