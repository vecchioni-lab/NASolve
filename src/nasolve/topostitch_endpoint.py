"""Read-only binding of an explicit movement mask to exact serialized PDB bytes.

Native chemistry/packing review is delegated to Cedar. This audit checks what
moved and what rounding changed; it does not select or approve a candidate.
"""
from dataclasses import dataclass
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


def endpoint_coordinate_cases(source, points, *, movable_indices, max_displacement_angstrom):
    """Bind explicit points and three-decimal rounding to exact source anchors.

    These are coordinate observations, not an emitted PDB or permission to move.
    Candidate-byte and tensor policy checks remain audit_masked_endpoint's job.
    """
    model_atom_rows(source)
    reference=tuple(tuple(float(line[a:b]) for a,b in ((30,38),(38,46),(46,54)))
        for line in source.splitlines() if line[:6] in (b'ATOM  ',b'HETATM'))
    mask=CoordinateMask(reference,movable_indices,max_displacement_angstrom)
    full=mask.expand(mask.displacements(points));rounded=list(reference)
    for i in mask.indices:
        fields=''.join(f'{v:8.3f}' for v in full[i])
        if len(fields)!=24:raise ValueError('Endpoint coordinate exceeds PDB field width')
        rounded[i]=tuple(float(fields[a:b]) for a,b in ((0,8),(8,16),(16,24)))
    # Match the actual displacement evaluator, including binary roundoff near
    # zero. These observations do not claim literal PDB decimal coordinates.
    rounded=mask.expand(mask.displacements(rounded))
    return {name:[list(p) for p in values] for name,values in
        [('source',reference),('full_precision',full),('rounded',rounded)]}


def project_coordinate_observation(native, observation, *, expected_points):
    """Build a transient reviewer input, never an authenticated model capture.

    The caller binds source/capture/mask/artifact bytes. Cedar must then replay
    native energy/ASU arithmetic and review geometry. Projection alone is no PASS.
    """
    from copy import deepcopy
    if recipe_digest(observation['points'])!=recipe_digest(expected_points):
        raise ValueError('Observed endpoint coordinates differ from the bound request')
    count=native['atom_count'];points=expected_points
    if (len(points)!=count or any(len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p) for p in points)
            or len(observation['native_energy_snapshots'])!=2 or observation['exact_repeat'] is not True):
        raise ValueError('Require complete repeated fixed-manager coordinate observations')
    result=deepcopy(native)
    result['geometry']['sites_cart_exact']=deepcopy(points)
    for atom,point in zip(result['atoms'],points):atom['xyz']=deepcopy(point)
    result['energy_inventory']['snapshots']=deepcopy(observation['native_energy_snapshots'])
    result['nonbonded_inventory']=deepcopy(observation['nonbonded_inventory'])
    return result


@dataclass(frozen=True)
class NativeEndpointMapping:
    """Detached coordinate assignment, not a native-manager or lifetime permit.

    All point arrays use the observed native order. Candidate points are the
    exact PDB decimals; full_precision_points retain the admitted initializer.
    Nothing is applied to a model. The executor still owns crystal/scattering,
    ADPs, topology/geometry, input lifetime and the actual preparation transition.
    """
    endpoint_audit_sha256: str
    native_model_role: str
    native_to_source: tuple
    native_identities: tuple
    movable_native_indices: tuple
    fixed_native_indices: tuple
    native_points: tuple
    parent_points: tuple
    candidate_points: tuple
    full_precision_points: tuple
    source_index_basis: str = "SOURCE_PDB_ATOM_RECORD_ORDER"


def _native_atom_order(native, payload, owner):
    """Share W188's complete source/native bijection through Cedar's reader."""
    identities=model_atom_rows(payload)
    native_keys,_=owner._native_atoms(native,payload)
    input_keys=[((r['chain'] or '_')+':'+str(r['residue_number']),r['residue_code'],r['atom_name'])
                for r in identities]
    if (type(native.get('atom_count')) is not int or native['atom_count']!=len(input_keys)
            or len(native_keys)!=len(input_keys) or len(set(input_keys))!=len(input_keys)
            or len(set(native_keys))!=len(native_keys) or set(native_keys)!=set(input_keys)):
        raise ValueError('Native atom mapping does not cover the exact parent')
    input_index={key:i for i,key in enumerate(input_keys)}
    return tuple(input_index[key] for key in native_keys),tuple(native_keys)


def map_native_endpoint(source, candidate, points, *, movable_indices,
        max_displacement_angstrom, expected_audit_sha256, native,
        native_model_role, native_owner=None):
    """Map one already-admitted endpoint onto an observed native atom order.

    The expected audit digest comes from the existing trusted preview/checkpoint
    join. Caller-supplied points or an unpinned fresh audit are not motion authority.
    Cedar's trusted ``_native_atoms`` owner checks complete identity, element,
    occupancy and coordinates against the explicitly chosen parent/candidate.
    It retains its strict conformer/model scope and roundoff policy. No nearest
    atom matching, relabelling, recut, new tolerance, file format or dispatch.

    Input atom order remains strict; only the native interpretation may reorder.
    Native ADPs, crystal and chemistry remain separate executor-owned checks.
    ``native_owner`` is a trusted dependency, never code imported from a receipt.
    """
    if native_model_role not in ('parent','candidate'):
        raise ValueError('Require an explicit parent or candidate native coordinate role')
    points=tuple(tuple(p) for p in points)
    audit=audit_masked_endpoint(source,candidate,points,movable_indices=movable_indices,
                               max_displacement_angstrom=max_displacement_angstrom)
    if (not isinstance(expected_audit_sha256,str)
            or recipe_digest(audit)!=expected_audit_sha256):
        raise ValueError('Endpoint differs from the admitted audit binding')
    if native_owner is None:
        try:from . import cif_attachment_native as native_owner
        except ImportError as exc:
            raise RuntimeError('The maintained Cedar native atom reader is required') from exc
    if (not isinstance(native,dict) or type(native.get('atom_count')) is not int
            or not isinstance(native.get('atoms'),list)):
        raise ValueError('Require a complete native atom observation')
    # Detach only atom state; unrelated large native geometry inventories stay
    # with their owner and cannot masquerade as chemistry qualification here.
    import json
    observed=json.loads(json.dumps({k:native[k] for k in ('atom_count','atoms')},allow_nan=False))
    payload=source if native_model_role=='parent' else candidate
    order,identities=_native_atom_order(observed,payload,native_owner)
    source_to_native={j:i for i,j in enumerate(order)}
    movable=tuple(source_to_native[i] for i in audit['movable_indices'])
    selected=set(movable)
    def ordered(data):
        xyz=tuple(tuple(float(l[a:b]) for a,b in ((30,38),(38,46),(46,54)))
                  for l in data.splitlines() if l[:6] in (b'ATOM  ',b'HETATM'))
        return tuple(xyz[i] for i in order)
    return NativeEndpointMapping(expected_audit_sha256,native_model_role,order,identities,
        movable,tuple(i for i in range(len(order)) if i not in selected),
        tuple(tuple(a['xyz']) for a in observed['atoms']),ordered(source),ordered(candidate),
        tuple(points[i] for i in order))
