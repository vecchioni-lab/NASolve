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
    from cctbx import geometry_restraints as gr, sgtbx, xray
    from cctbx.geometry_restraints.flags import flags
    from .topostitch_native_recipe import native_atom_identities
    return dict(Model=Model, XrayStructure=xray.structure, gr=gr, Operation=sgtbx.rt_mx, flags=flags,
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


def _model_state(model, geo, api, owner, expected_sha256):
    """Read both representations through the existing trusted Cedar output owner.

    Keep exact fractional sites in addition to Cedar's Cartesian scattering view.
    Never synchronize ADPs or set coordinates: differences remain observations.
    """
    _need(_digest(expected_sha256)
          and sha256(Path(owner.__file__).read_bytes()).hexdigest() == expected_sha256,
          'Changed native state owner source')
    _need(owner.POLICY_ID == 'native-refinement-output-state-v1',
          'Unsupported native state owner policy')
    xrs = model.get_xray_structure()
    _need(type(xrs) is api['XrayStructure'], 'Unsupported native scattering structure')
    _need(list(xrs.unit_cell().parameters()) == list(geo.crystal_symmetry.unit_cell().parameters())
          and {_exact_image(op)[0] for op in xrs.space_group()}
              == {_exact_image(op)[0] for op in geo.crystal_symmetry.space_group()},
          'Scattering and geometry crystal contexts differ')
    hierarchy = owner._hierarchy(model)
    scattering, projected = owner._scattering(xrs)
    fractional, force_sites = list(xrs.sites_frac()), list(xrs.sites_cart())
    count = len(hierarchy)
    _need(count > 0 and len(scattering['atoms']) == len(projected) == len(fractional)
          == len(force_sites) == len(model.get_sites_cart()) == count,
          'Incomplete dual native atom state')
    _need(all(len(p) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in p)
              for p in fractional + force_sites), 'Nonfinite native coordinate state')
    _need([row['xyz'] for row in hierarchy] == [list(p) for p in model.get_sites_cart()]
          and [row['xyz'] for row in projected] == [list(p) for p in force_sites],
          'Native coordinate views differ from their owner observations')
    # Reuse the output owner's representation-agreement tolerance. Stale ADPs
    # are recorded separately; all other ordered atom fields must still agree.
    stable = lambda rows: [{k:v for k,v in row.items() if k not in ('b', 'uij')} for row in rows]
    _need(owner._close(stable(hierarchy), stable(projected)),
          'Hierarchy and scattering atom states differ beyond ADPs')
    state = dict(hierarchy=hierarchy, scattering=scattering,
                 fractional_sites=fractional, force_sites=force_sites)
    state = json.loads(json.dumps(state, allow_nan=False))
    return xrs, state, dict(policy_id='topostitch-dual-native-state-v1',
        state_owner_policy_id=owner.POLICY_ID, state_owner_sha256=expected_sha256,
        atom_count=count, hierarchy_sha256=recipe_digest(state['hierarchy']),
        scattering_sha256=recipe_digest(state['scattering']),
        fractional_sites_sha256=recipe_digest(state['fractional_sites']),
        force_sites_sha256=recipe_digest(state['force_sites']))


def observe_native_pair_terms(model, *, frozen_context, frozen_policy,
                              policy_owner, expected_policy_owner_sha256,
                              state_owner=None, expected_state_owner_sha256=None):
    """Observe complete supported native families against a callback-free policy.

    ``policy_owner`` is the caller's trusted Cedar live-policy module, qualified
    against its frozen source digest. Its require function authenticates the
    actual manager API/profile and compares frozen exclusions/symmetry before and
    after reading. It must retain the C331 callback-free contract. Caller-supplied
    source/recipe provenance is not independently established by this observer.

    Opt in to a v2 observation by supplying the trusted Cedar output-state owner
    and its frozen source digest together. Reuse its hierarchy/scattering readers,
    also bind exact fractional and actual force sites, and check state before/after.
    Omission retains the original v1 record and hierarchy-based cache observation.
    This neither synchronizes state nor qualifies an active contribution owner.

    Pair-cache refresh may occur, but no forces, coordinates or policy are changed.
    Single-owner access is required; two inventory reads detect drift, not races.
    The result is observation evidence, never a normalization count or activation.
    """
    try:
        dual = state_owner is not None or expected_state_owner_sha256 is not None
        _need(not dual or (state_owner is not None and expected_state_owner_sha256 is not None),
              'Require native state owner and frozen source digest together')
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
        if dual:
            xrs, state, state_record = _model_state(model, geo, api, state_owner, expected_state_owner_sha256)
            sites = xrs.sites_cart()
        terms, origins = _read_terms(geo, sites, labels, api)
        _need((terms, origins) == _read_terms(geo, sites, labels, api),
              'Native term inventory changed during observation')
        policy_owner.require_live_nonbonded_policy(geo, baseline, **options)
        _need(model.restraints_manager.geometry is geo and list(model.get_sites_cart()) == points
              and api['identities'](model.get_hierarchy()) == identities
              and sha256(owner_path.read_bytes()).hexdigest() == expected_policy_owner_sha256,
              'Native observation context changed')
        if dual:
            current_xrs, current_state, current_record = _model_state(
                model, geo, api, state_owner, expected_state_owner_sha256)
            _need(current_xrs is xrs and current_state == state and current_record == state_record,
                  'Native scattering or hierarchy state changed during observation')
        result = dict(policy_id='topostitch-native-pair-observation-v2' if dual
                      else 'topostitch-native-pair-observation-v1', context=context,
            policy_owner_sha256=expected_policy_owner_sha256, terms=terms, origin_ids=origins,
            terms_sha256=recipe_digest(terms), points_sha256=recipe_digest(points),
            runtime_authority=False, scientific_acceptance=False)
        if dual:
            result['native_state'] = state_record
        return result
    except (KeyError, TypeError, AttributeError, IndexError, OverflowError, OSError) as exc:
        raise ValueError('Incomplete native pair observation') from exc
