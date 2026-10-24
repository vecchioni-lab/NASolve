"""Synthetic controls exercise graph selection and preserve canonical backbone."""
from pathlib import Path
import pytest

ROOT=Path(__file__).parents[1]


@pytest.mark.parametrize('code',['PDU','5PC'])
def test_public_control_grafts_only_connected_base_and_preserves_backbone(tmp_path,code):
    from nasolve.cif_linked_control import prepare_linked_control_models
    from nasolve.cif_construction_provenance import _pdb_inventory
    from nasolve.cif_fragment_restoration import _SCAFFOLD
    source=ROOT/'tests/fixtures/public_ccd'/f'{code}.cif';frame=ROOT/'MR_frames/5W6W/A_T.pdb'
    before=source.read_bytes(),frame.read_bytes();r=prepare_linked_control_models(frame,source,code,tmp_path/'out')
    model=_pdb_inventory(tmp_path/'out/candidate.pdb');original=_pdb_inventory(frame)
    assert {k[:2] for k in model}=={('A','1'),('A','2'),('A','3')}
    assert all(a['code']==code for k,a in model.items() if k[:2]==('A','2'))
    assert all(model[k]['xyz']==a['xyz'] for k,a in original.items() if k in model and (k[:2]!=('A','2') or k[-1] in _SCAFFOLD))
    assert not any(a['element'] in {'H','D'} or k[-1]=='OP3' for k,a in model.items())
    assert r['expected_links']==[['A:1','A:2'],['A:2','A:3']]
    assert not r['automatic_adoption'] and r['backbone_and_flanks_preserved']
    assert (source.read_bytes(),frame.read_bytes())==before


def test_bridged_sugar_remains_outside_standard_dna_graft(tmp_path):
    from nasolve.cif_linked_control import prepare_linked_control_models
    with pytest.raises(ValueError):
        prepare_linked_control_models(ROOT/'MR_frames/5W6W/A_T.pdb',ROOT/'tests/fixtures/public_ccd/ATL.cif','ATL',tmp_path/'out')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',['existing','symlink','bad_code','missing_site','phosphorylated_first','noncanonical','altered_graph','missing_coordinate'])
def test_control_preparation_does_not_guess_unsupported_inputs(tmp_path,defect):
    from nasolve.cif_linked_control import prepare_linked_control_models
    from nasolve.cif_stereochemistry_audit import _values
    from nasolve.cif_linked_preparation import _render
    source=tmp_path/'inputs/source.cif';source.parent.mkdir();source.write_bytes((ROOT/'tests/fixtures/public_ccd/PDU.cif').read_bytes())
    frame=tmp_path/'inputs/frame.pdb';frame.write_bytes((ROOT/'MR_frames/5W6W/A_T.pdb').read_bytes());out=tmp_path/'out';code='PDU'
    if defect=='existing':out.mkdir()
    if defect=='symlink':out.symlink_to(tmp_path/'inputs',target_is_directory=True)
    if defect=='bad_code':code='BAD/CODE'
    if defect=='missing_site':frame.write_text(''.join(line for line in frame.read_text().splitlines(keepends=True) if not (line.startswith('ATOM') and line[21:26]=='A   2')))
    if defect=='phosphorylated_first':
        line=next(line for line in frame.read_text().splitlines() if line.startswith('ATOM') and line[12:16].strip()=='P')
        frame.write_text(frame.read_text()+line[:22]+'   1'+line[26:]+'\n')
    if defect=='noncanonical':frame.write_text(frame.read_text().replace(' DA A   2',' ATL A   2'))
    if defect in {'altered_graph','missing_coordinate'}:
        v=_values(source,'PDU')
        if defect=='altered_graph':v['_chem_comp_bond.atom_id_2'][0]='P'
        else:v['_chem_comp_atom.pdbx_model_cartn_x_ideal'][0]='?'
        source.write_text(_render(v,'PDU'))
    with pytest.raises((ValueError,FileExistsError)):
        prepare_linked_control_models(frame,source,code,out)


def test_incomplete_native_evidence_remains_review(tmp_path):
    from nasolve.cif_linked_control import qualify_linked_control
    r=qualify_linked_control({}, {},tmp_path/'absent.pdb',{},tmp_path/'absent.cif','ZZZ')
    assert r['status']=='REVIEW' and not r['automatic_adoption'] and not r['requires_cif_review']
