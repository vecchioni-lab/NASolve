#!/usr/bin/env python3
"""Build an isolated source-graph numerical recovery diagnostic."""
import argparse
from pathlib import Path
from build_synthetic_dna_shuttle import build, _sha, prepare_branch_runner_destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--narestraints-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--delivery-prefix', default='30_Cedar')
    parser.add_argument('--local-artifact-checkout', type=Path)
    parser.add_argument('--component-control', action='append', default=[],
                        help='Bundle a hash-pinned public CCD control from the test catalog')
    args = parser.parse_args()
    if args.local_artifact_checkout is not None:
        prepare_branch_runner_destination(args.local_artifact_checkout, args.output)
    metadata = build(Path(__file__).resolve().parents[1], args.narestraints_root.resolve(), args.output,
        template_name='cif_numerical_recovery_probe_template.py', delivery_prefix=args.delivery_prefix,
        component_controls=tuple(args.component_control))
    print('Delivery:', metadata['delivery_prefix'])
    print('Output:', args.output)
    print('SHA-256:', _sha(args.output.read_bytes()))


if __name__ == '__main__':
    main()
