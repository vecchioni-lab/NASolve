"""Explicit base anchoring replaces host sugar geometry, never target chemistry."""
import json
from unittest.mock import patch
import pytest
from openpyxl import load_workbook
from tests.test_cif_whole_furanose import setup, run as old_run
from tests.test_cif_catalogue import snapshot


def inputs(tmp_path, *, bridged=False, rename=False, hand='D'):
    paths, context, roles = setup(tmp_path, bridged=bridged, rename=rename, hand=hand)
    from nasolve.cif_stereochemistry_audit import _values
    ids = _values(paths[0], 'Z99')['_chem_comp_atom.atom_id']
    # The workbook is authoritative even when every source atom has been renamed.
    if rename:
        original = ["N1", "C2", "C6"] if bridged else ["BN", "BC", "BX"]
        plain = tmp_path/'plain'; plain.mkdir()
        other, _, _ = setup(plain, bridged=bridged, hand=hand)
        old = _values(other[0], 'Z99')['_chem_comp_atom.atom_id']
        names = [ids[old.index(n)] for n in original]
    else:names = ['N1', 'C2', 'C6'] if bridged else ['BN', 'BC', 'BX']
    book = load_workbook(paths[3]); sheet = next(s for s in book.worksheets if s.max_row > 1)
    for role, name in zip(['C2', 'C6'], names[1:]):
        column = sheet.max_column+1; sheet.cell(1,column,role); sheet.cell(2,column,name)
    book.save(paths[3]); book.close()
    lines = paths[4].read_text().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line[:6]=='ATOM  ' and line[21:26]=='A  11':
            lines[i]=line[:46]+f'{-float(line[46:54]):8.3f}'+line[54:]
    paths[4].write_text(''.join(lines))
    return paths, context


def run(paths, context, roles=None):
    from nasolve.cif_whole_furanose import prepare_base_anchored_furanose_control
    return prepare_base_anchored_furanose_control(*paths,code='Z99',context=context,
        base_frame_roles=['N1','C2','C6'] if roles is None else roles)


@pytest.mark.parametrize('bridged,rename,hand',[(False,False,'D'),(False,True,'L'),(True,False,'D'),(True,True,'D')])
def test_different_host_hands_allow_explicit_base_placement_only(tmp_path,bridged,rename,hand):
    paths,c=inputs(tmp_path,bridged=bridged,rename=rename,hand=hand)
    with pytest.raises(ValueError,match='Host and target sugar hands'):old_run(paths,c)
    before=snapshot(tmp_path)
    q=run(paths,c)
    assert q['alignment']=='NAR_BASE_FRAME' and not q['automatic_adoption']
    assert not all(r['compatible'] for r in q['host_hand_checks'])
    assert len({r['center'] for r in q['retained_hands']})==4
    assert q['max_internal_distance_error_angstrom']<=.002
    assert q['native_linkage']=='NOT_ASSESSED' and q['model_optimization']=='NOT_RUN'
    unchanged=lambda p:[l for l in p.read_text().splitlines() if not(l[:6] in {'ATOM  ','HETATM'} and l[21:26]=='A  11')]
    assert unchanged(paths[4])==unchanged(paths[-1]/'model.pdb')
    assert all(snapshot(tmp_path)[k]==v for k,v in before.items())
    assert str(tmp_path) not in json.dumps(q)


@pytest.mark.parametrize('roles',[[],['N1','C2'],['N1','C2','C2'],['C2','N1','C6'],['N1','C2','missing'],'N1,C2,C6',[1,'C2','C6']])
def test_frame_requires_explicit_distinct_glycosidic_base_roles(tmp_path,roles):
    paths,c=inputs(tmp_path)
    with pytest.raises(ValueError):run(paths,c,roles)
    assert not paths[-1].exists()


@pytest.mark.parametrize('defect',['sugar_anchor','hydrogen_anchor','mirror_candidate','flat_host','missing_host_anchor'])
def test_frame_and_target_guards_remain_fail_closed(tmp_path,defect):
    from nasolve.cif_stereochemistry_audit import _values
    from tests.test_cif_stereochemistry_audit import write
    paths,c=inputs(tmp_path)
    if defect in {'sugar_anchor','hydrogen_anchor'}:
        b=load_workbook(paths[3]);s=next(s for s in b.worksheets if s.max_row > 1)
        for cell in s[1]:
            if cell.value=='C6':s.cell(2,cell.column,'C2' if defect=='sugar_anchor' else 'C1H0')
        b.save(paths[3]);b.close()
    elif defect=='mirror_candidate':
        v=_values(paths[1],'Z99');v['_chem_comp_atom.z']=[str(-float(x)) for x in v['_chem_comp_atom.z']];write(paths[1],v)
    else:
        lines=paths[4].read_text().splitlines(keepends=True);out=[]
        for line in lines:
            if line[:6]=='ATOM  ' and line[21:26]=='A  11':
                if defect=='missing_host_anchor' and line[12:16].strip()=='BX':continue
                if defect=='flat_host':line=line[:30]+f'{0:8.3f}'*3+line[54:]
            out.append(line)
        paths[4].write_text(''.join(out))
    with pytest.raises(ValueError):run(paths,c)
    assert not paths[-1].exists()


def test_cold_replay_immutable_output_and_rehashed_role_forgery(tmp_path):
    from nasolve.cif_whole_furanose import read_base_anchored_furanose_control,read_whole_furanose_control
    from nasolve.cif_fana_component import _digest
    original=tmp_path/'original';original.mkdir();paths,c=inputs(original,bridged=True);q=run(paths,c)
    with pytest.raises(FileExistsError):run(paths,c)
    with pytest.raises(ValueError):read_whole_furanose_control(paths[-1])
    moved=original.rename(tmp_path/'moved');control=moved/'control';before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):
        assert read_base_anchored_furanose_control(control)==q
    assert not original.exists() and snapshot(moved)==before
    selection=control/'selection.json';s=json.loads(selection.read_text());s['base_frame_roles']=['N1','C6','C2'];selection.write_text(json.dumps(s))
    receipt=control/'receipt.json';r=json.loads(receipt.read_text());r['files']['selection.json']=_digest(selection);receipt.write_text(json.dumps(r))
    with pytest.raises(ValueError):read_base_anchored_furanose_control(control)


def ordinary_three_site_frame(tmp_path):
    """Three asymmetric-unit neighbours with gaps in residue numbering."""
    paths, explicit = inputs(tmp_path, bridged=True)
    tetrahedron = {"P": (0,0,0), "OP1": (-.5,1.4,0), "OP2": (-.5,-.7,1.212),
                   "O5'": (1.6,0,0), "O3'": (5,0,0)}
    residues = {10: (2,"X01"), 11: (17,"Z99"), 12: (41,"X02")}
    lines = []
    for line in paths[4].read_text().splitlines(keepends=True):
        if not line.startswith("ATOM  "):
            lines.append(line)
            continue
        old = int(line[22:26])
        name = line[12:16].strip()
        if old not in residues or (old == 10 and name in {"P","OP1","OP2"}):
            continue
        number, code = residues[old]
        line = line[:17] + f"{code:>3} A{number:4d}" + line[26:]
        if name in tetrahedron:
            xyz = [v + (old-10)*s for v,s in zip(tetrahedron[name], (5.53,.76,1.308))]
            line = line[:30] + "".join(f"{v:8.3f}" for v in xyz) + line[54:]
        lines.append(line)
    paths[4].write_text("".join(lines))
    return paths, explicit["ports"]["phosphate"]["leaving_atom"]


def test_placement_derives_linked_partners_from_ordinary_frame_and_replays_after_move(tmp_path):
    from nasolve.cif_whole_furanose import (prepare_base_anchored_furanose_from_model,
                                            read_base_anchored_furanose_control)
    from tests.test_cif_model_context import report
    original = tmp_path / "original"; original.mkdir()
    paths, leaving = ordinary_three_site_frame(original)
    args = dict(code="Z99", site="A:17", leaving_atom=leaving,
                base_frame_roles=["N1","C2","C6"], postmr_report=report())
    placed = prepare_base_anchored_furanose_from_model(*paths, **args)
    ports = placed["context"]["ports"]
    assert ports["phosphate"]["partner"] == dict(site="A:2",component="X01",atom_id="O3'")
    assert ports["alcohol"]["partner"] == dict(site="A:41",component="X02",atom_id="P")
    assert ports["phosphate"]["leaving_atom"] == leaving
    assert placed["status"] == "PLACED_FOR_LINK_REVIEW"
    moved = original.rename(tmp_path/"moved") / paths[-1].name
    with patch("subprocess.Popen", side_effect=AssertionError("unexpected process")):
        assert read_base_anchored_furanose_control(moved) == placed
    # Rehashing a false partner still fails against the frozen ordinary model.
    from nasolve.cif_fana_component import _digest
    context = moved/"context.json"
    edited = json.loads(context.read_bytes()); edited["ports"]["phosphate"]["partner"]["site"] = "A:41"
    context.write_text(json.dumps(edited))
    receipt = moved/"receipt.json"; saved = json.loads(receipt.read_bytes())
    saved["files"]["context.json"] = _digest(context); receipt.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="ordinary"):
        read_base_anchored_furanose_control(moved)


@pytest.mark.parametrize("site", ["A:2","A:41","A:3"])
def test_ordinary_placement_requires_two_observed_internal_links(tmp_path, site):
    from nasolve.cif_whole_furanose import prepare_base_anchored_furanose_from_model
    from tests.test_cif_model_context import report
    paths, leaving = ordinary_three_site_frame(tmp_path)
    with pytest.raises(ValueError, match="internal|absent"):
        prepare_base_anchored_furanose_from_model(*paths, code="Z99", site=site,
            leaving_atom=leaving, base_frame_roles=["N1","C2","C6"], postmr_report=report())
    assert not paths[-1].exists()


def test_named_ordinary_leaving_atom_cannot_remove_a_retained_phosphate_oxygen(tmp_path):
    from nasolve.cif_whole_furanose import prepare_base_anchored_furanose_from_model
    from tests.test_cif_model_context import report
    paths, _ = ordinary_three_site_frame(tmp_path)
    with pytest.raises(ValueError, match="retained phosphate oxygen"):
        prepare_base_anchored_furanose_from_model(*paths, code="Z99", site="A:17",
            leaving_atom="OP2", base_frame_roles=["N1", "C2", "C6"], postmr_report=report())
    assert not paths[-1].exists()


def test_ordinary_placement_checks_host_file_before_parsing_coordinates(tmp_path):
    from nasolve.cif_whole_furanose import prepare_base_anchored_furanose_from_model
    from tests.test_cif_model_context import report
    paths, leaving = ordinary_three_site_frame(tmp_path)
    invalid = tmp_path / "invalid.pdb"
    invalid.write_bytes(b"\xff")
    linked = tmp_path / "linked.pdb"
    linked.symlink_to(invalid)
    with pytest.raises(ValueError, match="regular site artifact"):
        prepare_base_anchored_furanose_from_model(*paths[:4], linked, paths[-1], code="Z99",
            site="A:17", leaving_atom=leaving, base_frame_roles=["N1", "C2", "C6"], postmr_report=report())
    assert not paths[-1].exists()


def test_ordinary_placement_can_use_declared_phosphate_leaving_flag(tmp_path):
    from nasolve.cif_whole_furanose import prepare_base_anchored_furanose_from_model, read_base_anchored_furanose_control
    from tests.test_cif_model_context import report
    paths, leaving = ordinary_three_site_frame(tmp_path)
    args = dict(code="Z99", site="A:17", base_frame_roles=["N1","C2","C6"], postmr_report=report())
    inferred = prepare_base_anchored_furanose_from_model(*paths, **args)
    declared = tmp_path/"explicit"
    explicit = prepare_base_anchored_furanose_from_model(*paths[:-1], declared, leaving_atom=leaving, **args)
    assert inferred["context"] == explicit["context"]
    assert inferred["phosphate_leaving_atom"] == {"atom":leaving, "source":"_chem_comp_atom.pdbx_leaving_atom_flag"}
    assert (paths[-1]/"model.pdb").read_bytes() == (declared/"model.pdb").read_bytes()
    assert read_base_anchored_furanose_control(paths[-1]) == inferred


@pytest.mark.parametrize("defect", [None,"missing flags","unknown neighbour","two flags","retained oxygen","ester","unprotonated","double"])
def test_source_flag_uses_the_bound_graph_and_refuses_disputed_chemistry(tmp_path, defect):
    from nasolve.cif_attachment_profiles import inspect_attachment_profile
    from nasolve.cif_stereochemistry_audit import _values
    from nasolve.cif_whole_furanose import _source_phosphate_leaving_atom
    paths, explicit = inputs(tmp_path, bridged=True, rename=defect!="retained oxygen")
    values = _values(paths[0],"Z99")
    roles = inspect_attachment_profile(paths[0],"Z99",workbook=paths[3])["bindings"]
    ids = values["_chem_comp_atom.atom_id"]
    flag = "_chem_comp_atom.pdbx_leaving_atom_flag"
    leaving = explicit["ports"]["phosphate"]["leaving_atom"]
    if defect is None:
        assert leaving.startswith("X") and _source_phosphate_leaving_atom(values, roles) == leaving
        return
    if defect == "missing flags":
        values.pop(flag)
    elif defect == "retained oxygen":
        values[flag][ids.index(leaving)] = "N"
        values[flag][ids.index("OP2")] = "Y"
    elif defect in ("two flags","unknown neighbour","ester"):
        values[flag][ids.index(roles["five_o"])] = "?" if defect=="unknown neighbour" else "Y"
        if defect=="ester": values[flag][ids.index(leaving)] = "N"
    elif defect == "unprotonated":
        values["_chem_comp_atom.charge"][ids.index(leaving)] = "-1"
    else:
        pairs=zip(values["_chem_comp_bond.atom_id_1"],values["_chem_comp_bond.atom_id_2"])
        index, = [i for i,pair in enumerate(pairs) if set(pair)=={roles["phosphate"],leaving}]
        values["_chem_comp_bond.value_order"][index]="DOUB"
    with pytest.raises(ValueError, match="leaving|retained"):
        _source_phosphate_leaving_atom(values,roles)


def test_host_frame_uses_independent_workbook_atom_names(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values
    from tests.test_cif_stereochemistry_audit import write
    paths,c=inputs(tmp_path,bridged=True)
    v=_values(paths[2],'Z99');mapping={n:'Y'+str(i) for i,n in enumerate(v['_chem_comp_atom.atom_id'])}
    for key in v:
        if 'atom_id' in key:v[key]=[mapping.get(n,n) for n in v[key]]
        if key.endswith('.comp_id') or key=='_chem_comp.id':v[key]=['HST']*len(v[key])
    paths[2]=write(tmp_path/'host.cif',v)
    book=load_workbook(paths[3]);sheet=next(s for s in book.worksheets if s.max_row>1)
    values=[cell.value for cell in sheet[2]]
    values[0]='HST'
    for i,cell in enumerate(sheet[1]):
        if cell.value in {'N1','C2','C5','C6'}:values[i]=mapping[values[i]]
    sheet.append(values);book.save(paths[3]);book.close()
    lines=paths[4].read_text().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line[:6]=='ATOM  ' and line[21:26]=='A  11':
            lines[i]=line[:12]+f"{mapping[line[12:16].strip()]:>4}"+line[16:17]+'HST'+line[20:]
    paths[4].write_text(''.join(lines))
    q=run(paths,c)
    assert q['target_frame_atoms']==['N1','C2','C6']
    assert q['host_frame_atoms']==[mapping[n] for n in q['target_frame_atoms']]
    assert len(q['retained_hands'])==7
