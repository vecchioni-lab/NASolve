#!/usr/bin/env python3
"""Run the installed captured native diagnostic; defaults remain read-only.

Explicit --trial-iterations enables a bounded diagnostic trial, never adoption.
Use --cedar-source only for an explicitly trusted developer compatibility checkout.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nasolve.topostitch_captured_job import run_captured_objective


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('model','recipe','mask','native-receipt','phenix-root','output-parent'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--cedar-source',type=Path,help='Explicit trusted developer checkout; otherwise use installed Cedar owners')
    parser.add_argument('--endpoint-points',type=Path,help='Read-only full-precision coordinate JSON; requires checksum')
    parser.add_argument('--endpoint-sha256')
    parser.add_argument('--recipe-sha256',required=True);parser.add_argument('--mask-sha256',required=True)
    parser.add_argument('--timeout-seconds',type=float,default=600)
    parser.add_argument('--trial-iterations',type=int,default=0,help='Explicitly enable a bounded diagnostic native trial')
    parser.add_argument('--trial-calls',type=int,default=2000)
    parser.add_argument('--without-pairs',action='store_true',help='Matched cleanup control; still report unweighted pair energy')
    args=parser.parse_args(argv)
    try:
        directory,report=run_captured_objective(args.model,args.recipe,args.mask,args.native_receipt,
            args.output_parent,recipe_sha256=args.recipe_sha256,mask_sha256=args.mask_sha256,
            phenix=args.phenix_root,cedar_source=args.cedar_source,trial_iterations=args.trial_iterations,
            trial_calls=args.trial_calls,include_pairs=not args.without_pairs,timeout_seconds=args.timeout_seconds,
            endpoint_points=args.endpoint_points,endpoint_sha256=args.endpoint_sha256)
        print(json.dumps(dict(directory=str(directory),status=report['status'])))
        return 0 if report['status'] in ('INITIAL_CONTEXT_AND_EVALUATIONS_MATCH','BOUNDED_TRIAL_REVIEW','ENDPOINT_OBSERVATIONS_REVIEW') else 2
    except (ImportError,OSError,ValueError,RuntimeError,KeyError,TypeError) as exc:
        parser.exit(1,f'{parser.prog}: {exc}\n')


if __name__=='__main__':sys.exit(main())
