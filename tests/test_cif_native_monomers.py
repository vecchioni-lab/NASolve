"""Complete native identity evidence; synthetic fixtures assert no chemistry."""
from copy import deepcopy
import json
import shutil
from unittest.mock import patch
import pytest


def native_fixture():
    atoms=[];rows=[]
    for chain in ['A','B']:
        identity=dict(model_id='',chain_id=chain,resseq='   1',icode='',resname='ZZZ',altloc='')
        atoms.append(dict(i_seq=len(atoms),atom_id='P',identity=identity))
        rows.append(dict(site=chain+':1',resname='ZZZ',chain_id=chain,
            literal_identity=dict(status='RECORDED',**identity)))
    return dict(atoms=atoms,atom_count=len(atoms),monomer_mappings=dict(status='RECORDED',rows=rows))


def test_copied_chain_requires_its_own_native_identity():
    from nasolve.cif_native_monomers import capture_full_monomers,review_full_monomers
    native=native_fixture()
    proof=capture_full_monomers(native,False)
    native['full_monomer_inventory']=proof
    assert proof['residue_count']==2 and proof['mapping_count']==2
    assert review_full_monomers(native)==proof
    native['monomer_mappings']['rows'].pop()
    with pytest.raises(ValueError,match='complete'):
        review_full_monomers(native)


@pytest.mark.parametrize('defect',['copy','auto','numeric','missing','extra','duplicate','blank',
    'wrong_chain','wrong_site','wrong_name','unknown','atom_field','empty_atoms','count','stale_proof'])
def test_no_inferred_or_stale_monomer_evidence(defect):
    from nasolve.cif_native_monomers import capture_full_monomers,review_full_monomers
    n=native_fixture();n['full_monomer_inventory']=capture_full_monomers(n,False)
    rows=n['monomer_mappings']['rows'];flag=False
    if defect=='copy':flag=True
    if defect=='auto':flag=None
    if defect=='numeric':flag=0
    if defect=='missing':rows.pop()
    if defect=='extra':
        r=deepcopy(rows[-1]);r['literal_identity']['chain_id']='C';r.update(chain_id='C',site='C:1');rows.append(r)
    if defect=='duplicate':rows.append(deepcopy(rows[-1]))
    if defect=='blank':rows[-1]['literal_identity']['resseq']=''
    if defect=='wrong_chain':rows[-1]['chain_id']='A'
    if defect=='wrong_site':rows[-1]['site']='A:1'
    if defect=='wrong_name':rows[-1]['resname']='YYY'
    if defect=='unknown':rows[-1]['literal_identity']['status']='UNSUPPORTED'
    if defect=='atom_field':del n['atoms'][-1]['identity']['model_id']
    if defect=='empty_atoms':n['atoms']=[];n['atom_count']=0
    if defect=='count':n['atom_count']=True
    if defect=='stale_proof':n['full_monomer_inventory']['residue_count']=1
    with pytest.raises(ValueError):
        if defect=='stale_proof':review_full_monomers(n)
        else:capture_full_monomers(n,flag)


def test_full_site_policy_replays_after_relocation(tmp_path):
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites,read_dictionary_sites
    from tests.test_cif_dictionary_sites import inputs
    args=inputs(tmp_path);context=dict(policy_id='cif-explicit-site-native-context-v2',
        custom_restraints='absent',monomer_inventory='full_model')
    user=tmp_path/'user.phil';user.write_text('pdb_interpretation.use_ncs_to_build_restraints = True')
    out=tmp_path/'site';r=prepare_dictionary_sites(output=out,native_context=context,
        supplementary_phils=[user],**args)
    assert r['policy_id']=='cif-stored-dictionary-sites-v3'
    saved={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    out.rename(tmp_path/'moved');out=tmp_path/'moved'
    for name in ['store','snapshot','inputs','resources']:
        if (tmp_path/name).exists():shutil.rmtree(tmp_path/name)
    with patch('subprocess.Popen',side_effect=AssertionError('Must be read only')):
        read=read_dictionary_sites(out)
    assert read['native_options']==dict(full_monomer_inventory=True)
    for phase in ['before','after']:
        assert read[phase+'_phils'][-1]==out/'prepared/native_interpretation.phil'
        assert 'use_ncs_to_build_restraints = False' in read[phase+'_phils'][-1].read_text()
    assert all((out/p).read_bytes()==b and (out/p).stat().st_mtime_ns==t for p,(b,t) in saved.items())


@pytest.mark.parametrize('defect',['policy','mode','extra','missing','rehashed_phil','legacy_policy'])
def test_full_site_contract_cannot_be_silently_downgraded(tmp_path,defect):
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites,read_dictionary_sites,_files
    from tests.test_cif_dictionary_sites import inputs
    args=inputs(tmp_path);context=dict(policy_id='cif-explicit-site-native-context-v2',
        custom_restraints='absent',monomer_inventory='full_model')
    if defect=='policy':context['policy_id']='cif-explicit-site-native-context-v1'
    if defect=='mode':context['monomer_inventory']='infer_copies'
    if defect=='extra':context['guess']=True
    if defect=='missing':del context['monomer_inventory']
    out=tmp_path/'site'
    if defect in {'policy','mode','extra','missing'}:
        with pytest.raises(ValueError):prepare_dictionary_sites(output=out,native_context=context,**args)
        assert not out.exists()
    else:
        prepare_dictionary_sites(output=out,native_context=context,**args)
        receipt=out/'site_receipt.json';r=json.loads(receipt.read_text())
        if defect=='legacy_policy':r['policy_id']='cif-stored-dictionary-sites-v2'
        else:
            (out/'prepared/native_interpretation.phil').write_text('pdb_interpretation.use_ncs_to_build_restraints = True')
            r['files']=_files(out)
        receipt.write_text(json.dumps(r))
        with pytest.raises(ValueError):read_dictionary_sites(out)



@pytest.mark.parametrize('flag',[False,True,None])
def test_standalone_worker_records_policy_or_preserves_refusal(tmp_path,flag):
    from pathlib import Path
    from tests.test_cif_native_validation import native_runtime,files
    from nasolve.cif_native_validation import inspect_native_bundle
    from nasolve.cif_native_monomers import review_full_monomers
    from nasolve.cif_attachment_native import _capture
    model,dictionaries=files(tmp_path);executable,environment=native_runtime(tmp_path)
    module=tmp_path/'fake_native/fake_native.py';s=module.read_text()
    s=s.replace('apply_cif_modification=requests)',
        'apply_cif_modification=requests,use_ncs_to_build_restraints='+repr(flag)+')')
    s=s.replace('self.angle_proxies=[1,2]; self.dihedral_proxies=[1]',
        'self.angle_proxies=[]; self.dihedral_proxies=[]').replace(
        'self.chirality_proxies=[1]; self.planarity_proxies=[1]; self.parallelity_proxies=None',
        'self.chirality_proxies=[]; self.planarity_proxies=[]; self.parallelity_proxies=[]')
    module.write_text(s)
    result=inspect_native_bundle(model,dictionaries,tmp_path/'outputs',executable,
        environment=environment,phenix_version='FAKE_TEST',inventory_detail='linked',full_monomer_inventory=True)
    work=Path(result['native_directory'])
    if flag is False:
        assert result['status']=='REVIEW'
        assert review_full_monomers(result['native_validation'])['mapping_count']==1
    else:
        assert result['status']=='UNSUPPORTED'
        assert not (work/'native_calls.json').exists()
        assert 'explicit use_ncs_to_build_restraints=False' in result['native_validation']['error']
    captured,native,_=_capture(work/'native_receipt.json',model.read_bytes())
    assert captured==result and native==result['native_validation']


@pytest.mark.parametrize('defect',['missing_proof','false_copying','incomplete','changed_worker','unrequested',
    'wrong_receipt_policy','numeric_flag','unrequested_policy','unrequested_proof','boolean_count'])
def test_rehashed_capture_requires_consistent_request_worker_and_proof(tmp_path,defect):
    from nasolve.cif_attachment_native import _capture
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_native_monomers import capture_full_monomers,native_monomer_worker,POLICY_ID
    from tests.test_cif_attachment_native import fixture,rebind,save
    _,path=fixture(tmp_path);r=json.loads(path.read_text());native=r['native_validation']
    for row in native['monomer_mappings']['rows']:row['chain_id']=row['literal_identity']['chain_id']
    native['full_monomer_inventory']=capture_full_monomers(native,False)
    r['full_monomer_inventory_policy']=POLICY_ID
    spec_path=path.parent/'native_spec.json';spec=json.loads(spec_path.read_text());spec['full_monomer_inventory']=True
    worker=native_monomer_worker(_NATIVE_WORKER)
    save(path,r);save(spec_path,spec);(path.parent/'native_worker.py').write_text(worker);rebind(path)
    _capture(path,(path.parent/'inputs/model.pdb').read_bytes())
    r=json.loads(path.read_text());native=r['native_validation']
    if defect=='missing_proof':del native['full_monomer_inventory']
    if defect=='false_copying':native['full_monomer_inventory']['use_ncs_to_build_restraints']=True
    if defect=='incomplete':native['monomer_mappings']['rows'].pop()
    if defect=='changed_worker':worker+='\n# altered\n'
    if defect=='unrequested':del spec['full_monomer_inventory']
    if defect=='wrong_receipt_policy':r['full_monomer_inventory_policy']='unknown'
    if defect=='numeric_flag':spec['full_monomer_inventory']=1
    if defect=='boolean_count':native['full_monomer_inventory']['schema_version']=True
    if defect in {'unrequested_policy','unrequested_proof'}:
        del spec['full_monomer_inventory'];worker=_NATIVE_WORKER
        if defect=='unrequested_proof':del r['full_monomer_inventory_policy']
        else:del native['full_monomer_inventory']
    save(path,r);save(spec_path,spec);(path.parent/'native_worker.py').write_text(worker);rebind(path)
    with pytest.raises(ValueError):_capture(path,(path.parent/'inputs/model.pdb').read_bytes())


@pytest.mark.parametrize('flag,detail',[(1,'linked'),('yes','linked'),(None,'linked'),(True,'basic')])
def test_request_rejected_before_any_output(tmp_path,flag,detail):
    from nasolve.cif_native_validation import inspect_native_bundle
    with pytest.raises(ValueError):
        inspect_native_bundle(tmp_path/'missing',[],tmp_path/'out',tmp_path/'missing-python',
            environment={},phenix_version='FAKE',full_monomer_inventory=flag,inventory_detail=detail)
    assert not (tmp_path/'out').exists()
