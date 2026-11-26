"""Match a recorded RNA geometry adjustment to its explicit numerical table."""
from copy import deepcopy

import pytest


def _example():
    values = {"data_":"comp_TST", "_chem_comp.id":["TST"],
              "_chem_comp_plane_atom.atom_id":["X"]}
    table = {"data_":"mod_rna2p"}
    for category, atoms, field, start, end in (
        ("bond", ("AA","BB"), "value_dist", "1.51", "1.53"),
        ("angle", ("AA","BB","CC"), "value_angle", "110", "112"),
        ("tor", ("AA","BB","CC","DD"), "value_angle", "120", "117"),
    ):
        original, mod = "_chem_comp_"+category+".", "_chem_mod_"+category+"."
        for i, name in enumerate(atoms, 1):
            values[original+f"atom_id_{i}"]=[name]
            table[mod+f"atom_id_{i}"]=[name]
        values[original+field]=[start]
        values[original+field+"_esd"]=["0.03" if category=="bond" else "3"]
        table[mod+"mod_id"]=["rna2p"]
        table[mod+"function"]=["change"]
        table[mod+"new_"+field]=[end]
        table[mod+"new_"+field+"_esd"]=["0.02" if category=="bond" else "2"]
    values["_chem_comp_bond.type"]=["SINGLE"]
    table["_chem_mod_bond.new_type"]=["coval"]
    values["_chem_comp_tor.id"]=["original"]
    values["_chem_comp_tor.period"]=["3"]
    table["_chem_mod_tor.id"]=["library"]
    table["_chem_mod_tor.new_period"]=["1"]
    return values, table


def test_only_present_geometry_changes_and_original_orders_stay_available():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values, table = _example()
    original=deepcopy(values)
    projected, counts = project_pucker_targets(values,table)
    assert values==original
    assert projected["_chem_comp_bond.type"]==["coval"]
    assert projected["_chem_comp_tor.period"]==["1"]
    assert projected["_chem_comp_tor.id"]==["original"]
    assert projected["_chem_comp_plane_atom.atom_id"]==["X"]
    assert counts=={"bonds":1,"angles":1,"torsions":1}


@pytest.mark.parametrize("column,value", [
    ("_chem_mod_bond.function","delete"),("_chem_mod_bond.new_type","AROM"),
    ("_chem_mod_angle.new_value_angle","181"),("_chem_mod_tor.new_period","1.5"),
    ("_chem_mod_bond.new_value_dist","nan"),("_chem_mod_tor.new_value_angle_esd","0"),
    ("_chem_mod_angle.mod_id","rna3p"),("_chem_mod_atom.function","add"),
    ("_chem_mod_bond.new_value_dist_neutron","1.50")])
def test_unknown_or_nonphysical_adjustment_is_unexplained(column,value):
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    table[column]=[value]
    with pytest.raises(ValueError):
        project_pucker_targets(values,table)


def test_coval_is_never_a_global_alias_for_single():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    values["_chem_comp_bond.type"]=["AROM"]
    with pytest.raises(ValueError,match="single"):
        project_pucker_targets(values,table)
    values["_chem_comp_bond.type"]=["single"]
    values["_chem_comp_bond.value_order"]=["DOUB"]
    with pytest.raises(ValueError,match="single"):
        project_pucker_targets(values,table)


def test_bond_and_angle_match_both_directions_but_torsion_order_is_literal():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    for category,degree in (("bond",2),("angle",3),("tor",4)):
        cols=["_chem_mod_"+category+".atom_id_"+str(i) for i in range(1,degree+1)]
        for key,rev in zip(cols,[table[c] for c in reversed(cols)]):
            table[key]=rev
    p,counts=project_pucker_targets(values,table)
    assert counts=={"bonds":1,"angles":1,"torsions":0}
    assert p["_chem_comp_tor.period"]==["3"]


def test_duplicate_modifier_keys_are_refused():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    for k in table:
        if k.startswith("_chem_mod_bond."):
            table[k] *= 2
    with pytest.raises(ValueError,match="uplicate"):
        project_pucker_targets(values,table)


@pytest.mark.parametrize("fault", ["none","unexplained-bond","plane-weight","chirality-sign","extra-order"])
def test_adjusted_read_keeps_the_other_native_requirements(tmp_path, fault):
    from nasolve.cif_candidate_usability import _check_native_targets, qualify_candidate_native
    from nasolve.cif_rna_pucker import project_pucker_targets
    from nasolve.cif_stereochemistry_audit import _values
    from tests.test_cif_candidate_usability import native_case
    source,candidate,model,native=native_case(tmp_path)
    values=_values(candidate,"Q17")
    _,table=_example()
    bond="_chem_mod_bond."
    left,right=values["_chem_comp_bond.atom_id_1"][0],values["_chem_comp_bond.atom_id_2"][0]
    table[bond+"atom_id_1"],table[bond+"atom_id_2"]=[left],[right]
    projected,_=project_pucker_targets(values,table)
    definition=native["monomer_mappings"]["rows"][0]["metadata"]["effective_definition"]
    bs=definition["bonds"][0]
    bs.update(type="coval",value_dist=1.53,value_dist_esd=.02)
    live=native["geometry"]["proxy_details"]
    live["bond_simple"][0].update(distance_ideal=1.53,weight=2500.)
    if fault=="unexplained-bond":
        live["bond_simple"][1]["distance_ideal"]+=.1
    if fault=="plane-weight":
        live["planarity"][0]["weights"][0]+=1
    if fault=="chirality-sign":
        live["chirality"][0]["volume_ideal"]*=-1
    if fault=="extra-order":
        definition["bonds"][1]["type"]="coval"
    strict=qualify_candidate_native(source,candidate,model,"Q17",native)
    adjusted=_check_native_targets(source,candidate,model,"Q17",native,
        bond_representation_policy=None,projected=projected)
    assert not strict["native_usable"]
    assert adjusted["native_usable"] is (fault=="none")


def test_cli_pucker_replay_keeps_qualification_unchanged(tmp_path, monkeypatch, capsys):
    from nasolve.cli import main
    from nasolve import cli, cif_rna_pucker
    result={"status":"ADJUSTED_TARGETS_EXPLAINED","component":"ZZ8","modifier":"rna2p",
            "seeds":[],"matched_rows":{"bonds":2,"angles":3,"torsions":1},"qualification_unchanged":True}
    monkeypatch.setattr(cli,"discover_phenix",lambda *a,**k: object())
    monkeypatch.setattr(cif_rna_pucker,"review_pucker_adjustment",lambda directory, installation:result)
    assert main(["cif-doctor","explain-pucker",str(tmp_path)])==0
    assert "Matched rows for bonds (2), angles (3) and torsions (1)" in capsys.readouterr().out
    assert list(tmp_path.iterdir())==[]
