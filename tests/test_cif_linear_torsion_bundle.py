"""Bundle planning follows declarations; numerical stages cannot hide other changes."""
from copy import deepcopy
from pathlib import Path
import json, shutil
import pytest
from tests.test_cif_linear_torsion_candidate import dictionary
from nasolve.ligand_profiles import _emit


def sources(tmp_path, shared=False):
    paths=[]
    for code in ['R92','Q17']:
        d=tmp_path/code;d.mkdir();p,v=dictionary(d,code);paths.append(p)
    if shared:
        p=tmp_path/'shared.cif';p.write_text(paths[0].read_text().replace('data_unrelated','data_unrelated_one')+paths[1].read_text().replace('data_unrelated','data_unrelated_two'));paths=[p]
    return paths


@pytest.mark.parametrize('shared',[False,True])
def test_complete_ordered_bundle_uses_graph_and_preserves_every_other_field(tmp_path,shared):
    from nasolve.cif_linear_torsion_bundle import prepare_linear_torsion_bundle,read_linear_torsion_bundle
    paths=sources(tmp_path,shared);before=[p.read_bytes() for p in paths]
    out=tmp_path/'bundle';r=prepare_linear_torsion_bundle(paths,['R92','Q17','DG'],out)
    assert r['status']=='CANDIDATE_REVIEW' and len(r['steps'])==2
    assert [s['component'] for s in r['steps']]==(['Q17','R92'] if shared else ['R92','Q17'])
    assert r['steps'][0]['dictionaries_after']==r['steps'][1]['dictionaries_before']
    assert all(s['plan']['removed_torsion_count']==1 for s in r['steps'])
    assert not r['automatic_adoption'] and r['native_qualification']=='NOT_RUN'
    assert [p.read_bytes() for p in paths]==before
    moved=out.rename(tmp_path/'moved')
    for p in paths:p.unlink()
    assert read_linear_torsion_bundle(moved)==r
    with pytest.raises(ValueError):prepare_linear_torsion_bundle([],[],moved)


@pytest.mark.parametrize('defect',['duplicate_provider','duplicate_component','bent','missing_period','bad_path','duplicate_atom','duplicate_bond'])
def test_ambiguous_or_incomplete_plan_refuses_before_reserving_output(tmp_path,defect):
    from nasolve.cif_linear_torsion_bundle import prepare_linear_torsion_bundle
    p,v=dictionary(tmp_path);paths=[p];codes=['Q17']
    if defect=='duplicate_provider':paths=[p,p]
    if defect=='duplicate_component':codes*=2
    if defect=='bent':v['_chem_comp_angle.value_angle'][0]='179.9'
    if defect=='missing_period':del v['_chem_comp_tor.period']
    if defect=='bad_path':v['_chem_comp_tor.atom_id_4'][0]='S'
    if defect=='duplicate_atom':
        for k in v:
            if k.startswith('_chem_comp_atom.'):v[k].append(v[k][0])
    if defect=='duplicate_bond':
        for k in v:
            if k.startswith('_chem_comp_bond.'):v[k].append(v[k][0])
    p.write_text(_emit(v));out=tmp_path/'out'
    with pytest.raises(ValueError):prepare_linear_torsion_bundle(paths,codes,out)
    assert not out.exists()


@pytest.mark.parametrize('defect',['candidate','source','plan','order','selection','approval','extra','empty','bound_extra','schema_bool'])
def test_reader_rebuilds_plan_and_rejects_rehashed_changes(tmp_path,defect):
    from nasolve import cif_linear_torsion_bundle as bundle
    paths=sources(tmp_path);out=tmp_path/'out';r=bundle.prepare_linear_torsion_bundle(paths,['R92','Q17'],out)
    if defect in ['candidate','source']:
        ref=r['steps'][0]['candidate'] if defect=='candidate' else r['inputs'][0];p=out/ref['path'];p.write_bytes(p.read_bytes()+b'\n')
    if defect=='plan':r['steps'][0]['plan']['removed_torsion_count']=0
    if defect=='order':r['final_dictionaries'].reverse()
    if defect=='selection':r['modeled_components']=['Q17']
    if defect=='approval':r['automatic_adoption']=True
    if defect=='schema_bool':r['schema_version']=True
    if defect in ['extra','bound_extra']:(out/'extra').write_text('extra')
    if defect=='empty':(out/'empty').mkdir()
    if defect=='bound_extra':r['outputs'].append(bundle._ref(out/'extra',out))
    r['outputs']=[bundle._ref(out/x['path'],out) for x in r['outputs']]
    (out/bundle.REPORT).write_text(json.dumps(r))
    with pytest.raises(ValueError):bundle.read_linear_torsion_bundle(out)


def test_no_triples_or_no_matching_rows_do_not_invent_changes(tmp_path):
    from nasolve.cif_linear_torsion_bundle import prepare_linear_torsion_bundle
    p,v=dictionary(tmp_path);v['_chem_comp_bond.value_order'][1]='SING';p.write_text(_emit(v))
    r=prepare_linear_torsion_bundle([p],['Q17','DG'],tmp_path/'none')
    assert r['status']=='NO_CANDIDATE' and not r['steps']
    assert [v['status'] for v in r['scan']]==['NO_EXPLICIT_DICTIONARY','NO_DECLARED_TRIPLE']
    v['_chem_comp_bond.value_order'][1]='TRIP'
    for k in v:
        if k.startswith('_chem_comp_tor.'):v[k]=v[k][1:]
    p.write_text(_emit(v));r=prepare_linear_torsion_bundle([p],['Q17'],tmp_path/'clean')
    assert not r['steps'] and r['scan'][0]['status']=='NO_MATCHING_TORSIONS'


def numerical_case(tmp_path):
    from tests.test_cif_linked_torsion_energy import case
    from nasolve.cif_linear_torsion_bundle import prepare_linear_torsion_bundle
    before,after,source,candidate,refs=case(tmp_path)
    out=tmp_path/'bundle';prepare_linear_torsion_bundle([source],['Q17','5PC'],out)
    return out,[before,after],[refs]


def test_exact_stage_chain_retains_separate_numerical_and_adoption_boundaries(tmp_path):
    from nasolve.cif_linear_torsion_bundle import qualify_linear_torsion_bundle
    args=numerical_case(tmp_path);saved=deepcopy(args[1:]);q=qualify_linear_torsion_bundle(*args)
    assert q['numerical_checks_pass'] and q['removed_proxy_count']==1 and q['target_delta']==2
    assert q['derivative_qualification']=='NOT_RUN' and not q['automatic_adoption']
    assert q['native_execution_authentication']=='CALLER_REQUIRED' and args[1:]==saved


@pytest.mark.parametrize('defect',['missing_stage','extra_stage','missing_refs','components','energy','bystander','source_pin'])
def test_chain_requires_every_intermediate_inventory_and_attribution(tmp_path,defect):
    from nasolve.cif_linear_torsion_bundle import qualify_linear_torsion_bundle
    out,states,refs=numerical_case(tmp_path)
    if defect=='missing_stage':states.pop()
    if defect=='extra_stage':states.append(deepcopy(states[-1]))
    if defect=='missing_refs':refs.clear()
    if defect=='components':states[0]['atoms'][0]['identity']['resname']='OTHER'
    if defect=='energy':states[-1]['energy_inventory']['snapshots'][0]['target']+=1
    if defect=='bystander':states[-1]['restraint_policy']['secondary_structure_enabled']=True
    if defect=='source_pin':states[-1]['energy_inventory']['installed_sources'][0]['sha256']='b'*64
    with pytest.raises(ValueError):qualify_linear_torsion_bundle(out,states,refs)


def test_two_component_chain_attributes_both_changes_and_every_intermediate(tmp_path):
    import math
    from tests.test_cif_linked_torsion_energy import case
    from nasolve.cif_linear_torsion_bundle import prepare_linear_torsion_bundle,qualify_linear_torsion_bundle
    before,middle,source,_,refs=case(tmp_path)
    folder=tmp_path/'other';folder.mkdir();other,_=dictionary(folder,'5PC')
    for state in [before,middle]:
        state['dictionary_loading'].append({'input':'inputs/002_dictionary.cif','component_metadata':[{'id':'5PC','effective_definition':deepcopy(state['monomer_mappings']['rows'][1]['metadata']['effective_definition'])}]})
        for snap in state['energy_inventory']['snapshots']:
            for i in range(12):snap['gradient'][12+i]+=refs[0]['evaluations'][0]['single_gradient'][i]
            snap['gradient_norm']=math.hypot(*snap['gradient'])
    final=deepcopy(middle);final['dictionary_loading'][1]['component_metadata'][0]['effective_definition']['torsions']=[]
    final['monomer_mappings']['rows'][1]['metadata']['effective_definition']['torsions']=[]
    final['geometry']['proxy_details']['dihedral']=[];final['geometry']['proxy_counts']['dihedral']=0
    for snap in final['energy_inventory']['snapshots']:
        snap.update(target=3.,gradient=[1.]*24,gradient_norm=math.sqrt(24))
        snap['terms']['dihedral_residual_sum']=0.;snap['proxy_counts']['n_dihedral_proxies']=0
    otherref=deepcopy(refs[0]);otherref['proxy']=deepcopy(middle['geometry']['proxy_details']['dihedral'][0]);otherref['sites_cart']=[middle['geometry']['sites_cart_exact'][i] for i in otherref['proxy']['i_seqs']]
    out=tmp_path/'all';prepare_linear_torsion_bundle([source,other],['Q17','5PC'],out)
    q=qualify_linear_torsion_bundle(out,[before,middle,final],[refs,[otherref]])
    assert len(q['steps'])==2 and q['removed_proxy_count']==2 and q['target_delta']==4.
    with pytest.raises(ValueError):qualify_linear_torsion_bundle(out,[before,final,final],[refs,[otherref]])


@pytest.mark.parametrize('defect',['none','dictionary_order','model','phils','namespace','version','executable','authority','receipt_name'])
def test_captured_gate_binds_exact_ordered_consumer_context(tmp_path,monkeypatch,defect):
    from nasolve import cif_linear_torsion_bundle as bundle
    out,states,refs=numerical_case(tmp_path);plan=bundle.read_linear_torsion_bundle(out)
    model=tmp_path/'model.pdb';model.write_text('MODEL')
    phil=tmp_path/'policy.phil';phil.write_text('POLICY')
    capture={'phenix_version':'test','executable_sha256':'a'*64,'phil_namespace_policy':'direct','dictionary_source_policy':'EXPLICIT_DICTIONARIES'}
    calls={};receipts=[]
    for i,ds in enumerate([plan['inputs'],plan['final_dictionaries']]):
        d=tmp_path/str(i);d.mkdir();r=d/'native_receipt.json';r.write_text('receipt'+str(i));receipts.append(r)
        calls[d]=[deepcopy(capture),model,[out/x['path'] for x in ds],[phil],states[i],{}]
    second=calls[receipts[1].parent]
    if defect=='dictionary_order':second[2]=[out/x['path'] for x in plan['inputs']]
    if defect in ['model','phils']:
        p=tmp_path/'changed';p.write_text('CHANGED')
        if defect=='model':second[1]=p
        else:second[3]=[p]
    for name,key in [('namespace','phil_namespace_policy'),('version','phenix_version'),('executable','executable_sha256'),('authority','dictionary_source_policy')]:
        if defect==name:second[0][key]='CHANGED'
    if defect=='receipt_name':receipts[1]=receipts[1].rename(receipts[1].with_name('other.json'))
    monkeypatch.setattr(bundle,'_captured_inputs',lambda directory:calls[directory])
    if defect=='none':
        q=bundle.qualify_captured_linear_torsion_bundle(out,receipts,refs)
        assert q['native_execution_authentication']=='AUTHENTICATED_ORDERED_NATIVE_CAPTURES'
        assert q['kernel_execution_authentication']=='CALLER_REQUIRED' and q['numerical_checks_pass']
    else:
        with pytest.raises(ValueError):bundle.qualify_captured_linear_torsion_bundle(out,receipts,refs)
