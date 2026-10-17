"""Explicit geometry-only trials against fixed, captured native definitions."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .cif_captured_geometry import review_captured_geometry
from .cif_fragment_restoration import _model
from .cif_native_validation import _NATIVE_WORKER, _artifact, _stop, NATIVE_POLICY_ID

FIXED_GEOMETRY_POLICY = 'cif-fixed-native-geometry-trial-v1'
API_SOURCES = [
    {'url':'https://github.com/cctbx/cctbx_project/blob/master/scitbx/lbfgs/__init__.py',
     'git_blob':'f45c898e36cc736c7ec9a324d49bd413a0a069df'},
    {'url':'https://github.com/cctbx/cctbx_project/blob/master/cctbx/geometry_restraints/flags.py',
     'git_blob':'e67e240cc4c260bfbb8c4576c49056ec69c13c31'},
    {'url':'https://github.com/cctbx/cctbx_project/blob/master/cctbx/geometry_restraints/energies.py',
     'git_blob':'762debe3994bc1d5d80d766d937a5da7b9b6a4fc'},
]


def classify_stopping(stopping: dict) -> str:
    """Retain limit/error outcomes even when target or gradients improved."""
    if stopping['error']:
        return 'NOT_CONVERGED_ERROR'
    if stopping['iterations'] >= stopping['max_iterations'] or stopping['reason'] in {'max_iterations','max_calls'}:
        return 'NOT_CONVERGED_LIMIT'
    if stopping['reason'] == 'traditional_convergence_test':
        return 'NATIVE_CRITERION_MET' if stopping['native_criterion_met'] is True else 'NOT_CONVERGED'
    return 'NOT_ASSESSED'


def _points(points, count):
    if len(points) != count or any(len(p)!=3 or any(isinstance(v,bool) or not math.isfinite(float(v)) for v in p) for p in points):
        raise ValueError('Require complete finite full-precision coordinate correspondence')
    return [[float(v) for v in p] for p in points]


def review_fixed_coordinates(native: dict, points: list) -> dict:
    review_captured_geometry(native)
    points=_points(points,native['atom_count']);projection=deepcopy(native)
    projection['geometry']['sites_cart_exact']=points
    for atom,point in zip(projection['atoms'],points):atom['xyz']=point
    result=review_captured_geometry(projection)
    result['coordinate_source']='FIXED_MANAGER_FULL_PRECISION'
    return result


def write_geometry_candidate(source: Path, output: Path, native: dict, points: list) -> dict:
    """Preserve every PDB byte except the explicit new coordinate columns."""
    source,output=Path(source),Path(output)
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    original=source.read_bytes();_model(native,source,coordinates_match=True)
    points=_points(points,native['atom_count']);lines=original.splitlines(keepends=True)
    indices=[i for i,line in enumerate(lines) if line.startswith((b'ATOM  ',b'HETATM'))]
    if len(indices)!=len(points):raise ValueError('PDB/native ordering count mismatch')
    distances=[];roundtrip=[];by_site={}
    for i,atom,point in zip(indices,native['atoms'],points):
        line=lines[i];identity=atom['identity']
        key=(line[21:22].decode().strip(),line[22:26].decode().strip(),line[12:16].decode().strip())
        if key!=(identity['chain_id'].strip(),identity['resseq'].strip(),atom['atom_id']):
            raise ValueError('PDB/native atom ordering differs')
        fields=''.join(f'{v:8.3f}' for v in point)
        if len(fields)!=24:raise ValueError('Coordinate exceeds PDB field width')
        rounded=[float(fields[j:j+8]) for j in (0,8,16)]
        roundtrip.append(math.dist(rounded,point));distance=math.dist(atom['xyz'],point);distances.append(distance)
        by_site.setdefault(':'.join(key[:2]),[]).append(distance)
        lines[i]=line[:30]+fields.encode('ascii')+line[54:]
    candidate=b''.join(lines)
    if source.read_bytes()!=original:raise ValueError('Source model changed during serialization')
    def stats(values):return {'max':max(values,default=0.),'rms':math.sqrt(sum(v*v for v in values)/len(values)) if values else 0.,'mean':sum(values)/len(values) if values else 0.}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as handle:handle.write(candidate)
    return {'schema_version':1,'policy_id':FIXED_GEOMETRY_POLICY,'status':'REVIEW',
        'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'source_sha256':hashlib.sha256(original).hexdigest(),
        'atom_count':len(points),'metadata_and_headers_preserved':True,'source_preserved':True,
        'roundtrip_max_distance':max(roundtrip,default=0.),'roundtrip_precision':'PDB_8_3_SEPARATE_FROM_FULL_PRECISION',
        'displacement':stats(distances),'per_site_displacement':{s:stats(v) for s,v in by_site.items()},
        'scientific_approval':'NOT_RUN','automatic_adoption':False}


# The bootstrap is our unchanged inventory worker, executed in its own namespace.
# Catch only its successful SystemExit; keep its constructed native manager in
# this process. No captured executable script or pickle is loaded.
_GEOMETRY_WORKER = r'''from __future__ import print_function
import hashlib, importlib, io, json, math, sys, traceback
from pathlib import Path

trial = json.loads(Path(sys.argv[1]).read_text())
result = {"schema_version":1,"policy_id":trial["policy_id"],"status":"RUNNING",
          "scientific_approval":"NOT_RUN","automatic_adoption":False,"refinement":"NOT_RUN",
          "readyset_retry":"NOT_RUN","diffraction_data":"NOT_READ"}

def save():
    Path("geometry_result.json").write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")

def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()

try:
    sys.argv=["native_worker.py",trial["native_spec"]]
    namespace={"__name__":"__main__","__file__":"native_worker.py"}
    try:
        exec(compile(Path("native_worker.py").read_text(),"native_worker.py","exec"),namespace)
    except SystemExit as exc:
        if exc.code != 0:raise RuntimeError("Native inventory bootstrap did not complete")
    inventory=namespace["report"];expected=json.loads(Path(trial["expected_inventory"]).read_text())
    fields=["atoms","atom_count","monomer_mappings","geometry","installed_api_sources"]
    if any(inventory.get(k)!=expected.get(k) for k in fields):
        raise RuntimeError("Captured native identities, coordinates, definitions, proxies or APIs changed before minimization")
    result["captured_inventory_matches"]=True
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    import scitbx.lbfgs
    geo=namespace["geo"];sites=namespace["sites"].deep_copy()
    special=geo.site_symmetry_table.special_position_indices()
    result["special_position_count"]=len(special)
    if len(special):raise RuntimeError("Special-position coordinates require an explicit constraint policy")
    crystal=geo.crystal_symmetry
    result["crystal_symmetry"]={"unit_cell":list(crystal.unit_cell().parameters()),"space_group":str(crystal.space_group_info())}
    modules=[scitbx.lbfgs,flags,importlib.import_module("cctbx.geometry_restraints.manager"),
        importlib.import_module("cctbx.geometry_restraints.energies"),
        importlib.import_module("scitbx_lbfgs_ext"),importlib.import_module("cctbx_geometry_restraints_ext")]
    result["installed_optimizer_sources"]=[{"module":m.__name__,"historical_path":str(Path(m.__file__).resolve()),
        "sha256":hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in modules]
    active=flags.flags(default=True)
    result["flags"]={k:v for k,v in vars(active).items() if isinstance(v,bool)}
    result["normalization"]=False

    def value(v):
        if v is None or isinstance(v,(str,bool,int,float)):return v
        return list(v)
    def signature(points):
        pair=geo.pair_proxies(sites_cart=points).bond_proxies
        data={"simple":[[list(p.i_seqs),float(p.distance_ideal),float(p.weight),getattr(p,"origin_id",None),
                  value(getattr(p,"slack",None)),value(getattr(p,"limit",None)),value(getattr(p,"top_out",None)),
                  str(getattr(p,"rt_mx_ji",None))] for p in pair.simple],
              "asu":[[int(p.i_seq),int(p.j_seq),int(p.j_sym),float(p.distance_ideal),float(p.weight),getattr(p,"origin_id",None),
                  str(pair.asu_mappings().get_rt_mx_ji(pair=p))] for p in pair.asu]}
        fields={"angle":["angle_ideal","weight"],"dihedral":["angle_ideal","weight","periodicity","alt_angle_ideals"],
                "const_dihedral":["angle_ideal","weight","periodicity"],"chirality":["volume_ideal","both_signs","weight"],
                "planarity":["weights"],"parallelity":["j_seqs","weight","target_angle_deg","slack","top_out"]}
        for kind,attributes in fields.items():
            data[kind]=[[list(p.i_seqs),getattr(p,"origin_id",None)]+[value(getattr(p,a,None)) for a in attributes]
                        for p in (getattr(geo,kind+"_proxies") or [])]
        return canonical(data)
    fixed=signature(sites);result["constraint_signature_before"]=fixed
    def energy(points):
        e=geo.energies_sites(sites_cart=points,flags=active,compute_gradients=True,normalization=False)
        g=e.gradients.as_double()
        if not math.isfinite(float(e.target)) or not all(math.isfinite(float(v)) for v in g):
            raise RuntimeError("Non-finite native objective or gradient")
        return e
    def snapshot(e):
        return {"target":float(e.target),"gradient_norm":float(e.gradients.as_double().norm()),
            "max_atom_gradient":max(float(v) for v in e.gradients.norms()),
            "terms":{k:float(v) for k,v in vars(e).items() if k.endswith("_residual_sum") and isinstance(v,(int,float))},
            "proxy_counts":{k:v for k,v in vars(e).items() if k.startswith("n_") and k.endswith("_proxies") and (v is None or isinstance(v,int))}}
    result["initial"]=snapshot(energy(sites));save()
    class Evaluator:
        def __init__(self):self.x=sites.as_double().deep_copy();self.history=[]
        def compute_functional_and_gradients(self):
            self.current=energy(flex.vec3_double(self.x))
            return self.current.target,self.current.gradients.as_double()
        def callback_after_step(self,minimizer):
            self.history.append({"iteration":int(minimizer.iter()),"calls":int(minimizer.nfun()),
                "target":float(self.current.target),"gradient_norm":float(self.current.gradients.as_double().norm())})
            return False
    evaluator=Evaluator();log=io.StringIO()
    limits={"max_iterations":trial["max_iterations"],"max_calls":trial["max_calls"],
            "traditional_convergence_test":True,"traditional_convergence_test_eps":trial["gradient_epsilon"]}
    result["termination_parameters"]=limits
    try:
        minimizer=scitbx.lbfgs.run(target_evaluator=evaluator,
            termination_params=scitbx.lbfgs.termination_parameters(**limits),log=log)
    finally:
        Path("minimizer.log").write_text(log.getvalue())
        result["accepted_step_history"]=evaluator.history
    final=flex.vec3_double(evaluator.x);e=energy(final)
    result["final"]=snapshot(e);result["final_sites_cart"]=[list(p) for p in final]
    rounded=flex.vec3_double([tuple(float("%.3f"%v) for v in p) for p in final])
    result["serialized"]=snapshot(energy(rounded))
    result["constraint_signature_after"]=signature(final)
    if fixed!=result["constraint_signature_after"]:raise RuntimeError("Native restraint definitions changed during minimization")
    stops=[line.split("lbfgs minimizer stop: ",1)[1].strip() for line in log.getvalue().splitlines() if "lbfgs minimizer stop: " in line]
    result["stopping"]={"reason":stops[-1] if stops else "unreported","error":minimizer.error,
        "iterations":int(minimizer.iter()),"calls":int(minimizer.nfun()),"max_iterations":trial["max_iterations"],
        "native_criterion_met":bool(scitbx.lbfgs.traditional_convergence_test(evaluator.x.size(),trial["gradient_epsilon"])(evaluator.x,e.gradients.as_double()))}
    for row in result["installed_optimizer_sources"]:
        if hashlib.sha256(Path(row["historical_path"]).read_bytes()).hexdigest()!=row["sha256"]:
            raise RuntimeError("Installed optimizer source changed during trial")
    result["status"]="REVIEW"
except Exception as exc:
    result.update(status="FAILED",error=type(exc).__name__+": "+str(exc));traceback.print_exc()
finally:
    save()
sys.exit(0 if result["status"]=="REVIEW" else 2)
'''


def run_fixed_geometry(model: Path, dictionaries: list[Path], phils: list[Path], expected: dict,
        output_parent: Path, executable: Path, *, environment: dict, phenix_version: str,
        max_iterations: int=500, timeout_seconds: int=1200) -> dict:
    """Run one bounded native trial in a fresh directory; retain failure evidence."""
    if isinstance(max_iterations,bool) or not 1<=max_iterations<=1000:raise ValueError('Iterations must be 1-1000')
    if not math.isfinite(float(timeout_seconds)) or not 1<=timeout_seconds<=3600:raise ValueError('Timeout must be 1-3600 seconds')
    if not phenix_version:raise ValueError('Explicit Phenix version required')
    review_captured_geometry(expected);_model(expected,model,coordinates_match=True)
    paths=[Path(p).resolve() for p in [model,*dictionaries,*phils]]
    if not dictionaries or len(paths)!=len(set(paths)):raise ValueError('Require distinct explicit native inputs')
    parent=Path(output_parent).resolve()
    if any(parent==p.parent or p.parent in parent.parents for p in paths):raise ValueError('Trial output must be outside preserved input directories')
    payloads=[p.read_bytes() for p in paths];parent.mkdir(parents=True,exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='cif-fixed-geometry-',dir=parent));(work/'inputs').mkdir()
    frozen=[];inputs=[]
    for i,(path,data) in enumerate(zip(paths,payloads)):
        role='model' if i==0 else 'dictionary' if i<=len(dictionaries) else 'phil'
        target=work/'inputs'/(f'{i:03d}_{role}'+path.suffix);target.write_bytes(data);frozen.append(target)
        inputs.append({'input_index':i,'role':role,'source_provenance':str(path),**_artifact(target,work)})
    spec={'policy_id':NATIVE_POLICY_ID,'model':frozen[0].relative_to(work).as_posix(),
        'dictionaries':[p.relative_to(work).as_posix() for p in frozen[1:1+len(dictionaries)]],
        'phil_files':[p.relative_to(work).as_posix() for p in frozen[1+len(dictionaries):]],
        'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked'}
    trial={'policy_id':FIXED_GEOMETRY_POLICY,'native_spec':'native_spec.json','expected_inventory':'expected_inventory.json',
        'max_iterations':max_iterations,'max_calls':max_iterations*20,'gradient_epsilon':1e-5}
    for name,data in [('native_spec.json',spec),('geometry_spec.json',trial),('expected_inventory.json',expected)]:
        (work/name).write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')
    (work/'native_worker.py').write_text(_NATIVE_WORKER);(work/'geometry_worker.py').write_text(_GEOMETRY_WORKER)
    executable=Path(executable).resolve();command=[str(executable),'geometry_worker.py','geometry_spec.json']
    receipt={'schema_version':1,'audit_kind':'cif_fixed_native_geometry_trial','policy_id':FIXED_GEOMETRY_POLICY,
        'status':'FAILED','native_directory':str(work),'inputs':inputs,'command':command,
        'executable_provenance':str(executable),'executable_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
        'phenix_version':phenix_version,'api_sources':API_SOURCES,'automatic_adoption':False,'scientific_approval':'NOT_RUN',
        'refinement':'NOT_RUN','readyset_retry':'NOT_RUN','diffraction_data':'NOT_READ',
        'execution':{'status':'NOT_RUN','started_at':datetime.now(timezone.utc).isoformat(),'timeout_seconds':timeout_seconds}}
    clock=time.monotonic()
    try:
        with (work/'geometry.log').open('xb') as log:
            process=subprocess.Popen(command,cwd=work,env=dict(environment),stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:code=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop(process);receipt['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_stop(process);raise
            else:
                receipt['execution'].update(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
                path=work/'geometry_result.json'
                if not path.is_file() or path.is_symlink():raise ValueError('Worker omitted regular geometry_result.json')
                result=json.loads(path.read_text());receipt['result']=result
                if result.get('status')=='REVIEW' and code==0:
                    if result.get('policy_id')!=FIXED_GEOMETRY_POLICY or not result.get('captured_inventory_matches'):
                        raise ValueError('Worker omitted captured-manager match')
                    if result.get('constraint_signature_before')!=result.get('constraint_signature_after'):
                        raise ValueError('Worker changed fixed constraints')
                    _points(result['final_sites_cart'],expected['atom_count'])
                    receipt['convergence']=classify_stopping(result['stopping']);receipt['status']='REVIEW'
                else:receipt['error']=result.get('error','Geometry worker did not complete')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        receipt['error']=str(exc);receipt['execution']['status']='FAILED'
    receipt['source_preserved']=all(p.is_file() and p.read_bytes()==b for p,b in zip(paths,payloads))
    receipt['frozen_inputs_preserved']=all(p.is_file() and p.read_bytes()==b for p,b in zip(frozen,payloads))
    if not receipt['source_preserved'] or not receipt['frozen_inputs_preserved']:
        receipt.update(status='FAILED',error='Original or frozen geometry inputs changed')
    receipt['execution'].update(elapsed_seconds=round(time.monotonic()-clock,6),finished_at=datetime.now(timezone.utc).isoformat())
    receipt['outputs']=[_artifact(p,work) for p in sorted(work.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in work.rglob('*')):receipt.update(status='FAILED',error='Unexpected geometry output symlink')
    (work/'geometry_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return receipt
