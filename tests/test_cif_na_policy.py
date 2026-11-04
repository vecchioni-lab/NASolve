"""Explicit NARestraints membership is independent of starting distances."""
from copy import deepcopy
from pathlib import Path
import pytest


def fixture(tmp_path):
    from restraints.phenix import AT_PARALLEL_A,AT_PARALLEL_T
    names=[('DA',AT_PARALLEL_A),('DT',AT_PARALLEL_T),('DA',AT_PARALLEL_A)]
    atoms=[];lines=[]
    for site,(code,values) in enumerate(names,1):
        for name in values:
            i=len(atoms);xyz=[float(i),0.,0.]
            atoms.append({'i_seq':i,'label':f'Z:{site}:{name}','atom_id':name,'xyz':xyz,
                'identity':{'model_id':'','chain_id':'Z','resseq':str(site),'icode':'','resname':code,'altloc':''}})
            element=name[0]
            lines.append(f'ATOM  {i+1:5d} {name:>4} {code:>3} Z{site:4d}    {xyz[0]:8.3f}{0.:8.3f}{0.:8.3f}{1.:6.2f}{20.:6.2f}          {element:>2}\n')
    model=tmp_path/'source.pdb';model.write_text(''.join(lines)+'END\n')
    ph=tmp_path/'source.phil';ph.write_text('refinement {\n pdb_interpretation {\n secondary_structure {\n enabled = True\n nucleic_acid {\n base_pair {\n base1 = chain Z and resid 1\n base2 = chain Z and resid 2\n saenger_class = 20\n }\n stacking_pair {\n base1 = chain Z and resid 2\n base2 = chain Z and resid 3\n }\n }\n }\n apply_cif_modification {\n data_mod = KEEP_ME\n residue_selection = chain Z and resid 1\n }\n }\n}\n')
    native={'atoms':atoms,'monomer_mappings':{'rows':[]},'geometry':{'custom_proxy_requests':[]}}
    return model,ph,native


def test_compile_uses_narestraints_targets_keeps_modifiers_and_all_declared_contacts(tmp_path):
    from nasolve.cif_na_policy import compile_na_policy
    model,ph,native=fixture(tmp_path);before=ph.read_bytes()
    r=compile_na_policy(model,[ph],native,tmp_path/'compiled')
    assert r['pair_count']==1 and r['stack_count']==1
    assert r['request_counts']=={'angle':2,'bond':2,'parallelity':2}
    text=(tmp_path/'compiled'/r['compiled_phil']).read_text()
    assert 'enabled = False' in text and text.count('distance_ideal = 2.8')==2
    assert 'sigma = 0.027' in text and 'KEEP_ME' in (tmp_path/'compiled'/r['retained_phils'][0]).read_text()
    assert ph.read_bytes()==before and r['automatic_adoption'] is False
    assert r['policy_authority']=='NARestraints' and r['model_optimization']=='NOT_RUN'


@pytest.mark.parametrize('defect',['recipe','duplicate','selection','unsupported_setting','unbalanced','missing_atom','alternate'])
def test_ambiguous_or_unsupported_intent_stops_before_writing(tmp_path,defect):
    from nasolve.cif_na_policy import compile_na_policy
    model,ph,native=fixture(tmp_path);text=ph.read_text()
    if defect=='recipe':text=text.replace('saenger_class = 20','saenger_class = 19')
    if defect=='duplicate':text=text.replace(' stacking_pair {',' base_pair {\n base1 = chain Z and resid 2\n base2 = chain Z and resid 1\n saenger_class = 20\n }\n stacking_pair {')
    if defect=='selection':text=text.replace('base1 = chain Z and resid 1','base1 = all')
    if defect=='unsupported_setting':text=text.replace('saenger_class = 20','saenger_class = 20\n restrain_hbonds = False')
    if defect=='unbalanced':text+='}\n'
    if defect=='missing_atom':native['atoms'].pop()
    if defect=='alternate':native['atoms'][0]['identity']['altloc']='A'
    ph.write_text(text)
    with pytest.raises(ValueError):compile_na_policy(model,[ph],native,tmp_path/'compiled')
    assert not (tmp_path/'compiled').exists()


def test_overlap_with_preserved_edit_is_not_doubly_applied(tmp_path):
    from nasolve.cif_na_policy import compile_na_policy
    model,ph,native=fixture(tmp_path);first=compile_na_policy(model,[ph],native,tmp_path/'one')
    native['geometry']['custom_proxy_requests']=[first['compiled_requests'][0]]
    with pytest.raises(ValueError,match='overlap'):compile_na_policy(model,[ph],native,tmp_path/'two')


def test_policy_checks_native_membership_and_preserved_manager_without_native_id_constants(tmp_path):
    from nasolve.cif_na_policy import compile_na_policy,qualify_na_policy
    model,ph,base=fixture(tmp_path);policy=compile_na_policy(model,[ph],base,tmp_path/'compiled')
    kinds=['bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity']
    base['geometry']['proxy_details']={k:[] for k in kinds}
    base['geometry']['proxy_details']['bond_simple']=[{'i_seqs':[0,1],'atoms':[base['atoms'][0]['label'],base['atoms'][1]['label']],
        'origin_id':0,'distance_ideal':1.,'weight':100.,'symmetry_operation':None}]
    after=deepcopy(base)
    after['status']='REVIEW'
    after['restraint_policy']={'secondary_structure_enabled':False,'origin_ids':{'hydrogen bonds':37,'edits':41,'basepair stacking':43,'basepair parallelity':47,'basepair planarity':49}}
    after['geometry']['custom_proxy_requests']=deepcopy(policy['compiled_requests'])
    for request in policy['compiled_requests']:
        row={k:v for k,v in request.items() if k not in {'kind','action','selections'}};row['origin_id']=41
        after['geometry']['proxy_details']['bond_simple' if request['kind']=='bond' else request['kind']].append(row)
    assert qualify_na_policy(base,after,policy)['mechanics_checks_pass']
    bad=deepcopy(after);bad['geometry']['proxy_details']['bond_simple'][0]['weight']*=1.01
    assert not qualify_na_policy(base,bad,policy)['mechanics_checks_pass']
    bad=deepcopy(after);bad['geometry']['proxy_details']['bond_simple'].append({**bad['geometry']['proxy_details']['bond_simple'][0],'origin_id':37})
    assert not qualify_na_policy(base,bad,policy)['mechanics_checks_pass']
    bad=deepcopy(after);bad['restraint_policy']['secondary_structure_enabled']=True
    assert not qualify_na_policy(base,bad,policy)['mechanics_checks_pass']
    bad=deepcopy(after);bad['geometry']['proxy_details']['bond_simple'].pop(0)
    assert not qualify_na_policy(base,bad,policy)['mechanics_checks_pass']
