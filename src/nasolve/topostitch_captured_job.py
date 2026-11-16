"""Reusable captured native diagnostics; no campaign or model adoption authority.

Native chemistry, observed-context builders and process ownership remain Cedar's.
No optional native/runtime dependency is imported until a job is requested.
"""
from __future__ import annotations
from contextlib import contextmanager
from hashlib import sha256
import importlib
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from uuid import uuid4

WILLOW_MODULES = ('topostitch', 'topostitch_coordinates', 'topostitch_periodic',
                  'topostitch_transport', 'topostitch_recipe',
                  'topostitch_native_recipe', 'topostitch_capture', 'topostitch_trial', 'topostitch_endpoint', 'topostitch_native_terms')

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
        correction=correction,native_audit=audit,include_pairs=spec['include_pairs'],
        **{k:request[k] for k in ('tether_sigma_angstrom','max_displacement_angstrom','max_evaluations')})
    if 'endpoint_sha256' in spec:
        from nasolve.topostitch_endpoint import endpoint_coordinate_cases
        from nasolve.topostitch_trial import observe_masked_coordinates
        cases=endpoint_coordinate_cases(model,json.loads((root/'endpoint.json').read_bytes()),
            movable_indices=request['movable_indices'],max_displacement_angstrom=request['max_displacement_angstrom'])
        from nasolve.topostitch_native_terms import NativeTermObserver
        from native_term_kernels import native_plane_evaluator, native_evaluator, dihedral_geometry
        term_observer=NativeTermObserver(geo,ns['report'],request['movable_indices'],
            gr=objective._gr,flex=objective._flex,
            torsion_evaluate=native_evaluator(objective._gr,objective._flex),
            plane_evaluate=native_plane_evaluator(objective._gr,objective._flex),torsion_geometry=dihedral_geometry)
        observations=observe_masked_coordinates(objective,cases,
            capture_pairs=lambda points:ns['capture_asu_pairs'](geo,points),
            describe_pairs=lambda points:pairs.describe_terms(points,atom_identities=objective._identities),
            describe_native=term_observer.observe)
        result.update(status='ENDPOINT_OBSERVATIONS_REVIEW' if observations['status']=='COORDINATE_OBSERVATIONS_REVIEW' else 'ENDPOINT_OBSERVATIONS_FAILED',
            context=context,binding=objective.binding_report(),observations=observations)
    elif 'trial' in spec:
        from nasolve.topostitch_trial import run_native_masked_trial
        trial=run_native_masked_trial(objective,**spec['trial'])
        result.update(status='BOUNDED_TRIAL_REVIEW' if trial['status']=='ENDPOINT_DERIVATIVES_PASS' else 'TRIAL_REVIEW_REQUIRED',
                      context=context,binding=objective.binding_report(),trial=trial,optimization=trial['optimization_started'])
    else:
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
sys.exit(0 if result['status'] in ('INITIAL_CONTEXT_AND_EVALUATIONS_MATCH','BOUNDED_TRIAL_REVIEW','ENDPOINT_OBSERVATIONS_REVIEW') else 2)
'''


def _save(path, value, *, compact=False):
    options=dict(sort_keys=True,separators=(',',':')) if compact else dict(indent=2)
    path.write_text(json.dumps(value, allow_nan=False, **options)+'\n')


@contextmanager
def _cedar(source=None, *, guard_live_policy=False):
    """Use installed owners, or isolate one explicitly trusted developer checkout.

    A fresh temporary namespace permits repeated jobs without reusing stale
    imported developer code. It is removed even if import or execution fails.
    """
    package_root = Path(__file__).resolve().parent if source is None else Path(source).resolve(strict=True)/'nasolve'
    name = __package__ if source is None else '_topostitch_cedar_'+uuid4().hex
    if source is not None:
        package=types.ModuleType(name);package.__path__=[str(package_root)];sys.modules[name]=package
    try:
        names=('cif_attachment_native','cif_native_validation','cif_candidate_usability',
               'cif_native_nonbonded','cif_native_monomers','cif_fixed_geometry','phenix_runtime',
               'cif_captured_mixed_gradients','campaign_process','cif_selected_environment')
        if guard_live_policy:names+=('cif_live_nonbonded_policy',)
        modules={n:importlib.import_module(name+'.'+n) for n in names}
        if any(not Path(m.__file__).resolve().is_relative_to(package_root) for m in modules.values()):
            raise ValueError('Cedar owner resolved outside the selected package')
        yield modules
    finally:
        if source is not None:
            for key in list(sys.modules):
                if key==name or key.startswith(name+'.'):del sys.modules[key]


def _unchanged(*records):
    try:
        return all(p.read_bytes()==data for rows in records for p,data in rows.items())
    except OSError:
        return False


def run_captured_objective(model, recipe, mask, native_receipt, output_parent, *,
        recipe_sha256, mask_sha256, phenix, cedar_source=None, trial_iterations=0,
        trial_calls=2000, include_pairs=True, timeout_seconds=600, _process_runner=None,
        endpoint_points=None, endpoint_sha256=None, guard_live_policy=False):
    """Return ``(new_directory, report)`` for one immutable diagnostic job.

    ``phenix`` is an existing discovered installation or an explicit installation
    root. ``cedar_source=None`` uses owners in this installed NASolve package;
    an explicit source directory is only a developer compatibility route.
    The optional owned runner follows Cedar's existing process-runner protocol.
    Uncertain process cleanup escapes to that owner after retaining evidence.
    ``guard_live_policy=True`` requires the qualified Cedar owner/profile and
    freezes a new policy baseline only after fresh reconstruction matches capture.
    Historical captures do not gain missing policy provenance.
    Defaults perform no optimization. No candidate/checkpoint is published.
    """
    if type(guard_live_policy) is not bool:
        raise ValueError('Live policy guard must be an explicit boolean')
    if ((endpoint_points is None)!=(endpoint_sha256 is None)
            or endpoint_points is not None and trial_iterations!=0):
        raise ValueError('Endpoint observation needs points plus checksum and cannot optimize')
    if type(include_pairs) is not bool:
        raise ValueError('Pair inclusion must be an explicit boolean')
    if (type(trial_iterations) is not int or not 0<=trial_iterations<=500
            or type(trial_calls) is not int or not 10<=trial_calls<=5000):
        raise ValueError('Require 0-500 trial iterations and 10-5000 optimizer calls')
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 1<=timeout_seconds<=3600:
        raise ValueError('Require a timeout from 1 to 3600 seconds')
    if _process_runner is not None and not callable(_process_runner):
        raise ValueError('Require a callable owned process runner')
    args=types.SimpleNamespace(**{k:Path(v) for k,v in dict(model=model,recipe=recipe,
        mask=mask,native_receipt=native_receipt,output_parent=output_parent).items()},
        recipe_sha256=recipe_sha256,mask_sha256=mask_sha256,trial_iterations=trial_iterations,
        trial_calls=trial_calls,without_pairs=not include_pairs,timeout_seconds=timeout_seconds,
        endpoint_points=None if endpoint_points is None else Path(endpoint_points),endpoint_sha256=endpoint_sha256,
        guard_live_policy=guard_live_policy)
    owners=_cedar(cedar_source,guard_live_policy=True) if guard_live_policy else _cedar(cedar_source)
    with owners as cedar:
        return _run(args,cedar,phenix,_process_runner)


def _worker(spec, capture, cedar):
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
    return cedar['cif_captured_mixed_gradients']._native_context_worker(worker,capture)



def _guard_assets(cedar):
    """Read the qualified explicit owner/resource closure before allocating a job."""
    owner=cedar['cif_live_nonbonded_policy']
    package=Path(cedar['cif_attachment_native'].__file__).resolve().parent
    source=Path(owner.__file__).resolve(strict=True)
    profile=(source.parent/'data/nonbonded-native-profile.json').resolve(strict=True)
    if (source!=package/'cif_live_nonbonded_policy.py'
            or profile!=package/'data/nonbonded-native-profile.json'):
        raise ValueError('Live policy owner/profile differs from qualified package layout')
    if not all(callable(getattr(owner,n,None)) for n in ('snapshot_live_nonbonded_policy','require_live_nonbonded_policy')):
        raise ValueError('Incomplete live policy owner interface')
    assets={source:source.read_bytes(),profile:profile.read_bytes()}
    if json.loads(assets[profile]).get('profile_id')!=owner.PROFILE_ID:
        raise ValueError('Live policy owner/profile identity mismatch')
    return assets,dict(policy_id=owner.POLICY_ID,native_profile_id=owner.PROFILE_ID,
        owner_source_sha256=sha256(assets[source]).hexdigest(),native_profile_sha256=sha256(assets[profile]).hexdigest())


def _evaluation_worker(guard_live_policy):
    if not guard_live_policy:return WORKER
    block=r"""    from hashlib import sha256
    from cctbx.geometry_restraints.flags import flags
    from nasolve import cif_live_nonbonded_policy as live_policy
    guard=spec['live_policy_guard']
    owner_path=Path(live_policy.__file__)
    if (sha256(owner_path.read_bytes()).hexdigest()!=guard['owner_source_sha256']
            or sha256((owner_path.parent/'data/nonbonded-native-profile.json').read_bytes()).hexdigest()!=guard['native_profile_sha256']
            or sha256(model).hexdigest()!=guard['source_model_sha256']):
        raise ValueError('Staged live policy owner/profile/source mismatch')
    baseline=live_policy.snapshot_live_nonbonded_policy(geo,flags=flags(default=True),
        compute_gradients=True,normalization=False,disable_asu_cache=False,
        gradients=None,custom_nonbonded_function=None,external_energy_function=None,extension_objects=())
    baseline_record=dict(schema_version=1,kind='topostitch-live-policy-baseline',origin='FRESH_RECONSTRUCTED_CONTEXT',
        source_model_sha256=guard['source_model_sha256'],source_receipt_sha256=guard['source_receipt_sha256'],snapshot=baseline)
    (root/'live-policy.json').write_text(json.dumps(baseline_record,sort_keys=True,allow_nan=False)+'\n')
"""
    marker="    signature=audit.fixed_signature(geo,ns['sites'])"
    if WORKER.count(marker)!=1:raise ValueError('Guard worker construction boundary changed')
    guarded=WORKER.replace(marker,block+marker,1)
    marker="        correction=correction,native_audit=audit,include_pairs=spec['include_pairs'],"
    if guarded.count(marker)!=1:raise ValueError('Guard objective construction boundary changed')
    return guarded.replace(marker,marker+"\n        live_policy_owner=live_policy,expected_live_policy=baseline,",1)


def _verify_guard_result(root, evaluation, expected):
    """Cross-check worker evidence; native policy validation remains Cedar's."""
    try:
        record=json.loads((root/'live-policy.json').read_bytes())
        snapshot=record['snapshot']
        if (set(record)!={'schema_version','kind','origin','source_model_sha256','source_receipt_sha256','snapshot'}
                or type(record['schema_version']) is not int or record['schema_version']!=1
                or record['kind']!='topostitch-live-policy-baseline' or record['origin']!='FRESH_RECONSTRUCTED_CONTEXT'
                or any(record[k]!=expected[k] for k in ('source_model_sha256','source_receipt_sha256'))
                or type(snapshot['schema_version']) is not int or snapshot['schema_version']!=1
                or any(snapshot[k]!=expected[k] for k in ('policy_id','native_profile_id'))
                or sha256(json.dumps(snapshot['policy'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=snapshot['policy_sha256']):
            raise ValueError('Live policy baseline identity/digest mismatch')
        binding={k:snapshot[k] for k in ('policy_id','native_profile_id','policy_sha256')}
        binding.update({k:expected[k] for k in ('owner_source_sha256','native_profile_sha256')})
        if evaluation['binding']['live_nonbonded_policy']!=binding:
            raise ValueError('Guarded worker binding differs from expected baseline/provenance')
        return snapshot['policy_sha256']
    except (KeyError,TypeError,AttributeError) as exc:
        raise ValueError('Missing or malformed guarded-worker evidence') from exc


def _run(args, cedar, phenix, process_runner):
    from nasolve import topostitch_capture, topostitch_endpoint
    from nasolve.topostitch_recipe import recipe_digest
    paths={k:getattr(args,k).resolve(strict=True) for k in ('model','recipe','mask','native_receipt')}
    if args.endpoint_points is not None:paths['endpoint_points']=args.endpoint_points.resolve(strict=True)
    originals={p:p.read_bytes() for p in paths.values()}
    receipt,native,snapshots=cedar['cif_attachment_native']._capture(paths['native_receipt'],originals[paths['model']])
    if receipt['status']!='REVIEW' or not cedar['cif_fixed_geometry']._fixed_policy(native):
        raise ValueError('Require complete read-only capture with fixed native NA policy')
    topostitch_capture.compare_reconstructed_context(native,native)
    if args.trial_iterations:
        edit_origin=native['restraint_policy']['origin_ids']['edits']
        if any(row.get('origin_id')==edit_origin for rows in native['geometry']['proxy_details'].values() for row in rows):
            raise ValueError('First trial scope excludes preexisting native geometry edits to prevent pair double counting')
    spec=json.loads(snapshots[paths['native_receipt'].parent/'native_spec.json'])
    worker=_worker(spec,receipt,cedar)
    packet=json.loads(originals[paths['recipe']]);mask=json.loads(originals[paths['mask']])
    if recipe_digest(packet)!=args.recipe_sha256 or sha256(originals[paths['mask']]).hexdigest()!=args.mask_sha256:
        raise ValueError('Recipe or mask checksum mismatch')
    fields={'schema_version','kind','source_model_sha256','movable_indices','tether_sigma_angstrom',
            'max_displacement_angstrom','max_evaluations'}
    if (set(mask)!=fields or type(mask['schema_version']) is not int or mask['schema_version']!=1
            or mask['kind']!='topostitch-native-mask-request'
            or mask['source_model_sha256']!=sha256(originals[paths['model']]).hexdigest()):
        raise ValueError('Unsupported or stale movement request')
    if args.endpoint_points is not None:
        data=originals[paths['endpoint_points']]
        if sha256(data).hexdigest()!=args.endpoint_sha256:raise ValueError('Endpoint point checksum mismatch')
        endpoint_cases=topostitch_endpoint.endpoint_coordinate_cases(originals[paths['model']],json.loads(data),
            movable_indices=mask['movable_indices'],max_displacement_angstrom=mask['max_displacement_angstrom'])
    installation=(cedar['phenix_runtime'].installation_from_candidate(Path(phenix))
                  if isinstance(phenix,(str,os.PathLike)) else phenix)
    executable=installation.executables['phenix.python']
    # Discovery may report the release while capture records release-build.
    # Keep both labels as provenance; exact dispatcher/native source bytes bind it.
    if sha256(executable.read_bytes()).hexdigest()!=receipt['executable_sha256']:
        raise ValueError('Native dispatcher bytes differ from captured installation')
    guard_assets,guard_metadata=_guard_assets(cedar) if args.guard_live_policy else ({},None)
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
    if args.endpoint_points is not None:(root/'endpoint.json').write_bytes(originals[paths['endpoint_points']])
    runtime=root/'runtime';(runtime/'nasolve').mkdir(parents=True)
    (runtime/'nasolve/__init__.py').write_text('')
    sources={executable:executable.read_bytes()}
    willow=Path(topostitch_capture.__file__).parent
    for name in WILLOW_MODULES:
        p=willow/(name+'.py');sources[p]=p.read_bytes()
        (runtime/'nasolve'/p.name).write_bytes(sources[p])
    for source,name in [('cif_parallelity_correction.py','correction_core.py'),('cif_gradient_audit.py','audit_core.py')]:
        p=Path(cedar['cif_attachment_native'].__file__).with_name(source);sources[p]=p.read_bytes()
        (runtime/name).write_bytes(sources[p])
    if guard_metadata is not None:
        source=Path(cedar['cif_live_nonbonded_policy'].__file__).resolve()
        for path,data in guard_assets.items():
            target=runtime/'nasolve'/path.relative_to(source.parent)
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        sources.update(guard_assets)
    sources[Path(__file__).resolve()]=Path(__file__).read_bytes()
    owner_namespace=cedar['cif_attachment_native'].__package__
    if args.endpoint_points is not None:
        # Stage maintained Cedar numerical functions only; their complete source
        # modules and imports are pinned by the existing owner loop below.
        planes=importlib.import_module(owner_namespace+'.cif_plane_energy')
        torsions=importlib.import_module(owner_namespace+'.cif_dihedral_conditioning')
        kernels='import math\nNEAR_LINEAR_SINE='+repr(torsions.NEAR_LINEAR_SINE)+'\n'
        kernels+='\n'.join(inspect.getsource(f) for f in
            (planes.native_plane_evaluator,torsions.native_evaluator,torsions._norm,torsions.dihedral_geometry))
        (runtime/'native_term_kernels.py').write_text(kernels)
    for name,module in list(sys.modules.items()):
        if name.startswith(owner_namespace+'.') and getattr(module,'__file__',None):
            p=Path(module.__file__).resolve();sources[p]=p.read_bytes()
    request=dict(schema_version=1,recipe_sha256=args.recipe_sha256,mask_sha256=args.mask_sha256,include_pairs=not args.without_pairs)
    if args.endpoint_points is not None:request['endpoint_sha256']=args.endpoint_sha256
    if args.trial_iterations:request['trial']=dict(max_iterations=args.trial_iterations,max_calls=args.trial_calls)
    if guard_metadata is not None:
        guard_metadata.update(source_model_sha256=sha256(originals[paths['model']]).hexdigest(),
            source_receipt_sha256=sha256(originals[paths['native_receipt']]).hexdigest())
        request['live_policy_guard']=guard_metadata
    _save(root/'request.json',request)
    (root/'evaluate.py').write_text(_evaluation_worker(args.guard_live_policy))
    frozen={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
    report=dict(schema_version=1,kind='topostitch-captured-objective-probe',status='FAILED',
        runtime_authority=False,optimization_requested=bool(args.trial_iterations),optimization=False,refinement=False,scientific_acceptance=False,
        phenix_version=installation.version,captured_phenix_version=receipt['phenix_version'],
        executable_sha256=receipt['executable_sha256'],
        executable_historical_path=str(executable),command=['phenix.python','-B','evaluate.py'],
        source_receipt_sha256=sha256(originals[paths['native_receipt']]).hexdigest(),
        recipe_sha256=args.recipe_sha256,mask_sha256=args.mask_sha256,
        execution={'status':'NOT_RUN','timeout_seconds':args.timeout_seconds})
    if guard_metadata is not None:report['live_policy_guard']=dict(guard_metadata,baseline_verified=False)
    try:
        environment=dict(installation.environment,PYTHONDONTWRITEBYTECODE='1')
        code=cedar['cif_native_validation']._run_native_command([str(executable),'-B','evaluate.py'],
            cwd=root,log_path=root/'native.log',environment=environment,timeout_seconds=args.timeout_seconds,process_runner=process_runner)
        report['execution'].update(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
        evaluation=json.loads((root/'evaluation.json').read_bytes())
        report['optimization']=evaluation.get('optimization',False)
        if 'trial' in evaluation:
            report['trial_status']=evaluation['trial']['status']
            if 'failure_endpoint' in evaluation['trial']:
                report['failure_endpoint_status']=evaluation['trial']['failure_endpoint']['status']
            if 'stopping' in evaluation['trial']:
                report['stopping_classification']=cedar['cif_fixed_geometry'].classify_stopping(evaluation['trial']['stopping'])
        if code!=0:raise ValueError('Native probe/trial remains under review; inspect retained evaluation.json/native.log')
        if guard_metadata is not None:
            digest=_verify_guard_result(root,evaluation,guard_metadata)
            report['live_policy_guard'].update(baseline_verified=True,policy_sha256=digest)
        rebuilt=json.loads((root/'bootstrap/native_validation.json').read_bytes())
        cedar['cif_native_monomers'].review_full_monomers(rebuilt)
        cedar['cif_native_nonbonded'].review_native_nonbonded(rebuilt)
        report['context']=topostitch_capture.compare_reconstructed_context(native,rebuilt)
        if args.endpoint_points is not None:
            from nasolve.topostitch_packing import compare_native_packing
            from nasolve.topostitch_native_recipe import compare_pair_attribution
            from nasolve.topostitch_native_terms import compare_native_term_observations
            observations=evaluation['observations']
            if (observations['status']!='COORDINATE_OBSERVATIONS_REVIEW'
                    or observations['origin']!='FIXED_MANAGER_EVALUATION_NOT_REINTERPRETATION'
                    or observations['normalization'] is not False
                    or observations['optimization'] is not False
                    or [v['name'] for v in observations['cases']]!=list(endpoint_cases)):
                raise ValueError('Incomplete fixed-manager endpoint observation')
            projected={row['name']:topostitch_endpoint.project_coordinate_observation(native,row,
                expected_points=endpoint_cases[row['name']]) for row in observations['cases']}
            attributions={row['name']:row['pair_attribution'] for row in observations['cases']}
            native_terms={row['name']:row['native_terms'] for row in observations['cases']}
            pair_review=cedar['cif_native_nonbonded'].review_native_nonbonded
            review=dict(schema_version=1,kind='topostitch-native-endpoint-review',
                origin=observations['origin'],endpoint_points_sha256=args.endpoint_sha256,
                native_terms_from_source={name:compare_native_term_observations(native_terms['source'],native_terms[name])
                    for name in ('full_precision','rounded')},
                pair_attribution_from_source={name:compare_pair_attribution(attributions['source'],attributions[name])
                    for name in ('full_precision','rounded')},
                environments={name:cedar['cif_selected_environment'].review_selected_environment(value,mask['movable_indices'])
                    for name,value in projected.items()},
                packing_from_source={name:compare_native_packing(projected['source'],projected[name],reviewer=pair_review)
                    for name in ('full_precision','rounded')},
                rounding_packing=compare_native_packing(projected['full_precision'],projected['rounded'],reviewer=pair_review),
                source_reconstruction_packing=compare_native_packing(native,projected['source'],reviewer=pair_review),
                runtime_authority=False,scientific_acceptance=False,automatic_adoption=False,
                derivatives='NOT_RUN_BY_ENDPOINT_OBSERVER',chemistry_qualification='NOT_ESTABLISHED')
            _save(root/'endpoint-review.json',review,compact=True)
        report['status']=evaluation['status']
    except subprocess.TimeoutExpired as exc:
        report['execution'].update(status='TIMED_OUT',returncode=getattr(exc,'returncode',None))
        report['error']='Owned native interpreter exceeded timeout; partial evidence retained'
    except cedar['campaign_process'].CampaignProcessError as exc:
        report['execution']['status']='OWNERSHIP_ERROR'
        report['error']=str(exc)
        raise
    except (OSError,ValueError,RuntimeError) as exc:report['error']=str(exc)
    finally:
        report['inputs_and_sources_preserved']=_unchanged(originals,snapshots,sources,frozen)
        if not report['inputs_and_sources_preserved']:report.update(status='FAILED',error='Input or trusted source changed')
        if guard_metadata is not None and not report['inputs_and_sources_preserved']:
            report['live_policy_guard']['baseline_verified']=False
        report['trusted_sources']=[dict(historical_path=str(p),sha256=sha256(data).hexdigest()) for p,data in sources.items()]
        report['files']=[dict(anchor='probe_directory',path=p.relative_to(root).as_posix(),
            sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
            for p in sorted(root.rglob('*')) if p.is_file()]
        if (root/'endpoint-review.json').is_file():
            report['endpoint_review']=next(row for row in report['files'] if row['path']=='endpoint-review.json')
        if guard_metadata is not None and (root/'live-policy.json').is_file():
            report['live_policy_guard']['baseline']=next(row for row in report['files'] if row['path']=='live-policy.json')
        _save(root/'receipt.json',report)
    return root,report
