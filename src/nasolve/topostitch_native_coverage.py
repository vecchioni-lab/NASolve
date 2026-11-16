"""Optional callback-free native inventory observation for pair coverage.

Cedar owns native API qualification and exclusion/symmetry policy observation.
The caller supplies its trusted, checksum-bound policy owner and frozen context.
Nothing here chooses partners, approves exclusions or activates forces.
"""
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path

from .topostitch_pair_coverage import (_context,
    _digest, _inventory, _need, _MAX_TERMS)
from .topostitch_recipe import recipe_digest


def _native_api():
    from mmtbx.model import manager as Model
    from cctbx import geometry_restraints as gr, sgtbx
    from cctbx.geometry_restraints.flags import flags
    from .topostitch_native_recipe import native_atom_identities
    return dict(Model=Model, gr=gr, Operation=sgtbx.rt_mx, flags=flags,
                identities=native_atom_identities)


def _exact_image(operation):
    rotation = [Fraction(v, operation.r().den()) for v in operation.r().num()]
    translation = [Fraction(v, operation.t().den()) for v in operation.t().num()]
    _need(len(rotation) == 9 and len(translation) == 3
          and all(v.denominator == 1 for v in rotation), 'Unsupported native fractional image')
    # Membership identifies a group coset; returned declarations retain the full image.
    key = tuple(rotation), tuple(v % 1 for v in translation)
    return key, dict(rotation=[int(v) for v in rotation], translation=[str(v) for v in translation])


def _read_terms(geo, sites, labels, api):
    gr, Operation = api['gr'], api['Operation']
    group = {_exact_image(op)[0] for op in geo.crystal_symmetry.space_group()}
    rows = []; origins = []
    def atom(index, operation):
        _need(type(index) is int and 0 <= index < len(labels), 'Invalid native proxy atom index')
        _need(type(operation) is Operation, 'Unsupported native image type')
        key, image = _exact_image(operation)
        _need(key in group, 'Native proxy image is outside the qualified crystal group')
        return dict(atom=labels[index], **image)
    def emit(category, ordinal, kind, proxy, indices, others, operations):
        _need(len(rows) < _MAX_TERMS and len(indices)+len(others) <= 64,
              'Native inventory allowance exceeded')
        _need(len(operations) == len(indices)+len(others), 'Incomplete native per-atom images')
        a = [atom(i, op) for i, op in zip(indices, operations)]
        b = [atom(i, op) for i, op in zip(others, operations[len(indices):])]
        if kind == 'planarity':
            parameters = dict(weights=list(proxy.weights))
        else:
            field = {'bond':'distance_ideal', 'angle':'angle_ideal',
                     'parallelity':'target_angle_deg'}[kind]
            parameters = dict(ideal=getattr(proxy, field), weight=proxy.weight, slack=proxy.slack)
            if kind in ('bond', 'parallelity'):
                parameters.update(limit=proxy.limit, top_out=proxy.top_out)
        origin = proxy.origin_id
        _need(type(origin) is int and origin >= 0, 'Invalid native proxy origin')
        origins.append(origin)
        rows.append(dict(term_id=category+':'+str(ordinal), kind=kind,
                         atoms=a, other_atoms=b, parameters=parameters))
    bonds = geo.pair_proxies(sites_cart=sites).bond_proxies
    for category, proxies, expected in (
            ('bond_simple', bonds.simple, gr.bond_simple_proxy),
            ('bond_asu', bonds.asu, gr.bond_asu_proxy)):
        _need(len(proxies) <= _MAX_TERMS, 'Native bond allowance exceeded')
        for n, proxy in enumerate(proxies):
            _need(type(proxy) is expected, 'Unsupported native bond proxy type')
            if category == 'bond_simple':
                indices = list(proxy.i_seqs); image = proxy.rt_mx_ji
            else:
                indices = [proxy.i_seq, proxy.j_seq]
                image = bonds.asu_mappings().get_rt_mx_ji(pair=proxy)
            emit(category, n, 'bond', proxy, indices, [],
                 [Operation('x,y,z'), Operation('x,y,z') if image is None else image])
    for kind in ('angle', 'planarity', 'parallelity'):
        proxies = getattr(geo, kind+'_proxies')
        if proxies is None:
            continue
        _need(len(proxies) <= _MAX_TERMS, 'Native family allowance exceeded')
        for n, proxy in enumerate(proxies):
            _need(type(proxy) is getattr(gr, kind+'_proxy'), 'Unsupported native '+kind+' proxy type')
            indices = list(proxy.i_seqs)
            others = list(proxy.j_seqs) if kind == 'parallelity' else []
            sym = proxy.sym_ops
            operations = ([Operation('x,y,z')]*(len(indices)+len(others))
                          if sym is None or len(sym) == 0 else list(sym))
            emit(kind, n, kind, proxy, indices, others, operations)
    _inventory(rows, set(labels))
    return rows, origins


def observe_native_pair_terms(model, *, frozen_context, frozen_policy,
                              policy_owner, expected_policy_owner_sha256):
    """Observe complete supported native families against a callback-free policy.

    ``policy_owner`` is the caller's trusted Cedar live-policy module, qualified
    against its frozen source digest. Its require function authenticates the
    actual manager API/profile and compares frozen exclusions/symmetry before and
    after reading. It must retain the C331 callback-free contract. Caller-supplied
    source/recipe provenance is not independently established by this observer.

    Pair-cache refresh may occur, but no forces, coordinates or policy are changed.
    Single-owner access is required; two inventory reads detect drift, not races.
    The result is observation evidence, never a normalization count or activation.
    """
    try:
        context, baseline = json.loads(json.dumps([frozen_context, frozen_policy], allow_nan=False))
        _context(context)
        owner_path = Path(policy_owner.__file__)
        _need(_digest(expected_policy_owner_sha256)
              and sha256(owner_path.read_bytes()).hexdigest() == expected_policy_owner_sha256,
              'Changed native policy owner source')
        _need(baseline['policy_sha256'] == context['native_exclusion_policy_sha256'],
              'Changed frozen native policy context')
        api = _native_api()
        _need(type(model) is api['Model'], 'Unsupported native model type')
        geo = model.restraints_manager.geometry
        options = dict(flags=api['flags'](default=True), normalization=False,
                       compute_gradients=False, gradients=None, disable_asu_cache=False,
                       custom_nonbonded_function=None, external_energy_function=None, extension_objects=())
        observed = policy_owner.require_live_nonbonded_policy(geo, baseline, **options)
        symmetry = observed['policy']['symmetry']
        _need(recipe_digest(symmetry) == context['crystal_sha256'], 'Changed native crystal context')
        _need(all(len(row['matrices']) == 1 for row in symmetry['site_table']),
              'Special-position pair coverage is not qualified')
        identities = api['identities'](model.get_hierarchy())
        labels = [json.dumps(row, sort_keys=True, separators=(',', ':')) for row in identities]
        _need(labels == context['atom_labels'], 'Changed native atom order or identity')
        sites = model.get_sites_cart()
        points = list(sites)
        _need(len(points) == len(labels) == len(symmetry['site_indices'])
              and all(len(p) == 3 and all(math.isfinite(v) for v in p) for p in points),
              'Incomplete native coordinate inventory')
        terms, origins = _read_terms(geo, sites, labels, api)
        _need((terms, origins) == _read_terms(geo, sites, labels, api),
              'Native term inventory changed during observation')
        policy_owner.require_live_nonbonded_policy(geo, baseline, **options)
        _need(model.restraints_manager.geometry is geo and list(model.get_sites_cart()) == points
              and api['identities'](model.get_hierarchy()) == identities
              and sha256(owner_path.read_bytes()).hexdigest() == expected_policy_owner_sha256,
              'Native observation context changed')
        return dict(policy_id='topostitch-native-pair-observation-v1', context=context,
            policy_owner_sha256=expected_policy_owner_sha256, terms=terms, origin_ids=origins,
            terms_sha256=recipe_digest(terms), points_sha256=recipe_digest(points),
            runtime_authority=False, scientific_acceptance=False)
    except (KeyError, TypeError, AttributeError, IndexError, OverflowError, OSError) as exc:
        raise ValueError('Incomplete native pair observation') from exc
