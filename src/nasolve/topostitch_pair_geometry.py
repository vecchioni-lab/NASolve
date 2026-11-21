"""Cold, descriptive geometry of explicit pair terms across force providers.

The existing compiler, native attribution and observation owners supply the
records. This adapter neither evaluates forces nor authenticates arbitrary
caller-supplied evidence. It stays outside the frozen refinement helper closure.
"""
import json
import math

from .topostitch_native_recipe import compare_pair_attribution
from .topostitch_pair_coverage import _digest, _need, review_pair_coverage
from .topostitch_recipe import recipe_digest


def _geometry(rows):
    values = {kind: [] for kind in ('bond', 'angle', 'planarity', 'parallelity')}
    for row in rows:
        definition, measurement = row['definition'], row['measurement']
        kind = definition['kind']
        if kind == 'bond':
            observed = measurement['distance_angstrom']
            _need(observed > 0, 'Invalid measured pair distance')
            value = observed - definition['ideal']
        elif kind == 'angle':
            observed = measurement['angle_degrees']
            _need(0 <= observed <= 180, 'Invalid measured pair angle')
            value = observed - definition['ideal']
        elif kind == 'planarity':
            value = measurement['rms_distance_angstrom']
            _need(value >= 0, 'Invalid measured plane RMS')
        else:
            value = measurement['native_delta_degrees']
        values[kind].append(value)
    names = dict(bond='deviation_angstrom', angle='deviation_degrees',
                 planarity='of_plane_rms_angstrom', parallelity='native_delta_degrees')
    result = {}
    for kind, data in values.items():
        # No weighting by force constant, and no mixing degrees with angstroms.
        rms = math.sqrt(math.fsum(v*v for v in data) / len(data)) if data else None
        maximum = max(map(abs, data)) if data else None
        _need(rms is None or math.isfinite(rms), 'Nonfinite physical pair summary')
        result[kind] = dict(count=len(data), **{'rms_' + names[kind]: rms,
                                               'max_abs_' + names[kind]: maximum})
    return result


def review_pair_geometry(attribution, compiled_declarations, native_observation,
                         provider_selection, *, expected_inputs_sha256):
    """Join four previously authenticated records without running native code.

    The caller freezes ``recipe_digest([attribution, compiled_declarations,
    native_observation, provider_selection])`` before review. This detects changes;
    it does not establish that supplied records came from a qualified native run.
    Require a v2 observation of exact scattering force sites, not the v1 hierarchy
    points. Physical measurements cover the complete declared pair recipe and
    therefore do not depend on native/additive allocation. Native terms outside
    that exact coverage remain unclassified, including origins 0 and 4.

    Bond/angle RMS is unweighted deviation from declared targets. Plane RMS is
    the RMS of per-plane RMS distances, not pooled per-atom RMS. Parallelity uses
    the existing kernel's delta in degrees. None is an acceptance threshold,
    whole-model covalent statistic, objective normalization or weight selector.
    """
    try:
        records = json.loads(json.dumps([attribution, compiled_declarations,
            native_observation, provider_selection], allow_nan=False))
        _need(_digest(expected_inputs_sha256) and recipe_digest(records) == expected_inputs_sha256,
              'Changed frozen geometry-report inputs')
        attribution, compiled, observed, selection = records
        compare_pair_attribution(attribution, attribution)
        _need(compiled['policy_id'] == 'topostitch-compiled-pair-declarations-v1'
              and compiled['compiled_binding_sha256'] == attribution['binding_sha256'],
              'Different compiled pair measurement binding')
        _need(observed['policy_id'] == 'topostitch-native-pair-observation-v2',
              'Require exact dual-state native observation')
        for report in (compiled, observed):
            _need(report['runtime_authority'] is False and report['scientific_acceptance'] is False,
                  'Unsupported geometry-report authority')
        state, context = observed['native_state'], observed['context']
        _need(state['policy_id'] == 'topostitch-dual-native-state-v1'
              and state['state_owner_policy_id'] == 'native-refinement-output-state-v1'
              and type(state['atom_count']) is int and state['atom_count'] == len(context['atom_labels']),
              'Incomplete native force-state binding')
        _need(all(_digest(state[k]) for k in ('state_owner_sha256', 'hierarchy_sha256',
              'scattering_sha256', 'fractional_sites_sha256', 'force_sites_sha256'))
              and _digest(observed['policy_owner_sha256']), 'Invalid native owner/state digest')
        _need(state['force_sites_sha256'] == attribution['points_sha256'],
              'Pair measurements use different actual force coordinates')
        _need(compiled['source_model_sha256'] == context['source_model_sha256']
              and compiled['recipe_sha256'] == context['recipe_sha256']
              and compiled['atom_labels'] == context['atom_labels'],
              'Different pair source, recipe or atom order')
        requested, native = compiled['terms'], observed['terms']
        _need(recipe_digest(requested) == compiled['terms_sha256']
              and recipe_digest(native) == observed['terms_sha256'], 'Changed observed term digest')
        checked = review_pair_coverage(requested, native, selection['additive'],
            frozen=selection['frozen'], current_context=context)
        _need(checked == selection['review'], 'Changed saved pair coverage review')
        origins = observed['origin_ids']
        _need(isinstance(origins, list) and len(origins) == len(native)
              and all(type(v) is int and v >= 0 for v in origins), 'Incomplete native origin provenance')
        rows = attribution['terms']
        _need(len(rows) == len(requested), 'Incomplete measured pair inventory')
        for i, (row, term) in enumerate(zip(rows, requested)):
            definition, parameters = row['definition'], term['parameters']
            _need(term['term_id'] == definition['pair_id'] + ':' + str(i)
                  and term['kind'] == definition['kind'], 'Changed measured term order or identity')
            sigma = definition['sigma']
            _need(type(sigma) in (int, float) and math.isfinite(sigma) and sigma > 0,
                  'Invalid measured pair sigma')
            if term['kind'] == 'planarity':
                weights = parameters['weights']
            else:
                _need(definition['ideal'] == parameters['ideal'], 'Changed measured pair target')
                weights = [parameters['weight']]
            _need(all(math.isclose(w, 1/sigma**2, rel_tol=1e-12, abs_tol=0) for w in weights),
                  'Changed measured pair force parameters')
        assigned = {v['observed_id'] for v in checked['coverage'] if v['provider'] == 'native'}
        remainder = [dict(observed_id=t['term_id'], kind=t['kind'], origin_id=o)
                     for t, o in zip(native, origins) if t['term_id'] not in assigned]
        groups = {}
        for row in rows: groups.setdefault(row['definition']['pair_id'], []).append(row)
        return dict(schema_version=1, kind='topostitch-covered-pair-geometry',
            inputs_sha256=expected_inputs_sha256, compiled_binding_sha256=attribution['binding_sha256'],
            source_model_sha256=context['source_model_sha256'], recipe_sha256=context['recipe_sha256'],
            force_sites_sha256=state['force_sites_sha256'], native_observation_sha256=recipe_digest(observed),
            pair_geometry=_geometry(rows),
            pairs=[dict(pair_id=name, purpose=members[0]['definition']['purpose'],
                        geometry=_geometry(members)) for name, members in groups.items()],
            pair_energy=attribution['target'], pair_energy_normalization=attribution['normalization'],
            coverage=checked, unclassified_native_terms=remainder,
            covalent_geometry='UNASSESSED', runtime_authority=False, scientific_acceptance=False,
            limitations=[
                'Descriptive join of caller-authenticated records; checksums alone do not establish native execution.',
                'Complete declared canonical pair geometry only; no whole-model or covalent geometry approval.',
                'Unmatched native origins are provenance, not chemical classification.',
                'No weight choice, geometry mutation, force evaluation or scientific acceptance.'])
    except (KeyError, TypeError, IndexError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete covered pair geometry evidence') from exc
