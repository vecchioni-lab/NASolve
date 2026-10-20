"""Project declared restraint-dictionary chemistry into the CCD reader dialect.

Unknown atom aromaticity/CIP metadata stays unknown. Signed chiral volumes and
all original fields survive; this format adapter is not chemical perception.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .cif_doctor import assess_dictionaries, compare_dictionaries, _number, _ORDERS
from .cif_linked_preparation import component_values
from .ligand_profiles import _emit, _blocks

POLICY_ID = 'cif-declared-chemistry-ccd-reader-projection-v1'
_MISSING = {'', '.', '?'}


def _choice(values, fields, count, normalize):
    columns = [values[k] for k in fields if k in values]
    if any(len(column) != count for column in columns):
        raise ValueError('Incomplete reader-dialect column')
    result = []
    for i in range(count):
        known = {normalize(column[i]) for column in columns if column[i] not in _MISSING}
        if len(known) > 1:
            raise ValueError('Conflicting reader-dialect declarations: '+', '.join(fields))
        result.append(next(iter(known)) if known else '?')
    return result


def _flag(value):
    value = value.upper()
    if value not in {'Y', 'N'}:
        raise ValueError('Unsupported declared aromatic flag')
    return value


def _stereo(value):
    value = value.upper()
    if value not in {'R', 'S', 'N'}:
        raise ValueError('Unsupported declared atom stereo configuration')
    return value


def _charge(value):
    n = _number(value)
    if n is None or not n.is_integer() or abs(n) > 9:
        raise ValueError('Require a representable explicit integer formal charge')
    return str(int(n))


def _order(value):
    normalized = _ORDERS.get(value.upper())
    if normalized not in {'SINGLE', 'DOUBLE', 'TRIPLE'}:
        raise ValueError('CCD reader projection cannot invent a localized bond order')
    return {'SINGLE':'SING', 'DOUBLE':'DOUB', 'TRIPLE':'TRIP'}[normalized]


def _projection(values):
    lookup = {k.lower():v for k,v in values.items()}
    if len(lookup) != len(values):
        raise ValueError('Ambiguous case variants in reader input')
    a, b = '_chem_comp_atom.', '_chem_comp_bond.'
    na, nb = len(lookup[a+'atom_id']), len(lookup[b+'atom_id_1'])
    return {
        a+'charge':_choice(lookup,[a+'charge',a+'pdbx_formal_charge'],na,_charge),
        a+'pdbx_aromatic_flag':_choice(lookup,[a+'pdbx_aromatic_flag',a+'aromatic'],na,_flag),
        a+'pdbx_stereo_config':_choice(lookup,[a+'pdbx_stereo_config',a+'stereo_config'],na,_stereo),
        b+'value_order':_choice(lookup,[b+'value_order',b+'type'],nb,_order),
        b+'pdbx_aromatic_flag':_choice(lookup,[b+'pdbx_aromatic_flag',b+'aromatic'],nb,_flag),
    }


def prepare_elbow_ccd_input(source, code, output):
    """Preserve source bytes and known declarations; add reader aliases/unknowns."""
    source, output = Path(source).resolve(strict=True), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Reader input output already exists')
    if output.resolve() == source or any(p.is_symlink() for p in output.parents):
        raise ValueError('Reader input must be a separate regular output')
    original = source.read_bytes()
    assessment = assess_dictionaries([source], stage='ccd-reader-projection')
    if (len(assessment['components']) != 1 or assessment['components'][0]['component_id'] != code
            or assessment['components'][0]['verdicts']['graph'] != 'PASS'):
        raise ValueError('Require one graph-valid component for reader projection')
    values = component_values(source, code)
    projected = _projection(values)
    lookup = {k.lower():k for k in values}
    converted = deepcopy(values)
    added, changed = [], []
    for key, column in projected.items():
        actual = lookup.get(key, key)
        if actual not in values:
            added.append(key)
        elif values[actual] != column:
            changed.append(key)
        converted[actual] = column
    # Existing aliases and every non-consumer field (including signed chirality,
    # bond stereo, exact IDs, H and coordinates) remain verbatim parsed values.
    if any(converted[k] != v for k,v in values.items() if k.lower() not in projected):
        raise ValueError('Reader projection changed an unrelated declaration')
    if _projection(converted) != projected:
        raise ValueError('Reader projection changed known chemistry')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle:
        handle.write(_emit(converted).encode() if added or changed else original)
    restored = component_values(output, code)
    if (_projection(restored) != projected or any(restored[k] != v for k,v in values.items() if k.lower() not in projected)):
        raise ValueError('Serialized reader projection changed declarations')
    if source.read_bytes() != original:
        raise ValueError('Original graph source changed')
    atom_ids = values['_chem_comp_atom.atom_id']
    return {'schema_version':1, 'policy_id':POLICY_ID, 'component':code,
        'source_sha256':sha256(original).hexdigest(), 'consumer_sha256':sha256(output.read_bytes()).hexdigest(),
        'source_preserved':True, 'known_chemical_declarations':'PRESERVED',
        'added_fields':sorted(added), 'changed_fields':sorted(changed),
        'unknown_atom_metadata':{k:[atom_ids[i] for i,v in enumerate(column) if v=='?']
            for k,column in projected.items() if k.startswith('_chem_comp_atom.') and '?' in column},
        'raw_comparison':compare_dictionaries([source],[output]),
        'signed_chirality':'ORIGINAL_DECLARATIONS_PRESERVED', 'stereochemistry_inferred':False,
        'aromaticity_perceived':False, 'numerical_targets_inferred':False,
        'chemical_qualification':'NOT_RUN', 'automatic_adoption':False}
