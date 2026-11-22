"""The supplied-date workaround remains useful with or without the extension."""
from copy import deepcopy
import unittest

from cases.extensibility.build_modules import ROOT, deadline_package, register_deadline
from oracles.r1 import supplied_due_reserve
from spl_compiler.codecs import exact, read_json
from spl_compiler.modules import run_module_package


class SuppliedDeadlineTests(unittest.TestCase):
    def test_supplied_date_before_and_on_deadline_against_neutral_oracle(self):
        reference = register_deadline()
        original = read_json(ROOT / 'cases/r1/supplied-due-reserve.json')
        for close in ['2025-02-27', '2025-02-28']:
            fixture = deepcopy(original)
            fixture['close_date'] = close
            expected = supplied_due_reserve(fixture)
            result = run_module_package(deadline_package(fixture, reference=reference), ROOT)
            self.assertEqual(result['diagnostics'], [], result)
            line = result['results']['reserve_ledger']
            self.assertEqual(exact(line['released']), expected['released'])
            self.assertEqual(exact(line['closing_balance']), expected['closing_balance'])
            self.assertEqual(exact(result['closing_state'][0]['quantity']), expected['closing_balance'])


if __name__ == '__main__':
    unittest.main()
