"""Bounded atom-level observations for one explicitly selected periodic image.

Exact operators identify images. Coordinate coincidences are tolerance-bound
observations, never permission to merge source identities or adopt a connection.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from itertools import combinations_with_replacement, product
import json
import math
from pathlib import Path

from .topostitch_coordinates import _read_atoms, _residue, _Unassessed
from .topostitch_periodic import (
    _crystal, _image_record, _op_key, inspect_periodic_end_assignments,
)

_PADDING = 1e-7
_MAX_COINCIDENCES = 10_000


class _Budget:
    def __init__(self, maximum):
        if type(maximum) is not int or maximum < 1:
            raise ValueError('max_atom_tests must be a positive integer')
        self.maximum, self.used = maximum, 0

    def spend(self, count=1):
        if self.used + count > self.maximum:
            raise ValueError('Atom image audit budget exceeded; no partial audit returned')
        self.used += count


def _validate_options(tolerance, maximum):
    if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 0 < tolerance <= .05:
        raise ValueError('Coincidence tolerance must be finite and in (0, 0.05] Angstrom')
    return _Budget(maximum)


def _cartesian(fractional, cell, gemmi):
    return tuple(cell.orthogonalize(gemmi.Fractional(*fractional)))


def _fractional(xyz, cell, gemmi):
    point = tuple(cell.fractionalize(gemmi.Position(*xyz)))
    if any(not math.isfinite(v) or abs(v) > 1e6 for v in point):
        raise ValueError('Fractional atom coordinates exceed the supported numerical range')
    return point


def _append(rows, value):
    if len(rows) >= _MAX_COINCIDENCES:
        raise ValueError('Atom image coincidence record budget exceeded; no partial audit returned')
    rows.append(value)


def _orbit_contacts(points, cell, group, gemmi, tolerance, budget):
    """Find selected-source atom orbit coincidences, including self stabilizers.

    Enumerate metric-bounded lattice shifts, not component-wise nearest images.
    Distinct source atoms remain distinct even when their orbits coincide. The
    trivial identity of an atom with itself is omitted, not counted as evidence.
    """
    fractions = [_fractional(p,cell,gemmi) for p in points]
    ops = sorted(group.operations(),key=_op_key)
    # Count each atom-pair/operator screening and each exact distance evaluation.
    # Reserve screening work before any potentially large output is accumulated.
    budget.spend(len(points)*(len(points)+1)//2*len(ops))
    bounds = [(tolerance+_PADDING)*math.hypot(*row)+1e-9 for row in cell.frac.mat.tolist()]
    transformed = [[op.apply_to_xyz(p) for p in fractions] for op in ops]
    contacts = []
    for i,j in combinations_with_replacement(range(len(points)),2):
        for k,op in enumerate(ops):
            center = [a-b for a,b in zip(fractions[i],transformed[k][j])]
            intervals = [(math.ceil(c-b),math.floor(c+b)) for c,b in zip(center,bounds)]
            count = math.prod(max(0,hi-lo+1) for lo,hi in intervals)
            budget.spend(count)
            for shift in product(*(range(lo,hi+1) for lo,hi in intervals)):
                full = op.translated([op.DEN*n for n in shift])
                if i == j and full.triplet() == 'x,y,z':
                    continue
                target = _cartesian([v+n for v,n in zip(transformed[k][j],shift)],cell,gemmi)
                distance = math.dist(points[i],target)
                if distance <= tolerance+_PADDING:
                    _append(contacts,{'source_atom_index':i,'target_atom_index':j,
                        'target_image':_image_record(full,gemmi),
                        'distance_angstrom':distance,
                        'relation':'SELF_STABILIZER_OBSERVATION' if i==j else 'DISTINCT_SOURCE_ORBITS_COINCIDE'})
    return contacts


def _selected_overlap(points, left, right, op, cell, gemmi, tolerance, budget):
    """Compare the exact selected images without wrapping away their translation."""
    budget.spend(len(left)*len(right))
    images = {j:_cartesian(op.apply_to_xyz(_fractional(points[j],cell,gemmi)),cell,gemmi) for j in right}
    contacts = []
    for i in left:
        for j in right:
            distance = math.dist(points[i],images[j])
            if distance <= tolerance+_PADDING:
                _append(contacts,{'source_atom_index':i,'target_atom_index':j,
                    'distance_angstrom':distance,
                    'relation':'SAME_SOURCE_ATOM_IMAGE' if i==j else 'DISTINCT_SOURCE_ATOMS_COINCIDE'})
    return contacts


def _attach_image_audit(model_path, assignments, report, *, candidate_index,
                        coincidence_tolerance_angstrom=.01, max_atom_tests=2_000_000):
    """Internal adapter: report must come from this call's fresh periodic screen."""
    budget = _validate_options(coincidence_tolerance_angstrom,max_atom_tests)
    screen = report['periodic_screening']
    if type(candidate_index) is not int or not 0 <= candidate_index < len(screen['candidates']):
        raise ValueError('candidate_index must select an existing periodic candidate')
    edge = screen['candidates'][candidate_index]
    data = Path(model_path).read_bytes()
    digest = sha256(data).hexdigest()
    if digest != report['source_model_sha256']:
        raise ValueError('Source model checksum changed during atom image audit')
    gemmi,cell,group = _crystal(screen['inputs']['cell_parameters'],screen['inputs']['space_group'])
    inventory = _read_atoms(data)
    by_id = {a.end_id:a for a in assignments}
    left,right = (by_id[e] for e in edge['ends'])
    def sites(end):
        return set(end.overhang_sites+end.terminal_pair+end.inner_pair)
    selected = sorted(sites(left)|sites(right),key=lambda s:(s.chain,s.residue_number,s.insertion_code))
    atoms,issues = [],[]
    for site in selected:
        try:
            _residue(inventory,site)
        except _Unassessed as exc:
            issues.append({'code':exc.code,'site':asdict(site)})
            continue
        rows = sorted(next(iter(inventory[site].values())),key=lambda a:a[0])
        for name,code,alt,xyz,occupancy in rows:
            if occupancy is None or not math.isfinite(occupancy) or not 0 < occupancy <= 1:
                issues.append({'code':'UNUSABLE_OCCUPANCY','site':asdict(site),'atom_name':name})
            atoms.append({'site':asdict(site),'atom_name':name,'residue_code':code,
                          'position_angstrom':list(xyz),'occupancy':occupancy if occupancy is not None and math.isfinite(occupancy) else None,
                          'source_atom_index':len(atoms)})
    scope = {name:[a['source_atom_index'] for a in atoms if a['site'] in [asdict(s) for s in sites(end)]]
             for name,end in (('source',left),('target',right))}
    inputs = {'source_model_sha256':digest,
        'assignments_sha256':report['coordinate_assessment']['assignments_sha256'],
        'periodic_screen_input_sha256':screen['input_sha256'],
        'candidate_index':candidate_index,'ends':edge['ends'],'target_image':edge['target_image'],
        'coincidence_tolerance_angstrom':float(coincidence_tolerance_angstrom),
        'numerical_padding_angstrom':_PADDING,'max_atom_tests':max_atom_tests,
        'max_coincidence_records_per_section':_MAX_COINCIDENCES}
    result = {'schema_version':1,'kind':'topostitch-selected-image-identity',
        'algorithm':'selected-atom-orbit-coincidence-v1','gemmi_version':gemmi.__version__,
        'source_model_sha256':digest,'source_bytes_verified':True,'candidate_index':candidate_index,
        'inputs':inputs,'input_sha256':sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'atom_scope':'present atoms of overhang, terminal and inner-pair residues at the two selected ends',
        'atoms':atoms,'end_atom_indices':scope,'issues':issues,
        'orbit_contacts':[],'selected_image_overlaps':[],
        'selected_atom_sets_disjoint':None,'atom_tests':0,'assessment':'UNASSESSED',
        'physical_identity_validated':False,'geometry_validated':False,'runtime_authority':False,
        'identities_merged':False,'changes':[],
        'limitations':['Coincidence is a coordinate observation at the recorded tolerance, not an identity merge',
            'Only present selected atoms are assessed; omitted atoms and the rest of the crystal are not a packing audit',
            'Partial occupancies and coordinate uncertainty require review; alternate/ambiguous selected sites are unsupported',
            'No partner capacity, covalent closure, ASU-cut invariance, diffraction or connection acceptance is granted']}
    if not issues:
        points = [a['position_angstrom'] for a in atoms]
        result['orbit_contacts'] = _orbit_contacts(points,cell,group,gemmi,coincidence_tolerance_angstrom,budget)
        result['selected_image_overlaps'] = _selected_overlap(points,scope['source'],scope['target'],
            gemmi.Op(edge['target_image']['operator_xyz']),cell,gemmi,coincidence_tolerance_angstrom,budget)
        result['selected_atom_sets_disjoint'] = not result['selected_image_overlaps']
        result['atom_tests'] = budget.used
        ambiguous = result['orbit_contacts'] or result['selected_image_overlaps'] or any(a['occupancy']<1 for a in atoms)
        result['assessment'] = 'COINCIDENCE_OR_OCCUPANCY_REVIEW' if ambiguous else 'SELECTED_COORDINATES_DISTINCT'
    report['selected_image_identity'] = result
    return report



def _audit_transformed_image(data, source_audit, *, cell_parameters, space_group):
    """Recheck generated bytes against this fit's fresh, exact source selection.

    No new search or candidate-index lookup is performed after moving atoms.
    This internal helper accepts only identity-preserving renderer output.
    """
    from .topostitch_coordinates import ResidueSite
    options=source_audit['inputs'];tolerance=options['coincidence_tolerance_angstrom']
    budget=_validate_options(tolerance,options['max_atom_tests'])
    gemmi,cell,group=_crystal(cell_parameters,space_group)
    inventory=_read_atoms(data);expected={}
    for atom in source_audit['atoms']:
        site=ResidueSite(**atom['site']);expected.setdefault(site,{})[atom['atom_name']]=atom
    atoms=[];points_by_site={}
    for site,old in expected.items():
        _,points_by_site[site]=_residue(inventory,site)
        rows=next(iter(inventory[site].values()))
        actual={name:(code,occupancy) for name,code,alt,xyz,occupancy in rows}
        if actual!={name:(a['residue_code'],a['occupancy']) for name,a in old.items()}:
            raise ValueError('Generated candidate changed selected atom identities or occupancy')
    for atom in source_audit['atoms']:
        atoms.append({**atom,'position_angstrom':list(points_by_site[ResidueSite(**atom['site'])][atom['atom_name']])})
    points=[a['position_angstrom'] for a in atoms];scope=source_audit['end_atom_indices']
    orbit=_orbit_contacts(points,cell,group,gemmi,tolerance,budget)
    overlaps=_selected_overlap(points,scope['source'],scope['target'],
        gemmi.Op(options['target_image']['operator_xyz']),cell,gemmi,tolerance,budget)
    inputs={'candidate_model_sha256':sha256(data).hexdigest(),
        'source_model_sha256':source_audit['source_model_sha256'],
        'source_audit_input_sha256':source_audit['input_sha256'],
        'cell_parameters':list(cell_parameters),'space_group':space_group,
        'ends':options['ends'],'target_image':options['target_image'],
        'coincidence_tolerance_angstrom':tolerance,'numerical_padding_angstrom':_PADDING,
        'max_atom_tests':options['max_atom_tests'],'max_coincidence_records_per_section':_MAX_COINCIDENCES}
    return {'schema_version':1,'kind':'topostitch-transformed-image-identity',
        'algorithm':'fixed-selected-image-after-transform-v1','gemmi_version':gemmi.__version__,
        **inputs,'inputs':inputs,'input_sha256':sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'selection_basis':'Exact source selection and image; no post-transform candidate search',
        'atoms':atoms,'end_atom_indices':scope,'orbit_contacts':orbit,'selected_image_overlaps':overlaps,
        'selected_atom_sets_disjoint':not overlaps,'atom_tests':budget.used,
        'assessment':'COINCIDENCE_OR_OCCUPANCY_REVIEW' if orbit or overlaps or any(a['occupancy']<1 for a in atoms) else 'SELECTED_COORDINATES_DISTINCT',
        'physical_identity_validated':False,'geometry_validated':False,'runtime_authority':False,
        'limitations':['Present selected atoms only; no full packing, van der Waals or closure qualification',
            'Coincidence observations never merge source identities or approve a connection']}

def inspect_periodic_image_identity(model_path, assignments, *, expected_sha256,
        max_distance_angstrom, candidate_index, coincidence_tolerance_angstrom=.01,
        max_atom_tests=2_000_000, max_pairs=100_000, max_image_tests=100_000):
    """Inspect one candidate from a fresh verified search, with no identity merging.

    Candidate indices belong to the recorded exact search inputs, not a durable
    connection ID. No externally supplied candidate report is trusted here.
    """
    _validate_options(coincidence_tolerance_angstrom,max_atom_tests)
    assignments = tuple(assignments)
    report = inspect_periodic_end_assignments(model_path,assignments,expected_sha256=expected_sha256,
        max_distance_angstrom=max_distance_angstrom,max_pairs=max_pairs,max_image_tests=max_image_tests)
    return _attach_image_audit(model_path,assignments,report,candidate_index=candidate_index,
        coincidence_tolerance_angstrom=coincidence_tolerance_angstrom,max_atom_tests=max_atom_tests)
