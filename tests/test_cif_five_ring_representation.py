"""Source-authorized five-ring representation is not a new chemical structure."""
from copy import deepcopy

import pytest

from nasolve.cif_generation import inspect_component_generation
from tests.test_cif_aromatic_representation import add_angles
from tests.test_cif_stereochemistry_audit import write

POLICY = "cif-source-declared-neutral-five-membered-cn-aromatic-v1"
A, B = "_chem_comp_atom.", "_chem_comp_bond."


def pair(elements=("N", "N", "C", "N", "C")):
    # One pyrrolic nitrogen, two nonadjacent double bonds; every H explicit.
    ring = ["r" + str(i) for i in range(5)]
    attachments = [i for i, e in enumerate(elements) if i == 0 or e == "C"]
    names = ring + ["h" + str(i) for i in attachments]
    edges = list(zip(ring, ring[1:] + ring[:1])) + [(ring[i], "h" + str(i)) for i in attachments]
    v = {"data_": "comp_Q17", "_chem_comp.id": ["Q17"],
         A + "comp_id": ["Q17"] * len(names), A + "atom_id": names,
         A + "type_symbol": list(elements) + ["H"] * len(attachments),
         A + "charge": ["0"] * len(names), A + "pdbx_stereo_config": ["N"] * len(names),
         B + "comp_id": ["Q17"] * len(edges), B + "atom_id_1": [a for a, b in edges],
         B + "atom_id_2": [b for a, b in edges],
         B + "value_order": ["DOUB" if i in {1, 3} else "SING" for i in range(len(edges))],
         B + "pdbx_aromatic_flag": ["Y"] * 5 + ["N"] * len(attachments)}
    g = deepcopy(v)
    g[B + "type"] = ["aromatic"] * 5 + ["single"] * len(attachments)
    g.pop(B + "value_order"); g.pop(B + "pdbx_aromatic_flag")
    g[A + "type_energy"] = g[A + "type_symbol"][:]
    g[B + "value_dist"] = ["1.4"] * len(edges)
    g[B + "value_dist_esd"] = ["0.02"] * len(edges)
    add_angles(g)
    return v, g


def inspect(tmp_path, v, g, policy=POLICY):
    source, candidate = write(tmp_path / "source.cif", v), write(tmp_path / "candidate.cif", g)
    before = source.read_bytes(), candidate.read_bytes()
    result = inspect_component_generation(source, candidate, "Q17", bond_representation_policy=policy)
    assert before == (source.read_bytes(), candidate.read_bytes())
    return result


@pytest.mark.parametrize("elements", [("N", "N", "C", "N", "C"),
    ("N", "C", "N", "C", "C"), ("N", "N", "C", "C", "C"), ("N", "C", "C", "C", "C")])
@pytest.mark.parametrize("variant", ["plain", "renamed_reordered", "deuterated"])
def test_related_neutral_rings_are_explicit_opt_in(tmp_path, elements, variant):
    v, g = pair(elements)
    if variant == "deuterated":
        for d in (v, g): d[A + "type_symbol"][-1] = "D"
        g[A + "type_energy"][-1] = "D"
    if variant == "renamed_reordered":
        mapping = {n: "Z" + str(i) for i, n in enumerate(v[A + "atom_id"])}
        for d in (v, g):
            for k in d:
                if k.split(".")[-1].startswith("atom_id"): d[k] = [mapping.get(x, x) for x in d[k]]
                if k.startswith((A, B)): d[k] = list(reversed(d[k]))
    assert inspect(tmp_path, v, g, None)["status"] == "REJECTED"
    r = inspect(tmp_path, v, g)
    assert r["status"] == "CANDIDATE_REVIEW" and not r["automatic_adoption"]
    assert r["bond_representation"]["status"] == "SOURCE_DECLARED_EQUIVALENT"
    assert len(r["bond_representation"]["equivalent_rings"]) == 1
    assert not r["bond_representation"]["equivalent_fused_systems"]
    assert r["native_validation"] == "NOT_RUN"
    for old in ("cif-source-declared-neutral-purine-aromatic-v1", "cif-source-declared-neutral-6-oxo-purine-aromatic-v1"):
        assert inspect(tmp_path, v, g, old)["status"] == "REJECTED"


@pytest.mark.parametrize("defect", ["partial", "no_flags", "conflicting_flags", "candidate_flag", "charged_ring",
    "changed_charge", "missing_charge", "conflicting_charge", "changed_element", "changed_H", "changed_isotope",
    "ring_stereo", "bond_stereo", "exocyclic_double", "zero_donor", "adjacent_doubles", "extra_double",
    "unsupported_element", "chord", "new_bond", "outside_order"])
def test_source_aromatic_flag_does_not_authorize_chemical_changes(tmp_path, defect):
    v, g = pair()
    if defect == "partial": g[B + "type"][0] = "single"
    if defect == "no_flags": v.pop(B + "pdbx_aromatic_flag")
    if defect == "conflicting_flags": v[B + "aromatic"] = ["N"] * len(v[B + "comp_id"])
    if defect == "candidate_flag": g[B + "pdbx_aromatic_flag"] = ["N"] * len(g[B + "comp_id"])
    if defect == "charged_ring":
        for d in (v, g): d[A + "charge"][0] = "1"
    if defect == "changed_charge": g[A + "charge"][-1] = "1"
    if defect == "missing_charge": v[A + "charge"][0] = "?"
    if defect == "conflicting_charge": v[A + "pdbx_formal_charge"] = ["1"] + ["0"] * (len(v[A + "atom_id"]) - 1)
    if defect == "changed_element": g[A + "type_symbol"][0] = "C"
    if defect == "changed_H": g[B + "atom_id_1"][5] = "r1"; add_angles(g)
    if defect == "changed_isotope": g[A + "type_symbol"][-1] = "D"
    if defect == "ring_stereo": g[A + "pdbx_stereo_config"][0] = "R"
    if defect == "bond_stereo": v[B + "pdbx_stereo_config"] = ["E"] + ["N"] * (len(v[B + "comp_id"]) - 1)
    if defect == "exocyclic_double": v[B + "value_order"][5] = "DOUB"; g[B + "type"][5] = "double"
    if defect == "zero_donor":
        for d in (v, g): d[A + "type_symbol"][0] = "C"
    if defect == "adjacent_doubles": v[B + "value_order"][:5] = ["SING", "DOUB", "DOUB", "SING", "SING"]
    if defect == "extra_double": v[B + "value_order"][0] = "DOUB"
    if defect == "unsupported_element":
        for d in (v, g): d[A + "type_symbol"][0] = "O"
    if defect in {"chord", "new_bond"}:
        for d in ((v, g) if defect == "chord" else (g,)):
            for k in list(d):
                if k.startswith(B): d[k].append("Q17" if k.endswith("comp_id") else "r1" if k.endswith("atom_id_1") else "r4" if k.endswith("atom_id_2") else "1.4" if k.endswith("value_dist") else "0.02" if k.endswith("value_dist_esd") else "N" if k.endswith("pdbx_aromatic_flag") else "SING")
        add_angles(g)
    if defect == "outside_order": g[B + "type"][5] = "double"
    result = inspect(tmp_path, v, g)
    assert result["status"] == "REJECTED"
    assert result["bond_representation"]["status"] == "UNSUPPORTED_DIFFERENCE"


def test_packaged_dy_native_contract_preserves_rotatable_bridge(tmp_path):
    from importlib.resources import files
    from Bio.PDB.MMCIF2Dict import MMCIF2Dict
    from nasolve.cif_source_representation import generation_representation_contract
    source = files("nasolve").joinpath("data/chemical_references/DY.cif")
    contract = generation_representation_contract(source, "DY", POLICY)
    assert len(contract["allowed_systems"]) == 1
    edges = {frozenset(x) for x in contract["allowed_systems"][0]}
    assert len(edges) == 5 and frozenset(("C4", "N1T")) not in edges
    assert all(all(n.endswith("T") for n in e) for e in edges)
    original = MMCIF2Dict(str(source))
    assert original[B + "value_order"][7] == "SING"


@pytest.mark.parametrize('defect', ['none', 'partial', 'bridge', 'hydrogen', 'charge'])
def test_five_ring_native_contract_never_permits_partial_or_outside_changes(tmp_path, defect):
    from nasolve.cif_source_representation import generation_representation_contract, native_representation_check
    from tests.test_cif_source_representation import expected, snapshot
    v, _ = pair()
    for axis in 'xyz':
        v[A + 'pdbx_model_Cartn_' + axis + '_ideal'] = ['0.1'] * len(v[A + 'atom_id'])
    source = write(tmp_path / 'source.cif', v)
    e = expected(source); n = snapshot(e)
    contract = generation_representation_contract(source, 'Q17', POLICY)
    allowed = {tuple(edge) for edge in contract['allowed_systems'][0]}
    for row in n['bonds']:
        if tuple(row['atoms']) in allowed: row['native_order'] = 1.5
    if defect == 'partial':
        next(row for row in n['bonds'] if tuple(row['atoms']) in allowed)['native_order'] = 1
    if defect == 'bridge':
        next(row for row in n['bonds'] if tuple(row['atoms']) not in allowed)['native_order'] = 2
    if defect == 'hydrogen':
        next(row for row in n['atoms'] if row['element'] == 'H')['element'] = 'D'
    if defect == 'charge': n['atoms'][0]['native_atom_charge'] = 1
    result = native_representation_check(n, e, contract, coordinates=True, charges=True)
    assert (result['status'] == 'SOURCE_REPRESENTATION_PASS') is (defect == 'none')
    assert result['native_bond_order_editing'] == 'NOT_RUN'


def test_existing_owned_multiple_plane_reader_replays_new_policy_after_relocation(tmp_path, monkeypatch):
    import subprocess
    from nasolve.cif_source_representation import read_multiple_plane_candidate
    from tests.test_cif_source_representation import fake_generation
    def source_pair(directory):
        v, g = pair()
        for d in (v, g):
            for i, axis in enumerate('xyz'):
                d[A + 'pdbx_model_Cartn_' + axis + '_ideal'] = [str((n + 1) * (i + 1) / 10) for n in range(len(d[A + 'atom_id']))]
        return write(directory / 'source.cif', v), write(directory / 'candidate.cif', g)
    original = tmp_path / 'original'; original.mkdir()
    out, receipt = fake_generation(original, pair_factory=source_pair, policy=POLICY,
        ring_atoms=['r0', 'r1', 'r2', 'r3', 'r4'], aromatic_count=5, multiple_planes=True, request_owned=True)
    assert receipt['status'] == 'CANDIDATE_REVIEW'
    moved = tmp_path / 'relocated'
    original.rename(moved)
    assert not original.exists()
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Cold replay must not execute native code'))
    replay = read_multiple_plane_candidate(moved / out.relative_to(original))
    assert replay == receipt
