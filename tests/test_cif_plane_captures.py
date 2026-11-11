"""Owned generation and exact native capture binding; synthetic files are not native proof."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from tests.test_cif_attachment_native import artifact,save,rebind


def setup(tmp_path):
    from tests.test_cif_plane_generation import plane_generation
    from tests.test_cif_plane_native import fixture
    from nasolve.cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID
    source,_,request,work=plane_generation(tmp_path/'generation-control')
    other=tmp_path/'inventory-control';other.mkdir()
    before,after,_,dictionary,_,code,candidate=fixture(other)
    model=tmp_path/'model.pdb';lines=[]
    for native in (before,after):
        for atom in native['atoms']:
            if atom['identity']['resname']=='OTHER':atom['identity']['resname']='OTH'
            atom.update(element='C' if atom['atom_id'] in ('C','R') else atom['atom_id'],occupancy=1.)
        for row in native['monomer_mappings']['rows']:
            if row['literal_identity']['resname']=='OTHER':row['literal_identity']['resname']='OTH';row['metadata']['id']='OTH'
        native.update(schema_version=1,policy_id=NATIVE_POLICY_ID,automatic_adoption=False,
            scientific_approval='NOT_RUN',model_editing='NOT_RUN',optimization='NOT_RUN',readyset_retry='NOT_RUN')
        native['geometry'].update(status='RECORDED',simple_bonds=[],asu_bonds=[])
    for atom in before['atoms']:
        i=atom['identity']
        lines.append(f"HETATM{atom['i_seq']+1:5d} {atom['atom_id']:>4} {i['resname']:>3} {i['chain_id']}{int(i['resseq']):4d}    {0.:8.3f}{0.:8.3f}{0.:8.3f}{1.:6.2f}{20.:6.2f}          {atom['element']:>2}\n")
    model.write_text(''.join(lines)+'END\n')
    bystander=tmp_path/'other.cif';bystander.write_text('data_OTHER\n_custom.value unchanged\n')
    phils=[tmp_path/'first.phil',tmp_path/'second.phil']
    for p in phils:p.write_text('# '+p.stem+' retained policy\n')
    dictionaries=[bystander,dictionary];receipts=[]
    for label,native,chosen in [('before',before,dictionary),('after',after,candidate)]:
        folder=tmp_path/label;folder.mkdir();(folder/'inputs').mkdir()
        supplied=[('model',model),('dictionary',bystander),('dictionary',chosen),*[('phil',p) for p in phils]]
        rows=[];roles={'model':[],'dictionary':[],'phil':[]}
        for i,(role,p) in enumerate(supplied):
            frozen=folder/'inputs'/f'{i:03d}_{role}{p.suffix}';frozen.write_bytes(p.read_bytes())
            rows.append(dict(artifact(frozen,folder),role=role,input_index=i));roles[role].append(rows[-1]['path'])
        native['dictionary_loading'][0].update(input=roles['dictionary'][1],status='RECORDED')
        native['dictionary_loading'].insert(0,dict(input=roles['dictionary'][0],status='RECORDED',component_metadata=[]))
        native['phil_adaptations']=[dict(input=p) for p in roles['phil']]
        spec=dict(policy_id=NATIVE_POLICY_ID,model=roles['model'][0],dictionaries=roles['dictionary'],
            phil_files=roles['phil'],phil_namespace_policy='direct',inventory_detail='linked',policy_inventory=True)
        save(folder/'native_spec.json',spec)
        (folder/'native_worker.py').write_text(_NATIVE_WORKER);(folder/'native.log').write_text('SYNTHETIC, not native execution\n')
        report=dict(schema_version=1,audit_kind='cif_native_bundle_inspection',policy_id=NATIVE_POLICY_ID,
            status='REVIEW',source_preserved=True,frozen_inputs_preserved=True,symlink_outputs=[],automatic_adoption=False,
            scientific_approval='NOT_RUN',optimization='NOT_RUN',model_editing='NOT_RUN',readyset_retry='NOT_RUN',
            phenix_version='SYNTHETIC',executable_sha256='a'*64,api_sources=[dict(module='synthetic',sha256='b'*64)],
            execution=dict(status='COMPLETED',returncode=0),inputs=rows,outputs=[],phil_namespace_policy='direct',
            dictionary_source_policy='EXPLICIT_DICTIONARIES',native_validation=native)
        receipt=folder/'native_receipt.json';save(receipt,report);rebind(receipt);receipts.append(receipt)
    args=(source,code,request,1,candidate,model,*receipts)
    options=dict(dictionaries=dictionaries,dictionary_index=1,phil_files=phils)
    return args,options


def qualify(args,options):
    from nasolve.cif_plane_native import qualify_owned_plane_captures
    return qualify_owned_plane_captures(*args,**options)


def test_exact_owned_capture_delta_preserves_inputs_and_does_not_execute(tmp_path):
    args,options=setup(tmp_path)
    files={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in tmp_path.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')):
        report=qualify(args,options)
    assert report['capture_checks_pass'] and report['inventory_checks_pass']
    assert report['dictionary_index']==1 and report['support_generation']['attempt_number']==1
    assert report['energy_delta_qualification']=='NOT_RUN' and not report['automatic_adoption']
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==data for p,data in files.items())


@pytest.mark.parametrize('defect',['model','dictionary_order','phil_order','candidate','slot','bool_slot','wrong_request',
    'worker','native_payload','version','executable','api','options','model_inventory','geometry_inventory','bystander'])
def test_capture_provenance_or_unexplained_native_changes_cannot_pass(tmp_path,defect):
    args,options=setup(tmp_path);args=list(args);receipt=args[-1]
    if defect=='model':args[5].write_text(args[5].read_text()+'REMARK different\n')
    elif defect=='dictionary_order':options['dictionaries'].reverse()
    elif defect=='phil_order':options['phil_files'].reverse()
    elif defect=='candidate':args[4].write_text(args[4].read_text()+'\n')
    elif defect=='slot':options['dictionary_index']=0
    elif defect=='bool_slot':options['dictionary_index']=True
    elif defect=='wrong_request':args[3]=2
    elif defect=='worker':
        (receipt.parent/'native_worker.py').write_text('changed');rebind(receipt)
    elif defect=='native_payload':
        p=receipt.parent/'native_validation.json';p.write_text('{}')
    else:
        r=json.loads(receipt.read_text());n=r['native_validation']
        if defect=='version':r['phenix_version']='other'
        elif defect=='executable':r['executable_sha256']='0'*64
        elif defect=='api':r['api_sources']=[dict(module='other')]
        elif defect=='options':
            p=receipt.parent/'native_spec.json';s=json.loads(p.read_text());s['policy_inventory']=False;save(p,s)
        elif defect=='model_inventory':n['atoms'][0]['xyz'][0]+=1
        elif defect=='geometry_inventory':n['geometry']['sites_cart_exact'][0][0]+=1
        elif defect=='bystander':n['monomer_mappings']['rows'][1]['metadata']['formal_charge']=1
        save(receipt,r);rebind(receipt)
    with pytest.raises(ValueError):qualify(args,options)


def test_changed_capture_after_qualification_is_refused(tmp_path,monkeypatch):
    import nasolve.cif_plane_native as module
    args,options=setup(tmp_path);original=module.qualify_linked_plane_candidate
    def changed(*values):
        result=original(*values);p=args[-1].parent/'native.log';p.write_text(p.read_text()+'changed\n');return result
    monkeypatch.setattr(module,'qualify_linked_plane_candidate',changed)
    with pytest.raises(ValueError,match='changed during'):qualify(args,options)


def test_capture_and_owned_support_read_after_original_copy_is_gone(tmp_path):
    old=tmp_path/'old';old.mkdir();args,options=setup(old)
    expected=qualify(args,options)
    new=old.rename(tmp_path/'relocated');assert not old.exists()
    move=lambda p:new/p.relative_to(old)
    args=[move(p) if isinstance(p,Path) else p for p in args]
    options={**options,'dictionaries':list(map(move,options['dictionaries'])),'phil_files':list(map(move,options['phil_files']))}
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')):
        assert qualify(args,options)==expected
