"""Compare Cedar-reviewed native neighbors without reconstructing a neighbor list.

The caller must authenticate both captures with Cedar before calling this module.
The injected reviewer must be Cedar's maintained review_native_nonbonded function,
not a saved approval flag. This layer grants no geometry or chemistry approval.
"""
from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
import json
import math

POLICY = 'topostitch-directed-native-packing-comparison-v1'
NATIVE_POLICY = 'cif-native-nonbonded-asu-attribution-v1'


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Require finite native measurements')
    return float(value)


def _operation(rotation, translation):
    """Recover bounded standard-cell rational operations; never wrap a translation."""
    if len(rotation) != 9 or len(translation) != 3:
        raise ValueError('Incomplete fractional image operation')
    r = tuple(round(_number(v)) for v in rotation)
    t = tuple(Fraction(_number(v)).limit_denominator(24) for v in translation)
    if any(abs(a-b) > 1e-12 for a,b in zip(r,rotation)) or any(abs(float(a)-b)>1e-12 for a,b in zip(t,translation)):
        raise ValueError('Unsupported fractional operation precision or denominator')
    a,b,c,d,e,f,g,h,i = r
    determinant = a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
    if determinant != 1:
        raise ValueError('Require a proper unimodular fractional rotation')
    inverse = (e*i-f*h,c*h-b*i,b*f-c*e,f*g-d*i,a*i-c*g,c*d-a*f,d*h-e*g,b*g-a*h,a*e-b*d)
    return r,t,inverse


def _relative(first, second):
    # Apply first^-1 second. Comparing only j_sym would lose image identity.
    r,t,inverse = first
    other,u,_ = second
    rotation = tuple(sum(inverse[3*i+k]*other[3*k+j] for k in range(3)) for i in range(3) for j in range(3))
    translation = tuple(sum(inverse[3*i+k]*(u[k]-t[k]) for k in range(3)) for i in range(3))
    return rotation,translation


_IDENTITY = _operation((1,0,0,0,1,0,0,0,1),(0,0,0))


def _groups(native, review):
    labels = [a['label'] for a in native['atoms']]
    if not labels or any(not isinstance(s,str) or not s for s in labels) or len(set(labels)) != len(labels):
        raise ValueError('Require unique captured atom labels')
    inventory = native['nonbonded_inventory']
    if (inventory['policy_id'] != NATIVE_POLICY or review['policy_id'] != NATIVE_POLICY
            or review['analysis_completed'] is not True or review['pair_sum_and_gradient_replay'] is not True
            or review['fixed_manager_repeats'] is not True or review['geometry_accepted'] is not False):
        raise ValueError('Require replayed directed native evidence without geometry approval')
    rows = review['measurements']
    if len(rows) != len(inventory['pairs']) or review['pair_count'] != len(rows):
        raise ValueError('Native pair inventory differs from reviewed rows')
    mappings = {}
    for atom,image,r,t,_ in inventory['mappings']:
        if (atom,image) in mappings:
            raise ValueError('Duplicate captured image mapping')
        mappings[atom,image] = _operation(r,t)
    grouped = defaultdict(list)
    for index,row in enumerate(rows):
        kind,i,j,image,vdw = inventory['pairs'][index]
        if (row['proxy_index'] != index or row['kind'] != kind or row['i_seqs'] != [i,j]
                or row['image_j'] != image or row['atoms'] != [labels[i],labels[j]] or row['vdw_distance'] != vdw):
            raise ValueError('Reviewed row no longer binds its captured native pair')
        operation = _relative(_IDENTITY,_IDENTITY) if kind == 'simple' else _relative(mappings[i,0],mappings[j,image])
        distance,overlap,residual,weight = (_number(row[k]) for k in ('distance','overlap','residual','residual_weight'))
        if distance < 0 or residual < 0 or weight <= 0 or abs((vdw-distance)-overlap)>1e-8:
            raise ValueError('Inconsistent native pair measurement')
        # Retain direction and kind; reciprocal rows and native multiplicity are not discarded.
        grouped[(kind,labels[i],labels[j],*operation)].append(dict(proxy_index=index,image_j=image,
            distance=distance,overlap=overlap,vdw_distance=vdw,residual=residual,residual_weight=weight))
    result = {}
    for key,values in grouped.items():
        first=values[0]
        if any(abs(v[k]-first[k])>1e-8 for v in values for k in ('distance','overlap','vdw_distance')):
            raise ValueError('One atom/image identity has inconsistent native measurements')
        result[key] = dict(kind=key[0],atoms=list(key[1:3]),fractional_operation=dict(rotation=list(key[3]),translation=[str(v) for v in key[4]]),
            distance=first['distance'],overlap=first['overlap'],vdw_distance=first['vdw_distance'],
            residual=math.fsum(v['residual'] for v in values),multiplicity=len(values),
            residual_weights=sorted(v['residual_weight'] for v in values),directed_rows=values)
    if not math.isclose(math.fsum(v['residual'] for v in result.values()),_number(review['total_residual']),abs_tol=1e-7,rel_tol=1e-10):
        raise ValueError('Grouped native contributions do not reproduce the reviewed total')
    return result


def compare_native_packing(before, after, *, reviewer):
    """Report all directed before/after pairs under one unchanged native policy.

    Captured neighbor membership may change with coordinates. Missing rows are
    reported separately, never interpreted as resolved clashes. Scientific
    acceptance thresholds and physical partner choice remain outside this API.
    """
    try:
        contexts = ('installed_api_sources','restraint_policy','parameter_consumers','phil_adaptations')
        if any(before[k] != after[k] for k in contexts):
            raise ValueError('Native interpretation contexts differ')
        if [a['label'] for a in before['atoms']] != [a['label'] for a in after['atoms']]:
            raise ValueError('Captured atom identities/order differ')
        if before['geometry']['proxy_details'] != after['geometry']['proxy_details']:
            raise ValueError('Static native restraint definitions differ')
        bq,aq = before['nonbonded_inventory'],after['nonbonded_inventory']
        if bq['unit_cell'] != aq['unit_cell'] or bq['function_parameters'] != aq['function_parameters']:
            raise ValueError('Native cell or nonbonded function differs')
        reviews = (reviewer(before),reviewer(after))
        b,a = _groups(before,reviews[0]),_groups(after,reviews[1])
        common=[]
        for key in sorted(b.keys() & a.keys()):
            old,new=b[key],a[key]
            if old['vdw_distance'] != new['vdw_distance']:
                raise ValueError('Native VDW distance changed for a matched atom/image pair')
            common.append(dict(before=old,after=new,overlap_change=new['overlap']-old['overlap'],
                positive_overlap_change=max(0.,new['overlap'])-max(0.,old['overlap']),
                residual_change=new['residual']-old['residual'],
                multiplicity_unchanged=old['residual_weights']==new['residual_weights']))
        added=[a[k] for k in sorted(a.keys()-b.keys())]
        removed=[b[k] for k in sorted(b.keys()-a.keys())]
        worsened=[r for r in common if r['positive_overlap_change']>1e-9]
        return dict(schema_version=1,kind='topostitch-native-packing-comparison',policy_id=POLICY,
            input_native_sha256=dict(before=_digest(before),after=_digest(after)),
            unchanged_native_context=True,common_pairs=common,added_pairs=added,removed_pairs=removed,
            summary=dict(directed_rows_before=reviews[0]['pair_count'],directed_rows_after=reviews[1]['pair_count'],
                native_residual_before=reviews[0]['total_residual'],native_residual_after=reviews[1]['total_residual'],
                common_identity_count=len(common),added_identity_count=len(added),removed_identity_count=len(removed),
                worsened_existing_overlap_count=len(worsened),
                newly_overlapping_existing_count=sum(r['before']['overlap']<=0<r['after']['overlap'] for r in common),
                newly_listed_overlapping_count=sum(r['overlap']>0 for r in added),
                multiplicity_changes=sum(not r['multiplicity_unchanged'] for r in common)),
            worst_existing_overlap_increases=sorted(worsened,key=lambda r:-r['positive_overlap_change'])[:20],
            runtime_authority=False,geometry_accepted=False,automatic_adoption=False,
            limitations=['Caller must authenticate both captures through Cedar; input hashes do not replace receipt validation.',
                'Directed native multiplicity is retained; counts are not counts of unique physical contacts or a MolProbity clashscore.',
                'Only the captured native neighbor/exclusion policy is compared; no independent neighbor enumeration or chemistry approval.',
                'Standard-cell integer rotations and translations with denominator at most 24 only; lattice translations are never wrapped.',
                'No torsion/plane comparison, optimizer, refinement or model publication.'])
    except (KeyError,IndexError,TypeError,OverflowError) as exc:
        raise ValueError('Incomplete native packing comparison evidence') from exc
