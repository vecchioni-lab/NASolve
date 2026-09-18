"""Backbone-chemistry policy, terminal phosphate construction, and review state.

The automatic contract is deliberately narrow: ordinary DNA/RNA-like residues use
standard phosphodiester connectivity.  Unsupported backbone chemistry is never
inferred from atom names or distances.  A user may explicitly mark individual
sites as experimental passthrough; those sites are carried through without the
standard phosphate validator and remain visibly unreviewed until a human checks
an output model.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Mapping

from .run_context import artifact_reference


class BackboneError(ValueError):
    """Backbone chemistry cannot be interpreted without guessing."""


_SITE = re.compile(r"[A-Za-z0-9_]:-?(?:0|[1-9][0-9]*)[A-Za-z]?")
_ALLOWED_SITE_MODES = frozenset({"standard", "experimental_passthrough"})
_PHOSPHATE_NAMES = frozenset({"P", "OP1", "OP2", "OP3", "O1P", "O2P", "O3P"})
_ALIASES = {"O1P": "OP1", "O2P": "OP2", "O3P": "OP3", "O5*": "O5'", "C5*": "C5'"}


def validate_site(value: object) -> str:
    if not isinstance(value, str) or _SITE.fullmatch(value) is None:
        raise BackboneError(f"Invalid backbone site {value!r}; use CHAIN:RESID, e.g. A:12")
    return value


def validate_backbone_sites(value: object) -> dict[str, str]:
    """Validate a site->mode mapping without inferring chemistry."""
    if not isinstance(value, Mapping):
        raise BackboneError("backbone_sites must be a mapping of CHAIN:RESID to mode")
    result: dict[str, str] = {}
    for raw_site, raw_mode in value.items():
        site = validate_site(raw_site)
        if not isinstance(raw_mode, str):
            raise BackboneError(f"Backbone mode at {site} must be text")
        mode = raw_mode.strip().casefold().replace("-", "_")
        if mode not in _ALLOWED_SITE_MODES:
            raise BackboneError(
                f"Unsupported backbone mode {raw_mode!r} at {site}; use standard or "
                "experimental_passthrough. Reviewed custom linkage recipes are a future extension."
            )
        if site in result:
            raise BackboneError(f"Duplicate backbone site: {site}")
        result[site] = mode
    return result


def make_backbone_policy(
    sites: Mapping[str, str], *, allow_unreviewed: bool = False
) -> dict[str, object]:
    normalized = validate_backbone_sites(sites)
    if type(allow_unreviewed) is not bool:
        raise BackboneError("allow_unreviewed_backbone must be true or false")
    return {
        "schema_version": 1,
        "default": "standard_phosphodiester",
        "sites": normalized,
        "allow_unreviewed": allow_unreviewed,
        "experimental_passthrough_sites": sorted(
            site for site, mode in normalized.items() if mode == "experimental_passthrough"
        ),
    }


def validate_backbone_policy(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping) or value.get("schema_version") != 1:
        raise BackboneError("Malformed frozen backbone policy")
    if value.get("default") != "standard_phosphodiester":
        raise BackboneError("Unsupported default backbone contract")
    sites = validate_backbone_sites(value.get("sites", {}))
    allow = value.get("allow_unreviewed")
    if type(allow) is not bool:
        raise BackboneError("Malformed allow_unreviewed backbone flag")
    expected = sorted(site for site, mode in sites.items() if mode == "experimental_passthrough")
    if value.get("experimental_passthrough_sites") != expected:
        raise BackboneError("Frozen experimental backbone site list is inconsistent")
    return make_backbone_policy(sites, allow_unreviewed=allow)


def requested_backbone_policy(report: Mapping[str, object]) -> dict[str, object]:
    plan = report.get("post_mr_plan")
    if plan is None:
        return make_backbone_policy({})
    if not isinstance(plan, Mapping):
        raise BackboneError("Malformed frozen post-MR plan")
    value = plan.get("backbone_policy")
    return make_backbone_policy({}) if value is None else validate_backbone_policy(value)


def _name(value: str) -> str:
    text = value.strip().upper().replace("*", "'")
    return _ALIASES.get(text, text)


@dataclass(frozen=True)
class _PdbAtom:
    index: int
    line: str

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
    def name(self) -> str:
        return _name(self.line[12:16])

    @property
    def xyz(self) -> tuple[float, float, float]:
        try:
            return tuple(float(self.line[n:n + 8]) for n in (30, 38, 46))  # type: ignore[return-value]
        except ValueError as exc:
            raise BackboneError(f"Invalid coordinates at {self.site} {self.name}") from exc


def _atoms(lines: list[str]) -> list[_PdbAtom]:
    return [
        _PdbAtom(index, line)
        for index, line in enumerate(lines)
        if line.startswith(("ATOM  ", "HETATM")) and len(line) >= 54
    ]


def _one(group: list[_PdbAtom], name: str, site: str) -> _PdbAtom:
    matches = [atom for atom in group if atom.name == name]
    if len(matches) != 1:
        raise BackboneError(f"5'-phosphate {site}: expected one {name}, found {len(matches)}")
    if matches[0].line[16:17].strip():
        raise BackboneError(f"5'-phosphate {site}: alternate conformation on {name} requires review")
    return matches[0]


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(x - y for x, y in zip(a, b))  # type: ignore[return-value]


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(x + y for x, y in zip(a, b))  # type: ignore[return-value]


def _scale(a: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(x * factor for x in a)  # type: ignore[return-value]


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(vector: tuple[float, float, float], context: str) -> tuple[float, float, float]:
    length = math.sqrt(_dot(vector, vector))
    if length < 1e-6:
        raise BackboneError(f"Cannot construct {context}: degenerate reference geometry")
    return _scale(vector, 1.0 / length)


def _new_atom(
    template: str,
    serial: int,
    name: str,
    xyz: tuple[float, float, float],
    element: str,
) -> str:
    if serial > 99999:
        raise BackboneError("Cannot construct terminal phosphate: PDB atom serial limit exceeded")
    chars = list(template.rstrip("\n").ljust(80))
    chars[6:11] = list(f"{serial:5d}")
    chars[12:16] = list(f"{name:>4s}")
    chars[16] = " "
    chars[30:38] = list(f"{xyz[0]:8.3f}")
    chars[38:46] = list(f"{xyz[1]:8.3f}")
    chars[46:54] = list(f"{xyz[2]:8.3f}")
    chars[54:60] = list(f"{1.00:6.2f}")
    chars[76:78] = list(f"{element:>2s}")
    return "".join(chars) + "\n"


def _full_phosphate_coordinates(
    o5: _PdbAtom,
    c5: _PdbAtom,
    c4: _PdbAtom,
) -> dict[str, tuple[float, float, float]]:
    # Phenix native DNA geometry restrains P-O5'-C5' to 120.90 degrees.
    # Use the local sugar frame to choose the otherwise free torsion rather
    # than extending C5'->O5' linearly or depending on global XYZ axes.
    toward_c5 = _unit(_sub(c5.xyz, o5.xyz), "5'-phosphate O5'-C5' axis")
    toward_c4 = _sub(c4.xyz, c5.xyz)
    sugar_radial = _sub(
        toward_c4,
        _scale(toward_c5, _dot(toward_c4, toward_c5)),
    )
    away_from_sugar = _scale(
        _unit(sugar_radial, "5'-phosphate local sugar frame"),
        -1.0,
    )

    o5_angle = math.radians(120.90)
    p_direction = _add(
        _scale(toward_c5, math.cos(o5_angle)),
        _scale(away_from_sugar, math.sin(o5_angle)),
    )
    p = _add(o5.xyz, _scale(p_direction, 1.593))

    axis = _unit(_sub(o5.xyz, p), "5'-phosphate O5'-P axis")

    # Orient the terminal oxygens from the molecular frame as well. OP3 is
    # initially placed on the side opposite the sugar; Phenix then has a
    # chemically sensible tetrahedral starting group to regularize.
    from_p_to_c4 = _sub(c4.xyz, p)
    projected_sugar = _sub(
        from_p_to_c4,
        _scale(axis, _dot(from_p_to_c4, axis)),
    )
    u = _scale(
        _unit(projected_sugar, "5'-phosphate tetrahedral local frame"),
        -1.0,
    )
    v = _unit(_cross(axis, u), "5'-phosphate tetrahedral local frame")

    cos_theta = -1.0 / 3.0
    sin_theta = math.sqrt(8.0 / 9.0)
    result = {"P": p}
    for name, length, phi in (
        ("OP3", 1.48, 0.0),
        ("OP1", 1.48, 2.0 * math.pi / 3.0),
        ("OP2", 1.48, 4.0 * math.pi / 3.0),
    ):
        radial = _add(_scale(u, math.cos(phi)), _scale(v, math.sin(phi)))
        direction = _add(_scale(axis, cos_theta), _scale(radial, sin_theta))
        result[name] = _add(p, _scale(direction, length))
    return result


def _missing_op3_coordinate(group: list[_PdbAtom], p: _PdbAtom) -> tuple[float, float, float]:
    neighbors = [_one(group, name, p.site) for name in ("O5'", "OP1", "OP2")]
    directions = [_unit(_sub(atom.xyz, p.xyz), f"{p.site} {atom.name}-P") for atom in neighbors]
    missing = _unit(
        tuple(-sum(vector[axis] for vector in directions) for axis in range(3)),
        f"{p.site} missing OP3 direction",
    )
    return _add(p.xyz, _scale(missing, 1.60))


def ensure_five_prime_phosphates(
    source: Path,
    destination: Path,
    sites: tuple[str, ...],
) -> dict[str, object]:
    """Ensure a complete P/OP1/OP2/OP3 5'-terminal group at requested sites.

    Existing complete groups are preserved.  A group containing P/OP1/OP2 but
    lacking OP3 is completed geometrically.  If no phosphate atoms are present,
    P/OP1/OP2/OP3 are seeded from the O5'-C5' bond with idealized tetrahedral
    starting geometry for later ReadySet/Phenix regularization.  Other partial
    states fail closed rather than guessing which chemistry the user intended.
    """
    requested = tuple(validate_site(site) for site in sites)
    if len(set(requested)) != len(requested):
        raise BackboneError("Duplicate 5'-phosphate site request")
    if source.resolve() == destination.resolve():
        raise BackboneError("Terminal-phosphate construction requires a separate output model")
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    atoms = _atoms(lines)
    groups: dict[str, list[_PdbAtom]] = {}
    for atom in atoms:
        groups.setdefault(atom.site, []).append(atom)
    missing_sites = set(requested) - set(groups)
    if missing_sites:
        raise BackboneError("Requested 5'-phosphate residue is absent: " + ", ".join(sorted(missing_sites)))
    max_serial = max((int(atom.line[6:11]) for atom in atoms if atom.line[6:11].strip().isdigit()), default=0)
    additions: dict[int, list[str]] = {}
    report: dict[str, object] = {
        "mode": "ensure-complete-5prime-phosphate-v1",
        "requested_sites": list(requested),
        "constructed": [],
        "completed": [],
        "preserved": [],
        "input_sha256": sha256(source.read_bytes()).hexdigest(),
    }
    serial = max_serial
    for site in requested:
        group = groups[site]
        o5 = _one(group, "O5'", site)
        c5 = _one(group, "C5'", site)
        c4 = _one(group, "C4'", site)
        present = {atom.name for atom in group if atom.name in {"P", "OP1", "OP2", "OP3"}}
        last_index = max(atom.index for atom in group)
        template = o5.line
        p = _one(group, "P", site) if "P" in present else None
        incoming = (
            [
                atom for atom in atoms
                if atom.site != site and atom.chain == p.chain and atom.name == "O3'"
                and math.dist(atom.xyz, p.xyz) <= 2.1
            ]
            if p is not None else []
        )
        if len(incoming) > 1:
            raise BackboneError(f"5'-phosphate {site}: multiple possible incoming O3'-P links")
        if incoming:
            raise BackboneError(
                f"5'-phosphate {site}: terminal phosphate request conflicts with an internal O3'-P link"
            )
        if present == {"P", "OP1", "OP2", "OP3"}:
            report["preserved"].append({"site": site, "atoms": sorted(present)})
            continue
        if present == {"P", "OP1", "OP2"}:
            assert p is not None
            serial += 1
            op3 = _new_atom(template, serial, "OP3", _missing_op3_coordinate(group, p), "O")
            additions.setdefault(last_index, []).append(op3)
            report["completed"].append({"site": site, "added": ["OP3"], "placement": "tetrahedral-from-existing-P"})
            continue
        if present:
            raise BackboneError(
                f"5'-phosphate {site}: partial phosphate atoms {sorted(present)} require manual review; "
                "automatic construction supports either no phosphate or P/OP1/OP2 missing only OP3"
            )
        coordinates = _full_phosphate_coordinates(o5, c5, c4)
        built = []
        for name in ("P", "OP1", "OP2", "OP3"):
            serial += 1
            built.append(_new_atom(template, serial, name, coordinates[name], "P" if name == "P" else "O"))
        additions.setdefault(last_index, []).extend(built)
        report["constructed"].append({
            "site": site,
            "added": ["P", "OP1", "OP2", "OP3"],
            "placement": "idealized-local-sugar-frame",
            "requires_downstream_geometry_review": True,
        })
    output: list[str] = []
    for index, line in enumerate(lines):
        output.append(line)
        output.extend(additions.get(index, ()))
    text = "".join(output)
    destination.write_text(text, encoding="utf-8")
    report["output_sha256"] = sha256(text.encode("utf-8")).hexdigest()
    return report


def backbone_review_record(
    *, sites: tuple[str, ...], model: Path, run: Path, reviewed: bool
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "USER_REVIEWED" if reviewed else "UNREVIEWED",
        "sites": list(sites),
        "model": artifact_reference(model, run),
        "model_sha256": sha256(model.read_bytes()).hexdigest(),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": "experimental-passthrough; NASolve did not validate custom backbone connectivity",
    }


def write_backbone_review(
    path: Path, *, sites: tuple[str, ...], model: Path, run: Path, reviewed: bool
) -> None:
    value = backbone_review_record(sites=sites, model=model, run=run, reviewed=reviewed)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = [
    "BackboneError",
    "ensure_five_prime_phosphates",
    "make_backbone_policy",
    "requested_backbone_policy",
    "validate_backbone_policy",
    "validate_backbone_sites",
    "validate_site",
    "write_backbone_review",
]
