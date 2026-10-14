"""Counts cannot conceal changed custom targets, weights or native site atoms."""
from copy import deepcopy

import pytest

from nasolve.cif_linked_qualification import qualify_linked_bundle


def native_case():
    atoms=[{'i_seq':i,'atom_id':name,'label':str(i),'xyz':[float(i),0.,0.],
            'identity':{'model_id':'','chain_id':'A','resseq':str(resid),'icode':'','resname':code,'altloc':''}}
           for i,(resid,code,name) in enumerate([(1,'DG',"O3'"),(2,'IGU','P'),(2,'IGU',"O3'"),
                                                (3,'DG','P'),(2,'IGU','OP2'),(2,'IGU','keepH')])]
    links=[{'i_seqs':[0,1],'atoms':['0','1'],'distance_ideal':1.607,'weight':1/.012**2},
           {'i_seqs':[2,3],'atoms':['2','3'],'distance_ideal':1.607,'weight':1/.012**2}]
    custom={'i_seqs':[0,2],'atoms':['0','2'],'distance_ideal':2.8,'weight':25.}
    plane={'i_seqs':[0,1,2],'atoms':['0','1','2'],'weights':[25.,25.,25.]}
    parallel={'i_seqs':[0,1,2],'j_seqs':[3,4,5],'atoms':['0','1','2'],'j_atoms':['3','4','5'],
              'weight':100.,'target_angle_deg':0.}
    targets=['P',"O3'",'OP2','keepH']
    definition={'atoms':[{'atom_id':name,'type_symbol':'H' if name=='keepH' else 'O',
                         'type_energy':'OC2' if name=="O3'" else 'X','charge':'0'} for name in targets],
                'bonds':[{'atom_id_1':'OP2','atom_id_2':'keepH'}],'angles':[],'torsions':[],
                'chirality':[],'plane_atoms':[]}
    mappings=[{'site':site,'metadata':{'group':'DNA','atom_ids':ids,'effective_definition':definition if site=='A:2' else {}},
               'unexpected_atoms':{'atom_ids':[]},'missing_non_hydrogen_atoms':{'atom_ids':[]}}
              for site,ids in [('A:1',["O3'"]),('A:2',targets),('A:3',['P'])]]
    native={'status':'REVIEW','inventory_detail':'linked','fatal_problems':None,'unused_definitions':[],
            'unsupported_fields':[],'atoms':atoms,'monomer_mappings':{'rows':mappings},
            'geometry':{'simple_bonds':links+[custom],'asu_bonds':[],
                        'custom_proxy_requests':[dict(custom,kind='bond'),dict(plane,kind='planarity'),dict(parallel,kind='parallelity')],
                        'proxy_details':{'bond_simple':links+[custom],'planarity':[plane],'parallelity':[parallel]}}}
    prepared=[{'sites':[{'site':'A:2','expected_atoms':targets,
                        'expected_energy_types':{name:'OC2' if name=="O3'" else 'X' for name in targets},
                        'expected_formal_charges':{name:'0' for name in targets},
                        'expected_hydrogen_attachments':{'keepH':['OP2']}}]}]
    return native,deepcopy(native),prepared,[('A:1','A:2'),('A:2','A:3')],['A:1']


def test_complete_native_evidence_gets_scoped_mechanics_pass():
    result=qualify_linked_bundle(*native_case())
    assert result['status']=='LINKED_MECHANICS_PASS'
    assert result['automatic_adoption'] is False
    assert result['numerical_geometry']=='REVIEW_REQUIRED'


@pytest.mark.parametrize('defect',['wrong_target','wrong_weight','duplicate_plane','op3','lost_op2_h','dangling','changed_model','lost_link','wrong_o3_type','charge','missing_detail','lost_mapping','extra_stacking'])
def test_native_defects_cannot_pass_with_matching_aggregate_counts(defect):
    baseline,linked,prepared,edges,ends=native_case()
    if defect=='wrong_target': linked['geometry']['proxy_details']['bond_simple'][-1]['distance_ideal']=2.9
    elif defect=='wrong_weight': linked['geometry']['proxy_details']['planarity'][0]['weights'][0]=50.
    elif defect=='duplicate_plane':linked['geometry']['proxy_details']['planarity'].append(deepcopy(linked['geometry']['proxy_details']['planarity'][0]))
    elif defect=='op3':linked['monomer_mappings']['rows'][1]['metadata']['effective_definition']['atoms'].append({'atom_id':'OP3'})
    elif defect=='lost_op2_h':linked['monomer_mappings']['rows'][1]['metadata']['effective_definition']['bonds']=[]
    elif defect=='dangling':linked['monomer_mappings']['rows'][1]['metadata']['effective_definition']['torsions']=[{'atom_id_4':'absent'}]
    elif defect=='changed_model':linked['atoms'][0]['xyz'][0]=.5
    elif defect=='lost_link':linked['geometry']['simple_bonds']=linked['geometry']['simple_bonds'][1:]
    elif defect=='wrong_o3_type':linked['monomer_mappings']['rows'][1]['metadata']['effective_definition']['atoms'][1]['type_energy']='OH1'
    elif defect=='charge':linked['monomer_mappings']['rows'][1]['metadata']['effective_definition']['atoms'][2]['charge']='-1'
    elif defect=='missing_detail':linked.pop('inventory_detail')
    elif defect=='lost_mapping':linked['monomer_mappings']['rows'].pop()
    elif defect=='extra_stacking':linked['geometry']['proxy_details']['parallelity'].append(deepcopy(linked['geometry']['proxy_details']['parallelity'][0]))
    assert qualify_linked_bundle(baseline,linked,prepared,edges,ends)['status']=='REVIEW'


@pytest.mark.parametrize('charge,status',[(None,'UNSUPPORTED'),('?','UNSUPPORTED'),('.', 'UNSUPPORTED'),('nan','UNSUPPORTED'),('-1','REVIEW')])
def test_missing_charge_readback_is_distinct_from_a_charge_contradiction(charge,status):
    baseline,linked,prepared,edges,ends=native_case()
    atom=linked['monomer_mappings']['rows'][1]['metadata']['effective_definition']['atoms'][2]
    atom['charge']=charge;atom['partial_charge']=0.
    result=qualify_linked_bundle(baseline,linked,prepared,edges,ends)
    check=next(row for row in result['checks'] if row['check']=='effective-site-formal-charges:A:2')
    assert check['status']==status
    assert bool(check['unavailable'])==(status=='UNSUPPORTED')
    assert bool(check['contradictions'])==(status=='REVIEW')
    assert check['partial_charge_substituted'] is False
    assert result['status']=='REVIEW'
