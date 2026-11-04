"""Explicit isolated evidence can bridge legacy DNA metadata; defaults stay strict."""
from hashlib import sha256
from pathlib import Path
import pytest
from tests.test_cif_linked_preparation import fixture


def prepared_inputs(tmp_path):
    from nasolve.cif_linked_preparation import component_values,_render
    from nasolve.cif_candidate_usability import reassess_complete_candidate,POLICY_ID
    source,numerical,model,contexts=fixture(tmp_path)
    for p in [source,numerical]:
        v=component_values(p,'ZZZ');v.pop('_chem_comp.type');v['_chem_comp.group']=['DNA'];p.write_text(_render(v,'ZZZ'))
    q={'policy_id':POLICY_ID,'component':'ZZZ','native_usable':True,'scope':'ISOLATED_COMPONENT_ONLY',
       'candidate_sha256':sha256(numerical.read_bytes()).hexdigest(),'checks':{'explicit_fake_native_evidence':True},
       'source_assessment':reassess_complete_candidate(source,numerical,'ZZZ')}
    return source,numerical,model,contexts,q


@pytest.mark.parametrize('defect',['none','candidate','source','unusable','check','policy','scope','empty_checks','component'])
def test_qualified_legacy_group_requires_bound_source_and_candidate(tmp_path,defect):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts,q=prepared_inputs(tmp_path)
    if defect=='candidate':q['candidate_sha256']='0'*64
    if defect=='source':q['source_assessment']['finished_stereo']['source_sha256']='0'*64
    if defect=='unusable':q['native_usable']=False
    if defect=='check':q['checks']['explicit_fake_native_evidence']=False
    if defect=='policy':q['policy_id']='UNVERIFIED'
    if defect=='scope':q['scope']='LINKED'
    if defect=='empty_checks':q['checks']={}
    if defect=='component':q['component']='OTHER'
    out=tmp_path/'out'
    if defect!='none':
        with pytest.raises(ValueError):prepare_linked_component(source,numerical,model,contexts,out,code='ZZZ',native_qualification=q)
        assert not out.exists()
    else:
        r=prepare_linked_component(source,numerical,model,contexts,out,code='ZZZ',native_qualification=q)
        assert r['isolated_native_qualification']['candidate_sha256']==q['candidate_sha256']
        assert r['policy_id']=='cif-source-preserving-linked-sites-v2'
        assert r['source_preserved'] and not r['automatic_adoption']


def test_unqualified_legacy_group_does_not_change_existing_default(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts,_=prepared_inputs(tmp_path)
    with pytest.raises(ValueError,match='DNA LINKING'):
        prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ')


def test_candidate_corruption_cannot_be_hidden_by_old_qualification(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    source,numerical,model,contexts,q=prepared_inputs(tmp_path)
    numerical.write_text(numerical.read_text().replace('OH1','CH3'))
    with pytest.raises(ValueError):prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ',native_qualification=q)


@pytest.mark.parametrize('sign',['both','positive'])
def test_volume_omission_bridge_keeps_fixed_hands_required(tmp_path,sign):
    from nasolve.cif_linked_preparation import prepare_linked_component,component_values,_render
    from nasolve.cif_candidate_usability import reassess_complete_candidate
    source,numerical,model,contexts,q=prepared_inputs(tmp_path)
    v=component_values(source,'ZZZ');row=dict(comp_id='ZZZ',id='volume',atom_id_centre='P',atom_id_1='OP1',atom_id_2='OP2',atom_id_3="O5'",volume_sign=sign)
    v.update({'_chem_comp_chir.'+k:[x] for k,x in row.items()});source.write_text(_render(v,'ZZZ'));q['source_assessment']=reassess_complete_candidate(source,numerical,'ZZZ')
    if sign=='positive':
        with pytest.raises(ValueError):prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ',native_qualification=q)
    else:
        r=prepare_linked_component(source,numerical,model,contexts,tmp_path/'out',code='ZZZ',native_qualification=q)
        assert r['candidate_inspection']['automatic_adoption'] is False
        assert r['candidate_reassessment']['unoriented_volume_omissions'][0]['center']=='P'
