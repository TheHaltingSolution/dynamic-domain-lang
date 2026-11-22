"""A review must identify the fixture bytes actually consumed, despite edits."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import m1_demo


class M1DemoTests(unittest.TestCase):
    def test_review_retains_loaded_bytes_when_source_file_changes_during_execution(self):
        raw = (m1_demo.ROOT / 'cases/m1/fixtures/period-marginal.json').read_bytes()
        expected = {name: Fraction(value) for name, value in
                    [('basis', 150), ('uncapped', 20), ('entitlement', 20), ('closing_balance', 0)]}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            fixtures = folder / 'fixtures'
            fixtures.mkdir()
            source = fixtures / 'contract.json'
            source.write_bytes(raw)
            output = folder / 'review'

            def execute(_package, _root, *, backend, artifact_dir):
                self.assertEqual(backend, 'compare')
                Path(artifact_dir).mkdir(parents=True)
                replacement = json.loads(raw)
                replacement['facts'][0]['amount'] = '999'
                source.write_text(json.dumps(replacement), encoding='utf-8')
                return {'status': 'calculated', 'diagnostics': [],
                        'results': {'comparison': {name: str(value) for name, value in expected.items()}},
                        'result_digest': 'test-result', 'semantic_run_digest': 'test-semantic', 'module_closure': []}

            with patch.object(m1_demo.sys, 'argv', ['m1_demo.py', '--fixtures', str(fixtures), '--output', str(output)]), \
                 patch.object(m1_demo, 'identities', return_value=('compiler', 'runtime')), \
                 patch.object(m1_demo, 'register_m1', return_value={}), \
                 patch.object(m1_demo, 'm1_package', return_value={}), \
                 patch.object(m1_demo, 'ordinary_royalties', return_value=expected) as oracle, \
                 patch.object(m1_demo, 'run_module_package', side_effect=execute), \
                 patch('builtins.print'):
                m1_demo.main()
            row = json.loads((output / 'summary.json').read_text(encoding='utf-8'))['cases'][0]
            self.assertNotEqual(source.read_bytes(), raw)
            self.assertEqual(row['fixture_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual((output / row['artifact_subdirectory'] / 'neutral-fixture.json').read_bytes(), raw)
            self.assertEqual(oracle.call_args.args[0]['facts'][0]['amount'], '150')


if __name__ == '__main__':
    unittest.main()
