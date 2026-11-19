"""Native fixed-point energy/force attribution for target-only bond changes.

The existing capture owner authenticates native execution and the supplied local
kernel observations. This reader does not assume a harmonic potential, qualify a
reference library, optimize coordinates or approve an ordinary repaired bundle.
"""
import math

from .cif_linear_bond_native import qualify_linked_linear_bond_candidate
from .cif_linked_linear_torsion import _exact, _need
from .cif_linked_torsion_energy import _snapshots, _finite, _vector_close
from .cif_candidate_usability import _close

POLICY_ID = 'cif-linked-linear-bond-target-energy-v1'


def changed_bond_pairs(before, after):
    """Retain exact native order after the complete target inventory gate passes."""
    left,right=[n['geometry']['proxy_details']['bond_simple'] for n in (before,after)]
    _need(len(left)==len(right),'Bond target repair cannot change native membership')
    pairs=[]
    for old,new in zip(left,right):
        if _exact(old,new):continue
        fields={'i_seqs','atoms','distance_ideal','weight','origin_id','symmetry_operation'}
        _need(all(set(p)==fields and p['symmetry_operation'] is None for p in (old,new)),
              'Unqualified native bond fields or symmetry transformation')
        _need(_exact({k:v for k,v in old.items() if k!='distance_ideal'},
                     {k:v for k,v in new.items() if k!='distance_ideal'}),
              'Bond target attribution cannot change strength or identity')
        pairs.append((old,new))
    _need(bool(pairs),'Require a nonempty target-only native bond change')
    return pairs


def native_bond_evaluator(gr, flex):
    """Compare the actual native bond with a local native accumulator.

    Copy every native potential option explicitly. Never reconstruct the energy
    from distance and weight alone; slack and top-out remain native decisions.
    """
    def evaluate(sites, proxy):
        operator=proxy.rt_mx_ji
        if operator is not None:
            raise ValueError('Native bond attribution requires an untransformed simple proxy')
        ids=list(proxy.i_seqs)
        if len(ids)!=2 or len(set(ids))!=2:
            raise ValueError('Native bond attribution requires two distinct atoms')
        restraint=gr.bond(sites_cart=sites,proxy=proxy)
        local=gr.bond_simple_proxy(i_seqs=[0,1],distance_ideal=proxy.distance_ideal,
            weight=proxy.weight,slack=proxy.slack,limit=proxy.limit,
            top_out=proxy.top_out,origin_id=proxy.origin_id)
        points=flex.vec3_double([sites[i] for i in ids]);gradient=flex.vec3_double(2,(0.,0.,0.))
        proxies=gr.shared_bond_simple_proxy();proxies.append(local)
        target=gr.bond_residual_sum(sites_cart=points,proxies=proxies,gradient_array=gradient)
        return dict(single_target=float(restraint.residual()),
            single_gradient=[float(v) for point in restraint.gradients() for v in point],
            accumulated_target=float(target),accumulated_gradient=[float(v) for v in gradient.as_double()])
    return evaluate


def qualify_linked_linear_bond_energy(before, after, source, dictionary, component,
                                     reference, candidate, references, *, bonds):
    """Require local native changes to explain every global energy/force change.

    Each pair binds the before/after proxy, exact selected coordinates, native
    slack/limit/top-out, and two single/container evaluations. A numerical pass
    is fixed-point attribution; derivative correctness and survival are separate.
    """
    inventory=qualify_linked_linear_bond_candidate(before,after,source,dictionary,component,
                                                  reference,candidate,bonds=bonds)
    _need(inventory['inventory_checks_pass'],'Require exact native target delivery before energy attribution')
    try:
        left,right=_snapshots(before),_snapshots(after)
        _need(_exact(before['energy_inventory']['installed_sources'],after['energy_inventory']['installed_sources']),
              'Native energy consumers differ')
        points=before['geometry']['sites_cart_exact'];count=before['atom_count']
        _need(type(count) is int and count>0 and len(points)==count
              and all(len(p)==3 and all(_finite(v) for v in p) for p in points),'Invalid bond coordinates')
        pairs=changed_bond_pairs(before,after)
        _need(len(pairs)==inventory['changed_native_bonds']==len(references),'Require every changed bond reference')
        target_terms=[];gradient_terms=[[] for _ in range(3*count)];local_checks=[]
        for ref,pair in zip(references,pairs):
            _need(isinstance(ref,dict) and set(ref)=={'before','after'},'Incomplete local bond reference')
            options=[]
            for label,proxy,sign in zip(('before','after'),pair,(-1.,1.)):
                row=ref[label];ids=proxy['i_seqs']
                _need(len(ids)==2 and len(set(ids))==2 and all(type(i) is int and 0<=i<count for i in ids),
                      'Invalid local native bond indices')
                _need(set(row)=={'proxy','sites_cart','native_parameters','evaluations'}
                      and _exact(row['proxy'],proxy) and _exact(row['sites_cart'],[points[i] for i in ids]),
                      'Local bond reference differs from native proxy/coordinates')
                parameters=row['native_parameters'];options.append(parameters)
                _need(set(parameters)=={'slack','limit','top_out'} and _finite(parameters['slack'])
                      and parameters['slack']>=0 and _finite(parameters['limit'])
                      and type(parameters['top_out']) is bool
                      and (not parameters['top_out'] or parameters['limit']>0),'Invalid native bond potential options')
                evaluations=row['evaluations'];_need(len(evaluations)==2,'Require repeated native bond evaluations')
                for e in evaluations:
                    _need(set(e)=={'single_target','single_gradient','accumulated_target','accumulated_gradient'}
                          and all(_finite(e[k]) and e[k]>=0 for k in ('single_target','accumulated_target'))
                          and all(len(e[k])==6 and all(_finite(v) for v in e[k]) for k in ('single_gradient','accumulated_gradient')),
                          'Incomplete or nonfinite native bond observation')
                    local_checks.append(_close(e['single_target'],e['accumulated_target'])
                                        and _vector_close(e['single_gradient'],e['accumulated_gradient']))
                a,b=evaluations
                local_checks.append(_close(a['single_target'],b['single_target']) and _vector_close(a['single_gradient'],b['single_gradient']))
                target_terms.append(sign*a['single_target'])
                for j,index in enumerate(ids):
                    for axis in range(3):gradient_terms[3*index+axis].append(sign*a['single_gradient'][3*j+axis])
            _need(_exact(*options),'Native bond potential options changed with the target')
        expected_target=math.fsum(target_terms);expected_gradient=[math.fsum(v) for v in gradient_terms]
        checks=dict(local_native_evaluations_agree=all(local_checks))
        for label,snapshots in [('before',left),('after',right)]:
            a,b=snapshots
            checks[label+'_term_repeats']=a['terms'].keys()==b['terms'].keys() and all(_close(v,b['terms'][k]) for k,v in a['terms'].items())
            checks[label+'_count_repeats']=_exact(a['proxy_counts'],b['proxy_counts'])
            checks[label+'_term_sum']=all(_close(s['target'],math.fsum(s['terms'].values())) for s in snapshots)
        a,b=left[0],right[0]
        _need('bond_residual_sum' in a['terms'] and 'bond_residual_sum' in b['terms']
              and type(a['proxy_counts'].get('n_bond_proxies')) is int,'Missing native bond energy/count')
        checks['unaffected_terms']=a['terms'].keys()==b['terms'].keys() and all(_close(v,b['terms'][k]) for k,v in a['terms'].items() if k!='bond_residual_sum')
        checks['proxy_counts_unchanged']=_exact(a['proxy_counts'],b['proxy_counts'])
        checks['bond_delta_matches_local_native']=_close(b['terms']['bond_residual_sum']-a['terms']['bond_residual_sum'],expected_target)
        checks['total_delta_matches_local_native']=_close(b['target']-a['target'],expected_target)
        delta=[y-x for x,y in zip(a['gradient'],b['gradient'])]
        checks['full_gradient_delta_matches_local_native']=_vector_close(delta,expected_gradient)
        return dict(schema_version=1,policy_id=POLICY_ID,status='REVIEW',component=component,
            inventory_checks_pass=True,checks=checks,numerical_checks_pass=all(checks.values()),
            changed_bond_count=len(pairs),bond_target_delta=expected_target,target_delta=b['target']-a['target'],
            gradient_delta_error_norm=math.dist(delta,expected_gradient),tolerance={'absolute':1e-8,'relative':1e-10},
            reference_authority='NOT_QUALIFIED',native_kernel_provenance='CALLER_MUST_AUTHENTICATE',
            derivative_qualification='NOT_RUN',achieved_geometry='NOT_ASSESSED',scientific_approval='NOT_RUN',
            model_editing='NOT_RUN',optimization='NOT_RUN',automatic_adoption=False)
    except (KeyError,TypeError,IndexError,AttributeError,OverflowError) as exc:
        raise ValueError('Incomplete native bond-target energy evidence') from exc
