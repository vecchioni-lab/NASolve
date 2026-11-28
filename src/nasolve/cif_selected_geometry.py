"""Explicit selected-coordinate native trials with a frozen full environment."""
from copy import deepcopy
import ast
from hashlib import sha256
from inspect import getsource
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .cif_attachment_native import _capture, _json
from .cif_attachment_links import _input
from .cif_catalogue import _digest
from .cif_fana_junction import _path
from .cif_fragment_restoration import _key, _model
from .cif_fixed_geometry import classify_stopping
from .cif_mixed_gradient import _manager_digest, _numeric_equal
from .cif_native_gradients import review_native_gradients, NUMERIC_MODULES
from .cif_native_validation import _stop, _NATIVE_WORKER
from .cif_candidate_usability import native_energy_worker
from .cif_native_gradients import native_gradient_worker
from . import cif_nonbonded_cache_audit as cache
from .cif_native_nonbonded import _capture_pairs, review_native_nonbonded, POLICY_ID as PAIR_POLICY

POLICY_ID = 'cif-selected-native-geometry-v1'


class SelectedCoordinates:
    """Pack only selected atoms; reconstruct all other coordinates from frozen input."""
    def __init__(self, points, indices):
        self.points = deepcopy(points)
        if (not isinstance(indices, (list, tuple)) or not 0 < len(indices) < len(points)
                or any(type(i) is not int or not 0 <= i < len(points) for i in indices)
                or len(set(indices)) != len(indices)):
            raise ValueError('Require a nonempty distinct proper subset of atom indices')
        self.indices = list(indices)
        if any(len(p) != 3 for p in points): raise ValueError('Require Cartesian points')
        self._finite([x for p in points for x in p], 3*len(points))

    @staticmethod
    def _finite(values, count):
        if len(values) != count or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError('Require a complete finite numerical vector')
        return [float(v) for v in values]

    def pack(self, points):
        if len(points) != len(self.points) or any(len(p) != 3 for p in points):
            raise ValueError('Coordinate inventory differs')
        self._finite([x for p in points for x in p], 3*len(points))
        if any(p != points[i] for i, p in enumerate(self.points) if i not in self.indices):
            raise ValueError('Fixed environment coordinates changed')
        return [float(v) for i in self.indices for v in points[i]]

    def unpack(self, values):
        x = self._finite(values, 3*len(self.indices)); points = deepcopy(self.points)
        for j, i in enumerate(self.indices): points[i] = x[3*j:3*j+3]
        return points

    def project(self, gradient):
        g = self._finite(gradient, 3*len(self.points))
        return [g[3*i+j] for i in self.indices for j in range(3)]


def _limits(iterations, calls):
    if type(iterations) is not int or not 1 <= iterations <= 500 or type(calls) is not int or not 10 <= calls <= 5000:
        raise ValueError('Require 1-500 iterations and 10-5000 native trial evaluations')


def _start(receipt_path):
    path = _path(receipt_path); r = _json(path.read_bytes()); snapshots = {}
    models = [q for q in r['inputs'] if q['role'] == 'model']
    if len(models) != 1: raise ValueError('Require one captured starting model')
    ref = {k:models[0][k] for k in ('path', 'sha256', 'size')}
    model = _input(path.parent, dict(ref, anchor='manifest_directory'), snapshots)
    receipt, native, frozen = _capture(path, snapshots[model])
    _model(native, model, coordinates_match=True)
    if not review_native_gradients(native)['sampled_derivatives_pass']:
        raise ValueError('Starting native sampled derivatives remain under review')
    return receipt, native, model, frozen


def selected_model_bytes(model, native, points, indices):
    """Change only selected PDB coordinate fields, preserving fixed records byte-for-byte."""
    _model(native, model, coordinates_match=True)
    space = SelectedCoordinates(native['geometry']['sites_cart_exact'], indices); space.pack(points)
    selected = {_key(native['atoms'][i]):points[i] for i in indices}
    output = []; seen = set()
    for line in Path(model).read_bytes().splitlines(keepends=True):
        if line.startswith((b'ATOM  ', b'HETATM')):
            key = (line[21:22].decode().strip() or '_', line[22:26].decode().strip(),
                   line[26:27].decode().strip(), line[16:17].decode().strip(), line[12:16].decode().strip())
            if key in selected:
                fields = ''.join(f'{x:8.3f}' for x in selected[key]).encode()
                if len(fields) != 24 or key in seen: raise ValueError('Ambiguous or overflowing PDB coordinates')
                line = line[:30]+fields+line[54:]; seen.add(key)
        output.append(line)
    if seen != set(selected): raise ValueError('Incomplete selected PDB identity mapping')
    return b''.join(output)


_WORKER_BODY = r'''
spec=json.loads(Path('selected_spec.json').read_text())
result={'schema_version':1,'policy_id':spec['policy_id'],'status':'FAILED','automatic_adoption':False,
        'scientific_approval':'NOT_RUN','refinement':'NOT_RUN','trace':[]}
log=io.StringIO()
try:
    expected=json.loads(Path('start/native_receipt.json').read_text())['native_validation']
    ns={'__name__':'__main__','__file__':'native_worker.py'}
    os.chdir('bootstrap')
    try:
        sys.argv=['native_worker.py','native_spec.json']
        try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),ns)
        except SystemExit as exc:
            if exc.code!=0:raise RuntimeError('Native bootstrap failed')
    finally:os.chdir('..')
    native=ns['report'];import gradient_helpers;helpers=vars(gradient_helpers);geo=ns['geo']
    if helpers['_manager_digest'](native)!=spec['manager_sha256']:raise RuntimeError('Starting native manager differs')
    if native['energy_inventory']!=expected['energy_inventory'] or helpers['_numeric_sources']()!=expected['gradient_inventory']['installed_numeric_sources']:
        raise RuntimeError('Starting native energy, derivatives or numerical sources differ')
    import scitbx.lbfgs
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    def optimizer_sources():
        rows=helpers['_numeric_sources']()
        for name in ['scitbx.lbfgs','scitbx_lbfgs_ext']:
            module=importlib.import_module(name);p=Path(module.__file__).resolve()
            rows.append({'module':name,'historical_path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        return rows
    sources=optimizer_sources();space=SelectedCoordinates(native['geometry']['sites_cart_exact'],spec['moving_indices'])
    signature=helpers['fixed_signature'];before=signature(geo,ns['sites'])
    if before!=expected['gradient_inventory']['constraint_signature_before']:raise RuntimeError('Static constraints differ')
    def record(points):
        x=space.pack(points)
        if len(result['trace'])>=spec['max_calls']:raise RuntimeError('Selected native evaluation budget exhausted')
        e=geo.energies_sites(sites_cart=flex.vec3_double(points),flags=flags.flags(default=True),compute_gradients=True,normalization=False)
        nb=e.nonbonded_proxies
        if nb is None or len(nb.asu) or any(p.rt_mx_ji is not None and not p.rt_mx_ji.is_unit_mx() for p in nb.simple):
            raise RuntimeError('Unsupported nonidentity nonbonded environment')
        g=space._finite(list(e.gradients.as_double()),3*len(points));target=float(e.target)
        if not math.isfinite(target):raise RuntimeError('Nonfinite native target')
        row={'target':target,'gradient':g,'gradient_norm':math.sqrt(sum(v*v for v in g)),
             'terms':{k:float(v) for k,v in vars(e).items() if k.endswith('_residual_sum') and isinstance(v,(int,float))},
             'proxy_counts':{k:v for k,v in vars(e).items() if k.startswith('n_') and k.endswith('_proxies')}}
        result['trace'].append({'selected_coordinates':x,'snapshot':row});return row
    initial=record(space.points)
    class Evaluator:
        def __init__(self):self.x=flex.double(space.pack(space.points));self.history=[]
        def compute_functional_and_gradients(self):
            self.current=record(space.unpack(self.x));return self.current['target'],flex.double(space.project(self.current['gradient']))
        def callback_after_step(self,m):
            self.history.append({'iteration':int(m.iter()),'native_calls':int(m.nfun()),'trace_index':len(result['trace'])-1})
            return False
    evaluator=Evaluator()
    optimizer=scitbx.lbfgs.run(target_evaluator=evaluator,termination_params=scitbx.lbfgs.termination_parameters(
        max_iterations=spec['max_iterations'],max_calls=spec['max_calls']-4,
        traditional_convergence_test=True,traditional_convergence_test_eps=1e-5),log=log)
    final=space.unpack(evaluator.x);end=record(final);repeat=record(final)
    rounded=space.unpack([float('%.3f'%x) for x in space.pack(final)]);serialized=record(rounded)
    from nonbonded_helpers import _capture_pairs, PAIR_POLICY
    pair_inventory=_capture_pairs(geo,rounded)
    pair_inventory.update(schema_version=1,policy_id=PAIR_POLICY)
    projected=deepcopy(expected)
    for a,p in zip(projected['atoms'],final):a['xyz']=p[:]
    projected['geometry']['sites_cart_exact']=deepcopy(final)
    projected['energy_inventory']['snapshots']=[end,repeat]
    projected['gradient_inventory']=helpers['_capture_gradients'](geo,flex.vec3_double(final),projected,expected['gradient_inventory']['selected_indices'])
    stops=[l.split('lbfgs minimizer stop: ',1)[1].strip() for l in log.getvalue().splitlines() if 'lbfgs minimizer stop: ' in l]
    stopping={'reason':stops[-1] if stops else 'unreported','error':optimizer.error,'iterations':int(optimizer.iter()),
        'calls':int(optimizer.nfun()),'max_iterations':spec['max_iterations'],
        'native_criterion_met':bool(scitbx.lbfgs.traditional_convergence_test(evaluator.x.size(),1e-5)(evaluator.x,flex.double(space.project(end['gradient']))))}
    after=signature(geo,flex.vec3_double(final));sources_after=optimizer_sources()
    if before!=after or sources!=sources_after:raise RuntimeError('Constraints or native sources changed during trial')
    result.update(status='REVIEW',moving_indices=spec['moving_indices'],manager_sha256=spec['manager_sha256'],
        normalization=False,initial=initial,final=end,serialized=serialized,final_sites_cart=final,serialized_pair_inventory=pair_inventory,
        full_precision_inventory=projected,full_precision_inventory_origin='FIXED_MANAGER_EVALUATION_NOT_REINTERPRETATION',
        constraint_signature_before=before,constraint_signature_after=after,optimizer_sources=sources,
        optimizer_sources_after=sources_after,stopping=stopping,accepted_steps=evaluator.history,evaluation_calls=len(result['trace']))
except Exception as exc:
    result.update(error=type(exc).__name__+': '+str(exc));traceback.print_exc()
Path('minimizer.log').write_text(log.getvalue())
Path('selected_result.json').write_text(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def _gradient_helper_source():
    """Extract only the maintained isolated helper literal, never captured code."""
    tree = ast.parse(native_gradient_worker(native_energy_worker(_NATIVE_WORKER)))
    matches = [node.value.args[0] for node in tree.body if isinstance(node, ast.Expr)
               and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
               and node.value.func.id == 'exec' and len(node.value.args) == 2
               and isinstance(node.value.args[1], ast.Name) and node.value.args[1].id == '_gradient_helpers']
    if len(matches) != 1: raise ValueError('Maintained gradient helper boundary changed')
    return ast.literal_eval(matches[0])


def _pair_helper_source():
    return ('import math\nPAIR_POLICY='+repr(PAIR_POLICY)+'\n'+getsource(cache._close)+'\n'
            +getsource(cache.native_cache_evaluator)+'\n'+getsource(_capture_pairs))


def review_selected_pairs(native, points, snapshot, inventory):
    """Bind two actual pair evaluations to one recorded fixed-manager snapshot."""
    projected=deepcopy(native)
    for a,p in zip(projected['atoms'],points):a['xyz']=p[:]
    projected['geometry']['sites_cart_exact']=deepcopy(points)
    projected['energy_inventory']['snapshots']=[deepcopy(snapshot),deepcopy(snapshot)]
    projected['nonbonded_inventory']=inventory
    return review_native_nonbonded(projected)


def selected_geometry_worker():
    return ('import hashlib,importlib,io,json,math,os,sys,traceback\nfrom pathlib import Path\nfrom copy import deepcopy\n'
            + getsource(SelectedCoordinates) + '\n' + _WORKER_BODY)


def review_selected_result(result, native, spec, log):
    """Validate saved selection/mechanics evidence; do not rerun or certify the optimizer."""
    try:
        r = result; _limits(spec['max_iterations'], spec['max_calls'])
        space = SelectedCoordinates(native['geometry']['sites_cart_exact'], spec['moving_indices'])
        if (type(spec['schema_version']) is not int or spec['schema_version'] != 1
                or r['schema_version'] != 1 or type(r['schema_version']) is not int or r['policy_id'] != POLICY_ID
                or r['status'] != 'REVIEW' or r['normalization'] is not False or r['automatic_adoption'] is not False
                or r['scientific_approval'] != 'NOT_RUN' or r['refinement'] != 'NOT_RUN'
                or r['moving_indices'] != space.indices or r['manager_sha256'] != _manager_digest(native)
                or r['manager_sha256'] != spec['manager_sha256'] or spec['policy_id'] != POLICY_ID):
            raise ValueError('Selected trial identity or policy differs')
        if not review_native_gradients(native)['sampled_derivatives_pass']:
            raise ValueError('Starting derivatives remain unqualified')
        final = r['final_sites_cart']; space.pack(final)
        trace = r['trace']
        if (type(r['evaluation_calls']) is not int or r['evaluation_calls'] != len(trace)
                or not 5 <= len(trace) <= spec['max_calls']): raise ValueError('Invalid evaluation accounting')
        for row in trace:
            space.unpack(row['selected_coordinates']); e = row['snapshot']; space.project(e['gradient'])
            space._finite([e['target'], e['gradient_norm'], *e['terms'].values()], 2+len(e['terms']))
            if (not math.isclose(e['gradient_norm'],math.sqrt(sum(v*v for v in e['gradient'])),rel_tol=1e-12,abs_tol=1e-10)
                    or any(v is not None and (type(v) is not int or v < 0) for v in e['proxy_counts'].values())):
                raise ValueError('Invalid native trace values')
        start = native['energy_inventory']['snapshots'][0]
        if (not _numeric_equal(trace[0]['snapshot'], start) or trace[0]['selected_coordinates'] != space.pack(space.points)
                or r['initial'] != trace[0]['snapshot'] or r['final'] != trace[-3]['snapshot']
                or r['serialized'] != trace[-1]['snapshot'] or not _numeric_equal(trace[-3]['snapshot'], trace[-2]['snapshot'])
                or any(row['selected_coordinates'] != space.pack(final) for row in trace[-3:-1])
                or trace[-1]['selected_coordinates'] != [float(f'{v:.3f}') for v in space.pack(final)]):
            raise ValueError('Initial/final/serialized evidence differs')
        projected = deepcopy(native)
        for atom, point in zip(projected['atoms'], final): atom['xyz'] = point[:]
        projected['geometry']['sites_cart_exact'] = deepcopy(final)
        projected['energy_inventory']['snapshots'] = [trace[-3]['snapshot'], trace[-2]['snapshot']]
        projected['gradient_inventory'] = r['full_precision_inventory']['gradient_inventory']
        if projected != r['full_precision_inventory'] or r['full_precision_inventory_origin'] != 'FIXED_MANAGER_EVALUATION_NOT_REINTERPRETATION':
            raise ValueError('Endpoint changed more than selected coordinates and evaluated energy')
        endpoint = review_native_gradients(projected)
        rounded=space.unpack(trace[-1]['selected_coordinates'])
        review_selected_pairs(native,rounded,r['serialized'],r['serialized_pair_inventory'])
        sig = native['gradient_inventory']['constraint_signature_before']
        if any(value != sig for value in [r['constraint_signature_before'],r['constraint_signature_after'],projected['gradient_inventory']['constraint_signature_before']]):
            raise ValueError('Static native constraints differ')
        sources = r['optimizer_sources']
        if (sources != r['optimizer_sources_after'] or sources[:5] != native['gradient_inventory']['installed_numeric_sources']
                or [q['module'] for q in sources] != [*NUMERIC_MODULES,'scitbx.lbfgs','scitbx_lbfgs_ext']
                or any(not isinstance(q['sha256'],str) or len(q['sha256']) != 64 or any(c not in '0123456789abcdef' for c in q['sha256'])
                       or not isinstance(q['historical_path'],str) or not q['historical_path'] for q in sources)):
            raise ValueError('Optimizer source fingerprints differ')
        stops = [line.split('lbfgs minimizer stop: ',1)[1].strip() for line in log.splitlines() if 'lbfgs minimizer stop: ' in line]
        stopping = r['stopping']
        if (stopping['reason'] != (stops[-1] if stops else 'unreported') or stopping['max_iterations'] != spec['max_iterations']
                or type(stopping['native_criterion_met']) is not bool
                or any(type(stopping[k]) is not int or stopping[k] < 0 for k in ('iterations','calls'))
                or stopping['iterations'] > spec['max_iterations'] or stopping['calls'] != len(trace)-4
                or stopping['error'] is not None and not isinstance(stopping['error'],str)):
            raise ValueError('Optimizer stopping/call evidence differs')
        previous = -1; iteration = 0
        for step in r['accepted_steps']:
            index = step['trace_index']
            if (type(index) is not int or not previous < index < len(trace)-3
                    or type(step['iteration']) is not int or step['iteration'] != iteration+1
                    or type(step['native_calls']) is not int or step['native_calls'] != index):
                raise ValueError('Accepted-step trace differs')
            previous = index; iteration = step['iteration']
        if iteration != stopping['iterations']: raise ValueError('Incomplete accepted-step history')
        return {'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','moving_indices':space.indices,
                'fixed_coordinates_preserved':True,'initial_target':r['initial']['target'],'final_target':r['final']['target'],
                'serialized_target':r['serialized']['target'],'stopping':stopping,'stopping_classification':classify_stopping(stopping),
                'evaluation_calls':len(trace),'endpoint_sampled_derivatives_pass':endpoint['sampled_derivatives_pass'],
                'full_environment_evaluated':True,'native_execution':'NOT_RUN_BY_READER','automatic_adoption':False,
                'chemical_qualification':'NOT_ESTABLISHED','geometry_accepted':False}
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete selected native geometry evidence') from exc


def _save(path, value):
    path.write_text(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')


def _files(root):
    paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths): raise ValueError('Selected trial cannot traverse symlinks')
    return {p.relative_to(root).as_posix():_digest(p.read_bytes()) for p in paths if p.is_file() and p != root/'receipt.json'}


def run_selected_geometry(native_receipt, output_parent, executable, *, environment, phenix_version,
                          moving_indices, max_iterations=200, max_calls=2000, timeout_seconds=180):
    """Create one immutable diagnostic attempt; retain all failed/partial outputs."""
    _limits(max_iterations,max_calls)
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 3600 or not phenix_version:
        raise ValueError('Require explicit version and a finite 1-3600 second bound')
    source = _path(native_receipt); receipt,native,model,frozen = _start(source)
    space = SelectedCoordinates(native['geometry']['sites_cart_exact'],moving_indices)
    exe=Path(executable).resolve(strict=True)
    if not exe.is_file() or not os.access(exe,os.X_OK):raise ValueError('Require an executable native dispatcher')
    executable_hash=sha256(exe.read_bytes()).hexdigest()
    parent = Path(output_parent).absolute()
    if any(p.is_symlink() for p in [parent,*parent.parents]) or parent == source.parent or source.parent in parent.parents:
        raise ValueError('Output must be separate from the frozen starting capture')
    parent.mkdir(parents=True,exist_ok=True);root=Path(tempfile.mkdtemp(prefix='cif-selected-',dir=parent))
    for p,data in frozen.items():
        dest=root/'start'/p.relative_to(source.parent);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    spec_native=_json((root/'start/native_spec.json').read_bytes())
    for name in ['native_worker.py','native_spec.json',spec_native['model'],*spec_native['dictionaries'],*spec_native['phil_files']]:
        dest=root/'bootstrap'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((root/'start'/name).read_bytes())
    bootstrap_spec=dict(spec_native);bootstrap_spec.pop('gradient_indices')
    _save(root/'bootstrap/native_spec.json',bootstrap_spec)
    (root/'bootstrap/native_worker.py').write_text(native_energy_worker(_NATIVE_WORKER))
    (root/'gradient_helpers.py').write_text(_gradient_helper_source())
    (root/'nonbonded_helpers.py').write_text(_pair_helper_source())
    spec={'schema_version':1,'policy_id':POLICY_ID,'moving_indices':space.indices,'max_iterations':max_iterations,
          'max_calls':max_calls,'manager_sha256':_manager_digest(native)}
    _save(root/'selected_spec.json',spec);(root/'selected_worker.py').write_text(selected_geometry_worker())
    command=[str(exe),'-B','selected_worker.py'];start=time.monotonic()
    result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','phenix_version':str(phenix_version),
            'executable_provenance':str(exe),'executable_sha256':executable_hash,
            'command':command,'automatic_adoption':False,'execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds}}
    try:
        with (root/'native.log').open('xb') as log:
            job=subprocess.Popen(command,cwd=root,env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:rc=job.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop(job);result['execution'].update(status='TIMED_OUT',returncode=job.returncode)
            except BaseException:_stop(job);raise
            else:
                result['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
                raw=_json((root/'selected_result.json').read_bytes())
                if rc==0:
                    review_selected_result(raw,native,spec,(root/'minimizer.log').read_text())
                    (root/'candidate.pdb').write_bytes(selected_model_bytes(model,native,raw['final_sites_cart'],space.indices))
                    result['status']='REVIEW'
                else:result['error']=raw.get('error','Native selected trial failed')
    except (OSError,ValueError) as exc:result['error']=type(exc).__name__+': '+str(exc)
    result['execution']['elapsed_seconds']=time.monotonic()-start
    result['source_preserved']=all(p.read_bytes()==data for p,data in frozen.items())
    if not result['source_preserved']:result.update(status='FAILED',error='Starting capture changed')
    result['files']=_files(root);_save(root/'receipt.json',result)
    return root


def read_selected_geometry(directory):
    """Verify a completed portable attempt without SDK access or code execution."""
    root=_path(directory,directory=True);receipt=_json((root/'receipt.json').read_bytes())
    before=_files(root)
    if (type(receipt['schema_version']) is not int or receipt['schema_version']!=1 or receipt['policy_id']!=POLICY_ID
            or receipt['status']!='REVIEW' or receipt['source_preserved'] is not True or receipt['automatic_adoption'] is not False
            or receipt['execution']['status']!='COMPLETED' or type(receipt['execution']['returncode']) is not int
            or receipt['execution']['returncode']!=0 or before!=receipt['files']):
        raise ValueError('Require a complete preserved selected trial')
    _,native,model,_=_start(root/'start/native_receipt.json')
    if (root/'selected_worker.py').read_text()!=selected_geometry_worker():raise ValueError('Require the maintained selected worker')
    spec=_json((root/'selected_spec.json').read_bytes());spec_native=_json((root/'start/native_spec.json').read_bytes())
    if (root/'nonbonded_helpers.py').read_text()!=_pair_helper_source():raise ValueError('Require maintained native pair helpers')
    if (root/'gradient_helpers.py').read_text()!=_gradient_helper_source() or (root/'bootstrap/native_worker.py').read_text()!=native_energy_worker(_NATIVE_WORKER):
        raise ValueError('Require maintained numerical helpers and ordinary bootstrap worker')
    expected_spec=dict(spec_native);expected_spec.pop('gradient_indices')
    if _json((root/'bootstrap/native_spec.json').read_bytes())!=expected_spec:raise ValueError('Bootstrap request differs')
    for name in [spec_native['model'],*spec_native['dictionaries'],*spec_native['phil_files']]:
        if (root/'bootstrap'/name).read_bytes()!=(root/'start'/name).read_bytes():raise ValueError('Bootstrap inputs differ from captured start')
    rebuilt=_json((root/'bootstrap/native_validation.json').read_bytes())
    if _manager_digest(rebuilt)!=_manager_digest(native) or rebuilt['energy_inventory']!=native['energy_inventory']:
        raise ValueError('Fresh bootstrap differs from the qualified starting capture')
    raw=_json((root/'selected_result.json').read_bytes())
    report=review_selected_result(raw,native,spec,(root/'minimizer.log').read_text())
    if (root/'candidate.pdb').read_bytes()!=selected_model_bytes(model,native,raw['final_sites_cart'],spec['moving_indices']):
        raise ValueError('Candidate differs from the exact selected coordinate serialization')
    if _files(root)!=before:raise ValueError('Selected trial changed during replay')
    report['candidate_sha256']=sha256((root/'candidate.pdb').read_bytes()).hexdigest()
    return report
