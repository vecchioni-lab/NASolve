"""Fresh plane candidates preserve the old ring and every non-plane term."""
from copy import deepcopy

import pytest

from tests import test_cif_plane_coverage as fixtures
from nasolve.ligand_profiles import _blocks


def inputs(tmp_path, code="XYZ"):
    s=fixtures.values(code)
    for axis in "xyz":s["_chem_comp_atom.pdbx_model_Cartn_"+axis+"_ideal"]=s.pop("_chem_comp_atom."+axis)
    d=deepcopy(s);fixtures.plane(d,["C","O","N"])
    d["_chem_comp_bond.value_dist"]=["1.234","1.407","1.607"]
    d["_chem_comp_bond.value_dist_esd"]=["0.02"]*3
    p=deepcopy(s);fixtures.plane(p,["C","O","N","R"],name="native-local")
    return s,d,p


def prepare(tmp_path,s,d,p):
    from nasolve.cif_plane_candidate import prepare_trigonal_plane_candidate
    paths=[fixtures.write(tmp_path,v,n+".cif") for v,n in zip((s,d,p),("source","dictionary","proposal"))]
    old=[(f.read_bytes(),f.stat().st_mtime_ns) for f in paths]
    out=tmp_path/"candidate.cif"
    result=prepare_trigonal_plane_candidate(*paths,s["_chem_comp.id"][0],out)
    assert [(f.read_bytes(),f.stat().st_mtime_ns) for f in paths]==old
    return paths,out,result


@pytest.mark.parametrize("code",["PDU","ZZZ","A1AAZ"])
def test_completion_adds_only_one_supported_plane_row(tmp_path,code):
    s,d,p=inputs(tmp_path,code)
    paths,out,r=prepare(tmp_path,s,d,p)
    before=_blocks(paths[1])[0].values;after=_blocks(out)[0].values
    for key,value in before.items():
        if key.startswith("_chem_comp_plane_atom."):assert after[key][:-1]==value
        else:assert after[key]==value
    assert r["additions"]==[dict(plane="plane1",atom="R",dist_esd=.02)]
    assert r["remaining_missing_explicit_planes"]==[]
    assert r["status"]=="CANDIDATE_REVIEW" and not r["automatic_adoption"]
    assert r["native_qualification"]=="NOT_RUN" and "NOT_VERIFIED" in r["corroboration"]


@pytest.mark.parametrize("defect,reason",[
    ("nonplanar","SOURCE_IDEAL_OUTSIDE"),("collinear","COLLINEAR_SOURCE"),
    ("no_ideal","REQUIRE_EXPLICIT_SOURCE_IDEAL"),("no_partial","REQUIRE_ONE_EXISTING"),
    ("two_partials","REQUIRE_ONE_EXISTING"),("no_support","NO_CORROBORATING"),
    ("ambiguous_sigma","AMBIGUOUS_CORROBORATING"),("support_chiral","NO_CORROBORATING"),
    ("already_complete","No supported plane completion"),
    ("old_plane_outlier","SOURCE_IDEAL_OUTSIDE"),
])
def test_unsupported_completion_leaves_no_candidate(tmp_path,defect,reason):
    s,d,p=inputs(tmp_path);a="_chem_comp_atom."
    if defect=="nonplanar":s[a+"pdbx_model_Cartn_z_ideal"][-1]="1"
    elif defect=="collinear":s[a+"pdbx_model_Cartn_y_ideal"][2]="0"
    elif defect=="no_ideal":
        for axis in "xyz":s[a+axis]=s.pop(a+"pdbx_model_Cartn_"+axis+"_ideal")
    elif defect=="no_partial":d={k:v for k,v in d.items() if not k.startswith("_chem_comp_plane_atom.")}
    elif defect=="two_partials":fixtures.plane(d,["C","O","R"],name="plane2")
    elif defect=="no_support":p=deepcopy(s)
    elif defect=="ambiguous_sigma":fixtures.plane(p,["C","O","N","R"],name="other",sigma=".03")
    elif defect=="support_chiral":p[a+"pdbx_stereo_config"][0]="R"
    elif defect=="already_complete":fixtures.plane(d,["R"])
    elif defect=="old_plane_outlier":
        # Another existing member must be retained and source-compatible too.
        for v in (s,d,p):
            for key,col in list(v.items()):
                if key.startswith(a):col.append({"atom_id":"X","comp_id":"XYZ","type_symbol":"O","charge":"0","pdbx_stereo_config":"N","pdbx_model_Cartn_x_ideal":"0","pdbx_model_Cartn_y_ideal":"0","pdbx_model_Cartn_z_ideal":"1"}[key[len(a):]])
        fixtures.plane(d,["X"])
    with pytest.raises(ValueError,match=reason):prepare(tmp_path,s,d,p)
    assert not (tmp_path/"candidate.cif").exists()


def test_unrelated_blocks_are_preserved_byte_for_byte(tmp_path):
    from nasolve.cif_plane_candidate import prepare_trigonal_plane_candidate
    s,d,p=inputs(tmp_path)
    paths=[fixtures.write(tmp_path,v,n+".cif") for v,n in zip((s,d,p),("source","dictionary","proposal"))]
    extra="\ndata_unrelated\n# preserve this formatting\n_custom.value  12\n"
    paths[1].write_text(paths[1].read_text()+extra)
    out=tmp_path/"candidate.cif"
    prepare_trigonal_plane_candidate(*paths,"XYZ",out)
    assert _blocks(out)[-1].text==_blocks(paths[1])[-1].text


@pytest.mark.parametrize("which",["existing","symlink_parent"])
def test_output_never_overwrites_or_follows_symlink_parent(tmp_path,which):
    from nasolve.cif_plane_candidate import prepare_trigonal_plane_candidate
    s,d,p=inputs(tmp_path);paths=[fixtures.write(tmp_path,v,n+".cif") for v,n in zip((s,d,p),("source","dictionary","proposal"))]
    if which=="existing":out=tmp_path/"candidate.cif";out.write_bytes(b"preserve\n")
    else:
        real=tmp_path/"real";real.mkdir();link=tmp_path/"link";link.symlink_to(real,target_is_directory=True);out=link/"candidate.cif"
    with pytest.raises(ValueError,match="fresh separate"):prepare_trigonal_plane_candidate(*paths,"XYZ",out)
    if which=="existing":assert out.read_bytes()==b"preserve\n"
    else:assert not out.exists()


@pytest.mark.parametrize("when",["before_write","after_write"])
def test_changing_input_refuses_and_preserves_any_partial_output(tmp_path,monkeypatch,when):
    import nasolve.cif_plane_candidate as module
    s,d,p=inputs(tmp_path);paths=[fixtures.write(tmp_path,v,n+".cif") for v,n in zip((s,d,p),("source","dictionary","proposal"))]
    out=tmp_path/"candidate.cif"
    if when=="before_write":
        original=module._source_plane_evidence
        def changed(*args):
            r=original(*args);paths[0].write_text(paths[0].read_text()+"\n#changed\n");return r
        monkeypatch.setattr(module,"_source_plane_evidence",changed)
    else:
        original=module.audit_trigonal_plane_coverage
        def changed(source,dictionary,code):
            r=original(source,dictionary,code)
            if dictionary==out:paths[0].write_text(paths[0].read_text()+"\n#changed\n")
            return r
        monkeypatch.setattr(module,"audit_trigonal_plane_coverage",changed)
    with pytest.raises(ValueError,match="input changed"):module.prepare_trigonal_plane_candidate(*paths,"XYZ",out)
    assert out.exists()==(when=="after_write")


def test_extra_plane_column_is_not_silently_invented(tmp_path):
    s,d,p=inputs(tmp_path);d["_chem_comp_plane_atom.custom"]=["retain"]*3
    with pytest.raises(ValueError,match="Unsupported existing plane columns"):prepare(tmp_path,s,d,p)
    assert not (tmp_path/"candidate.cif").exists()


def test_partial_supported_repair_retains_unresolved_centre(tmp_path):
    s,d,p=inputs(tmp_path)
    second={k:[(x+"2" if "atom_id" in k else x) for x in v] if isinstance(v,list) else v for k,v in s.items()}
    for v in (s,d,p):
        for k,col in second.items():
            if k.startswith(("_chem_comp_atom.","_chem_comp_bond.")):
                v[k].extend(col)
        # Numerical rows apply to all bonds, even though only plane rows change.
        if "_chem_comp_bond.value_dist" in v:
            v["_chem_comp_bond.value_dist"].extend(["1.234","1.407","1.607"])
            v["_chem_comp_bond.value_dist_esd"].extend(["0.02"]*3)
    fixtures.plane(d,["C2","O2","N2"],name="plane2")
    paths,out,r=prepare(tmp_path,s,d,p)
    assert r["remaining_missing_explicit_planes"]==["C2"]
    assert r["unresolved_centres"]==[dict(centre="C2",reason="NO_CORROBORATING_LOCAL_PLANE")]
    assert r["status"]=="CANDIDATE_REVIEW" and not r["automatic_adoption"]


def test_added_esd_copies_supplied_text_without_reformatting(tmp_path):
    s,d,p=inputs(tmp_path)
    p["_chem_comp_plane_atom.dist_esd"]=["0.020"]*4
    paths,out,r=prepare(tmp_path,s,d,p)
    assert _blocks(out)[0].values["_chem_comp_plane_atom.dist_esd"][-1]=="0.020"


def test_unmodified_ideal_hydrogens_do_not_block_heavy_plane_completion(tmp_path):
    s,d,p=inputs(tmp_path);a="_chem_comp_atom.";b="_chem_comp_bond."
    for v in (s,d,p):
        for key,entry in [("comp_id","XYZ"),("atom_id","HN"),("type_symbol","H"),("charge","0"),("pdbx_stereo_config","N"),("pdbx_model_Cartn_x_ideal","-.5"),("pdbx_model_Cartn_y_ideal","1"),("pdbx_model_Cartn_z_ideal",".7")]:v[a+key].append(entry)
        for key,entry in [("comp_id","XYZ"),("atom_id_1","N"),("atom_id_2","HN"),("value_order","SING")]:v[b+key].append(entry)
        if b+"value_dist" in v:v[b+"value_dist"].append("1.0");v[b+"value_dist_esd"].append(".02")
    fixtures.plane(d,["HN"])
    paths,out,r=prepare(tmp_path,s,d,p)
    proof=r["selected_centres"][0]["source_plane_evidence"]
    assert proof["unassessed_source_ideal_hydrogens"]==["HN"]
    assert "HN" not in proof["source_ideal_distances_angstrom"]
    assert _blocks(out)[0].values["_chem_comp_plane_atom.atom_id"]==["C","O","N","HN","R"]
