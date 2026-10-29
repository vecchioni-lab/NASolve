"""A proposed mirrored source needs explicit intent, full identity and every hand."""
from copy import deepcopy
from unittest.mock import patch
import pytest
from tests.test_cif_fana import inputs, numerical
from tests.test_cif_stereochemistry_audit import write
from tests.test_cif_catalogue import snapshot

A,B="_chem_comp_atom.","_chem_comp_bond."
INTENT="whole-component-enantiomer"


def mirrored(v):
    d=deepcopy(v);d["data_"]="comp_LF1";d["_chem_comp.id"]=["LF1"]
    for k in d:
        if k.endswith(".comp_id"):d[k]=["LF1"]*len(d[k])
        if k in {A+"pdbx_stereo_config",A+"stereo_config"}:d[k]=[{"R":"S","S":"R"}.get(x,x) for x in d[k]]
        if k.lower() in {A+"z",A+"model_cartn_z",A+"pdbx_model_cartn_z_ideal"}:d[k]=[str(-float(x)) for x in d[k]]
    return d


def inspect(s,b,t,**kwargs):
    from nasolve.cif_fana_enantiomer import inspect_fana_enantiomer
    return inspect_fana_enantiomer(s,"Z99",t,"LF1",workbook=b,intent=kwargs.get("intent",INTENT))


@pytest.mark.parametrize("variant",["plain","renamed","permuted","translated","rotated","deuterated","all_coordinates","reverse"])
def test_explicit_enantiomer_retains_complete_graph_and_changes_all_hands(tmp_path,variant):
    s,b,v,n=inputs(tmp_path,rename=variant=="renamed",hand="L" if variant=="reverse" else "D")
    if variant=="deuterated":v[A+"type_symbol"][v[A+"type_symbol"].index("H")]="D"
    if variant=="all_coordinates":
        for axis in "xyz":
            v[A+"model_Cartn_"+axis]=v[A+axis][:]
            v[A+"pdbx_model_Cartn_"+axis+"_ideal"]=v[A+axis][:]
    write(s,v);g=mirrored(v)
    if variant=="translated":
        for axis in "xyz":g[A+axis]=[str(float(x)+5) for x in g[A+axis]]
    if variant=="rotated":g[A+"x"],g[A+"y"]=g[A+"y"],[str(-float(x)) for x in g[A+"x"]]
    if variant=="permuted":
        for k in g:
            if k.startswith((A,B)):g[k]=g[k][::-1]
    t=write(tmp_path/"target.cif",g);before=snapshot(tmp_path)
    with patch("subprocess.Popen",side_effect=AssertionError("read only")):
        q=inspect(s,b,t)
    assert q["status"]=="ENANTIOMER_SOURCE_PASS",q["review_reasons"]
    assert q["target_family"]==("beta-D-FANA" if variant=="reverse" else "beta-L-FANA")
    assert all(x["all_distances_preserved"] and x["all_sugar_hands_inverted"] for x in q["coordinate_families"])
    assert len(q["coordinate_families"])==(3 if variant=="all_coordinates" else 1)
    assert not q["automatic_adoption"] and q["absolute_cip_assignment"]=="NOT_RUN"
    assert q["target_nar_registration"]=="NOT_RUN" and snapshot(tmp_path)==before


@pytest.mark.parametrize("defect",["same_hand","labels_only","coords_only","one_epimer","isotope","charge","missing_charge","hydrogen_move","missing_f","extra_center","unknown_marker","missing_coordinates","partial_family","unreflected_family","flat","distorted","bond_flag","numerical","descriptor","same_code"])
def test_unproven_or_partial_mirror_does_not_pass(tmp_path,defect):
    s,b,v,n=inputs(tmp_path);g=mirrored(v)
    if defect=="same_hand":g=deepcopy(v)
    if defect in {"same_hand","same_code"}:
        if defect=="same_hand":
            g["_chem_comp.id"]=["LF1"]
            for k in g:
                if k.endswith(".comp_id"):g[k]=["LF1"]*len(g[k])
        else:g["_chem_comp.id"]=["Z99"];g[A+"comp_id"]=["Z99"]*len(g[A+"atom_id"]);g[B+"comp_id"]=["Z99"]*len(g[B+"atom_id_1"])
    if defect=="labels_only":g[A+"z"]=v[A+"z"][:]
    if defect=="coords_only":g[A+"pdbx_stereo_config"]=v[A+"pdbx_stereo_config"][:]
    if defect=="one_epimer":g[A+"pdbx_stereo_config"][g[A+"atom_id"].index("C2")]=v[A+"pdbx_stereo_config"][v[A+"atom_id"].index("C2")]
    if defect=="isotope":g[A+"type_symbol"][g[A+"type_symbol"].index("H")]="D"
    if defect=="charge":g[A+"charge"][0]="1"
    if defect=="missing_charge":g[A+"charge"][0]="?"
    if defect=="hydrogen_move":g[B+"atom_id_1"][-1]="P1"
    if defect=="missing_f":g[A+"type_symbol"][g[A+"atom_id"].index("F")]="O"
    if defect=="extra_center":v[A+"pdbx_stereo_config"][0]="R";g[A+"pdbx_stereo_config"][0]="S";write(s,v)
    if defect=="unknown_marker":v[A+"pdbx_stereo_config"][0]="?";write(s,v)
    if defect=="missing_coordinates":g.pop(A+"z")
    if defect=="partial_family":g[A+"model_Cartn_x"]=g[A+"x"][:]
    if defect=="unreflected_family":
        for axis in "xyz":v[A+"model_Cartn_"+axis]=v[A+axis][:];g[A+"model_Cartn_"+axis]=v[A+axis][:]
        write(s,v)
    if defect=="flat":g[A+"z"]=["0"]*len(g[A+"z"])
    if defect=="distorted":g[A+"x"][0]=str(float(g[A+"x"][0])+0.1)
    if defect=="bond_flag":g[B+"pdbx_aromatic_flag"]=["Y"]*len(g[B+"atom_id_1"])
    if defect=="numerical":g=numerical(g)
    if defect=="descriptor":g["_pdbx_chem_comp_descriptor.comp_id"]=["LF1"];g["_pdbx_chem_comp_descriptor.descriptor"]=["unverified-stereo-smiles"]
    t=write(tmp_path/"target.cif",g)
    try:q=inspect(s,b,t)
    except ValueError:return
    assert q["status"]=="REVIEW" and q["review_reasons"]


@pytest.mark.parametrize("intent",[None,"mirror","sugar-only",True])
def test_inversion_intent_is_explicit(tmp_path,intent):
    s,b,v,n=inputs(tmp_path);t=write(tmp_path/"target.cif",mirrored(v))
    with pytest.raises(ValueError,match="intent"):inspect(s,b,t,intent=intent)


def test_relocated_sources_replay_without_native_code(tmp_path):
    original=tmp_path/"original";s,b,v,n=inputs(original);t=write(original/"target.cif",mirrored(v))
    q=inspect(s,b,t);moved=original.rename(tmp_path/"moved");assert not original.exists()
    with patch("subprocess.Popen",side_effect=AssertionError("read only")):
        assert inspect(moved/s.name,moved/b.name,moved/t.name)==q


@pytest.mark.parametrize("scale",[1e200,1e308])
def test_finite_coordinates_with_overflowed_geometry_cannot_pass(tmp_path,scale):
    import json
    s,b,v,n=inputs(tmp_path)
    for axis in "xyz":v[A+axis]=[str(float(x)*(scale/8)) for x in v[A+axis]]
    write(s,v);t=write(tmp_path/"target.cif",mirrored(v))
    q=inspect(s,b,t)
    assert q["status"]=="REVIEW"
    json.dumps(q,allow_nan=False)
