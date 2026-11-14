"""FANA source identity and candidate preservation; synthetic graphs, not physics."""
from copy import deepcopy
from itertools import combinations
import json
import random
from unittest.mock import patch

import pytest
from .test_cif_catalogue import workbook, row, snapshot
from .test_cif_stereochemistry_audit import write


def molecule(*, hand="D", ribo=False, rename=False, charge=0):
    atoms = {"BN": "N", "BC": "C", "BX": "C", "C1": "C", "C2": "C",
             "C3": "C", "C4": "C", "OR": "O", "C5": "C", "O5": "O",
             "O3": "O", "F": "F", "P": "P", "P1": "O", "P2": "O", "OP3": "O"}
    edges = [("BN","BC","SING"),("BC","BX","DOUB"),("BX","BN","SING"),
             ("BN","C1","SING"),("C1","OR","SING"),("OR","C4","SING"),
             ("C4","C3","SING"),("C3","C2","SING"),("C2","C1","SING"),
             ("C4","C5","SING"),("C5","O5","SING"),("O5","P","SING"),
             ("C3","O3","SING"),("C2","F","SING"),("P","P1","DOUB"),
             ("P","P2","SING"),("P","OP3","SING")]
    for parent,count in {"BC":1,"BX":1,"C1":1,"C2":1,"C3":1,"C4":1,"C5":2,"O3":1,"P2":1,"OP3":1}.items():
        for i in range(count):
            name=parent+"H"+str(i);atoms[name]="H";edges.append((parent,name,"SING"))
    names={a:f"Z{i:02}" if rename else a for i,a in enumerate(atoms)}
    marks=dict(zip(["C1","C2","C3","C4"],"RRRR" if ribo else "RSRR"))
    if hand=="L":marks={a:{"R":"S","S":"R"}[s] for a,s in marks.items()}
    rng=random.Random(781);xyz={a:[rng.uniform(-4,4) for _ in range(3)] for a in atoms}
    a,b="_chem_comp_atom.","_chem_comp_bond."
    v={"data_":"Z99","_chem_comp.id":["Z99"],"_chem_comp.type":["DNA linking"],
       a+"comp_id":["Z99"]*len(atoms),a+"atom_id":[names[n] for n in atoms],
       a+"type_symbol":list(atoms.values()),a+"charge":[str(charge if n=="BN" else 0) for n in atoms],
       a+"pdbx_stereo_config":[marks.get(n,"N") for n in atoms],
       b+"comp_id":["Z99"]*len(edges),b+"atom_id_1":[names[x] for x,y,o in edges],
       b+"atom_id_2":[names[y] for x,y,o in edges],b+"value_order":[o for x,y,o in edges]}
    for i,axis in enumerate("xyz"):v[a+axis]=[str(xyz[n][i]) for n in atoms]
    return v,names


def numerical(v):
    from nasolve.cif_stereochemistry_audit import _graph,_volume
    g=deepcopy(v);a,b="_chem_comp_atom.","_chem_comp_bond."
    elements,bonds,charges,neighbors=_graph({k.lower():x for k,x in g.items()})
    g[a+"type_energy"]=list(elements.values());g[b+"value_dist"]=["1.5"]*len(bonds);g[b+"value_dist_esd"]=[".02"]*len(bonds)
    angles=[(x,c,y) for c,ns in neighbors.items() for x,y in combinations(sorted(ns),2)]
    p="_chem_comp_angle.";g[p+"comp_id"]=["Z99"]*len(angles)
    for i in range(3):g[p+"atom_id_"+str(i+1)]=[r[i] for r in angles]
    g[p+"value_angle"]=["109.5"]*len(angles);g[p+"value_angle_esd"]=["2"]*len(angles)
    coords={n:[float(g[a+x][i]) for x in "xyz"] for i,n in enumerate(g[a+"atom_id"])}
    centers=[n for n,s in zip(g[a+"atom_id"],g[a+"pdbx_stereo_config"]) if s in {"R","S"}]
    p="_chem_comp_chir.";g[p+"comp_id"]=["Z99"]*len(centers);g[p+"id"]=[str(i) for i in range(len(centers))];g[p+"atom_id_centre"]=centers
    for i in range(3):g[p+"atom_id_"+str(i+1)]=[sorted(neighbors[c])[i] for c in centers]
    g[p+"volume_sign"]=["positive" if _volume(coords,c,sorted(neighbors[c])[:3])>0 else "negative" for c in centers]
    return g


def inputs(tmp_path, **kwargs):
    v,names=molecule(**kwargs)
    source=write(tmp_path/"source.cif",v)
    book=workbook(tmp_path,[("cytosine",row("Z99",N1=names["BN"],C5=names["BC"],**{"Sugar Type":"deliberately wrong"}))])
    return source,book,v,names


def assess(source,book,candidate=None):
    from nasolve.cif_fana import inspect_fana
    return inspect_fana(source,"Z99",workbook=book,candidate=candidate)


@pytest.mark.parametrize("hand",["D","L"])
@pytest.mark.parametrize("rename",[False,True])
@pytest.mark.parametrize("charge",[0,1])
def test_source_family_uses_graph_and_source_stereo_not_names_or_labels(tmp_path,hand,rename,charge):
    s,b,v,n=inputs(tmp_path,hand=hand,rename=rename,charge=charge);before=snapshot(tmp_path)
    with patch("subprocess.Popen",side_effect=AssertionError("read only")):
        q=assess(s,b)
    assert q["status"]=="SOURCE_MATCH" and q["source_family"]=="beta-"+hand+"-FANA"
    assert q["fluorine_atom"]==n["F"] and q["core_stereo"]["ring_c2"]["declared"]==("S" if hand=="D" else "R")
    assert q["source_profile"]["ports"]["phosphate"]["leaving_atoms"]=="NOT_ASSIGNED"
    assert q["native_qualification"]=="NOT_ASSESSED" and not q["automatic_adoption"]
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize("hand",["D","L"])
def test_ribo_epimer_is_not_fana_even_with_a_misleading_label(tmp_path,hand):
    s,b,v,n=inputs(tmp_path,hand=hand,ribo=True)
    q=assess(s,b)
    assert q["status"]=="REVIEW" and q["source_family"] is None
    assert "SOURCE_STEREO_NOT_BETA_FANA" in q["review_reasons"]


@pytest.mark.parametrize("defect",["unknown_stereo","alpha","fluorine_on_base","fluorine_charge","missing_hydrogen","wrong_f_bond","carbon_attachment","sugar_charge","missing_nar_atom"])
def test_unproven_fluorosugar_never_matches(tmp_path,defect):
    s,b,v,n=inputs(tmp_path);a="_chem_comp_atom.";bs="_chem_comp_bond.";ids=v[a+"atom_id"]
    if defect=="unknown_stereo":v[a+"pdbx_stereo_config"][ids.index("C2")]="?"
    if defect=="alpha":v[a+"pdbx_stereo_config"][ids.index("C1")]="S"
    if defect=="fluorine_on_base":v[bs+"atom_id_1"][v[bs+"atom_id_2"].index("F")]="BC"
    if defect=="fluorine_charge":v[a+"charge"][ids.index("F")]="-1"
    if defect=="sugar_charge":v[a+"charge"][ids.index("C2")]="1"
    if defect=="missing_hydrogen":v[a+"type_symbol"][ids.index("C2H0")]="C"
    if defect=="wrong_f_bond":v[bs+"value_order"][v[bs+"atom_id_2"].index("F")]="DOUB"
    if defect=="carbon_attachment":v[a+"type_symbol"][ids.index("BN")]="C"
    if defect=="missing_nar_atom":b=workbook(tmp_path,[("cytosine",row("Z99",N1="absent"))])
    write(s,v);q=assess(s,b)
    assert q["status"]=="REVIEW" and q["review_reasons"]


def test_complete_candidate_keeps_fluorine_full_source_state_and_fixed_hand(tmp_path):
    s,b,v,n=inputs(tmp_path);c=write(tmp_path/"candidate.cif",numerical(v));before=snapshot(tmp_path)
    q=assess(s,b,c)
    assert q["status"]=="CANDIDATE_PRESERVED",q["review_reasons"]
    assert q["candidate_assessment"]["formal_charges_preserved"]
    assert all(r["handedness"]=="PRESERVED" for r in q["candidate_core_stereo"])
    assert q["native_qualification"]=="NOT_ASSESSED" and snapshot(tmp_path)==before


@pytest.mark.parametrize("defect",["mirror","c2_inverted","flat","missing_coordinates","missing_fixed_terms","lost_f","f_to_o","charge","op3_deleted"])
def test_candidate_damage_or_unassessed_hand_cannot_pass(tmp_path,defect):
    s,b,v,n=inputs(tmp_path);g=numerical(v);a="_chem_comp_atom."
    if defect=="mirror":g[a+"z"]=[str(-float(x)) for x in g[a+"z"]]
    if defect=="c2_inverted":
        ids=g[a+"atom_id"];i,j=ids.index("F"),ids.index("C2H0")
        for axis in "xyz":g[a+axis][i],g[a+axis][j]=g[a+axis][j],g[a+axis][i]
    if defect=="flat":g[a+"z"]=["0"]*len(g[a+"atom_id"])
    if defect=="missing_coordinates":g.pop(a+"z")
    if defect=="missing_fixed_terms":g={k:x for k,x in g.items() if not k.startswith("_chem_comp_chir.")}
    if defect in {"lost_f","op3_deleted"}:
        victim="F" if defect=="lost_f" else "OP3";index=g[a+"atom_id"].index(victim)
        for k in list(g):
            if k.startswith(a):g[k].pop(index)
    if defect=="f_to_o":g[a+"type_symbol"][g[a+"atom_id"].index("F")]="O"
    if defect=="charge":g[a+"charge"][g[a+"atom_id"].index("BN")]="1"
    c=write(tmp_path/"candidate.cif",g)
    q=assess(s,b,c)
    assert q["status"]=="REVIEW" and q["review_reasons"]


def test_cli_read_only_and_cold_relocation(tmp_path,capsys):
    from nasolve.cli import main
    original=tmp_path/"original";original.mkdir();s,b,v,n=inputs(original)
    c=write(original/"candidate.cif",numerical(v));expected=assess(s,b,c);moved=tmp_path/"moved";original.rename(moved);before=snapshot(moved)
    with patch("subprocess.Popen",side_effect=AssertionError("no native process")):
        assert assess(moved/s.name,moved/b.name,moved/c.name)==expected
        assert main(["cif-doctor","fana",str(moved/s.name),"--code","Z99","--workbook",str(moved/b.name),"--candidate",str(moved/c.name),"--json"])==2
    assert json.loads(capsys.readouterr().out)==expected
    assert str(tmp_path) not in json.dumps(expected) and not original.exists()
    assert snapshot(moved)==before


@pytest.mark.parametrize("target",["source","workbook","candidate"])
def test_source_or_workbook_change_during_assessment_is_rejected(tmp_path,target):
    import nasolve.cif_fana as module
    s,b,v,n=inputs(tmp_path);c=write(tmp_path/"candidate.cif",numerical(v));original=module.inspect_attachment_profile
    def change(*args,**kwargs):
        q=original(*args,**kwargs);p={"source":s,"workbook":b,"candidate":c}[target];p.write_bytes(p.read_bytes()+b"\n");return q
    with patch.object(module,"inspect_attachment_profile",change),pytest.raises(ValueError,match="changed"):
        assess(s,b,c)


def test_cli_text_and_missing_source(tmp_path,capsys):
    from nasolve.cli import main
    s,b,v,n=inputs(tmp_path)
    args=["cif-doctor","fana",str(s),"--code","Z99","--workbook",str(b)]
    assert main(args)==2
    output=capsys.readouterr().out
    assert "SOURCE_MATCH" in output and "beta-D-FANA" in output
    assert "native qualification" in output
    args[2]=str(tmp_path/"missing.cif")
    assert main(args)==1 and "CIF Doctor:" in capsys.readouterr().err


def test_unknown_representation_policy_is_not_ignored(tmp_path):
    from nasolve.cif_fana import inspect_fana
    s,b,v,n=inputs(tmp_path)
    with pytest.raises(ValueError):
        inspect_fana(s,"Z99",workbook=b,bond_representation_policy="allow-any-bond")
