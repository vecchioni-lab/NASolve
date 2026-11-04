"""Prove zero-contribution neighbour-cache changes before a strict retry."""
from copy import deepcopy
import math

POLICY_ID='cif-native-nonbonded-cache-proof-v1'

def _norm(v):return math.sqrt(math.fsum(x*x for x in v))
def _close(a,b):return math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10)
def _vector(a,b):return len(a)==len(b) and _norm([x-y for x,y in zip(a,b)])<=1e-8+1e-10*max(1.,_norm(a),_norm(b))


def _pair_proof(row,count):
    pairs={};target=0.;gradient=[0.]*(3*count);valid=True
    try:
        for p in row['pairs']:
            ids=p['i_seqs'];g=p['gradient'];key=tuple(ids)
            if (len(ids)!=2 or ids!=sorted(ids) or len(set(ids))!=2 or any(type(i) is not int or not 0<=i<count for i in ids)
                    or key in pairs or len(g)!=6 or any(type(v) not in (int,float) or not math.isfinite(v) for v in [p['vdw_distance'],p['residual'],*g])
                    or p['vdw_distance']<=0 or p['residual']<0):return {},False
            pairs[key]=p;target+=p['residual']
            for j,i in enumerate(ids):
                for axis in range(3):gradient[3*i+axis]+=g[3*j+axis]
        valid=(row['proxy_counts']['n_nonbonded_proxies']==len(pairs) and len(row['nonbonded_gradient'])==3*count
            and _close(target,row['nonbonded_target']) and _vector(gradient,row['nonbonded_gradient']))
    except (KeyError,TypeError,ValueError,OverflowError):valid=False
    return pairs,valid


def compare_cache_snapshots(before,after,atom_count):
    a,ap=_pair_proof(before,atom_count);b,bp=_pair_proof(after,atom_count);added=sorted(set(b)-set(a));removed=sorted(set(a)-set(b))
    common=all(a[k]['vdw_distance']==b[k]['vdw_distance'] and _close(a[k]['residual'],b[k]['residual']) and _vector(a[k]['gradient'],b[k]['gradient']) for k in a.keys()&b.keys())
    zero=all(row['residual']==0. and all(v==0. for v in row['gradient']) for row in [*[a[k] for k in removed],*[b[k] for k in added]])
    checks={'before_single_container_sum':ap,'after_single_container_sum':bp,'common_pairs_unchanged':common,
        'changed_pairs_exactly_zero':zero,'function_unchanged':before.get('function_parameters')==after.get('function_parameters'),
        'nonbonded_target_unchanged':_close(before['nonbonded_target'],after['nonbonded_target']),
        'nonbonded_gradient_unchanged':_vector(before['nonbonded_gradient'],after['nonbonded_gradient'])}
    return {'policy_id':POLICY_ID,'checks':checks,'checks_pass':all(checks.values()),'added_pairs':[list(k) for k in added],
        'removed_pairs':[list(k) for k in removed],'before_count':len(a),'after_count':len(b),'automatic_adoption':False}


def audit_cache_stabilized_impact(evaluate,cases,indices,references,*,max_calls=2000):
    if __package__:
        from .cif_linear_torsion_impact import audit_linear_torsion_impact,FAMILIES
    else:
        from impact_core import audit_linear_torsion_impact,FAMILIES
    if type(max_calls) is not int or not 1<=max_calls<=2000:raise ValueError('Invalid evaluation budget')
    calls=0;result=None;out={};numerical_calls=0
    def call(manager,points,family,*,capture_pairs=False):
        nonlocal calls
        if calls>=max_calls:raise ValueError('Native manager evaluation budget exhausted')
        calls+=1;p=deepcopy(points);r=evaluate(manager,p,family,capture_pairs=capture_pairs)
        if p!=points:raise ValueError('Native cache callback mutated coordinates')
        return r
    for label,points in cases.items():
        snapshots=[{m:{f:call(m,points,f,capture_pairs=True) for f in FAMILIES} for m in ['original','candidate']} for _ in range(2)]
        transitions={};checks=[];stable={}
        for manager in ['original','candidate']:
            first,last=snapshots[0][manager],snapshots[1][manager]
            for name,left,right in [('first_full_to_nonbonded',first['all'],first['nonbonded']),('full_repeat',first['all'],last['all']),
                                    ('nonbonded_repeat',first['nonbonded'],last['nonbonded']),('settled_full_to_nonbonded',last['all'],last['nonbonded'])]:
                q=compare_cache_snapshots(left,right,len(points));transitions[manager+'_'+name]=q;checks.append(q['checks_pass'])
            checks.append(_close(first['all']['target'],last['all']['target']) and _vector(first['all']['gradient'],last['all']['gradient']))
            stable[manager]=last['all']['nonbonded_membership']
            checks.append(last['nonbonded']['nonbonded_membership']==stable[manager])
        checks.append(stable['original']==stable['candidate'])
        preflight={'policy_id':POLICY_ID,'snapshots':snapshots,'transitions':transitions,'checks_pass':all(checks),
            'raw_transitions_preserved':True,'strict_impact_retried':False,'post_preflight_membership_stable':True}
        if not all(checks):
            out[label]={'cache_preflight':preflight,'numerical_checks_pass':False,'strict_impact':'NOT_RUN'};continue
        def fixed(manager,p,family):
            row=call(manager,p,family)
            if family in {'all','nonbonded'} and (row['nonbonded_membership']!=stable[manager]
                    or row.get('function_parameters')!=snapshots[1][manager]['all'].get('function_parameters')):
                preflight['post_preflight_membership_stable']=False
            # Kernel proof snapshots belong to preflight, not every FD row.
            return {k:v for k,v in row.items() if k not in {'pairs','nonbonded_gradient','nonbonded_target','cache_state'}}
        trial=audit_linear_torsion_impact(fixed,{label:points},indices,{label:references[label]},max_calls=max_calls)
        numerical_calls+=trial['evaluation_calls'];result=trial;case=trial['cases'][label];preflight['strict_impact_retried']=True
        case['cache_preflight']=preflight;case['checks']['cache_pair_membership_stable']=preflight['post_preflight_membership_stable']
        case['numerical_checks_pass']=all(case['checks'].values());out[label]=case
    if result is None:
        result={'schema_version':1,'status':'REVIEW','model_optimization':'NOT_RUN','automatic_adoption':False,'scientific_approval':'NOT_RUN'}
    result.update(cases=out,analysis_completed=True,numerical_checks_pass=all(v['numerical_checks_pass'] for v in out.values()),
        evaluation_calls=calls,max_evaluation_calls=max_calls,impact_evaluation_calls=numerical_calls,
        cache_policy_id=POLICY_ID,cache_preflight_completed=True,pair_kernel_calls=getattr(evaluate,'pair_kernel_calls',0),max_pair_kernel_calls=5000)
    return result


def replay_cache_impact_evidence(saved,cases,indices,references):
    """Recompute saved pair proofs and strict arithmetic without native code.

    Perturbed pair lists were not stored by v1. Their continuous membership
    gate remains an explicitly identified, pinned-worker result.
    """
    from .cif_linear_torsion_impact import replay_impact_evidence,FAMILIES,STEPS
    try:
        if (saved['cache_policy_id']!=POLICY_ID or saved['cache_preflight_completed'] is not True
                or saved['analysis_completed'] is not True or saved['numerical_checks_pass'] is not True
                or saved['automatic_adoption'] is not False or set(saved['cases'])!=set(cases)
                or saved['max_evaluation_calls']!=2000 or saved['max_pair_kernel_calls']!=5000):
            raise ValueError('Incomplete successful cache audit')
        kernels=0;calls=0;transitions=0;proof={}
        for label,points in cases.items():
            case=saved['cases'][label];pf=case['cache_preflight'];snapshots=pf['snapshots']
            if (len(snapshots)!=2 or pf['policy_id']!=POLICY_ID or any(pf[k] is not True for k in
                    ['checks_pass','strict_impact_retried','post_preflight_membership_stable','raw_transitions_preserved'])):
                raise ValueError('Cache preflight did not qualify')
            rebuilt={};stable={}
            for manager in ['original','candidate']:
                first,last=snapshots[0][manager],snapshots[1][manager]
                if set(first)!=set(FAMILIES) or set(last)!=set(FAMILIES):raise ValueError('Incomplete cache cycle')
                for name,left,right in [('first_full_to_nonbonded',first['all'],first['nonbonded']),
                        ('full_repeat',first['all'],last['all']),('nonbonded_repeat',first['nonbonded'],last['nonbonded']),
                        ('settled_full_to_nonbonded',last['all'],last['nonbonded'])]:
                    q=compare_cache_snapshots(left,right,len(points));rebuilt[manager+'_'+name]=q;transitions+=1
                    if not q['checks_pass']:raise ValueError('Saved native pair contributions require review')
                if not _close(first['all']['target'],last['all']['target']) or not _vector(first['all']['gradient'],last['all']['gradient']):
                    raise ValueError('Cache repeat changed full energy or gradient')
                stable[manager]=last['all']['nonbonded_membership']
                if last['nonbonded']['nonbonded_membership']!=stable[manager]:raise ValueError('Unsettled saved membership')
                for cycle in [first,last]:
                    for family in ['all','nonbonded']:
                        row=cycle[family];pairs,valid=_pair_proof(row,len(points))
                        membership=[{'i_seqs':list(ids),'vdw_distance':p['vdw_distance']} for ids,p in sorted(pairs.items())]
                        if not valid or row['nonbonded_membership']!=membership:raise ValueError('Pair proof and membership differ')
                        kernels+=len(pairs)+1
                for stage in ['baselines','repeats','final_repeats']:
                    for family in ['all','nonbonded']:
                        row=case[stage][manager][family]
                        if row['nonbonded_membership']!=stable[manager] or row['function_parameters']!=last['all']['function_parameters']:
                            raise ValueError('Saved strict baseline membership or function changed')
            if stable['original']!=stable['candidate'] or rebuilt!=pf['transitions'] or case['checks']['cache_pair_membership_stable'] is not True:
                raise ValueError('Saved cache proof differs')
            projected=deepcopy(saved);projected['cases']={label:deepcopy(case)}
            del projected['cases'][label]['cache_preflight'];del projected['cases'][label]['checks']['cache_pair_membership_stable']
            projected['cases'][label]['numerical_checks_pass']=all(projected['cases'][label]['checks'].values())
            projected['evaluation_calls']=6*len(FAMILIES)+2*len(STEPS)*sum(len(rows) for rows in case['candidate_derivatives'].values())
            q=replay_impact_evidence(projected,{label:points},indices,{label:references[label]})
            if q['cases'][label]['failed_checks'] or case['numerical_checks_pass'] is not True:raise ValueError('Strict numerical retry requires review')
            calls+=q['evaluation_calls_recomputed'];proof[label]=q['cases'][label]
        if (not 0<kernels==saved['pair_kernel_calls']<=5000 or calls!=saved['impact_evaluation_calls']
                or calls+4*len(FAMILIES)*len(cases)!=saved['evaluation_calls'] or saved['evaluation_calls']>2000):
            raise ValueError('Saved cache evaluation accounting differs')
        return {'status':'SAVED_CACHE_AND_STRICT_REPLAY_PASS','captured_code_execution':'NOT_RUN',
            'preflight_transitions_recomputed':transitions,'recorded_pair_kernel_calls_verified':kernels,
            'strict_calls_recomputed':calls,'evaluation_calls_recomputed':saved['evaluation_calls'],'cases':proof,
            'perturbed_membership':'PINNED_WORKER_RESULT_ONLY; raw perturbed pair lists were not stored'}
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete saved cache proof') from exc


def native_cache_evaluator(managers,gr,flex,flags):
    """Use the native energy object's actual pair list; never rebuild to inspect."""
    def evaluate(manager,points,family,*,capture_pairs=False):
        geo,_=managers[manager];active=flags.flags(default=family=='all')
        if family!='all':setattr(active,family,True)
        sites=flex.vec3_double(points);e=geo.energies_sites(sites_cart=sites,flags=active,compute_gradients=True,normalization=False)
        row={'target':float(e.target),'gradient':[float(v) for v in e.gradients.as_double()],
            'proxy_counts':{k:v for k,v in vars(e).items() if k.startswith('n_') and k.endswith('_proxies') and (v is None or isinstance(v,int))},
            'nonbonded_membership':None}
        if family not in {'all','nonbonded'}:return row
        nb=e.nonbonded_proxies;function=e.nonbonded_function
        if nb is None or len(nb.asu) or not isinstance(function,gr.prolsq_repulsion_function):raise RuntimeError('Unsupported nonbonded function or ASU pair proof')
        parameters={'class':'prolsq_repulsion_function',**{k:float(getattr(function,k)) for k in ['c_rep','k_rep','irexp','rexp']}}
        pairs=[];membership=[]
        def kernel():
            if evaluate.pair_kernel_calls>=5000:raise ValueError('Native pair kernel budget exhausted')
            evaluate.pair_kernel_calls+=1
        for p in nb.simple:
            ids=list(p.i_seqs);rt=p.rt_mx_ji
            if rt is not None and not rt.is_unit_mx():raise RuntimeError('Symmetry nonbonded proof unsupported')
            order=sorted(range(2),key=lambda j:ids[j]);identity=[ids[j] for j in order]
            descriptor={'i_seqs':identity,'vdw_distance':float(p.vdw_distance)};membership.append(descriptor)
            if capture_pairs:
                kernel();r=gr.nonbonded_prolsq(sites_cart=sites,proxy=p,function=function);gradient=list(r.gradients())
                pairs.append({**descriptor,'residual':float(r.residual()),'gradient':[float(v) for j in order for v in gradient[j]]})
        membership.sort(key=lambda p:(p['i_seqs'],p['vdw_distance']));row['nonbonded_membership']=membership;row['function_parameters']=parameters
        if capture_pairs:
            kernel();gradient=flex.vec3_double(len(points),(0.,0.,0.))
            target=gr.nonbonded_residual_sum(sites_cart=sites,sorted_asu_proxies=nb,gradient_array=gradient,function=function)
            if not _close(float(target),float(e.nonbonded_residual_sum)):raise RuntimeError('Native nonbonded container/manager target differs')
            row.update(pairs=sorted(pairs,key=lambda p:p['i_seqs']),nonbonded_target=float(target),nonbonded_gradient=[float(v) for v in gradient.as_double()],
                cache_state={k:getattr(geo,k,None) for k in ['n_updates_pair_proxies','nonbonded_distance_cutoff','adjusted_nonbonded_distance_cutoff','effective_nonbonded_buffer']})
        return row
    evaluate.pair_kernel_calls=0
    return evaluate
