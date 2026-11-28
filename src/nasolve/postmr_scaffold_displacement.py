"""Carry isotropic B values across an already verified DNA scaffold restoration."""
from hashlib import sha256
from math import isfinite
from pathlib import Path

from .postmr_restoration import RNA_ROLES, canonical_name

_POLICY = "postmr-identical-host-scaffold-isotropic-b-v1"
_ATOMS = {"ATOM", "HETATM"}
_ASSOCIATED = {"ANISOU", "SIGATM", "SIGUIJ"}


def _site(line):
    return (line[21:22].strip() or "_", line[22:27].strip())


def _indexed(lines):
    sites = {}
    for line in lines:
        kind = line[:6].strip()
        if kind in {"MODEL", "ENDMDL"}:
            return None
        if kind in _ATOMS | _ASSOCIATED:
            sites.setdefault(_site(line), []).append(line)
    return sites


def _validated_b_field(donor, restored):
    if min(len(atom.rstrip("\r\n")) for atom in (donor, restored)) < 78:
        raise ValueError("Incomplete scaffold atom fields")
    element = donor[76:78].strip().upper()
    if not element or element != restored[76:78].strip().upper():
        raise ValueError("Host and restored scaffold elements differ")
    if any(float(donor[i:i+8]) != float(restored[i:i+8]) for i in (30, 38, 46)):
        raise ValueError("Host and restored scaffold coordinates differ")
    occ = float(donor[54:60])
    b = float(donor[60:66])
    if not (0 < occ <= 1 and occ == float(restored[54:60]) and isfinite(b) and b >= 0):
        raise ValueError("Unusable host B factor or incompatible occupancy")
    return donor[60:66]


class HostDisplacement:
    """Bind original and raw model state once for the selected restoration sites."""

    def __init__(self, original, raw_lines, *, canonical_ribose=False):
        self.canonical_ribose = canonical_ribose
        payload = Path(original).read_bytes()
        self.source_sha256 = sha256(payload).hexdigest()
        self.original = _indexed(payload.decode("utf-8", errors="replace").splitlines())
        self.raw = _indexed(raw_lines)

    def apply(self, action, restored, geometry):
        record = {"policy_id": _POLICY, "source_sha256": self.source_sha256}
        if self.canonical_ribose:
            record["source"] = "VERIFIED_CANONICAL_RIBOSE_INPUT"
        try:
            supported = RNA_ROLES if self.canonical_ribose else {"DA", "DC", "DG", "DT"}
            if action.before not in supported:
                raise ValueError("Incoming residue needs its own sugar and phosphate mapping")
            if self.original is None or self.raw is None:
                raise ValueError("Multiple-model records require a model selector")
            site = tuple(action.site.split(":"))
            original = self.original.get(site, [])
            if any(line[:6].strip() in _ASSOCIATED or line[16:17].strip()
                   for group in (original, self.raw.get(site, [])) for line in group):
                raise ValueError("Site has an alternate conformation or associated displacement records")
            scaffold = set(geometry["scaffold_atoms"])
            if any(line[17:20].strip() != action.before for line in original):
                raise ValueError("Ambiguous host component identity")
            donors = {}
            for line in original:
                name = canonical_name(line[12:16].strip())
                if name in scaffold:
                    if name in donors:
                        raise ValueError("Ambiguous host scaffold atom identity")
                    donors[name] = line
            if donors.keys() != scaffold:
                raise ValueError("Host lacks a restored scaffold atom")
            result = []
            changed = []
            for line in restored:
                name = canonical_name(line[12:16].strip())
                if name in donors:
                    donor = donors[name]
                    b_field = _validated_b_field(donor, line)
                    if line[60:66] != b_field:
                        changed.append(name)
                        line = line[:60] + b_field + line[66:]
                result.append(line)
        except ValueError as exc:
            geometry["host_displacement"] = dict(record, status="RETAINED", reason=str(exc))
            return restored
        geometry["host_displacement"] = dict(record, status="TRANSFERRED", atoms=sorted(scaffold),
                                             changed_atoms=sorted(changed))
        if changed:
            geometry["metadata_preserved"] = False
        return result
