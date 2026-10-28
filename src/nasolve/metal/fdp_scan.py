"""Explicit seed-bound occupancy grids and bounded immutable execution passes."""
import hashlib
from itertools import product
import math
from pathlib import Path
import re
import subprocess

from .context import _reference
from .fdp import _integer, run_fdp
from .fdp_compare import _load_trial
from .materialize import _json, _json_bytes, _source
from .recipe import RecipeError, canonical, digest, number

PROTOCOL = 'metal-fdp-scan-v1'
MAX_TRIALS = 128


def _directory(run, path, prefix):
    path = Path(path).expanduser()
    if not path.is_absolute(): path = run/path
    if path.is_symlink() or path.parent.is_symlink():
        raise RecipeError('Scan artifact must not be a symlink')
    path = path.resolve()
    if path.parent != run/'Metal' or not re.fullmatch(prefix+r'_\d{3,}', path.name):
        raise RecipeError('Require an explicit numbered '+prefix+' directory in this run')
    return path


def _allocate(run, prefix):
    root = run/'Metal'
    if root.is_symlink(): raise RecipeError('Metal root must not be a symlink')
    index = max([int(m.group(1)) for p in root.iterdir()
                 if (m := re.fullmatch(prefix+r'_(\d{3,})',p.name))], default=0)+1
    while True:
        path = root/f'{prefix}_{index:03d}'
        try:
            path.mkdir()
            return path
        except FileExistsError: index += 1


def _manifest_directory(run, ref):
    _source(ref,run)
    if ref['anchor'] != 'run' or Path(ref['relative_path']).name != 'manifest.json':
        raise RecipeError('Require a run-anchored manifest')
    return Path(ref['relative_path']).parent


def _make_plan(run, seed, axes, max_trials):
    _integer(max_trials,1,MAX_TRIALS,'maximum planned trials')
    loaded = _load_trial(run,seed)
    q = loaded['occupancy_vector']
    fitted = {g['id'] for g in loaded['basis']['groups'] if g['refine_fdp']}
    if not isinstance(axes,dict) or not axes or set(axes)-set(q):
        raise RecipeError('Occupancy axes must name existing placed metal nodes')
    normalized = {}
    count = 1
    for node,values in sorted(axes.items()):
        if not isinstance(values,list) or not 1 <= len(values) <= MAX_TRIALS:
            raise RecipeError('Each occupancy axis requires 1 to 128 explicit values')
        values = [number(v,'scan occupancy') for v in values]
        if (len(set(values)) != len(values) or any(not 0 <= v <= 1 or
                not math.isclose(v,round(v,2),rel_tol=0,abs_tol=1e-10) for v in values)):
            raise RecipeError('Occupancies must be distinct values in [0,1] with at most two decimals')
        values = [round(v,2) for v in values]
        if len(set(values)) != len(values):
            raise RecipeError('Occupancies duplicate after PDB rounding')
        if node in fitted and 0 in values:
            raise RecipeError('Fitted sites require positive occupancy; zero-q fdp is not identifiable')
        normalized[node] = sorted(round(v,2) for v in values)
        count *= len(values)
    if count > max_trials:
        raise RecipeError(f'Grid has {count} points, exceeding explicit limit {max_trials}')
    doc = dict(kind='metal-fdp-scan-plan',schema_version=1,protocol=PROTOCOL,
               seed=loaded['ref'],seed_trial_id=loaded['trial_id'],axes=normalized,max_trials=max_trials,
               locked_occupancies={n:v for n,v in q.items() if n not in normalized},
               fixed_settings=loaded['settings'],fit_nodes=sorted(fitted),
               points=[dict(point_id=digest(vector),occupancies=vector)
                       for values in product(*normalized.values())
                       for vector in [dict(sorted(dict(q,**dict(zip(normalized,values))).items()))]],
               automatic_checkpoint_selection=False,scientific_acceptance='NOT_ASSESSED')
    doc['plan_id'] = digest(doc)
    return doc


def create_plan(run, seed, occupancies, *, max_trials):
    """Plan a complete Cartesian occupancy grid offline from an audited seed."""
    run = Path(run).expanduser().resolve()
    plan = _make_plan(run,seed,occupancies,max_trials)
    directory = _allocate(run,'fdp_scan_plan')
    plan = _locate_plan(plan,run,directory)
    try:
        (directory/'plan.json').write_bytes(_json_bytes(plan))
        verify_plan(run,directory)
        return plan
    except BaseException as exc:
        with (directory/'failure.json').open('xb') as handle:
            handle.write(_json_bytes(dict(status='FAILED',exception=type(exc).__name__,error=str(exc))))
        raise


def _locate_plan(plan, run, directory):
    plan = dict(plan)
    plan.pop('plan_id')
    plan['directory'] = dict(anchor='run',relative_path=str(directory.relative_to(run)))
    plan['plan_id'] = digest(plan)
    return plan


def verify_plan(run, directory):
    run = Path(run).expanduser().resolve()
    directory = _directory(run,directory,'fdp_scan_plan')
    try:
        if {p.name for p in directory.iterdir()} != {'plan.json'} or (directory/'plan.json').is_symlink():
            raise RecipeError('Unexpected scan plan inventory')
        doc = _json((directory/'plan.json').read_bytes())
        seed = _manifest_directory(run,doc['seed'])
        expected = _locate_plan(_make_plan(run,seed,doc['axes'],doc['max_trials']),run,directory)
        if canonical(doc) != canonical(expected): raise RecipeError('Scan plan differs from source replay')
        return doc
    except (OSError,ValueError,KeyError,TypeError) as exc:
        if isinstance(exc,RecipeError): raise
        raise RecipeError('Cannot verify scan plan: '+str(exc)) from exc


def _inputs(run, plan_directory, resume=None, seen=None):
    directory = _directory(run,plan_directory,'fdp_scan_plan')
    plan = verify_plan(run,directory)
    plan_ref = _reference(directory/'plan.json',run)
    seed = _load_trial(run,_manifest_directory(run,plan['seed']))
    available = {p['point_id']:(seed['ref'],'REUSED_SEED') for p in plan['points']
                 if canonical(p['occupancies']) == canonical(seed['occupancy_vector'])}
    resume_ref = None
    if resume is not None:
        prior = verify_scan(run,resume,_seen=seen)
        if prior['plan'] != plan_ref: raise RecipeError('Resume requires the identical scan plan')
        prior_directory = _directory(run,resume,'fdp_scan')
        resume_ref = _reference(prior_directory/'manifest.json',run)
        report = _json(_source(prior['files']['report'],run))
        for point in report['points']:
            if point['trial'] is not None:
                available[point['point_id']] = (point['trial'],'REUSED_SCAN')
    return plan,plan_ref,seed,available,resume_ref


def pending_count(run, plan, resume=None):
    """Count missing points without native discovery or execution."""
    run = Path(run).expanduser().resolve()
    doc,_,_,available,_ = _inputs(run,plan,resume)
    return len(doc['points'])-len(available)


def _check_native(native, seed):
    """Do not mix a saved seed with changed worker/native source or kernels."""
    worker = Path(__file__).with_name('_fdp_native.py')
    if hashlib.sha256(worker.read_bytes()).hexdigest() != seed['basis']['worker_sha256']:
        raise RecipeError('Current native worker differs from the seed; use a new seed')
    code = ("import json,runpy,sys; from phenix import phenix_info; "
            "m=runpy.run_path(sys.argv[1]); "
            "print(json.dumps(dict(version='-'.join(str(v) for v in phenix_info.version_and_release_tag() if v),"
            "hashes=m['native_source_hashes']())))")
    try:
        done = subprocess.run([str(native.executables['phenix.python']),'-B','-c',code,str(worker)],
                              env=native.environment,capture_output=True,text=True,timeout=30,check=False)
        if done.returncode: raise RecipeError('Cannot inspect native identity: '+done.stderr[-1500:])
        identity = _json(done.stdout)
        if (identity['version'] != seed['basis']['native_version'] or
                identity['hashes'] != seed['basis']['native_source_hashes']):
            raise RecipeError('Native version/source/kernels differ from the seed; use a new seed')
    except (OSError,ValueError,TypeError,KeyError,subprocess.TimeoutExpired) as exc:
        if isinstance(exc,RecipeError): raise
        raise RecipeError('Cannot check native identity: '+str(exc)) from exc


def _matched(run, ref, seed, point):
    loaded = _load_trial(run,_manifest_directory(run,ref))
    if (loaded['ref'] != ref or canonical(loaded['basis']) != canonical(seed['basis']) or
            canonical(loaded['settings']) != canonical(seed['settings']) or
            canonical(loaded['occupancy_vector']) != canonical(point['occupancies'])):
        raise RecipeError('Scan trial differs from planned occupancy or fixed experiment')
    return loaded


def _report(run, plan, seed, available, receipts, job_budget, failure):
    _integer(job_budget,0,MAX_TRIALS,'native job budget')
    available = dict(available)
    pending = [p for p in plan['points'] if p['point_id'] not in available]
    if len(receipts) > job_budget or len(receipts) > len(pending):
        raise RecipeError('Scan exceeds its job budget or point count')
    for receipt,point in zip(receipts,pending):
        if set(receipt) != {'point_id','trial'} or receipt['point_id'] != point['point_id']:
            raise RecipeError('Scan receipts must follow pending point order')
        available[point['point_id']] = (receipt['trial'],'EXECUTED')
    attempts = len(receipts)+(failure is not None)
    if attempts > job_budget: raise RecipeError('Scan failure exceeds job budget')
    remaining = pending[len(receipts):]
    if failure is not None:
        if (not isinstance(failure,dict) or set(failure) != {'point_id','exception','error'} or not remaining
                or failure['point_id'] != remaining[0]['point_id'] or
                any(not isinstance(failure[k],str) or not failure[k] for k in ('exception','error'))):
            raise RecipeError('Invalid recorded scan failure')
    elif remaining and len(receipts) != job_budget:
        raise RecipeError('Partial scan must exhaust its budget or record a failure')
    rows = []
    for point in plan['points']:
        ref,state = available.get(point['point_id'],(None,'PENDING'))
        loaded = _matched(run,ref,seed,point) if ref else None
        rows.append(dict(point,state=state,trial=ref,trial_id=loaded['trial_id'] if loaded else None,
                         sites=loaded['result']['sites'] if loaded else [],
                         wavelength_A=loaded['result']['wavelength_A'] if loaded else None))
    return dict(kind='metal-fdp-scan-report',schema_version=1,protocol=PROTOCOL,plan_id=plan['plan_id'],
                status='PARTIAL_REVIEW' if remaining else 'SCAN_REVIEW',points=rows,
                trial_attempts=attempts,new_completed=len(receipts),reused=len(available)-len(receipts),
                pending=len(remaining),job_budget=job_budget,failure=failure,
                stopping='EXECUTION_ERROR' if failure else 'JOB_BUDGET' if remaining else 'COMPLETE',
                fixed_settings=plan['fixed_settings'],fit_nodes=plan['fit_nodes'],
                automatic_checkpoint_selection=False,scientific_acceptance='NOT_ASSESSED',
                convergence='NOT_ESTABLISHED_BY_SCAN',
                note='Independent fixed-q trials; a completed grid does not establish geometry, identity, count or convergence')


def _manifest(run, directory, plan_ref, resume_ref, receipts, job_budget, failure, report):
    files = {'report':_reference(directory/'report.json',run)}
    files.update({f'point_{i:03d}':_reference(directory/f'point_{i:03d}.json',run)
                  for i in range(1,len(receipts)+1)})
    doc = dict(kind='metal-fdp-scan',schema_version=1,protocol=PROTOCOL,status=report['status'],
               plan=plan_ref,resume=resume_ref,job_budget=job_budget,failure=failure,files=files,
               automatic_checkpoint_selection=False,scientific_acceptance='NOT_ASSESSED')
    doc['scan_id'] = digest(doc)
    return doc


def run_scan(run, plan_directory, *, native=None, job_budget, resume=None):
    """Run at most job_budget independent fits; resume creates a new scan pass."""
    run = Path(run).expanduser().resolve()
    _integer(job_budget,0,MAX_TRIALS,'native job budget')
    plan,pref,seed,available,rref = _inputs(run,plan_directory,resume)
    pending = [p for p in plan['points'] if p['point_id'] not in available]
    if pending and job_budget:
        if native is None: raise RecipeError('Native installation required for pending scan jobs')
        _check_native(native,seed)
    seed_doc = _json(_source(seed['ref'],run))
    seed_plan = _json(_source(seed_doc['files']['plan.json'],run))
    options = dict(seed_plan['options']);options.pop('occupancies')
    geometry = _manifest_directory(run,seed_doc['parent']['manifest'])
    directory = _allocate(run,'fdp_scan')
    receipts = []; failure = None
    try:
        for point in pending[:job_budget]:
            try:
                trial = run_fdp(run,geometry,native=native,occupancies=point['occupancies'],
                                timeout=seed_doc['execution']['timeout_seconds'],**options)
                ref = _reference(run/Path(trial['files']['result.json']['relative_path']).parent/'manifest.json',run)
                _matched(run,ref,seed,point)
            except (RecipeError,OSError,KeyboardInterrupt) as exc:
                failure = dict(point_id=point['point_id'],exception=type(exc).__name__,error=str(exc) or 'Interrupted')
                break
            receipt = dict(point_id=point['point_id'],trial=ref)
            with (directory/f'point_{len(receipts)+1:03d}.json').open('xb') as handle:
                handle.write(_json_bytes(receipt))
            receipts.append(receipt)
        # Every inherited and newly completed result must still verify before publication.
        repeated = _inputs(run,plan_directory,resume)
        if canonical(repeated) != canonical((plan,pref,seed,available,rref)):
            raise RecipeError('Scan inputs changed during execution')
        report = _report(run,plan,seed,available,receipts,job_budget,failure)
        (directory/'report.json').write_bytes(_json_bytes(report))
        doc = _manifest(run,directory,pref,rref,receipts,job_budget,failure,report)
        (directory/'manifest.json').write_bytes(_json_bytes(doc))
        return doc
    except BaseException as exc:
        with (directory/'failure.json').open('xb') as handle:
            handle.write(_json_bytes(dict(status='FAILED',exception=type(exc).__name__,error=str(exc))))
        raise


def verify_scan(run, directory, *, _seen=None):
    """Replay a finalized scan pass and its explicit lineage without native code."""
    run = Path(run).expanduser().resolve()
    directory = _directory(run,directory,'fdp_scan')
    seen = set(_seen or ())
    if directory in seen or len(seen)>=128: raise RecipeError('Cyclic or excessive scan lineage')
    seen.add(directory)
    try:
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
            raise RecipeError('Scan payload must contain regular files')
        doc = _json((directory/'manifest.json').read_bytes())
        plan_ref = doc['plan'];_source(plan_ref,run)
        if plan_ref['anchor'] != 'run' or Path(plan_ref['relative_path']).name != 'plan.json':
            raise RecipeError('Scan requires an anchored plan')
        resume = _manifest_directory(run,doc['resume']) if doc['resume'] else None
        plan,pref,seed,available,rref = _inputs(run,Path(plan_ref['relative_path']).parent,resume,seen)
        point_names = sorted(name for name in doc['files'] if name != 'report')
        if point_names != [f'point_{i:03d}' for i in range(1,len(point_names)+1)]:
            raise RecipeError('Nonsequential scan receipts')
        if {p.name for p in directory.iterdir()} != {'manifest.json','report.json',*(n+'.json' for n in point_names)}:
            raise RecipeError('Unfinalized or unexpected scan inventory')
        receipts = [_json(_source(doc['files'][name],run)) for name in point_names]
        report = _report(run,plan,seed,available,receipts,doc['job_budget'],doc['failure'])
        if _source(doc['files']['report'],run) != _json_bytes(report):
            raise RecipeError('Scan report differs from verified trial replay')
        expected = _manifest(run,directory,pref,rref,receipts,doc['job_budget'],doc['failure'],report)
        if canonical(doc) != canonical(expected): raise RecipeError('Scan manifest or acceptance policy changed')
        return doc
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        if isinstance(exc,RecipeError): raise
        raise RecipeError('Cannot verify scan: '+str(exc)) from exc
