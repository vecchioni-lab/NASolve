"""Source-selected Cartesian trigonal geometry, independent of residue names.

Descriptive model measurements do not approve chemical targets, infer native
symmetry, or authorize flattening. C208 owns the bounded chemical selector.
"""
from hashlib import sha256
from itertools import combinations
from math import asin, degrees, hypot
from pathlib import Path

from .cif_attachment_sites import _model
from .cif_construction_provenance import _pdb_inventory
from .cif_plane_coverage import audit_trigonal_plane_coverage, _local_geometry
from .cif_plane_candidate import _NONCOLLINEAR
from .cif_stereochemistry_audit import _values, _graph
from .cif_triple_bond_audit import _angle

POLICY_ID = 'cif-source-trigonal-model-geometry-v1'


def _measure(xyz, centre, neighbors):
    result = _local_geometry(xyz, centre, neighbors)
    if result['status'] != 'DESCRIPTIVE':
        return result
    vectors = [[x-y for x,y in zip(xyz[n],xyz[centre])] for n in neighbors]
    vectors = [[x/hypot(*v) for x in v] for v in vectors]
    elevations = []
    for index, atom in enumerate(neighbors):
        a,b = [v for j,v in enumerate(vectors) if j != index]
        normal = [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        length = hypot(*normal)
        angle = None if length <= _NONCOLLINEAR else degrees(asin(min(1.,abs(sum(x*y for x,y in zip(vectors[index],normal))/length))))
        elevations.append(dict(atom=atom, reference_neighbors=[n for j,n in enumerate(neighbors) if j != index],
            absolute_out_of_plane_degrees=angle, reference_normal_length=length))
    angles = [dict(atoms=[a,centre,b],degrees=_angle(xyz,[a,centre,b])) for a,b in combinations(neighbors,2)]
    if any(r['absolute_out_of_plane_degrees'] is None for r in elevations):result['status']='DEGENERATE'
    result.update(neighbor_angles=angles,angle_sum_degrees=sum(r['degrees'] for r in angles),bond_elevations=elevations)
    return result


def review_trigonal_model_geometry(source, dictionary, component, model):
    """Measure every modeled occurrence selected by the existing source rule.

    Missing local atoms remain explicit. No global plane fit, native residual,
    scientific pass threshold or coordinate edit is inferred from these values.
    """
    paths = [Path(p) for p in (source,dictionary,model)]
    source,dictionary,model = paths
    frozen = [p.read_bytes() for p in paths]
    try:
        coverage = audit_trigonal_plane_coverage(source,dictionary,component)
        sites = _model(frozen[2]);inventory = _pdb_inventory(model)
        elements = _graph(_values(source,component))[0]
        selected = sorted(site for site,row in sites.items() if row['component']==component)
        rows = []
        for site in selected:
            chain,residue = site.split(':')
            atoms = {key[-1]:row for key,row in inventory.items() if (key[0],str(int(key[1])))==(chain,residue)}
            for centre in coverage['centres']:
                names = [centre['centre'],*centre['neighbors']]
                missing = sorted(set(names)-atoms.keys())
                row = dict(site=site,centre=centre['centre'],neighbors=centre['neighbors'],
                    coverage=centre['coverage'],covering_planes=centre['covering_planes'],partial_planes=centre['partial_planes'])
                if missing:
                    row['geometry']=dict(status='UNAVAILABLE',missing_atoms=missing)
                elif any(atoms[n]['element']!=elements[n] for n in names):
                    raise ValueError('Modeled trigonal atom element differs from source')
                else:
                    row['geometry']=_measure({n:atoms[n]['xyz'] for n in names},centre['centre'],centre['neighbors'])
                rows.append(row)
        return dict(schema_version=1,policy_id=POLICY_ID,status='REVIEW' if rows else 'UNASSESSED',component=component,
            source_sha256=coverage['source_sha256'],dictionary_sha256=coverage['dictionary_sha256'],model_sha256=sha256(frozen[2]).hexdigest(),
            selection=coverage['selection'],modeled_sites=selected,measurements=rows,
            unassessed_carbon_centres=coverage['unassessed_carbon_centres'],
            coordinate_scope='LITERAL_SAME_RESIDUE_CARTESIAN; NO_SYMMETRY_IMAGE_INFERENCE',
            degeneracy_policy=dict(normalized_cross_product_min=_NONCOLLINEAR,meaning='NUMERICAL_RANK_GUARD_NOT_CHEMICAL_THRESHOLD'),
            native_membership='NOT_ASSESSED',complete_geometry_qualification='NOT_RUN',scientific_approval='NOT_RUN',automatic_adoption=False,
            model_editing='NOT_RUN',optimization='NOT_RUN',input_integrity='UNCHANGED',
            limitations=['C208 explicit neutral three-heavy-neighbor carbon scope; unsupported chemistry remains unassessed.',
                'A small normalized volume alone does not prove healthy geometry; collapsed or collinear vectors are marked degenerate.',
                'Coverage, Cartesian shape, native membership/mechanics and scientific acceptance are separate.',
                'Strict supported PDB identities only; no conformer collapse, alias guessing or symmetry inference.'])
    finally:
        if any(p.read_bytes()!=data for p,data in zip(paths,frozen)):
            raise ValueError('Trigonal model review input changed')


def _observed_trigonal_geometry(projections, observation):
    """Describe an already authenticated selected-site native observation.

    The execution owner validates capture, model and source identity before this
    adapter is called. Reuse C208 selection and Cartesian measurements; a plane
    listing, positive weights and achieved shape are deliberately separate facts.
    """
    from math import isfinite
    from .cif_dictionary_sites import _need
    from .cif_linked_qualification import _site
    expected = [dict(site=site, component=code) for site, (_, code) in sorted(projections.items())]
    _need(observation['sites'] == expected, 'Observed trigonal site/component scope differs')
    snapshots = {Path(path): Path(path).read_bytes() for path, _ in projections.values()}
    result = dict(schema_version=1, policy_id='cif-source-trigonal-native-geometry-v1',
        status='UNASSESSED', reason=observation.get('reason'), measurements=[], native_planes=[],
        declared_sites={site: dict(component=code, projection_sha256=sha256(snapshots[Path(path)]).hexdigest())
                        for site, (path, code) in sorted(projections.items())},
        unassessed_carbon_centres={}, coordinate_scope='LITERAL_SAME_RESIDUE_CARTESIAN',
        coordinate_precision=observation.get('coordinate_precision'),
        model_state_sha256=observation.get('model_state_sha256'),
        native_residuals='NOT_EVALUATED', scientific_approval='NOT_RUN', automatic_adoption=False,
        limitations=['Existing neutral three-heavy-neighbor carbon selector only; other chemistry remains unassessed.',
            'Only already captured sites and intra-site planes are available; no missing cross-site or symmetry term is inferred.',
            'Plane membership and positive weights do not prove flat geometry or adequate restraint strength.',
            'Cartesian measurements are descriptive, not native energies or a new chemical acceptance threshold.'])
    try:
        if observation['status'] == 'UNASSESSED':
            return result
        _need(observation['status'] == 'OBSERVED', 'Require an observed native state')
        atoms_by_site = {site: {} for site in projections}; by_index = {}
        for atom in observation['atoms']:
            site = _site(atom); name = atom['atom_id']; index = atom['i_seq']
            _need(site in atoms_by_site and name not in atoms_by_site[site] and index not in by_index,
                  'Ambiguous observed trigonal atom identity')
            _need(atom['identity']['resname'].strip() == projections[site][1],
                  'Observed trigonal component differs from source')
            atoms_by_site[site][name] = atom; by_index[index] = atom
        planes_by_site = {site: [] for site in projections}
        for index, plane in enumerate(observation['geometry']['proxy_details']['planarity']):
            ids, weights = plane['i_seqs'], plane['weights']
            _need(ids and len(set(ids)) == len(ids) and all(i in by_index for i in ids),
                  'Observed trigonal plane indices differ')
            sites = {_site(by_index[i]) for i in ids}
            _need(len(sites) == 1 and plane['atoms'] == [by_index[i]['label'] for i in ids],
                  'Observed trigonal plane crosses site or atom identity')
            _need(isinstance(weights, list) and len(weights) == len(ids)
                  and all(type(w) in (int, float) and isfinite(w) and w >= 0 for w in weights),
                  'Observed trigonal plane weights are unavailable or invalid')
            planes_by_site[next(iter(sites))].append((index, plane))
        selected = {}; used_planes = {}
        for site, (path, code) in sorted(projections.items()):
            key = (Path(path), code)
            if key not in selected:
                selected[key] = (audit_trigonal_plane_coverage(path, path, code), _graph(_values(path, code))[0])
            coverage, elements = selected[key]; atoms = atoms_by_site[site]
            _need(all(name in elements and atom['element'] == elements[name] for name, atom in atoms.items()),
                  'Observed trigonal atom element/name differs from source')
            result['unassessed_carbon_centres'][site] = coverage['unassessed_carbon_centres']
            for centre in coverage['centres']:
                names = [centre['centre'], *centre['neighbors']]; missing = sorted(set(names)-atoms.keys())
                covering = []; positive = []
                if missing:
                    geometry = dict(status='UNAVAILABLE', missing_atoms=missing)
                else:
                    geometry = _measure({n: atoms[n]['xyz'] for n in names}, centre['centre'], centre['neighbors'])
                    local = {atoms[n]['i_seq'] for n in names}
                    for index, plane in planes_by_site[site]:
                        if not local <= set(plane['i_seqs']):
                            continue
                        covering.append(index)
                        if all(w > 0 for i, w in zip(plane['i_seqs'], plane['weights']) if i in local):
                            positive.append(index)
                        used_planes[index] = dict(proxy_index=index, site=site, i_seqs=list(plane['i_seqs']),
                            atom_names=[by_index[i]['atom_id'] for i in plane['i_seqs']],
                            weights=list(plane['weights']), origin_id=plane['origin_id'])
                result['measurements'].append(dict(site=site, component=code, centre=centre['centre'],
                    neighbors=centre['neighbors'], geometry=geometry, covering_plane_indices=covering,
                    positively_weighted_covering_plane_indices=positive,
                    coverage=('UNAVAILABLE_MISSING_LOCAL_ATOMS' if missing else
                              'CAPTURED_INTRA_SITE_PLANE_PRESENT' if covering else 'NO_CAPTURED_INTRA_SITE_PLANE')))
        result.update(status='REVIEW' if result['measurements'] else 'UNASSESSED', reason=None,
            native_planes=[used_planes[i] for i in sorted(used_planes)],
            selection='EXPLICIT_SOURCE_GRAPH_AND_STATE; NO_COMPONENT_OR_ATOM_NAME_ALLOWLIST')
        return result
    finally:
        _need(all(path.read_bytes() == data for path, data in snapshots.items()),
              'Trigonal source projection changed during read')
