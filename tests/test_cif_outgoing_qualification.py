"""New outgoing modifiers must preserve the captured baseline and old gates."""
from copy import deepcopy
from pathlib import Path
import runpy

import pytest


def case(tmp_path):
    helper=runpy.run_path(str(Path(__file__).with_name('test_cif_terminal_qualification.py')))['case']
    before,after,prepared,links,ends,projections=helper(tmp_path)
    for native in [before,after]:
        for row in native['monomer_mappings']['rows']:
            row['chem_mod_ids']={'status':'RECORDED','ids':['existing'] if row['site']=='A:2' else []}
    captured=deepcopy(before)
    after['monomer_mappings']['rows'][1]['chem_mod_ids']['ids'].append('new_outgoing')
    prepared[0]['sites'][0].update(modification_id='new_outgoing',prior_modification_ids=['existing'],
        outgoing_correction={'oxygen':"O3'",'after_type':'OC2'})
    return before,after,prepared,links,ends,projections,captured


def test_complete_explicit_fake_evidence_retains_scoped_mechanics_only(tmp_path):
    from nasolve.cif_outgoing_qualification import qualify_outgoing_bundle
    *args,captured=case(tmp_path)
    result=qualify_outgoing_bundle(*args,captured_baseline=captured)
    assert result['status']=='OUTGOING_BUNDLE_MECHANICS_PASS'
    assert result['automatic_adoption'] is False and result['achieved_model_geometry']=='NOT_RUN'
    assert next(c for c in result['checks'] if c['check']=='exact-native-site-modification-ids')['status']=='PASS'


@pytest.mark.parametrize('defect',['lost_old_id','lost_new_id','new_id_wrong_site','unselected_id',
    'fresh_baseline_definition','captured_proxy_changed','missing_proxy_detail','formal_unavailable'])
def test_matching_proxy_counts_cannot_hide_registration_or_replay_defects(tmp_path,defect):
    from nasolve.cif_outgoing_qualification import qualify_outgoing_bundle
    before,after,prepared,links,ends,projections,captured=case(tmp_path)
    rows=after['monomer_mappings']['rows']
    if defect=='lost_old_id':rows[1]['chem_mod_ids']['ids'].remove('existing')
    elif defect=='lost_new_id':rows[1]['chem_mod_ids']['ids'].remove('new_outgoing')
    elif defect=='new_id_wrong_site':
        rows[1]['chem_mod_ids']['ids'].remove('new_outgoing');rows[0]['chem_mod_ids']['ids'].append('new_outgoing')
    elif defect=='unselected_id':rows[0]['chem_mod_ids']['ids'].append('unexpected')
    elif defect=='fresh_baseline_definition':before['monomer_mappings']['rows'][0]['metadata']['group']='wrong'
    elif defect=='captured_proxy_changed':captured['geometry']['proxy_details']['bond_simple'][0]['weight']*=2
    elif defect=='missing_proxy_detail':captured['geometry']['proxy_details']['bond_simple']=None
    else:rows[1]['metadata']['effective_definition']['atoms'][0]['charge']=None
    result=qualify_outgoing_bundle(before,after,prepared,links,ends,projections,captured_baseline=captured)
    assert result['status']=='REVIEW'
    if defect=='formal_unavailable':
        assert next(c for c in result['checks'] if c['check']=='effective-site-formal-charges:A:2')['status']=='UNSUPPORTED'


def test_unaffected_projection_proxies_and_reviewed_torsion_gates_stay_active(tmp_path):
    from nasolve.cif_outgoing_qualification import qualify_outgoing_bundle
    before,after,prepared,links,ends,projections,captured=case(tmp_path)
    after['monomer_mappings']['rows'][1]['metadata']['effective_definition']['bonds'][0]['value_dist_neutron']=1.6
    result=qualify_outgoing_bundle(before,after,prepared,links,ends,projections,captured_baseline=captured)
    assert next(c for c in result['checks'] if c['check']=='projected-native-bonds:A:2')['status']=='REVIEW'
