"""Run this checkout's tests, including from an extracted source freeze.

The explicit path avoids importing another checkout through an embedded Python
installation's fixed ._pth file. It changes no global environment or toolchain.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'Tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
