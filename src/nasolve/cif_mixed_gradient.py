"""Fresh initial-only derivative evidence for a verified mixed native manager.

The numerical evaluators are the maintained fixed-native implementations. This
module stages their trusted sources, records one bounded SDK job and replays its
saved numerical evidence. It does not optimize or reuse a different manager's
derivative qualification.
"""
from __future__ import annotations
from collections import defaultdict,deque
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import time

POLICY_ID='cif-mixed-initial-native-gradient-v1'
REPORT='mixed_initial_gradients.json'
ANCHOR='mixed_initial_gradient_directory'
MAX_CALLS=2000
MAX_PAIRS=5000
_CORE_FILES={'correction_core.py':'cif_parallelity_correction.py','gradient_core.py':'cif_gradient_audit.py',
    'parallelity_core.py':'cif_parallelity_audit.py','mixed_gradient_core.py':'cif_mixed_gradient.py'}
_NUMERIC=('scitbx.lbfgs','cctbx.geometry_restraints.flags','cctbx.geometry_restraints.manager',
    'cctbx.geometry_restraints.energies','scitbx_lbfgs_ext','cctbx_geometry_restraints_ext')
_ADAPTERS=('cctbx.geometry_restraints','cctbx.array_family.flex')


def _compact_dump(path,value):
    path.write_text(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')


def _manager_digest(native):
    fields=('atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy')
    value={k:native[k] for k in fields}
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _norm(values):return math.sqrt(math.fsum(x*x for x in values))
def _close(a,b):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _need(value):
    if not value:raise ValueError('Mixed initial numerical evidence does not reproduce')


def _numeric_equal(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(_numeric_equal(v,b[k]) for k,v in a.items())
    if isinstance(a,list):return len(a)==len(b) and all(_numeric_equal(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return _close(a,b)
    return a==b


def _point_key(points):return tuple(tuple(p) for p in points)


def _gradient_replay(audit,points,baseline_evaluations,selected):
    """Replay the unchanged audit from recorded targets and repeated vectors."""
    from .cif_gradient_audit import audit_gradients,FAMILIES,STEPS
    _need(set(audit['cases'])=={'initial'} and set(baseline_evaluations)==set(FAMILIES))
    case=audit['cases']['initial'];families=case['families'];count=len(points);table=defaultdict(deque)
    def add(p,family,value):table[(family,_point_key(p))].append(deepcopy(value))
    common={};full=families['all']['baseline']['gradient']
    if _norm(full):common['full_gradient']=[v/_norm(full) for v in full]
    v=[1. if i%2 else -1. for i in range(3*count)];common['alternating_global']=[x/_norm(v) for x in v]
    for index in selected:
        for axis in range(3):
            v=[0.]*(3*count);v[3*index+axis]=1.;common[f'atom_{index}_axis_{axis}']=v
    for family in FAMILIES:
        row=families[family];records=baseline_evaluations[family]
        _need(len(records)==(3 if family=='all' else 2))
        for record in records:add(points,family,record)
        vectors=dict(common);gradient=row['baseline']['gradient']
        if _norm(gradient):vectors['family_gradient']=[v/_norm(gradient) for v in gradient]
        _need([r['direction'] for r in row['directions']]==list(vectors))
        for direction in row['directions']:
            vector=vectors[direction['direction']];_need([s['step'] for s in direction['samples']]==list(STEPS))
            for sample in direction['samples']:
                for sign,label in [(1,'plus'),(-1,'minus')]:
                    shifted=[[x+sign*sample['step']*vector[3*i+j] for j,x in enumerate(p)] for i,p in enumerate(points)]
                    add(shifted,family,{'target':sample[label+'_target'],'gradient':[0.]*(3*count),'proxy_counts':sample[label+'_proxy_counts']})
    if _norm(full):
        direction=[v/_norm(full) for v in full]
        for sample in case['descent_profile']:
            shifted=[[x-sample['step']*direction[3*i+j] for j,x in enumerate(p)] for i,p in enumerate(points)]
            add(shifted,'all',{'target':sample['target'],'gradient':[0.]*(3*count),'proxy_counts':sample['proxy_counts']})
    def evaluate(p,family):
        key=(family,_point_key(p));_need(bool(table[key]));return table[key].popleft()
    references={'initial':{k:v['captured'] for k,v in case['captured_snapshot_match']['comparisons'].items()}}
    replay=audit_gradients(evaluate,{'initial':points},selected,references=references,max_calls=MAX_CALLS)
    _need(not any(table.values()) and _numeric_equal(audit,replay))
    return replay['cases']['initial']['sampled_gradients_consistent']


def _plane_replay(audit,points,proxies):
    """Re-evaluate every reported plane comparison using its saved raw samples."""
    from .cif_parallelity_correction import audit_plane_orders
    from .cif_parallelity_audit import toy_planes,STEPS
    _need(set(audit['cases'])=={'initial'})
    stream=deque()
    def order(p,proxy,evidence):
        baseline=evidence['baseline'];directions={};g=baseline['order_safe_gradient']
        for name,indices in [('i_plane',proxy['i_seqs']),('j_plane',proxy['j_seqs'])]:
            selected=set(indices);v=[x if i//3 in selected else 0. for i,x in enumerate(g)]
            if not _norm(v):v=[(1. if i%2 else -1.) if i//3 in selected else 0. for i in range(3*len(p))]
            directions[name]=[x/_norm(v) for x in v]
        v=[1. if i%2 else -1. for i in range(3*len(p))];directions['alternating_local']=[x/_norm(v) for x in v]
        stream.append((p,proxy,baseline))
        _need([r['direction'] for r in evidence['directions']]==list(directions))
        for row in evidence['directions']:
            v=directions[row['direction']];_need([s['step'] for s in row['samples']]==list(STEPS))
            for sample in row['samples']:
                for sign,label in [(1,'plus'),(-1,'minus')]:
                    shifted=[[x+sign*sample['step']*v[3*i+j] for j,x in enumerate(point)] for i,point in enumerate(p)]
                    value={k+suffix:sample[k][label+'_target'] if suffix=='_target' else [0.]*(3*len(p))
                        for k in ['native_complete','order_safe'] for suffix in ['_target','_gradient']}
                    stream.append((shifted,proxy,value))
        stream.append((p,proxy,evidence['repeat']))
    def pair(p,proxy,row):
        indices=list(dict.fromkeys(proxy['i_seqs']+proxy['j_seqs']));mapping={i:j for j,i in enumerate(indices)}
        local={**proxy,**{k:[mapping[i] for i in proxy[k]] for k in ['i_seqs','j_seqs']}};p=[p[i] for i in indices]
        _need(row['proxy']==proxy and row['global_indices']==indices)
        order(p,local,row['original']);order(p,{**local,'i_seqs':local['j_seqs'],'j_seqs':local['i_seqs']},row['swapped'])
    rows=audit['cases']['initial']['proxies'];_need(len(rows)==len(proxies))
    for proxy,row in zip(proxies,rows):pair(points,proxy,row)
    angle=math.radians(30.);c,s=math.cos(angle),math.sin(angle)
    rotate=lambda p:[[x,c*y-s*z,s*y+c*z] for x,y,z in p]
    _need(len(audit['toy_cases'])==6)
    for i,toy in enumerate(toy_planes()):
        pair(toy['points'],toy['proxy'],audit['toy_cases'][2*i]);pair(rotate(toy['points']),toy['proxy'],audit['toy_cases'][2*i+1])
    def evaluate(p,proxy):
        _need(bool(stream));expected_p,expected_proxy,value=stream.popleft()
        _need(p==expected_p and proxy==expected_proxy);return deepcopy(value)
    replay=audit_plane_orders(evaluate,{'initial':points},proxies,max_pairs=MAX_PAIRS)
    _need(not stream and _numeric_equal(audit,replay))
    return replay['order_safe_qualified']


def _validate_result(result,expected,selected_indices):
    """Recompute sampled flags, counts, finite differences and plane controls."""
    from .cif_parallelity_correction import ORDER_CORRECTION_ID
    try:
        r=result;count=expected['atom_count'];points=expected['geometry']['sites_cart_exact']
        _need(r['schema_version']==1 and r['policy_id']==POLICY_ID and r['status']=='REVIEW' and r['scientific_qualification']=='NOT_ASSESSED'
            and r['analysis_completed'] is True and r['normalization'] is False
            and r['model_optimization']=='NOT_RUN' and r['automatic_adoption'] is False and r['correction_policy_id']==ORDER_CORRECTION_ID
            and r['selected_indices']==list(selected_indices) and 1<=len(selected_indices)<=6 and len(set(selected_indices))==len(selected_indices)
            and all(type(i) is int and 0<=i<count for i in selected_indices))
        digest=r['constraint_signature_before'];_need(isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest)
            and digest==r['constraint_signature_after'] and r['correction_statistics']['max_energy_change']==0.)
        raw=r['raw_snapshot'];reference=expected['energy_inventory']['snapshots'][0]
        _need(raw.keys()==reference.keys() and _numeric_equal(raw,reference))
        audit=r['gradient_audit'];planes=r['plane_order_audit'];proxies=r['native_parallelity_proxies']
        _need(type(audit['evaluation_calls']) is int and 0<audit['evaluation_calls']<=MAX_CALLS and audit['max_evaluation_calls']==MAX_CALLS
            and type(planes['evaluation_pairs']) is int and 0<planes['evaluation_pairs']<=MAX_PAIRS and planes['max_evaluation_pairs']==MAX_PAIRS)
        _need(type(r['correction_statistics']['correction_evaluations']) is int
            and r['correction_statistics']['correction_evaluations']==audit['evaluation_calls'])
        fields=('i_seqs','j_seqs','weight','target_angle_deg','slack','top_out','origin_id')
        _need([{k:p[k] for k in fields} for p in proxies]==[{k:p[k] for k in fields} for p in expected['geometry']['proxy_details']['parallelity']])
        complete=_gradient_replay(audit,points,r['baseline_evaluations'],list(selected_indices));plane=_plane_replay(planes,points,proxies)
        _need(_close(audit['cases']['initial']['families']['all']['baseline']['target'],raw['target']))
        checks={'complete_initial_sampled_derivatives':complete,'complete_both_order_plane_derivatives_and_controls':plane,
            'unchanged_native_energy':True,'unchanged_static_constraint_signature':True,'captured_raw_snapshot':True}
        passed=all(v is True for v in checks.values())
        return {'policy_id':POLICY_ID,'status':'MIXED_INITIAL_DERIVATIVES_PASS' if passed else 'REVIEW',
            'sampled_derivatives_pass':passed,'checks':checks,'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False}
    except (KeyError,TypeError,IndexError,ZeroDivisionError,OverflowError,AssertionError) as exc:
        raise ValueError('Incomplete mixed initial derivative evidence') from exc


_WORKER=r'''from __future__ import print_function
import hashlib,importlib,json,math,sys,traceback
from pathlib import Path
from mixed_gradient_core import POLICY_ID,MAX_CALLS,MAX_PAIRS,_NUMERIC,_ADAPTERS,_manager_digest,_compact_dump
from correction_core import evaluate_fixed_native,audit_plane_orders,plane_order_evaluator,ORDER_CORRECTION_ID
from gradient_core import audit_gradients,fixed_signature
spec=json.loads(Path('gradient_spec.json').read_text())
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','analysis_completed':False,
    'normalization':False,'model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_qualification':'NOT_ASSESSED'}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Fresh native bootstrap failed')
    native=namespace['report'];_compact_dump(Path('native_validation.json'),native)
    if hashlib.sha256(Path('correction_core.py').read_bytes()).hexdigest()!=spec['correction_core_sha256']:
        raise RuntimeError('Qualified plane correction source differs')
    if _manager_digest(native)!=spec['expected_manager_sha256']:raise RuntimeError('Captured native manager differs')
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    geo,sites=namespace['geo'],namespace['sites'];points=[list(p) for p in sites]
    special=list(geo.site_symmetry_table.special_position_indices())
    if special:raise RuntimeError('Special-position initial derivatives unsupported')
    modules=[importlib.import_module(n) for n in _NUMERIC];adapters=[importlib.import_module(n) for n in _ADAPTERS]
    def fingerprints(values):return [{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),
        'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in values]
    numeric,adapter=fingerprints(modules),fingerprints(adapters)
    if native['energy_inventory']['installed_sources']!=spec['expected_energy_sources']:raise RuntimeError('Captured native energy APIs differ')
    cpp=[];source_dir=Path(modules[2].__file__).resolve().parent
    for name in ['parallelity.h','parallelity_bpl.cpp']:
        data=(source_dir/name).read_bytes();out=Path('installed_source')/name;out.parent.mkdir(exist_ok=True);out.write_bytes(data)
        cpp.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'status':'RECORDED'})
    signature=fixed_signature(geo,sites)
    proxies=[{'i_seqs':list(p.i_seqs),'j_seqs':list(p.j_seqs),'weight':float(p.weight),'target_angle_deg':float(p.target_angle_deg),
        'slack':float(p.slack),'limit':float(p.limit),'top_out':bool(p.top_out),'origin_id':int(p.origin_id)} for p in geo.parallelity_proxies]
    stats={'max_energy_change':0.,'max_plane_residual_difference':0.,'correction_evaluations':0};baselines={n:[] for n in ['all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded']}
    def evaluate(p,family):
        active=flags.flags(default=family=='all')
        if family!='all':setattr(active,family,True)
        value=evaluate_fixed_native(geo,p,active,gr,flex,plane_order_safe=True)
        delta=abs(value['target']-value['native_target']);stats['max_energy_change']=max(stats['max_energy_change'],delta)
        if delta:raise RuntimeError('Correction changed native energy')
        detail=value['parallelity_correction']
        if detail['applied']:stats['max_plane_residual_difference']=max(stats['max_plane_residual_difference'],abs(detail['native_plane_residual']-detail['individual_plane_residual']))
        stats['correction_evaluations']+=1
        simple={k:value[k] for k in ['target','gradient','proxy_counts']}
        if p==points:baselines[family].append(simple)
        return simple
    raw=native['energy_inventory']['snapshots'][0]
    audit=audit_gradients(evaluate,{'initial':points},spec['selected_indices'],references={'initial':{'target':raw['target']}},max_calls=MAX_CALLS)
    planes=audit_plane_orders(plane_order_evaluator(gr,flex),{'initial':points},proxies,max_pairs=MAX_PAIRS)
    after=fixed_signature(geo,sites)
    if after!=signature or points!=[list(p) for p in sites]:raise RuntimeError('Audit changed coordinates or static constraints')
    for row in numeric+adapter:
        if hashlib.sha256(Path(row['historical_path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native numeric source changed')
    for row in cpp:
        if hashlib.sha256((source_dir/row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Native plane source changed')
    result.update(status='REVIEW',analysis_completed=True,selected_indices=spec['selected_indices'],raw_snapshot=raw,
        gradient_audit=audit,plane_order_audit=planes,baseline_evaluations=baselines,native_parallelity_proxies=proxies,
        correction_policy_id=ORDER_CORRECTION_ID,correction_statistics=stats,constraint_signature_before=signature,
        constraint_signature_after=after,installed_numeric_sources=numeric,installed_adapter_sources=adapter,
        installed_numeric_sources_after=fingerprints(modules),installed_adapter_sources_after=fingerprints(adapters),
        installed_parallelity_sources=cpp,special_position_indices=special,coordinates_unchanged=True,
        manager_sha256=_manager_digest(native),correction_core_sha256=spec['correction_core_sha256'])
except Exception as exc:
    result.update(error=type(exc).__name__+': '+str(exc));traceback.print_exc()
_compact_dump(Path('gradient_result.json'),result)
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def _ref(path,root,anchor=ANCHOR):
    from .cif_mixed_recovery import _safe
    path,root=Path(path),Path(root)
    if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Gradient artifact traverses symlink')
    name=path.relative_to(root).as_posix()
    if not _safe(name):raise ValueError('Unsafe gradient artifact')
    data=path.read_bytes();return {'anchor':anchor,'path':name,'sha256':sha256(data).hexdigest(),'size':len(data)}


def _resolve(root,context,parent,ref):
    from .cif_mixed_recovery import _safe
    directories={ANCHOR:Path(root),'context_directory':Path(context),'linked_parent_directory':Path(parent)}
    if not isinstance(ref,dict) or ref.get('anchor') not in directories or not _safe(ref.get('path')):raise ValueError('Unsafe gradient reference')
    directory=directories[ref['anchor']];path=directory/ref['path']
    if _ref(path,directory,ref['anchor'])!=ref:raise ValueError('Gradient artifact differs')
    return path


def _inputs(context_root,parent_root):
    from .cif_mixed_context import read_mixed_context,_resolve as resolve
    context_root,parent_root=Path(context_root),Path(parent_root)
    context=read_mixed_context(context_root,linked_parent_directory=parent_root)
    if context['status']!='MIXED_CONTEXT_MECHANICS_PASS':raise ValueError('Require verified full mixed native mechanics')
    capture_path=resolve(context_root,parent_root,context['native_active']['receipt']);capture=json.loads(capture_path.read_bytes())
    expected=capture['native_validation'];refs=context['inputs']
    model=resolve(context_root,parent_root,refs['model']);dictionaries=[resolve(context_root,parent_root,r) for r in context['bundle']['native_dictionaries']]
    phils=[resolve(context_root,parent_root,refs['active_policy']),*[resolve(context_root,parent_root,r) for r in context['bundle']['context_phils']]]
    def bind(path):return _ref(path,context_root,'context_directory') if path.is_relative_to(context_root) else _ref(path,parent_root,'linked_parent_directory')
    bindings={'context_report':_ref(context_root/'mixed_context.json',context_root,'context_directory'),
        'linked_parent_report':_ref(parent_root/'mixed_linked_recovery.json',parent_root,'linked_parent_directory'),
        'active_capture':bind(capture_path),'model':bind(model),'dictionaries':[bind(p) for p in dictionaries],'phils':[bind(p) for p in phils]}
    return context,model,dictionaries,phils,expected,bindings


def _prepare(root,model,dictionaries,phils,expected):
    from .cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID
    from .cif_candidate_usability import native_energy_worker
    from .cif_gradient_audit import review_distance_groups
    from .cif_fixed_geometry import _fixed_policy
    from .cif_corrected_geometry import QUALIFIED_CORRECTION_SHA256
    _need(sha256(Path(__file__).with_name('cif_parallelity_correction.py').read_bytes()).hexdigest()==QUALIFIED_CORRECTION_SHA256)
    _need(_fixed_policy(expected));points=expected['geometry']['sites_cart_exact'];plan=review_distance_groups(expected,points)
    proxies=expected['geometry']['proxy_details']['parallelity'];pairs=52*(len(proxies)+6)
    _need(1<=len(proxies)<=64 and pairs<=MAX_PAIRS)
    work=root/'job';(work/'inputs').mkdir(parents=True);inputs=[]
    paths=[model,*dictionaries,*phils]
    for i,path in enumerate(paths):
        role='model' if i==0 else 'dictionary' if i<=len(dictionaries) else 'phil';out=work/'inputs'/f'{i:03d}_{role}{path.suffix}'
        out.write_bytes(path.read_bytes());inputs.append({'role':role,'input_index':i,'artifact':_ref(out,root)})
    native={'policy_id':NATIVE_POLICY_ID,'model':inputs[0]['artifact']['path'].removeprefix('job/'),
        'dictionaries':[v['artifact']['path'].removeprefix('job/') for v in inputs if v['role']=='dictionary'],
        'phil_files':[v['artifact']['path'].removeprefix('job/') for v in inputs if v['role']=='phil'],
        'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked','policy_inventory':True,'energy_inventory':True}
    spec={'policy_id':POLICY_ID,'selected_indices':plan['selected_indices'],'expected_manager_sha256':_manager_digest(expected),
        'expected_energy_sources':expected['energy_inventory']['installed_sources'],'max_energy_calls':MAX_CALLS,'max_plane_pairs':MAX_PAIRS,
        'required_plane_pairs':pairs,'correction_core_sha256':QUALIFIED_CORRECTION_SHA256}
    _compact_dump(work/'native_spec.json',native);_compact_dump(work/'gradient_spec.json',spec);_compact_dump(root/'initial_probe_plan.json',plan)
    (work/'native_worker.py').write_text(native_energy_worker(_NATIVE_WORKER));(work/'gradient_worker.py').write_text(_WORKER)
    for name,source in _CORE_FILES.items():(work/name).write_bytes(Path(__file__).with_name(source).read_bytes())
    return {'inputs':inputs,'native_spec':_ref(work/'native_spec.json',root),'gradient_spec':_ref(work/'gradient_spec.json',root),
        'probe_plan':_ref(root/'initial_probe_plan.json',root),'selected_indices':plan['selected_indices'],
        'required_plane_pairs':pairs,'cores':{name:_ref(work/name,root) for name in _CORE_FILES},
        'worker':_ref(work/'gradient_worker.py',root),'native_worker':_ref(work/'native_worker.py',root)}


def _decision():return {'status':'CONTINUE_WITH_NOTES','selected':'verified_constructed_model','native_usable':True,
    'optional_derivative_phase':True,'requires_cif_review':False,'automatic_adoption':False}


def _publish(root,context,parent,report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT and p.suffix not in {'.pickle','.pkl','.pyc'}]
    _compact_dump(root/REPORT,report);read_mixed_initial_gradients(root,context_directory=context,linked_parent_directory=parent);return report


def audit_mixed_initial_gradients(context_directory,linked_parent_directory,phenix,output,*,timeout_seconds=600):
    from .cif_native_validation import _stop
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require a native deadline from1to600seconds')
    context,parent,root=Path(context_directory),Path(linked_parent_directory),Path(output).absolute()
    if root.exists() or any(p.is_symlink() for p in [root,*root.parents]) or any(root.resolve().is_relative_to(p.resolve()) for p in [context,parent]):
        raise ValueError('Require a fresh separate gradient output')
    source,model,dictionaries,phils,expected,bindings=_inputs(context,parent);root.mkdir(parents=True)
    preparation=_prepare(root,model,dictionaries,phils,expected)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':preparation,
        'new_native_calls':0,'maximum_native_calls':1,'timeout_seconds':timeout_seconds,'execution':{'status':'NOT_RUN'},
        'qualification':{'status':'NOT_RUN'},'coordinate_decision':_decision(),'maximum_energy_calls':MAX_CALLS,'maximum_plane_pairs':MAX_PAIRS,
        'initial_coordinates_only':True,'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','readyset_execution':'NOT_RUN',
        'coot_execution':'NOT_RUN','refinement':'NOT_RUN','cache_writes':'NOT_RUN','captured_code_execution':'NOT_RUN',
        'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,'requires_cif_review':False,'policy_authority':'NARestraints',
        'source_chemical_findings':'PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_DERIVATIVE_QUALIFICATION'}
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True);before=sha256(executable.read_bytes()).hexdigest()
        report.update(status='REVIEW',phenix_version=phenix.version,executable_provenance=str(executable),executable_sha256=before)
        started=time.monotonic()
        try:
            with (root/'job/gradient.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','gradient_worker.py'],cwd=root/'job',env=dict(phenix.environment),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                report['new_native_calls']=1
                try:code=process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:_stop(process);report['execution']={'status':'TIMED_OUT','returncode':process.returncode}
                except BaseException:_stop(process);raise
                else:report['execution']={'status':'COMPLETED' if code==0 else 'FAILED','returncode':code}
            if report['execution']['status']=='COMPLETED':
                result=json.loads((root/'job/gradient_result.json').read_bytes());q=_validate_result(result,expected,preparation['selected_indices'])
                _compact_dump(root/'qualification.json',q);report['qualification']={'artifact':_ref(root/'qualification.json',root)}
                if q['sampled_derivatives_pass']:report['status']='MIXED_INITIAL_DERIVATIVES_PASS'
        except (OSError,ValueError,KeyError,TypeError) as exc:
            report['error']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['error']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
        if sha256(executable.read_bytes()).hexdigest()!=before:raise ValueError('Selected native interpreter changed')
    return _publish(root,context,parent,report)


def _read_mixed_initial_gradients(directory,*,context_directory,linked_parent_directory):
    from .cif_native_validation import _NATIVE_WORKER
    from .cif_candidate_usability import native_energy_worker
    root,context,parent=map(Path,(directory,context_directory,linked_parent_directory))
    if any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('Unsafe gradient directory')
    report=json.loads((root/REPORT).read_bytes());_need(report['policy_id']==POLICY_ID and report['schema_version']==1
        and report['status'] in {'PREPARED_ONLY','REVIEW','MIXED_INITIAL_DERIVATIVES_PASS'} and report['initial_coordinates_only'] is True
        and report['automatic_adoption'] is False and report['requires_cif_review'] is False and report['scientific_qualification']=='NOT_ASSESSED'
        and report['policy_authority']=='NARestraints' and report['coordinate_decision']==_decision()
        and all(report[k]=='NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution'])
        and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600)
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,context,parent,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT and p.suffix not in {'.pickle','.pkl','.pyc'}:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    _,model,dictionaries,phils,expected,bindings=_inputs(context,parent);_need(report['inputs']==bindings)
    prep=report['preparation'];work=root/'job'
    _need((work/'native_worker.py').read_bytes()==native_energy_worker(_NATIVE_WORKER).encode() and (work/'gradient_worker.py').read_bytes()==_WORKER.encode())
    for name,source in _CORE_FILES.items():_need((work/name).read_bytes()==Path(__file__).with_name(source).read_bytes())
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix='mixed-gradient-reader-') as temporary:
        replay=Path(temporary).resolve();fresh=_prepare(replay,model,dictionaries,phils,expected);_need(prep==fresh)
        for p in replay.rglob('*'):
            if p.is_file():_need((root/p.relative_to(replay)).read_bytes()==p.read_bytes())
    _need(report['maximum_native_calls']==1 and report['maximum_energy_calls']==MAX_CALLS and report['maximum_plane_pairs']==MAX_PAIRS
        and type(report['new_native_calls']) is int and report['new_native_calls'] in {0,1})
    q=None
    if 'artifact' in report['qualification']:
        _need(report['new_native_calls']==1 and report['execution']['status']=='COMPLETED' and report['execution']['returncode']==0)
        q=json.loads(_resolve(root,context,parent,report['qualification']['artifact']).read_bytes())
        result=json.loads((work/'gradient_result.json').read_bytes());native=json.loads((work/'native_validation.json').read_bytes())
        from .cif_corrected_geometry import QUALIFIED_CORRECTION_SHA256
        _need(_manager_digest(native)==_manager_digest(expected) and result['manager_sha256']==_manager_digest(expected)
            and result['coordinates_unchanged'] is True and result['special_position_indices']==[]
            and result['correction_core_sha256']==QUALIFIED_CORRECTION_SHA256
            and native['energy_inventory']['installed_sources']==expected['energy_inventory']['installed_sources']
            and _numeric_equal(native['energy_inventory'],expected['energy_inventory'])
            and _numeric_equal(result['raw_snapshot'],native['energy_inventory']['snapshots'][0]))
        _need(_numeric_equal(q,_validate_result(result,expected,prep['selected_indices'])))
        for field,modules in [('installed_numeric_sources',_NUMERIC),('installed_adapter_sources',_ADAPTERS)]:
            rows=result[field]
            _need([r['module'] for r in rows]==list(modules) and all(isinstance(r['sha256'],str) and len(r['sha256'])==64
                and all(c in '0123456789abcdef' for c in r['sha256']) and isinstance(r['historical_path'],str) and bool(r['historical_path']) for r in rows)
                and result[field+'_after']==rows)
        pins={r['module']:r['sha256'] for field in ['installed_numeric_sources','installed_adapter_sources'] for r in result[field]}
        _need(all(r['module'] in pins and pins[r['module']]==r['sha256'] for r in expected['energy_inventory']['installed_sources']))
        _need({r['path'] for r in result['installed_parallelity_sources']}=={'parallelity.h','parallelity_bpl.cpp'})
        for row in result['installed_parallelity_sources']:
            data=(work/'installed_source'/row['path']).read_bytes();_need(row=={'path':row['path'],'bytes':len(data),'sha256':sha256(data).hexdigest(),'status':'RECORDED'})
    else:_need(report['qualification']=={'status':'NOT_RUN'})
    if report['new_native_calls']==0:
        _need(q is None and ((report['status']=='PREPARED_ONLY' and report['execution']=={'status':'NOT_RUN'})
            or (report['status']=='REVIEW' and report['execution'].get('status')=='LAUNCH_FAILED'
                and isinstance(report['execution'].get('error'),str) and bool(report['execution']['error'])
                and type(report['execution'].get('elapsed_seconds')) in (int,float)
                and math.isfinite(report['execution']['elapsed_seconds']) and report['execution']['elapsed_seconds']>=0)))
    else:
        execution=report['execution'];state=execution['status'];code=execution['returncode']
        _need(report['status']!='PREPARED_ONLY' and state in {'COMPLETED','FAILED','TIMED_OUT'}
            and type(code) is int and (state!='COMPLETED' or code==0) and (state!='FAILED' or code!=0)
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0
            and isinstance(report['phenix_version'],str) and bool(report['phenix_version'])
            and isinstance(report['executable_provenance'],str) and bool(report['executable_provenance'])
            and isinstance(report['executable_sha256'],str) and len(report['executable_sha256'])==64
            and all(c in '0123456789abcdef' for c in report['executable_sha256']))
    passed=q is not None and q['sampled_derivatives_pass'] is True
    _need((report['status']=='MIXED_INITIAL_DERIVATIVES_PASS')==passed)
    return report


def read_mixed_initial_gradients(directory,*,context_directory,linked_parent_directory):
    """Read only maintained sources and saved evidence, never launch an SDK."""
    try:return _read_mixed_initial_gradients(directory,context_directory=context_directory,linked_parent_directory=linked_parent_directory)
    except (KeyError,TypeError,IndexError) as exc:raise ValueError('Incomplete mixed initial gradient report') from exc
