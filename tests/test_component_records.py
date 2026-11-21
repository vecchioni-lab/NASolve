from copy import deepcopy
import pytest
from restraints.residue_library import load_residue_records


def test_ordinary_5pc_definition_accepts_equivalent_aliases_without_workbook_edit():
    from nasolve.curated_ligands import ligand_definition
    assert ligand_definition('5PC').parent_code == 'DC'


@pytest.mark.parametrize('change',['description','role','unknown_role','category','sugar','phosphate','attachment','sheet'])
def test_shared_resolution_preserves_all_operational_roles_and_context(change):
    from nasolve.component_records import resolve_component_record
    first=deepcopy(next(r for r in load_residue_records() if r['Ligand code']=='PDU'))
    first['Ligand code']='Q17';second=deepcopy(first)
    second.update(Name='A descriptive alias',Notes='test',**{'C5-mod':'a description'})
    if change=='role':second['O4']='N3'
    if change=='unknown_role':second['UNRECOGNIZED_ROLE']='X9'
    if change=='category':second['Base Analog']='C'
    if change=='sugar':second['Sugar Type']='RNA'
    if change=='phosphate':second['Phosphate']='DIFFERENT'
    if change=='attachment':second['Glycosidic atom']='DIFFERENT'
    if change=='sheet':second['Source sheet']='DIFFERENT'
    before=deepcopy([first,second])
    if change=='description':
        selected,proof=resolve_component_record([first,second],'Q17')
        assert selected['O4']==first['O4'] and proof['matching_records']==2
        assert proof['resolution']=='EQUIVALENT_ROLE_RECORDS'
    else:
        with pytest.raises(ValueError,match='unambiguous'):resolve_component_record([first,second],'Q17')
    assert [first,second]==before


def test_ordinary_narestraints_loader_collapses_only_required_equivalent_records():
    from nasolve.postmr import _patch_narestraints_records
    records=load_residue_records();before=deepcopy(records)
    result,events=_patch_narestraints_records(records,{'5PC'})
    assert len([r for r in result if r['Ligand code']=='5PC'])==1
    assert any(r['ligand_code']=='5PC' and r['scope']=='process-local' for r in events)
    assert records==before
    unchanged,_=_patch_narestraints_records(records,set())
    assert unchanged==records


def test_ordinary_narestraints_loader_refuses_conflicting_aliases():
    from nasolve.postmr import _patch_narestraints_records,PostMRPreparationError
    records=deepcopy(load_residue_records())
    matches=[r for r in records if r['Ligand code']=='5PC'];matches[-1]['O2']='DIFFERENT'
    with pytest.raises(PostMRPreparationError,match='unambiguous'):_patch_narestraints_records(records,{'5PC'})
