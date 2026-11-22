"""Explicit intrinsic backbone proposals; no fitting, ranking or runtime admission.

Keep P/C4' and every other atom fixed while rotating a congruent O5'/C5'
segment about their axis. An optional reflection selects the other local
congruent branch, not a reflection of the sugar or the molecule. Chemical
context, clashes and evidence still require the existing native owners.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math

from .topostitch_coordinates import ResidueSite, _read_atoms
from .topostitch_endpoint import audit_masked_endpoint
from .topostitch_recipe import model_atom_rows
from .topostitch_transport import CoordinateMask, _rotation, _apply


def _sub(a,b):
    return tuple(x-y for x,y in zip(a,b))


def _cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def _unit(v):
    length=math.hypot(*v)
    if not math.isfinite(length) or length<1e-8:
        raise ValueError('Degenerate intrinsic shoulder frame')
    return tuple(x/length for x in v)


def _handedness(points,indices):
    center=points[indices["C4'"]]
    u,v,w=(_unit(_sub(points[indices[name]],center))for name in ("C3'","O4'","C5'"))
    volume=sum(a*b for a,b in zip(_cross(u,v),w))
    if abs(volume)<1e-8:
        raise ValueError('Degenerate C4 sugar handedness')
    return volume


@dataclass(frozen=True)
class LocalBackboneProposal:
    """Detached proposal and exact endpoint audit, never an admitted motion."""
    candidate_bytes: bytes
    points: tuple
    movable_indices: tuple
    report_json: bytes


def propose_backbone_shoulder(source, *, expected_source_sha256, site,
        reflection, rotation_degrees, max_displacement_angstrom):
    """Propose one explicit local orientation from exact canonical PDB bytes.

    Atom identity uses the existing PDB reader and exact ResidueSite (including
    insertion code), never serial-number order or a nearest-atom guess. First
    scope excludes alternate/partial local residues, explicit local hydrogens
    and movable ANISOU tensors. Only O5' and C5' move; P, C4', all sugar-ring/base
    atoms and metadata remain fixed. Both full precision and PDB rounding obey
    the displacement limit and preserve the initial C4 handedness sign. This
    relative sign check does not establish that the source stereochemistry is
    correct. There is no base-pair, map, diffraction or experimental admission.

    The caller explicitly chooses a reflection and signed rotation in [-180,180]
    degrees about P -> C4'. No search or default scientifically preferred angle
    is supplied. The two-atom proposal does not reuse or change the whole-pair
    bend-preview schema. Native mapping/preparation still needs its own trusted
    admission and full source-chemistry checks before any coordinate transfer.
    """
    if type(source) is not bytes or sha256(source).hexdigest()!=expected_source_sha256:
        raise ValueError('Require exact source PDB bytes and their expected SHA-256')
    if not isinstance(site,ResidueSite) or type(reflection)is not bool:
        raise ValueError('Require an exact residue site and explicit reflection boolean')
    if (type(rotation_degrees)not in (int,float) or not math.isfinite(rotation_degrees)
            or not -180<=rotation_degrees<=180):
        raise ValueError('Require a finite rotation in [-180,180] degrees')
    identities=model_atom_rows(source)
    groups=_read_atoms(source).get(site)
    if not groups or len(groups)!=1:
        raise ValueError('Require one unambiguous local residue segment')
    lines=source.splitlines(keepends=True)
    atom_lines=[i for i,line in enumerate(lines)if line[:6]in(b'ATOM  ',b'HETATM')]
    reference=tuple(tuple(float(lines[i][a:b])for a,b in ((30,38),(38,46),(46,54)))for i in atom_lines)
    local=[i for i,row in enumerate(identities)if (row['chain'],row['residue_number'],row['insertion_code'])==(site.chain,site.residue_number,site.insertion_code)]
    if (len({identities[i]['residue_code']for i in local})!=1 or any(
            identities[i]['residue_code']not in ('DA','DC','DG','DT') or identities[i]['altloc']
            or float(lines[atom_lines[i]][54:60])!=1. for i in local)):
        raise ValueError('Require full-occupancy canonical local DNA without alternates')
    if any(lines[atom_lines[i]][76:78].strip()in(b'H',b'D') or
           identities[i]['atom_name'].lstrip('0123456789').startswith(('H','D'))for i in local):
        raise ValueError('Explicit local hydrogens require a separate qualified motion')
    indices={identities[i]['atom_name']:i for i in local}
    required=('P',"O5'","C5'","C4'","C3'","O4'")
    if not set(required)<=indices.keys():
        raise ValueError('Missing exact shoulder or C4 sugar-frame atoms')
    moving=(indices["O5'"],indices["C5'"])
    mask=CoordinateMask(reference,moving,max_displacement_angstrom)
    origin=reference[indices['P']]
    axis=_unit(_sub(reference[indices["C4'"]],origin))
    normal=_unit(_cross(axis,_sub(reference[indices["O5'"]],origin)))
    rotation=_rotation(tuple(v*rotation_degrees for v in axis),1.)
    points=list(reference)
    if reflection or rotation_degrees!=0:
        for i in moving:
            vector=_sub(reference[i],origin)
            if reflection:
                dot=sum(x*n for x,n in zip(vector,normal))
                vector=tuple(x-2*dot*n for x,n in zip(vector,normal))
            points[i]=tuple(o+x for o,x in zip(origin,_apply(rotation,vector)))
    points=tuple(points)
    mask.displacements(points)
    before=_handedness(reference,indices);after=_handedness(points,indices)
    if before*after<=0:
        raise ValueError('Proposal changes C4 sugar handedness')
    rendered=lines.copy();rounded=list(reference)
    for i in moving:
        fields=''.join(f'{v:8.3f}'for v in points[i]).encode('ascii')
        if len(fields)!=24:raise ValueError('Endpoint coordinate exceeds PDB field width')
        line=lines[atom_lines[i]];rendered[atom_lines[i]]=line[:30]+fields+line[54:]
        rounded[i]=tuple(float(fields[a:b])for a,b in ((0,8),(8,16),(16,24)))
    rounded_sign=_handedness(rounded,indices)
    if before*rounded_sign<=0:
        raise ValueError('PDB rounding changes C4 sugar handedness')
    candidate=b''.join(rendered)
    audit=audit_masked_endpoint(source,candidate,points,movable_indices=moving,
        max_displacement_angstrom=max_displacement_angstrom)
    chain=[indices[n]for n in required[:4]]
    error=max(abs(math.dist(points[i],points[j])-math.dist(reference[i],reference[j]))
              for k,i in enumerate(chain)for j in chain[:k])
    report=dict(kind='topostitch-intrinsic-shoulder-proposal',schema_version=1,
        source_model_sha256=sha256(source).hexdigest(),candidate_model_sha256=sha256(candidate).hexdigest(),
        site=asdict(site),reflection=reflection,rotation_degrees=float(rotation_degrees),
        fixed_axis_indices=[indices['P'],indices["C4'"]],movable_indices=list(moving),
        index_basis='SOURCE_PDB_ATOM_RECORD_ORDER',max_internal_distance_error_angstrom=error,
        C4_normalized_volumes=dict(source=before,full_precision=after,rounded=rounded_sign),
        relative_C4_handedness_preserved=True,endpoint_audit=audit,
        motion_admission=False,geometry_accepted=False,scientific_acceptance=False)
    return LocalBackboneProposal(candidate,points,moving,
        json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
