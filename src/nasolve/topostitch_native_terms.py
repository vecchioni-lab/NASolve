"""Read-only live native torsion/plane observations through maintained kernels.

Cedar owns the numerical kernels. This adapter verifies that complete live proxy
semantics fit those kernels before comparing them with original native objects.
No proxy, weight, gradient, model or chemical acceptance policy is changed.
"""
from copy import deepcopy
import math

from .topostitch_recipe import recipe_digest

KINDS = ('dihedral', 'planarity')
MAX_TERMS = 5000


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _close(a, b):
    return _finite(a) and _finite(b) and math.isclose(a, b, abs_tol=1e-8, rel_tol=1e-10)


def _vector(a, b):
    if len(a) != len(b) or not all(_finite(v) for v in (*a, *b)):
        return False
    error = math.dist(a, b); scale = max(1., math.hypot(*a), math.hypot(*b))
    return math.isfinite(error) and math.isfinite(scale) and error <= 1e-8 + 1e-10 * scale


def checked_proxy_rows(geometry, native):
    """Check live semantics absent from the historical descriptive inventory.

    A capture's simple parameter rows do not establish identity symmetry or the
    absence of torsion slack/top-out. Inspect the live objects, never infer them.
    """
    result = {}
    count = native['atom_count']; atoms = native['atoms']
    if type(count) is not int or count != len(atoms) or count < 1:
        raise ValueError('Incomplete native atom inventory')
    if any(a['i_seq'] != i for i, a in enumerate(atoms)):
        raise ValueError('Native atom ordering differs')
    total = 0
    for kind in KINDS:
        proxies = getattr(geometry, kind + '_proxies')
        proxies = [] if proxies is None else proxies
        rows = native['geometry']['proxy_details'][kind]
        if len(proxies) != len(rows) or native['geometry']['proxy_counts'][kind] != len(rows):
            raise ValueError('Live and captured native proxy inventories differ')
        total += len(rows)
        if total > MAX_TERMS:
            raise ValueError('Native term observation budget exceeded')
        checked = []
        for proxy, row in zip(proxies, rows):
            fields = ({'i_seqs', 'atoms', 'angle_ideal', 'weight', 'periodicity', 'alt_angle_ideals', 'origin_id'}
                      if kind == 'dihedral' else {'i_seqs', 'atoms', 'weights', 'origin_id'})
            if set(row) != fields:
                raise ValueError('Unsupported captured native term fields')
            ids = row['i_seqs']
            if (not isinstance(ids, list) or len(set(ids)) != len(ids)
                    or any(type(i) is not int or not 0 <= i < count for i in ids)
                    or (len(ids) != 4 if kind == 'dihedral' else len(ids) < 3)
                    or row['atoms'] != [atoms[i]['label'] for i in ids]
                    or type(row['origin_id']) is not int):
                raise ValueError('Incomplete native term atom binding')
            required = (fields - {'atoms'}) | {'sym_ops'}
            if kind == 'dihedral':
                required |= {'limit', 'top_out', 'slack'}
            if any(not hasattr(proxy, name) for name in required):
                raise ValueError('Live native proxy API omits required policy fields')
            actual = dict(i_seqs=list(proxy.i_seqs), atoms=row['atoms'], origin_id=int(proxy.origin_id))
            # Missing properties are unsupported, not assumed to be defaults.
            operations = proxy.sym_ops
            operations = None if operations is None else [op.as_xyz() for op in operations]
            if operations is not None and (len(operations) != len(ids) or any(op != 'x,y,z' for op in operations)):
                raise ValueError('Native term observation requires identity-only proxy images')
            policy = dict(symmetry_operations=operations)
            if kind == 'dihedral':
                actual.update(angle_ideal=float(proxy.angle_ideal), weight=float(proxy.weight),
                              periodicity=int(proxy.periodicity),
                              alt_angle_ideals=None if proxy.alt_angle_ideals is None else list(proxy.alt_angle_ideals))
                policy.update(limit=float(proxy.limit), top_out=proxy.top_out, slack=float(proxy.slack))
                if policy['limit'] != -1. or policy['top_out'] is not False or policy['slack'] != 0.:
                    raise ValueError('Unsupported native torsion limit, top-out or slack')
                alt = row['alt_angle_ideals']
                if (not _finite(row['angle_ideal']) or not _finite(row['weight']) or row['weight'] < 0
                        or type(row['periodicity']) is not int
                        or alt is not None and (not isinstance(alt, list) or len(alt) > 6 or any(not _finite(v) for v in alt))):
                    raise ValueError('Unsupported native torsion parameters')
            else:
                actual['weights'] = list(proxy.weights)
                if len(row['weights']) != len(ids) or any(not _finite(v) or v <= 0 for v in row['weights']):
                    raise ValueError('Require finite positive complete plane weights')
            if actual != row:
                raise ValueError('Live native term differs from captured definition')
            checked.append(dict(definition=deepcopy(row), live_policy=policy))
        result[kind] = checked
    return result


class NativeTermObserver:
    """Use original live proxies and Cedar kernels, with full family sum checks."""
    def __init__(self, geometry, native, moving_indices, *, gr, flex,
                 torsion_evaluate, plane_evaluate, torsion_geometry):
        self.geometry = geometry
        self.native = deepcopy({k:native[k] for k in ('atom_count', 'atoms', 'geometry')})
        self.gr, self.flex = gr, flex
        self.evaluators = dict(dihedral=torsion_evaluate, planarity=plane_evaluate)
        self.torsion_geometry = torsion_geometry
        self.rows = checked_proxy_rows(geometry, native)
        indices = list(moving_indices)
        if (not indices or len(set(indices)) != len(indices)
                or any(type(i) is not int or not 0 <= i < native['atom_count'] for i in indices)):
            raise ValueError('Require explicit valid moving atom indices')
        self.selected = set(indices)
        self.binding = recipe_digest(dict(atom_identities=[a['identity'] for a in native['atoms']],
                                          rows=self.rows, moving_indices=indices))

    def observe(self, points, native_components):
        if checked_proxy_rows(self.geometry, self.native) != self.rows:
            raise ValueError('Native term policy changed after binding')
        count = self.native['atom_count']
        if len(points) != count or any(len(p) != 3 or any(not _finite(v) for v in p) for p in points):
            raise ValueError('Require complete finite endpoint coordinates')
        xyz = self.flex.vec3_double(points); families = {}; calls = 0
        for kind in KINDS:
            proxies = getattr(self.geometry, kind + '_proxies')
            measurements = []; scattered = [[] for _ in range(3 * count)]
            for index, (proxy, bound) in enumerate(zip([] if proxies is None else proxies, self.rows[kind])):
                definition = bound['definition']; ids = definition['i_seqs']
                local = [points[i] for i in ids]
                first = self.evaluators[kind](local, definition)
                second = self.evaluators[kind](local, definition)
                restraint = getattr(self.gr, kind)(sites_cart=xyz, proxy=proxy)
                target = float(restraint.residual())
                gradient = [float(v) for p in restraint.gradients() for v in p]
                calls += 5  # Two Cedar single/container evaluations plus original live proxy.
                if (first != second or len(gradient) != 3 * len(ids)
                        or not _close(first['single_target'], target)
                        or not _close(first['accumulated_target'], target)
                        or not _vector(first['single_gradient'], gradient)
                        or not _vector(first['accumulated_gradient'], gradient)):
                    raise ValueError('Cedar and original live native term evaluations differ')
                for i, atom in enumerate(ids):
                    for j in range(3):
                        scattered[3 * atom + j].append(gradient[3 * i + j])
                if kind == 'dihedral':
                    measured = dict(native_angle_defined=bool(restraint.have_angle_model),
                        native_angle_degrees=float(restraint.angle_model) if restraint.have_angle_model else None,
                        native_delta_degrees=float(restraint.delta), conditioning=self.torsion_geometry(local))
                    if (measured['native_angle_defined'] != first['native_angle_defined']
                            or measured['native_angle_degrees'] != first['native_angle_degrees']):
                        raise ValueError('Live torsion measurement differs from Cedar kernel')
                else:
                    measured = dict(rms_distance_angstrom=float(restraint.rms_deltas()),
                                    signed_distances_angstrom=list(restraint.deltas()))
                if not _finite(target) or target < 0:
                    raise ValueError('Nonfinite or negative native term residual')
                selected_count = sum(i in self.selected for i in ids)
                scope = 'fixed_only' if selected_count == 0 else 'selected_only' if selected_count == len(ids) else 'boundary'
                measurements.append(dict(proxy_index=index, **bound, scope=scope,
                    native_residual=target, measurement=measured, kernel_evaluations=[first, second]))
            total = math.fsum(row['native_residual'] for row in measurements)
            gradients = [math.fsum(values) for values in scattered]
            container_gradient = self.flex.vec3_double(count, (0., 0., 0.))
            if proxies is None:
                container_target = 0.
            else:
                container_target = float(getattr(self.gr, kind + '_residual_sum')(
                    sites_cart=xyz, proxies=proxies, gradient_array=container_gradient))
                calls += 1
            if (not _close(total, container_target) or not _close(total, native_components[kind + '_residual_sum'])
                    or not _vector(gradients, list(container_gradient.as_double()))):
                raise ValueError('Individual native terms do not reproduce full family target/gradient')
            families[kind] = dict(rows=measurements, proxy_count=len(measurements), native_residual=total,
                container_target=container_target, complete_family_sum_verified=True,
                full_family_gradient_verified=True)
        if checked_proxy_rows(self.geometry, self.native) != self.rows:
            raise ValueError('Native term policy changed during observation')
        return dict(schema_version=1, kind='topostitch-native-term-observation',
            binding_sha256=self.binding, points_sha256=recipe_digest(points), families=families,
            native_kernel_calls=calls, maximum_terms=MAX_TERMS,
            deferred_proxy_kinds={k:len(v) for k,v in self.native['geometry']['proxy_details'].items() if k not in KINDS},
            normalization=False, derivative_qualification='NOT_RUN', chemical_qualification='NOT_ESTABLISHED',
            runtime_authority=False, scientific_acceptance=False)


def compare_native_term_observations(before, after):
    """Retain every local change; no geometry or derivative acceptance threshold."""
    for report in (before, after):
        if (type(report['schema_version']) is not int or report['schema_version'] != 1
                or report['kind'] != 'topostitch-native-term-observation'
                or report['normalization'] is not False or report['scientific_acceptance'] is not False
                or report['runtime_authority'] is not False or report['derivative_qualification'] != 'NOT_RUN'
                or report['chemical_qualification'] != 'NOT_ESTABLISHED' or set(report['families']) != set(KINDS)):
            raise ValueError('Unsupported native term observation policy')
        for name in ('binding_sha256', 'points_sha256'):
            value = report[name]
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Require explicit native term binding and coordinate digests')
        for family in report['families'].values():
            rows = family['rows']
            if (not isinstance(rows, list) or len(rows) > MAX_TERMS or type(family['proxy_count']) is not int
                    or family['proxy_count'] != len(rows) or family['complete_family_sum_verified'] is not True
                    or family['full_family_gradient_verified'] is not True
                    or [r['proxy_index'] for r in rows] != list(range(len(rows)))
                    or any(not _finite(r['native_residual']) or r['native_residual'] < 0 for r in rows)
                    or family['native_residual'] != math.fsum(r['native_residual'] for r in rows)
                    or not _close(family['native_residual'], family['container_target'])):
                raise ValueError('Native term summary does not reproduce its complete rows')
    if (before['binding_sha256'] != after['binding_sha256']
            or before['deferred_proxy_kinds'] != after['deferred_proxy_kinds']):
        raise ValueError('Native term binding or deferred inventory changed')
    families = {}
    for kind in KINDS:
        a, b = before['families'][kind], after['families'][kind]
        if a['proxy_count'] != b['proxy_count']:
            raise ValueError('Native term inventory changed')
        rows = []
        for x, y in zip(a['rows'], b['rows']):
            if any(x[k] != y[k] for k in ('proxy_index', 'definition', 'live_policy', 'scope')):
                raise ValueError('Native term definitions or scope changed')
            if x['scope'] not in ('selected_only', 'boundary', 'fixed_only'):
                raise ValueError('Invalid native term coordinate scope')
            rows.append(dict(proxy_index=x['proxy_index'], definition=x['definition'], live_policy=x['live_policy'],
                scope=x['scope'], before=x['native_residual'], after=y['native_residual'],
                change=y['native_residual']-x['native_residual'],
                before_measurement=x['measurement'], after_measurement=y['measurement']))
        families[kind] = dict(rows=rows, target_change=b['native_residual']-a['native_residual'],
            scopes={scope:dict(proxy_count=sum(r['scope'] == scope for r in rows),
                residual_change=math.fsum(r['change'] for r in rows if r['scope'] == scope),
                increased_proxy_indices=[r['proxy_index'] for r in rows if r['scope'] == scope and r['change'] > 0])
                for scope in ('selected_only', 'boundary', 'fixed_only')})
    return dict(schema_version=1, kind='topostitch-native-term-comparison', binding_sha256=before['binding_sha256'],
        source_points_sha256=before['points_sha256'], endpoint_points_sha256=after['points_sha256'],
        families=families, deferred_proxy_kinds=deepcopy(before['deferred_proxy_kinds']),
        increases_are_descriptive_not_acceptance_thresholds=True,
        derivative_qualification='NOT_RUN', chemical_qualification='NOT_ESTABLISHED',
        runtime_authority=False, scientific_acceptance=False)
