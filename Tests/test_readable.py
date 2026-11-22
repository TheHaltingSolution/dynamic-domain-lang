"""Readable grammar, explicit bindings, original economics and mutation checks."""
from fractions import Fraction
import json
from pathlib import Path
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import evaluate
from spl_compiler.parser import ParseError, parse
from spl_compiler.readable import expand_readable, is_readable, parse_readable, readable_policy_dependencies

ROOT = Path(__file__).resolve().parents[1]


def tiny(rules, bindings='  Bind "Amount" to amount.\n'):
    return ('Participation Schedule for A and B\n' + rules + '\nBindings:\n'
            '  Schedule Generic.\n'
            '  Using language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft".\n'
            + bindings)


def load(path):
    return (ROOT / path).read_text(encoding="utf-8")


def run_readable(source, binding_path):
    bindings = json.loads(load(binding_path))
    return evaluate(check_schedule(parse_readable(source)), bindings["inputs"], bindings["openings"])


class ReadableTests(unittest.TestCase):
    def test_three_profiles_match_original_calculations(self):
        for case, binding in [('sv/sv01', 'sv'), ('sv/rq07', 'rq07'), ('lg/lg01', 'lg')]:
            with self.subTest(case=case):
                source = load(f'cases/{case}-readable.spl')
                self.assertTrue(is_readable(source))
                outcome = run_readable(source, f'cases/{binding}/bindings.json')
                bindings = json.loads(load(f'cases/{binding}/bindings.json'))
                original = evaluate(check_schedule(parse(load(f'cases/{case}.spl'))), bindings['inputs'], bindings['openings'])
                self.assertEqual('calculated', outcome.status, outcome.diagnostics)
                self.assertEqual(original.emissions, outcome.emissions)
                self.assertEqual(original.closing, outcome.closing)
        sv = run_readable(load('cases/sv/sv01-readable.spl'), 'cases/sv/bindings.json')
        self.assertEqual(Fraction(18000), sv.emissions['pool']['payable'])
        lg = run_readable(load('cases/lg/lg01-readable.spl'), 'cases/lg/bindings.json')
        self.assertEqual(Fraction(35), lg.emissions['settlement']['payable'])

    def test_recomposes_new_names_and_rate(self):
        source = load('cases/sv/sv01-readable.spl').replace('Skouras', 'Orion').replace('Ventura', 'Lyra').replace('25%', '30%')
        outcome = run_readable(source, 'cases/sv/bindings.json')
        self.assertEqual('calculated', outcome.status)
        self.assertEqual(Fraction(17000), outcome.emissions['pool']['payable'])
        # Receipt changes also flow through selectors and formulas.
        bindings = json.loads(load('cases/sv/bindings.json'))
        bindings['inputs']['receipts'][0]['amount']['value'] = '120000'
        changed = evaluate(check_schedule(parse_readable(source)), bindings['inputs'], bindings['openings'])
        self.assertEqual(Fraction(19800), changed.emissions['pool']['payable'])

    def test_percentage_exact_and_multiword_names(self):
        source = tiny('Amount is 7.500% of USD 100.\nReport "value": Amount.')
        result = evaluate(check_schedule(parse_readable(source)), {}, {})
        self.assertEqual(Fraction(15, 2), result.emissions['value'])
        tree = parse_readable(source)
        self.assertEqual('7.500', tree['declarations'][0]['expr']['left']['left']['value'])

    def test_bound_expressions_preserve_precedence(self):
        source = tiny('Amount is 20% of Net Revenue.\nReport "value": Amount.',
                      '  Bind "Amount" to amount.\n  Bind "Net Revenue" to USD 100 - USD 10.\n')
        result = evaluate(check_schedule(parse_readable(source)), {}, {})
        self.assertEqual(Fraction(18), result.emissions['value'])

    def test_quoted_text_is_never_rewritten(self):
        source = tiny('Amount is "Amount less 25% of Cash".\nReport "value": Amount.')
        result = evaluate(check_schedule(parse_readable(source)), {}, {})
        self.assertEqual('Amount less 25% of Cash', result.emissions['value'])

    def test_branch_expressions_keep_both_authored_spans(self):
        source = tiny('If true:\n  Amount is 25% of USD 100.\nOtherwise:\n  Amount is 10% of USD 100.\nReport "value": Amount.')
        tree = parse_readable(source, 'branches.spl')
        branch = tree['declarations'][0]['expr']
        self.assertEqual(3, branch['then']['span']['line'])
        self.assertEqual(5, branch['else']['span']['line'])
        self.assertEqual('branches.spl', branch['else']['span']['source'])
        self.assertEqual(2, tree['declarations'][0]['span']['line'])

    def test_unknown_and_ambiguous_constructs_fail(self):
        bad_sources = [
            tiny('Amount is 10% of USD 100').replace('Generic.', 'Generic.'),
            tiny('If true:\n  Amount is USD 1.\nReport "value": Amount.'),
            tiny('If true:\n  Amount is USD 1.\nOtherwise:\n  Other is USD 2.'),
            tiny('Report "value": Amount, Other.'),
            tiny('For each Something:\n  Report by Item: Amount.'),
            tiny('Amount is 1.\nOtherwise:\n  Amount is 2.'),
            tiny('Account for each fiscal month.', '  Bind "fiscal month" to missing.\n'),
        ]
        for source in bad_sources:
            with self.subTest(source=source), self.assertRaises(ParseError):
                parse_readable(source)
        with self.assertRaises(ParseError):
            parse_readable(tiny('Amount is 1.').replace('Bindings:', 'Rules:'))
        with self.assertRaises(ParseError):
            parse_readable(tiny('Amount is 1.', '  Bind "Amount" to x.\n  Bind "Amount" to y.\n'))

    def test_settlement_heading_binds_a_typed_participant(self):
        source = load('cases/sv/sv01-readable.spl')
        with self.assertRaises(ParseError) as raised:
            parse_readable(source.replace('For settlement with Skouras:', 'For settlement with Another Party:'))
        self.assertEqual(source.splitlines().index('For settlement with Skouras:') + 1,
                         raised.exception.span['line'])
        from spl_compiler.model import SPLException
        with self.assertRaises(SPLException) as typed:
            check_schedule(parse_readable(source.replace('Settle "Skouras" with policy.participant_id.', 'Settle "Skouras" with policy.pool_id.')))
        self.assertEqual('TYPE_MISMATCH', typed.exception.code)

    def test_supporting_strings_and_unused_expressions_are_closed(self):
        for binding in ['  Bind "Bad\\x" to unused.\n',
                        '  Bind "Bad\\uD800" to unused.\n',
                        '  Bind "Unused" to $injection.\n']:
            with self.subTest(binding=binding), self.assertRaises(ParseError):
                parse_readable(tiny('Amount is 1.', '  Bind "Amount" to amount.\n' + binding))

    def test_indentation_is_checked(self):
        for rules in [' Amount is 1.', 'Amount is 1.\n  Amount is 2.', 'If true:\n  Amount is 1.\n   Amount is 2.\nOtherwise:\n  Amount is 3.', '\tAmount is 1.']:
            with self.subTest(rules=rules), self.assertRaises(ParseError) as raised:
                parse_readable(tiny(rules))
            self.assertEqual('READABLE_INDENTATION', raised.exception.code)

    def test_quarter_heading_is_an_executable_guard(self):
        source = load('cases/sv/sv01-readable.spl')
        expanded = expand_readable(source).source
        self.assertIn('require is_calendar_quarter(accounting_period)', expanded)
        bindings = json.loads(load('cases/sv/bindings.json'))
        bindings['inputs']['policy']['period']['end'] = '2026-03-30'
        outcome = evaluate(check_schedule(parse_readable(source)), bindings['inputs'], bindings['openings'])
        self.assertEqual('blocked', outcome.status)
        self.assertEqual({}, outcome.emissions)
        self.assertEqual({}, outcome.closing)
        self.assertEqual('READABLE_CALENDAR_QUARTER_REQUIRED', outcome.diagnostics[0]['code'])

    def test_posting_profile_never_fabricates_incurred_dates(self):
        source = load('cases/sv/rq07-readable.spl')
        expanded = expand_readable(source).source
        self.assertIn('c.recognition_date', expanded)
        self.assertNotIn('c.incurred_date', expanded)
        self.assertNotIn('SVPostingCost', expand_readable(load('cases/sv/sv01-readable.spl')).source)

    def test_incorporated_policy_is_typed_provenance_with_authored_span(self):
        source = tiny('Incorporate policy "cost-incurred@1".\nAmount is USD 1.\nReport "value": Amount.')
        tree = parse_readable(source, 'policies.spl')
        marker = tree['declarations'][0]
        self.assertEqual('incorporated_policy_0', marker['name'])
        self.assertEqual('cost-incurred@1', marker['expr']['value'])
        self.assertEqual(2, marker['span']['line'])
        result = evaluate(check_schedule(tree), {}, {})
        self.assertEqual(Fraction(1), result.emissions['value'])
        dependencies = readable_policy_dependencies(source, 'policies.spl')
        self.assertEqual('cost-incurred@1', dependencies['policies'][0]['policy_id'])
        self.assertEqual(2, dependencies['policies'][0]['span']['line'])
        self.assertEqual({'Amount': 'amount'}, dependencies['bindings'])
        self.assertEqual(source.splitlines().index('  Bind "Amount" to amount.') + 1,
                         dependencies['binding_spans']['Amount']['line'])

    def test_incorporation_rejects_duplicate_unversioned_and_nested_policies(self):
        for rules in [
            'Incorporate policy "cost-incurred".\nAmount is USD 1.',
            'Incorporate policy "cost-incurred@".\nAmount is USD 1.',
            'Incorporate policy "cost@1@2".\nAmount is USD 1.',
            'Incorporate policy "cost@1".\nIncorporate policy "cost@1".\nAmount is USD 1.',
            'For settlement with Party:\n  Incorporate policy "cost@1".\n  Amount is USD 1.',
            'Incorporate the policy described in an email.\nAmount is USD 1.',
        ]:
            with self.subTest(rules=rules), self.assertRaises(ParseError):
                parse_readable(tiny(rules, '  Bind "Amount" to amount.\n  Settle "Party" with missing.\n'))


if __name__ == '__main__':
    unittest.main()
