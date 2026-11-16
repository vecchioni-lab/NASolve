"""Read-only live native nonbonded inputs, separate from pair/chemistry approval.

Only the packaged native API profile is supported. File qualification is cached
once per process; the enclosing native owner still authenticates source lifetime,
atom identity, other forces and actual evaluation/cache behavior. This module
never evaluates energy, generates neighbours, copies a native manager or changes
its state. Snapshots are observations, not permission to copy geometry objects.
"""
from functools import lru_cache
import hashlib
import importlib
import json
import math
from pathlib import Path
import platform

POLICY_ID = 'cif-live-nonbonded-policy-v1'
PROFILE_ID = 'phenix-2.2.1-6174-darwin-arm64-nonbonded-v1'
MAX_ATOMS = 10000
MAX_ITEMS = 100000
MAX_BYTES = 16 * 1024 * 1024
MAX_NODES = 1000000
PARAMETER_SCALARS = ('factor_1_4_interactions', 'const_shrink_1_4_interactions',
    'default_distance', 'minimum_distance', 'const_shrink_donor_acceptor')
PARAMETER_TABLES = ('radius_table', 'ionic_radius_table', 'donor_acceptor_table')
FUNCTION_FIELDS = ('c_rep', 'k_rep', 'irexp', 'rexp')
ASSIGNMENT_FIELDS = ('model_indices', 'conformer_indices', 'sym_excl_indices',
    'donor_acceptor_excl_groups', 'nonbonded_types', 'nonbonded_charges')
FLAG_FIELDS = ('bond', 'nonbonded', 'angle', 'dihedral', 'reference_coordinate',
    'reference_dihedral', 'ncs_dihedral', 'den_restraints', 'chirality',
    'planarity', 'parallelity', 'bond_similarity', 'ramachandran_restraints')
SEARCH_FIELDS = ('nonbonded_distance_cutoff', 'nonbonded_buffer',
    'min_cubicle_edge', 'plain_pairs_radius', 'max_reasonable_bond_distance')
CACHE_FIELDS = ('adjusted_nonbonded_distance_cutoff', 'effective_nonbonded_buffer',
    'n_updates_pair_proxies', 'nonbonded_distance_cutoff_was_determined_automatically')


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Require finite native policy numbers')
    return float(value)


def _integer(value, *, minimum=None, maximum=None):
    if (type(value) is not int or abs(value) > 2**63 - 1
            or (minimum is not None and value < minimum)
            or (maximum is not None and value > maximum)):
        raise ValueError('Invalid native policy integer/index')
    return value


def _boolean(value):
    if type(value) is not bool:
        raise ValueError('Require resolved boolean evaluation settings')
    return value


def _text(value):
    if type(value) is not str or len(value.encode('utf-8')) > 256:
        raise ValueError('Require bounded native type/map keys')
    return value


def _encoded(value):
    # Bound traversal before JSON encoding, including cycles/deep nested inputs.
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > 32:
            raise ValueError('Native policy primitive bounds exceeded')
        if type(item) in (dict, list):
            if len(item) > MAX_ITEMS or len(pending) + nodes + len(item) > MAX_NODES:
                raise ValueError('Native policy collection bounds exceeded')
            if type(item) is dict:
                for key in item:
                    _text(key)
                children = item.values()
            else:
                children = item
            pending.extend((child, depth + 1) for child in children)
        elif type(item) is str:
            _text(item)
        elif item is None or type(item) is bool:
            pass
        elif type(item) is int:
            _integer(item)
        elif type(item) is float:
            _number(item)
        else:
            raise ValueError('Require detached JSON policy primitives')
    return _json_bytes(value)


def _json_bytes(value):
    """Encode already-validated primitives without repeating their tree walk."""
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(raw) > MAX_BYTES:
        raise ValueError('Native policy byte bound exceeded')
    return raw


def _qualify_modules(profile):
    if (profile['profile_id'] != PROFILE_ID or profile['system'] != platform.system()
            or profile['machine'] != platform.machine()):
        raise ValueError('Unsupported live nonbonded native platform/profile')
    modules = {}
    for name, expected in profile['modules'].items():
        module = importlib.import_module(name)
        path = Path(module.__file__)
        if path.stat().st_size != expected['size']:
            raise ValueError('Unsupported native source: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != expected['sha256']:
            raise ValueError('Unsupported native source: ' + name)
        modules[name] = module
    return modules


@lru_cache(maxsize=1)
def _native_types():
    """Qualify the installed API once; no host path is part of the profile."""
    try:
        profile = json.loads((Path(__file__).parent / 'data' / 'nonbonded-native-profile.json').read_text())
        _qualify_modules(profile)
        from cctbx import crystal, geometry_restraints as gr, sgtbx
        from cctbx.array_family import flex
        from cctbx.geometry_restraints.manager import manager
        from cctbx.geometry_restraints.flags import flags
        params = gr.nonbonded_params()
        return dict(manager=manager, params=gr.nonbonded_params,
            function=gr.prolsq_repulsion_function, flags=flags,
            crystal=(crystal.symmetry, crystal.special_position_settings),
            site_table=sgtbx.site_symmetry_table, site_ops=sgtbx.site_symmetry_ops,
            shell=crystal.pair_sym_table, operation=sgtbx.rt_mx,
            scalar_map=type(params.radius_table), nested_map=type(params.distance_table),
            pair_map=type(crystal.pair_sym_table(1)[0]),
            indices=flex.size_t, charges=flex.int, types=flex.std_string)
    except (ImportError, OSError, KeyError, AttributeError, TypeError) as exc:
        raise ValueError('Supported live nonbonded native API unavailable') from exc


class _Reader:
    def __init__(self, types):
        self.types = types
        self.remaining = MAX_ITEMS

    def count(self, values, maximum=MAX_ITEMS):
        count = len(values)
        if count > maximum or count > self.remaining:
            raise ValueError('Native policy item bound exceeded')
        self.remaining -= count
        return count

    def exact(self, value, name):
        expected = self.types[name]
        accepted = expected if type(expected) is tuple else (expected,)
        if type(value) not in accepted:
            raise ValueError('Unsupported native policy type: ' + name)

    def mapping(self, value, *, nested=False):
        self.exact(value, 'nested_map' if nested else 'scalar_map')
        self.count(value)
        # Native maps are unique-key maps, but retain empty nested maps explicitly.
        return {_text(key): self.mapping(row) if nested else _number(row)
                for key, row in sorted(value.items())}

    def operation(self, value):
        self.exact(value, 'operation')
        self.remaining -= 1
        if self.remaining < 0:
            raise ValueError('Native symmetry operation bound exceeded')
        def rational(part, size):
            nums = list(part.num())
            if len(nums) != size:
                raise ValueError('Incomplete rational symmetry operation')
            return [[_integer(n) for n in nums], _integer(part.den(), minimum=1)]
        # special_op can be a singular projection, not a proper rotation.
        return dict(rotation=rational(value.r(), 9), translation=rational(value.t(), 3))

    def shells(self, shells, count):
        self.count(shells, 32)
        if not len(shells):
            raise ValueError('Require complete native exclusion shells')
        result = []
        for shell in shells:
            self.exact(shell, 'shell')
            if self.count(shell) != count:
                raise ValueError('Exclusion shell/atom count differs')
            rows = []
            for row in shell:
                self.exact(row, 'pair_map')
                self.count(row)
                entries = []
                for partner, ops in sorted(row.items()):
                    op_count = self.count(ops)
                    # Indexed access avoids a costly Boost.Python iterator stop
                    # for every (often single-operation) shell entry.
                    entries.append([_integer(partner, minimum=0, maximum=count-1),
                                    [self.operation(ops[i]) for i in range(op_count)]])
                rows.append(entries)
            result.append(rows)
        return result

    def symmetry(self, crystal, table, count):
        # Initial qualification covers crystallographic managers only.
        self.exact(crystal, 'crystal')
        self.exact(table, 'site_table')
        cell = list(crystal.unit_cell().parameters())
        if len(cell) != 6:
            raise ValueError('Incomplete native unit cell')
        indices, entries = table.indices(), table.table()
        if self.count(indices) != count or not self.count(entries):
            raise ValueError('Incomplete site-symmetry assignments')
        group = crystal.space_group()
        self.count(group, 384)
        table_rows = []
        for entry in entries:
            self.exact(entry, 'site_ops')
            matrices = entry.matrices()
            self.count(matrices, 384)
            table_rows.append(dict(matrices=[self.operation(op) for op in matrices],
                special_op=self.operation(entry.special_op()),
                multiplicity=_integer(entry.multiplicity(), minimum=1)))
        return dict(cell=[_number(v) for v in cell],
            group=[self.operation(op) for op in group],
            site_indices=[_integer(i, minimum=0, maximum=len(entries)-1) for i in indices],
            site_table=table_rows)


def _cache_observations(geo):
    return dict(adjusted_nonbonded_distance_cutoff=_number(geo.adjusted_nonbonded_distance_cutoff),
        effective_nonbonded_buffer=_number(geo.effective_nonbonded_buffer),
        n_updates_pair_proxies=_integer(geo.n_updates_pair_proxies, minimum=0),
        nonbonded_distance_cutoff_was_determined_automatically=
            _boolean(geo.nonbonded_distance_cutoff_was_determined_automatically))


def snapshot_live_nonbonded_policy(geo, *, flags, normalization,
        compute_gradients=False, disable_asu_cache=False, gradients=None,
        custom_nonbonded_function=None, external_energy_function=None,
        extension_objects=()):
    """Observe supported fixed inputs without evaluating or warming the manager.

    Pass the SAME flags/options as the actual native evaluation. Configured
    cutoff must already be numeric. Custom functions, extension energies and
    supplied gradient buffers are unsupported; absence never triggers a fallback.
    Working cache fields are recorded separately and do not enter policy equality.
    """
    try:
        reader = _Reader(_native_types())
        reader.exact(geo, 'manager')
        reader.exact(flags, 'flags')
        if (gradients is not None or custom_nonbonded_function is not None
                or external_energy_function is not None or geo.external_energy_function is not None
                or type(extension_objects) not in (tuple, list) or len(extension_objects)):
            raise ValueError('Unsupported custom live nonbonded evaluation settings')
        if any(name in vars(geo) for name in ('pair_proxies', 'energies_sites')):
            raise ValueError('Overridden native manager evaluation is unsupported')
        if geo.nonbonded_distance_cutoff is None:
            raise ValueError('Require an already resolved configured nonbonded cutoff')
        reader.exact(geo.nonbonded_params, 'params')
        reader.exact(geo.nonbonded_function, 'function')
        reader.exact(geo.nonbonded_types, 'types')
        count = reader.count(geo.nonbonded_types, MAX_ATOMS)
        if not count:
            raise ValueError('Require nonempty native atom/type assignments')
        assignments = {}
        for name in ASSIGNMENT_FIELDS:
            values = getattr(geo, name)
            if values is None:
                assignments[name] = None
                continue
            kind = 'types' if name == 'nonbonded_types' else 'charges' if name == 'nonbonded_charges' else 'indices'
            reader.exact(values, kind)
            size = reader.count(values, MAX_ATOMS)
            if size != count and (name == 'nonbonded_types' or size != 0):
                raise ValueError('Native assignment/atom count differs: ' + name)
            assignments[name] = [_text(v) if kind == 'types' else
                _integer(v, minimum=None if kind == 'charges' else 0) for v in values]
        p = geo.nonbonded_params
        parameters = {name: _number(getattr(p, name)) for name in PARAMETER_SCALARS}
        parameters.update({name: reader.mapping(getattr(p, name)) for name in PARAMETER_TABLES})
        parameters['distance_table'] = reader.mapping(p.distance_table, nested=True)
        policy = dict(parameters=parameters, assignments=assignments,
            function={name: _number(getattr(geo.nonbonded_function, name)) for name in FUNCTION_FIELDS},
            shells=reader.shells(geo.shell_sym_tables, count),
            symmetry=reader.symmetry(geo.crystal_symmetry, geo.site_symmetry_table, count),
            search={name: None if name in SEARCH_FIELDS[3:] and getattr(geo, name) is None
                    else _number(getattr(geo, name)) for name in SEARCH_FIELDS},
            invocation=dict(flags={name: _boolean(getattr(flags, name)) for name in FLAG_FIELDS},
                normalization=_boolean(normalization), compute_gradients=_boolean(compute_gradients),
                disable_asu_cache=_boolean(disable_asu_cache), gradients=None,
                custom_nonbonded_function=None, external_energy_function=None, extension_objects=[]))
        snapshot = dict(schema_version=1, policy_id=POLICY_ID, native_profile_id=PROFILE_ID,
            policy=policy, policy_sha256=hashlib.sha256(_encoded(policy)).hexdigest(),
            cache_observations=_cache_observations(geo))
        # Policy was traversed above; envelope/cache fields have explicit validators.
        _json_bytes(snapshot)
        return snapshot
    except (AttributeError, TypeError, OverflowError, IndexError) as exc:
        raise ValueError('Incomplete or malformed live nonbonded policy') from exc


def require_live_nonbonded_policy(geo, expected, **evaluation_options):
    """Compare against a frozen primitive baseline; never replace it on mismatch.

    Policy SHA256 detects accidental edits; it is not an authenticity credential.
    The caller owns baseline selection and before/after evaluation placement.
    This comparison does not validate generated cache contents or other forces.
    """
    _encoded(expected)
    keys = {'schema_version', 'policy_id', 'native_profile_id', 'policy',
            'policy_sha256', 'cache_observations'}
    if (type(expected) is not dict or set(expected) != keys
            or type(expected['schema_version']) is not int or expected['schema_version'] != 1
            or expected['policy_id'] != POLICY_ID or expected['native_profile_id'] != PROFILE_ID
            or type(expected['policy']) is not dict
            or hashlib.sha256(_json_bytes(expected['policy'])).hexdigest() != expected['policy_sha256']):
        raise ValueError('Invalid live nonbonded policy baseline or digest')
    cache = expected['cache_observations']
    if type(cache) is not dict or set(cache) != set(CACHE_FIELDS):
        raise ValueError('Invalid native cache observations')
    _number(cache['adjusted_nonbonded_distance_cutoff'])
    _number(cache['effective_nonbonded_buffer'])
    _integer(cache['n_updates_pair_proxies'], minimum=0)
    _boolean(cache['nonbonded_distance_cutoff_was_determined_automatically'])
    current = snapshot_live_nonbonded_policy(geo, **evaluation_options)
    if current['policy_sha256'] != expected['policy_sha256']:
        changed = sorted(k for k in set(current['policy']) | set(expected['policy'])
                         if _json_bytes(current['policy'].get(k)) != _json_bytes(expected['policy'].get(k)))
        raise ValueError('Live nonbonded policy changed: ' + ', '.join(changed))
    return current
