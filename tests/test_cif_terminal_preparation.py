"""Explicit synthetic native targets; no installed chemistry is asserted here."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy

import pytest


def resource_fixture(tmp_path, *, hydrogen="HX5'"):
    directory=tmp_path/'resources';directory.mkdir()
    bond={'atom_id_1':"O5'",'atom_id_2':hydrogen,'type':'single',
          'value_dist':.91,'value_dist_esd':.03,'value_dist_neutron':1.03}
    angle={'atom_id_1':"C5'",'atom_id_2':"O5'",'atom_id_3':hydrogen,
           'value_angle':117.,'value_angle_esd':4.}
    native={'schema_version':1,'policy_id':'cif-installed-terminal-resources-v2','status':'REVIEW',
        'modifications':{'5*END':{'metadata':{'id':'5*END','group_id':'DNA/RNA'},
            'atoms':[{'function':'delete','atom_id':n} for n in ['P','OP1','OP2']]+[
                {'function':'change','atom_id':"O5'",'new_atom_id':"O5'",'new_type_symbol':'',
                 'new_type_energy':'OH_TEST','new_partial_charge':-.21},
                {'function':'add','atom_id':'','new_atom_id':hydrogen,'new_type_symbol':'H',
                 'new_type_energy':'H_TEST','new_partial_charge':.14}],
            'bonds':[{'function':'add',**{('new_'+k if k in {'type','value_dist','value_dist_esd','value_dist_neutron'} else k):v for k,v in bond.items()}}],
            'angles':[{'function':'add',**{('new_'+k if k.startswith('value_') else k):v for k,v in angle.items()}}],
            'torsions':[],'chirality':[],'plane_atoms':[]}},
        'canonical_control':{'code':'DG','base_preserved':True,'applied_modification_ids':['5*END'],
            'base':{'metadata':{'group':'DNA'},'atoms':[]},
            'effective':{'metadata':{'group':'DNA'},'atoms':[
                {'atom_id':"O5'",'type_symbol':'O','type_energy':'OH_TEST','partial_charge':-.21},
                {'atom_id':hydrogen,'type_symbol':'H','type_energy':'H_TEST','partial_charge':.14}],
                'bonds':[bond],'angles':[angle]}},
        'source_files':[{'historical_path':'/fake/native.cif','sha256':'a'*64,'size':123,'preserved_after_capture':True}],
        'api_sources':[{'module':'fake.native','sha256':'b'*64}]}
    report=directory/'native_resources.json';report.write_text(json.dumps(native))
    receipt={'schema_version':1,'audit_kind':'cif_native_terminal_resource_inventory',
        'policy_id':native['policy_id'],'status':'REVIEW','native_resources':native,
        'execution':{'status':'COMPLETED','returncode':0},'phenix_version':'fake-test',
        'outputs':[{'anchor':'native_directory','path':report.name,'size':report.stat().st_size,
                    'sha256':hashlib.sha256(report.read_bytes()).hexdigest()}]}
    path=directory/'resources_receipt.json';path.write_text(json.dumps(receipt))
    return path,native


def inputs(tmp_path):
    helper=runpy.run_path(str(Path(__file__).with_name('test_cif_linked_preparation.py')))['fixture']
    return helper(tmp_path)


def test_native_fragment_changes_only_the_declared_free_end(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component,component_values,hydrogen_neighbors
    from nasolve.cif_terminal_preparation import prepare_terminal_component
    source,numerical,model,contexts=inputs(tmp_path)
    resource,_=resource_fixture(tmp_path)
    before=[p.read_bytes() for p in (source,numerical,model,resource)]
    old=prepare_linked_component(source,numerical,model,contexts,tmp_path/'old',code='ZZZ')
    result=prepare_terminal_component(source,numerical,model,contexts,resource,tmp_path/'new',code='ZZZ')
    assert result['sites'][0]==old['sites'][0] and result['sites'][2]==old['sites'][2]
    assert (tmp_path/'new/base_dictionary.cif').read_bytes()==(tmp_path/'old/base_dictionary.cif').read_bytes()
    terminal=result['sites'][1]
    assert terminal['expected_energy_types']["O5'"]=='OH_TEST'
    assert terminal['expected_energy_types']["HX5'"]=='H_TEST'
    assert terminal['expected_formal_charges']["HX5'"]=='?'
    assert terminal['expected_hydrogen_attachments']["HX5'"]==["O5'"]
    assert terminal['modification_id']!=old['sites'][1]['modification_id']
    projected=component_values(tmp_path/'new/projected_B_1.cif','ZZZ')
    assert hydrogen_neighbors(projected,"O5'")==["HX5'"]
    text=(tmp_path/'new/site_modifications.cif').read_text()
    assert '_chem_mod_bond.new_value_dist_neutron' in text and '1.03' in text
    assert '_chem_mod_angle.new_value_angle' in text and '117.0' in text
    assert result['terminal_resource']['added_hydrogen_formal_charge']=='UNASSESSED'
    assert result['automatic_adoption'] is False and result['native_validation']=='NOT_RUN'
    assert [p.read_bytes() for p in (source,numerical,model,resource)]==before


@pytest.mark.parametrize('defect',['report_changed','failed_execution','unsupported','source_changed','collision'])
def test_unreviewed_or_changed_resource_cannot_publish_a_terminal_candidate(tmp_path,defect):
    from nasolve.cif_terminal_preparation import prepare_terminal_component
    source,numerical,model,contexts=inputs(tmp_path)
    resource,_=resource_fixture(tmp_path,hydrogen='keepH' if defect=='collision' else "HX5'")
    if defect=='report_changed':(resource.parent/'native_resources.json').write_text('{}')
    elif defect in {'failed_execution','unsupported','source_changed'}:
        r=json.loads(resource.read_text())
        if defect=='failed_execution':r['execution']['returncode']=2
        elif defect=='unsupported':r['status']='UNSUPPORTED'
        else:r['native_resources']['source_files'][0]['preserved_after_capture']=False
        resource.write_text(json.dumps(r))
    with pytest.raises(ValueError):
        prepare_terminal_component(source,numerical,model,contexts,resource,tmp_path/'out',code='ZZZ')
    assert not (tmp_path/'out').exists()


def test_an_unrequested_terminal_adaptation_is_refused(tmp_path):
    from nasolve.cif_terminal_preparation import prepare_terminal_component
    source,numerical,model,contexts=inputs(tmp_path)
    resource,_=resource_fixture(tmp_path)
    contexts=[c for c in contexts if c['site']!='B:1']
    model.write_text(''.join(line for line in model.read_text().splitlines(keepends=True)
                             if not line.startswith(('ATOM  ','HETATM')) or line[21]!='B'))
    with pytest.raises(ValueError,match='free_OH'):
        prepare_terminal_component(source,numerical,model,contexts,resource,tmp_path/'out',code='ZZZ')
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',['element','energy','sigma'])
def test_internally_hashed_but_unsupported_fragment_still_requires_review(tmp_path,defect):
    from nasolve.cif_terminal_preparation import prepare_terminal_component
    source,numerical,model,contexts=inputs(tmp_path)
    resource,_=resource_fixture(tmp_path)
    receipt=json.loads(resource.read_text());native=receipt['native_resources'];mod=native['modifications']['5*END']
    if defect=='element':mod['atoms'][3]['new_type_symbol']='N'
    elif defect=='energy':mod['atoms'][4]['new_type_energy']='?'
    else:mod['bonds'][0]['new_value_dist_esd']=-.03
    report=resource.parent/'native_resources.json';report.write_text(json.dumps(native))
    receipt['outputs'][0].update(sha256=hashlib.sha256(report.read_bytes()).hexdigest(),size=report.stat().st_size)
    resource.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):prepare_terminal_component(source,numerical,model,contexts,resource,tmp_path/'out',code='ZZZ')
    assert not (tmp_path/'out').exists()
