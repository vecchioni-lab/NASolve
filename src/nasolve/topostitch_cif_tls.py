"""Read-only transport of explicitly declared TLS under one proper crystal image.

Raw S components are preserved. This does not choose Phenix's trace convention,
refit TLS, split mixed-image groups, rewrite CIF selections or approve a writer.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import math
from pathlib import Path

from .topostitch_cif_annotations import _rows
from .topostitch_cif_fragments import observe_relabel_cif_fragments, _reference_integer
from .topostitch_registration import _fingerprint
from .topostitch_transport import CartesianImage, crystallographic_image

_SYMMETRIC = ((0,0),(1,1),(2,2),(0,1),(0,2),(1,2))
_KEYS = {'origin_angstrom':3,'T_angstrom_squared':6,'L_degrees_squared':6,'S_angstrom_degrees':9}


def _validated(parameters):
    if not isinstance(parameters,dict) or set(parameters) != set(_KEYS):
        raise ValueError('Require explicit origin and T/L/S with declared units')
    result = {}
    for key, size in _KEYS.items():
        values = parameters[key]
        if (not isinstance(values,(list,tuple)) or len(values) != size
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in values)):
            raise ValueError('Require finite TLS parameters: '+key)
        result[key] = [float(v) for v in values]
    return result


def _symmetric(values):
    a,b,c,d,e,f = values
    return ((a,d,e),(d,b,f),(e,f,c))


def tls_u_cart(parameters, point):
    """Evaluate declared TLS U in Å²; L is degree² and S is Å·degree.

    U = T + A L A^T + A S + S^T A^T, with A r's negative cross-product matrix.
    All nine S values are used; no trace-zero overwrite or positivity correction.
    """
    p = _validated(parameters)
    if (not isinstance(point,(tuple,list)) or len(point) != 3
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in point)):
        raise ValueError('Require a finite Cartesian TLS site')
    x,y,z = [v-o for v,o in zip(point,p['origin_angstrom'])]
    a = ((0.,z,-y),(-z,0.,x),(y,-x,0.))
    t = _symmetric(p['T_angstrom_squared'])
    l = _symmetric([v*(math.pi/180.)**2 for v in p['L_degrees_squared']])
    s = [p['S_angstrom_degrees'][i:i+3] for i in (0,3,6)]
    result = [t[i][j] + math.fsum(a[i][k]*l[k][m]*a[j][m] for k in range(3) for m in range(3))
        + math.fsum((a[i][k]*s[k][j]+s[k][i]*a[j][k])*(math.pi/180.) for k in range(3))
        for i,j in _SYMMETRIC]
    if not all(math.isfinite(v) for v in result):
        raise ValueError('TLS evaluation exceeds finite range')
    return result


def transport_tls_parameters(parameters, image):
    """Carry origin and T/L/S through an already qualified proper rigid image."""
    p = _validated(parameters)
    if not isinstance(image,CartesianImage):
        raise ValueError('Require a validated proper Cartesian image')
    r = image.rotation
    s = [p['S_angstrom_degrees'][i:i+3] for i in (0,3,6)]
    transformed = dict(origin_angstrom=list(image.apply(p['origin_angstrom'])),
        T_angstrom_squared=list(image.rotate_tensor(p['T_angstrom_squared'])),
        L_degrees_squared=list(image.rotate_tensor(p['L_degrees_squared'])),
        S_angstrom_degrees=[math.fsum(r[i][k]*s[k][m]*r[j][m] for k in range(3) for m in range(3))
                           for i in range(3) for j in range(3)])
    return _validated(transformed)


def _parameters(row):
    try:
        return _validated(dict(origin_angstrom=[float(row['origin_'+a])for a in 'xyz'],
            T_angstrom_squared=[float(row[f'T[{i+1}][{j+1}]'])for i,j in _SYMMETRIC],
            L_degrees_squared=[float(row[f'L[{i+1}][{j+1}]'])for i,j in _SYMMETRIC],
            S_angstrom_degrees=[float(row[f'S[{i+1}][{j+1}]'])for i in range(3)for j in range(3)]))
    except (KeyError,TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Missing or nonfinite declared TLS parameters') from exc


def _member_ids(row, atoms, sites, scheme):
    """Narrow explicit single-chain label range with matching author evidence."""
    issues = []
    start = _reference_integer(row.get('beg_label_seq_id'))
    end = _reference_integer(row.get('end_label_seq_id'))
    chain = row.get('beg_label_asym_id')
    author = row.get('beg_auth_asym_id')
    first = _reference_integer(row.get('beg_auth_seq_id'))
    last = _reference_integer(row.get('end_auth_seq_id'))
    if (not isinstance(chain,str) or not chain or chain != row.get('end_label_asym_id')
            or start is None or end is None or not 0 < start <= end
            or not isinstance(author,str) or author != row.get('end_auth_asym_id')
            or first is None or last is None or last-first != end-start):
        return [],['Unsupported or conflicting TLS label/author range']
    if row.get('selection') not in (None,False):
        issues.append('Explicit TLS selection expression is outside the supported range scope')
    description = row.get('selection_details')
    explicit_range = f"(chain '{author}' and resid {first} through {last})"
    if row.get('selection') is None and description != explicit_range:
        issues.append('Unknown TLS selection lacks an explicit complete range description')
    if description not in (None,False,explicit_range):
        issues.append('TLS selection details are not the qualified explicit range')
    members = [a for a in atoms if a.get('label_asym_id') == chain
        and _reference_integer(a.get('label_seq_id')) is not None
        and start <= _reference_integer(a['label_seq_id']) <= end]
    numbers = {_reference_integer(a['label_seq_id'])for a in members}
    if len(numbers) != end-start+1:
        issues.append('TLS range includes missing coordinate positions')
    ids = [a['id'] for a in members]
    if any(atom_id not in sites for atom_id in ids):
        issues.append('TLS range includes unregistered atoms with unqualified image membership')
    author_members = [a['id'] for a in atoms if a.get('auth_asym_id') == author
        and _reference_integer(a.get('auth_seq_id')) is not None
        and first <= _reference_integer(a['auth_seq_id']) <= last]
    if set(ids) != set(author_members):
        issues.append('TLS label and author selections have different members')
    for a in members:
        number = _reference_integer(a['label_seq_id'])
        rows = [s for s in scheme if s.get('asym_id') == chain
                and _reference_integer(s.get('seq_id')) == number]
        if (a.get('auth_asym_id') != author or _reference_integer(a.get('auth_seq_id')) != first+number-start
                or a.get('pdbx_PDB_ins_code') not in (None,False)
                or not rows or any(s.get('pdb_ins_code') is not False for s in rows)):
            issues.append('TLS author numbering/insertion membership is unresolved')
            break
    if any(row.get(key) not in (None,False)for key in ('beg_PDB_ins_code','end_PDB_ins_code')):
        issues.append('TLS inserted endpoints are outside the supported range scope')
    return ids,issues


def observe_relabel_cif_tls(directory, model, **fragment_binding):
    """Retain original TLS groups; transport only complete uniform-image groups.

    Multiple range rows for one TLS parameter group are aggregated. Unknown
    selections, missing members and mixed images remain available for review.
    No group is split or applied to atom ADPs; total deposited U stays untouched.
    """
    import gemmi

    model = Path(model);data = model.read_bytes()
    lineage = observe_relabel_cif_fragments(directory,model,**fragment_binding)
    if model.read_bytes() != data or sha256(data).hexdigest() != lineage['original_model_sha256']:
        raise ValueError('Original CIF changed during TLS observation')
    doc = gemmi.cif.read_string(data.decode('ascii'))
    block = next(b for b in doc if '_atom_site.' in b.get_mmcif_category_names())
    atoms = _rows(block,'_atom_site.');by_id = {a['id']:a for a in atoms}
    raw = _rows(block,'_pdbx_refine_tls.');ranges = _rows(block,'_pdbx_refine_tls_group.')
    scheme = _rows(block,'_pdbx_poly_seq_scheme.')
    sites = {atom_id:s for f in lineage['fragments']for s in f['sites']for atom_id in s['original_atom_ids']}
    parsed = gemmi.make_structure_from_block(block)
    cell = list(parsed.cell.parameters);group = parsed.find_spacegroup().xhm()
    counts = Counter(r.get('id')for r in raw);range_counts = Counter(r.get('id')for r in ranges)
    result = []
    for row in raw:
        key = row.get('id');issues = []
        if not isinstance(key,str) or not key or counts[key] != 1:
            issues.append('Missing or duplicate TLS parameter identifier')
        refinement_id = row.get('pdbx_refine_id')
        if not isinstance(refinement_id,str) or not refinement_id.strip():
            issues.append('TLS parameters require an explicit refinement identifier')
        selections = [g for g in ranges if g.get('refine_tls_id') == key]
        if not selections:issues.append('No declared TLS group membership')
        ids = []
        for selection in selections:
            if (not isinstance(selection.get('id'),str) or not selection['id'].strip()
                    or range_counts[selection['id']] != 1
                    or not isinstance(selection.get('pdbx_refine_id'),str)
                    or not selection['pdbx_refine_id'].strip()
                    or selection['pdbx_refine_id'] != refinement_id):
                issues.append('Ambiguous TLS group/refinement identifier')
            selected,errors = _member_ids(selection,atoms,sites,scheme)
            if set(ids).intersection(selected):issues.append('Overlapping TLS range membership')
            ids.extend(selected);issues.extend(errors)
        ids = list(dict.fromkeys(ids))
        if lineage['metadata_coverage_status'] != 'CONSISTENT_DECLARATIONS':
            issues.append('Original polymer coverage requires review')
        try:parameters = _parameters(row)
        except ValueError as exc:
            parameters = None;issues.append(str(exc))
        images = {}
        for atom_id in ids:
            if atom_id in sites:
                operation = gemmi.Op(sites[atom_id]['representative_operator_xyz']).triplet()
                images.setdefault(operation,[]).append(atom_id)
        transported = None;image = None;maximum = None
        status = 'REVIEW_REQUIRED' if issues else 'MIXED_IMAGES_REVIEW' if len(images) != 1 else 'UNIFORM_IMAGE_TRANSPORT_OBSERVED'
        if status == 'UNIFORM_IMAGE_TRANSPORT_OBSERVED':
            image = crystallographic_image(cell,group,next(iter(images)))
            transported = transport_tls_parameters(parameters,image)
            errors = []
            for atom_id in ids:
                xyz = [float(by_id[atom_id]['Cartn_'+axis])for axis in 'xyz']
                old = image.rotate_tensor(tls_u_cart(parameters,xyz))
                new = tls_u_cart(transported,image.apply(xyz))
                errors.extend(abs(a-b)for a,b in zip(old,new))
            maximum = max(errors,default=0.)
            if maximum > 1e-9:raise ValueError('Uniform TLS tensor transport exceeds numerical bound')
        trace = sum(parameters['S_angstrom_degrees'][i]for i in (0,4,8)) if parameters else None
        result.append(dict(tls_id=key,status=status,issues=issues,original_parameter_row=row,
            original_group_rows=selections,member_atom_ids=ids,member_images=images,
            original_parameters=parameters,transported_parameters=transported,
            operator_xyz=next(iter(images)) if len(images)==1 else None,
            cartesian_rotation=image.rotation if image else None,cartesian_translation_angstrom=image.translation if image else None,
            maximum_tls_u_component_error_angstrom_squared=maximum,source_s_trace_angstrom_degrees=trace,
            parameter_convention_status='UNAVAILABLE' if trace is None else 'NONZERO_S_TRACE_REVIEW' if abs(trace)>1e-8 else 'TRACE_ZERO_WITHIN_1E_8',
            native_zeroize_trace_applied=False,parameter_uncertainties_transported=False))
    orphan = [r for r in ranges if counts[r.get('refine_tls_id')] != 1]
    report = dict(schema_version=1,kind='topostitch-original-cif-tls-transport',
        status='UNAVAILABLE' if not raw else 'OBSERVED_REVIEW_REQUIRED',
        original_model_sha256=lineage['original_model_sha256'],fragment_lineage_sha256=lineage['report_sha256'],
        original_tls_rows=raw,original_group_rows=ranges,groups=result,orphan_group_rows=orphan,
        uniform_group_count=sum(g['status']=='UNIFORM_IMAGE_TRANSPORT_OBSERVED'for g in result),
        mixed_group_count=sum(g['status']=='MIXED_IMAGES_REVIEW'for g in result),
        coordinates_written=False,total_atom_adps_changed=False,groups_split=False,writer_authorized=False,
        native_refinement_compatibility_approved=False,runtime_authority=False,scientific_acceptance=False,
        limitations=['Declared raw TLS field only; not positivity, refinement provenance or total atom ADP validation',
            'Every supplied S component is retained; native trace-zero reinterpretation is a separate unresolved convention',
            'Mixed-image or incomplete groups are not split, silently copied or assigned new selections',
            'Only explicit label/author ranges and their exact simple selection details are supported',
            'Parameter uncertainty covariance, output references, native refinement and writer remain unqualified'])
    if model.read_bytes() != data:raise ValueError('Original CIF changed during TLS observation')
    report['report_sha256'] = _fingerprint(report)
    return report
