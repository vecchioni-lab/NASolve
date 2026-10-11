#!/usr/bin/env python3
"""Build a source-bundled native candidate probe without private input payloads."""
import argparse
from pathlib import Path

from build_synthetic_dna_shuttle import build, _sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--narestraints-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    metadata = build(Path(__file__).resolve().parents[1], args.narestraints_root.resolve(),
                     args.output, template_name="cif_generation_probe_template.py")
    print("Output:", args.output)
    print("SHA-256:", _sha(args.output.read_bytes()))
    print("Runtime files:", len(metadata["runtime_files"]))


if __name__ == "__main__":
    main()
