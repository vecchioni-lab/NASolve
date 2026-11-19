"""Source-supported native parent-chi matching for ordinary DNA construction.

The existing DNA graph boundary selects the operation; a component label does
not. Matching establishes only initial parent conformation, not chemical or
achieved-geometry approval. Historical scripts omit this opt-in operation.
"""
from hashlib import sha256
from pathlib import Path

from .cif_linked_preparation import component_values
from .cif_stereochemistry_audit import _graph
from .postmr_restoration import source_graph_fragment

POLICY_ID = "postmr-source-graph-parent-chi-v1"
MATCH_TOLERANCE_DEGREES = 0.1
_PARENT_ROLES = {
    "DA": ("N9", "C4", "C8"), "DG": ("N9", "C4", "C8"),
    "DC": ("N1", "C2", "C6"), "DT": ("N1", "C2", "C6"),
}


def parent_conformation_plan(dictionary: Path, component: str, parent_code: str) -> dict:
    """Select a shared canonical chi frame without guessing modified backbones."""
    result = {"policy_id": POLICY_ID, "status": "UNASSESSED", "component": component}
    before = None
    try:
        if parent_code not in _PARENT_ROLES:
            raise ValueError("Parent is outside the supported canonical DNA frame")
        before = Path(dictionary).read_bytes()
        graph = source_graph_fragment(dictionary, component)
        values = component_values(dictionary, component)
        elements, _, _, neighbors = _graph(values)
        anchor, first, second = _PARENT_ROLES[parent_code]
        if (graph["attachment_atom"] != anchor or elements.get(anchor) != "N"
                or any(elements.get(n) != "C" for n in (first, second))
                or neighbors[anchor] != {"C1'", first, second}):
            raise ValueError("Source lacks the shared canonical N-glycosidic chi frame")
    except (OSError, ValueError) as exc:
        result["reason"] = str(exc)
        return result
    finally:
        if before is not None and Path(dictionary).read_bytes() != before:
            raise ValueError("Source changed during conformation planning")
    if sha256(before).hexdigest() != graph["source_sha256"]:
        raise ValueError("Source changed during conformation planning")
    result.update(status="MATCH_PARENT_CHI", parent=parent_code,
                  source_sha256=graph["source_sha256"],
                  atoms=["O4'", "C1'", anchor, first],
                  match_tolerance_degrees=MATCH_TOLERANCE_DEGREES)
    return result


def native_helpers() -> list[str]:
    """Emit helpers into the standalone Coot script, with no NASolve import."""
    return [
        "import math",
        "def nasolve_chi(molecule, chain, residue, names):",
        "    reader = getattr(coot, 'get_torsion_py', None)",
        "    if not callable(reader):",
        "        raise RuntimeError('Coot lacks parent-conformation torsion readback')",
        "    specs = [[chain, residue, '', ' ' + name.ljust(3), ''] for name in names]",
        "    value = reader(molecule, *specs)",
        "    if type(value) not in (int, float) or not math.isfinite(value):",
        "        raise RuntimeError('Coot could not measure the declared parent chi frame')",
        "    return float(value)",
        "def nasolve_check_chi(molecule, expected, names, site, stage, tolerance):",
        "    observed = nasolve_chi(molecule, 'A', 1, names)",
        "    difference = abs((observed - expected + 180.0) % 360.0 - 180.0)",
        "    print('NASOLVE_PARENT_CHI', site, stage, expected, observed, difference)",
        "    if difference > tolerance:",
        "        raise RuntimeError('Coot did not preserve the parent chi at ' + site)",
    ]


def native_match_lines(plan: dict, site: str, chain: str, residue: int) -> list[str]:
    if plan["status"] != "MATCH_PARENT_CHI":
        return [f"print('NASOLVE_PARENT_CHI_UNASSESSED', {site!r}, {plan['reason']!r})"]
    return [
        f"print('NASOLVE_PARENT_CHI_PLAN', {site!r}, {plan!r})",
        "chi_matcher = getattr(coot, 'match_ligand_torsions', None)",
        "if not callable(chi_matcher):",
        "    raise RuntimeError('Coot lacks native parent-conformation matching')",
        f"chi_atoms = {plan['atoms']!r}",
        f"parent_chi = nasolve_chi(imol, {chain!r}, {residue}, chi_atoms)",
        "initial_chi = nasolve_chi(ligand_imol, 'A', 1, chi_atoms)",
        f"print('NASOLVE_INITIAL_CHI', {site!r}, parent_chi, initial_chi)",
        f"chi_matcher(ligand_imol, imol, {chain!r}, {residue})",
        f"nasolve_check_chi(ligand_imol, parent_chi, chi_atoms, {site!r}, 'matched', {plan['match_tolerance_degrees']!r})",
    ]


def native_overlap_check_lines(plan: dict, site: str) -> list[str]:
    if plan["status"] != "MATCH_PARENT_CHI":
        return []
    return [
        f"nasolve_check_chi(ligand_imol, parent_chi, chi_atoms, {site!r}, 'overlapped', {plan['match_tolerance_degrees']!r})",
    ]
