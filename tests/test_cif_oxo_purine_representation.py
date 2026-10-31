"""Synthetic neutral 6-oxo fused purines; atom names never select chemistry."""
from copy import deepcopy
import json
import pytest
from nasolve.cif_generation import inspect_component_generation
from nasolve.cif_source_representation import generation_representation_contract, native_representation_check
from tests.test_cif_purine_representation import A, B, POLICY as OLD_POLICY, pair as old_pair
from tests.test_cif_aromatic_representation import add_angles
from tests.test_cif_stereochemistry_audit import write
from tests.test_cif_source_representation import expected, snapshot

POLICY = "cif-source-declared-neutral-6-oxo-purine-aromatic-v1"
FIVE = {"C4", "C5", "N7", "C8", "N9"}


def pair():
    names = ["N1", "C2", "N3", "C4", "C5", "C6", "N7", "C8", "N9", "O6", "N2", "R", "H1", "H8", "H21", "H22", "HR1", "HR2", "HR3"]
    edges = [("N1","C2"),("C2","N3"),("N3","C4"),("C4","C5"),("C5","C6"),("C6","N1"),("C5","N7"),("N7","C8"),("C8","N9"),("N9","C4"),("C6","O6"),("C2","N2"),("N9","R"),("N1","H1"),("C8","H8"),("N2","H21"),("N2","H22"),("R","HR1"),("R","HR2"),("R","HR3")]
    elements = [n[0] if n[0] in "NHO" else "C" for n in names]
    orders = ["DOUB" if i in {1,3,7,10} else "SING" for i in range(len(edges))]
    aromatic = [set(e) <= FIVE for e in edges]
    v = {"data_":"comp_Q17", "_chem_comp.id":["Q17"], A+"comp_id":["Q17"]*len(names), A+"atom_id":names, A+"type_symbol":elements, A+"charge":["0"]*len(names), A+"pdbx_stereo_config":["N"]*len(names), B+"comp_id":["Q17"]*len(edges), B+"atom_id_1":[a for a,b in edges], B+"atom_id_2":[b for a,b in edges], B+"value_order":orders, B+"pdbx_aromatic_flag":["Y" if x else "N" for x in aromatic]}
    for i,axis in enumerate("xyz"):
        v[A+"pdbx_model_Cartn_"+axis+"_ideal"]=[str((n+1)*(i+1)/10) for n in range(len(names))]
    g = deepcopy(v)
    g[B+"type"]=["aromatic" if x else o for x,o in zip(aromatic,orders)]
    g.pop(B+"value_order");g.pop(B+"pdbx_aromatic_flag")
    g[A+"type_energy"]=elements[:]
    g[B+"value_dist"]=["1.4"]*len(edges);g[B+"value_dist_esd"]=["0.02"]*len(edges)
    add_angles(g)
    return v,g


def source_pair(tmp_path):
    v,g=pair()
    return write(tmp_path/"source.cif",v),write(tmp_path/"candidate-fixture.cif",g)


@pytest.mark.parametrize("variant",["plain","renamed","permuted","deuterated","other_donor"])
def test_oxo_purine_needs_its_own_explicit_policy(tmp_path,variant):
    v,g=pair()
    if variant=="deuterated":
        for d in (v,g):d[A+"type_symbol"][12]="D"
        g[A+"type_energy"][12]="D"
    if variant=="other_donor":
        v[B+"value_order"][7:9]=["SING","DOUB"]
        for d in (v,g):d[B+"atom_id_1"][12]="N7"
        add_angles(g)
    if variant=="renamed":
        mapping={n:"Z"+str(i) for i,n in enumerate(v[A+"atom_id"])}
        for d in (v,g):
            for k in d:
                if k.split(".")[-1].startswith("atom_id"):d[k]=[mapping[x] for x in d[k]]
    if variant=="permuted":
        for d in (v,g):
            for k in d:
                if k.startswith((A,B)):d[k]=list(reversed(d[k]))
    source,candidate=write(tmp_path/"source.cif",v),write(tmp_path/"candidate.cif",g)
    before=source.read_bytes(),candidate.read_bytes()
    for policy in (None,OLD_POLICY):
        assert inspect_component_generation(source,candidate,"Q17",bond_representation_policy=policy)["status"]=="REJECTED"
    r=inspect_component_generation(source,candidate,"Q17",bond_representation_policy=POLICY)
    assert r["status"]=="CANDIDATE_REVIEW" and not r["automatic_adoption"]
    system=r["bond_representation"]["equivalent_fused_systems"][0]
    assert len(system["bonds"])==5 and len(system["atoms"])==9
    contract=generation_representation_contract(source,"Q17",POLICY)
    assert len(contract["allowed_systems"])==1 and len(contract["allowed_systems"][0])==5
    assert before==(source.read_bytes(),candidate.read_bytes())


@pytest.mark.parametrize("defect",["missing_flag","candidate_flag","partial","six_order","carbonyl_order","thione","ring_charge","missing_charge","charge_conflict","isotope","hydrogen_move","ring_stereo","bond_stereo","wrong_pattern","fusion_n","underfilled","extra_fusion","extra_carbonyl","six_aromatic"])
def test_oxo_flags_do_not_authorize_other_chemistry(tmp_path,defect):
    v,g=pair()
    if defect=="missing_flag":v[B+"pdbx_aromatic_flag"][3]="?"
    if defect=="candidate_flag":g[B+"pdbx_aromatic_flag"]=["N"]*len(g[B+"type"])
    if defect=="partial":g[B+"type"][3]="DOUB"
    if defect=="six_order":g[B+"type"][0]="DOUB"
    if defect=="carbonyl_order":g[B+"type"][10]="SING"
    if defect=="thione":
        for d in (v,g):d[A+"type_symbol"][9]="S"
        g[A+"type_energy"][9]="S"
    if defect=="ring_charge":
        for d in (v,g):d[A+"charge"][6]="1"
    if defect=="missing_charge":v[A+"charge"][6]="?"
    if defect=="charge_conflict":v[A+"pdbx_formal_charge"]=["1"]*len(v[A+"atom_id"])
    if defect=="isotope":g[A+"type_symbol"][12]="D"
    if defect=="hydrogen_move":g[B+"atom_id_1"][13]="N3"
    if defect=="ring_stereo":v[A+"pdbx_stereo_config"][3]="R"
    if defect=="bond_stereo":v[B+"pdbx_stereo_config"]=["E"]*len(v[B+"value_order"])
    if defect in {"wrong_pattern","fusion_n"}:
        for d in (v,g):d[A+"type_symbol"][7 if defect=="wrong_pattern" else 3]="N"
    if defect=="underfilled":
        for d in (v,g):d[B+"atom_id_1"][13]="R"
    if defect=="extra_fusion":
        for d in (v,g):d[B+"atom_id_2"][19]="C8"
    if defect=="extra_carbonyl":
        for d in (v,g):
            d[A+"type_symbol"][13]="O"
            d[B+("type" if d is g else "value_order")][14]="DOUB"
    if defect=="six_aromatic":v[B+"pdbx_aromatic_flag"][0]="Y"
    source,candidate=write(tmp_path/"s.cif",v),write(tmp_path/"g.cif",g)
    r=inspect_component_generation(source,candidate,"Q17",bond_representation_policy=POLICY)
    assert r["status"]=="REJECTED"
    assert r["bond_representation"]["status"]=="UNSUPPORTED_DIFFERENCE"


@pytest.mark.parametrize("defect",["none","exact","partial","carbonyl","six_ring","charge","coordinates"])
def test_native_oxo_permission_is_exactly_five_edges(tmp_path,defect):
    source,_=source_pair(tmp_path);e=expected(source);n=snapshot(e)
    contract=generation_representation_contract(source,"Q17",POLICY)
    allowed={tuple(x) for x in contract["allowed_systems"][0]}
    for row in n["bonds"]:
        if tuple(row["atoms"]) in allowed and defect!="exact":row["native_order"]=1.5
    if defect=="partial":next(r for r in n["bonds"] if tuple(r["atoms"]) in allowed)["native_order"]=1
    if defect in {"carbonyl","six_ring"}:
        edge={"C6","O6"} if defect=="carbonyl" else {"N1","C2"}
        next(r for r in n["bonds"] if set(r["atoms"])==edge)["native_order"]=1.5
    if defect=="charge":n["atoms"][0]["native_atom_charge"]=1
    if defect=="coordinates":n["atoms"][0]["xyz"]=list(n["atoms"][0]["xyz"]);n["atoms"][0]["xyz"][0]+=0.01
    r=native_representation_check(n,e,contract,coordinates=True,charges=True)
    assert (r["status"]=="SOURCE_REPRESENTATION_PASS") is (defect in {"none","exact"})


def test_new_policy_does_not_silently_adopt_whole_purine_rule(tmp_path):
    v,g=old_pair();s,c=write(tmp_path/"s.cif",v),write(tmp_path/"c.cif",g)
    assert inspect_component_generation(s,c,"Q17",bond_representation_policy=POLICY)["status"]=="REJECTED"
    assert inspect_component_generation(s,c,"Q17",bond_representation_policy=OLD_POLICY)["status"]=="CANDIDATE_REVIEW"


@pytest.mark.parametrize("mode",["none","conversion_edge","conversion_coordinates","conversion_stereo","finished_charge","finished_edge","exception_after"])
def test_oxo_generation_and_replay_keep_fixed_spectator_state(tmp_path,mode):
    from tests.test_cif_source_representation import fake_generation
    from nasolve.cif_source_representation import read_representation_candidate
    out,r=fake_generation(tmp_path,mode,pair_factory=source_pair,policy=POLICY,ring_atoms=FIVE,aromatic_count=5,edge_value=2)
    if mode in {"none","exception_after"}:assert r["status"]=="CANDIDATE_REVIEW"
    elif mode.startswith("finished"):assert r["status"]=="REJECTED" and r["candidate_retained"]
    else:assert r["candidate"] is None
    assert read_representation_candidate(out)==r
    moved=out.rename(tmp_path/"relocated")
    assert not out.exists() and read_representation_candidate(moved)==r


@pytest.mark.parametrize("policy",[None,"unknown",OLD_POLICY])
def test_receipt_cannot_rebind_oxo_permission(tmp_path,policy):
    from tests.test_cif_source_representation import fake_generation
    from nasolve.cif_source_representation import read_representation_candidate
    out,r=fake_generation(tmp_path,pair_factory=source_pair,policy=POLICY,ring_atoms=FIVE,aromatic_count=5,edge_value=2)
    assert r["status"]=="CANDIDATE_REVIEW"
    r["bond_representation_policy"]=policy
    (out/"source_candidate_receipt.json").write_text(json.dumps(r))
    with pytest.raises(ValueError):read_representation_candidate(out)
