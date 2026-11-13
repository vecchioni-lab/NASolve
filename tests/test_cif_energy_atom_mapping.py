"""Explicit composed capture transport; synthetic receipts are not native science."""
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from .test_cif_native_atom_mapping import mapped_fixture
from .test_cif_attachment_native import rebind,save


def composed_fixture(root):
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_native_atom_mapping import native_mapping_worker
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_monomers import capture_full_monomers,native_monomer_worker,POLICY_ID
    paths=mapped_fixture(root,True);path=paths[1];r=json.loads(path.read_text());n=r['native_validation']
    for row in n['monomer_mappings']['rows']:row['chain_id']=row['literal_identity']['chain_id']
    n['full_monomer_inventory']=capture_full_monomers(n,False)
    n['energy_inventory']=dict(policy_id='cif-fixed-native-usability-energy-v1',status='RECORDED',normalization=False,
        evaluation_calls=2,snapshots=[dict(target=1.,gradient=[0.]*(3*n['atom_count']),gradient_norm=0.) for _ in range(2)],installed_sources=[])
    r['full_monomer_inventory_policy']=POLICY_ID
    spec=json.loads((path.parent/'native_spec.json').read_text())
    spec.update(energy_inventory=True,full_monomer_inventory=True,policy_inventory=True)
    save(path.parent/'native_spec.json',spec)
    worker=native_monomer_worker(native_mapping_worker(native_energy_worker(_NATIVE_WORKER)))
    compile(worker,'native_worker.py','exec')
    (path.parent/'native_worker.py').write_text(worker);save(path,r);rebind(path)
    return paths


def test_exact_composed_worker_replays_after_relocation(tmp_path):
    from nasolve.cif_attachment_native import _capture,_native_atoms
    from nasolve.cif_native_atom_mapping import bound_name_mappings
    old=tmp_path/'old';old.mkdir();paths=composed_fixture(old);path=paths[1]
    relative=path.relative_to(old);moved=tmp_path/'moved';shutil.move(old,moved);path=moved/relative
    model=(path.parent/'inputs/model.pdb').read_bytes()
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('cold read')):
        receipt,native,_=_capture(path,model)
        summary,maps=bound_name_mappings(native,_native_atoms(native,model)[0])
    assert summary['status']=='RECORDED' and maps['A:1']["O5'"]=='O5X'
    assert not old.exists() and all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())


@pytest.mark.parametrize('defect',['full','policy','nonbonded','gradients','worker','receipt_mapping'])
def test_rehashed_composition_cannot_hide_missing_scope_or_changed_worker(tmp_path,defect):
    from nasolve.cif_attachment_native import _capture
    paths=composed_fixture(tmp_path);path=paths[1];specpath=path.parent/'native_spec.json'
    spec=json.loads(specpath.read_text());r=json.loads(path.read_text())
    if defect in {'full','policy'}:spec.pop('full_monomer_inventory' if defect=='full' else 'policy_inventory')
    if defect=='nonbonded':spec['nonbonded_inventory']=True
    if defect=='gradients':spec['gradient_indices']=[0]
    if defect=='worker':(path.parent/'native_worker.py').write_text('unqualified composition')
    if defect=='receipt_mapping':r.pop('atom_name_mapping_policy')
    save(specpath,spec);save(path,r);rebind(path)
    with pytest.raises(ValueError):_capture(path,(path.parent/'inputs/model.pdb').read_bytes())


def test_owned_timeout_preserves_partial_mapping_without_qualifying_it(tmp_path):
    from nasolve.cif_attachment_native import _capture,_capture_timeout
    paths=composed_fixture(tmp_path);path=paths[1];r=json.loads(path.read_text())
    r.update(status='FAILED',native_validation=None,error='Owned native interpreter process group exceeded the requested timeout')
    r['execution'].update(status='TIMED_OUT',returncode=-15,timeout_seconds=1,elapsed_seconds=1.01)
    r['input_integrity']=[dict(input_index=i,source_preserved=True,snapshot_preserved=True) for i in range(len(r['inputs']))]
    (path.parent/'native_validation.json').write_text('{incomplete');save(path,r);rebind(path)
    payload=(path.parent/'inputs/model.pdb').read_bytes()
    with pytest.raises(ValueError):_capture(path,payload)
    receipt,native,_=_capture_timeout(path,payload)
    assert native is None and receipt['execution']['status']=='TIMED_OUT'


@pytest.mark.parametrize('options',[{'full_monomer_inventory':False}, {'policy_inventory':False},
    {'nonbonded_inventory':True}, {'gradient_indices':[0]}])
def test_unsupported_composition_refuses_before_allocation(tmp_path,options):
    from nasolve.cif_native_validation import inspect_native_bundle
    kwargs=dict(inventory_detail='linked',energy_inventory=True,atom_name_mapping=True,
        full_monomer_inventory=True,policy_inventory=True);kwargs.update(options)
    with pytest.raises(ValueError):inspect_native_bundle(tmp_path/'absent',[],tmp_path/'out',tmp_path/'python',
        environment={},phenix_version='test',**kwargs)
    assert not (tmp_path/'out').exists()


def test_captured_manager_intake_keeps_the_observed_mapping(tmp_path):
    from nasolve.cif_captured_mixed_gradients import _inputs
    paths=composed_fixture(tmp_path)
    capture,model,dictionaries,phils,native,bindings=_inputs(paths[1].parent)
    assert native['atom_name_mapping_policy']=='cif-native-observed-atom-name-mapping-v1'
    assert bindings['active_capture']['sha256']
    assert dictionaries==[] and capture['dictionary_source_policy']=='INSTALLED_LIBRARY_ONLY' and model.is_file()


def test_numerical_rebuild_keeps_mapping_in_the_exact_manager(tmp_path):
    from nasolve.cif_captured_mixed_gradients import _inputs,_preserve_native_context
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_atom_mapping import native_mapping_worker
    from nasolve.cif_native_monomers import native_monomer_worker
    (tmp_path/'capture').mkdir();paths=composed_fixture(tmp_path/'capture')
    capture,*_= _inputs(paths[1].parent)
    work=tmp_path/'numerical/job';work.mkdir(parents=True)
    save(work/'native_spec.json',{})
    (work/'native_worker.py').write_text(native_energy_worker(_NATIVE_WORKER))
    preparation=_preserve_native_context(work.parent,capture,{})
    assert json.loads((work/'native_spec.json').read_bytes())['atom_name_mapping'] is True
    assert preparation['atom_name_mapping_policy']==capture['atom_name_mapping_policy']
    assert (work/'native_worker.py').read_text()==native_monomer_worker(native_mapping_worker(native_energy_worker(_NATIVE_WORKER)))
