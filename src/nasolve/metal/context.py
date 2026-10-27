"""Read-only bridge from generated NASolve checkpoints to the metal editor.

This adapter imports single-model PDB files without changing their bytes, uses
the existing checkpoint/path resolver, and snapshots effective PostMR roles.
It does not construct, place, refine or select a metal hypothesis.
"""
from dataclasses import dataclass, field
import hashlib
import importlib.metadata
import json
from pathlib import Path

from ..checkpoints import CheckpointError, read_registry, resolve_checkpoint, inherited_paths
from ..postmr import _patch_narestraints_records, PostMRPreparationError
from ..run_context import artifact_reference, dataset_directory
from .binding import Atom, AtomKey, ModelSnapshot, ResidueKey, RoleMap
from .recipe import RecipeError, canonical, digest, element, number, text
from .preview import preview


@dataclass(frozen=True)
class ImportedModel:
    snapshot: ModelSnapshot
    _state: str = field(repr=False)

    def to_dict(self):
        return {'model': self.snapshot.to_dict(), 'atomic_state': json.loads(self._state)}


def read_pdb(path: Path, *, checkpoint_id=None) -> ImportedModel:
    """Import exact PDB identity, XYZ, occupancy, B and optional ANISOU.

    One model only; no implicit element/occupancy defaults, alternate merging,
    symmetry expansion or mmCIF fallback. Unsupported input is a clear error.
    """
    try:
        raw = Path(path).read_bytes()
        lines = raw.decode('ascii').splitlines()
    except (OSError, UnicodeError) as exc:
        raise RecipeError(f'Cannot read PDB: {exc}') from exc
    atoms, states, identities, anisou = [], [], set(), {}
    model_id, model_count, ended = '1', 0, False

    def key(line):
        return AtomKey(model_id=model_id, chain_id=line[21:22].strip(),
                       residue_id=line[22:26].strip(), component_id=line[17:20].strip(),
                       insertion_code=line[26:27].strip(), altloc=line[16:17].strip(),
                       segment_id=line[72:76].strip(), atom_name=line[12:16].strip())

    for row, line in enumerate(lines, 1):
        kind = line[:6].strip()
        if kind == 'MODEL':
            model_count += 1
            if model_count > 1 or atoms or ended:
                raise RecipeError('Only a single PDB model is supported')
            model_id = line[10:14].strip()
            text(model_id, 'MODEL identifier')
        elif kind == 'ENDMDL':
            ended = True
        elif kind in {'ATOM', 'HETATM', 'ANISOU'}:
            if ended or len(line) < 78:
                raise RecipeError(f'Malformed or unsupported PDB record at line {row}')
            identity = key(line)
            if kind == 'ANISOU':
                if identity in anisou:
                    raise RecipeError('Duplicate ANISOU identity')
                try:
                    anisou[identity] = [int(line[start:start+7]) for start in (28, 35, 42, 49, 56, 63)]
                except ValueError as exc:
                    raise RecipeError(f'Invalid ANISOU at line {row}') from exc
                continue
            if identity in identities:
                raise RecipeError('Duplicate PDB atom identity')
            try:
                xyz = tuple(number(float(line[i:i+8]), 'coordinate') for i in (30, 38, 46))
                q = number(float(line[54:60]), 'occupancy')
                b = number(float(line[60:66]), 'B factor')
                symbol = element(line[76:78].strip().capitalize())
            except ValueError as exc:
                raise RecipeError(f'Invalid PDB atomic state at line {row}: {exc}') from exc
            identities.add(identity)
            atoms.append(Atom(identity, symbol, xyz))
            states.append({'key': identity.to_dict(), 'occupancy': q, 'b_iso': b,
                           'record': kind, 'anisou': None})
    if not atoms:
        raise RecipeError('PDB has no coordinate atoms')
    if anisou.keys() - identities:
        raise RecipeError('ANISOU has no matching atom')
    for atom, state in zip(atoms, states):
        state['anisou'] = anisou.get(atom.key)
    snapshot = ModelSnapshot(tuple(atoms), hashlib.sha256(raw).hexdigest(), checkpoint_id)
    return ImportedModel(snapshot, canonical(states))


def _reference(path, run):
    path = Path(path)
    ref = artifact_reference(path, run)
    if ref['anchor'] == 'absolute':
        raise RecipeError('Metal inputs must belong to a declared run, dataset or repository anchor')
    raw = path.read_bytes()
    return dict(ref, sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))


@dataclass(frozen=True)
class MetalContext:
    run: Path
    imported: ImportedModel
    roles: RoleMap
    _document: str = field(repr=False)

    def to_dict(self):
        return json.loads(self._document)

    @property
    def residue_slots(self):
        return {name: ResidueKey(**row) for name, row in self.to_dict()['residue_slots'].items()}

    def preview(self, recipe, *, atom_bindings=None):
        names = {node['residue_slot'] for node in recipe.to_dict()['nodes'] if node['kind'] == 'donor'}
        if names - self.residue_slots.keys():
            raise RecipeError('W recipes use the ordered residue slots first and second')
        result = preview(recipe, model=self.imported.snapshot, roles=self.roles,
                         residue_slots={k: v for k, v in self.residue_slots.items() if k in names},
                         atom_bindings=atom_bindings or {})
        result['context_id'] = self.to_dict()['context_id']
        return result


def load_run_context(run, *, checkpoint='postmr', dataset_id=None, records=None) -> MetalContext:
    """Read one explicit generated W checkpoint; never write a registry/pointer."""
    try:
        run, registry = read_registry(Path(run))
        selected = resolve_checkpoint(registry, checkpoint)
        if selected.get('usable') is not True:
            raise RecipeError('Selected checkpoint is not usable')
        paths = inherited_paths(selected, run)
        report = json.loads((run / 'report.json').read_text())
        if not isinstance(report.get('frame'), dict) or report['frame'].get('name') != 'W':
            raise RecipeError('This integration supports the explicit W/5W6W contract')
        sources = {key: _reference(paths[key], run) for key in ('model', 'observations')}
        sources['restraints'] = [_reference(p, run) for p in paths['restraints']]
        sources['report'] = _reference(run / 'report.json', run)
        sources['phases'] = _reference(paths['phases'], run) if paths['phases'] else None
        imported = read_pdb(paths['model'], checkpoint_id=selected['id'])
        if imported.snapshot.source_sha256 != sources['model']['sha256']:
            raise RecipeError('Model changed during import')
        slots = {}
        for slot, chain, residue in [('first', 'A', '12'), ('second', 'B', '4')]:
            candidates = {a.key.residue() for a in imported.snapshot.atoms
                          if a.key.chain_id == chain and a.key.residue_id == residue}
            if len(candidates) != 1:
                raise RecipeError(f'W {slot} site {chain}:{residue} is missing or ambiguous')
            candidate = next(iter(candidates))
            if candidate.insertion_code or candidate.altloc:
                raise RecipeError(f'W {slot} site requires an explicit alternate/insertion policy')
            slots[slot] = candidate.to_dict()
        codes = {row['component_id'] for row in slots.values()}
        if records is None:
            from restraints.residue_library import load_residue_records
            records = load_residue_records()
            version = importlib.metadata.version('NARestraints')
        else:
            version = 'explicit supplied records'
        raw_roles = [dict(r) for r in records if r.get('Ligand code') in codes]
        effective, corrections = _patch_narestraints_records(raw_roles, codes)
        roles = RoleMap(effective, source_sha256=digest(raw_roles),
                        source_label=f'NARestraints {version}; PostMR effective role corrections')
        dataset_id = dataset_id or dataset_directory(run).name
        text(dataset_id, 'dataset_id')
        doc = {'kind': 'metal-run-context', 'schema_version': 1, 'protocol': 'metal-run-context-v1',
               'dataset_id': dataset_id, 'run_id': run.name, 'checkpoint_id': selected['id'],
               'frame': 'W', 'residue_slots': slots, 'sources': sources,
               'roles': roles.to_dict(), 'role_corrections': corrections,
               **imported.to_dict(), 'fixed_f_prime': True, 'native_ready': False,
               'qualification': 'Imported generated model; metal geometry and refinement are not qualified'}
        doc['context_id'] = digest(doc)
        return MetalContext(run, imported, roles, canonical(doc))
    except (CheckpointError, PostMRPreparationError, OSError, ValueError, ImportError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError(str(exc)) from exc
