"""Synthetic deposition metadata without any experimental data."""
import pytest

from nasolve.cli import main

gemmi = pytest.importorskip("gemmi")


def make_cif(path, *, extended=True, link=True, op_id="1", reverse=False, alt=False, gap=False):
    doc = gemmi.cif.Document()
    b = doc.add_new_block("test")
    b.set_mmcif_category("_cell.", {k:[str(v)] for k,v in zip(
        ("length_a","length_b","length_c","angle_alpha","angle_beta","angle_gamma"),(20,20,20,90,90,90))})
    b.set_mmcif_category("_symmetry.", {"space_group_name_H-M":["P 1"]})
    b.set_mmcif_category("_space_group_symop.", {"id":[op_id],"operation_xyz":["x,y,z"]})
    b.set_mmcif_category("_entity_poly.", {"entity_id":["1"], "type":["polydeoxyribonucleotide"]})
    b.set_mmcif_category("_struct_asym.", {"id":["NA"],"entity_id":["1"]})
    p = 21.61 if extended else 1.61
    n = 3 if gap else 2
    atoms = [(1,"G7","O3'","O",0.,0.,0.),(1,"G7","C3'","C",-1.,0.6,0.),
             (n,"QX","P","P",p,0.,0.),(n,"QX","OP1","O",p+.5,1.40,0.),
             (n,"QX","OP2","O",p+.49,-.70,1.),(n,"QX","O5'","O",p+.3,-.8,-1.)]
    if alt:
        atoms.append((1,"G7","O3'","O",0.4,1.2,0.))
    columns = ("id","pdbx_PDB_model_num","label_asym_id","label_entity_id","label_seq_id","label_comp_id",
               "label_atom_id","type_symbol","label_alt_id","occupancy","Cartn_x","Cartn_y","Cartn_z")
    values = []
    for i,(seq,comp,name,elem,x,y,z) in enumerate(atoms):
        letter = ("A" if i==0 else "B") if alt and name=="O3'" else False
        values.append((str(i+1),"1","NA","1",str(seq),comp,name,elem,letter,"0.5" if letter else "1",str(x),str(y),str(z)))
    b.set_mmcif_category("_atom_site.",dict(zip(columns,map(list,zip(*values)))))
    if link:
        oxygen = ("NA","1","G7","O3'",op_id+"_555")
        phosphate = ("NA",str(n),"QX","P",op_id+("_455" if extended else "_555"))
        fields={"id":["c1"],"conn_type_id":["covale"]}
        for i,endpoint in enumerate((phosphate,oxygen) if reverse else (oxygen,phosphate),1):
            for tag,v in zip(("label_asym_id","label_seq_id","label_comp_id","label_atom_id","symmetry"),endpoint):
                fields[f"ptnr{i}_{tag}"]=[v]
        b.set_mmcif_category("_struct_conn.",fields)
    doc.write_file(str(path))
    return path


def test_separate_ordinary_step_from_named_crystal_connection(tmp_path, capsys):
    import json
    model=make_cif(tmp_path/"input.cif")
    raw=model.read_bytes()
    assert main(["cif-doctor","deposition-links",str(model),"--json"]) == 2
    r=json.loads(capsys.readouterr().out)["model"]
    assert r["ordinary"]["measured"]==1
    assert r["ordinary"]["long_steps"][0]["distance_A"]==pytest.approx(21.61)
    (edge,)=r["declared"]
    assert edge["operator_on_P"]=="x-1,y,z"
    assert edge["observations"][0]["distance_A"]==pytest.approx(1.61)
    assert edge["observations"][0]["O3_P_OP1_deg"]==pytest.approx(109.65,abs=.1)
    assert model.read_bytes()==raw


def test_reordered_operators_and_reversed_rows_match_but_missing_records_are_reported(tmp_path):
    from nasolve.cif_deposition_links import inspect_deposition_links
    a=make_cif(tmp_path/"a.cif",extended=False)
    b=make_cif(tmp_path/"b.cif",extended=False,op_id="7",reverse=True)
    before=a.read_bytes(),b.read_bytes()
    r=inspect_deposition_links(a, processed=b)
    assert r["status"]=="CHECKED" and r["comparison"]["missing"]==[]
    assert (a.read_bytes(),b.read_bytes())==before
    plain=make_cif(tmp_path/"plain.cif",extended=False,link=False)
    r=inspect_deposition_links(a,processed=plain)
    assert r["status"]=="REVIEW"
    assert r["comparison"]["comparable"] and len(r["comparison"]["missing"])==1
    assert r["processed"]["ordinary"]["maximum_A"]==pytest.approx(1.61)
    changed=make_cif(tmp_path/"changed.cif",extended=True,link=False)
    r=inspect_deposition_links(a,processed=changed)
    assert not r["comparison"]["comparable"] and r["comparison"]["missing"] is None
    shifted = make_cif(tmp_path/"shifted.cif", extended=True)
    reversed_shift = make_cif(tmp_path/"reversed.cif", extended=True, op_id="4", reverse=True)
    assert inspect_deposition_links(shifted, processed=reversed_shift)["comparison"]["missing"] == []


def test_ambiguous_conformers_and_missing_sequence_positions_do_not_approve_a_step(tmp_path):
    from nasolve.cif_deposition_links import inspect_deposition_links
    alt=inspect_deposition_links(make_cif(tmp_path/"alt.cif",extended=False,alt=True))
    assert alt["status"]=="REVIEW" and alt["model"]["ordinary"]["measured"]==0
    assert alt["model"]["ordinary"]["unmeasured"]
    gap=inspect_deposition_links(make_cif(tmp_path/"gap.cif",gap=True,link=False))
    assert gap["model"]["ordinary"]["measured"]==0 and gap["model"]["ordinary"]["sequence_gaps"]


def test_missing_operator_is_unresolved_and_absent_polymer_declarations_are_not_guessed(tmp_path):
    from nasolve.cif_deposition_links import inspect_deposition_links
    path=make_cif(tmp_path/"test.cif",extended=False)
    doc=gemmi.cif.read_file(str(path))
    for cat in ("_space_group_symop.", "_entity_poly."):
        b=doc[0]
        for item in list(b):
            tag=item.loop.tags[0] if item.loop else item.pair[0] if item.pair else ""
            if tag.startswith(cat):
                item.erase()
        doc.write_file(str(path))
        r=inspect_deposition_links(path)
        assert r["status"]=="REVIEW"
        if cat=="_space_group_symop.":
            assert r["model"]["declared"][0]["operator_on_P"] is None
    assert r["model"]["ordinary"]["measured"]==0


def test_unobserved_oxygen_and_gzip_preserve_scope(tmp_path):
    import gzip
    from nasolve.cif_deposition_links import inspect_deposition_links

    path = make_cif(tmp_path / "model.cif", extended=False)
    doc = gemmi.cif.read_file(str(path))
    atoms = doc[0].get_mmcif_category("_atom_site.")
    atoms["occupancy"][atoms["label_atom_id"].index("OP2")] = "0"
    doc[0].set_mmcif_category("_atom_site.", atoms)
    packed = tmp_path / "model.cif.gz"
    packed.write_bytes(gzip.compress(doc.as_string().encode()))
    result = inspect_deposition_links(packed)
    assert result["status"] == "REVIEW"
    assert result["model"]["ordinary"]["measured"] == 1
    assert result["model"]["missing_declared_OP_angles"] == ["c1"]
    assert result["model"]["declared"][0]["observations"][0]["O3_P_OP2_deg"] is None


def test_changed_coordinate_labels_must_still_agree_with_the_declared_sequence(tmp_path):
    from nasolve.cif_deposition_links import inspect_deposition_links

    path = make_cif(tmp_path / "conflict.cif", extended=False)
    doc = gemmi.cif.read_file(str(path))
    doc[0].set_mmcif_category("_entity_poly_seq.", {
        "entity_id": ["1", "1"], "num": ["1", "2"], "mon_id": ["G7", "WRONG"],
    })
    doc.write_file(str(path))
    result = inspect_deposition_links(path)
    assert result["model"]["ordinary"]["maximum_A"] == pytest.approx(1.61)
    assert result["status"] == "REVIEW"
    assert result["model"]["sequence_conflicts"] == [("1", "NA", 2, "QX", "_entity_poly_seq.")]
