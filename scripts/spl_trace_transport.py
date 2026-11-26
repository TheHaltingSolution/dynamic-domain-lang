"""Compatibility CLI for the production lossless trace transport."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spl_compiler.trace_transport import *

if __name__ == "__main__":
    raise SystemExit(main())
