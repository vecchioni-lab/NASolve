"""A declared ordinary phosphate can borrow only its own matched native link."""
from copy import deepcopy
from types import SimpleNamespace

import pytest


def inspection():
    from nasolve.topostitch_recipe import recipe_digest
    donors = {"C3'", "C4'", "O3'"}
    bond = ("O3' P", {"distance_ideal": 1.593, "weight": 2500., "symmetry_operation": None})
    terms = []
    for labels, parameters in (bond, *[(s, {"angle_ideal": 111., "weight": .09}) for s in
            ["C3' O3' P", "O3' P OP1", "O3' P OP2", "O3' P O5'"]], *[(s, {"angle_ideal": -124.,
             "weight": .008, "periodicity": 2, "alt_angle_ideals": None}) for s in
            ["C4' C3' O3' P", "C3' O3' P O5'", "O3' P O5' C5'"]]):
        atoms = [["o3-site" if n in donors else "phosphate-site", n] for n in labels.split()]
        terms.append(dict(kind={2:"bond_simple", 3:"angle", 4:"dihedral"}[len(atoms)], atoms=atoms, parameters=parameters))
    group = dict(terms=terms, terms_sha256=recipe_digest(terms), links=[["K:3","L:9"], ["A:11","B:2"]])
    return dict(policy_id="phosphate-image-observation-v1", model_sha256="a"*64,
        cell=[90,90,80,90,90,120], space_group="P 3",
        o3=["X:8","RX9","O3'"], phosphate=["Y:14","Q2","P"], o3_image="-x+y,-x,z+1",
        phosphate_atoms={s: (None if s == "OP3" else {"element": s[0], "occupancy": 1.})
                         for s in ["P","OP1","OP2","OP3","O5'"]},
        registered_continuation=dict(measurement_status="MEASURED",source={"coordinate_site":"X:8","atom":"O3'"},
            target={"coordinate_site":"Y:14","atom":"P"}, oxygen_operator_xyz="-x+y,-x,z+1"),
        native_reference_links=dict(status="AGREEING_REFERENCES", groups=[group], phenix_version="2.2.1-6174"))


def test_exact_oxygen_image_and_reference_numbers_in_the_emitted_bond():
    from nasolve.cif_phosphate_restraints import phosphate_bond_phil
    row = inspection()
    before = deepcopy(row)
    text = phosphate_bond_phil(row)
    assert "atom_selection_1 = chain Y and resseq 14 and resname Q2 and name P" in text
    assert "atom_selection_2 = chain X and resseq 8 and resname RX9 and name O3'" in text
    assert "symmetry_operation = -x+y,-x,z+1" in text
    assert "distance_ideal = 1.593" in text and "sigma = 0.02" in text
    assert text.count("action = add") == 1 and row == before


@pytest.mark.parametrize("change", ["nearest", "lost image", "zero", "OP3", "missing term", "changed bytes",
                                    "repeated source", "wrong torsion", "edited weight", "unsafe site"])
def test_an_incomplete_or_unbound_link_cannot_supply_a_bond(change):
    from nasolve.cif_phosphate_restraints import phosphate_bond_phil
    from nasolve.topostitch_recipe import recipe_digest
    r = inspection()
    g = r["native_reference_links"]["groups"][0]
    if change == "nearest":
        del r["registered_continuation"]
    elif change == "lost image":
        r["o3_image"] = "x,y,z"
    elif change == "zero":
        r["phosphate_atoms"]["OP2"]["occupancy"] = 0.
    elif change == "OP3":
        r["phosphate_atoms"]["OP3"] = {"element": "O", "occupancy": 1.}
    elif change == "missing term":
        g["terms"].pop()
    elif change == "changed bytes":
        g["terms_sha256"] = "b"*64
    elif change == "repeated source":
        g["links"][1] = g["links"][0]
    elif change == "wrong torsion":
        g["terms"][-1]["atoms"][-1][1] = "OP1"
    elif change == "edited weight":
        g["terms"][2]["parameters"]["weight"] = -1.
    else:
        r["phosphate"][0] = r["registered_continuation"]["target"]["coordinate_site"] = "Y:14 or all"
    if change != "changed bytes":
        g["terms_sha256"] = recipe_digest(g["terms"])
    with pytest.raises(ValueError):
        phosphate_bond_phil(r)


def test_live_reference_checks_fields_missing_from_the_standard_capture():
    from nasolve.cif_phosphate_restraints import ordinary_proxy_parameters
    term = inspection()["native_reference_links"]["groups"][0]["terms"][-1]
    value = dict(term["parameters"], origin_id=0, slack=0., limit=-1., top_out=False, sym_ops=None)
    assert ordinary_proxy_parameters(term, SimpleNamespace(**value))["limit"] == -1.
    for change in ({"slack": .2}, {"top_out": True}, {"limit": 15.}, {"alt_angle_ideals": [30.]},
                   {"angle_ideal": -123.}, {"periodicity": 1}, {"origin_id": 2},
                   {"sym_ops": [SimpleNamespace(is_unit_mx=lambda: False)]}):
        with pytest.raises(ValueError):
            ordinary_proxy_parameters(term, SimpleNamespace(**(value | change)))
    del value["slack"]
    with pytest.raises(ValueError):
        ordinary_proxy_parameters(term, SimpleNamespace(**value))


def test_cryst1_precision_accepts_the_mtz_floats_and_preserves_the_measured_cell():
    from nasolve.cif_phosphate_restraints import _cryst1_cell
    stored = [106.218,106.218,91.636,90.,90.,120.]
    native = [106.21800231933591,106.21800231933591,91.63600158691406,90.,90.,119.99999999999999]
    assert _cryst1_cell(native) == _cryst1_cell(stored)
    assert _cryst1_cell([106.2186, *native[1:]]) != _cryst1_cell(stored)
    assert _cryst1_cell([*native[:5], 119.994]) != _cryst1_cell(stored)
