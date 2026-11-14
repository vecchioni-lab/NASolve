"""Generic source/native graph recovery selection; no component exceptions."""
import hashlib

import pytest

from tests.test_cif_fragment_restoration import fixture


def case(tmp_path):
    from nasolve.cif_linked_preparation import _render
    raw,model,parent,n,_=fixture(tmp_path)
    definition=n['monomer_mappings']['rows'][0]['metadata']['effective_definition']
    values={'data_':'comp_ZZZ','_chem_comp.id':['ZZZ'],'_chem_comp.type':['DNA LINKING'],'_chem_comp.group':['DNA']}
    for field in ['atom_id','type_symbol']:
        values['_chem_comp_atom.'+field]=[r[field] for r in definition['atoms']]
    values['_chem_comp_atom.comp_id']=['ZZZ']*len(definition['atoms'])
    for field in ['atom_id_1','atom_id_2','type']:
        values['_chem_comp_bond.'+field]=[r[field] for r in definition['bonds']]
    source=tmp_path/'opaque-resource.cif';source.write_text(_render(values,'ZZZ'))
    audit={'inputs':[{'input_index':7,'role':'dictionary','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'size':source.stat().st_size}],
        'components':[{'component_id':'ZZZ','input_index':7}]}
    definition['bonds'][7]['type']='aromatic'
    n['monomer_mappings']['rows'][0]['chem_mod_ids']={'status':'RECORDED','ids':[]}
    return n,model,source,audit


def test_source_hash_and_graph_select_recovery_without_name_or_component_allowlist(tmp_path):
    from nasolve.cif_effective_source_recovery import plan_effective_source_recovery
    n,model,source,audit=case(tmp_path);before=source.read_bytes()
    plan=plan_effective_source_recovery(n,model,audit,{'declared_resource':source},['Z:9'])
    assert plan['recovery_codes']==['ZZZ'] and plan['blocked']==[]
    assert plan['selected'][0]['source_resource']=='declared_resource'
    assert plan['selected'][0]['sites']==['Z:9'] and source.read_bytes()==before


@pytest.mark.parametrize('defect',['changed_source','missing_source','ambiguous_source','invalid_source_graph','prior_modifier','source_component_mismatch'])
def test_unverified_or_uncomposable_source_cannot_trigger_recovery(tmp_path,defect):
    from nasolve.cif_effective_source_recovery import plan_effective_source_recovery
    n,model,source,audit=case(tmp_path);resources={'resource':source}
    if defect=='changed_source':source.write_text(source.read_text()+'# changed\n')
    if defect=='missing_source':resources={}
    if defect=='ambiguous_source':
        other=tmp_path/'second.cif';other.write_bytes(source.read_bytes());resources['second']=other
    if defect=='invalid_source_graph':
        source.write_text(source.read_text().replace('single','aromatic'));audit['inputs'][0].update(sha256=hashlib.sha256(source.read_bytes()).hexdigest(),size=source.stat().st_size)
    if defect=='prior_modifier':n['monomer_mappings']['rows'][0]['chem_mod_ids']['ids']=['PRESERVE_ME']
    if defect=='source_component_mismatch':audit['components'][0]['component_id']='QQQ'
    plan=plan_effective_source_recovery(n,model,audit,resources,['Z:9'])
    assert plan['recovery_codes']==[] and plan['blocked']


def test_supported_native_graph_needs_no_regeneration(tmp_path):
    from nasolve.cif_effective_source_recovery import plan_effective_source_recovery
    n,model,source,audit=case(tmp_path);n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][7]['type']='single'
    plan=plan_effective_source_recovery(n,model,audit,{'resource':source},['Z:9'])
    assert plan['recovery_codes']==[] and plan['blocked']==[] and plan['unchanged_sites']==['Z:9']


def test_declared_source_type_is_case_insensitive(tmp_path):
    from nasolve.cif_effective_source_recovery import plan_effective_source_recovery
    n,model,source,audit=case(tmp_path)
    source.write_text(source.read_text().replace('DNA LINKING','DNA linking'))
    audit['inputs'][0].update(sha256=hashlib.sha256(source.read_bytes()).hexdigest(),size=source.stat().st_size)
    assert plan_effective_source_recovery(n,model,audit,{'resource':source},['Z:9'])['recovery_codes']==['ZZZ']


@pytest.mark.parametrize(('status','name','contradictions','expected'),[
    ('PASS','any',[],True),('UNSUPPORTED','effective-site-formal-charges:Z:9',[],True),
    ('UNSUPPORTED','effective-site-formal-charges:Z:9',[{'mismatch':True}],False),
    ('UNSUPPORTED','different-check',[],False),('REVIEW','target',[],False)])
def test_only_explicit_unavailable_charge_readback_can_continue_a_diagnostic(status,name,contradictions,expected):
    from nasolve.cif_effective_source_recovery import mechanics_can_continue
    assert mechanics_can_continue({'checks':[{'check':name,'status':status,'contradictions':contradictions}]}) is expected
    assert not mechanics_can_continue({'checks':[]})
