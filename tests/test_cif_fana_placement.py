"""Synthetic geometry controls; no claim that the artificial coordinates are physical."""
import json
from unittest.mock import patch
import pytest

from tests.test_cif_fana import molecule, numerical
from tests.test_cif_fana_enantiomer import mirrored
from tests.test_cif_fana_component import prepare
from tests.test_cif_catalogue import workbook, row, snapshot
from tests.test_cif_stereochemistry_audit import write

CONTEXT = {"site":"A:2", "incoming_site":"A:1", "outgoing_site":"A:3",
           "five_prime_state":"linked", "three_prime_state":"linked",
           "symmetry_operation":"x,y,z", "leaving_atom":"OP3"}


def setup(tmp_path, *, host_alias=False, phosphate_alias=False):
    v,_ = molecule()
    rename = {"BN":"N1","BC":"C5","BX":"C6","C1":"C1'","C2":"C2'","C3":"C3'",
              "C4":"C4'","OR":"O4'","C5":"C5'","O5":"O5'","O3":"O3'","P1":"OP1","P2":"OP2"}
    if phosphate_alias:rename.update(P1="O1P",P2="O2P",OP3="O3P")
    for key in v:
        if "atom_id" in key: v[key] = [rename.get(x,x) for x in v[key]]
    source=write(tmp_path/"parent.cif",v);target=write(tmp_path/"target.cif",mirrored(v))
    book=workbook(tmp_path,[("cytosine",row("Z99",N1="N1",C5="C5")), ("cytosine",row("0DC",N1="NX" if host_alias else "N1",C5="C5"))])
    ccd=tmp_path/"ccd";(ccd/"z").mkdir(parents=True);(ccd/"z/data_Z99.cif").write_text("occupied")
    package=tmp_path/"component";prepare(source,book,target,ccd,package)
    values=numerical(mirrored(v))
    for k in values:
        if k.endswith(".comp_id"):values[k]=["LF1"]*len(values[k])
    candidate=write(tmp_path/"numerical.cif",values)
    from nasolve.cif_stereochemistry_audit import _values,_coordinates,_graph
    xyz=_coordinates(_values(candidate,"LF1"),source=False)[1]
    elements=_graph(_values(candidate,"LF1"))[0]
    serial=0;lines=["REMARK synthetic whole-sugar test\n"]
    for site in (1,2,3):
        for name,p in xyz.items():
            if elements[name] in {"H","D"} or name in {"F","OP3","O3P"} or site==1 and name in {"P","OP1","OP2","O1P","O2P"}:continue
            serial+=1;x,y,z=p
            # Proper 90-degree rotation plus translation, same hand.
            x,y,z=-y+site*15,x+10,z+2
            host_name="NX" if host_alias and name=="N1" else {"O1P":"OP1","O2P":"OP2"}.get(name,name)
            lines.append(f"ATOM  {serial:5d} {host_name:>4} 0DC A{site:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  0.75 12.50          {elements[name]:>2}\n")
    lines.append("TER\nEND\n");frame=tmp_path/"frame.pdb";frame.write_text("".join(lines))
    return package,candidate,frame,tmp_path/"control"


def run(paths,context=None):
    from nasolve.cif_fana_placement import prepare_fana_linked_control
    return prepare_fana_linked_control(*paths,context=CONTEXT if context is None else context)


def test_whole_residue_moves_rigidly_without_restoring_dna_sugar(tmp_path):
    from nasolve.cif_fana_placement import read_fana_linked_control
    from nasolve.cif_construction_provenance import _pdb_inventory
    paths=setup(tmp_path);before=snapshot(tmp_path)
    with patch("subprocess.Popen",side_effect=AssertionError("offline")):
        q=run(paths);assert read_fana_linked_control(paths[-1])==q
    model=paths[-1]/"model.pdb";old=_pdb_inventory(paths[2]);new=_pdb_inventory(model)
    assert all(new[k]==v for k,v in old.items() if k[:2]!=("A","2"))
    unchanged=lambda p:[l for l in p.read_text().splitlines() if not(l[:6] in {"ATOM  ","HETATM"} and l[21:26]=="A   2")]
    assert unchanged(paths[2])==unchanged(model)
    assert new[("A","2","","","F")]["element"]=="F"
    assert ("A","2","","","OP3") not in new
    assert len(q["four_sugar_hands"])==4 and len(q["host_hand_checks"])==3
    assert q["max_internal_distance_error_angstrom"]<=.002 and abs(q["rotation_determinant"]-1)<1e-10
    assert q["native_linkage"]=="NOT_ASSESSED" and not q["automatic_adoption"]
    assert len(q["junction_distances"])==2
    assert q["deleted_source_atoms_for_declared_links"]==["O3H0","OP3","OP3H0"]
    after=snapshot(tmp_path);assert all(after[k]==v for k,v in before.items())
    assert str(tmp_path) not in json.dumps(q)


@pytest.mark.parametrize("defect",["hand","missing_f","source_charge","extra_block","partial_coordinates","flat_frame","wrong_host_hand","extra_site","altloc","model_record","op3","first_phosphate","hydrogen","link_record","duplicate_serial","field_overflow"])
def test_unsupported_chemistry_or_frame_is_not_written(tmp_path,defect):
    from nasolve.cif_stereochemistry_audit import _values
    paths=setup(tmp_path);package,candidate,frame,out=paths
    if defect in {"hand","missing_f","source_charge","partial_coordinates","extra_block"}:
        v=_values(candidate,"LF1");a="_chem_comp_atom.";ids=v[a+"atom_id"]
        if defect=="hand":v[a+"z"]=[str(-float(x)) for x in v[a+"z"]]
        if defect=="missing_f":v[a+"type_symbol"][ids.index("F")]="O"
        if defect=="source_charge":v[a+"charge"][ids.index("OP3")]="-1"
        if defect=="partial_coordinates":v[a+"x"][0]="?"
        write(candidate,v)
        if defect=="extra_block":candidate.write_text(candidate.read_text()+"\ndata_comp_OTHER\n_chem_comp.id OTHER\n")
    else:
        lines=frame.read_text().splitlines(keepends=True)
        if defect=="model_record":lines.insert(0,"MODEL        1\n")
        if defect=="link_record":lines.insert(0,"LINK        stale\n")
        for i,l in enumerate(lines):
            if l[:6] not in {"ATOM  ","HETATM"}:continue
            if defect=="wrong_host_hand":l=l[:46]+f"{-float(l[46:54]):8.3f}"+l[54:]
            if defect=="flat_frame" and l[21:26]=="A   2":l=l[:30]+f"{0:8.3f}"*3+l[54:]
            if defect=="altloc":l=l[:16]+"A"+l[17:]
            if defect=="extra_site" and l[21:26]=="A   3":l=l[:22]+"   4"+l[26:]
            if defect=="op3" and l[12:16].strip()=="OP2":l=l[:12]+" OP3"+l[16:]
            if defect=="hydrogen" and i==1:l=l[:76]+" H\n"
            if defect=="duplicate_serial":l=l[:6]+"    1"+l[11:]
            if defect=="field_overflow" and i==1:l=l[:6]+"99999"+l[11:]
            lines[i]=l
        if defect=="first_phosphate":
            l=next(l for l in lines if l[:6]=="ATOM  " and l[12:16].strip()=="P");lines.insert(1,l[:6]+"99998"+l[11:22]+"   1"+l[26:])
        frame.write_text("".join(lines))
    before=snapshot(tmp_path)
    with pytest.raises(ValueError):run(paths)
    assert not out.exists() and snapshot(tmp_path)==before


@pytest.mark.parametrize("key,value",[("incoming_site",None),("outgoing_site","A:1"),("five_prime_state","phosphate"),("three_prime_state","free_OH"),("leaving_atom","OP1"),("symmetry_operation","-x,y,z"),("undeclared",True)])
def test_no_terminal_or_leaving_atom_guess(tmp_path,key,value):
    paths=setup(tmp_path);context={**CONTEXT,key:value}
    with pytest.raises(ValueError):run(paths,context)
    assert not paths[-1].exists()


@pytest.mark.parametrize("defect",["model","report","context","extra","symlink","receipt","incomplete"])
def test_replay_recomputes_even_with_rehashed_outputs(tmp_path,defect):
    from nasolve.cif_fana_placement import read_fana_linked_control
    from nasolve.cif_fana_component import _digest
    paths=setup(tmp_path);run(paths);out=paths[-1];receipt=out/"receipt.json";r=json.loads(receipt.read_text())
    name=None
    if defect=="model":name="model.pdb";(out/name).write_text((out/name).read_text().replace("  1.00 20.00","  1.00 99.00"))
    if defect=="report":
        name="placement.json";v=json.loads((out/name).read_text());v["native_linkage"]="PASS";(out/name).write_text(json.dumps(v))
    if defect=="context":name="context.json";(out/name).write_text(json.dumps({**CONTEXT,"leaving_atom":"OP2"}))
    if defect=="extra":(out/"unbound.pdb").write_text("extra")
    if defect=="symlink":(out/"frame.pdb").unlink();(out/"frame.pdb").symlink_to(paths[2])
    if defect=="receipt":r["schema_version"]=True
    if name:r["files"][name]=_digest(out/name)
    receipt.write_text(json.dumps(r))
    if defect=="incomplete":receipt.unlink()
    with pytest.raises((ValueError,FileNotFoundError)):read_fana_linked_control(out)


def test_cold_replay_is_read_only_after_original_disappears(tmp_path):
    from nasolve.cif_fana_placement import read_fana_linked_control
    original=tmp_path/"original";original.mkdir();paths=setup(original);q=run(paths)
    moved=original.rename(tmp_path/"moved");assert not original.exists();before=snapshot(moved)
    with patch("subprocess.Popen",side_effect=AssertionError("offline")):
        assert read_fana_linked_control(moved/"control")==q
    assert snapshot(moved)==before


def test_existing_output_is_never_repaired(tmp_path):
    paths=setup(tmp_path);run(paths);before=snapshot(tmp_path)
    with pytest.raises(FileExistsError):run(paths)
    assert snapshot(tmp_path)==before


def test_explicit_other_neutral_phosphate_oxygen_is_not_selected_by_name(tmp_path):
    paths=setup(tmp_path)
    q=run(paths,{**CONTEXT,"leaving_atom":"OP2"})
    assert q["deleted_source_atoms_for_declared_links"]==["O3H0","OP2","P2H0"]
    assert "OP3" in q["model_heavy_atoms"] and "OP2" not in q["model_heavy_atoms"]


def test_host_glycosidic_atom_comes_from_the_bound_workbook(tmp_path):
    paths=setup(tmp_path,host_alias=True);q=run(paths)
    assert q["host_glycosidic_atom"]=="NX" and len(q["host_hand_checks"])==3


def test_source_phosphate_names_survive_without_alias_rewriting(tmp_path):
    paths=setup(tmp_path,phosphate_alias=True)
    q=run(paths,{**CONTEXT,"leaving_atom":"O3P"})
    assert "O1P" in q["model_heavy_atoms"] and "O2P" in q["model_heavy_atoms"]
    assert "O3P" not in q["model_heavy_atoms"] and "OP1" not in q["model_heavy_atoms"]


@pytest.mark.parametrize("defect",["output_parent_symlink","output_in_package","package_in_output"])
def test_output_cannot_reuse_or_traverse_source_locations(tmp_path,defect):
    paths=list(setup(tmp_path))
    if defect=="output_parent_symlink":
        link=tmp_path/"alias";link.symlink_to(tmp_path,target_is_directory=True);paths[-1]=link/"new-control"
    if defect=="output_in_package":paths[-1]=paths[0]/"nested"
    if defect=="package_in_output":paths[-1]=tmp_path
    before=snapshot(tmp_path)
    with pytest.raises((ValueError,FileExistsError)):run(paths)
    assert snapshot(tmp_path)==before


def test_interruption_preserves_partial_inputs_without_completion(tmp_path):
    import nasolve.cif_fana_placement as module
    paths=setup(tmp_path);original=module._placement;count=0
    def interrupted(*a,**kw):
        nonlocal count
        count+=1
        if count==2:raise RuntimeError("simulated interruption")
        return original(*a,**kw)
    with patch.object(module,"_placement",interrupted),pytest.raises(RuntimeError):run(paths)
    out=paths[-1]
    assert (out/"frame.pdb").exists() and not (out/"receipt.json").exists()
    with pytest.raises(ValueError):module.read_fana_linked_control(out)
    with pytest.raises(FileExistsError):run(paths)
