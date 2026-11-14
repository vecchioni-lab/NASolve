"""Separate, source-supported completion of existing trigonal plane groups.

Only supplied plane membership/ESDs can be transferred. Native provenance,
mechanics, chemical approval and adoption are deliberately separate gates.
"""
from copy import deepcopy
from hashlib import sha256
from math import hypot, isfinite
from pathlib import Path

from .cif_plane_coverage import audit_trigonal_plane_coverage, _planes, _table
from .cif_stereochemistry_audit import _values, _graph, _coordinates
from .ligand_profiles import _blocks, _emit

POLICY_ID = "cif-source-trigonal-plane-completion-v1"
_P = "_chem_comp_plane_atom."
_FIELDS = {"comp_id", "plane_id", "atom_id", "dist_esd"}
_NONCOLLINEAR = 1e-6  # Dimensionless numerical rank guard, not a chemical cutoff.


class UnsupportedPlaneCompletion(ValueError):
    """Well-formed inputs supply no supported missing plane row."""


def _source_plane_evidence(xyz, shared, original, added, sigma):
    names = sorted(set(original) | {added})
    if not all(n in xyz for n in names):
        raise ValueError("INCOMPLETE_SOURCE_IDEAL_PLANE_COORDINATES")
    origin = xyz[shared[0]]
    vectors = [[x-y for x,y in zip(xyz[n], origin)] for n in shared[1:]]
    lengths = [hypot(*v) for v in vectors]
    if any(not isfinite(v) or v <= 1e-12 for v in lengths):
        raise ValueError("DEGENERATE_SOURCE_IDEAL_ANCHORS")
    a,b = [[x/length for x in v] for v,length in zip(vectors,lengths)]
    normal = [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    size = hypot(*normal)
    if not isfinite(size) or size <= _NONCOLLINEAR:
        raise ValueError("COLLINEAR_SOURCE_IDEAL_ANCHORS")
    normal = [v/size for v in normal]
    distances = {n: abs(sum((x-y)*v for x,y,v in zip(xyz[n],origin,normal))) for n in names}
    limits = {**original, added: sigma}
    if any(not isfinite(d) or d > limits[n] for n,d in distances.items()):
        raise ValueError("SOURCE_IDEAL_OUTSIDE_SUPPLIED_PLANE_ESDS")
    return {"anchor_atoms": shared, "normalized_cross_product": size,
            "source_ideal_distances_angstrom": distances, "supplied_esds_angstrom": limits,
            "interpretation": "CONSERVATIVE_TEMPLATE_COMPATIBILITY_GATE; NOT_CHEMICAL_APPROVAL"}


def prepare_trigonal_plane_candidate(source, dictionary, corroborating_dictionary, code, output):
    """Append supported rows to a fresh candidate; preserve all original terms.

    One unambiguous existing partial plane and agreeing supplied ESDs are needed.
    Source ideal heavy-atom geometry is a refusal gate, never a new target.
    Existing H/D plane rows stay exact; their ideal coordinates are unassessed.
    Unrepairable centres are retained explicitly; no usable-result claim is made.
    """
    paths = [Path(p).resolve(strict=True) for p in (source,dictionary,corroborating_dictionary)]
    source,dictionary,corroborating_dictionary = paths
    output = Path(output).absolute()
    if (output.exists() or output.is_symlink() or output in paths
            or any(p.is_symlink() for p in output.parents)):
        raise ValueError("Require a fresh separate plane candidate without symlink parents")
    frozen = [p.read_bytes() for p in paths]
    try:
        before = audit_trigonal_plane_coverage(source,dictionary,code)
        support = audit_trigonal_plane_coverage(source,corroborating_dictionary,code)
        sv,dv,pv = [_values(p,code) for p in paths]
        elements = _graph(sv)[0]
        original_planes = _planes(dv,elements)
        support_planes = _planes(pv,_graph(pv)[0])
        support_esd_text = {(r['plane_id'],r['atom_id']):r['dist_esd'] for r in _table(pv,'plane_atom')}
        source_family, xyz = _coordinates(sv,source=True)
        eligible = {r['centre']:r for r in support['centres']}
        planned, unresolved = [], []
        for row in before['centres']:
            if row['coverage'] != 'EXPLICIT_PLANE_MISSING':
                continue
            centre = row['centre']
            try:
                if source_family != 'SOURCE_IDEAL':
                    raise ValueError('REQUIRE_EXPLICIT_SOURCE_IDEAL_COORDINATES')
                if len(row['partial_planes']) != 1:
                    raise ValueError('REQUIRE_ONE_EXISTING_PARTIAL_PLANE')
                partial = row['partial_planes'][0]
                added = partial['missing'][0]
                corroboration = eligible.get(centre,{})
                covers = corroboration.get('covering_planes',[])
                if not covers:
                    raise ValueError('NO_CORROBORATING_LOCAL_PLANE')
                sigmas = {support_planes[p['plane']][added] for p in covers}
                if len(sigmas) != 1:
                    raise ValueError('AMBIGUOUS_CORROBORATING_PLANE_ESDS')
                sigma = next(iter(sigmas))
                existing = original_planes[partial['plane']]
                heavy = {n:esd for n,esd in existing.items() if elements[n] not in {'H','D'}}
                evidence = _source_plane_evidence(xyz,partial['shared'],heavy,added,sigma)
                evidence['unassessed_source_ideal_hydrogens'] = sorted(set(existing)-heavy.keys())
                planned.append(dict(centre=centre,plane=partial['plane'],atom=added,
                    dist_esd=sigma,dist_esd_text=support_esd_text[(covers[0]['plane'],added)],corroborating_planes=[p['plane'] for p in covers],
                    source_plane_evidence=evidence))
            except ValueError as exc:
                unresolved.append(dict(centre=centre,reason=str(exc)))
        if not planned:
            raise UnsupportedPlaneCompletion('No supported plane completion: '+repr(unresolved))
        # Different centres may support the same missing row. Deduplicate only
        # agreeing declarations; retain each centre's independent selection proof.
        additions = {}; addition_text = {}
        for row in planned:
            key = (row['plane'],row['atom'])
            if key in additions and additions[key] != row['dist_esd']:
                raise ValueError('Conflicting additions to one plane atom')
            additions[key] = row['dist_esd']
            addition_text.setdefault(key,row['dist_esd_text'])
        expected, rendered, appended = [], [], set()
        for block in _blocks(dictionary):
            v = deepcopy(block.values)
            columns = {k.lower():k for k in v if k.lower().startswith(_P)}
            changed = False
            if columns and code in v.get(columns.get(_P+'comp_id',''),[]):
                if set(columns) != {_P+k for k in _FIELDS}:
                    raise ValueError('Unsupported existing plane columns; cannot invent values')
                if len({len(v[k]) for k in columns.values()}) != 1:
                    raise ValueError('Incomplete existing plane columns')
                matching = {v[columns[_P+'plane_id']][i] for i,c in enumerate(v[columns[_P+'comp_id']]) if c == code}
                for (plane,atom),sigma in sorted(additions.items()):
                    if plane not in matching:
                        continue
                    if (plane,atom) in appended:
                        raise ValueError('Ambiguous plane definition across blocks')
                    new = dict(comp_id=code,plane_id=plane,atom_id=atom,dist_esd=addition_text[(plane,atom)])
                    for field,value in new.items():v[columns[_P+field]].append(value)
                    appended.add((plane,atom));changed=True
            expected.append(v);rendered.append(_emit(v) if changed else block.text)
        if appended != set(additions):
            raise ValueError('Planned plane additions did not resolve exactly')
        if [p.read_bytes() for p in paths] != frozen:
            raise ValueError('Plane-completion input changed before writing')
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x',encoding='utf-8') as stream:stream.write(''.join(rendered))
        if [b.values for b in _blocks(output)] != expected:
            raise ValueError('Candidate differs from exact parsed addition allowlist')
        after = audit_trigonal_plane_coverage(source,output,code)
        remaining = set(after['missing_explicit_planes'])
        if any(r['centre'] in remaining for r in planned):
            raise ValueError('Candidate did not complete selected local coverage')
        return dict(schema_version=1,policy_id=POLICY_ID,status='CANDIDATE_REVIEW',component=code,
            source_sha256=sha256(frozen[0]).hexdigest(),dictionary_sha256=sha256(frozen[1]).hexdigest(),
            corroborating_dictionary_sha256=sha256(frozen[2]).hexdigest(),candidate_sha256=sha256(output.read_bytes()).hexdigest(),
            additions=[dict(plane=p,atom=a,dist_esd=s) for (p,a),s in sorted(additions.items())],
            selected_centres=planned,unresolved_centres=unresolved,remaining_missing_explicit_planes=sorted(remaining),
            parsed_allowlist_pass=True,input_integrity='UNCHANGED',source_coordinate_family=source_family,
            corroboration='SUPPLIED_DICTIONARY; GENERATOR_PROVENANCE_NOT_VERIFIED',native_qualification='NOT_RUN',
            scientific_approval='NOT_RUN',automatic_adoption=False,model_editing='NOT_RUN',
            limitations=['Only existing unambiguous planes are extended; no ring plane is replaced or chemical state changed.',
                        'Source ideal heavy-atom compatibility is a conservative refusal gate, not chemical authority; existing H/D rows stay exact and their coordinates are unassessed.',
                        'Supplied plane membership and ESDs are not authenticated native generation or calibrated accuracy.',
                        'Native membership/mechanics, source chemistry, achieved geometry and ordinary adoption remain separate gates.'])
    finally:
        if [p.read_bytes() for p in paths] != frozen:
            raise ValueError('Plane-completion input changed during preparation')
