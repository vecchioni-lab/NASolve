"""Whole-plane numerical attribution after exact source-supported completion.

Supplied captures and kernel observations require caller authentication. This
pure gate checks fixed-point arithmetic, not derivative correctness or adoption.
"""
import math

from .cif_plane_native import qualify_linked_plane_candidate, _canonical_proxy
from .cif_linked_linear_torsion import _exact, _need
from .cif_linked_torsion_energy import _snapshots, _finite, _vector_close
from .cif_candidate_usability import _close

POLICY_ID = 'cif-linked-plane-completion-energy-v1'


def changed_plane_pairs(before, after):
    """Pair whole groups by unchanged native order, preserving atom/weight ties.

    The exact plane inventory gate must pass before using these as a repair plan.
    Unknown proxy fields and symmetry extensions require another evaluator.
    """
    left, right = [n['geometry']['proxy_details']['planarity'] for n in (before,after)]
    _need(len(left) == len(right), 'Plane completion cannot change the plane count')
    pairs = []
    for old, new in zip(left,right):
        old, new = _canonical_proxy(old), _canonical_proxy(new)
        if _exact(old,new):
            continue
        _need(all(set(p) == {'i_seqs','atoms','weights','origin_id'} for p in (old,new)),
              'Unsupported plane proxy fields for numerical attribution')
        old_members = {i:(a,w) for i,a,w in zip(old['i_seqs'],old['atoms'],old['weights'])}
        new_members = {i:(a,w) for i,a,w in zip(new['i_seqs'],new['atoms'],new['weights'])}
        _need(old_members.keys() < new_members.keys() and all(_exact(v,new_members[i]) for i,v in old_members.items())
              and type(old['origin_id']) is int and old['origin_id'] == new['origin_id'] == 0,
              'Require a strict identity-preserving component plane extension')
        pairs.append((old,new))
    _need(0 < len(pairs) <= 128, 'Require a bounded nonempty set of completed planes')
    return pairs


def native_plane_evaluator(gr, flex):
    """Evaluate one complete identity-only group through two native interfaces."""
    def evaluate(points, row):
        if set(row) != {'i_seqs','atoms','weights','origin_id'} or len(points) != len(row['i_seqs']):
            raise ValueError('Require one complete supported local plane')
        count = len(points)
        proxy = gr.planarity_proxy(i_seqs=list(range(count)), weights=flex.double(row['weights']), origin_id=row['origin_id'])
        sites = flex.vec3_double(points)
        restraint = gr.planarity(sites_cart=sites,proxy=proxy)
        proxies = gr.shared_planarity_proxy();proxies.append(proxy)
        gradient = flex.vec3_double(count,(0.,0.,0.))
        target = gr.planarity_residual_sum(sites_cart=sites,proxies=proxies,gradient_array=gradient)
        return dict(single_target=float(restraint.residual()),
            single_gradient=[float(v) for p in restraint.gradients() for v in p],
            accumulated_target=float(target), accumulated_gradient=[float(v) for v in gradient.as_double()])
    return evaluate


def qualify_linked_plane_energy(before, after, source, dictionary, support, component, candidate, references):
    """Attribute the full native delta to old/new whole-plane evaluations.

    Each reference pairs before/after proxy, exact local sites, observed symmetry
    operations and two single/container evaluations. Added atoms alone are not an
    energy model: fitting the completed plane changes forces on old members too.
    """
    inventory = qualify_linked_plane_candidate(before,after,source,dictionary,support,component,candidate)
    _need(inventory['inventory_checks_pass'], 'Require exact plane inventory qualification first')
    try:
        left,right = _snapshots(before),_snapshots(after)
        _need(_exact(before['energy_inventory']['installed_sources'],after['energy_inventory']['installed_sources']),
              'Plane energy consumers differ')
        points = before['geometry']['sites_cart_exact']; count = before['atom_count']
        _need(type(count) is int and count > 0 and len(points) == count
              and all(len(p)==3 and all(_finite(v) for v in p) for p in points), 'Invalid native plane coordinates')
        pairs = changed_plane_pairs(before,after)
        _need(len(pairs) == inventory['extended_native_planes'] == len(references), 'Require every changed whole-plane reference')
        gradient_terms = [[] for _ in range(3*count)]; target_terms=[]; reference_checks=[]
        for reference,pair in zip(references,pairs):
            _need(set(reference) == {'before','after'}, 'Incomplete old/new plane reference')
            for label,proxy,sign in zip(('before','after'),pair,(-1.,1.)):
                ref=reference[label]; ids=proxy['i_seqs']
                _need(all(0 <= i < count for i in ids), 'Plane reference index outside captured coordinates')
                _need(set(ref) == {'proxy','sites_cart','symmetry_operations','evaluations'}
                      and _exact(ref['proxy'],proxy) and _exact(ref['sites_cart'],[points[i] for i in ids]),
                      'Plane reference identity/weights/coordinates differ')
                ops=ref['symmetry_operations']
                _need(ops is None or (isinstance(ops,list) and len(ops)==len(ids) and all(v=='x,y,z' for v in ops)),
                      'Symmetry-transformed planes require separate numerical qualification')
                evaluations=ref['evaluations'];_need(len(evaluations)==2, 'Require two whole-plane evaluations')
                for row in evaluations:
                    _need(set(row)=={'single_target','single_gradient','accumulated_target','accumulated_gradient'}
                          and all(_finite(row[k]) and row[k]>=0 for k in ('single_target','accumulated_target'))
                          and all(len(row[k])==3*len(ids) and all(_finite(v) for v in row[k])
                                  for k in ('single_gradient','accumulated_gradient')), 'Incomplete or nonfinite plane numerical reference')
                    reference_checks.append(_close(row['single_target'],row['accumulated_target'])
                        and _vector_close(row['single_gradient'],row['accumulated_gradient']))
                a,b=evaluations
                reference_checks.append(_close(a['single_target'],b['single_target']) and _vector_close(a['single_gradient'],b['single_gradient']))
                target_terms.append(sign*a['single_target'])
                for local,index in enumerate(ids):
                    for axis in range(3):gradient_terms[3*index+axis].append(sign*a['single_gradient'][3*local+axis])
        expected_target=math.fsum(target_terms);expected_gradient=[math.fsum(v) for v in gradient_terms]
        checks={'whole_plane_repeats_and_container':all(reference_checks)}
        for label,snapshots in [('before',left),('after',right)]:
            a,b=snapshots
            checks[label+'_term_repeats']=a['terms'].keys()==b['terms'].keys() and all(_close(v,b['terms'][k]) for k,v in a['terms'].items())
            checks[label+'_count_repeats']=_exact(a['proxy_counts'],b['proxy_counts'])
            checks[label+'_term_sum']=all(_close(s['target'],math.fsum(s['terms'].values())) for s in snapshots)
        a,b=left[0],right[0]
        _need('planarity_residual_sum' in a['terms'] and 'planarity_residual_sum' in b['terms']
              and type(a['proxy_counts'].get('n_planarity_proxies')) is int, 'Missing native plane energy/count')
        checks['unaffected_terms']=a['terms'].keys()==b['terms'].keys() and all(_close(v,b['terms'][k]) for k,v in a['terms'].items() if k!='planarity_residual_sum')
        checks['proxy_counts_unchanged']=_exact(a['proxy_counts'],b['proxy_counts'])
        checks['plane_delta_matches_complete_groups']=_close(b['terms']['planarity_residual_sum']-a['terms']['planarity_residual_sum'],expected_target)
        checks['total_delta_matches_complete_groups']=_close(b['target']-a['target'],expected_target)
        delta=[y-x for x,y in zip(a['gradient'],b['gradient'])]
        checks['full_gradient_delta_matches_complete_groups']=_vector_close(delta,expected_gradient)
        return dict(schema_version=1,policy_id=POLICY_ID,status='REVIEW',component=component,
            inventory_checks_pass=True,checks=checks,numerical_checks_pass=all(checks.values()),changed_plane_count=len(pairs),
            whole_plane_target_delta=expected_target,target_delta=b['target']-a['target'],gradient_delta_error_norm=math.dist(delta,expected_gradient),
            tolerance={'absolute':1e-8,'relative':1e-10},derivative_qualification='NOT_RUN',achieved_geometry='NOT_ASSESSED',
            scientific_approval='NOT_RUN',model_editing='NOT_RUN',optimization='NOT_RUN',automatic_adoption=False,
            scope='FIXED_POINT_WHOLE_PLANE_ATTRIBUTION; CALLER_AUTHENTICATES_CAPTURES_AND_KERNEL_REFERENCES')
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete whole-plane energy evidence') from exc
