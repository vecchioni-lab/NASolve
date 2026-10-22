"""Source metadata is explicit; restoration cannot silently change mechanics."""
from copy import deepcopy
import math
import pytest
from tests.test_cif_candidate_usability import native_case
from tests.test_cif_stereochemistry_audit import write


def classification_case(tmp_path,kind='ccd'):
    from nasolve.cif_linked_preparation import component_values
    s,c,m,n=native_case(tmp_path);v=component_values(s,'Q17')
    if kind=='ccd':v.pop('_chem_comp.group',None);v['_chem_comp.type']=['DNA linking']
    elif kind=='legacy':v['_chem_comp.group']=['DNA']
    elif kind=='both':v['_chem_comp.group']=['DNA'];v['_chem_comp.type']=['DNA LINKING']
    elif kind=='missing':v.pop('_chem_comp.group',None)
    elif kind=='conflict':v['_chem_comp.group']=['RNA'];v['_chem_comp.type']=['DNA LINKING']
    elif kind=='rna':v.pop('_chem_comp.group',None);v['_chem_comp.type']=['RNA LINKING']
    elif kind=='peptide':v.pop('_chem_comp.group',None);v['_chem_comp.type']=['L-PEPTIDE LINKING']
    write(s,v);n['monomer_mappings']['rows'][0]['metadata']['classification']={'status':'RECORDED','value':'DNA'}
    return s,c,m,n


@pytest.mark.parametrize('kind',['ccd','legacy','both','missing','conflict','rna','peptide'])
def test_only_explicit_consistent_source_dna_declarations_authorize_header_restoration(tmp_path,kind):
    from nasolve.cif_source_classification import prepare_source_dna_metadata
    from nasolve.cif_linked_preparation import component_values
    s,c,m,n=classification_case(tmp_path,kind);before=s.read_bytes(),c.read_bytes();out=tmp_path/'prepared'
    if kind in {'ccd','legacy','both'}:
        r=prepare_source_dna_metadata(s,c,'Q17',out);candidate=out/r['candidate']['path'];a=component_values(c,'Q17');b=component_values(candidate,'Q17')
        assert b['_chem_comp.group']==['DNA'] and b['_chem_comp.type']==['DNA LINKING']
        allowed={'_chem_comp.group','_chem_comp.type','data_'}
        assert {k:v for k,v in a.items() if k not in allowed}=={k:v for k,v in b.items() if k not in allowed}
        assert r['numerical_and_chemical_rows_preserved'] and not r['automatic_adoption']
    else:
        with pytest.raises(ValueError):prepare_source_dna_metadata(s,c,'Q17',out)
        assert not out.exists()
    assert before==(s.read_bytes(),c.read_bytes())


@pytest.mark.parametrize('defect',['charges','fixed_hand','output_exists','output_symlink','output_in_inputs'])
def test_source_chemistry_and_owned_output_guards_remain_active(tmp_path,defect):
    from nasolve.cif_source_classification import prepare_source_dna_metadata
    from nasolve.cif_linked_preparation import component_values
    s,c,m,n=classification_case(tmp_path);out=tmp_path/'prepared'
    if defect=='charges':v=component_values(c,'Q17');v['_chem_comp_atom.charge'][0]='1';write(c,v)
    if defect=='fixed_hand':v=component_values(c,'Q17');v['_chem_comp_chir.volume_sign']=['negative'];write(c,v)
    if defect=='output_exists':out.mkdir();(out/'sentinel').write_text('KEEP')
    if defect=='output_symlink':target=tmp_path/'real';target.mkdir();out.symlink_to(target,target_is_directory=True)
    if defect=='output_in_inputs':out=s.parent/'nested'
    before=s.read_bytes(),c.read_bytes()
    with pytest.raises((ValueError,FileExistsError)):prepare_source_dna_metadata(s,c,'Q17',out)
    assert before==(s.read_bytes(),c.read_bytes())
    if defect=='output_exists':assert (out/'sentinel').read_text()=='KEEP'


@pytest.mark.parametrize('defect',['none','permuted_native','group','classification','target','weight','energy','gradient','coordinates','dictionary_coordinate','ss'])
def test_classification_candidate_requires_native_dna_and_the_same_fixed_mechanics(tmp_path,defect):
    from nasolve.cif_source_classification import prepare_source_dna_metadata,qualify_source_dna_metadata
    s,c,m,base=classification_case(tmp_path);out=tmp_path/'prepared';r=prepare_source_dna_metadata(s,c,'Q17',out);p=out/r['candidate']['path']
    for v in base['energy_inventory']['snapshots']:
        v['gradient']=list(range(1,1+3*base['atom_count']));v['gradient_norm']=math.sqrt(sum(x*x for x in v['gradient']))
    n=deepcopy(base);meta=n['monomer_mappings']['rows'][0]['metadata'];meta['group']='DNA'
    if defect=='permuted_native':
        n['atoms'].reverse();mapping={a['i_seq']:i for i,a in enumerate(n['atoms'])}
        for i,a in enumerate(n['atoms']):a['i_seq']=i
        n['geometry']['sites_cart_exact']=[a['xyz'] for a in n['atoms']]
        for rows in n['geometry']['proxy_details'].values():
            for row in rows:row['i_seqs']=[mapping[i] for i in row['i_seqs']]
        for v in n['energy_inventory']['snapshots']:v['gradient']=[x for i in reversed(range(n['atom_count'])) for x in v['gradient'][3*i:3*i+3]]
    if defect=='group':meta['group']='ligand'
    if defect=='classification':meta['classification']['value']='RNA'
    if defect=='target':n['geometry']['proxy_details']['angle'][0]['angle_ideal']+=1
    if defect=='weight':n['geometry']['proxy_details']['bond_simple'][0]['weight']*=.5
    if defect=='energy':
        for v in n['energy_inventory']['snapshots']:v['target']+=1
    if defect=='gradient':
        for v in n['energy_inventory']['snapshots']:v['gradient'][0]*=-1
    if defect=='coordinates':n['atoms'][0]['xyz'][0]+=.01
    if defect=='dictionary_coordinate':
        from nasolve.cif_linked_preparation import component_values
        v=component_values(p,'Q17');v['_chem_comp_atom.x'][0]=str(float(v['_chem_comp_atom.x'][0])+.01);write(p,v)
    if defect=='ss':n['restraint_policy']['secondary_structure_enabled']=True
    q=qualify_source_dna_metadata(s,c,p,m,'Q17',base,n)
    assert q['native_equivalent'] is (defect in {'none','permuted_native'})
    assert q['baseline_qualification']['native_usable']
    assert not q['automatic_adoption'] and q['linked_context']=='NOT_RUN'


@pytest.mark.parametrize('new_usable',[True,False,None])
def test_unqualified_header_candidate_falls_back_to_the_verified_candidate_without_user_review(tmp_path,new_usable):
    from nasolve.cif_source_classification import prepare_source_dna_metadata,classification_decision
    from nasolve.cif_candidate_usability import qualify_candidate_native,isolated_candidate_decision
    s,c,m,n=classification_case(tmp_path);q=qualify_candidate_native(s,c,m,'Q17',n);original=isolated_candidate_decision(s,c,'Q17',q,'NOT_CONVERGED_REPORTED')
    out=tmp_path/'prepared';r=prepare_source_dna_metadata(s,c,'Q17',out);p=out/r['candidate']['path']
    decision=classification_decision(c,p if new_usable is not None else None,'Q17',original,new_usable is True)
    assert decision['continue_solving'] and decision['status']=='CONTINUE_WITH_NOTES'
    assert decision['selected_candidate']==('source_declared_dna' if new_usable else 'verified_generated_fallback')
    assert decision['converged'] is False and not decision['requires_cif_review'] and not decision['automatic_adoption']


def test_already_restored_metadata_keeps_exact_bytes(tmp_path):
    from nasolve.cif_source_classification import prepare_source_dna_metadata
    s,c,m,n=classification_case(tmp_path);a=prepare_source_dna_metadata(s,c,'Q17',tmp_path/'a');p=tmp_path/'a'/a['candidate']['path']
    b=prepare_source_dna_metadata(s,p,'Q17',tmp_path/'b');assert (tmp_path/'b'/b['candidate']['path']).read_bytes()==p.read_bytes()
    assert b['metadata_changes']==[]


def test_native_qualification_cannot_invent_dna_authority_for_another_source(tmp_path):
    from nasolve.cif_source_classification import qualify_source_dna_metadata
    from nasolve.cif_linked_preparation import component_values
    s,c,m,n=classification_case(tmp_path,'rna');v=component_values(c,'Q17');v['_chem_comp.group']=['DNA'];v['_chem_comp.type']=['DNA LINKING'];p=write(tmp_path/'unjustified.cif',v)
    with pytest.raises(ValueError):qualify_source_dna_metadata(s,c,p,m,'Q17',n,n)
