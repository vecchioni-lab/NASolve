"""Explicit local aliases retain chemical and NAR authority without registration."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from tests.test_cif_fana import inputs,molecule
from tests.test_cif_fana_enantiomer import mirrored
from tests.test_cif_stereochemistry_audit import write
from tests.test_cif_catalogue import snapshot,workbook,row


def setup(tmp_path):
    s,b,v,n=inputs(tmp_path)
    t=write(tmp_path/"mirror.cif",mirrored(v))
    ccd=tmp_path/"ccd";(ccd/"z").mkdir(parents=True)
    (ccd/"z/data_Z99.cif").write_bytes(s.read_bytes())
    return s,b,t,ccd,tmp_path/"package"


def prepare(s,b,t,ccd,out,**kw):
    from nasolve.cif_fana_component import prepare_fana_enantiomer_component
    return prepare_fana_enantiomer_component(s,"Z99",t,"LF1",workbook=b,
        ccd_root=ccd,reserved_codes=kw.pop("reserved_codes",[]),output=out,
        intent=kw.pop("intent","whole-component-enantiomer"),**kw)


def test_local_binding_replays_and_preserves_every_original(tmp_path):
    from nasolve.cif_fana_component import read_fana_enantiomer_component,bind_fana_enantiomer_records
    s,b,t,c,o=setup(tmp_path);before=snapshot(tmp_path)
    with patch("subprocess.Popen",side_effect=AssertionError("offline")):
        q=prepare(s,b,t,c,o)
        assert read_fana_enantiomer_component(o)==q
        records=[{"Ligand code":"ABC","private":"unchanged"}];saved=deepcopy(records)
        overlay=bind_fana_enantiomer_records(o,records,ccd_root=c,reserved_codes=[])
    assert records==saved and overlay[:-1]==records
    assert overlay[-1]==q["record"] and q["record"]["Ligand code"]=="LF1"
    assert q["record"]["Sugar Type"]=="L-FANA"
    assert q["parent_roles"]==q["target_roles"]
    assert q["namespace"]["scope"]=="DECLARED_CCD_FILENAMES_AND_CALLER_CODES"
    assert q["global_reservation"] is False and q["automatic_adoption"] is False
    assert not any(str(tmp_path) in json.dumps(x) for x in [q])
    after=snapshot(tmp_path);assert all(after[k]==v for k,v in before.items())


@pytest.mark.parametrize("collision",["ccd","workbook","caller","dangling_link","ccd_directory"])
def test_collision_never_creates_a_package(tmp_path,collision):
    s,b,t,c,o=setup(tmp_path);reserved=[]
    if collision in {"ccd","dangling_link","ccd_directory"}:
        p=c/"l/data_LF1.cif";p.parent.mkdir()
        if collision=="ccd":p.write_text("invalid chemistry still occupies code")
        elif collision=="dangling_link":p.symlink_to(c/"missing")
        else:p.mkdir()
    if collision=="workbook":b=workbook(tmp_path,[("cytosine",row("Z99",N1="BN",C5="BC")),("unique",row("LF1"))])
    if collision=="caller":reserved=["LF1"]
    with pytest.raises(ValueError,match="occupied"):
        prepare(s,b,t,c,o,reserved_codes=reserved)
    assert not o.exists()


@pytest.mark.parametrize("defect",["target_bytes","record","report","namespace","receipt_policy","receipt_schema","receipt_files","receipt_hash","escape","duplicate_json","extra_file","symlink"])
def test_frozen_package_cannot_gain_authority_by_tampering(tmp_path,defect):
    from nasolve.cif_fana_component import read_fana_enantiomer_component
    s,b,t,c,o=setup(tmp_path);prepare(s,b,t,c,o)
    p=o/"receipt.json";r=json.loads(p.read_text())
    if defect=="target_bytes":(o/"inputs/target.cif").write_text("bad")
    if defect in {"record","report"}:
        path=o/"binding.json";v=json.loads(path.read_text())
        if defect=="record":v["record"]["N1"]="NOT_AN_ATOM"
        else:v["enantiomer"]["status"]="MADE_UP"
        path.write_text(json.dumps(v))
        # Even a self-consistent replacement hash must not authorize a new binding.
        from hashlib import sha256
        r["files"]["binding.json"]={"sha256":sha256(path.read_bytes()).hexdigest(),"size":path.stat().st_size}
    if defect=="namespace":(o/"namespace.json").write_text("{}")
    if defect=="receipt_policy":r["policy_id"]="other"
    if defect=="receipt_schema":r["schema_version"]=True
    if defect=="receipt_files":r["files"].pop("inputs/parent.cif")
    if defect=="receipt_hash":r["files"]["inputs/parent.cif"]["sha256"]="0"*64
    if defect=="escape":r["files"]["../outside"]={"sha256":"0"*64,"size":0}
    if defect=="extra_file":(o/"hidden.cif").write_text("unbound")
    if defect=="symlink":
        path=o/"inputs/parent.cif";path.unlink();path.symlink_to(s)
    p.write_text(json.dumps(r))
    if defect=="duplicate_json":p.write_text(p.read_text()[:-1]+',"schema_version":1}')
    with pytest.raises((ValueError,FileNotFoundError)):read_fana_enantiomer_component(o)


@pytest.mark.parametrize("collision",["ccd","record","caller"])
def test_binding_checks_live_namespace_again(tmp_path,collision):
    from nasolve.cif_fana_component import bind_fana_enantiomer_records
    s,b,t,c,o=setup(tmp_path);prepare(s,b,t,c,o);records=[];reserved=[]
    if collision=="ccd":(c/"l").mkdir();(c/"l/data_LF1.cif").write_text("new definition")
    if collision=="record":records=[{"Ligand code":"LF1"}]
    if collision=="caller":reserved=["LF1"]
    with pytest.raises(ValueError,match="occupied"):bind_fana_enantiomer_records(o,records,ccd_root=c,reserved_codes=reserved)


def test_cold_read_uses_frozen_evidence_and_is_not_a_current_reservation(tmp_path):
    from nasolve.cif_fana_component import read_fana_enantiomer_component
    original=tmp_path/"original";original.mkdir();s,b,t,c,o=setup(original)
    q=prepare(s,b,t,c,o);moved=original.rename(tmp_path/"moved");assert not original.exists()
    before=snapshot(moved)
    with patch("subprocess.Popen",side_effect=AssertionError("no native execution")):
        assert read_fana_enantiomer_component(moved/"package")==q
    assert snapshot(moved)==before


@pytest.mark.parametrize("defect",["intent","unmirrored","existing","nested","reserved_string","empty_ccd"])
def test_unreviewed_inputs_stop_without_overwrite(tmp_path,defect):
    s,b,t,c,o=setup(tmp_path);kw={}
    if defect=="intent":kw["intent"]="sugar only"
    if defect=="unmirrored":v=mirrored(molecule()[0]);v["_chem_comp_atom.pdbx_stereo_config"][v["_chem_comp_atom.atom_id"].index("C2")]="S";write(t,v)
    if defect=="existing":o.mkdir();(o/"keep").write_text("untouched")
    if defect=="nested":o=t/"package"
    if defect=="reserved_string":kw["reserved_codes"]="ABC"
    if defect=="empty_ccd":c=tmp_path/"empty";c.mkdir()
    before=snapshot(tmp_path)
    with pytest.raises((ValueError,FileExistsError)):prepare(s,b,t,c,o,**kw)
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize("change", ["workbook", "namespace"])
def test_changed_authority_leaves_partial_evidence_without_completion(tmp_path,change):
    import nasolve.cif_fana_component as module
    s,b,t,c,o=setup(tmp_path);derive=module._derive;calls=[]
    def changing(*args,**kwargs):
        result=derive(*args,**kwargs);calls.append(1)
        if len(calls)==2:
            if change=="workbook":b.write_bytes(b.read_bytes()+b"\n")
            else:(c/"l").mkdir();(c/"l/data_LF1.cif").write_text("concurrent occupant")
        return result
    with patch.object(module,"_derive",changing),pytest.raises(ValueError,match="changed"):
        prepare(s,b,t,c,o)
    assert o.is_dir() and (o/"binding.json").exists() and not (o/"receipt.json").exists()
    with pytest.raises(ValueError):module.read_fana_enantiomer_component(o)


@pytest.mark.parametrize("filename", ["data_lf1.cif", "DATA_LF1.CIF"])
def test_ccd_case_variants_occupy_the_same_code_on_every_platform(tmp_path,filename):
    s,b,t,c,o=setup(tmp_path);(c/"l").mkdir();(c/"l"/filename).write_text("occupied")
    with pytest.raises(ValueError,match="occupied"):prepare(s,b,t,c,o)
    assert not o.exists()


def test_case_variant_consumer_record_cannot_shadow_the_target(tmp_path):
    from nasolve.cif_fana_component import bind_fana_enantiomer_records
    s,b,t,c,o=setup(tmp_path);prepare(s,b,t,c,o)
    with pytest.raises(ValueError,match="occupied"):
        bind_fana_enantiomer_records(o,[{"Ligand code":"lf1"}],ccd_root=c,reserved_codes=[])


def test_ccd_directory_symlink_cannot_expand_the_declared_namespace(tmp_path):
    s,b,t,c,o=setup(tmp_path);outside=tmp_path/"outside";outside.mkdir()
    (c/"alias").symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match="symlink"):prepare(s,b,t,c,o)
    assert not o.exists()



def test_record_iterators_preserve_all_existing_consumer_records(tmp_path):
    from nasolve.cif_fana_component import bind_fana_enantiomer_records
    s,b,t,c,o=setup(tmp_path);prepare(s,b,t,c,o)
    records=[{"Ligand code":"ABC","roles":{"N1":"keep"}},{"Ligand code":"DEF"}]
    overlay=bind_fana_enantiomer_records(o,iter(records),ccd_root=c,reserved_codes=[])
    assert overlay[:-1]==records and overlay[-1]["Ligand code"]=="LF1"
    overlay[0]["roles"]["N1"]="changed only in overlay"
    assert records[0]["roles"]["N1"]=="keep"
