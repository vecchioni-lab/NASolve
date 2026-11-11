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
