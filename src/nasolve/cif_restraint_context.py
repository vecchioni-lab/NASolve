"""Bind ordered explicit restraint inputs without becoming a PHIL evaluator.

The supplied PHIL owns targets. This bounded reader accepts the explicit
bond/angle/planarity/parallelity grammar emitted by the maintained NAR compiler.
It does not infer authorship, generate restraints or qualify native realization.
Only the dictionary composer may add site-modification requests downstream.
"""
from collections import Counter
from hashlib import sha256
from math import isfinite
from pathlib import Path

from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _bytes
from .cif_explicit_na_policy import _model
from .cif_na_policy import SS, _parse, _path, _requests, _signature
from .cif_native_context import _signature as _checked_signature

POLICY_ID = 'cif-owned-explicit-restraints-v1'
PLANARITY_POLICY_ID = 'cif-owned-explicit-restraints-v2'
_TARGETS = {'bond': 'distance_ideal', 'angle': 'angle_ideal', 'parallelity': 'target_angle_deg'}
_CONTAINERS = {'refinement', 'pdb_interpretation', 'geometry_restraints', 'geometry_restraints.edits'}


def _checked_requests(text, atoms, *, require_scoped_names=False):
    nodes, _ = _parse(text); declarations = 0; disabled = 0
    for node in nodes:
        path = _path(node); fields = node['fields']
        if path in _CONTAINERS:
            _need(not fields, 'Unsupported explicit restraint container fields')
        elif path == SS:
            _need(not node['children'] and fields == {'enabled': 'False'},
                  'Require explicitly disabled native secondary structure')
            disabled += 1
        elif path.startswith('geometry_restraints.edits.'):
            kind = path.removeprefix('geometry_restraints.edits.')
            _need(kind in {*_TARGETS, 'planarity'}, 'Unsupported explicit restraint kind')
            if kind == 'planarity':
                expected = {'atom_selection', 'action', 'sigma'}
            else:
                selections = {'atom_selection_'+str(i+1) for i in range(3 if kind == 'angle' else 2)}
                expected = selections | {'action', 'sigma', _TARGETS[kind]}
            _need(not node['children'] and set(fields) == expected
                  and fields['action'] == 'add', 'Unsupported explicit restraint action or fields')
            sigma = float(fields['sigma'])
            _need(isfinite(sigma) and sigma > 0, 'Require a finite positive explicit restraint sigma')
            declarations += 1
        else:
            # No silently stripped legacy modifier or ignored alternative PHIL
            # spelling may bypass the composer's exclusive modifier ownership.
            raise ValueError('Unsupported scope or competing site-modifier owner: '+path)
    try:
        requests = _requests(text, atoms, require_scoped_names=require_scoped_names)
    except (KeyError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete or unrepresentable explicit restraint') from exc
    _need(len(requests) == declarations, 'Explicit restraint declaration coverage differs')
    for request in requests:
        # Reuse endpoint identity, finite target/weight and plane disjointness
        # checks. PDB record indices here are not asserted to be native indices.
        _checked_signature({'atoms': atoms}, request['kind'], request)
    return requests, disabled


def derive_restraint_context(model, supplementary_phils):
    """Return a byte/order/model-bound declaration without writing or executing.

    One to 64 ordered inputs may contain up to 4096 unique explicit requests.
    Includes, substitutions, native secondary-structure guessing, site modifiers,
    unknown fields/actions and unsupported selection syntax refuse. Every accepted
    input byte and request is retained; there is no target/coordinate rewriting.
    Atom-name alternatives must be parenthesized to retain their site scope in
    native boolean selection. Plane-bearing records use v2; grouped plane-free
    records retain exact v1 semantics.
    """
    return _derive_from_paths(model, supplementary_phils, require_scoped_names=True)


def _derive_from_paths(model, supplementary_phils, *, require_scoped_names):
    _need(isinstance(supplementary_phils, (list, tuple)) and 1 <= len(supplementary_phils) <= 64,
          'Require one to 64 ordered explicit PHIL inputs')
    paths = [Path(p) for p in supplementary_phils]
    originals = [_read(p) for p in paths]
    result = _derive_restraint_payload(model, originals, require_scoped_names=require_scoped_names)
    _need(all(_read(p) == data for p, data in zip(paths, originals)),
          'PHIL changed while binding explicit restraints')
    return result


def _derive_restraint_payload(model, originals, *, require_scoped_names=False):
    """Shared byte-bound derivation for frozen and not-yet-written PHIL payloads."""
    _need(isinstance(originals, (list, tuple)) and 1 <= len(originals) <= 64
          and all(isinstance(data, bytes) for data in originals), 'Require ordered PHIL bytes')
    model = Path(model); original = _read(model)
    raw, atoms, _, _, _, _ = _model(model)
    _need(raw == original, 'Model changed while binding explicit restraints')
    requests = []; inputs = []; disabled = 0
    for number, data in enumerate(originals):
        rows, controls = _checked_requests(data.decode('utf-8'), atoms, require_scoped_names=require_scoped_names)
        start = len(requests); requests.extend(rows); disabled += controls
        inputs.append(dict(input_index=number, sha256=sha256(data).hexdigest(), size=len(data),
                           request_indices=list(range(start, len(requests))), disabled_ss_controls=controls))
    _need(disabled > 0, 'Require an explicit disabled secondary-structure control')
    _need(1 <= len(requests) <= 4096, 'Require one to 4096 explicit restraint requests')
    signatures = [_signature(r['kind'], r, values=False) for r in requests]
    _need(len(signatures) == len(set(signatures)), 'Duplicate explicit restraint endpoints across ordered inputs')
    _need(_read(model) == original, 'Model changed while binding explicit restraints')
    policy = PLANARITY_POLICY_ID if any(r['kind'] == 'planarity' for r in requests) else POLICY_ID
    return dict(schema_version=1, policy_id=policy, model_sha256=sha256(original).hexdigest(),
                inputs=inputs, requests=requests, request_counts=dict(sorted(Counter(r['kind'] for r in requests).items())),
                index_basis='PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES',
                target_authority='SUPPLIED_EXPLICIT_PHIL', site_modifier_owner='DICTIONARY_COMPOSER',
                secondary_structure_enabled=False, native_membership='NOT_ASSESSED')


def validate_restraint_context(model, supplementary_phils, record, *, require_scoped_names=False):
    """Reconstruct frozen input meaning without changing historical records.

    New creation/execution must require scoped names. Read-only replay retains
    the legacy derivation; a readable historical record is not permission to run.
    """
    _need(isinstance(record, dict) and type(record.get('schema_version')) is int
          and record['schema_version'] == 1 and record.get('policy_id') in (POLICY_ID, PLANARITY_POLICY_ID),
          'Unsupported explicit restraint context')
    expected = _derive_from_paths(model, supplementary_phils, require_scoped_names=require_scoped_names)
    _need(_bytes(record) == _bytes(expected), 'Explicit restraint context differs from frozen inputs')
    return expected
