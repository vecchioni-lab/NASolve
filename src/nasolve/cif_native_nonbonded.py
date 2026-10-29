"""Read-only native nonbonded attribution, separate from chemical acceptance."""
from collections import defaultdict
from inspect import getsource
import math

from . import cif_nonbonded_cache_audit as cache
from .cif_candidate_usability import energy_inventory_checks
from .cif_captured_geometry import review_captured_geometry, _site, _number

POLICY_ID = 'cif-native-nonbonded-attribution-v1'


def _capture_pairs(geo, points):
    """Run inside the native worker; reuse its actual energy-object pair lists."""
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    from cctbx.geometry_restraints import flags
    evaluate = native_cache_evaluator({'fixed': (geo, None)}, gr, flex, flags)
    snapshots = [evaluate('fixed', points, 'all', capture_pairs=True) for _ in range(2)]
    return {'status': 'RECORDED', 'normalization': False, 'symmetry_scope': 'IDENTITY_ONLY',
            'evaluation_calls': 2, 'pair_kernel_calls': evaluate.pair_kernel_calls,
            'max_pair_kernel_calls': 5000, 'snapshots': snapshots}


def native_nonbonded_worker(base):
    """Augment only the explicit energy worker; preserve all legacy bytes."""
    header = 'try:\n    from iotbx import phil\n'
    token = '    report["energy_inventory"]["status"]="RECORDED"\n'
    if base.count(header) != 1 or base.count(token) != 1 or 'nonbonded_inventory' in base:
        raise ValueError('Unsupported native energy worker for pair capture')
    helpers = getsource(cache._close) + '\n' + getsource(cache.native_cache_evaluator) + '\n' + getsource(_capture_pairs)
    extra = ('    report["nonbonded_inventory"] = _capture_pairs(geo, original_sites)\n'
             '    report["nonbonded_inventory"].update(schema_version=1, policy_id=' + repr(POLICY_ID) + ')\n'
             '    if original_sites != [[float(x) for x in p] for p in sites]:\n'
             '        raise RuntimeError("Native pair inventory moved coordinates")\n')
    return base.replace(header, helpers + '\n' + header).replace(token, token + extra)


def _pair_values(a, b, vdw, parameters):
    """Replay the captured prolsq convention, including zero-distance gradient."""
    distance = math.dist(a, b)
    c, k, i, r = (parameters[n] for n in ('c_rep', 'k_rep', 'irexp', 'rexp'))
    term = max(0., (k*vdw)**i-distance**i)
    residual = c*term**r
    factor = 0. if term == 0 or distance == 0 else -c*r*term**(r-1)*i*distance**(i-2)
    first = [factor*(x-y) for x,y in zip(a,b)]
    return distance, residual, [*first, *[-v for v in first]]


def review_native_nonbonded(native):
    """Explain actual native pairs; never infer membership from distance alone.

    Capture receipts, frozen input/worker hashes and source chemistry must be
    verified separately. Saved evidence proves this manager, not physical truth.
    """
    try:
        review_captured_geometry(native)
        if not all(energy_inventory_checks(native).values()):
            raise ValueError('Require complete repeatable fixed native energy evidence')
        q = native['nonbonded_inventory']; snapshots = q['snapshots']
        if (type(q['schema_version']) is not int or q['schema_version'] != 1 or q['policy_id'] != POLICY_ID
                or q['status'] != 'RECORDED' or q['normalization'] is not False
                or q['symmetry_scope'] != 'IDENTITY_ONLY' or type(q['evaluation_calls']) is not int
                or q['evaluation_calls'] != 2 or len(snapshots) != 2
                or type(q['max_pair_kernel_calls']) is not int or q['max_pair_kernel_calls'] != 5000):
            raise ValueError('Incomplete or unsupported native pair capture')
        atoms = native['atoms']; points = native['geometry']['sites_cart_exact']; kernels = 0
        energy = native['energy_inventory']['snapshots'][-1]
        for row in snapshots:
            for v in [row['target'], row['nonbonded_target'], *row['gradient'], *row['nonbonded_gradient']]:
                _number(v)
            pairs, valid = cache._pair_proof(row, len(atoms)); kernels += len(pairs)+1
            membership = [{'i_seqs': list(k), 'vdw_distance': p['vdw_distance']} for k,p in sorted(pairs.items())]
            if (not valid or row['nonbonded_membership'] != membership
                    or row['proxy_counts'] != energy['proxy_counts']
                    or not cache._close(row['target'], energy['target'])
                    or not cache._vector(row['gradient'], energy['gradient'])
                    or not cache._close(row['nonbonded_target'], _number(energy['terms']['nonbonded_residual_sum']))):
                raise ValueError('Pair inventory does not reproduce the captured manager')
            parameters = row['function_parameters']
            if (set(parameters) != {'class', 'c_rep', 'k_rep', 'irexp', 'rexp'}
                    or parameters['class'] != 'prolsq_repulsion_function'
                    or any(_number(parameters[k]) <= 0 for k in ('c_rep','k_rep','irexp','rexp'))):
                raise ValueError('Unsupported captured nonbonded function')
            for ids,p in pairs.items():
                distance,residual,gradient = _pair_values(points[ids[0]],points[ids[1]],p['vdw_distance'],parameters)
                for v in [distance,residual,*gradient]: _number(v)
                if not cache._close(residual,p['residual']) or not cache._vector(gradient,p['gradient']):
                    raise ValueError('Pair residual/gradient differs from coordinates and function')
        if (type(q['pair_kernel_calls']) is not int or q['pair_kernel_calls'] != kernels or kernels > 5000
                or not cache.compare_cache_snapshots(*snapshots,len(atoms))['checks_pass']
                or snapshots[0]['nonbonded_membership'] != snapshots[1]['nonbonded_membership']):
            raise ValueError('Pair repeat or kernel accounting differs')
        rows = []; groups = defaultdict(lambda: {'pair_count':0,'positive_residual_pairs':0,'residual':0.})
        for p in snapshots[-1]['pairs']:
            ids = p['i_seqs']; distance = math.dist(points[ids[0]],points[ids[1]])
            sites = [_site(atoms[i]) for i in ids]; key = tuple(sorted(set(sites)))
            row = {'i_seqs':ids.copy(),'atoms':[atoms[i]['label'] for i in ids], 'sites':sites,
                   'distance':distance,'vdw_distance':p['vdw_distance'],'overlap':p['vdw_distance']-distance,
                   'residual':p['residual'],'gradient_norm':cache._norm(p['gradient']),
                   'coincident':distance==0,'same_site':len(key)==1}
            rows.append(row); g = groups[key]; g['pair_count'] += 1
            g['positive_residual_pairs'] += p['residual'] > 0; g['residual'] += p['residual']
        ranked = sorted(rows,key=lambda r:(-r['residual'],r['i_seqs']))
        return {'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','analysis_completed':True,
                'pair_count':len(rows),'positive_residual_pairs':sum(r['residual']>0 for r in rows),
                'total_residual':snapshots[-1]['nonbonded_target'],'function_parameters':dict(parameters),
                'measurements':rows,'worst':ranked[:20],
                'by_site_pair':sorted(({'sites':list(k),**v} for k,v in groups.items()),key=lambda r:(-r['residual'],r['sites'])),
                'pair_sum_and_gradient_replay':True,'fixed_manager_repeats':True,
                'native_execution':'NOT_RUN','symmetry_scope':'IDENTITY_ONLY','chemical_qualification':'NOT_ESTABLISHED',
                'geometry_accepted':False,'automatic_adoption':False,
                'limitations':['Native exclusions/types and repulsion parameters are observations, not chemical authority.',
                               'No symmetry/ASU support, clashscore, physical acceptance threshold or complete force-field qualification.',
                               'Receipts and frozen inputs/worker/output hashes require separate attestation.']}
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete native pair attribution evidence') from exc
