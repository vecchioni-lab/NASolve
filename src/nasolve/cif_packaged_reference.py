"""Exact packaged chemical sources, never runtime dictionaries or mutation aliases.

Resource paths exist only while parsing/composing. Returned identities use package
anchors; original metadata claims do not grant native or model qualification.
"""
from hashlib import sha256
from importlib import resources
import json
import re

from .cif_linked_preparation import component_values

ANCHOR = 'nasolve:data/chemical_references'
POLICY_ID = 'cif-packaged-chemical-reference-v1'
COMPOSITION_POLICY_ID = 'cif-packaged-deoxy-source-composition-v1'


def _reference(name, data):
    return dict(anchor=ANCHOR, path=name, sha256=sha256(data).hexdigest(), size=len(data))


def _directory():
    return resources.files('nasolve').joinpath('data/chemical_references')


def read_packaged_reference(code):
    """Return exact definition bytes, metadata and package-bound identities.

    Only the exact laboratory code is looked up. No local-folder/CCD search,
    alias inference, numerical generation or interpretation of qualification
    claims in descriptive metadata occurs here.
    """
    if not isinstance(code, str) or re.fullmatch('[A-Z0-9]{1,3}', code) is None:
        raise ValueError('Require an exact PDB-compatible packaged reference code')
    directory = _directory()
    manifest, definition = directory.joinpath(code + '.json'), directory.joinpath(code + '.cif')
    raw = manifest.read_bytes()
    metadata = json.loads(raw)
    if (not isinstance(metadata, dict) or type(metadata.get('schema_version')) is not int
            or metadata['schema_version'] != 1 or metadata.get('kind') != 'NASolve packaged chemical reference'
            or not isinstance(metadata.get('identity'), dict)
            or metadata['identity'].get('laboratory_code') != code
            or not isinstance(metadata.get('definition'), dict)):
        raise ValueError('Packaged chemical reference identity/schema differs')
    declared = metadata['definition']
    if (declared.get('anchor') != ANCHOR or declared.get('path') != code + '.cif'
            or not isinstance(declared.get('sha256'), str)
            or re.fullmatch('[0-9a-f]{64}', declared['sha256']) is None):
        raise ValueError('Packaged reference needs its exact local resource identity')
    data = definition.read_bytes()
    if sha256(data).hexdigest() != declared['sha256']:
        raise ValueError('Packaged chemical definition checksum differs')
    with resources.as_file(definition) as path:
        if path.read_bytes() != data:
            raise ValueError('Packaged definition changed before parsing')
        component_values(path, code)
    if manifest.read_bytes() != raw or definition.read_bytes() != data:
        raise ValueError('Packaged reference changed while reading')
    return dict(schema_version=1, policy_id=POLICY_ID, definition=data, metadata=metadata,
                source=_reference(code + '.cif', data), manifest=_reference(code + '.json', raw),
                native_qualification='NOT_RUN', automatic_adoption=False)


def compose_packaged_dna_source(backbone_source, backbone_code, reference_code, *, component):
    """Use the existing explicit compositor with an exact packaged reference.

    The caller still chooses the backbone, hand, source phosphate state and
    resulting component. This emits source bytes, not numerical restraints or a
    model; linked/terminal qualification and mutation activation remain separate.
    """
    from .cif_reference_composition import compose_dna_source
    selected = read_packaged_reference(reference_code)
    definition = _directory().joinpath(selected['source']['path'])
    with resources.as_file(definition) as path:
        if path.read_bytes() != selected['definition']:
            raise ValueError('Packaged reference changed before composition')
        data, composition = compose_dna_source(backbone_source, backbone_code, path,
                                              reference_code, component=component)
    if read_packaged_reference(reference_code) != selected:
        raise ValueError('Packaged reference changed during composition')
    return data, dict(schema_version=1, policy_id=COMPOSITION_POLICY_ID, component=component,
        source=selected['source'], manifest=selected['manifest'], composition=composition,
        output_sha256=sha256(data).hexdigest(), native_qualification='NOT_RUN', automatic_adoption=False)
