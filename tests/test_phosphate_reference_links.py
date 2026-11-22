"""Reference link chemistry comes from intact links with matching local definitions."""
from copy import deepcopy

import pytest


def capture():
    families = ("bond_simple", "bond_asu", "angle", "dihedral", "const_dihedral",
                "chirality", "planarity", "parallelity")
    details = {kind: [] for kind in families}
    mappings, atoms = [], []
    for number in range(1, 7):
        # 1→2 and 3→4 are intact links. The candidate is 5→6.
        code = "X93" if number % 2 else "Y42"
        names = ("C3'", "O3'") if number % 2 else ("P", "OP1")
        identity = dict(altloc="", icode="", model_id="", chain_id="A", resseq=str(number), resname=code)
        definition = dict(atoms=[{"atom_id": n} for n in names], bonds=[], angles=[], torsions=[],
                          chirality=[], plane_atoms=[])
        mappings.append(dict(site=f"A:{number}", resname=code, literal_identity=dict(identity, status="RECORDED"),
                             chem_mod_ids=dict(status="RECORDED", ids=[]),
                             metadata=dict(status="RECORDED", effective_definition=definition)))
        for name in names:
            atoms.append(dict(i_seq=len(atoms), atom_id=name, label=f"{number}/{name}", identity=identity,
                              element=name[0]))
    def term(kind, indices, **params):
        details[kind].append(dict(i_seqs=indices, atoms=[atoms[i]["label"] for i in indices], origin_id=0, **params))
    for i in (0, 4):
        term("bond_simple", [i+1, i+2], distance_ideal=1.61, weight=1000., symmetry_operation=None)
        term("angle", [i+1, i+2, i+3], angle_ideal=108., weight=.1)
        term("dihedral", [i, i+1, i+2, i+3], angle_ideal=170., periodicity=3, weight=.002)
    return dict(atoms=atoms, monomer_mappings=dict(status="RECORDED", rows=mappings), geometry=dict(
        proxy_details=details, proxy_counts={f:len(rows) for f,rows in details.items()},
        proxy_count_status={f:"RECORDED" for f in families if f not in ("bond_simple","bond_asu")}))


def read(native):
    from nasolve.cif_phosphate_reference import reference_link_terms
    return reference_link_terms(native, phosphate="A:6", o3="A:5")


def test_two_intact_references_retain_the_angles_and_signed_torsion():
    native = capture()
    before = deepcopy(native)
    report = read(native)
    assert report["status"] == "AGREEING_REFERENCES"
    group, = report["groups"]
    assert group["links"] == [["A:1","A:2"], ["A:3","A:4"]]
    assert sorted(t["kind"] for t in group["terms"]) == ["angle","bond_simple","dihedral"]
    torsion, = [t for t in group["terms"] if t["kind"] == "dihedral"]
    assert torsion["parameters"]["periodicity"] == 3 and torsion["parameters"]["angle_ideal"] == 170
    assert report["automatic_adoption"] is False and native == before


def test_incompatible_chemistry_and_competing_targets_stay_distinct():
    native = capture()
    native["geometry"]["proxy_details"]["angle"][1]["angle_ideal"] = 107
    assert read(native)["status"] == "DIFFERENT_REFERENCES"
    native["monomer_mappings"]["rows"][3]["metadata"]["effective_definition"]["atoms"].append({"atom_id":"OP3"})
    report = read(native)
    assert report["status"] == "ONE_REFERENCE" and report["groups"][0]["links"] == [["A:1","A:2"]]
    native["monomer_mappings"]["rows"][1]["chem_mod_ids"]["ids"].append("terminal")
    assert read(native)["status"] == "NO_MATCHING_REFERENCE"


def test_image_bond_and_user_distance_cannot_nominate_an_intact_source():
    native = capture()
    first, second = native["geometry"]["proxy_details"]["bond_simple"]
    first["symmetry_operation"] = "x+1,y,z"
    second["origin_id"] = 4
    assert read(native)["status"] == "NO_MATCHING_REFERENCE"


def test_incomplete_family_and_misbound_atom_label_fail():
    native = capture()
    native["geometry"]["proxy_count_status"]["dihedral"] = "UNSUPPORTED"
    with pytest.raises(ValueError, match="famil"):
        read(native)
    native = capture()
    native["geometry"]["proxy_details"]["angle"][0]["atoms"].reverse()
    with pytest.raises(ValueError, match="labels"):
        read(native)


def test_additional_crosslink_and_missing_torsion_parameter_remain_visible():
    native = capture()
    details = native["geometry"]["proxy_details"]
    details["bond_asu"].append(dict(details["bond_simple"][0], symmetry_operation="x,y+1,z"))
    native["geometry"]["proxy_counts"]["bond_asu"] = 1
    result = read(native)
    assert result["status"] == "ONE_REFERENCE" and result["excluded_multiple_bonds"] == [["A:1","A:2"]]
    del details["dihedral"][1]["periodicity"]
    with pytest.raises(ValueError, match="periodicity"):
        read(native)
