"""Derivative-evidence preconditions for an explicit corrected geometry trial."""
from __future__ import annotations
import math

POLICY_ID='cif-fixed-na-corrected-geometry-trial-v1'
CORRECTION_ID='native-parallelity-both-first-planes-v1'
AUDIT_ID='cif-fixed-native-plane-order-gradient-audit-v1'
FAMILIES=('all','bond','angle','dihedral','chirality','planarity','parallelity','nonbonded')
CASES={'initial','full_precision','pdb_rounded'}
STEPS=[1e-3,1e-4,1e-5,1e-6]


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


def validate_gradient_qualification(result,atom_count):
    """Recompute sampled proof before allowing any optimizer invocation."""
    try:
        q=result
        _need(q['policy_id']==AUDIT_ID and q['correction_policy_id']==CORRECTION_ID and q['plane_order_safe'] is True)
        _need(q['correction_qualification']=='SAMPLED_NATIVE_DERIVATIVES_PASS' and q['analysis_completed'] is True
              and q['captured_inventory_matches'] is True and q['normalization'] is False
              and q['model_optimization']=='NOT_RUN' and q['automatic_adoption'] is False)
        _need(q['constraint_signature_before']==q['constraint_signature_after'] and len(q['constraint_signature_before'])==64)
        _need(set(q['cases'])==CASES and q['step_sizes']==STEPS and q['directional_tolerance']=={'absolute':1e-4,'relative':1e-4})
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
