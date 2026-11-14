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


def _single_edge_capacity(audit, gemmi):
    """Bind exact edge incidence to this fresh selected-coordinate observation.

    This deliberately excludes global schemes and special-position equivalences.
    It never merges labels or uses a center as evidence of molecular identity.
    """
    from .topostitch_pairings import _periodic_incidence
    inputs = audit['inputs']; ends = inputs['ends']
    operator = gemmi.Op(inputs['target_image']['operator_xyz'])
    incidence = _periodic_incidence(ends, operator, gemmi)
    scopes = audit['end_atom_indices']
    shared = sorted(set(scopes['source']) & set(scopes['target']))
    issues = []
    if audit['assessment'] != 'SELECTED_COORDINATES_DISTINCT':
        issues.append('SELECTED_COORDINATE_IDENTITY_UNRESOLVED')
    if not scopes['source'] or not scopes['target']:
        issues.append('EMPTY_SELECTED_ATOM_SCOPE')
    if ends[0] != ends[1] and shared:
        issues.append('DISTINCT_END_LABELS_SHARE_SOURCE_ATOMS')
    identity_self = ends[0] == ends[1] and operator.triplet() == 'x,y,z'
    if identity_self:
        issues.append('IDENTITY_SELF_EDGE')
    status = ('CAPACITY_REVIEW_REQUIRED' if issues else
              'ONE_PARTNER_IN_SELECTED_SCOPE' if all(r['partner_count'] == 1 for r in incidence)
              else 'MULTIPLE_PARTNERS_IN_SELECTED_SCOPE')
    return {'schema_version': 1, 'kind': 'topostitch-single-edge-capacity',
        'source_model_sha256': audit['source_model_sha256'],
        'coordinate_evidence_sha256': sha256(json.dumps(audit,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
        'ends': list(ends), 'target_image': inputs['target_image'], 'incidence': incidence,
        'assessment': status, 'issues': issues, 'shared_source_atom_indices': shared,
        'one_partner_in_selected_scope': status == 'ONE_PARTNER_IN_SELECTED_SCOPE',
        'coordinate_basis': 'PRESENT_SELECTED_ATOMS_AT_RECORDED_COINCIDENCE_TOLERANCE',
        'coincidence_tolerance_angstrom': inputs['coincidence_tolerance_angstrom'],
        'lattice_translations_preserved': True, 'identities_merged': False,
        'global_assignment_validated': False, 'full_molecular_identity_validated': False,
        'geometry_validated': False, 'runtime_authority': False, 'connection_accepted': False,
        'limitations': ['One explicit undirected edge orbit, not a complete connection scheme',
            'Conditional on the selected present-atom coordinate audit and its tolerance',
            'Special-position, coincident-label and partial-occupancy cases require review',
            'No sequence/orientation approval, chemical linkage, recut or automatic adoption']}


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
    result['single_edge_capacity'] = _single_edge_capacity(result, gemmi)
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
    result = {'schema_version':1,'kind':'topostitch-transformed-image-identity',
        'algorithm':'fixed-selected-image-after-transform-v1','gemmi_version':gemmi.__version__,
        **inputs,'inputs':inputs,'input_sha256':sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'selection_basis':'Exact source selection and image; no post-transform candidate search',
        'atoms':atoms,'end_atom_indices':scope,'orbit_contacts':orbit,'selected_image_overlaps':overlaps,
        'selected_atom_sets_disjoint':not overlaps,'atom_tests':budget.used,
        'assessment':'COINCIDENCE_OR_OCCUPANCY_REVIEW' if orbit or overlaps or any(a['occupancy']<1 for a in atoms) else 'SELECTED_COORDINATES_DISTINCT',
        'physical_identity_validated':False,'geometry_validated':False,'runtime_authority':False,
        'limitations':['Present selected atoms only; no full packing, van der Waals or closure qualification',
            'Coincidence observations never merge source identities or approve a connection']}
    result['single_edge_capacity'] = _single_edge_capacity(result, gemmi)
    return result

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


def inspect_model_orbit_identity(model_path, *, expected_sha256,
                                 coincidence_tolerance_angstrom=.01, max_atom_tests=2_000_000):
    """Observe all present PDB atom orbits in exact source record order.

    Includes unregistered polymers, ligands, ions, waters and alternate records;
    none are silently dropped or merged. Coincidences and occupancy/identity
    ambiguity remain review findings, not a molecular or ASU-cut qualification.
    """
    from .topostitch_recipe import model_atom_rows
    from .topostitch_coordinates import ResidueSite
    from .topostitch_periodic import crystal_from_pdb_bytes
    from .topostitch_registration import _fingerprint
    budget = _validate_options(coincidence_tolerance_angstrom, max_atom_tests)
    data = Path(model_path).read_bytes()
    digest = sha256(data).hexdigest()
    if digest != expected_sha256:
        raise ValueError('Source model checksum mismatch')
    identities = model_atom_rows(data)
    residues = _read_atoms(data)
    gemmi, cell, name = crystal_from_pdb_bytes(data)
    group = gemmi.find_spacegroup_by_name(name)
    lines = [line for line in data.decode('ascii').splitlines() if line[:6] in ('ATOM  ', 'HETATM')]
    atoms, issues = [], []
    for index, (identity, line) in enumerate(zip(identities, lines)):
        site = ResidueSite(identity['chain'], identity['residue_number'], identity['insertion_code'])
        xyz = [float(line[a:b]) for a, b in ((30,38), (38,46), (46,54))]
        try:
            occupancy = float(line[54:60])
        except ValueError:
            occupancy = None
        codes = []
        if occupancy is None or not math.isfinite(occupancy) or not 0 < occupancy <= 1:
            codes.append('UNUSABLE_OCCUPANCY')
        elif occupancy < 1:
            codes.append('PARTIAL_OCCUPANCY')
        if identity['altloc']:
            codes.append('ALTERNATE_CONFORMER')
        groups = residues[site]
        if len(groups) != 1 or len({row[1] for group_rows in groups.values() for row in group_rows}) != 1:
            codes.append('AMBIGUOUS_COORDINATE_SITE')
        issues.extend({'source_atom_index': index, 'code': code} for code in codes)
        atoms.append({'source_atom_index': index, 'identity': identity,
                      'record_type': line[:6].strip(), 'position_angstrom': xyz,
                      'occupancy': occupancy if occupancy is not None and math.isfinite(occupancy) else None})
    contacts = _orbit_contacts([a['position_angstrom'] for a in atoms], cell, group, gemmi,
                               coincidence_tolerance_angstrom, budget)
    inputs = {'source_model_sha256': digest, 'cell_parameters': list(cell.parameters),
              'space_group': group.xhm(), 'coincidence_tolerance_angstrom': float(coincidence_tolerance_angstrom),
              'numerical_padding_angstrom': _PADDING, 'max_atom_tests': max_atom_tests,
              'max_coincidence_records': _MAX_COINCIDENCES}
    report = {'schema_version': 1, 'kind': 'topostitch-present-model-orbit-observation',
              'algorithm': 'present-model-atom-orbits-v1', 'gemmi_version': gemmi.__version__,
              'source_model_sha256': digest, 'source_bytes_verified': True,
              'inputs': inputs, 'input_sha256': _fingerprint(inputs), 'atoms': atoms,
              'atom_scope': 'Every present ATOM/HETATM record, in source order; no selection or chemistry filter',
              'orbit_contacts': contacts, 'issues': issues, 'atom_tests': budget.used,
              'assessment': 'MODEL_ORBIT_REVIEW' if contacts or issues else 'PRESENT_MODEL_COORDINATES_DISTINCT',
              'physical_identity_validated': False, 'identities_merged': False,
              'chemical_connectivity_validated': False, 'asu_cut_validated': False,
              'runtime_authority': False, 'changes': [],
              'limitations': ['Coordinate coincidences depend on the recorded tolerance and numerical padding',
                              'No omitted atoms, chemical identity, occupancy interpretation or molecular graph is inferred',
                              'Special positions and coincident source labels remain distinct review findings',
                              'No scattering, ADP, packing, geometry, recut or connection acceptance']}
    report['report_sha256'] = _fingerprint(report)
    if Path(model_path).read_bytes() != data:
        raise ValueError('Source model changed during orbit observation')
    return report
