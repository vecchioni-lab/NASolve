"""Derivative-evidence preconditions for an explicit corrected geometry trial."""
from __future__ import annotations
import math
from copy import deepcopy

POLICY_ID='cif-fixed-na-corrected-geometry-trial-v1'
CONTINUATION_POLICY_ID='cif-fixed-na-corrected-geometry-continuation-v1'
CORRECTION_ID='native-parallelity-both-first-planes-v1'
AUDIT_ID='cif-fixed-native-plane-order-gradient-audit-v1'
FAMILIES=('all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded')
CASES={'initial','full_precision','pdb_rounded'}
STEPS=[1e-3,1e-4,1e-5,1e-6]
REPLACEMENT_AUDIT_ID='cif-replacement-manager-gradient-qualification-v1'
QUALIFIED_CORRECTION_SHA256='701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f'
NUMERIC_MODULES=('scitbx.lbfgs','cctbx.geometry_restraints.flags','cctbx.geometry_restraints.manager',
    'cctbx.geometry_restraints.energies','scitbx_lbfgs_ext','cctbx_geometry_restraints_ext')
ADAPTER_MODULES=('cctbx.geometry_restraints','cctbx.array_family.flex')


def _need(value):
    if not value:raise ValueError('Require complete qualified native gradient evidence')


def _close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _norm(values):return math.sqrt(math.fsum(v*v for v in values))
def _finite(values,count):
    _need(len(values)==count and all(type(v) in (int,float) and math.isfinite(v) for v in values))


def _directions(rows,vectors,baselines,kind=None):
    _need(len(rows)==len(vectors) and {r['direction'] for r in rows}==set(vectors))
    for row in rows:
        analytical=math.fsum(a*b for a,b in zip(vectors[row['direction']],baselines))
        recorded=row['analytical'] if kind is None else row['analytical'][kind]
        _need(_close(analytical,recorded) and [s['step'] for s in row['samples']]==STEPS)
        passes=[]
        for sample in row['samples']:
            s=sample if kind is None else sample[kind]
            _finite([s['plus_target'],s['minus_target'],s['numerical'],s['absolute_error'],s['bound']],5)
            numerical=(s['plus_target']-s['minus_target'])/(2*sample['step'])
            error=abs(numerical-analytical);bound=1e-4+1e-4*max(abs(numerical),abs(analytical));okay=error<=bound
            _need(_close(numerical,s['numerical']) and _close(error,s['absolute_error']) and _close(bound,s['bound']) and s['consistent'] is okay)
            passes.append(okay)
        _need(any(passes[i] and passes[i+1] for i in range(3)))
        _need(row['status']=='CONSISTENT' if kind is None else row[kind+'_consistent'] is True)


def _sampled_cases(q,atom_count,cases):
    _need(set(q['cases'])==cases and q['step_sizes']==STEPS and q['directional_tolerance']=={'absolute':1e-4,'relative':1e-4})
    selected=q['selected_indices'];_need(1<=len(selected)<=6 and len(set(selected))==len(selected)
        and all(type(i) is int and 0<=i<atom_count for i in selected))
    for case in q['cases'].values():
        _need(case['sampled_gradients_consistent'] and case['baseline_repeats_consistent'] and case['captured_snapshot_match']['consistent'])
        _need(case['target_additivity']['consistent'] and case['gradient_additivity']['consistent'] and set(case['families'])==set(FAMILIES))
        full=case['families']['all']['baseline'];_finite(full['gradient'],3*atom_count);common={}
        length=_norm(full['gradient'])
        if length:common['full_gradient']=[g/length for g in full['gradient']]
        v=[1. if i%2 else -1. for i in range(3*atom_count)];length=_norm(v);common['alternating_global']=[g/length for g in v]
        for index in selected:
            for axis in range(3):
                v=[0.]*(3*atom_count);v[3*index+axis]=1.;common[f'atom_{index}_axis_{axis}']=v
        for family in case['families'].values():
            baseline=family['baseline'];g=baseline['gradient'];_finite(g,3*atom_count)
            _need(family['sampled_directions_consistent'] and family['repeat_consistent'] and _close(_norm(g),baseline['gradient_norm']))
            vectors=dict(common)
            length=_norm(g)
            if length:vectors['family_gradient']=[v/length for v in g]
            _directions(family['directions'],vectors,g)


def validate_gradient_qualification(result,atom_count):
    """Recompute sampled proof before allowing any optimizer invocation."""
    if isinstance(result,dict) and result.get('policy_id')==REPLACEMENT_AUDIT_ID:
        return validate_replacement_gradient_qualification(result,atom_count)
    try:
        q=result
        _need(q['policy_id']==AUDIT_ID and q['correction_policy_id']==CORRECTION_ID and q['plane_order_safe'] is True)
        _need(q['correction_qualification']=='SAMPLED_NATIVE_DERIVATIVES_PASS' and q['analysis_completed'] is True
              and q['captured_inventory_matches'] is True and q['normalization'] is False
              and q['model_optimization']=='NOT_RUN' and q['automatic_adoption'] is False)
        _need(q['constraint_signature_before']==q['constraint_signature_after'] and len(q['constraint_signature_before'])==64)
        _sampled_cases(q,atom_count,CASES)
        plane=q['plane_order_audit'];_need(plane['analysis_completed'] and plane['order_safe_qualified'] and set(plane['cases'])==CASES)
        _need(plane['step_sizes']==STEPS and len(plane['toy_cases'])==6 and len(plane['rotation_controls'])==3)
        for case in [*plane['cases'].values(),{'proxies':plane['toy_cases'],'summary':plane['toy_summary']}]:
            rows=case['proxies'];_need(bool(rows))
            summary=case['summary'];_need(all(summary[k] for k in ['order_safe_derivatives_consistent','baseline_repeats_consistent','swapped_energies_consistent','order_safe_swapped_gradients_consistent']))
            _need(summary['proxy_count']==len(rows) and summary['orders']==2*len(rows))
            for row in rows:
                _need(row['swapped_energies_consistent'] and row['order_safe_swapped_gradients_consistent'])
                mapping={index:i for i,index in enumerate(row['global_indices'])}
                for order in ['original','swapped']:
                    data=row[order];g=data['baseline']['order_safe_gradient'];_finite(g,3*len(mapping));vectors={}
                    _need(data['order_safe_derivatives_consistent'] and data['baseline_repeat_consistent'])
                    for name,key in [('i_plane','i_seqs' if order=='original' else 'j_seqs'),('j_plane','j_seqs' if order=='original' else 'i_seqs')]:
                        selected={mapping[i] for i in row['proxy'][key]};v=[value if i//3 in selected else 0. for i,value in enumerate(g)]
                        if not _norm(v):v=[(1. if i%2 else -1.) if i//3 in selected else 0. for i in range(len(g))]
                        length=_norm(v);vectors[name]=[value/length for value in v]
                    v=[1. if i%2 else -1. for i in range(len(g))];length=_norm(v);vectors['alternating_local']=[value/length for value in v]
                    _directions(data['directions'],vectors,g,'order_safe')
        _need(all(row['rotation_energy_consistent'] and row['rotation_gradient_consistent'] for row in plane['rotation_controls']))
        return True
    except (KeyError,TypeError,OverflowError,ZeroDivisionError) as exc:
        raise ValueError('Require complete qualified native gradient evidence') from exc


def replacement_manager_view(native):
    """Keep named plane membership, policy and APIs; covalent targets may differ."""
    return deepcopy({'atom_count':native['atom_count'],
        'atoms':[{k:a[k] for k in ['i_seq','atom_id','label','element','identity']} for a in native['atoms']],
        'planarity':native['geometry']['proxy_details']['planarity'],
        'parallelity':native['geometry']['proxy_details']['parallelity'],
        'restraint_policy':native['restraint_policy'],'installed_api_sources':native['installed_api_sources']})


def _plane_projection(rows):
    keys=('i_seqs','j_seqs','weight','target_angle_deg','slack','top_out','origin_id')
    return [{k:r[k] for k in keys} for r in rows]


def validate_replacement_manager_bridge(bridge,parent,atom_count):
    """Require the exact already qualified plane inventory and named index basis."""
    try:
        _need(parent['policy_id']==AUDIT_ID)
        validate_gradient_qualification(parent,atom_count)
        old,new=bridge['previous'],bridge['replacement'];_need(old==new)
        _need(old['atom_count']==atom_count and len(old['atoms'])==atom_count
            and [a['i_seq'] for a in old['atoms']]==list(range(atom_count)))
        labels=[a['label'] for a in old['atoms']];_need(len(set(labels))==atom_count)
        keys=[(a['identity']['model_id'],a['identity']['chain_id'],a['identity']['resseq'],
            a['identity']['icode'],a['identity']['altloc'],a['atom_id']) for a in old['atoms']]
        _need(len(set(keys))==atom_count and bool(old['installed_api_sources']))
        policy=old['restraint_policy'];ids=policy['origin_ids']
        names={'hydrogen bonds','edits','basepair stacking','basepair parallelity','basepair planarity'}
        _need(policy['secondary_structure_enabled'] is False and set(ids)==names
            and all(type(i) is int for i in ids.values()) and len(set(ids.values()))==len(names))
        competing={i for k,i in ids.items() if k!='edits'}
        for kind in ['planarity','parallelity']:
            _need(isinstance(old[kind],list))
            for row in old[kind]:
                _need(row.get('origin_id') not in competing)
                for field,names_field in [('i_seqs','atoms'),*([('j_seqs','j_atoms')] if kind=='parallelity' else [])]:
                    indices=row[field];_need(len(indices)>=3 and len(indices)==len(set(indices))
                        and all(type(i) is int and 0<=i<atom_count for i in indices)
                        and row[names_field]==[labels[i] for i in indices])
        _need(bool(old['parallelity']) and _plane_projection(old['parallelity'])==_plane_projection(parent['native_parallelity_proxies']))
        _need(all(_plane_projection([r['proxy'] for r in case['proxies']])==_plane_projection(parent['native_parallelity_proxies'])
            for case in parent['plane_order_audit']['cases'].values()))
        return True
    except (KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError) as exc:
        raise ValueError('Require unchanged qualified plane membership and native index basis') from exc


def validate_replacement_gradient_qualification(result,atom_count):
    """Qualify a new fixed covalent objective without recycling the old target."""
    try:
        q=result;parent=q['parent_qualification']
        _need(q['policy_id']==REPLACEMENT_AUDIT_ID and parent['policy_id']==AUDIT_ID)
        validate_replacement_manager_bridge(q['manager_bridge'],parent,atom_count)
        _need(q['correction_policy_id']==CORRECTION_ID and q['plane_order_safe'] is True
            and q['correction_core_sha256']==QUALIFIED_CORRECTION_SHA256)
        _need(q['correction_qualification']=='SAMPLED_NATIVE_DERIVATIVES_PASS' and q['analysis_completed'] is True
            and q['captured_inventory_matches'] is True and q['normalization'] is False
            and q['model_optimization']=='NOT_RUN' and q['automatic_adoption'] is False)
        digest=q['constraint_signature_before'];_need(digest==q['constraint_signature_after']
            and isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest))
        _need(type(q['evaluation_calls']) is int and type(q['max_evaluation_calls']) is int
            and 0<q['evaluation_calls']<=q['max_evaluation_calls']<=2000)
        _need(q['correction_statistics']['max_energy_change']==0.)
        for field,modules in [('installed_numeric_sources',NUMERIC_MODULES),('installed_adapter_sources',ADAPTER_MODULES)]:
            rows=q[field];_need([r['module'] for r in rows]==list(modules))
            _need([(r['module'],r['sha256']) for r in rows]==[(r['module'],r['sha256']) for r in parent[field]])
            _need(all(isinstance(r['sha256'],str) and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']) for r in rows))
        cpp=q['installed_parallelity_sources'];_need(cpp==parent['installed_parallelity_sources']
            and len(cpp)==2 and {r['path'] for r in cpp}=={'parallelity.h','parallelity_bpl.cpp'}
            and all(r['status']=='RECORDED' and type(r['bytes']) is int and r['bytes']>0
                and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']) for r in cpp))
        _need(q['native_parallelity_proxies']==parent['native_parallelity_proxies'])
        _sampled_cases(q,atom_count,{'initial'})
        case=q['cases']['initial'];families=case['families'];baseline=families['all']['baseline']
        for family in families.values():
            b=family['baseline'];_finite([b['target'],family['repeat_target'],family['repeat_gradient_norm']],3)
            _need(_close(b['target'],family['repeat_target']) and _close(b['gradient_norm'],family['repeat_gradient_norm']))
        total=math.fsum(families[name]['baseline']['target'] for name in FAMILIES[1:])
        _need(_close(total,baseline['target']) and _close(case['target_additivity']['all'],baseline['target'])
            and _close(case['target_additivity']['sum_controls'],total))
        summed=[math.fsum(families[name]['baseline']['gradient'][i] for name in FAMILIES[1:]) for i in range(3*atom_count)]
        mismatch=_norm([a-b for a,b in zip(summed,baseline['gradient'])])
        _need(_close(mismatch,case['gradient_additivity']['difference_norm'])
            and mismatch<=1e-8+1e-10*max(1.,baseline['gradient_norm']))
        raw=q['raw_snapshot'];captured,rebuilt=raw['captured'],raw['rebuilt']
        for row in [captured,rebuilt]:_finite([row['target'],*row['gradient']],1+3*atom_count)
        _need(_close(captured['target'],rebuilt['target'])
            and all(_close(a,b) for a,b in zip(captured['gradient'],rebuilt['gradient'])))
        _need(_close(baseline['target'],captured['target']))
        comparison=case['captured_snapshot_match']['comparisons']['target']
        _need(comparison['consistent'] is True and _close(comparison['captured'],captured['target'])
            and _close(comparison['rebuilt'],baseline['target']))
        return True
    except (KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError) as exc:
        raise ValueError('Require complete replacement-manager gradient qualification') from exc


def validate_continuation(result,qualified,atom_count):
    """Require a qualified, bounded prior endpoint before coordinate continuation."""
    try:
        validate_gradient_qualification(qualified,atom_count)
        q=result
        _need(q['policy_id'] in {POLICY_ID,CONTINUATION_POLICY_ID} and q['status']=='REVIEW')
        _need(q['starting_coordinates'] in {'CAPTURED_INITIAL','SAVED_FULL_PRECISION_ENDPOINT'})
        _need(q['captured_inventory_matches'] is True and q['qualified_initial_snapshot_matches'] is True
            and q['policy_inventory'] is True and q['normalization'] is False and q['automatic_adoption'] is False)
        _need(q['correction_policy_id']==CORRECTION_ID and q['endpoint_derivative_qualification']=='SAMPLED_NATIVE_DERIVATIVES_PASS')
        _need(q['constraint_signature_before']==q['constraint_signature_after']==qualified['constraint_signature_before'])
        for field,old in [('installed_optimizer_sources','installed_numeric_sources'),('installed_adapter_sources','installed_adapter_sources'),('installed_parallelity_sources','installed_parallelity_sources')]:
            _need(q[field]==qualified[old])
        stopping=q['stopping']
        _need(stopping['error'] is None and stopping['native_criterion_met'] is False)
        _need(all(type(stopping[k]) is int and stopping[k]>0 for k in ['iterations','calls','max_iterations']))
        _need((stopping['reason']=='max_iterations' and stopping['iterations']>=stopping['max_iterations'])
            or (stopping['reason']=='max_calls' and stopping['calls']>=q['termination_parameters']['max_calls']))
        points=q['final_sites_cart'];_need(len(points)==atom_count)
        for point in points:_finite(point,3)
        audit=q['endpoint_gradient_audit']
        _need(audit['policy_id']=='cif-fixed-native-gradient-audit-v1' and type(audit['evaluation_calls']) is int
            and 0<audit['evaluation_calls']<=audit['max_evaluation_calls']<=4000)
        _need(audit['analysis_completed'] is True and audit['automatic_adoption'] is False and audit['model_optimization']=='NOT_RUN')
        _need(audit['selected_indices']==qualified['selected_indices'])
        _sampled_cases(audit,atom_count,{'full_precision','pdb_rounded'})
        for name,field in [('full_precision','final'),('pdb_rounded','serialized')]:
            baseline=audit['cases'][name]['families']['all']['baseline']
            _need(all(_close(q[field][key],baseline[key]) for key in ['target','gradient_norm']))
        return True
    except (KeyError,TypeError,OverflowError,ZeroDivisionError) as exc:
        raise ValueError('Require complete qualified continuation evidence') from exc
