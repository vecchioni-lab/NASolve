"""Source-declared representation checks, not aromaticity perception or native evidence."""
from itertools import combinations

import pytest

from nasolve.cif_generation import inspect_component_generation
from nasolve.ligand_profiles import _emit


def values(code="Q11", *, numerical=False, ring_size=6):
    ring = ["C1", "C2", "N3", "C4", "C5", "C6"][:ring_size]
    names = ring + ["O5'", "P", "OP1", "OP2", "OP3", "keepH", "leaveH", "baseH"]
    elements = ["N" if atom == "N3" else "C" for atom in ring] + ["O", "P", "O", "O", "O", "H", "H", "H"]
    bonds = list(zip(ring, ring[1:] + ring[:1])) + [
        (ring[0], "O5'"), ("O5'", "P"), ("P", "OP1"), ("P", "OP2"),
        ("P", "OP3"), ("OP2", "keepH"), ("OP3", "leaveH"), (ring[-1], "baseH")]
    orders = ["SING" if i % 2 == 0 else "DOUB" for i in range(ring_size)] + [
        "SING", "SING", "DOUB", "SING", "SING", "SING", "SING", "SING"]
    result = {
        "data_": "comp_" + code, "_chem_comp.id": [code],
        "_chem_comp_atom.comp_id": [code] * len(names),
        "_chem_comp_atom.atom_id": names, "_chem_comp_atom.type_symbol": elements,
        "_chem_comp_atom.charge": ["0"] * len(names),
        "_chem_comp_bond.comp_id": [code] * len(bonds),
        "_chem_comp_bond.atom_id_1": [a for a, _ in bonds],
        "_chem_comp_bond.atom_id_2": [b for _, b in bonds],
        "_chem_comp_bond.value_order": orders,
        "_chem_comp_bond.pdbx_aromatic_flag": ["Y"] * ring_size + ["N"] * 8,
    }
    if numerical:
        result["_chem_comp_atom.type_energy"] = elements[:]
        result["_chem_comp_bond.value_dist"] = ["1.4"] * len(bonds)
        result["_chem_comp_bond.value_dist_esd"] = ["0.02"] * len(bonds)
        add_angles(result)
    return result


def add_angles(result):
    code = result["_chem_comp.id"][0]
    bonds = list(zip(result["_chem_comp_bond.atom_id_1"], result["_chem_comp_bond.atom_id_2"]))
    angles = []
    for center in result["_chem_comp_atom.atom_id"]:
        neighbors = [b if a == center else a for a, b in bonds if center in (a, b)]
        angles.extend((a, center, b) for a, b in combinations(neighbors, 2))
    result.update({
        "_chem_comp_angle.comp_id": [code] * len(angles),
        "_chem_comp_angle.atom_id_1": [a for a, _, _ in angles],
        "_chem_comp_angle.atom_id_2": [b for _, b, _ in angles],
        "_chem_comp_angle.atom_id_3": [c for _, _, c in angles],
        "_chem_comp_angle.value_angle": ["120"] * len(angles),
        "_chem_comp_angle.value_angle_esd": ["2"] * len(angles),
    })


def pair(code="Q11", *, ring_size=6):
    source = values(code, ring_size=ring_size)
    generated = values(code, numerical=True, ring_size=ring_size)
    generated["_chem_comp_bond.type"] = ["aromatic"] * ring_size + [
        "double" if order == "DOUB" else "single"
        for order in generated.pop("_chem_comp_bond.value_order")[ring_size:]]
    generated.pop("_chem_comp_bond.pdbx_aromatic_flag")
    return source, generated


def inspect(tmp_path, source, generated):
    paths = tmp_path / "source.cif", tmp_path / "candidate.cif"
    for path, dictionary in zip(paths, (source, generated)):
        path.write_text(_emit(dictionary), encoding="utf-8")
    before = [path.read_bytes() for path in paths]
    receipt = inspect_component_generation(*paths, source["_chem_comp.id"][0])
    assert [path.read_bytes() for path in paths] == before
    return receipt


@pytest.mark.parametrize("code", ["Q11", "X99"])
def test_complete_source_declared_six_ring_is_representation_evidence(tmp_path, code):
    source, generated = pair(code)
    receipt = inspect(tmp_path, source, generated)
    assert receipt["status"] == "CANDIDATE_REVIEW"
    assert receipt["rejection_reasons"] == []
    assert receipt["bond_representation"]["status"] == "SOURCE_DECLARED_EQUIVALENT"
    assert len(receipt["bond_representation"]["equivalent_rings"]) == 1
    assert len(receipt["bond_representation"]["equivalent_rings"][0]["bonds"]) == 6
    assert any(row["field"] == "bond_orders" for row in receipt["chemical_changes"])
    assert any(row["field"] == "bond_orders" for row in receipt["comparison"]["differences"])
    assert receipt["automatic_adoption"] is False
    assert receipt["native_validation"] == "NOT_RUN"


@pytest.mark.parametrize("defect", [
    "missing-source-flags", "source-nonaromatic", "conflicting-source-flags",
    "candidate-nonaromatic", "partial-conversion", "not-alternating",
    "nonaromatic-order-change", "exocyclic-double", "fused-ring", "unsupported-element",
    "charged-ring", "missing-ring-charge", "explicit-ring-stereo", "outside-ring-change",
])
def test_unproven_bond_changes_remain_rejected(tmp_path, defect):
    source, generated = pair()
    if defect == "missing-source-flags":
        source.pop("_chem_comp_bond.pdbx_aromatic_flag")
    elif defect == "source-nonaromatic":
        source["_chem_comp_bond.pdbx_aromatic_flag"][0] = "N"
    elif defect == "conflicting-source-flags":
        source["_chem_comp_bond.aromatic"] = ["N"] * 14
    elif defect == "candidate-nonaromatic":
        generated["_chem_comp_bond.pdbx_aromatic_flag"] = ["N"] * 14
    elif defect == "partial-conversion":
        generated["_chem_comp_bond.type"][0] = "single"
    elif defect == "not-alternating":
        source["_chem_comp_bond.value_order"][0] = "DOUB"
    elif defect == "nonaromatic-order-change":
        generated["_chem_comp_bond.type"][:6] = ["double"] * 6
    elif defect == "exocyclic-double":
        source["_chem_comp_bond.value_order"][6] = "DOUB"
        generated["_chem_comp_bond.type"][6] = "double"
    elif defect == "fused-ring":
        # A chord adds a second cycle; its unchanged order is not a bridge.
        for dictionary in (source, generated):
            dictionary["_chem_comp_bond.comp_id"].append("Q11")
            dictionary["_chem_comp_bond.atom_id_1"].append("C1")
            dictionary["_chem_comp_bond.atom_id_2"].append("C4")
        source["_chem_comp_bond.value_order"].append("SING")
        source["_chem_comp_bond.pdbx_aromatic_flag"].append("N")
        generated["_chem_comp_bond.type"].append("single")
        generated["_chem_comp_bond.value_dist"].append("1.4")
        generated["_chem_comp_bond.value_dist_esd"].append("0.02")
        add_angles(generated)
    elif defect == "unsupported-element":
        for dictionary in (source, generated):
            dictionary["_chem_comp_atom.type_symbol"][2] = "S"
        generated["_chem_comp_atom.type_energy"][2] = "S"
    elif defect == "charged-ring":
        for dictionary in (source, generated):
            dictionary["_chem_comp_atom.charge"][0] = "1"
    elif defect == "missing-ring-charge":
        generated["_chem_comp_atom.charge"][0] = "?"
    elif defect == "explicit-ring-stereo":
        source["_chem_comp_bond.pdbx_stereo_config"] = ["E"] + ["N"] * 13
    elif defect == "outside-ring-change":
        generated["_chem_comp_bond.type"][8] = "single"
    receipt = inspect(tmp_path, source, generated)
    assert receipt["status"] == "REJECTED"
    assert "generated-atom-bond-or-hydrogen-identity-changed" in receipt["rejection_reasons"]


def test_other_ring_sizes_require_separate_support(tmp_path):
    source, generated = pair(ring_size=5)
    receipt = inspect(tmp_path, source, generated)
    assert receipt["status"] == "REJECTED"


@pytest.mark.parametrize("defect", ["op2-hydrogen", "formal-charge", "numerical-target", "ring-atom"])
def test_equivalent_ring_does_not_hide_independent_defects(tmp_path, defect):
    source, generated = pair()
    if defect == "op2-hydrogen":
        generated["_chem_comp_bond.atom_id_1"][11] = "OP1"
        add_angles(generated)
    elif defect == "formal-charge":
        generated["_chem_comp_atom.charge"][7] = "1"
    elif defect == "numerical-target":
        generated["_chem_comp_bond.value_dist"][0] = "0"
    elif defect == "ring-atom":
        generated["_chem_comp_atom.type_symbol"][0] = "N"
        generated["_chem_comp_atom.type_energy"][0] = "N"
    receipt = inspect(tmp_path, source, generated)
    assert receipt["status"] == "REJECTED"
    assert receipt["rejection_reasons"]
    assert receipt["automatic_adoption"] is False


def test_exact_orders_do_not_need_aromatic_normalization(tmp_path):
    source = values()
    generated = values(numerical=True)
    receipt = inspect(tmp_path, source, generated)
    assert receipt["status"] == "CANDIDATE_REVIEW"
    assert receipt["bond_representation"]["status"] == "EXACT"
    assert receipt["bond_representation"]["equivalent_rings"] == []


def test_source_only_inspection_keeps_representation_unassessed(tmp_path):
    path = tmp_path / "source.cif"
    path.write_text(_emit(values()), encoding="utf-8")
    receipt = inspect_component_generation(path, None, "Q11")
    assert receipt["status"] == "SOURCE_REVIEW"
    assert receipt["bond_representation"]["status"] == "NOT_RUN"
