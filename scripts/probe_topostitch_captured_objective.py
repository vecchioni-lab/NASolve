#!/usr/bin/env python3
"""Reconstruct a Cedar-authenticated initial context and evaluate a bounded mask.

Run in ordinary Python with a trusted Cedar src checkout and explicit Phenix
installation. This developer probe creates one new local evidence directory.
It does not optimize, write a candidate, run refinement or adopt a checkpoint.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types

WILLOW_MODULES = ('topostitch', 'topostitch_coordinates', 'topostitch_periodic',
                  'topostitch_transport', 'topostitch_recipe',
                  'topostitch_native_recipe', 'topostitch_capture')

# Only maintained source builds this worker. Captured worker text is evidence,
# never an executable input. The bootstrap keeps its native manager in memory.
WORKER = r'''
import json, math, os, sys, traceback
from pathlib import Path
root=Path.cwd()
sys.path.insert(0,str(root/'runtime'))
from nasolve.topostitch_capture import compare_reconstructed_context
from nasolve.topostitch_native_recipe import NativePairRecipe, NativeMaskedObjective
import correction_core as correction
import audit_core as audit
result={'schema_version':1,'kind':'topostitch-captured-objective-evaluation',
        'status':'FAILED','optimization':False,'refinement':False,'scientific_acceptance':False}
try:
    expected=json.loads((root/'start/native_validation.json').read_bytes())
    spec=json.loads((root/'request.json').read_bytes())
    ns={'__name__':'__main__','__file__':'native_worker.py'}
    os.chdir(root/'bootstrap')
    try:
        sys.argv=['native_worker.py','native_spec.json']
        try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),ns)
        except SystemExit as exc:
            if exc.code!=0:raise RuntimeError('Fresh native interpretation failed')
    finally:os.chdir(root)
    context=compare_reconstructed_context(expected,ns['report'])
    model=(root/'model.pdb').read_bytes()
    packet=json.loads((root/'recipe.json').read_bytes())
    request=json.loads((root/'mask.json').read_bytes())
    pairs=NativePairRecipe(packet,model,expected_recipe_sha256=spec['recipe_sha256'],correction=correction)
    geo=ns['geo'];acp=ns['acp']
    signature=audit.fixed_signature(geo,ns['sites'])
    objective=NativeMaskedObjective(geo,acp.pdb_hierarchy,model,pairs,
        movable_indices=request['movable_indices'],expected_native_signature=signature,
        correction=correction,native_audit=audit,
        **{k:request[k] for k in ('tether_sigma_angstrom','max_displacement_angstrom','max_evaluations')})
    count=3*len(request['movable_indices'])
    cases=[]
    for name,delta in [('zero',[0.]*count),('nonuniform',[.002*math.sin(i+1) for i in range(count)])]:
        value=objective.evaluate(delta);repeat=objective.evaluate(delta)
        if any(value[k]!=repeat[k] for k in value if k!='evaluation_calls'):
            raise ValueError('Reconstructed masked evaluation is not repeatable')
        cases.append(dict(name=name,displacements=delta,evaluation=value))
    result.update(status='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH',context=context,
                  binding=objective.binding_report(),cases=cases)
except Exception as exc:
    result['error']=type(exc).__name__+': '+str(exc);traceback.print_exc()
(root/'evaluation.json').write_text(json.dumps(result,sort_keys=True,allow_nan=False)+'\n')
sys.exit(0 if result['status']=='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH' else 2)
'''


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def _cedar(source):
    """Load explicit trusted sources without replacing Willow's nasolve package."""
    source=Path(source).resolve(strict=True)/'nasolve'
    name='_topostitch_trusted_cedar'
    if name in sys.modules:
        raise ValueError('Trusted Cedar namespace already loaded; use a fresh host process')
    package=types.ModuleType(name);package.__path__=[str(source)];sys.modules[name]=package
    names=('cif_attachment_native','cif_native_validation','cif_candidate_usability',
           'cif_native_nonbonded','cif_native_monomers','cif_fixed_geometry','phenix_runtime')
    modules={n:importlib.import_module(name+'.'+n) for n in names}
    if any(not Path(m.__file__).resolve().is_relative_to(source) for m in modules.values()):
        raise ValueError('Cedar owner resolved outside explicitly trusted source')
    return modules


def _worker(spec, cedar):
    fields={'policy_id','model','dictionaries','phil_files','phil_namespace_policy',
            'inventory_detail','policy_inventory','installed_library_only',
            'energy_inventory','nonbonded_inventory','nonbonded_policy','full_monomer_inventory'}
    if (set(spec)-fields or spec.get('inventory_detail')!='linked'
            or any(spec.get(k) is not True for k in ('policy_inventory','energy_inventory',
                'nonbonded_inventory','full_monomer_inventory'))
            or spec.get('nonbonded_policy')!='cif-native-nonbonded-asu-attribution-v1'):
        raise ValueError('Require linked, full-monomer, energy, policy and explicit ASU capture; mapping/gradient extensions are outside this probe')
    worker=cedar['cif_native_validation']._NATIVE_WORKER
    worker=cedar['cif_candidate_usability'].native_energy_worker(worker)
    worker=cedar['cif_native_nonbonded'].native_nonbonded_worker(worker,policy=spec['nonbonded_policy'])
    return cedar['cif_native_monomers'].native_monomer_worker(worker)


def run(args):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from nasolve import topostitch_capture
    from nasolve.topostitch_recipe import recipe_digest
    cedar=_cedar(args.cedar_source)
    paths={k:getattr(args,k).resolve(strict=True) for k in ('model','recipe','mask','native_receipt')}
    originals={p:p.read_bytes() for p in paths.values()}
    receipt,native,snapshots=cedar['cif_attachment_native']._capture(paths['native_receipt'],originals[paths['model']])
    if receipt['status']!='REVIEW' or not cedar['cif_fixed_geometry']._fixed_policy(native):
        raise ValueError('Require complete read-only capture with fixed native NA policy')
    topostitch_capture.compare_reconstructed_context(native,native)
    spec=json.loads(snapshots[paths['native_receipt'].parent/'native_spec.json'])
    worker=_worker(spec,cedar)
    packet=json.loads(originals[paths['recipe']]);mask=json.loads(originals[paths['mask']])
    if recipe_digest(packet)!=args.recipe_sha256 or sha256(originals[paths['mask']]).hexdigest()!=args.mask_sha256:
        raise ValueError('Recipe or mask checksum mismatch')
    fields={'schema_version','kind','source_model_sha256','movable_indices','tether_sigma_angstrom',
            'max_displacement_angstrom','max_evaluations'}
    if (set(mask)!=fields or type(mask['schema_version']) is not int or mask['schema_version']!=1
            or mask['kind']!='topostitch-native-mask-request'
            or mask['source_model_sha256']!=sha256(originals[paths['model']]).hexdigest()):
        raise ValueError('Unsupported or stale movement request')
    installation=cedar['phenix_runtime'].installation_from_candidate(args.phenix_root)
    executable=installation.executables['phenix.python']
    if sha256(executable.read_bytes()).hexdigest()!=receipt['executable_sha256']:
        raise ValueError('Native dispatcher bytes differ from captured installation')
    if not math.isfinite(args.timeout_seconds) or not 1<=args.timeout_seconds<=3600:
        raise ValueError('Require a timeout from 1 to 3600 seconds')
    parent=args.output_parent.absolute()
    if any(p.is_symlink() for p in [parent,*parent.parents]):raise ValueError('Output cannot traverse symlinks')
    if parent.is_relative_to(paths['native_receipt'].parent):raise ValueError('Output must be outside the frozen capture')
    parent.mkdir(parents=True,exist_ok=True)
    root=Path(tempfile.mkdtemp(prefix='captured-objective-',dir=parent))
    # Complete authenticated capture is retained for offline review/relocation.
    for p,data in snapshots.items():
        dest=root/'start'/p.relative_to(paths['native_receipt'].parent)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    for name in [spec['model'],*spec['dictionaries'],*spec['phil_files']]:
        dest=root/'bootstrap'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((root/'start'/name).read_bytes())
    _save(root/'bootstrap/native_spec.json',spec)
    (root/'bootstrap/native_worker.py').write_text(worker)
    for key,name in [('model','model.pdb'),('recipe','recipe.json'),('mask','mask.json')]:
        (root/name).write_bytes(originals[paths[key]])
    runtime=root/'runtime';(runtime/'nasolve').mkdir(parents=True)
    (runtime/'nasolve/__init__.py').write_text('')
    sources={}
    willow=Path(topostitch_capture.__file__).parent
    for name in WILLOW_MODULES:
        p=willow/(name+'.py');sources[p]=p.read_bytes()
        (runtime/'nasolve'/p.name).write_bytes(sources[p])
    for source,name in [('cif_parallelity_correction.py','correction_core.py'),('cif_gradient_audit.py','audit_core.py')]:
        p=args.cedar_source.resolve()/'nasolve'/source;sources[p]=p.read_bytes()
        (runtime/name).write_bytes(sources[p])
    sources[Path(__file__).resolve()]=Path(__file__).read_bytes()
    for name,module in list(sys.modules.items()):
        if name.startswith('_topostitch_trusted_cedar.') and getattr(module,'__file__',None):
            p=Path(module.__file__).resolve();sources[p]=p.read_bytes()
    _save(root/'request.json',dict(schema_version=1,recipe_sha256=args.recipe_sha256,mask_sha256=args.mask_sha256))
    (root/'evaluate.py').write_text(WORKER)
    frozen={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
    report=dict(schema_version=1,kind='topostitch-captured-objective-probe',status='FAILED',
        runtime_authority=False,optimization=False,refinement=False,scientific_acceptance=False,
        phenix_version=installation.version,captured_phenix_version=receipt['phenix_version'],
        executable_sha256=receipt['executable_sha256'],
        executable_historical_path=str(executable),command=['phenix.python','-B','evaluate.py'],
        source_receipt_sha256=sha256(originals[paths['native_receipt']]).hexdigest(),
        recipe_sha256=args.recipe_sha256,mask_sha256=args.mask_sha256,
        execution={'status':'NOT_RUN','timeout_seconds':args.timeout_seconds})
    try:
        environment=dict(installation.environment,PYTHONDONTWRITEBYTECODE='1')
        code=cedar['cif_native_validation']._run_native_command([str(executable),'-B','evaluate.py'],
            cwd=root,log_path=root/'native.log',environment=environment,timeout_seconds=args.timeout_seconds)
        report['execution'].update(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
        if code!=0:raise ValueError('Native probe failed; inspect retained evaluation.json/native.log')
        rebuilt=json.loads((root/'bootstrap/native_validation.json').read_bytes())
        cedar['cif_native_monomers'].review_full_monomers(rebuilt)
        cedar['cif_native_nonbonded'].review_native_nonbonded(rebuilt)
        report['context']=topostitch_capture.compare_reconstructed_context(native,rebuilt)
        report['status']='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH'
    except subprocess.TimeoutExpired as exc:
        report['execution'].update(status='TIMED_OUT',returncode=exc.returncode)
        report['error']='Owned native interpreter exceeded timeout; partial evidence retained'
    except (OSError,ValueError,RuntimeError) as exc:report['error']=str(exc)
    finally:
        report['inputs_and_sources_preserved']=all(p.read_bytes()==data for records in
            (originals,snapshots,sources,frozen) for p,data in records.items())
        if not report['inputs_and_sources_preserved']:report.update(status='FAILED',error='Input or trusted source changed')
        report['trusted_sources']=[dict(historical_path=str(p),sha256=sha256(data).hexdigest()) for p,data in sources.items()]
        report['files']=[dict(anchor='probe_directory',path=p.relative_to(root).as_posix(),
            sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
            for p in sorted(root.rglob('*')) if p.is_file()]
        _save(root/'receipt.json',report)
    print(json.dumps(dict(directory=str(root),status=report['status'])))
    return 0 if report['status']=='INITIAL_CONTEXT_AND_EVALUATIONS_MATCH' else 2


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('model','recipe','mask','native-receipt','cedar-source','phenix-root','output-parent'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--recipe-sha256',required=True);parser.add_argument('--mask-sha256',required=True)
    parser.add_argument('--timeout-seconds',type=float,default=600)
    args=parser.parse_args(argv)
    try:return run(args)
    except (ImportError,OSError,ValueError,RuntimeError,KeyError,TypeError) as exc:
        parser.exit(1,f'{parser.prog}: {exc}\n')


if __name__=='__main__':sys.exit(main())
