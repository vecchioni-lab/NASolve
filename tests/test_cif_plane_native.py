"""Source-rebuilt plane completion changes only its exact native memberships."""
from copy import deepcopy

import pytest

from tests.test_cif_plane_candidate import inputs, prepare


def fixture(tmp_path,code='Q17'):
    paths,candidate,plan=prepare(tmp_path,*inputs(tmp_path,code))
    def identity(code,chain):
        return dict(model_id='',chain_id=chain,resseq='1',icode='',altloc='',resname=code)
    definition=dict(plane_atoms=[dict(plane_id='plane1',atom_id=n,dist_esd=.02) for n in ('C','O','N')],
                    bonds=[dict(atom_id_1='C',atom_id_2='O',type='DOUB',value_dist=1.234)])
    atoms=[];mappings=[];proxies=[]
    for chain,component in [('A',code),('B','OTHER')]:
        ident=identity(component,chain);offset=len(atoms)
        mappings.append(dict(literal_identity=ident,chem_mod_ids=['preserve-phosphate'],
                             metadata=dict(id=component,effective_definition=deepcopy(definition))))
        for index,name in enumerate(('C','O','N','R'),offset):
            atoms.append(dict(i_seq=index,atom_id=name,identity=ident,label=f'{chain}:{name}',xyz=[0.,0.,0.]))
        proxies.append(dict(i_seqs=list(range(offset,offset+3)),atoms=[a['label'] for a in atoms[offset:offset+3]],
                            weights=[2500.]*3,origin_id=0))
    before=dict(status='REVIEW',fatal_problems=None,unused_definitions=[],unsupported_fields=[],inventory_detail='linked',
        atom_count=len(atoms),atoms=atoms,monomer_mappings=dict(rows=mappings),
        dictionary_loading=[dict(input='inputs/001_dictionary.cif',component_metadata=[dict(id=code,effective_definition=deepcopy(definition))])],
        geometry=dict(proxy_details=dict(planarity=proxies,bond_asu=[dict(link='preserve-polymer')],parallelity=[dict(origin='NAR')]),
                      proxy_counts=dict(planarity=2),sites_cart_exact=[a['xyz'] for a in atoms]),
        installed_api_sources=[dict(path='native.py',sha256='f'*64)],restraint_policy=dict(secondary_structure_enabled=False))
    after=deepcopy(before)
    addition=dict(plane_id='plane1',atom_id='R',dist_esd=.02)
    after['dictionary_loading'][0]['component_metadata'][0]['effective_definition']['plane_atoms'].append(deepcopy(addition))
    after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['plane_atoms'].append(deepcopy(addition))
    proxy=after['geometry']['proxy_details']['planarity'][0]
    proxy['i_seqs'].append(3);proxy['atoms'].append('A:R');proxy['weights'].append(2500.)
    return before,after,*paths,code,candidate


def qualify(args):
    from nasolve.cif_plane_native import qualify_linked_plane_candidate
    return qualify_linked_plane_candidate(*args)


@pytest.mark.parametrize('code',['Q17','PDU','A1AAZ'])
def test_exact_completed_plane_preserves_same_named_bystander_and_inputs(tmp_path,code):
    args=fixture(tmp_path,code);old=deepcopy(args[:2]);frozen=[p.read_bytes() for p in (*args[2:5],args[-1])]
    result=qualify(args)
    assert result['inventory_checks_pass']
    assert result['extended_native_planes']==1 and result['added_native_members']==1
    assert result['modeled_occurrences']==1
    assert result['native_provenance']=='CALLER_MUST_AUTHENTICATE'
    assert not result['automatic_adoption'] and result['derivative_qualification']=='NOT_RUN'
    assert args[:2]==old and [p.read_bytes() for p in (*args[2:5],args[-1])]==frozen


@pytest.mark.parametrize('defect',['bystander','links','nar','charge','coordinates','policy','api','unknown','typed','new_weight','lost_ring'])
def test_other_native_changes_cannot_pass(tmp_path,defect):
    args=fixture(tmp_path);after=args[1]
    if defect=='bystander':after['geometry']['proxy_details']['planarity'][1]['weights'][0]=1.
    elif defect=='links':after['geometry']['proxy_details']['bond_asu']=[]
    elif defect=='nar':after['geometry']['proxy_details']['parallelity']=[]
    elif defect=='charge':after['monomer_mappings']['rows'][1]['metadata']['formal_charge']=1
    elif defect=='coordinates':after['geometry']['sites_cart_exact'][0]=[1.,2.,3.]
    elif defect=='policy':after['restraint_policy']['secondary_structure_enabled']=True
    elif defect=='api':after['installed_api_sources']=[]
    elif defect=='unknown':after['new_category']={}
    elif defect=='typed':after['geometry']['proxy_counts']['planarity']=True
    elif defect=='new_weight':after['geometry']['proxy_details']['planarity'][0]['weights'][-1]=1.
    elif defect=='lost_ring':
        p=after['geometry']['proxy_details']['planarity'][0]
        for k in ('i_seqs','atoms','weights'):p[k].pop(0)
    assert not qualify(args)['inventory_checks_pass']


@pytest.mark.parametrize('defect',['candidate','provider','mapping','atom','added_atom_absent','proxy_absent',
                                 'proxy_duplicate','weight','label','origin','definition','unsupported'])
def test_unbound_or_ambiguous_native_plan_is_refused(tmp_path,defect):
    args=fixture(tmp_path);before=args[0]
    if defect=='candidate':args[-1].write_bytes(args[-1].read_bytes()+b'\n')
    elif defect=='provider':before['dictionary_loading']*=2
    elif defect=='mapping':before['monomer_mappings']['rows'].append(deepcopy(before['monomer_mappings']['rows'][0]))
    elif defect=='atom':before['atoms'].append(deepcopy(before['atoms'][0]))
    elif defect=='added_atom_absent':before['atoms'].pop(3)
    elif defect=='proxy_absent':before['geometry']['proxy_details']['planarity'].pop(0)
    elif defect=='proxy_duplicate':before['geometry']['proxy_details']['planarity'].append(deepcopy(before['geometry']['proxy_details']['planarity'][0]))
    elif defect=='weight':before['geometry']['proxy_details']['planarity'][0]['weights'][0]=1.
    elif defect=='label':before['geometry']['proxy_details']['planarity'][0]['atoms'][0]='wrong'
    elif defect=='origin':before['geometry']['proxy_details']['planarity'][0]['origin_id']=4
    elif defect=='definition':before['monomer_mappings']['rows'][0]['metadata']['effective_definition']['plane_atoms'][0]['dist_esd']=.2
    elif defect=='unsupported':args[1]['unsupported_fields']=['opaque_plane']
    with pytest.raises(ValueError):qualify(args)


def test_every_occurrence_is_extended_and_energy_is_not_inherited(tmp_path):
    args=fixture(tmp_path)
    for native in args[:2]:
        native['monomer_mappings']['rows'][1]['literal_identity']['resname']='Q17'
        native['monomer_mappings']['rows'][1]['metadata']['id']='Q17'
        for atom in native['atoms'][4:]:atom['identity']['resname']='Q17'
    after=args[1];after['monomer_mappings']['rows'][1]['metadata']['effective_definition']['plane_atoms'].append(dict(plane_id='plane1',atom_id='R',dist_esd=.02))
    proxy=after['geometry']['proxy_details']['planarity'][1]
    proxy['i_seqs'].append(7);proxy['weights'].append(2500.);proxy['atoms'].append('B:R')
    for native,value in zip(args[:2],(10,9)):native['energy_inventory']=dict(target=value)
    result=qualify(args)
    assert result['inventory_checks_pass'] and result['extended_native_planes']==2
    assert result['energy_delta_qualification']=='NOT_RUN'


def test_plane_permutation_keeps_exact_index_weight_label_association(tmp_path):
    args=fixture(tmp_path)
    for native in args[:2]:
        proxy=native['geometry']['proxy_details']['planarity'][0]
        for k in ('i_seqs','weights','atoms'):proxy[k].reverse()
    assert qualify(args)['inventory_checks_pass']


def test_relocation_works_without_original_inputs(tmp_path):
    import shutil
    old=tmp_path/'old';old.mkdir();args=fixture(old)
    new=tmp_path/'new';shutil.move(old,new)
    relocated=(*args[:2],*(new/p.name for p in args[2:5]),args[-2],new/args[-1].name)
    assert not old.exists() and qualify(relocated)['inventory_checks_pass']
