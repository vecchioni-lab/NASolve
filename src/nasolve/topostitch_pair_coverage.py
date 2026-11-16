"""Read-only coverage of declared pair terms by native and additive providers.

The caller authenticates complete native observations, the recipe, atom ordering,
crystal and exclusion policy through their existing owners. This checker compares
those frozen declarations; it cannot discover omitted native terms, observe active
forces, approve exclusions or install a refinement callback.
"""
from fractions import Fraction
import json
import math
import re

from .topostitch_packing import _operation, _relative
from .topostitch_recipe import recipe_digest

POLICY_ID = 'topostitch-declared-pair-coverage-v1'
_CONTEXT_DIGESTS = ('source_model_sha256', 'recipe_sha256', 'crystal_sha256',
                    'native_exclusion_policy_sha256')
_PARAMETERS = {
    'bond': {'ideal', 'weight', 'slack', 'limit', 'top_out'},
    'angle': {'ideal', 'weight', 'slack'},
    'planarity': {'weights'},
    'parallelity': {'ideal', 'weight', 'slack', 'limit', 'top_out'},
}
_MAX_TERMS = 25000
_MAX_ATOMS_PER_TERM = 64


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _context(context):
    _need(isinstance(context, dict) and set(context) == {*_CONTEXT_DIGESTS, 'atom_labels'},
          'Incomplete pair coverage context')
    _need(all(_digest(context[k]) for k in _CONTEXT_DIGESTS), 'Invalid context digest')
    labels = context['atom_labels']
    _need(isinstance(labels, list) and 1 <= len(labels) <= 100000
          and all(isinstance(s, str) and 0 < len(s) <= 4096 for s in labels)
          and len(set(labels)) == len(labels), 'Require complete distinct atom labels')
    return set(labels)


def _site(row, labels):
    _need(isinstance(row, dict) and set(row) == {'atom', 'rotation', 'translation'},
          'Incomplete exact atom/image reference')
    _need(isinstance(row['atom'], str) and row['atom'] in labels, 'Unknown atom label')
    r, t = row['rotation'], row['translation']
    _need(isinstance(r, list) and len(r) == 9
          and all(type(v) is int and abs(v) <= 12 for v in r), 'Invalid exact rotation')
    _need(isinstance(t, list) and len(t) == 3
          and all(isinstance(v, str) and len(v) <= 32
                  and re.fullmatch(r'-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?', v) for v in t),
          'Invalid rational translation')
    translation = tuple(Fraction(v) for v in t)
    _need(all(str(v) == text and 24 % v.denominator == 0 and abs(v.numerator) <= 1000000
              for v, text in zip(translation, t)), 'Unsupported rational translation')
    rotation, unused, inverse = _operation(r, (0, 0, 0))
    return row['atom'], (rotation, translation, inverse)


def _relative_sites(sites, anchor):
    result = []
    for label, operation in sites:
        rotation, translation = _relative(anchor, operation)
        _need(all(abs(v) <= 1000000 for v in rotation)
              and all(abs(v.numerator) <= 1000000 for v in translation),
              'Relative image exceeds exact arithmetic budget')
        result.append((label, rotation, translation))
    return tuple(result)


def _parameters(kind, row, atom_count):
    _need(isinstance(row, dict) and set(row) == _PARAMETERS[kind],
          'Incomplete or unsupported term parameters')
    for key, value in row.items():
        if key == 'top_out':
            _need(type(value) is bool, 'Invalid native top-out mode')
        else:
            values = value if key == 'weights' else [value]
            _need(isinstance(values, list) and (key != 'weights' or len(values) == atom_count)
                  and all(type(v) in (int, float) and math.isfinite(v) for v in values),
                  'Require complete finite term parameters')
    if kind == 'planarity':
        _need(all(v >= 0 for v in row['weights']), 'Negative plane weight')
    else:
        _need(row['weight'] >= 0 and row['slack'] >= 0, 'Negative term weight or slack')
        _need(0 < row['ideal'] if kind == 'bond' else
              0 <= row['ideal'] <= (180 if kind == 'angle' else 90), 'Invalid term ideal')
    return dict(row)


def _term(row, labels):
    _need(isinstance(row, dict) and set(row) ==
          {'term_id', 'kind', 'atoms', 'other_atoms', 'parameters'}, 'Incomplete pair term')
    name, kind = row['term_id'], row['kind']
    _need(isinstance(name, str) and 0 < len(name) <= 256 and isinstance(kind, str)
          and kind in _PARAMETERS, 'Unsupported term identity or family')
    a, b = row['atoms'], row['other_atoms']
    _need(isinstance(a, list) and isinstance(b, list)
          and len(a) + len(b) <= _MAX_ATOMS_PER_TERM, 'Term atom allowance exceeded')
    _need((len(a) == 2 and not b) if kind == 'bond' else
          (len(a) == 3 and not b) if kind == 'angle' else
          (len(a) >= 3 and not b) if kind == 'planarity' else
          (len(a) >= 3 and len(b) >= 3), 'Incomplete term atom membership')
    a, b = [_site(s, labels) for s in a], [_site(s, labels) for s in b]
    _need(len(set(a)) == len(a) and len(set(b)) == len(b), 'Duplicate atom/image in term')
    params = _parameters(kind, row['parameters'], len(a))
    if kind in ('bond', 'angle'):
        key = min(_relative_sites(sites, sites[0][1]) for sites in (a, list(reversed(a))))
    elif kind == 'planarity':
        choices = []
        for unused, anchor in a:
            weighted = sorted(zip(_relative_sites(a, anchor), params['weights']))
            choices.append((tuple(v[0] for v in weighted), tuple(v[1] for v in weighted)))
        key, weights = min(choices)
        params['weights'] = weights
    else:
        key = min(tuple(sorted((tuple(sorted(_relative_sites(a, anchor))),
                                tuple(sorted(_relative_sites(b, anchor))))))
                  for unused, anchor in a + b)
    return name, (kind, key), params


def _inventory(rows, labels):
    _need(isinstance(rows, list) and len(rows) <= _MAX_TERMS, 'Term inventory allowance exceeded')
    result = [_term(row, labels) for row in rows]
    _need(len({r[0] for r in result}) == len(result), 'Duplicate term identifier')
    return result


def _same_parameters(a, b):
    # Native reciprocal-square weights can differ by floating-point rounding.
    # No absolute tolerance: distinct tiny weights must remain distinct.
    for key in a:
        if key in ('weight', 'weights'):
            left, right = ([a[key]], [b[key]]) if key == 'weight' else (a[key], b[key])
            if len(left) != len(right) or any(not math.isclose(x, y, rel_tol=1e-12, abs_tol=0.)
                                            for x, y in zip(left, right)):
                return False
        elif a[key] != b[key]:
            return False
    return True


def review_pair_coverage(requested, native, additive, *, frozen, current_context):
    """Require each requested term exactly once from its explicit provider.

    Terms contain an ID, one of bond/angle/planarity/parallelity, ordered ``atoms``
    and ``other_atoms`` (parallelity only), and all supported score parameters.
    Each atom reference has a complete source label, nine integer fractional
    rotation coefficients and three reduced rational translation strings.

    ``frozen`` binds context, byte-independent JSON digests of all three ordered
    inventories, and ``native_requested_ids``. Remaining requested IDs must come
    from the explicit additive inventory. Nothing is inferred, removed or applied.
    Context binds source model, recipe, ordered atom labels, crystal and the caller's
    authenticated native exclusion policy. Hashes are integrity checks, not proof
    that a caller supplied a complete native observation or a scientifically valid
    recipe. General-position, standard-setting image equivalence only; the caller
    must establish that scope and space-group membership of every image.
    Coordinates, force activity, normalization, callback
    lifecycle and final-writer binding are outside this read-only check.
    """
    try:
        # Freeze caller data; never rewrite declarations or adopt a changed baseline.
        requested, native, additive, frozen, current_context = json.loads(json.dumps(
            [requested, native, additive, frozen, current_context], allow_nan=False))
        _need(isinstance(frozen, dict) and set(frozen) == {'context', 'requested_sha256',
              'native_sha256', 'additive_sha256', 'native_requested_ids'}, 'Incomplete frozen binding')
        labels = _context(frozen['context']); _context(current_context)
        _need(frozen['context'] == current_context, 'Changed pair coverage context')
        for key, values in (('requested', requested), ('native', native), ('additive', additive)):
            value = frozen[key + '_sha256']
            _need(_digest(value) and recipe_digest(values) == value, 'Changed ' + key + ' inventory digest')
        expected, existing, additions = (_inventory(rows, labels) for rows in (requested, native, additive))
        _need(bool(expected), 'Require a nonempty requested recipe')
        requested_by_support = {}
        for row in expected:
            _need(row[1] not in requested_by_support, 'Duplicate requested support')
            requested_by_support[row[1]] = row
        assigned = frozen['native_requested_ids']
        _need(isinstance(assigned, list) and all(isinstance(v, str) for v in assigned)
              and len(set(assigned)) == len(assigned)
              and assigned == [r[0] for r in expected if r[0] in assigned],
              'Invalid native provider assignment')
        supplied = {}
        for provider, rows in (('native', existing), ('additive', additions)):
            for name, key, parameters in rows:
                target = requested_by_support.get(key)
                if target is None:
                    _need(provider == 'native', 'Unrequested additive term: ' + name)
                    continue
                _need(_same_parameters(target[2], parameters), 'Mismatched term parameters: ' + target[0])
                _need(key not in supplied, 'Duplicate coverage: ' + target[0])
                supplied[key] = provider, name
        coverage = []
        for name, key, unused in expected:
            _need(key in supplied, 'Missing requested term: ' + name)
            provider, occurrence = supplied[key]
            _need(provider == ('native' if name in assigned else 'additive'),
                  'Requested provider differs: ' + name)
            coverage.append(dict(requested_id=name, provider=provider, observed_id=occurrence))
        return dict(policy_id=POLICY_ID, frozen_binding_sha256=recipe_digest(frozen),
            requested_sha256=frozen['requested_sha256'], native_sha256=frozen['native_sha256'],
            additive_sha256=frozen['additive_sha256'],
            native_exclusion_policy_sha256=current_context['native_exclusion_policy_sha256'],
            coverage=coverage, native_requested_term_count=len(assigned),
            additive_requested_term_count=len(coverage)-len(assigned),
            observed_native_term_count=len(existing), declared_coverage_complete=True,
            runtime_authority=False, scientific_acceptance=False)
    except (KeyError, TypeError, IndexError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Malformed pair coverage declarations') from exc


def _compiled_fractional_image(text, cell_parameters):
    """Read exact native operator fields and check their compiled Cartesian image."""
    from cctbx import sgtbx, uctbx
    from scitbx import matrix
    operation = sgtbx.rt_mx(text)
    cell = uctbx.unit_cell(cell_parameters)
    rotation = [Fraction(v, operation.r().den()) for v in operation.r().num()]
    _need(all(v.denominator == 1 for v in rotation), 'Noninteger fractional rotation is unsupported')
    declaration = dict(rotation=[int(v) for v in rotation],
        translation=[str(Fraction(v, operation.t().den())) for v in operation.t().num()])
    cart = (matrix.sqr(cell.orthogonalization_matrix()) * matrix.sqr(operation.r().as_double())
            * matrix.sqr(cell.fractionalization_matrix()))
    return declaration, [[cart[3*i+j] for j in range(3)] for i in range(3)], list(
        cell.orthogonalize(operation.t().as_double()))


def describe_compiled_pair_terms(recipe, packet, *, expected_binding_sha256):
    """Export W104 declarations from an already constructed NativePairRecipe.

    The original class remains the sole PHIL/compiler owner. This optional native
    adapter checks its frozen packet/binding, live proxy membership and parameters,
    and exact image roles against compiled Cartesian references. It evaluates no
    forces and changes neither the recipe, a native manager nor existing workers.
    Native cctbx imports are delayed until this function needs an image. The caller
    still owns native-profile qualification and complete actual-manager observation.
    """
    from .topostitch_native_recipe import NativePairRecipe
    try:
        _need(isinstance(recipe, NativePairRecipe), 'Require a constructed NativePairRecipe')
        packet = json.loads(json.dumps(packet, allow_nan=False))
        binding = recipe.binding_report()
        _need(_digest(expected_binding_sha256) and recipe_digest(binding) == expected_binding_sha256,
              'Changed compiled pair binding')
        _need(binding['recipe_sha256'] == recipe_digest(packet)
              and binding['source_model_sha256'] == packet['source_model_sha256']
              and _digest(packet['source_model_sha256']), 'Changed frozen pair packet')
        _need(recipe._identities == packet['atom_identities']
              and recipe._count == binding['atom_count'] == packet['atom_count']
              and recipe._count == len(recipe._identities)
              and recipe._terms == binding['terms'], 'Changed compiled pair atom/term inventory')
        labels = [json.dumps(row, sort_keys=True, separators=(',', ':')) for row in recipe._identities]
        _need(len(set(labels)) == len(labels), 'Ambiguous compiled atom labels')
        def references():
            return json.loads(json.dumps([dict(asu_index=i, rotation=image.rotation,
                translation=image.translation) for i, image in recipe._refs], allow_nan=False))
        _need(references() == binding['references'], 'Changed compiled Cartesian references')
        pairs = {p['pair_id']:p for p in packet['pairs']}
        _need(len(pairs) == len(packet['pairs']), 'Duplicate bound pair ID')
        containers = dict(bond=recipe._bonds, angle=recipe._angles,
                          planarity=recipe._planes, parallelity=recipe._parallel)
        positions = {kind:0 for kind in containers}
        counts = {name:{kind:0 for kind in containers} for name in pairs}
        images = {}; rows = []
        for ordinal, definition in enumerate(binding['terms']):
            kind = definition['kind']; pair = pairs[definition['pair_id']]
            _need(kind in containers and definition['purpose'] == pair['purpose'],
                  'Changed compiled pair family or purpose')
            proxy = containers[kind][positions[kind]]; positions[kind] += 1
            counts[definition['pair_id']][kind] += 1
            indices = list(proxy.i_seqs)
            others = list(proxy.j_seqs) if kind == 'parallelity' else []
            _need(indices == definition['i_seqs'] and others == definition.get('j_seqs', []),
                  'Changed live compiled proxy membership')
            if kind == 'bond':
                _need(proxy.rt_mx_ji is None, 'Unexpected live bond image')
            else:
                _need(proxy.sym_ops is None or len(proxy.sym_ops) == 0,
                      'Unexpected live proxy images on expanded coordinates')
            left, right = set(pair['role_indices']['L']), set(pair['role_indices']['R'])
            _need(not left & right, 'Ambiguous compiled pair roles')
            def atoms(ids):
                result = []
                for index in ids:
                    reference = binding['references'][index]; atom_index = reference['asu_index']
                    _need(type(atom_index) is int and 0 <= atom_index < len(labels)
                          and atom_index in left | right, 'Compiled reference is outside pair roles')
                    text = 'x,y,z' if atom_index in left else pair['target_operator_xyz']
                    if text not in images:
                        images[text] = _compiled_fractional_image(text, packet['crystal']['cell_parameters'])
                    exact, rotation, translation = images[text]
                    expected = [v for row in rotation for v in row] + translation
                    actual = [v for row in reference['rotation'] for v in row] + reference['translation']
                    _need(len(actual) == 12 and all(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-10)
                                                   for a, b in zip(actual, expected)),
                          'Exact role image differs from compiled Cartesian reference')
                    result.append(dict(atom=labels[atom_index], **exact))
                return result
            a, b = atoms(indices), atoms(others)
            weight = 1 / definition['sigma'] ** 2
            if kind == 'planarity':
                parameters = dict(weights=list(proxy.weights)); expected = dict(weights=[weight]*len(a))
            else:
                ideal_name = {'bond':'distance_ideal', 'angle':'angle_ideal',
                              'parallelity':'target_angle_deg'}[kind]
                parameters = dict(ideal=getattr(proxy, ideal_name), weight=proxy.weight, slack=proxy.slack)
                expected = dict(ideal=definition['ideal'], weight=weight, slack=0.)
                if kind in ('bond', 'parallelity'):
                    parameters.update(limit=proxy.limit, top_out=proxy.top_out)
                    expected.update(limit=-1. if kind == 'bond' else 1., top_out=False)
            _parameters(kind, parameters, len(a))
            _need(_same_parameters(expected, parameters), 'Changed live compiled proxy parameters')
            rows.append(dict(term_id=definition['pair_id']+':'+str(ordinal), kind=kind,
                             atoms=a, other_atoms=b, parameters=parameters))
        _need(all(positions[k] == len(v) for k, v in containers.items()), 'Extra compiled proxy terms')
        _need(all(counts[k] == p['expected_counts'] for k, p in pairs.items()),
              'Incomplete compiled pair family coverage')
        _inventory(rows, set(labels))
        _need(recipe.binding_report() == binding and references() == binding['references'],
              'Compiled pair binding changed during observation')
        # Detach nested arrays and native scalar wrappers from the returned declaration.
        result = dict(policy_id='topostitch-compiled-pair-declarations-v1',
            compiled_binding_sha256=expected_binding_sha256,
            source_model_sha256=binding['source_model_sha256'], recipe_sha256=binding['recipe_sha256'],
            atom_labels=labels, terms=rows, terms_sha256=recipe_digest(rows),
            runtime_authority=False, scientific_acceptance=False)
        return json.loads(json.dumps(result, allow_nan=False))
    except (KeyError, TypeError, AttributeError, IndexError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete compiled pair declaration') from exc
