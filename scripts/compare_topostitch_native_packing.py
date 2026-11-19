#!/usr/bin/env python3
"""Read-only comparison of two Cedar-authenticated native packing captures.

Use a trusted Cedar source checkout with the current nonbonded capture owner.
No captured worker is executed and no model/refinement is written.
"""
import argparse
from hashlib import sha256
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import types


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
    parser.add_argument('--mask',type=Path)
    parser.add_argument('--anisou-policy',choices=('reject-movable','preserve-cartesian'),default='reject-movable')
    parser.add_argument('--mask-sha256')
    parser.add_argument('--full-precision',type=Path,help='JSON list of all ASU Cartesian points before PDB rounding')
    parser.add_argument('--full-precision-sha256')
    args=parser.parse_args(argv)
    if args.out.exists():parser.error('Output already exists')
    endpoint_args=(args.mask,args.mask_sha256,args.full_precision,args.full_precision_sha256)
    if any(v is not None for v in endpoint_args) and not all(v is not None for v in endpoint_args):
        parser.error('Endpoint review requires mask, full-precision points and both file checksums')
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
        review_modules=[cif_attachment_native,cif_native_nonbonded,cif_native_asu,comparison]
        if args.mask is not None:
            from nasolve import cif_fixed_geometry, cif_selected_environment
            # Keep Cedar as the normal nasolve package. This explicitly named
            # local package loads Willow's endpoint audit and relative helpers.
            package=types.ModuleType('willow_endpoint_review')
            package.__path__=[str(path.parent)];sys.modules[package.__name__]=package
            endpoint=importlib.import_module(package.__name__+'.topostitch_endpoint')
            payloads=[]
            for p,expected in ((args.mask,args.mask_sha256),(args.full_precision,args.full_precision_sha256)):
                p=p.resolve(strict=True);data=p.read_bytes();_remember(snapshots,{p:data})
                if sha256(data).hexdigest()!=expected:raise ValueError('Endpoint request checksum mismatch')
                payloads.append(json.loads(data))
            mask,points=payloads
            fields={'schema_version','kind','source_model_sha256','movable_indices',
                    'tether_sigma_angstrom','max_displacement_angstrom','max_evaluations'}
            if (set(mask)!=fields or type(mask['schema_version']) is not int or mask['schema_version']!=1
                    or mask['kind']!='topostitch-native-mask-request'
                    or mask['source_model_sha256']!=bindings['before']['model_sha256']):
                raise ValueError('Unsupported or stale endpoint mask request')
            byte_audit=endpoint.audit_masked_endpoint(snapshots[args.before_model.resolve()],
                snapshots[args.after_model.resolve()],points,movable_indices=mask['movable_indices'],
                max_displacement_angstrom=mask['max_displacement_angstrom'],anisou_policy=args.anisou_policy)
            mechanics=cif_fixed_geometry.qualify_fixed_policy_geometry(*natives,args.after_model,
                {'candidate_sha256':bindings['after']['model_sha256']})
            if not mechanics['mechanics_checks_pass']:
                failed=[r['check'] for r in mechanics['checks'] if r['status']!='PASS']
                raise ValueError('Native endpoint mechanics differ: '+', '.join(failed))
            report['endpoint_review']=dict(schema_version=1,kind='topostitch-masked-native-endpoint-review',
                byte_audit=byte_audit,mechanics=mechanics,mask_file_sha256=args.mask_sha256,
                full_precision_file_sha256=args.full_precision_sha256,
                full_precision_scalar_geometry=cif_fixed_geometry.review_fixed_coordinates(natives[0],points),
                source_environment=cif_selected_environment.review_selected_environment(natives[0],mask['movable_indices']),
                serialized_environment=cif_selected_environment.review_selected_environment(natives[1],mask['movable_indices']),
                full_precision_native_energy_and_packing='NOT_EVALUATED_BY_THIS_READ_ONLY_REVIEW',
                full_precision_derivatives='NOT_EVALUATED_BY_THIS_READ_ONLY_REVIEW',
                runtime_authority=False,geometry_accepted=False,automatic_adoption=False)
            review_modules.extend([endpoint,cif_fixed_geometry,cif_selected_environment])
        if any(p.read_bytes()!=data for p,data in snapshots.items()):raise ValueError('Captured evidence changed during comparison')
        report['authenticated_inputs']=bindings
        report['reader_script_sha256']=sha256(Path(__file__).read_bytes()).hexdigest()
        report['review_sources']=[dict(module=m.__name__,sha256=sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in review_modules]
        report['phenix_version']=receipts[0]['phenix_version']
        report['native_execution']='NOT_RUN_READ_ONLY_CAPTURE_REVIEW'
        # A detached report is never placed inside either frozen capture tree.
        if any(args.out.resolve().is_relative_to(getattr(args,s+'_receipt').resolve().parent) for s in ('before','after')):
            raise ValueError('Output must be outside frozen native captures')
        with args.out.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print(json.dumps(report['summary'],sort_keys=True))
    except (ImportError,OSError,ValueError,RuntimeError,KeyError,TypeError) as exc:parser.exit(1,f'{parser.prog}: {exc}\n')
    return 0


if __name__=='__main__':sys.exit(main())
