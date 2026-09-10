"""Conservative cleanup of leaving oxygens on linked nucleotide phosphates.

Distances here are broad connectivity guards, not ideal refinement restraints.
Uncertain chemistry is reported as an error; coordinates are never rebuilt.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
from math import acos, degrees, dist, isfinite
from pathlib import Path


class PhosphateError(ValueError):
    """A phosphate cannot be classified or cleaned without guessing."""


_ALIASES = {"O1P": "OP1", "O2P": "OP2", "O3P": "OP3"}
_MIN_PO = 1.2
_MAX_PO = 2.1


def _name(value: str) -> str:
    value = value.strip().replace("*", "'")
    return _ALIASES.get(value, value)


@dataclass(frozen=True)
class _Atom:
    index: int
    line: str
    model: int
    segment: int

    @property
    def chain(self) -> str:
        return self.line[21:22].strip() or "_"

    @property
    def resid(self) -> str:
        return self.line[22:27].strip()

    @property
    def site(self) -> str:
        return f"{self.chain}:{self.resid}"

    @property
    def key(self) -> tuple[int, int, str, str]:
        return self.model, self.segment, self.chain, self.resid

    @property
    def name(self) -> str:
        return _name(self.line[12:16])

    @property
    def serial(self) -> str:
        return self.line[6:11].strip()

    @property
    def xyz(self) -> tuple[float, float, float]:
        try:
            xyz = tuple(float(self.line[n:n + 8]) for n in (30, 38, 46))
        except ValueError as exc:
            raise PhosphateError(f"Invalid coordinates at {self.site} {self.name}") from exc
        if not all(isfinite(v) for v in xyz):
            raise PhosphateError(f"Nonfinite coordinates at {self.site} {self.name}")
        return xyz  # type: ignore[return-value]


def _atoms(lines: list[str]) -> list[_Atom]:
    result = []
    model = segment = 0
    for index, line in enumerate(lines):
        if line.startswith("MODEL "):
            model += 1
            segment = 0
        elif line.startswith("TER"):
            segment += 1
        elif line.startswith(("ATOM  ", "HETATM")):
            result.append(_Atom(index, line, model, segment))
    return result


def _one(atoms: list[_Atom], name: str, site: str) -> _Atom:
    matches = [a for a in atoms if a.name == name]
    if len(matches) != 1:
        raise PhosphateError(f"Phosphate {site}: expected one {name}, found {len(matches)}")
    atom = matches[0]
    if atom.line[16:17].strip():
        raise PhosphateError(f"Phosphate {site}: ambiguous alternate conformation for {name}")
    element = atom.line[76:78].strip().upper()
    expected = "P" if name == "P" else "O"
    if element and element != expected:
        raise PhosphateError(f"Phosphate {site}: {name} has element {element}, expected {expected}")
    return atom


def _incoming(phosphorus: _Atom, atoms: list[_Atom]) -> _Atom | None:
    near = [a for a in atoms if a.name == "O3'" and a.key != phosphorus.key
            and a.model == phosphorus.model and a.segment == phosphorus.segment
            and a.chain == phosphorus.chain and dist(a.xyz, phosphorus.xyz) <= _MAX_PO]
    if len(near) > 1:
        raise PhosphateError(f"Phosphate {phosphorus.site}: multiple possible incoming O3' links")
    if not near:
        return None
    oxygen = _one(near, "O3'", near[0].site)
    if dist(oxygen.xyz, phosphorus.xyz) < _MIN_PO:
        raise PhosphateError(f"Phosphate {phosphorus.site}: implausibly short incoming O3'-P link")
    return oxygen


def _check_outgoing(group: list[_Atom], reference_p: _Atom, reference: list[_Atom],
                    atoms: list[_Atom]) -> None:
    """Preserve a reference-known link from this nucleotide to the next P."""
    reference_group = [a for a in reference if a.key == reference_p.key]
    reference_oxygen = [a for a in reference_group if a.name == "O3'"]
    if not reference_oxygen:
        return
    old_o = _one(reference_oxygen, "O3'", reference_p.site)
    partners = [a for a in reference if a.name == "P" and a.key != old_o.key
                and a.model == old_o.model and a.segment == old_o.segment
                and a.chain == old_o.chain and dist(a.xyz, old_o.xyz) <= _MAX_PO]
    if not partners:
        return
    if len(partners) != 1 or dist(partners[0].xyz, old_o.xyz) < _MIN_PO:
        raise PhosphateError(f"Phosphate {reference_p.site}: ambiguous reference outgoing O3'-P link")
    oxygen = _one(group, "O3'", reference_p.site)
    current = [a for a in atoms if a.name == "P" and a.site == partners[0].site
               and a.model == oxygen.model and a.segment == oxygen.segment]
    if len(current) != 1 or not _MIN_PO <= dist(oxygen.xyz, current[0].xyz) <= _MAX_PO:
        raise PhosphateError(f"Phosphate {reference_p.site}: outgoing O3'-P link changed or disappeared from the reference model")


def _link_end(line: str, offset: int) -> tuple[str, str, str]:
    return (line[21 + offset:22 + offset].strip() or "_",
            line[22 + offset:27 + offset].strip(), _name(line[12 + offset:16 + offset]))


def _check_explicit_links(lines: list[str], phosphorus: _Atom, extra: _Atom | None,
                          incoming: _Atom | None, atoms: list[_Atom]) -> None:
    p_id = (phosphorus.chain, phosphorus.resid, "P")
    op_id = (phosphorus.chain, phosphorus.resid, "OP3")
    for line in lines:
        if not line.startswith("LINK  "):
            continue
        ends = (_link_end(line, 0), _link_end(line, 30))
        if op_id in ends and extra is not None and incoming is not None:
            raise PhosphateError(f"Phosphate {phosphorus.site}: OP3 has an explicit LINK; inspect before removal")
        if p_id in ends:
            other = ends[1] if ends[0] == p_id else ends[0]
            if other[2] == "O3'":
                if incoming is None or other[:2] != (incoming.chain, incoming.resid):
                    raise PhosphateError(f"Phosphate {phosphorus.site}: explicit incoming LINK is not confirmed by local connectivity")
                symmetry = (line[59:65].strip(), line[66:72].strip())
                if any(s not in ("", "1555", "1_555") for s in symmetry):
                    raise PhosphateError(f"Phosphate {phosphorus.site}: symmetry LINK requires inspection")
    by_serial = defaultdict(list)
    for atom in atoms:
        by_serial[atom.serial].append(atom)
    for line in lines:
        if not line.startswith("CONECT"):
            continue
        serials = [line[n:n + 5].strip() for n in range(6, len(line.rstrip()), 5)]
        serials = [s for s in serials if s]
        if not serials:
            continue
        for a, b in ((serials[0], s) for s in serials[1:]):
            affects_phosphate = phosphorus.serial in (a, b) or (
                extra is not None and incoming is not None and extra.serial in (a, b)
            )
            if affects_phosphate and any(len(by_serial[s]) != 1 for s in (a, b)):
                raise PhosphateError(
                    f"Phosphate {phosphorus.site}: CONECT {a}-{b} has ambiguous "
                    "or missing atom serials; inspect the connection before cleanup"
                )
            if extra is not None and incoming is not None and extra.serial in (a, b):
                other = b if a == extra.serial else a
                if other != phosphorus.serial:
                    raise PhosphateError(f"Phosphate {phosphorus.site}: OP3 has an unexpected CONECT bond")
            if phosphorus.serial in (a, b):
                other = b if a == phosphorus.serial else a
                for atom in by_serial[other]:
                    if atom.name == "O3'" and atom.key != phosphorus.key and atom != incoming:
                        raise PhosphateError(f"Phosphate {phosphorus.site}: CONECT incoming link is not confirmed by local connectivity")


def sanitize_phosphates(
    source: Path,
    destination: Path,
    *,
    reference_model: Path | None = None,
    check_sites: tuple[str, ...] = (),
) -> dict[str, object]:
    """Remove only OP3/O3P with a verified incoming nucleotide O3'-P link.

    The source is preserved. TER boundaries, insertion codes, alternate atoms,
    and explicit connections are respected. Previously repaired sites may be
    rechecked after ReadySet even when their extra oxygen is already absent.
    """
    if source.resolve() == destination.resolve():
        raise PhosphateError("Phosphate cleanup requires a separate output; preserve the raw model")
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    atoms = _atoms(lines)
    groups: dict[tuple[int, int, str, str], list[_Atom]] = defaultdict(list)
    for atom in atoms:
        groups[atom.key].append(atom)
    sugar_names = {"C1'", "C2'", "C3'", "C4'", "C5'", "O3'", "O4'", "O5'"}
    targets = [group for group in groups.values()
               if (any(a.name == "OP3" for a in group)
                   and len({a.name for a in group} & sugar_names) >= 2)
               or group[0].site in check_sites]
    missing_sites = set(check_sites) - {group[0].site for group in targets}
    if missing_sites:
        raise PhosphateError("Previously repaired phosphate site disappeared: " + ", ".join(sorted(missing_sites)))
    reference = _atoms(reference_model.read_text(encoding="utf-8").splitlines(keepends=True)) if reference_model else []
    report: dict[str, object] = {"removed": [], "retained": [], "checked": [],
        "connectivity_distance_range_angstrom": [_MIN_PO, _MAX_PO],
        "angle_range_degrees": [60., 160.],
        "input_sha256": sha256(source.read_bytes()).hexdigest()}
    removed_atoms = []
    seen_sites: set[str] = set()
    for group in targets:
        site = group[0].site
        if site in seen_sites:
            raise PhosphateError(f"Phosphate {site}: repeated residue identity or multiple models requires inspection")
        seen_sites.add(site)
        p = _one(group, "P", site)
        oxygen_names = ("OP1", "OP2", "O5'")
        oxygens = [_one(group, n, site) for n in oxygen_names]
        extra = _one(group, "OP3", site) if any(a.name == "OP3" for a in group) else None
        incoming = _incoming(p, atoms)
        reference_p = [a for a in reference if a.site == site and a.name == "P"]
        if len(reference_p) > 1:
            raise PhosphateError(f"Phosphate {site}: ambiguous reference phosphorus")
        if reference_p:
            original_incoming = _incoming(reference_p[0], reference)
            if (incoming.site if incoming else None) != (original_incoming.site if original_incoming else None):
                raise PhosphateError(f"Phosphate {site}: incoming O3'-P link changed or disappeared from the reference model")
            _check_outgoing(group, reference_p[0], reference, atoms)
        if site in check_sites and incoming is None:
            raise PhosphateError(f"Previously repaired phosphate {site} lost its incoming O3'-P link")
        _check_explicit_links(lines, p, extra, incoming, atoms)
        if incoming is not None:
            oxygens.append(incoming)
        elif extra is not None:
            oxygens.append(extra)
        lengths = {}
        for oxygen in oxygens:
            length = dist(p.xyz, oxygen.xyz)
            label = f"{oxygen.site}/{oxygen.name}"
            if not _MIN_PO <= length <= _MAX_PO:
                raise PhosphateError(f"Phosphate {site}: implausible P-{oxygen.name} distance {length:.3f} A")
            lengths[label] = round(length, 4)
        angles = {}
        for first, second in combinations(oxygens, 2):
            u = tuple(x - y for x, y in zip(first.xyz, p.xyz))
            v = tuple(x - y for x, y in zip(second.xyz, p.xyz))
            cosine = sum(x * y for x, y in zip(u, v)) / (dist(first.xyz, p.xyz) * dist(second.xyz, p.xyz))
            angle = degrees(acos(max(-1., min(1., cosine))))
            if not 60. <= angle <= 160.:
                raise PhosphateError(f"Phosphate {site}: implausible {first.name}-P-{second.name} angle {angle:.1f} degrees")
            angles[f"{first.site}/{first.name}-P-{second.site}/{second.name}"] = round(angle, 2)
        details = {"site": site, "residue": p.line[17:20].strip(),
            "incoming_site": incoming.site if incoming else None,
            "p_o_distances_angstrom": lengths, "o_p_o_angles_degrees": angles}
        report["checked"].append(details)
        if extra is not None and incoming is not None:
            removed_atoms.append(extra)
            report["removed"].append({**details, "atom": extra.line[12:16].strip(),
                "serial": extra.serial, "reason": "verified-incoming-O3-prime-P-link"})
        elif extra is not None:
            report["retained"].append({**details, "atom": extra.line[12:16].strip(),
                "reason": "unlinked-or-terminal-phosphate"})
    removed_indices = {a.index for a in removed_atoms}
    removed_serials = {a.serial for a in removed_atoms}
    # Coot model merges can retain per-monomer serials. Coordinate selection
    # and atom-associated records have full identities; only CONECT relies
    # exclusively on serials, and affected ambiguous edges were rejected above.
    removed_identities = {(a.model, a.segment, a.line[12:27]) for a in removed_atoms}
    output = []
    model = segment = 0
    for index, line in enumerate(lines):
        if line.startswith("MODEL "):
            model += 1
            segment = 0
        elif line.startswith("TER"):
            segment += 1
        if index in removed_indices:
            continue
        if line.startswith(("ANISOU", "SIGATM", "SIGUIJ")) and (
            model, segment, line[12:27]
        ) in removed_identities:
            continue
        if line.startswith("CONECT") and removed_serials:
            serials = [line[n:n + 5].strip() for n in range(6, len(line.rstrip()), 5)]
            serials = [s for s in serials if s]
            if serials and serials[0] in removed_serials:
                continue
            if any(s in removed_serials for s in serials):
                serials = [s for s in serials if s not in removed_serials]
                if len(serials) < 2:
                    continue
                line = "CONECT" + "".join(f"{s:>5}" for s in serials) + "\n"
        output.append(line)
    destination.write_text("".join(output), encoding="utf-8")
    report["output_sha256"] = sha256(destination.read_bytes()).hexdigest()
    return report
