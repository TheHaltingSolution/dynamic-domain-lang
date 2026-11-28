"""Export the reviewed example's registry-pinned validation module closure."""
import argparse
from pathlib import Path

from spl_compiler.codecs import read_json, write_json
from spl_compiler.modules import linking_manifest, resolve_module


FOLDER = Path(__file__).resolve().parent


def example_module():
    return resolve_module(read_json(FOLDER / "reference.json"), FOLDER.parents[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_json(args.output, linking_manifest(example_module()))


if __name__ == "__main__":
    main()
