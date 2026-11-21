"""Read-only measurements of explicitly assigned nucleic-acid pairs.

Default mode measures Cartesian P--P spans, not screw-axis radii. The explicit
simple-twist mode reuses the separate canonical frame reader. Assignments declare
pairing; neither mode infers or validates it. Single-model PDB, identity images.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from .topostitch_coordinates import ResidueSite, _read_atoms
from .topostitch_recipe import recipe_digest

METHOD = 'declared-pair-phosphate-span-v1'


def _label(value, name):
    if not isinstance(value, str) or not value or value.strip() != value or any(ord(c) < 32 for c in value):
        raise ValueError(f'{name} must be a nonempty printable label')


@dataclass(frozen=True)
class HelicalSite:
    """Exact residue/conformer identity; component names are never canonicalized."""

    chain: str
    residue_number: int
    component: str
    insertion_code: str = ''
    altloc: str = ''
    operator_xyz: str = 'x,y,z'

    def __post_init__(self):
        ResidueSite(self.chain, self.residue_number, self.insertion_code)
        if not isinstance(self.component, str) or re.fullmatch(r'[A-Za-z0-9]{1,3}', self.component) is None:
            raise ValueError('component must be the exact PDB component name')
        if not isinstance(self.altloc, str) or re.fullmatch(r'[A-Za-z0-9]?', self.altloc) is None:
            raise ValueError('altloc must be empty or one alphanumeric character')
        if self.operator_xyz != 'x,y,z':
            raise ValueError('Only the explicitly declared identity image x,y,z is qualified')

    def coordinate_site(self):
        return ResidueSite(self.chain, self.residue_number, self.insertion_code)


def _physical_site(site):
    # A component label or conformer choice cannot create another physical residue.
    return site.chain, site.residue_number, site.insertion_code, site.operator_xyz


@dataclass(frozen=True)
class DeclaredPair:
    pair_id: str
    strand_i: HelicalSite
    strand_ii: HelicalSite
    role: str = 'core'
    break_before: bool = False

    def __post_init__(self):
        _label(self.pair_id, 'pair_id')
        if not isinstance(self.strand_i, HelicalSite) or not isinstance(self.strand_ii, HelicalSite):
            raise ValueError('Both strands require explicit HelicalSite records')
        if _physical_site(self.strand_i) == _physical_site(self.strand_ii):
            raise ValueError('A pair requires two distinct physical residues')
        if self.role not in ('core', 'flank') or type(self.break_before) is not bool:
            raise ValueError('Require core/flank role and boolean break_before')


@dataclass(frozen=True)
class PairedRegion:
    """Caller-ordered pairs, including declared flanks and breaks.

    model_index=0 selects the only coordinate model (ordinal, not MODEL serial).
    pair_id is a caller-maintained logical correspondence, not an inferred match.
    """

    region_id: str
    pairs: tuple[DeclaredPair, ...]
    model_index: int = 0

    def __post_init__(self):
        _label(self.region_id, 'region_id')
        if type(self.model_index) is not int or self.model_index != 0:
            raise ValueError('Only single-model PDB model_index=0 is supported')
        if not isinstance(self.pairs, (list, tuple)) or not self.pairs or any(not isinstance(p, DeclaredPair) for p in self.pairs):
            raise ValueError('Region requires a nonempty ordered list of DeclaredPair records')
        object.__setattr__(self, 'pairs', tuple(self.pairs))
        if len({p.pair_id for p in self.pairs}) != len(self.pairs):
            raise ValueError('Logical pair IDs must be unique within a region')
        sites = [_physical_site(s) for p in self.pairs for s in (p.strand_i, p.strand_ii)]
        if len(set(sites)) != len(sites):
            raise ValueError('A physical residue cannot occupy multiple declared pairs')


def _site_atom(atoms, site, atom_name, *, missing_reason='MISSING_ATOM',
               ambiguous_reason='AMBIGUOUS_ATOM'):
    result = dict(site=asdict(site), atom_name=atom_name, status='UNAVAILABLE', reason=None)

    def absent(reason):
        return {**result, 'reason': reason}

    groups = atoms.get(site.coordinate_site())
    if not groups:
        return absent('MISSING_RESIDUE')
    if len(groups) != 1:
        return absent('AMBIGUOUS_RESIDUE')
    rows = next(iter(groups.values()))
    if site.altloc and not any(row[2] == site.altloc for row in rows):
        return absent('MISSING_CONFORMER')
    if not site.altloc and any(row[0] == atom_name and row[2] for row in rows):
        return absent('ALTERNATE_CONFORMER_REQUIRED')
    candidates = [row for row in rows if row[2] in ('', site.altloc)]
    if not candidates or {row[1] for row in candidates} != {site.component}:
        return absent('COMPONENT_MISMATCH')
    phosphates = [row for row in candidates if row[0] == atom_name]
    if not phosphates:
        return absent(missing_reason)
    if len(phosphates) != 1:
        return absent(ambiguous_reason)
    name, component, altloc, xyz, occupancy = phosphates[0]
    if occupancy is None or not math.isfinite(occupancy) or not 0 < occupancy <= 1:
        return absent('UNUSABLE_OCCUPANCY')
    return {**result, 'status': 'AVAILABLE', 'actual_altloc': altloc,
            'component': component, 'xyz_angstrom': list(xyz), 'occupancy': occupancy}


def _phosphate(atoms, site):
    return _site_atom(atoms, site, 'P', missing_reason='MISSING_PHOSPHATE',
                      ambiguous_reason='AMBIGUOUS_PHOSPHATE')


def inspect_phosphate_spans(model_path, region, *, expected_model_sha256,
                            include_half_span=False):
    """Measure a byte-pinned model without writing or assigning scientific approval.

    Returned paths are relative to the caller-supplied model's directory. To
    relocate, pass the new explicit model path; no basename search is performed.
    Missing sites/atoms stay per-pair unavailable. Structural ambiguities in the
    file or declaration are refused, rather than silently choosing a model/image.
    """
    if not isinstance(region, PairedRegion):
        raise ValueError('region must be a PairedRegion')
    if not isinstance(expected_model_sha256, str) or re.fullmatch('[0-9a-f]{64}', expected_model_sha256) is None:
        raise ValueError('Require a lowercase SHA256 model hash')
    if type(include_half_span) is not bool:
        raise ValueError('include_half_span must be boolean')
    path = Path(model_path)
    payload = path.read_bytes()
    if sha256(payload).hexdigest() != expected_model_sha256:
        raise ValueError('Model hash differs from the declared source')
    atoms = _read_atoms(payload)
    declaration = json.loads(json.dumps(asdict(region)))
    rows = []
    for pair in region.pairs:
        phosphates = [_phosphate(atoms, s) for s in (pair.strand_i, pair.strand_ii)]
        available = all(p['status'] == 'AVAILABLE' for p in phosphates)
        distance = math.dist(*(p['xyz_angstrom'] for p in phosphates)) if available else None
        row = dict(pair_id=pair.pair_id, role=pair.role, break_before=pair.break_before,
                   status='MEASURED' if available else 'UNAVAILABLE', phosphates=phosphates,
                   distance_angstrom=distance)
        if include_half_span:
            row['half_span_angstrom'] = distance/2 if distance is not None else None
        rows.append(row)
    # Detect changes during reading; this is not a filesystem lock.
    if path.read_bytes() != payload:
        raise ValueError('Model bytes changed during measurement')
    measured = sum(r['status'] == 'MEASURED' for r in rows)
    return dict(schema_version=1, kind='regional-phosphate-spans', method=METHOD,
                source={'anchor': 'model_directory', 'relative_path': path.name,
                        'sha256': expected_model_sha256, 'size': len(payload),
                        'format': 'PDB', 'model_index': 0},
                region=declaration, region_sha256=recipe_digest(declaration),
                pairs=rows, coverage={'declared_pairs': len(rows), 'measured_pairs': measured,
                                     'unavailable_pairs': len(rows)-measured},
                axis_radii={'status': 'NOT_MEASURED', 'reason': 'P–P half-span is not a local-axis radius'},
                simple_step_twist={'status': 'NOT_MEASURED'},
                assignment_authority='CALLER_DECLARED', pairing_validated=False,
                runtime_authority=False, coordinate_changes=False)


def _region_from_json(value):
    if not isinstance(value, dict):
        raise ValueError('Region JSON must be an object')
    values = dict(value)
    values['pairs'] = [DeclaredPair(**{**pair,
        'strand_i': HelicalSite(**pair['strand_i']),
        'strand_ii': HelicalSite(**pair['strand_ii'])}) for pair in values['pairs']]
    return PairedRegion(**values)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--region', required=True, type=Path, help='Explicit PairedRegion JSON')
    parser.add_argument('--sha256', required=True, help='Expected model SHA256')
    parser.add_argument('--half-span', action='store_true')
    parser.add_argument('--simple-twist', action='store_true', help='Opt into canonical simple-step twist; requires topology extra')
    parser.add_argument('--max-ring-fit-rmsd', type=float, help='Explicit maximum canonical ring-fit RMSD in angstroms')
    args = parser.parse_args(argv)
    try:
        region = _region_from_json(json.loads(args.region.read_text()))
        if args.simple_twist:
            from .helical_twist import inspect_helical_region
            result = inspect_helical_region(args.model, region, expected_model_sha256=args.sha256,
                include_half_span=args.half_span, max_ring_fit_rmsd_angstrom=args.max_ring_fit_rmsd)
        else:
            if args.max_ring_fit_rmsd is not None:
                raise ValueError('--max-ring-fit-rmsd requires --simple-twist')
            result = inspect_phosphate_spans(args.model, region, expected_model_sha256=args.sha256,
                                            include_half_span=args.half_span)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    # Keep CLI declarations identical to the classes used by optional adapters.
    from .helical_geometry import main as _installed_main
    _installed_main()
