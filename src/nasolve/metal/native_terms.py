"""Explicit metal recipe declarations for shared native coverage review.

This adapter infers no partners, chemistry or providers and imports no native
runtime. Willow owns inventory observation and coverage comparison; Cedar owns
native policy authentication. A caller must supply those proofs separately.
"""
import json
import re

from .export import _replay, export_restraints
from .recipe import RecipeError, canonical, digest, element

POLICY = 'metal-explicit-native-terms-v1'
_IDENTITY = {'chain', 'residue_number', 'insertion_code', 'residue_code', 'atom_name', 'altloc'}


def _identity(key):
    if (key['segment_id'] or key['symmetry'] != 'x,y,z'
            or not re.fullmatch(r'-?(0|[1-9][0-9]*)', key['residue_id'])
            or key['residue_id'] == '-0'):
        raise RecipeError('Shared coverage requires identity images, blank segments and canonical integer residue IDs')
    return dict(chain=key['chain_id'], residue_number=int(key['residue_id']),
                insertion_code=key['insertion_code'], residue_code=key['component_id'],
                atom_name=key['atom_name'], altloc=key['altloc'])


def describe_native_terms(preview, native_atoms):
    """Bind explicit enabled distances/angles to a complete native atom order.

    Each native row supplies ``identity`` (the six fields returned by Willow's
    native_atom_identities), ``element``, ``model_id`` and ``segment_id``. The
    latter fields prevent silently losing identities absent from shared labels.
    The full inventory must match, with reordering permitted. Only implicit
    native model '' -> source model '1' is normalized; no other model alias is
    inferred. Coordinates may have moved and are not read by this adapter.

    Targets and sigmas follow the existing PHIL export's 12-significant-digit
    serialization; defaults declare harmonic terms with zero slack. Angle atom
    order and vertex stay explicit, including 0/180-degree targets. The result is
    a declaration, never proof that any native term exists or acts in refinement.
    """
    try:
        bound = _replay(preview)
        # Reuse exact export eligibility, including single-model and selector
        # ambiguity checks, rather than implementing a second selection policy.
        export_restraints(bound)
        source = bound['inputs']['model']
        atoms = source['atoms']
        if not isinstance(native_atoms, list) or len(native_atoms) != len(atoms):
            raise RecipeError('Native atom inventory is incomplete')
        model_ids = {a['key']['model_id'] for a in atoms}
        if len(model_ids) != 1:
            raise RecipeError('Shared coverage requires one source model')
        source_model = next(iter(model_ids))
        expected = {}
        for atom in atoms:
            label = canonical(_identity(atom['key']))
            if label in expected:
                raise RecipeError('Ambiguous source identity after shared-label projection')
            expected[label] = atom['element']
        labels = []; models = set(); normalized = []
        for row in native_atoms:
            if (not isinstance(row, dict) or set(row) != {'identity', 'element', 'model_id', 'segment_id'}
                    or not isinstance(row['identity'], dict) or set(row['identity']) != _IDENTITY):
                raise RecipeError('Incomplete native atom identity')
            identity = row['identity']
            if (type(identity['residue_number']) is not int
                    or any(not isinstance(identity[k], str) for k in _IDENTITY - {'residue_number'})
                    or not isinstance(row['model_id'], str) or row['segment_id'] != ''
                    or not isinstance(row['element'], str) or not re.fullmatch('[A-Za-z]{1,2}', row['element'])):
                raise RecipeError('Unsupported native atom identity or element')
            label = canonical(identity); symbol = element(row['element'].title())
            if label not in expected or expected[label] != symbol:
                raise RecipeError('Native atom identity or element differs from recipe inventory')
            labels.append(label); models.add(row['model_id'])
            normalized.append(dict(identity=dict(identity), element=symbol,
                                   model_id=row['model_id'], segment_id=''))
        if len(set(labels)) != len(labels) or set(labels) != set(expected):
            raise RecipeError('Ambiguous or incomplete native atom inventory')
        if models != {source_model} and not (source_model == '1' and models == {''}):
            raise RecipeError('Native model identity differs from recipe inventory')
        node_labels = {row['node_id']: canonical(_identity(row['atom']['key']))
                       for row in bound['nodes'] if row['atom'] is not None}
        requested = []; disabled = []
        for row in bound['restraints']:
            if not row['enabled']:
                disabled.append(row['restraint_id'])
                continue
            kind = 'bond' if row['kind'] == 'distance' else 'angle'
            ideal = float(format(row['target'], '.12g'))
            sigma = float(format(row['sigma'], '.12g'))
            parameters = dict(ideal=ideal, weight=1. / sigma**2, slack=0.)
            if kind == 'bond':
                parameters.update(limit=-1., top_out=False)
            requested.append(dict(term_id=row['restraint_id'], kind=kind,
                atoms=[dict(atom=node_labels[n], rotation=[1,0,0,0,1,0,0,0,1],
                            translation=['0','0','0']) for n in row['node_ids']],
                other_atoms=[], parameters=parameters))
        result = dict(kind='metal-native-term-declaration', schema_version=1, policy_id=POLICY,
            preview_input_sha256=bound['input_sha256'], recipe_sha256=bound['inputs']['recipe_sha256'],
            source_model_sha256=source['source_sha256'], atom_labels=labels,
            native_inventory_sha256=digest(normalized),
            model_binding=dict(source=source_model, native=next(iter(models))),
            requested=requested, requested_sha256=digest(requested), disabled_restraint_ids=disabled,
            numerical_policy='existing_PHIL_export_12_significant_digits_harmonic_defaults',
            scope='explicit_recipe_declarations_only; native_inventory_and_policy_authentication_required',
            runtime_authority=False, scientific_acceptance=False)
        return json.loads(canonical(result))
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot describe native metal terms: '+str(exc)) from exc
