"""Consume an actual saved E0 closing state under the extended runtime."""
import unittest

from cases.waterfall.build_modules import ROOT, waterfall_package
from spl_compiler.codecs import exact, read_json
from spl_compiler.modules import bind_module_package, run_module_package


class ExtensionCompatibilityTests(unittest.TestCase):
    def test_real_e0_published_state_carries_into_e1_successor(self):
        saved = read_json(ROOT / 'cases/extensibility/e0-waterfall-state.json')
        fixture = read_json(ROOT / 'cases/waterfall/roundlake-like-p2.json')
        package = waterfall_package(fixture)
        package['state_cells'] = [{key: value for key, value in cell.items() if key != 'movement'}
                                  for cell in saved['closing_state']]
        self.assertTrue(all('prior_result_ref' in cell for cell in package['state_cells']))
        result = run_module_package(bind_module_package(package, ROOT), ROOT)
        self.assertEqual(result['diagnostics'], [], result)
        self.assertEqual([exact(row['recovered']) for row in result['results']['claim_movements']], [32, 8])
        self.assertEqual(exact(result['results']['control']['residual']), 35)
        self.assertEqual([exact(row['payable']) for row in result['statements']], [exact('49.5'), exact('25.5')])
        self.assertEqual(exact(result['results']['control']['closing_claims']), 0)


if __name__ == '__main__':
    unittest.main()
