"""Activate qualified mixed coordinates through the ordinary bundle reader.

The exact source capsule is preserved once. Resolution reconstructs bounded
temporary data views and replays existing observations, never native programs.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .cif_mixed_runtime_source import verified_endpoint_source
from .cif_runtime_bundle import (ANCHOR, MANIFEST_FILE, _json_bytes, _load_json, _reference, _resolve_reference)

POLICY_ID = 'cif-qualified-mixed-runtime-bundle-v1'
_FIXED = {'schema_version': 1, 'policy_id': POLICY_ID, 'manifest_file': MANIFEST_FILE,
    'scope': 'PORTABLE_QUALIFIED_RUNTIME_BUNDLE', 'status': 'ACTIVATED_WITH_NOTES',
    'native_evidence': 'VERIFIED_SOURCE_CAPTURE', 'requires_cif_review': False,
    'scientific_approval': 'NOT_RUN', 'automatic_adoption': False,
    'production_consumption': 'PUBLIC_CIF_DOCTOR_BUNDLE_ASSESSMENT', 'checkpoint_adoption': 'NOT_RUN',
    'automatic_acquisition': 'NOT_RUN', 'model_optimization': 'NOT_RUN', 'refinement': 'NOT_RUN',
    'new_native_calls': 0, 'captured_code_execution': 'NOT_RUN', 'diffraction_data': 'NOT_READ'}


def _need(value):
    if not value:
        raise ValueError('Incomplete or changed qualified mixed runtime bundle')


def _summary(source):
    replay = source['replay']
    return {'atom_count': source['atom_count'], 'source_replay_policy': replay.get('policy_id', 'cif-saved-endpoint-portable-replay-v1'),
        'source_status': replay['status'], 'saved_native_calls': replay['saved_native_calls'],
        'scientific_qualification': 'NOT_ASSESSED', 'source_chemical_findings': source['source_chemical_findings']}


def prepare_mixed_runtime_bundle(source, output, *, source_sha256):
    """Preserve one verified capsule and freeze its exact selected resources."""
    source, output = Path(source).expanduser().absolute(), Path(output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    _need(not any(p.is_symlink() for p in output.parents) and not source.is_relative_to(output))
    original = source.read_bytes()
    with verified_endpoint_source(source, source_sha256) as verified:
        rows = verified['resources']; _need(rows and rows[0][0] == 'model'
            and all(role in {'model', 'dictionary', 'phil'} for role, _, _ in rows))
        roles = [role for role, _, _ in rows]
        _need(roles == ['model'] + ['dictionary']*roles.count('dictionary') + ['phil']*roles.count('phil')
            and roles.count('dictionary') > 0 and roles.count('phil') > 0)
        output.mkdir(parents=True)
        capsule = output/'evidence/source_review.zip'; capsule.parent.mkdir(); capsule.write_bytes(original)
        resources = {'model': None, 'dictionaries': [], 'phils': []}
        for i, (role, name, data) in enumerate(rows):
            folder = {'model': 'model', 'dictionary': 'dictionaries', 'phil': 'parameters'}[role]
            suffix = {'model': '.pdb', 'dictionary': '.cif', 'phil': '.phil'}[role]
            path = output/folder/f'{i:03d}{suffix}'; path.parent.mkdir(exist_ok=True); path.write_bytes(data)
            ref = _reference(path, output)
            if role == 'model': resources['model'] = ref
            else: resources['dictionaries' if role == 'dictionary' else 'phils'].append(ref)
        value = {**deepcopy(_FIXED), 'resources': resources, 'source_capsule': _reference(capsule, output),
            'source_archive': {'sha256': source_sha256, 'scope': 'VERIFIED_MIXED_ENDPOINT_REPLAY_CAPSULE'},
            'decision': deepcopy(verified['replay']['coordinate_decision']), 'qualification': _summary(verified)}
        _need(source.read_bytes() == original and sha256(original).hexdigest() == source_sha256)
        (output/MANIFEST_FILE).write_bytes(_json_bytes(value))
    return value


def verify_mixed_runtime_resources(path, value):
    """Cheap final integrity check after an already verified read-only use."""
    path = Path(path); root = path.parent
    _need(type(value.get('schema_version')) is int and type(value.get('new_native_calls')) is int
        and all(type(value.get(k)) is type(v) and value.get(k) == v for k, v in _FIXED.items())
        and path.name == MANIFEST_FILE and _load_json(path) == value)
    refs = value['resources']
    _need(isinstance(refs['dictionaries'], list) and bool(refs['dictionaries'])
          and isinstance(refs['phils'], list) and bool(refs['phils']))
    rows = [refs['model'], *refs['dictionaries'], *refs['phils'], value['source_capsule']]
    _need(len(rows) == len({row['relative_path'] for row in rows}))
    resolved = [_resolve_reference(root, row) for row in rows]
    _need(value['source_archive'] == {'sha256': value['source_capsule']['sha256'],
                                    'scope': 'VERIFIED_MIXED_ENDPOINT_REPLAY_CAPSULE'})
    return resolved


def resolve_mixed_runtime_bundle(path, value=None):
    path = Path(path); value = _load_json(path) if value is None else value
    try:
        resolved = verify_mixed_runtime_resources(path, value)
        with verified_endpoint_source(resolved[-1], value['source_archive']['sha256']) as verified:
            _need(value['decision'] == verified['replay']['coordinate_decision'] and value['qualification'] == _summary(verified))
            expected = [(role, data) for role, _, data in verified['resources']]
            refs = value['resources']
            actual = [('model', resolved[0].read_bytes()),
                *[('dictionary', _resolve_reference(path.parent, r).read_bytes()) for r in refs['dictionaries']],
                *[('phil', _resolve_reference(path.parent, r).read_bytes()) for r in refs['phils']]]
            _need(actual == expected)
        verify_mixed_runtime_resources(path, value)
        return {'model': resolved[0], 'dictionaries': resolved[1:1+len(refs['dictionaries'])],
            'phils': resolved[1+len(refs['dictionaries']):-1], 'manifest': value, 'manifest_path': path}
    except (KeyError, TypeError, IndexError, OSError) as exc:
        raise ValueError('Incomplete or changed qualified mixed runtime bundle') from exc
