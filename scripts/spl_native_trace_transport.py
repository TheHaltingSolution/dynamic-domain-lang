"""Compatibility CLI for the production bounded native compact reader."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spl_compiler.native_trace import *

if __name__ == "__main__":
    raise SystemExit(main())
