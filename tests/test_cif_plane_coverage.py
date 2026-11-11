"""Coverage is graph-selected and explicitly narrower than chemical approval."""
from copy import deepcopy
from pathlib import Path

import pytest

from nasolve.ligand_profiles import _emit


def values(code="XYZ"):
    a,b="_chem_comp_atom.","_chem_comp_bond."
    return {"data_":"comp_"+code,"_chem_comp.id":[code],
            a+"comp_id":[code]*4,a+"atom_id":["C","O","N","R"],
            a+"type_symbol":["C","O","N","C"],a+"charge":["0"]*4,
            a+"pdbx_stereo_config":["N"]*4,
            a+"x":["0","1","-.5","-.5"],a+"y":["0","0","1","-1"],a+"z":["0"]*4,
            b+"comp_id":[code]*3,b+"atom_id_1":["C"]*3,b+"atom_id_2":["O","N","R"],
            b+"value_order":["DOUB","SING","SING"]}


def plane(v, members, name="plane1", sigma="0.02"):
    p="_chem_comp_plane_atom."
    for key, entries in [("comp_id",[v["_chem_comp.id"][0]]*len(members)),
                         ("plane_id",[name]*len(members)),("atom_id",members),
                         ("dist_esd",[sigma]*len(members))]:
        v.setdefault(p+key,[]).extend(entries)


def write(tmp_path, v, filename):
    p=tmp_path/filename;p.write_text(_emit(v));return p


def audit(tmp_path, source, dictionary=None):
    from nasolve.cif_plane_coverage import audit_trigonal_plane_coverage
    s=write(tmp_path,source,"source.cif")
    d=write(tmp_path,dictionary if dictionary is not None else source,"dictionary.cif")
    before=[(p.read_bytes(),p.stat().st_mtime_ns) for p in (s,d)]
    r=audit_trigonal_plane_coverage(s,d,source["_chem_comp.id"][0])
    assert [(p.read_bytes(),p.stat().st_mtime_ns) for p in (s,d)] == before
    assert r==audit_trigonal_plane_coverage(s,d,source["_chem_comp.id"][0])
    return r


@pytest.mark.parametrize("code",["PDU","ZZZ"])
def test_missing_exocyclic_member_is_selected_without_component_name_rule(tmp_path,code):
    s=values(code);d=deepcopy(s);plane(d,["C","O","N"])
    r=audit(tmp_path,s,d)
    assert r["status"]=="REVIEW" and r["missing_explicit_planes"]==["C"]
    c=r["centres"][0]
    assert c["partial_planes"]==[dict(plane="plane1",shared=["C","N","O"],missing=["R"],existing_members=["C","N","O"])]
    assert c["source_geometry"]["absolute_normalized_volume"]==0
    assert r["achieved_geometry"]=="NOT_ASSESSED" and r["automatic_adoption"] is False


def test_complete_carbonyl_plane_has_only_scoped_coverage_pass(tmp_path):
    s=values();d=deepcopy(s);plane(d,["C","O","N","R"])
    r=audit(tmp_path,s,d)
    assert r["status"]=="SCOPED_EXPLICIT_COVERAGE_PASS"
    assert r["centres"][0]["covering_planes"][0]["member_esds"]==dict.fromkeys(["C","O","N","R"],.02)
    assert r["native_membership"]=="NOT_RUN" and r["scientific_approval"]=="NOT_RUN"


def test_atom_renaming_preserves_connectivity_selected_finding(tmp_path):
    s=values();rename={"C":"Z1","O":"Z2","N":"Z3","R":"Z4"}
    for key,col in s.items():
        if key.endswith(".atom_id") or ".atom_id_" in key:s[key]=[rename[n] for n in col]
    r=audit(tmp_path,s)
    assert r["missing_explicit_planes"]==["Z1"]
    assert r["centres"][0]["neighbors"]==["Z2","Z3","Z4"]


@pytest.mark.parametrize("defect,reason",[
    ("tetrahedral","OUTSIDE_THREE_COORDINATE_CARBON_SCOPE"),
    ("hydrogen","IMPLICIT_OR_HYDROGEN_FLANK_NOT_ASSESSED"),
    ("aromatic","BOND_REPRESENTATION_NOT_ASSESSED"),
    ("saturated","BOND_REPRESENTATION_NOT_ASSESSED"),
    ("charged","CHARGED_OR_UNKNOWN_CENTRE_NOT_ASSESSED"),
    ("unknown_charge","CHARGED_OR_UNKNOWN_CENTRE_NOT_ASSESSED"),
    ("stereo","DECLARED_CHIRAL_CENTRE_NOT_ASSESSED"),
    ("signed","DECLARED_CHIRAL_CENTRE_NOT_ASSESSED"),
])
def test_unsupported_chemistry_never_becomes_a_missing_plane_repair(tmp_path,defect,reason):
    s=values();a,b="_chem_comp_atom.","_chem_comp_bond."
    if defect=="tetrahedral":
        for key,entry in [("comp_id","XYZ"),("atom_id","H"),("type_symbol","H"),("charge","0"),("pdbx_stereo_config","N"),("x","0"),("y","0"),("z","1")]:s[a+key].append(entry)
        for key,entry in [("comp_id","XYZ"),("atom_id_1","C"),("atom_id_2","H"),("value_order","SING")]:s[b+key].append(entry)
        s[b+"value_order"]=["SING"]*4
    elif defect=="hydrogen":s[a+"type_symbol"][3]="H"
    elif defect=="aromatic":s[b+"value_order"]=["AROM"]*3
    elif defect=="saturated":s[b+"value_order"]=["SING"]*3
    elif defect=="charged":s[a+"charge"][0]="1"
    elif defect=="unknown_charge":s[a+"charge"][0]="?"
    elif defect=="stereo":s[a+"pdbx_stereo_config"][0]="R"
    else:
        p="_chem_comp_chir."
        s.update({p+"comp_id":["XYZ"],p+"id":["chir1"],p+"atom_id_centre":["C"],p+"atom_id_1":["O"],p+"atom_id_2":["N"],p+"atom_id_3":["R"],p+"volume_sign":["positiv"]})
    r=audit(tmp_path,s)
    assert r["status"]=="UNASSESSED" and not r["centres"]
    assert next(x for x in r["unassessed_carbon_centres"] if x["centre"]=="C")["reason"]==reason


def test_nonplanar_source_coordinates_are_described_not_flattened(tmp_path):
    s=values();s["_chem_comp_atom.z"][-1]="1"
    r=audit(tmp_path,s)
    assert r["centres"][0]["source_geometry"]["absolute_normalized_volume"]>.4
    assert r["automatic_adoption"] is False


def test_related_torsions_are_retained_without_claiming_unrestrained_geometry(tmp_path):
    s=values();d=deepcopy(s);p="_chem_comp_tor."
    d.update({p+"comp_id":["XYZ"],p+"id":["improper"],p+"type":["improper"],
              **{p+"atom_id_"+str(i):[n] for i,n in enumerate(["O","C","N","R"],1)},
              p+"value_angle":["180"],p+"value_angle_esd":["2"],p+"period":["2"]})
    r=audit(tmp_path,s,d)
    assert r["centres"][0]["related_torsion_terms"][0]["value_angle_esd"]=="2"
    assert r["centres"][0]["coverage"]=="EXPLICIT_PLANE_MISSING"


@pytest.mark.parametrize("sigma",["0","-1","nan","inf","?"])
def test_invalid_plane_weights_are_not_coverage(tmp_path,sigma):
    s=values();d=deepcopy(s);plane(d,["C","O","N","R"],sigma=sigma)
    with pytest.raises(ValueError):audit(tmp_path,s,d)


@pytest.mark.parametrize("change",["bond","charge","duplicate","dangling"])
def test_conflicting_graph_or_state_refuses(tmp_path,change):
    s=values();d=deepcopy(s)
    if change=="bond":d["_chem_comp_bond.value_order"][0]="SING"
    elif change=="charge":d["_chem_comp_atom.charge"][0]="1"
    elif change=="duplicate":d["_chem_comp_atom.atom_id"][1]="C"
    else:d["_chem_comp_bond.atom_id_2"][0]="MISSING"
    with pytest.raises(ValueError):audit(tmp_path,s,d)


@pytest.mark.parametrize("code", ["PDU", "ATL"])
def test_public_sugar_and_bridged_centres_are_not_planarity_targets(tmp_path, code):
    from nasolve.cif_plane_coverage import audit_trigonal_plane_coverage
    p=Path(__file__).parent/"fixtures/public_ccd"/(code+".cif")
    before=p.read_bytes();r=audit_trigonal_plane_coverage(p,p,code)
    assert p.read_bytes()==before
    if code == "PDU": assert "C5" in r["missing_explicit_planes"]
    assert not {"C1'","C2'","C3'","C4'","C5'"}&set(r["missing_explicit_planes"])


def test_input_change_is_refused_even_with_otherwise_valid_report(tmp_path,monkeypatch):
    import nasolve.cif_plane_coverage as module
    s=write(tmp_path,values(),"source.cif");d=write(tmp_path,values(),"dict.cif")
    original=module._planes
    def mutate(*args):
        result=original(*args);s.write_text(s.read_text()+"\n# changed\n");return result
    monkeypatch.setattr(module,"_planes",mutate)
    with pytest.raises(ValueError,match="input changed"):
        module.audit_trigonal_plane_coverage(s,d,"XYZ")
