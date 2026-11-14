"""Read-only binding of an explicit movement mask to exact serialized PDB bytes.

Native chemistry/packing review is delegated to Cedar. This audit checks what
moved and what rounding changed; it does not select or approve a candidate.
"""
from hashlib import sha256
import math

from .topostitch_recipe import model_atom_rows, recipe_digest
from .topostitch_transport import CoordinateMask


def _identity(line):
    return tuple(line[a:b].strip() for a,b in ((12,16),(16,17),(17,20),(21,22),(22,26),(26,27)))


def audit_masked_endpoint(source, candidate, points, *, movable_indices, max_displacement_angstrom, anisou_policy="reject-movable"):
    """Bind full precision and exact PDB rounding; preserve every other byte.

    First scope: full-occupancy canonical DNA atoms without alternate conformers
    and an explicit tensor policy. No residue, atom, bond or dictionary is created.
    The caller authenticates both native captures and the movement request.
    """
    if not isinstance(source,bytes) or not isinstance(candidate,bytes):
        raise ValueError('Require explicit source and candidate PDB bytes')
    if anisou_policy not in ('reject-movable','preserve-cartesian'):
        raise ValueError('Require a declared ANISOU policy')
    identities=model_atom_rows(source)
    if model_atom_rows(candidate)!=identities:
        raise ValueError('Candidate atom identities/order changed')
    original=source.splitlines(keepends=True);actual=candidate.splitlines(keepends=True)
    if len(original)!=len(actual):raise ValueError('Candidate PDB record inventory changed')
    atom_lines=[i for i,line in enumerate(original) if line[:6] in (b'ATOM  ',b'HETATM')]
    reference=tuple(tuple(float(original[i][a:b]) for a,b in ((30,38),(38,46),(46,54))) for i in atom_lines)
    mask=CoordinateMask(reference,movable_indices,max_displacement_angstrom)
    points=tuple(tuple(p) for p in points)
    delta=mask.displacements(points)
    selected=set(mask.indices);keys=set()
    for i in selected:
        row=identities[i];line=original[atom_lines[i]]
        if row['residue_code'] not in ('DA','DT','DG','DC') or row['altloc'] or float(line[54:60])!=1.:
            raise ValueError('Movable endpoint atoms require full-occupancy canonical DNA without alternates')
        keys.add(_identity(line))
    tensors=[_identity(line) for line in original if line.startswith(b'ANISOU') and _identity(line) in keys]
    if len(tensors)!=len(set(tensors)):raise ValueError('Duplicate movable ANISOU records')
    if tensors and anisou_policy=='reject-movable':
        raise ValueError('Movable ANISOU tensors require an explicit coordinate-only preserve-cartesian policy')
    expected=original.copy();rounded=list(reference)
    for i in selected:
        fields=''.join(f'{value:8.3f}' for value in points[i]).encode('ascii')
        if len(fields)!=24:raise ValueError('Endpoint coordinate exceeds PDB field width')
        line=original[atom_lines[i]];expected[atom_lines[i]]=line[:30]+fields+line[54:]
        rounded[i]=tuple(float(fields[a:b]) for a,b in ((0,8),(8,16),(16,24)))
    if b''.join(expected)!=candidate:
        raise ValueError('Candidate differs from exact masked coordinate serialization or changes protected bytes')
    mask.displacements(rounded)  # Rounding must also respect the declared motion bound.
    distances=[math.dist(reference[i],points[i]) for i in mask.indices]
    rounded_distances=[math.dist(reference[i],rounded[i]) for i in mask.indices]
    return dict(schema_version=1,kind='topostitch-masked-endpoint-byte-audit',
        status='EXACT_MASKED_SERIALIZATION',source_model_sha256=sha256(source).hexdigest(),
        candidate_model_sha256=sha256(candidate).hexdigest(),full_precision_points_sha256=recipe_digest(points),
        movable_indices=list(mask.indices),atom_count=len(reference),fixed_atom_count=len(reference)-len(selected),
        moved_atom_count=sum(points[i]!=reference[i] for i in mask.indices),
        serialized_moved_atom_count=sum(rounded[i]!=reference[i] for i in mask.indices),
        full_precision_max_displacement_angstrom=max(distances),
        serialized_max_displacement_angstrom=max(rounded_distances),
        max_displacement_angstrom=mask.max_displacement_angstrom,
        roundtrip_max_distance_angstrom=max(math.dist(points[i],rounded[i]) for i in selected),
        fixed_records_preserved=True,noncoordinate_bytes_preserved=True,
        anisou_policy=anisou_policy,movable_anisou_count=len(tensors),
        adp_refinement=False,thermal_model_qualified=False,
        full_precision_displacements_sha256=recipe_digest(delta),
        runtime_authority=False,geometry_accepted=False,scientific_acceptance=False)
