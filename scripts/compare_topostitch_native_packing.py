#!/usr/bin/env python3
"""Read-only comparison of two Cedar-authenticated native packing captures.

Use a trusted Cedar source checkout with the current nonbonded capture owner.
No captured worker is executed and no model/refinement is written.
"""
import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys


def _remember(snapshots, additions):
    for path,data in additions.items():
        if path in snapshots and snapshots[path] != data:
            raise ValueError('Captured input changed between reads: '+str(path))
        snapshots[path]=data


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cedar-source',type=Path,required=True)
    for side in ('before','after'):
        parser.add_argument('--'+side+'-receipt',type=Path,required=True)
        parser.add_argument('--'+side+'-model',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.out.exists():parser.error('Output already exists')
    try:
        source=args.cedar_source.resolve(strict=True)
        if not (source/'nasolve/cif_native_nonbonded.py').is_file():
            raise ValueError('Require a trusted Cedar src directory with native nonbonded review')
        sys.path.insert(0,str(source))
        from nasolve import cif_attachment_native, cif_native_nonbonded, cif_native_asu
        for module in (cif_attachment_native,cif_native_nonbonded,cif_native_asu):
            if not Path(module.__file__).resolve().is_relative_to(source):
                raise ValueError('Cedar imports did not resolve to the requested source')
        path=Path(__file__).resolve().parents[1]/'src/nasolve/topostitch_packing.py'
        spec=importlib.util.spec_from_file_location('willow_packing_comparison',path)
        comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)
        snapshots={};natives=[];bindings={};receipts=[]
        for side in ('before','after'):
            model=getattr(args,side+'_model').resolve(strict=True)
            receipt_path=getattr(args,side+'_receipt').resolve(strict=True)
            data=model.read_bytes();_remember(snapshots,{model:data})
            receipt,native,more=cif_attachment_native._capture(receipt_path,data)
            _remember(snapshots,more);natives.append(native);receipts.append(receipt)
            bindings[side]=dict(model_sha256=sha256(data).hexdigest(),receipt_sha256=sha256(snapshots[receipt_path]).hexdigest())
        for key in ('phenix_version','executable_sha256','api_sources','dictionary_source_policy','phil_namespace_policy'):
            if receipts[0][key] != receipts[1][key]:raise ValueError('Native receipt contexts differ: '+key)
        report=comparison.compare_native_packing(*natives,reviewer=cif_native_nonbonded.review_native_nonbonded)
        if any(p.read_bytes()!=data for p,data in snapshots.items()):raise ValueError('Captured evidence changed during comparison')
        report['authenticated_inputs']=bindings
        report['reader_script_sha256']=sha256(Path(__file__).read_bytes()).hexdigest()
        report['review_sources']=[dict(module=m.__name__,sha256=sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (cif_attachment_native,cif_native_nonbonded,cif_native_asu,comparison)]
        report['phenix_version']=receipts[0]['phenix_version']
        report['native_execution']='NOT_RUN_READ_ONLY_CAPTURE_REVIEW'
        # A detached report is never placed inside either frozen capture tree.
        if any(args.out.resolve().is_relative_to(getattr(args,s+'_receipt').resolve().parent) for s in ('before','after')):
            raise ValueError('Output must be outside frozen native captures')
        with args.out.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print(json.dumps(report['summary'],sort_keys=True))
    except (ImportError,OSError,ValueError,RuntimeError) as exc:parser.exit(1,f'{parser.prog}: {exc}\n')
    return 0


if __name__=='__main__':sys.exit(main())
