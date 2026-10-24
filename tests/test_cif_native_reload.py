"""Read-only reload attribution; no origin-code or residue exceptions."""
from copy import deepcopy
import pytest
from tests.test_cif_captured_geometry import native


def case():
    before=native();after=deepcopy(before)
    for report,points in [(before,[[0.,0.,0.],[-1.,0.,0.],[3.5,0.,0.],[4.5,0.,0.]]),
                          (after,[[0.,0.,0.],[-1.,0.,0.],[3.1,0.,0.],[4.1,0.,0.]])]:
        for atom,point in zip(report['atoms'],points):atom['xyz']=point
        report['geometry']['sites_cart_exact']=points
        for atom in report['atoms'][2:]:atom['identity']['resseq']='10'
        report['monomer_mappings']={'rows':[{'site':'Z:9','metadata':{}},{'site':'Z:10','metadata':{}}]}
        report['geometry']['custom_proxy_requests']=[]
    def row(indices,**values):return {'i_seqs':indices,'atoms':[before['atoms'][i]['label'] for i in indices],**values}
    stem=row([2,3],distance_ideal=1.,weight=100.,origin_id=0,symmetry_operation=None)
    for r in [before,after]:r['geometry']['proxy_details']['bond_simple'].append(deepcopy(stem));r['geometry']['proxy_counts']['bond_simple']+=1
    after['geometry']['proxy_details']['bond_simple'].append(row([0,2],distance_ideal=2.9,weight=25.,origin_id=37,symmetry_operation=None))
    after['geometry']['proxy_details']['angle'] += [row([1,0,2],angle_ideal=120.,weight=.1,origin_id=37),row([0,2,3],angle_ideal=120.,weight=.1,origin_id=37)]
    for kind in ['angle','bond_simple']:after['geometry']['proxy_counts'][kind]=len(after['geometry']['proxy_details'][kind])
    return before,after


def test_cutoff_consistent_additions_are_explained_without_passing_exact_gate():
    from nasolve.cif_native_reload import audit_native_reload
    a,b=case();original=deepcopy((a,b));r=audit_native_reload(a,b,cutoff=3.4,hydrogen_bond_origin_id=37)
    assert r['classification']=='CUTOFF_CONSISTENT_HBOND_ACTIVATION' and r['status']=='REVIEW'
    assert r['exact_proxy_preservation'] is False and r['added_hydrogen_bonds']==1 and r['associated_angles']==2
    assert r['activations'][0]['before_distance']==3.5 and r['activations'][0]['after_distance']==3.1
    assert (a,b)==original and r['automatic_adoption'] is False


@pytest.mark.parametrize('defect',['changed_target','removal','wrong_origin','no_crossing','unpaired_angle','definition','custom_request','extra_kind','missing_weight','missing_target'])
def test_other_changes_cannot_be_excused_as_conditional_hbonds(defect):
    from nasolve.cif_native_reload import audit_native_reload
    a,b=case();g=b['geometry']
    if defect=='missing_weight':g['proxy_details']['bond_simple'][-1]['weight']=None
    if defect=='missing_target':g['proxy_details']['angle'][-1]['angle_ideal']=None
    if defect=='changed_target':g['proxy_details']['bond_simple'][0]['distance_ideal']=.7
    if defect=='removal':g['proxy_details']['chirality']=[];g['proxy_counts']['chirality']=0
    if defect=='wrong_origin':g['proxy_details']['bond_simple'][-1]['origin_id']=38
    if defect=='no_crossing':
        a['atoms'][2]['xyz'][0]=3.3;a['geometry']['sites_cart_exact'][2][0]=3.3
    if defect=='unpaired_angle':g['proxy_details']['angle'].pop();g['proxy_counts']['angle']-=1
    if defect=='definition':b['monomer_mappings']['rows'][0]['metadata']['changed']=True
    if defect=='custom_request':g['custom_proxy_requests'].append({'changed':True})
    if defect=='extra_kind':g['proxy_details']['dihedral']=[{'unexpected':'term'}];g['proxy_counts']['dihedral']=1
    r=audit_native_reload(a,b,cutoff=3.4,hydrogen_bond_origin_id=37)
    assert r['classification']=='UNEXPLAINED_NATIVE_DRIFT' and r['status']=='REVIEW' and not r['exact_proxy_preservation']


def test_saved_vector_equivalence_keeps_roundoff_and_native_energy_basis_explicit():
    from nasolve.cif_native_reload import audit_saved_endpoint_readback
    a,b=case();points=deepcopy(b['geometry']['sites_cart_exact']);points[0][0]=.000123
    b['atoms'][0]['xyz'][0]=1e-15;b['geometry']['sites_cart_exact'][0][0]=1e-15
    fixed={'status':'REVIEW','constraint_signature_before':'same','constraint_signature_after':'same',
           'final_sites_cart':points,'serialized':{'target':12.3}}
    r=audit_saved_endpoint_readback(a,b,fixed)
    assert r['status']=='MATCH_AT_PDB_PRECISION' and r['native_float_max_difference']==1e-15
    assert r['recorded_fixed_manager_pdb_evaluation']=={'target':12.3} and r['new_native_execution']=='NOT_RUN'
    b['atoms'][0]['xyz'][0]=.002;b['geometry']['sites_cart_exact'][0][0]=.002
    assert audit_saved_endpoint_readback(a,b,fixed)['status']=='REVIEW'


@pytest.mark.parametrize('defect',['missing','duplicate','wrong_scope','negative'])
def test_cutoff_reader_requires_one_explicit_normalized_native_value(defect):
    from nasolve.cif_native_reload import native_hbond_cutoff
    text='pdb_interpretation {\n secondary_structure {\n  nucleic_acid {\n hbond_distance_cutoff = 3.4\n }\n }\n}\n'
    if defect=='missing':text=text.replace('hbond_distance_cutoff = 3.4','other = 3.4')
    if defect=='duplicate':text=text.replace('hbond_distance_cutoff = 3.4','hbond_distance_cutoff = 3.4\nhbond_distance_cutoff = 3.4')
    if defect=='wrong_scope':text=text.replace('nucleic_acid','protein')
    if defect=='negative':text=text.replace('3.4','-1')
    with pytest.raises(ValueError):native_hbond_cutoff(text)
