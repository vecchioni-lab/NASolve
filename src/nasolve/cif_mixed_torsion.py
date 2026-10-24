"""Fixed-coordinate native torsion localization after a retained geometry trial.

All native kernels, chemical definitions and the original continuation decision
remain unchanged. Finer differences are diagnostic observations, never a new
endpoint qualification or an instruction to remove a restraint.
"""
from __future__ import annotations
from collections import deque
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time

POLICY_ID='cif-mixed-fixed-torsion-audit-v1'
REPORT='mixed_torsion_audit.json'
ANCHOR='mixed_torsion_directory'
STEPS=(1e-3,1e-4,1e-5,1e-6,1e-7,1e-8,1e-9)
MAX_PAIRS=10000
MAX_GROUP_CALLS=600
MAX_PROXIES=8
NEAR_SINE=math.sin(math.radians(5.))
CASES=('initial','full_precision','pdb_rounded')
_FIELDS=('i_seqs','angle_ideal','weight','periodicity','alt_angle_ideals','origin_id')


def _need(value):
    if not value:raise ValueError('Mixed torsion evidence does not reproduce')
def _norm(values):return math.sqrt(math.fsum(v*v for v in values))
def _close(a,b):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _bytes(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def _dump(path,value):Path(path).write_bytes(_bytes(value)+b'\n')
def _digest(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def _hash(value):return sha256(_bytes(value)).hexdigest()
def _load(path):
    from .cif_review_transport import _parse_json
    return _parse_json(Path(path).read_bytes())
def _same(a,b):
    if type(a) is not type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(_same(v,b[k]) for k,v in a.items())
    if isinstance(a,list):return len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    return _close(a,b) if isinstance(a,float) else a==b

def _geometry(points):
    if __package__:from .cif_dihedral_conditioning import dihedral_geometry
    else:from conditioning_core import dihedral_geometry
    return dihedral_geometry(points)

def _points(cases):
    _need(set(cases)==set(CASES));count=len(cases['initial']);_need(count>0)
    for points in cases.values():_need(len(points)==count and all(len(p)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in p) for p in points))
    return count

def _proxy(row,count):
    p={k:deepcopy(row.get(k)) for k in _FIELDS};ids=p['i_seqs'];alt=p['alt_angle_ideals']
    _need(isinstance(ids,list) and len(ids)==4 and len(set(ids))==4 and all(type(i) is int and 0<=i<count for i in ids)
        and type(p['periodicity']) is int and type(p['origin_id']) is int
        and all(type(p[k]) in (int,float) and math.isfinite(p[k]) for k in ['weight','angle_ideal']) and p['weight']>=0
        and (alt is None or isinstance(alt,list) and all(type(v) in (int,float) and math.isfinite(v) for v in alt)))
    return p


def select_torsions(expected,coordinate_cases,case_gradients):
    """Rank native rows by saved geometry and atom-gradient evidence, not names."""
    count=_points(coordinate_cases);_need(expected['atom_count']==count and set(case_gradients)==set(CASES))
    _need(all(len(g)==3*count and all(type(x) in (int,float) and math.isfinite(x) for x in g) for g in case_gradients.values()))
    details=expected['geometry']['proxy_details'];edges={tuple(sorted(r['i_seqs'])) for r in details['bond_simple']}
    rows=[]
    for kind in ['dihedral','const_dihedral']:
        for index,row in enumerate(details[kind] or []):
            p=_proxy(row,count);geometry={k:_geometry([points[i] for i in p['i_seqs']]) for k,points in coordinate_cases.items()}
            minimum=min(v['minimum_sine'] for v in geometry.values());score=max(_norm([g[3*i+j] for i in p['i_seqs'] for j in range(3)]) for g in case_gradients.values())
            rows.append({'kind':kind,'native_index':index,'proxy':p,'geometry':geometry,'minimum_sine':minimum,'atom_gradient_score':score,
                'bond_path_supported':all(tuple(sorted(pair)) in edges for pair in zip(p['i_seqs'],p['i_seqs'][1:])),
                'eligible':kind=='dihedral' and p['weight']>0,'near_collinear':minimum<=NEAR_SINE})
    key=lambda r:(_bytes(r['proxy']),r['kind'],r['native_index'])
    active=[r for r in rows if r['eligible']];near=sorted((r for r in active if r['near_collinear']),key=lambda r:(r['minimum_sine'],key(r)))
    chosen=[{**r,'selection_reason':'NEAR_COLLINEAR'} for r in near[:6]];covered={i for r in chosen for i in r['proxy']['i_seqs']}
    controls=sorted((r for r in active if not r['near_collinear'] and not covered.intersection(r['proxy']['i_seqs'])),key=lambda r:(-r['atom_gradient_score'],key(r)))
    for r in controls:
        if len([v for v in chosen if v['selection_reason']=='GRADIENT_CONTROL'])==2:break
        if not covered.intersection(r['proxy']['i_seqs']):chosen.append({**r,'selection_reason':'GRADIENT_CONTROL'});covered.update(r['proxy']['i_seqs'])
    _need(bool(chosen) and len(chosen)<=MAX_PROXIES)
    return {'schema_version':1,'policy_id':POLICY_ID,'near_collinear_sine_screen':NEAR_SINE,'maximum_selected':MAX_PROXIES,
        'maximum_near':6,'maximum_controls':2,'eligible':sorted(rows,key=key),'selected':chosen,'active_ordinary_count':len(active),
        'near_eligible_count':len(near),'truncated_near_count':max(0,len(near)-6),'excluded_count':sum(not r['eligible'] for r in rows),
        'positive_constant_count':sum(r['kind']=='const_dihedral' and r['proxy']['weight']>0 for r in rows),
        'selection_scope':'SAVED_GEOMETRY_AND_ATOM_GRADIENT; NO_COMPONENT_ALLOWLIST','full_torsion_qualification':False}


def audit_torsions(evaluate,groups,coordinate_cases,proxies,*,max_pairs=MAX_PAIRS,max_group_calls=MAX_GROUP_CALLS):
    """Record raw kernels and recomputable finite differences under fixed inputs."""
    count=_points(coordinate_cases);_need(1<=len(proxies)<=MAX_PROXIES and type(max_pairs) is int and 1<=max_pairs<=MAX_PAIRS
        and type(max_group_calls) is int and 1<=max_group_calls<=MAX_GROUP_CALLS)
    proxies=[_proxy(p,count) for p in proxies];_need(all(p['weight']>0 for p in proxies))
    result={'schema_version':1,'policy_id':POLICY_ID,'analysis_completed':False,'step_sizes':list(STEPS),
        'directional_tolerance':{'absolute':1e-4,'relative':1e-4},'evaluation_pairs':0,'max_evaluation_pairs':max_pairs,
        'group_calls':0,'max_group_calls':max_group_calls,'observations':[],'cases':{},'model_optimization':'NOT_RUN',
        'restraint_changes':'NONE','coordinate_model_written':False,'automatic_adoption':False,'endpoint_requalification':'NOT_RUN',
        'limitations':['Sampled fine-step agreement does not prove every derivative, conditioning, chemistry or convergence.',
            'All failed coarse samples and the original coordinate decision remain unchanged; no native bug or repaired endpoint is inferred.']}
    def invoke(kind,points,selector,gradients):
        field,limit=('evaluation_pairs',max_pairs) if kind=='local' else ('group_calls',max_group_calls)
        _need(result[field]<limit);result[field]+=1
        request={'kind':kind,'points_sha256':_hash(points),'selector':selector,'gradients':gradients}
        try:
            copied_points,copied_selector=deepcopy(points),deepcopy(selector)
            raw=(evaluate if kind=='local' else groups)(copied_points,copied_selector,gradients)
            if copied_points!=points or copied_selector!=selector:raise RuntimeError('Diagnostic callback mutated fixed inputs')
            if '_captured_exception' in raw:value=deepcopy(raw['_captured_exception'])
            else:
                targets=['single_target','accumulated_target'] if kind=='local' else ['target']
                _need(all(type(raw[k]) in (int,float) and math.isfinite(raw[k]) for k in targets))
                value={k:float(raw[k]) for k in targets}
                if kind=='local':
                    defined,angle=raw['native_angle_defined'],raw.get('native_angle_degrees')
                    _need(type(defined) is bool and (not defined or type(angle) in (int,float) and math.isfinite(angle)))
                    value.update(native_angle_defined=defined,native_angle_degrees=angle)
                if gradients:
                    keys=['single_gradient','accumulated_gradient'] if kind=='local' else ['gradient'];n=12 if kind=='local' else 3*count
                    for k in keys:
                        v=raw[k];_need(len(v)==n and all(type(x) in (int,float) and math.isfinite(x) for x in v));value[k]=[float(x) for x in v]
                value['status']='FINITE'
        except Exception as exc:value={'status':'EXCEPTION','exception_type':type(exc).__name__,'message':str(exc)}
        result['observations'].append({'request':request,'value':deepcopy(value)});return value
    def derivatives(points,selector,baseline,directions,kind):
        rows=[];kinds=['single','accumulated'] if kind=='local' else ['group']
        for name,vector in directions:
            analytical={k:math.fsum(a*b for a,b in zip(vector,baseline[k+'_gradient' if kind=='local' else 'gradient'])) for k in kinds};samples=[]
            for step in STEPS:
                shifted=lambda sign:[[v+sign*step*vector[3*i+j] for j,v in enumerate(p)] for i,p in enumerate(points)]
                plus,minus=invoke(kind,shifted(1),selector,False),invoke(kind,shifted(-1),selector,False);row={'step':step,'comparisons':{}}
                for k in kinds:
                    okay=plus['status']==minus['status']=='FINITE' and (kind!='local' or plus.get('native_angle_defined') is True and minus.get('native_angle_defined') is True)
                    if okay:
                        key=k+'_target' if kind=='local' else 'target';numerical=(plus[key]-minus[key])/(2*step);error=abs(numerical-analytical[k]);bound=1e-4+1e-4*max(abs(numerical),abs(analytical[k]))
                        row['comparisons'][k]={'numerical':numerical,'absolute_error':error,'bound':bound,'consistent':error<=bound}
                    else:row['comparisons'][k]={'consistent':False,'finding':'UNDEFINED_OR_NONFINITE_SAMPLE'}
                samples.append(row)
            agreement=lambda subset:{k:any(a['comparisons'][k]['consistent'] and b['comparisons'][k]['consistent'] for a,b in zip(subset,subset[1:])) for k in kinds}
            rows.append({'direction':name,'analytical':analytical,'samples':samples,'adjacent_step_agreement':agreement(samples),
                'coarse_adjacent_agreement':agreement(samples[:4]),'fine_adjacent_agreement':agreement(samples[4:])})
        return rows
    for label in CASES:
        points=coordinate_cases[label];local=[];selected_sum=[0.]*(3*count);selected_target=0.;local_finite=True
        for p in proxies:
            source=[points[i] for i in p['i_seqs']];orders={}
            for order,indices in [('forward',[0,1,2,3]),('reversed',[3,2,1,0])]:
                local_points=[source[i] for i in indices];b=invoke('local',local_points,p,True);repeat=invoke('local',local_points,p,True);directions=[]
                finite=b['status']=='FINITE';defined=finite and b.get('native_angle_defined') is True and _geometry(local_points)['geometry_defined']
                if defined:
                    directions=[('atom_'+str(i//3)+'_axis_'+str(i%3),[float(i==j) for j in range(12)]) for i in range(12)]
                    g=b['single_gradient'];length=_norm(g)
                    if length:directions.append(('local_gradient',[v/length for v in g]))
                    directions.append(('alternating_local',[(1. if i%2 else -1.)/math.sqrt(12) for i in range(12)]))
                rows=derivatives(local_points,p,b,directions,'local')
                orders[order]={'geometry':_geometry(local_points),'baseline':b,'repeat':repeat,'baseline_repeats_consistent':_same(b,repeat),
                    'single_and_container_agree':finite and _close(b['single_target'],b['accumulated_target']) and all(_close(x,y) for x,y in zip(b['single_gradient'],b['accumulated_gradient'])),
                    'directions':rows,'sampled_agreement':bool(rows) and all(all(r['adjacent_step_agreement'].values()) for r in rows)}
            forward,reverse=orders['forward']['baseline'],orders['reversed']['baseline'];finite=forward['status']==reverse['status']=='FINITE'
            reverse_vector=lambda values:[v for i in [9,6,3,0] for v in values[i:i+3]]
            agreement=finite and all(_close(forward[k+'_target'],reverse[k+'_target']) and all(_close(a,b) for a,b in zip(forward[k+'_gradient'],reverse_vector(reverse[k+'_gradient']))) for k in ['single','accumulated'])
            local.append({'proxy':p,'orders':orders,'reversed_order_consistent':agreement})
            if forward['status']=='FINITE':
                selected_target+=forward['single_target']
                for i,g in zip(p['i_seqs'],[forward['single_gradient'][j:j+3] for j in range(0,12,3)]):
                    for j,v in enumerate(g):selected_sum[3*i+j]+=v
            else:local_finite=False
        baselines={k:invoke('group',points,k,True) for k in ['full','selected','remainder','family']};repeats={k:invoke('group',points,k,True) for k in baselines};group_rows={}
        all_finite=all(v['status']=='FINITE' for v in baselines.values());vectors=[]
        if all_finite:
            for group in ['full','selected','remainder']:
                g=baselines[group]['gradient'];length=_norm(g)
                if length:vectors.append((group+'_gradient',[v/length for v in g]))
            vectors.append(('alternating_global',[(1. if i%2 else -1.)/math.sqrt(3*count) for i in range(3*count)]))
        for group in ['full','selected','remainder']:group_rows[group]={'directions':derivatives(points,group,baselines[group],vectors,'group')}
        def agrees(a,b):return a['status']==b['status']=='FINITE' and _close(a['target'],b['target']) and all(_close(x,y) for x,y in zip(a['gradient'],b['gradient']))
        attribution={'full_matches_native_family':agrees(baselines['full'],baselines['family']),
            'selected_matches_individual_sum':local_finite and all_finite and _close(selected_target,baselines['selected']['target']) and all(_close(a,b) for a,b in zip(selected_sum,baselines['selected']['gradient'])),
            'selected_plus_remainder':all_finite and _close(baselines['full']['target'],baselines['selected']['target']+baselines['remainder']['target'])
                and all(_close(a,b+c) for a,b,c in zip(baselines['full']['gradient'],baselines['selected']['gradient'],baselines['remainder']['gradient'])),
            'baseline_repeats_consistent':all(agrees(v,repeats[k]) for k,v in baselines.items())}
        result['cases'][label]={'proxies':local,'groups':group_rows,'group_baselines':baselines,'group_repeats':repeats,'attribution':attribution,
            'summary':{'selected_proxy_count':len(proxies),'local_sampled_agreement':all(r['reversed_order_consistent'] and all(o['sampled_agreement'] and o['baseline_repeats_consistent'] and o['single_and_container_agree'] for o in r['orders'].values()) for r in local),
                'group_attribution_consistent':all(attribution.values()),'group_sampled_agreement':bool(vectors) and all(all(v['adjacent_step_agreement'].values()) for r in group_rows.values() for v in r['directions']),
                'local_fine_only_directions':sum(not all(v['coarse_adjacent_agreement'].values()) and all(v['fine_adjacent_agreement'].values()) for r in local for o in r['orders'].values() for v in o['directions']),
                'local_coarse_review_directions':sum(not all(v['coarse_adjacent_agreement'].values()) for r in local for o in r['orders'].values() for v in o['directions']),
                'local_fine_review_directions':sum(not all(v['fine_adjacent_agreement'].values()) for r in local for o in r['orders'].values() for v in o['directions']),
                'group_fine_only_directions':sum(not all(v['coarse_adjacent_agreement'].values()) and all(v['fine_adjacent_agreement'].values()) for r in group_rows.values() for v in r['directions'])}}
    result['analysis_completed']=True
    result['summary']={'selected_proxy_count':len(proxies),'cases':{k:v['summary'] for k,v in result['cases'].items()},'endpoint_requalification':'NOT_RUN'}
    return result


def replay_torsions(result,coordinate_cases,proxies):
    """Replay every request, index/order, step and arithmetic without native code."""
    stream=deque(deepcopy(result['observations']))
    def callback(kind):
        def evaluate(points,selector,gradients):
            _need(bool(stream));row=stream.popleft();_need(row['request']=={'kind':kind,'points_sha256':_hash(points),'selector':selector,'gradients':gradients})
            value=row['value'];return deepcopy(value) if value['status']=='FINITE' else {'_captured_exception':deepcopy(value)}
        return evaluate
    replay=audit_torsions(callback('local'),callback('group'),coordinate_cases,proxies,max_pairs=MAX_PAIRS,max_group_calls=MAX_GROUP_CALLS)
    _need(not stream and _same(result,replay));return {'status':'MIXED_TORSION_AUDIT_COMPLETE','summary':replay['summary'],'endpoint_requalification':'NOT_RUN','automatic_adoption':False}


def _manager_digest(native):
    return _hash({k:native[k] for k in ['atoms','atom_count','monomer_mappings','geometry','installed_api_sources','restraint_policy']})


_WORKER=r'''from pathlib import Path
import hashlib,importlib,json,sys,traceback
from mixed_torsion_core import POLICY_ID,audit_torsions,_manager_digest,_dump,_same,_proxy,_need
from conditioning_core import native_evaluator
from correction_core import evaluate_fixed_native
from gradient_core import fixed_signature
spec=json.loads(Path('torsion_spec.json').read_bytes())
result={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','analysis_completed':False}
try:
    sys.argv=['native_worker.py','native_spec.json'];namespace={'__name__':'__main__','__file__':'native_worker.py'}
    try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
    except SystemExit as exc:
        if exc.code!=0:raise RuntimeError('Fresh native bootstrap failed')
    expected=json.loads(Path('expected_inventory.json').read_bytes());native=namespace['report'];_dump(Path('native_validation.json'),native)
    _need(_manager_digest(native)==spec['expected_manager_sha256']==_manager_digest(expected))
    _need(_same(native['energy_inventory'],expected['energy_inventory']))
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    geo,sites=namespace['geo'],namespace['sites'];original=[list(p) for p in sites]
    _need(not geo.site_symmetry_table.special_position_indices())
    def fingerprints(names):
        modules=[importlib.import_module(n) for n in names]
        return [{'module':m.__name__,'historical_path':str(Path(m.__file__).resolve()),'sha256':hashlib.sha256(Path(m.__file__).resolve().read_bytes()).hexdigest()} for m in modules]
    sources=fingerprints([r['module'] for r in spec['expected_sources']])
    _need([(r['module'],r['sha256']) for r in sources]==[(r['module'],r['sha256']) for r in spec['expected_sources']])
    signature=fixed_signature(geo,sites);_need(signature==spec['expected_constraint_signature'])
    source_dir=Path(importlib.import_module('cctbx.geometry_restraints.manager').__file__).resolve().parent;cpp=[]
    for name in ['dihedral.h','dihedral_bpl.cpp']:
        path=source_dir/name;row={'path':name,'status':'UNAVAILABLE'}
        if path.is_file():
            data=path.read_bytes();out=Path('installed_source')/name;out.parent.mkdir(exist_ok=True);out.write_bytes(data)
            row.update(status='RECORDED',sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
        cpp.append(row)
    selected=[];native_parameters=[];all_proxies=list(geo.dihedral_proxies or [])
    for row in spec['selection']['selected']:
        p=all_proxies[row['native_index']];raw={k:list(p.i_seqs) if k=='i_seqs' else getattr(p,k,None) for k in ['i_seqs','angle_ideal','weight','periodicity','alt_angle_ideals','origin_id']}
        if raw['alt_angle_ideals'] is not None:raw['alt_angle_ideals']=list(raw['alt_angle_ideals'])
        _need(_proxy(raw,len(sites))==row['proxy'])
        _need((p.sym_ops is None or not len(p.sym_ops)) and p.limit==-1 and p.top_out is False and p.slack==0)
        selected.append(p);native_parameters.append({**row['proxy'],'limit':float(p.limit),'slack':float(p.slack),'top_out':bool(p.top_out),'symmetry':'NONE'})
    chosen={r['native_index'] for r in spec['selection']['selected']};remainder=[p for i,p in enumerate(all_proxies) if i not in chosen]
    def shared(values):
        out=gr.shared_dihedral_proxy()
        for p in values:out.append(p)
        return out
    containers={k:shared(v) for k,v in [('full',all_proxies),('selected',selected),('remainder',remainder)]}
    local=native_evaluator(gr,flex)
    def evaluate(points,proxy,gradients):return local(points,proxy)
    def groups(points,group,gradients):
        if group=='family':
            active=flags.flags(default=False);active.dihedral=True
            raw=evaluate_fixed_native(geo,points,active,gr,flex,plane_order_safe=True)
            return {'target':raw['target'],'gradient':raw['gradient']}
        buffer=flex.vec3_double(len(points),(0.,0.,0.));target=gr.dihedral_residual_sum(sites_cart=flex.vec3_double(points),proxies=containers[group],gradient_array=buffer)
        return {'target':float(target),'gradient':[float(v) for v in buffer.as_double()]}
    audit=audit_torsions(evaluate,groups,spec['coordinate_cases'],[r['proxy'] for r in spec['selection']['selected']])
    for label,row in audit['cases'].items():
        baseline=row['group_baselines']['family'];reference=spec['case_references'][label]
        row['saved_family_match']=baseline['status']=='FINITE' and _same(baseline['target'],reference['target']) and _same(baseline['gradient'],reference['gradient'])
    after=fixed_signature(geo,sites);_need(after==signature and [list(p) for p in sites]==original)
    sources_after=fingerprints([r['module'] for r in spec['expected_sources']]);_need(sources_after==sources)
    for r in cpp:
        if r['status']=='RECORDED':_need(hashlib.sha256((source_dir/r['path']).read_bytes()).hexdigest()==r['sha256'])
    result.update(status='REVIEW',audit=audit,captured_inventory_matches=True,manager_sha256=_manager_digest(native),
        constraint_signature_before=signature,constraint_signature_after=after,initial_coordinates_unchanged=True,
        installed_sources=sources,installed_sources_after=sources_after,installed_dihedral_sources=cpp,selected_native_parameters=native_parameters,
        positive_constant_count=spec['selection']['positive_constant_count'],analysis_completed=True,
        model_optimization='NOT_RUN',restraint_changes='NONE',automatic_adoption=False,endpoint_requalification='NOT_RUN')
except Exception as exc:
    result.update(error=type(exc).__name__+': '+str(exc));traceback.print_exc()
_dump(Path('torsion_result.json'),result)
sys.exit(0 if result['status']=='REVIEW' else 2)
'''


def _ref(path,root,anchor=ANCHOR):
    from .cif_mixed_geometry import _ref as reference
    return reference(path,root,anchor)

def _resolve(root,geometry,gradient,context,parent,ref):
    from .cif_mixed_recovery import _safe
    anchors={ANCHOR:Path(root),'geometry_directory':Path(geometry),'gradient_directory':Path(gradient),'context_directory':Path(context),'linked_parent_directory':Path(parent)}
    _need(isinstance(ref,dict) and ref.get('anchor') in anchors and _safe(ref.get('path')))
    directory=anchors[ref['anchor']];path=directory/ref['path'];_need(_ref(path,directory,ref['anchor'])==ref);return path


def _inputs(geometry,gradient,context,parent,parent_archive_sha256):
    from .cif_mixed_geometry import read_mixed_geometry_trial,REPORT as GEOMETRY_REPORT,_completed_result
    from .cif_mixed_gradient import _inputs as native_inputs
    report=_load(geometry/GEOMETRY_REPORT)
    source=read_mixed_geometry_trial(geometry,gradient_directory=gradient,context_directory=context,linked_parent_directory=parent,parent_archive_sha256=report['parent_archive_sha256'])
    _need(_digest(parent_archive_sha256) and source['execution']['status']=='COMPLETED' and source['new_native_calls']>=1)
    _,model,cifs,phils,expected,bindings=native_inputs(context,parent)
    result=_completed_result(geometry,expected);proof=_load(gradient/'job/gradient_result.json');count=expected['atom_count']
    final=result['final_sites_cart'];cases={'initial':expected['geometry']['sites_cart_exact'],'full_precision':final,
        'pdb_rounded':[[float('%.3f'%v) for v in p] for p in final]};_need(_points(cases)==count)
    references={'initial':proof['gradient_audit']['cases']['initial']['families']['dihedral']['baseline'],
        **{k:result['endpoint_gradient_audit']['cases'][k]['families']['dihedral']['baseline'] for k in ['full_precision','pdb_rounded']}}
    _need(result['constraint_signature_before']==result['constraint_signature_after']==proof['constraint_signature_before']
        and result['installed_optimizer_sources']==proof['installed_numeric_sources'] and result['installed_adapter_sources']==proof['installed_adapter_sources'])
    plan=select_torsions(expected,cases,{k:v['gradient'] for k,v in references.items()})
    bindings={**bindings,'geometry_report':_ref(geometry/GEOMETRY_REPORT,geometry,'geometry_directory'),
        'geometry_result':_ref(geometry/'job/geometry_result.json',geometry,'geometry_directory'),
        'expected_inventory':_ref(geometry/'job/expected_inventory.json',geometry,'geometry_directory'),
        'initial_result':_ref(gradient/'job/gradient_result.json',gradient,'gradient_directory')}
    return source,model,cifs,phils,expected,proof,cases,references,plan,bindings


_CORES={'mixed_torsion_core.py':'cif_mixed_torsion.py','conditioning_core.py':'cif_dihedral_conditioning.py',
    'correction_core.py':'cif_parallelity_correction.py','gradient_core.py':'cif_gradient_audit.py'}


def _prepare(root,model,cifs,phils,expected,proof,cases,references,plan):
    from .cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID
    from .cif_candidate_usability import native_energy_worker
    work=root/'job';(work/'inputs').mkdir(parents=True);inputs=[]
    for i,path in enumerate([model,*cifs,*phils]):
        role='model' if i==0 else 'dictionary' if i<=len(cifs) else 'phil';out=work/'inputs'/f'{i:03d}_{role}{path.suffix}'
        out.write_bytes(path.read_bytes());inputs.append({'input_index':i,'role':role,'artifact':_ref(out,root)})
    native={'policy_id':NATIVE_POLICY_ID,'model':inputs[0]['artifact']['path'].removeprefix('job/'),
        'dictionaries':[r['artifact']['path'].removeprefix('job/') for r in inputs if r['role']=='dictionary'],
        'phil_files':[r['artifact']['path'].removeprefix('job/') for r in inputs if r['role']=='phil'],
        'phil_namespace_policy':'refinement-root-to-interpreter-v1','inventory_detail':'linked','policy_inventory':True,'energy_inventory':True}
    spec={'schema_version':1,'policy_id':POLICY_ID,'expected_manager_sha256':_manager_digest(expected),
        'expected_constraint_signature':proof['constraint_signature_before'],'coordinate_cases':cases,'case_references':{k:{'target':v['target'],'gradient':v['gradient']} for k,v in references.items()},
        'selection':plan,'expected_sources':proof['installed_numeric_sources']+proof['installed_adapter_sources'],
        'max_evaluation_pairs':MAX_PAIRS,'max_group_calls':MAX_GROUP_CALLS}
    for name,value in [('native_spec.json',native),('torsion_spec.json',spec),('expected_inventory.json',expected)]:_dump(work/name,value)
    _dump(root/'torsion_selection.json',plan);(work/'native_worker.py').write_text(native_energy_worker(_NATIVE_WORKER));(work/'torsion_worker.py').write_text(_WORKER)
    for name,source in _CORES.items():(work/name).write_bytes(Path(__file__).with_name(source).read_bytes())
    return {'inputs':inputs,'worker':_ref(work/'torsion_worker.py',root),'spec':_ref(work/'torsion_spec.json',root),'selection':_ref(root/'torsion_selection.json',root),
        'selected_proxy_count':len(plan['selected']),'cores':{name:_ref(work/name,root) for name in _CORES}}


def _validate_result(root,result,expected,proof,cases,references,plan):
    r=result;_need(type(r['schema_version']) is int and r['schema_version']==1 and r['policy_id']==POLICY_ID and r['status']=='REVIEW' and r['analysis_completed'] is True
        and r['captured_inventory_matches'] is True and r['manager_sha256']==_manager_digest(expected)
        and r['constraint_signature_before']==r['constraint_signature_after']==proof['constraint_signature_before']
        and r['initial_coordinates_unchanged'] is True and r['model_optimization']=='NOT_RUN' and r['restraint_changes']=='NONE'
        and r['automatic_adoption'] is False and r['endpoint_requalification']=='NOT_RUN' and r['positive_constant_count']==plan['positive_constant_count'])
    native=_load(root/'job/native_validation.json');_need(_manager_digest(native)==_manager_digest(expected) and _same(native['energy_inventory'],expected['energy_inventory']))
    pins=proof['installed_numeric_sources']+proof['installed_adapter_sources'];sources=r['installed_sources']
    _need([(x['module'],x['sha256']) for x in sources]==[(x['module'],x['sha256']) for x in pins] and sources==r['installed_sources_after'])
    parameters=[{**row['proxy'],'limit':-1.,'slack':0.,'top_out':False,'symmetry':'NONE'} for row in plan['selected']];_need(r['selected_native_parameters']==parameters)
    cpp=r['installed_dihedral_sources'];_need([x['path'] for x in cpp]==['dihedral.h','dihedral_bpl.cpp'])
    for row in cpp:
        if row['status']=='RECORDED':
            data=(root/'job/installed_source'/row['path']).read_bytes();_need(len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256'])
        else:_need(row=={'path':row['path'],'status':'UNAVAILABLE'})
    audit=deepcopy(r['audit']);matches={}
    for label,row in audit['cases'].items():
        match=row.pop('saved_family_match');baseline=row['group_baselines']['family'];reference=references[label]
        actual=baseline['status']=='FINITE' and _same(baseline['target'],reference['target']) and _same(baseline['gradient'],reference['gradient'])
        _need(type(match) is bool and match==actual);matches[label]=actual
    replay=replay_torsions(audit,cases,[row['proxy'] for row in plan['selected']])
    summary={**replay['summary'],'saved_family_matches':matches,'positive_constant_count':plan['positive_constant_count'],
        'full_native_family_coverage':'UNSUPPORTED_POSITIVE_CONSTANT_TORSIONS' if plan['positive_constant_count'] else 'CHECKED_BY_INDEPENDENT_GROUP_COMPARISON'}
    return {'status':'MIXED_TORSION_AUDIT_COMPLETE','summary':summary,'endpoint_requalification':'NOT_RUN','automatic_adoption':False}


def _analysis(root,report,expected,proof,cases,references,plan):
    if report['execution']['status']!='COMPLETED':return {'status':'NOT_RUN'}
    try:return _validate_result(root,_load(root/'job/torsion_result.json'),expected,proof,cases,references,plan)
    except (OSError,ValueError,KeyError,TypeError,IndexError,ZeroDivisionError,OverflowError) as exc:
        return {'status':'REVIEW','finding_type':type(exc).__name__,'finding':'OPTIONAL_TORSION_EVIDENCE_INCOMPLETE','endpoint_requalification':'NOT_RUN'}


def _publish(root,geometry,gradient,context,parent,report):
    _need(not any(p.is_symlink() for p in root.rglob('*')))
    report['outputs']=[_ref(p,root) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/REPORT and p.suffix not in {'.pkl','.pickle','.pyc'}]
    _dump(root/REPORT,report);read_mixed_torsions(root,geometry_directory=geometry,gradient_directory=gradient,context_directory=context,linked_parent_directory=parent,parent_archive_sha256=report['parent_archive_sha256']);return report


def audit_mixed_torsions(geometry_directory,gradient_directory,context_directory,linked_parent_directory,phenix,output,*,parent_archive_sha256,timeout_seconds=120):
    from .cif_native_validation import _stop
    if type(timeout_seconds) is not int or not 1<=timeout_seconds<=600:raise ValueError('Require a native deadline from 1 to 600 seconds')
    _need(_digest(parent_archive_sha256));geometry,gradient,context,parent=map(Path,(geometry_directory,gradient_directory,context_directory,linked_parent_directory));root=Path(output).absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents]) and not any(root.resolve().is_relative_to(p.resolve()) for p in [geometry,gradient,context,parent]))
    source,model,cifs,phils,expected,proof,cases,references,plan,bindings=_inputs(geometry,gradient,context,parent,parent_archive_sha256);root.mkdir(parents=True)
    prep=_prepare(root,model,cifs,phils,expected,proof,cases,references,plan)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','inputs':bindings,'preparation':prep,'parent_archive_sha256':parent_archive_sha256,
        'parent_archive_verification':'CALLER_VERIFIED_EXACT_C90_CAPSULE_BYTES; SCIENCE_BOUND_BY_MAINTAINED_PARENT_READERS',
        'maximum_native_calls':1,'new_native_calls':0,'timeout_seconds':timeout_seconds,'maximum_evaluation_pairs':MAX_PAIRS,'maximum_group_calls':MAX_GROUP_CALLS,
        'execution':{'status':'NOT_RUN'},'qualification':{'status':'NOT_RUN'},'coordinate_decision':deepcopy(source['coordinate_decision']),
        'original_geometry_status':source['status'],'original_geometry_qualification':deepcopy(source['qualification']),
        'model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','readyset_execution':'NOT_RUN','coot_execution':'NOT_RUN','refinement':'NOT_RUN',
        'cache_writes':'NOT_RUN','captured_code_execution':'NOT_RUN','endpoint_requalification':'NOT_RUN','scientific_qualification':'NOT_ASSESSED',
        'automatic_adoption':False,'requires_cif_review':False,'policy_authority':'NARestraints','source_chemical_findings':'PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_DIAGNOSTIC'}
    if phenix is not None:
        executable=Path(phenix.executables['phenix.python']).resolve(strict=True);fingerprint=sha256(executable.read_bytes()).hexdigest()
        report.update(status='REVIEW',phenix_version=phenix.version,executable_provenance=str(executable),executable_sha256=fingerprint);started=time.monotonic()
        try:
            with (root/'job/torsion.log').open('xb') as log:
                process=subprocess.Popen([str(executable),'-B','torsion_worker.py'],cwd=root/'job',env=dict(phenix.environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                report['new_native_calls']=1
                try:code=process.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:_stop(process);report['execution']={'status':'TIMED_OUT','returncode':process.returncode}
                except BaseException as exc:
                    _stop(process);report['execution']={'status':'WAIT_FAILED','returncode':process.returncode,'error_type':type(exc).__name__};raise
                else:report['execution']={'status':'COMPLETED' if code==0 else 'FAILED','returncode':code}
        except (OSError,ValueError,KeyError,TypeError,IndexError,OverflowError) as exc:
            report['optional_finding']=type(exc).__name__+': '+str(exc)
            if report['new_native_calls']==0:report['execution']={'status':'LAUNCH_FAILED','error':report['optional_finding']}
        report['execution']['elapsed_seconds']=round(time.monotonic()-started,6);_need(sha256(executable.read_bytes()).hexdigest()==fingerprint)
        report['qualification']=_analysis(root,report,expected,proof,cases,references,plan)
        if report['qualification']['status']=='MIXED_TORSION_AUDIT_COMPLETE':report['status']='MIXED_TORSION_AUDIT_COMPLETE';report['summary']=report['qualification']['summary']
    return _publish(root,geometry,gradient,context,parent,report)


def _read_mixed_torsions(directory,*,geometry_directory,gradient_directory,context_directory,linked_parent_directory,parent_archive_sha256):
    root,geometry,gradient,context,parent=map(Path,(directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory));report=_load(root/REPORT)
    _need(_digest(parent_archive_sha256) and report['parent_archive_sha256']==parent_archive_sha256 and report['schema_version']==1 and report['policy_id']==POLICY_ID
        and report['status'] in {'PREPARED_ONLY','REVIEW','MIXED_TORSION_AUDIT_COMPLETE'} and type(report['schema_version']) is int
        and type(report['maximum_native_calls']) is int and report['maximum_native_calls']==1
        and type(report['new_native_calls']) is int and report['new_native_calls'] in [0,1] and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=600
        and report['maximum_evaluation_pairs']==MAX_PAIRS and report['maximum_group_calls']==MAX_GROUP_CALLS
        and report['automatic_adoption'] is False and report['requires_cif_review'] is False and report['policy_authority']=='NARestraints'
        and report['parent_archive_verification']=='CALLER_VERIFIED_EXACT_C90_CAPSULE_BYTES; SCIENCE_BOUND_BY_MAINTAINED_PARENT_READERS'
        and report['source_chemical_findings']=='PRESERVED_IN_BOUND_CONTEXT; NOT_PROMOTED_BY_DIAGNOSTIC'
        and report['scientific_qualification']=='NOT_ASSESSED' and all(report[k]=='NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset_execution','coot_execution','refinement','cache_writes','captured_code_execution','endpoint_requalification']))
    refs=report['outputs'];_need(len(refs)==len({r['path'] for r in refs}) and all(r['anchor']==ANCHOR for r in refs))
    for ref in refs:_resolve(root,geometry,gradient,context,parent,ref)
    actual=set()
    for p in root.rglob('*'):
        _need(not p.is_symlink())
        if p.is_file() and p!=root/REPORT and p.suffix not in {'.pkl','.pickle','.pyc'}:actual.add(p.relative_to(root).as_posix())
    _need(actual=={r['path'] for r in refs})
    source,model,cifs,phils,expected,proof,cases,references,plan,bindings=_inputs(geometry,gradient,context,parent,parent_archive_sha256)
    _need(report['inputs']==bindings and report['coordinate_decision']==source['coordinate_decision'] and report['original_geometry_status']==source['status'] and report['original_geometry_qualification']==source['qualification'])
    with tempfile.TemporaryDirectory(prefix='mixed-torsion-reader-') as temporary:
        replay=Path(temporary).resolve();prep=_prepare(replay,model,cifs,phils,expected,proof,cases,references,plan);_need(prep==report['preparation'])
        for p in replay.rglob('*'):
            if p.is_file():_need((root/p.relative_to(replay)).read_bytes()==p.read_bytes())
    execution=report['execution'];state=execution['status']
    if report['new_native_calls']==0:
        _need((report['status']=='PREPARED_ONLY' and execution=={'status':'NOT_RUN'}) or (report['status']=='REVIEW' and state=='LAUNCH_FAILED' and isinstance(execution['error'],str)))
    else:
        _need(report['status']!='PREPARED_ONLY' and state in {'COMPLETED','FAILED','TIMED_OUT','WAIT_FAILED'} and type(execution['returncode']) is int
            and (state!='COMPLETED' or execution['returncode']==0) and (state!='FAILED' or execution['returncode']!=0)
            and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds']) and execution['elapsed_seconds']>=0
            and _digest(report['executable_sha256']) and isinstance(report['phenix_version'],str) and report['phenix_version'])
    q=_analysis(root,report,expected,proof,cases,references,plan)
    _need(report['qualification']==q and report.get('summary')==q.get('summary') and (report['status']=='MIXED_TORSION_AUDIT_COMPLETE') is (q['status']=='MIXED_TORSION_AUDIT_COMPLETE'))
    return report


def read_mixed_torsions(directory,*,geometry_directory,gradient_directory,context_directory,linked_parent_directory,parent_archive_sha256):
    """Reproduce the audit and preserve the prior decision without a native job."""
    try:return _read_mixed_torsions(directory,geometry_directory=geometry_directory,gradient_directory=gradient_directory,
        context_directory=context_directory,linked_parent_directory=linked_parent_directory,parent_archive_sha256=parent_archive_sha256)
    except (KeyError,TypeError,IndexError,OverflowError) as exc:raise ValueError('Incomplete mixed torsion report') from exc
