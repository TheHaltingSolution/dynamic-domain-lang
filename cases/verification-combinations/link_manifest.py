"""Export the registry-pinned dependency closure for quarterly recovery."""
import argparse
from pathlib import Path

from spl_compiler.codecs import read_json, write_json
from spl_compiler.modules import linking_manifest, resolve_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    module = resolve_module(read_json(folder / "reference.json"), folder.parents[1])
    write_json(args.output, linking_manifest(module))


if __name__ == "__main__":
    main()
