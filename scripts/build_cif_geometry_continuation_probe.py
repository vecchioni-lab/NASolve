#!/usr/bin/env python3
"""Build the qualified full-precision fixed-NA geometry continuation."""
import argparse
from pathlib import Path
from build_synthetic_dna_shuttle import build,_sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--narestraints-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--delivery-prefix',default='28_Cedar')
    args=parser.parse_args()
    metadata=build(Path(__file__).resolve().parents[1],args.narestraints_root.resolve(),args.output,
        template_name='cif_geometry_continuation_probe_template.py',delivery_prefix=args.delivery_prefix)
    print('Delivery:',metadata['delivery_prefix']);print('Output:',args.output);print('SHA-256:',_sha(args.output.read_bytes()))


if __name__=='__main__':main()
