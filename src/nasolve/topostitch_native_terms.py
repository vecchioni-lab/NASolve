"""Read-only native term observations and explicit angle snapshot evaluation.

Cedar owns the numerical kernels. This adapter verifies that complete live proxy
semantics fit those kernels before comparing them with original native objects.
The angle snapshot reconstructs only its private proxy array with explicit cell
context. No source proxy, manager, model or chemical acceptance policy is changed.
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


ANGLE_SNAPSHOT_KIND = 'topostitch-native-angle-snapshot'
_ANGLE_FIELDS = {'proxy_index', 'i_seqs', 'angle_ideal', 'weight', 'slack', 'origin_id', 'sym_ops'}


def _digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in '0123456789abcdef' for c in value))


def _angle_proxy_row(proxy, index):
    if any(not hasattr(proxy, key) for key in _ANGLE_FIELDS - {'proxy_index'}):
        raise ValueError('Live angle proxy omits required policy fields')
    return dict(proxy_index=index, i_seqs=list(proxy.i_seqs),
                angle_ideal=proxy.angle_ideal, weight=proxy.weight, slack=proxy.slack,
                origin_id=proxy.origin_id,
                sym_ops=None if proxy.sym_ops is None else [op.as_xyz() for op in proxy.sym_ops])


def validate_angle_snapshot(snapshot, *, expected_sha256):
    """Validate/detach a plain record without importing a native interpreter.

    Operator membership, metric compatibility and exact native reconstruction are
    checked by NativeAngleSnapshot. A digest binds data; it is not authentication
    of its creator or permission to apply restraints.
    """
    if not _digest(expected_sha256) or recipe_digest(snapshot) != expected_sha256:
        raise ValueError('Angle snapshot checksum mismatch')
    fields = {'schema_version', 'kind', 'source_native_sha256', 'atom_count',
              'atom_labels', 'crystal', 'terms', 'normalization', 'runtime_authority'}
    if (not isinstance(snapshot, dict) or set(snapshot) != fields
            or type(snapshot['schema_version']) is not int or snapshot['schema_version'] != 1
            or snapshot['kind'] != ANGLE_SNAPSHOT_KIND
            or snapshot['normalization'] is not False or snapshot['runtime_authority'] is not False
            or not _digest(snapshot['source_native_sha256'])):
        raise ValueError('Unsupported angle snapshot schema or policy')
    count, labels, terms = snapshot['atom_count'], snapshot['atom_labels'], snapshot['terms']
    if (type(count) is not int or not 1 <= count <= 100000
            or not isinstance(labels, list) or len(labels) != count
            or any(not isinstance(s, str) or not s or len(s) > 512 for s in labels)
            or len(set(labels)) != count
            or not isinstance(terms, list) or len(terms) > MAX_TERMS):
        raise ValueError('Invalid angle snapshot inventory or budget')
    crystal = snapshot['crystal']
    if not isinstance(crystal, dict) or set(crystal) != {'cell_parameters', 'space_group'}:
        raise ValueError('Require an explicit angle crystal context')
    cell, group = crystal['cell_parameters'], crystal['space_group']
    if (not isinstance(cell, list) or len(cell) != 6 or any(not _finite(v) for v in cell)
            or any(v <= 0 for v in cell[:3]) or any(not 0 < v < 180 for v in cell[3:])
            or not isinstance(group, str) or not group.strip() or len(group) > 120):
        raise ValueError('Invalid angle crystal context')
    for index, row in enumerate(terms):
        if not isinstance(row, dict) or set(row) != _ANGLE_FIELDS:
            raise ValueError('Unsupported angle term fields')
        ids, ops = row['i_seqs'], row['sym_ops']
        if (type(row['proxy_index']) is not int or row['proxy_index'] != index
                or not isinstance(ids, list) or len(ids) != 3
                or any(type(i) is not int or not 0 <= i < count for i in ids)
                or len(set(ids)) != 3
                or not _finite(row['angle_ideal']) or not 0 <= row['angle_ideal'] <= 180
                or not _finite(row['weight']) or row['weight'] < 0
                or not _finite(row['slack']) or row['slack'] < 0
                or type(row['origin_id']) is not int or not 0 <= row['origin_id'] <= 255
                or ops is not None and (not isinstance(ops, list) or len(ops) != 3
                    or any(not isinstance(op, str) or not op.strip() or len(op) > 160 for op in ops))):
            raise ValueError('Invalid or unsupported angle term policy')
    return deepcopy(snapshot)


def freeze_native_angles(geometry, native, *, cell_parameters, space_group):
    """Freeze complete live angle semantics after the caller authenticates context.

    Every scalar/index/label is compared with the existing descriptive capture.
    Images and slack come from live objects, never from absent historical fields.
    This does not infer new terms, select seams, transport images or edit a manager.
    """
    atoms, count = native['atoms'], native['atom_count']
    if (type(count) is not int or count != len(atoms)
            or any(type(a['i_seq']) is not int or a['i_seq'] != i for i, a in enumerate(atoms))):
        raise ValueError('Native angle atom ordering differs')
    rows = native['geometry']['proxy_details']['angle']
    proxies = geometry.angle_proxies
    proxies = [] if proxies is None else proxies
    if (len(rows) > MAX_TERMS or len(proxies) != len(rows)
            or type(native['geometry']['proxy_counts']['angle']) is not int
            or native['geometry']['proxy_counts']['angle'] != len(rows)):
        raise ValueError('Live and captured angle inventories differ')
    labels = [a['label'] for a in atoms]; terms = []
    for index, (proxy, row) in enumerate(zip(proxies, rows)):
        if set(row) != {'i_seqs', 'atoms', 'angle_ideal', 'weight', 'origin_id'}:
            raise ValueError('Unsupported captured angle definition')
        term = _angle_proxy_row(proxy, index)
        ids = term['i_seqs']
        if (any(type(i) is not int or not 0 <= i < count for i in ids)
                or row != dict(i_seqs=ids, atoms=[labels[i] for i in ids],
                    angle_ideal=term['angle_ideal'], weight=term['weight'], origin_id=term['origin_id'])):
            raise ValueError('Live angle definition differs from captured context')
        terms.append(term)
    record = dict(schema_version=1, kind=ANGLE_SNAPSHOT_KIND,
                  source_native_sha256=recipe_digest(native), atom_count=count,
                  atom_labels=labels, crystal=dict(cell_parameters=list(cell_parameters), space_group=space_group),
                  terms=terms, normalization=False, runtime_authority=False)
    return validate_angle_snapshot(record, expected_sha256=recipe_digest(record))


class NativeAngleSnapshot:
    """Rebuild and evaluate a frozen angle family with explicit crystal context.

    This diagnostic owns only its new proxy array, never a native manager. It
    serializes plain records and reconstructs operators, avoiding native proxy
    pickle. It is not a refinement callback, a seam policy or an additive term:
    adding its energy to a manager containing the same angles would double count.
    Only trusted local pickle data may be loaded, as with any Python pickle.
    """
    def __init__(self, snapshot, *, expected_sha256):
        from cctbx import crystal, geometry_restraints as gr, sgtbx
        from scitbx.array_family import flex
        from scitbx import matrix
        from .topostitch_transport import CartesianImage
        self._record = validate_angle_snapshot(snapshot, expected_sha256=expected_sha256)
        self._digest = expected_sha256
        self._gr, self._flex = gr, flex
        context = self._record['crystal']
        symmetry = crystal.symmetry(unit_cell=context['cell_parameters'],
                                    space_group_symbol=context['space_group'])
        self._cell = symmetry.unit_cell()
        # cctbx may symmetrize a cell. This observer must not silently change it.
        if any(abs(a-b) > 1e-9 for a,b in zip(self._cell.parameters(), context['cell_parameters'])):
            raise ValueError('Native angle crystal changed the declared cell')
        orth = matrix.sqr(self._cell.orthogonalization_matrix())
        frac = matrix.sqr(self._cell.fractionalization_matrix())
        operations = {}
        for row in self._record['terms']:
            for text in row['sym_ops'] or []:
                if text in operations:
                    continue
                op = sgtbx.rt_mx(text)
                if op.as_xyz() != text or op.mod_positive() not in symmetry.space_group():
                    raise ValueError('Angle operator is noncanonical or outside the declared group')
                rot = orth * matrix.sqr(op.r().as_double()) * frac
                CartesianImage(tuple(tuple(rot[3*i+j] for j in range(3)) for i in range(3)),
                               tuple(self._cell.orthogonalize(op.t().as_double())))
                operations[text] = op
        self._proxies = gr.shared_angle_proxy()
        for row in self._record['terms']:
            self._proxies.append(gr.angle_proxy(i_seqs=row['i_seqs'],
                sym_ops=None if row['sym_ops'] is None else [operations[t] for t in row['sym_ops']],
                angle_ideal=row['angle_ideal'], weight=row['weight'], slack=row['slack'],
                origin_id=row['origin_id']))
        self._verify_live()

    def _verify_live(self):
        if (len(self._proxies) != len(self._record['terms'])
                or [_angle_proxy_row(p, i) for i,p in enumerate(self._proxies)] != self._record['terms']):
            raise ValueError('Reconstructed angle metadata changed or was lost')

    def snapshot(self):
        self._verify_live()
        return deepcopy(self._record)

    def __getstate__(self):
        return dict(snapshot=self.snapshot(), expected_sha256=self._digest)

    def __setstate__(self, state):
        if not isinstance(state, dict) or set(state) != {'snapshot', 'expected_sha256'}:
            raise ValueError('Unsupported native angle reload state')
        self.__init__(**state)

    def evaluate(self, points, *, atom_labels):
        """Full ordered Cartesian coordinates; explicit labels guard reindexing.

        Return the unnormalized angle-family target and ASU Cartesian gradient.
        The caller owns model/image placement and must not mistake this numerical
        observation for complete chemistry or ordinary refinement qualification.
        """
        self._verify_live()
        points = [list(p) for p in points]
        if (list(atom_labels) != self._record['atom_labels'] or len(points) != self._record['atom_count']
                or any(len(p) != 3 or any(not _finite(v) for v in p) for p in points)):
            raise ValueError('Angle evaluation requires the exact ordered finite atom inventory')
        xyz = self._flex.vec3_double(points)
        gradient = self._flex.vec3_double(len(points), (0.,0.,0.))
        target = float(self._gr.angle_residual_sum(unit_cell=self._cell, sites_cart=xyz,
                       proxies=self._proxies, gradient_array=gradient))
        gradients = [list(p) for p in gradient]
        if not _finite(target) or target < 0 or any(not _finite(v) for p in gradients for v in p):
            raise ValueError('Native angle evaluation returned nonfinite or negative values')
        self._verify_live()
        return dict(schema_version=1, kind='topostitch-native-angle-evaluation',
                    snapshot_sha256=self._digest, points_sha256=recipe_digest(points),
                    residual_sum=target, gradients=gradients, term_count=len(self._proxies),
                    normalization=False, runtime_authority=False, scientific_acceptance=False)
