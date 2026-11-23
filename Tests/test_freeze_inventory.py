"""A replay package must retain the schemas its canonical runner reads."""
import unittest

from scripts.spl_freeze import ROOT, source_files


class FreezeInventoryTests(unittest.TestCase):
    def test_canonical_runtime_and_schema_dependencies_are_in_source_archive(self):
        inventory = {path.relative_to(ROOT).as_posix() for path in source_files()}
        required = {'lean-toolchain', 'lakefile.toml', 'SPL/Runtime.lean', 'SPL/Bindings.lean',
                    'spl_compiler/modules.py', 'spl_compiler/codecs.py',
                    'schemas/spl-module-descriptor.schema.json', 'schemas/spl-module-package.schema.json',
                    'schemas/spl-bounded-package.schema.json', 'scripts/spl_check.py',
                    'scripts/spl_conformance.py', 'docs/spl/feature-test-matrix.json',
                    'validation/__init__.py', 'validation/generated_cases.py',
                    'validation/trace_coverage.py'}
        self.assertTrue(required <= inventory, required - inventory)
        self.assertFalse(any(name.startswith(('.lake/', '.git/')) for name in inventory))


if __name__ == '__main__':
    unittest.main()
