"""Exact caller-supplied coordinate identities and reusable NARestraints roles.

No structure-file parser or native selection string is hidden here. Source hashes
are supplied by an importer; the independently calculated inventory fingerprint
binds every atom/coordinate actually passed to this preview layer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Mapping, Sequence

from ..component_records import resolve_component_record, role_signature
from .recipe import RecipeError, canonical, checksum, digest, element, number, text


@dataclass(frozen=True, kw_only=True)
class ResidueKey:
    model_id: str
    chain_id: str
    residue_id: str
    component_id: str
    insertion_code: str = ''
    altloc: str = ''
    segment_id: str = ''
    symmetry: str = 'x,y,z'

    def __post_init__(self):
        for key in ('model_id', 'residue_id', 'component_id', 'symmetry'):
            text(getattr(self, key), key)
        for key in ('chain_id', 'insertion_code', 'altloc', 'segment_id'):
            text(getattr(self, key), key, empty=True)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, kw_only=True)
class AtomKey(ResidueKey):
    atom_name: str

    def __post_init__(self):
        super().__post_init__()
        text(self.atom_name, 'atom_name')

    def residue(self) -> ResidueKey:
        row = self.to_dict()
        del row['atom_name']
        return ResidueKey(**row)


@dataclass(frozen=True)
class Atom:
    key: AtomKey
    element: str
    xyz: tuple[float, float, float]

    def __post_init__(self):
        if not isinstance(self.key, AtomKey):
            raise RecipeError('Atom requires an exact AtomKey')
        element(self.element)
        if not isinstance(self.xyz, (tuple, list)) or len(self.xyz) != 3:
            raise RecipeError('Require three Cartesian coordinates in angstroms')
        object.__setattr__(self, 'xyz', tuple(number(v, 'coordinate') for v in self.xyz))

    def to_dict(self) -> dict:
        return {'key': self.key.to_dict(), 'element': self.element, 'xyz': list(self.xyz)}


@dataclass(frozen=True)
class ModelSnapshot:
    atoms: tuple[Atom, ...]
    source_sha256: str
    checkpoint_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.atoms, (list, tuple)) or any(not isinstance(a, Atom) for a in self.atoms):
            raise RecipeError('Require an explicit atom inventory')
        object.__setattr__(self, 'atoms', tuple(self.atoms))
        checksum(self.source_sha256, 'model.source_sha256')
        if self.checkpoint_id is not None:
            text(self.checkpoint_id, 'checkpoint_id')

    def to_dict(self) -> dict:
        return {'source_sha256': self.source_sha256, 'checkpoint_id': self.checkpoint_id,
                'atoms': [a.to_dict() for a in self.atoms]}

    @property
    def fingerprint(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True, init=False)
class RoleMap:
    """Snapshot an explicit effective workbook-record set and its source digest.

    Shared component resolution preserves equivalent descriptive aliases and
    refuses operational conflicts. No live workbook discovery or correction is
    performed; any upstream correction must be included in supplied provenance.
    """
    _json: str = field(repr=False)
    source_sha256: str
    source_label: str

    def __init__(self, records: Sequence[Mapping], *, source_sha256: str, source_label: str):
        checksum(source_sha256, 'roles.source_sha256')
        text(source_label, 'roles.source_label')
        if not isinstance(records, (list, tuple)) or any(not isinstance(r, dict) for r in records):
            raise RecipeError('Require an explicit list of role records')
        for record in records:
            text(record.get('Ligand code'), 'role record Ligand code')
        object.__setattr__(self, '_json', canonical(records))
        object.__setattr__(self, 'source_sha256', source_sha256)
        object.__setattr__(self, 'source_label', source_label)

    def records(self) -> list[dict]:
        return json.loads(self._json)

    def to_dict(self) -> dict:
        return {'source_sha256': self.source_sha256, 'source_label': self.source_label,
                'records': self.records()}

    @property
    def fingerprint(self) -> str:
        return digest(self.to_dict())

    def resolve(self, component: str, role: str) -> tuple[str | None, dict | None, list[str]]:
        records = self.records()
        if not any(row['Ligand code'] == component for row in records):
            return None, None, ['missing_role_record']
        try:
            selected, proof = resolve_component_record(records, component)
        except ValueError:
            return None, None, ['ambiguous_role_record']
        # Descriptive/annotation columns must never become atom selectors.
        if role not in role_signature(selected)['atom_roles']:
            return None, proof, ['missing_role']
        value = selected.get(role)
        if not isinstance(value, str) or not value.strip() or value.strip() in ('.', '?'):
            return None, proof, ['missing_role']
        return value.strip(), proof, []
