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
from typing import Mapping
import re


class PhosphateError(ValueError):
    """A phosphate cannot be classified or cleaned without guessing."""


_ALIASES = {"O1P": "OP1", "O2P": "OP2", "O3P": "OP3"}
_MIN_PO = 1.2
_MAX_PO = 2.1


def validate_op3_sites(values: object) -> tuple[str, ...]:
    """Validate explicit, site-scoped consent; never interpret a truthy flag."""
    if not isinstance(values, (list, tuple)):
        raise PhosphateError("allow_op3_sites must be a list of CHAIN:RESID sites")
    sites = []
    for value in values:
        if not isinstance(value, str) or re.fullmatch(
            r"[A-Za-z0-9_]:-?(?:0|[1-9][0-9]*)[A-Za-z]?", value
        ) is None:
            raise PhosphateError(f"Invalid OP3 site {value!r}; use CHAIN:RESID, e.g. A:1")
        if value in sites:
            raise PhosphateError(f"Duplicate OP3 request: {value}")
        sites.append(value)
    return tuple(sites)


def validate_phosphate_intent(value: object, sites: tuple[str, ...]) -> None:
    """Check an additive frozen chemistry record without consulting current recipes."""
    if not isinstance(value, Mapping) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise PhosphateError("Malformed frozen phosphate intent schema")
    source = value.get("source")
    if not isinstance(source, str) or source not in {"recipe", "dataset", "none"}:
        raise PhosphateError("Malformed frozen phosphate intent source")
    if validate_op3_sites(value.get("allow_op3_sites")) != sites:
        raise PhosphateError("Frozen phosphate intent differs from allowed OP3 sites")
    if "recipe" not in value:
        raise PhosphateError("Frozen phosphate intent is missing its recipe declaration")
    recipe = value["recipe"]
    if recipe is not None:
        if not isinstance(recipe, Mapping):
            raise PhosphateError("Malformed frozen phosphate recipe")
        for key in ("id", "version", "frame"):
            text = recipe.get(key)
            if not isinstance(text, str) or not text.strip() or any(ord(c) < 32 for c in text):
                raise PhosphateError(f"Malformed frozen phosphate recipe {key}")
        for key in ("sha256", "config_sha256"):
            if not isinstance(recipe.get(key), str) or re.fullmatch(r"[0-9a-f]{64}", recipe[key]) is None:
                raise PhosphateError(f"Malformed frozen phosphate recipe {key}")
        declared = validate_op3_sites(recipe.get("terminal_phosphate_sites"))
        if source == "recipe" and declared != sites:
            raise PhosphateError("Frozen recipe phosphate sites disagree with effective intent")
    elif source == "recipe":
        raise PhosphateError("Recipe-derived phosphate intent has no recipe declaration")
    if source == "none" and (sites or recipe is not None):
        raise PhosphateError("Unrequested phosphate intent cannot authorize sites")


def phosphate_intent_summary(sites: object, intent: object = None) -> str:
    allowed = validate_op3_sites(sites)
    label = "legacy frozen intent" if allowed else "no request"
    if intent is not None:
        validate_phosphate_intent(intent, allowed)
        source = intent["source"]
        if source == "recipe":
            recipe = intent["recipe"]
            label = f"recipe {recipe['id']}@{recipe['version']}"
        elif source == "dataset":
            label = "explicit dataset override"
    return f"5'-phosphate/OP3 sites: {', '.join(allowed) or 'none'} ({label})"


def requested_op3_sites(report: Mapping[str, object]) -> tuple[str, ...]:
    """Read frozen intent, not coordinate presence or current nasolve.txt."""
    plan = report.get("post_mr_plan")
    if plan is not None and not isinstance(plan, Mapping):
        raise PhosphateError("Malformed frozen post-MR plan")
    sites = validate_op3_sites(plan.get("allow_op3_sites", []) if plan else [])
    if plan and "phosphate_intent" in plan:
        validate_phosphate_intent(plan["phosphate_intent"], sites)
    postmr = report.get("postmr")
    if isinstance(postmr, Mapping) and "phosphate_policy" in postmr:
        policy = postmr["phosphate_policy"]
        if not isinstance(policy, Mapping) or policy.get("mode") != "op3-explicit-opt-in-v1":
            raise PhosphateError("Malformed frozen phosphate policy")
        if validate_op3_sites(policy.get("allow_op3_sites")) != sites:
            raise PhosphateError("PostMR phosphate consent differs from frozen AutoMR intent")
    return sites


def _name(value: str) -> str:
    value = value.strip().upper().replace("*", "'")
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
        if op_id in ends and extra is not None:
            raise PhosphateError(f"Phosphate {phosphorus.site}: OP3 has an explicit LINK; inspect before removal")
        if p_id in ends:
            other = ends[1] if ends[0] == p_id else ends[0]
            if other[2] != "O3'" and other not in {
                (phosphorus.chain, phosphorus.resid, name) for name in ("OP1", "OP2", "OP3", "O5'")
            }:
                raise PhosphateError(f"Phosphate {phosphorus.site}: unexpected explicit phosphorus LINK")
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
            if extra is not None and extra.serial in (a, b):
                other = b if a == extra.serial else a
                if other != phosphorus.serial:
                    raise PhosphateError(f"Phosphate {phosphorus.site}: OP3 has an unexpected CONECT bond")
            if phosphorus.serial in (a, b):
                other = b if a == phosphorus.serial else a
                for atom in by_serial[other]:
                    if atom.name == "O3'" and atom.key != phosphorus.key and atom != incoming:
                        raise PhosphateError(f"Phosphate {phosphorus.site}: CONECT incoming link is not confirmed by local connectivity")


def _process_phosphates(
    source: Path,
    destination: Path | None,
    *,
    reference_model: Path | None = None,
    check_sites: tuple[str, ...] = (),
    inspect_sites: tuple[str, ...] = (),
    allow_op3_sites: tuple[str, ...] = (),
) -> dict[str, object]:
    """Remove only OP3/O3P with a verified incoming nucleotide O3'-P link.

    The source is preserved. TER boundaries, insertion codes, alternate atoms,
    and explicit connections are respected. Previously repaired sites may be
    rechecked after ReadySet even when their extra oxygen is already absent.
    """
    allowed = set(validate_op3_sites(allow_op3_sites))
    if destination is not None and source.resolve() == destination.resolve():
        raise PhosphateError("Phosphate cleanup requires a separate output; preserve the raw model")
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    atoms = _atoms(lines)
    groups: dict[tuple[int, int, str, str], list[_Atom]] = defaultdict(list)
    for atom in atoms:
        groups[atom.key].append(atom)
    sugar_names = {"C1'", "C2'", "C3'", "C4'", "C5'", "O3'", "O4'", "O5'"}
    requested = set(check_sites) | set(inspect_sites) | allowed
    targets = [group for group in groups.values()
               if any(a.name == "OP3" for a in group) or group[0].site in requested]
    missing = requested - {group[0].site for group in targets}
    if missing:
        raise PhosphateError("Requested phosphate site is absent: " + ", ".join(sorted(missing)))
    missing_sites = set(check_sites) - {group[0].site for group in targets}
    if missing_sites:
        raise PhosphateError("Previously repaired phosphate site disappeared: " + ", ".join(sorted(missing_sites)))
    reference = _atoms(reference_model.read_text(encoding="utf-8").splitlines(keepends=True)) if reference_model else []
    report: dict[str, object] = {"removed": [], "retained": [], "checked": [],
        "connectivity_distance_range_angstrom": [_MIN_PO, _MAX_PO],
        "angle_range_degrees": [60., 160.],
        "input_sha256": sha256(source.read_bytes()).hexdigest(),
        "mode": "op3-explicit-opt-in-v1", "allow_op3_sites": list(allow_op3_sites)}
    removed_atoms = []
    seen_sites: set[str] = set()
    for group in targets:
        site = group[0].site
        if site in seen_sites:
            raise PhosphateError(f"Phosphate {site}: repeated residue identity or multiple models requires inspection")
        seen_sites.add(site)
        if len({a.name for a in group} & sugar_names) < 2:
            raise PhosphateError(f"Phosphate {site}: OP3 or its request is not on an identifiable nucleotide")
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
        if site in allowed:
            if incoming is not None:
                raise PhosphateError(f"Phosphate {site}: explicit OP3 request conflicts with an internal O3'-P link")
            if extra is None:
                raise PhosphateError(f"Phosphate {site}: requested OP3 is absent; automatic terminal-phosphate construction is not supported")
            if any(a.name == "O3'" and dist(a.xyz, p.xyz) <= _MAX_PO for a in group):
                raise PhosphateError(f"Phosphate {site}: possible cyclic phosphate is not a 5'-terminal OP3 exception")
            # Consent cannot convert a cross-chain/TER/symmetry bond into a terminus.
            if any(a.name == "O3'" and a.key != p.key and a.model == p.model
                   and dist(a.xyz, p.xyz) <= _MAX_PO for a in atoms):
                raise PhosphateError(f"Phosphate {site}: possible incoming link across a chain/TER boundary requires review")
        elif extra is not None and incoming is None:
            raise PhosphateError(f"Phosphate {site}: unrequested terminal/unlinked OP3; review the chemistry or explicitly set allow_op3_sites for a valid 5'-phosphate")
        if site in inspect_sites and incoming is None and extra is None:
            raise PhosphateError(f"Phosphate {site}: absent OP3 without a verified incoming O3'-P link; terminal dictionary profile requires review")
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
        outgoing_site = None
        own_o3 = [a for a in group if a.name == "O3'"]
        if own_o3:
            o3 = _one(own_o3, "O3'", site)
            outgoing = [a for a in atoms if a.name == "P" and a.key != p.key
                        and a.model == p.model and a.chain == p.chain and a.segment == p.segment
                        and dist(a.xyz, o3.xyz) <= _MAX_PO]
            if len(outgoing) > 1 or (outgoing and dist(outgoing[0].xyz, o3.xyz) < _MIN_PO):
                raise PhosphateError(f"Phosphate {site}: ambiguous outgoing O3'-P connection")
            if outgoing:
                outgoing_site = outgoing[0].site
        details = {"site": site, "residue": p.line[17:20].strip(),
            "incoming_site": incoming.site if incoming else None, "outgoing_site": outgoing_site,
            "p_o_distances_angstrom": lengths, "o_p_o_angles_degrees": angles}
        report["checked"].append(details)
        if extra is not None and incoming is not None:
            removed_atoms.append(extra)
            report["removed"].append({**details, "atom": extra.line[12:16].strip(),
                "serial": extra.serial, "reason": "verified-incoming-O3-prime-P-link"})
        elif extra is not None:
            report["retained"].append({**details, "atom": extra.line[12:16].strip(),
                "reason": "explicitly-requested-unlinked-phosphate"})
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
    cleaned = "".join(output)
    if destination is not None:
        destination.write_text(cleaned, encoding="utf-8")
    report["output_sha256"] = sha256(cleaned.encode("utf-8")).hexdigest()
    return report


def sanitize_phosphates(
    source: Path, destination: Path, *, reference_model: Path | None = None,
    check_sites: tuple[str, ...] = (), allow_op3_sites: tuple[str, ...] = (),
) -> dict[str, object]:
    """Remove verified internal extras; retain terminal OP3 only with consent.

    Unrequested unlinked OP3 stops preparation, rather than deleting an oxygen
    and pretending an incomplete phosphate is sound. Raw inputs are preserved.
    """
    return _process_phosphates(source, destination, reference_model=reference_model,
                              check_sites=check_sites, allow_op3_sites=allow_op3_sites)


def audit_phosphates(
    source: Path, *, allow_op3_sites: tuple[str, ...] = (),
    inspect_sites: tuple[str, ...] = (), check_sites: tuple[str, ...] = (),
    reference_model: Path | None = None,
) -> dict[str, object]:
    """Read-only gate: a model needing cleanup is not checkpoint-ready."""
    result = _process_phosphates(source, None, allow_op3_sites=allow_op3_sites,
                                inspect_sites=inspect_sites, check_sites=check_sites,
                                reference_model=reference_model)
    if result["removed"]:
        sites = ", ".join(row["site"] for row in result["removed"])
        raise PhosphateError(f"Unrequested internal OP3 remains at {sites}; prepare a new model, do not alter an existing checkpoint")
    return result
