"""Failure evidence and fallback wiring; synthetic captures are never chemistry proof."""
from hashlib import sha256
from pathlib import Path
import json,os,shutil,subprocess,sys
import pytest
from nasolve.campaign_records import read_record,write_record
from tests.test_cif_attachment_native import fixture as capture_fixture, artifact, save


def timeout_capture(tmp_path):
    _,path=capture_fixture(tmp_path);record=json.loads(path.read_bytes())
    record.update(status='FAILED',native_validation=None,error='Owned native interpreter process group exceeded the requested timeout')
    record['execution'].update(status='TIMED_OUT',returncode=-15,timeout_seconds=1,elapsed_seconds=1.01)
    record['input_integrity']=[dict(input_index=i,source_preserved=True,snapshot_preserved=True) for i in range(len(record['inputs']))]
    (path.parent/'native_validation.json').unlink()
    record['outputs']=[artifact(p,path.parent) for p in sorted(path.parent.rglob('*')) if p.is_file() and p!=path]
    save(path,record);return path,(path.parent/record['inputs'][0]['path']).read_bytes()


def test_timeout_reader_preserves_strict_scientific_reader(tmp_path):
    from nasolve.cif_attachment_native import _capture,_capture_timeout
    path,model=timeout_capture(tmp_path)
    receipt,native,snapshots=_capture_timeout(path,model)
    assert receipt['execution']['status']=='TIMED_OUT' and native is None and path in snapshots
    with pytest.raises(ValueError):_capture(path,model)


@pytest.mark.parametrize('defect',['worker','input','spec','hash','embedded','unpreserved','code','state','integrity','version','elapsed','limit','integrity-type'])
def test_timeout_does_not_excuse_changed_or_ambiguous_capture(tmp_path,defect):
    from nasolve.cif_attachment_native import _capture_timeout
    path,model=timeout_capture(tmp_path);record=json.loads(path.read_bytes())
    if defect=='worker':(path.parent/'native_worker.py').write_text('OTHER')
    elif defect=='input':(path.parent/record['inputs'][0]['path']).write_bytes(model+b'OTHER')
    elif defect=='spec':
        p=path.parent/'native_spec.json';s=json.loads(p.read_bytes());s['model']='other.pdb';save(p,s)
    elif defect=='hash':record['outputs'][0]['sha256']='0'*64
    elif defect=='embedded':record['native_validation']={'status':'REVIEW'}
    elif defect=='unpreserved':record['source_preserved']=False
    elif defect=='code':record['execution']['returncode']=True
    elif defect=='state':record['execution']['status']='FAILED'
    elif defect=='integrity':record['input_integrity'][0]['snapshot_preserved']=False
    elif defect=='version':record['phenix_version']=''
    elif defect=='elapsed':record['execution']['elapsed_seconds']=-1
    elif defect=='limit':record['execution']['timeout_seconds']=True
    elif defect=='integrity-type':record['input_integrity'][0]='bad'
    if defect in {'worker','input','spec'}:
        record['outputs']=[artifact(p,path.parent) for p in sorted(path.parent.rglob('*')) if p.is_file() and p!=path]
        if defect=='input':record['inputs'][0].update(artifact(path.parent/record['inputs'][0]['path'],path.parent))
    save(path,record)
    with pytest.raises(ValueError):_capture_timeout(path,model)


def test_timeout_partial_report_is_preserved_without_becoming_native_proof(tmp_path):
    from nasolve.cif_attachment_native import _capture_timeout
    path,model=timeout_capture(tmp_path);record=json.loads(path.read_bytes())
    partial=path.parent/'native_validation.json';partial.write_bytes(b'{"status":')
    record['outputs'].append(artifact(partial,path.parent));save(path,record)
    receipt,native,snapshots=_capture_timeout(path,model)
    assert native is None and snapshots[partial]==b'{"status":' and receipt['status']=='FAILED'


def failure_case(tmp_path,monkeypatch,kind='TIMED_OUT',bystander=None):
    from nasolve import cif_prepared_repair_failure as m
    from nasolve.cif_repair_process import PreparedRepairProcesses,inspect_prepared_repair_processes
    from nasolve.cif_native_validation import NATIVE_POLICY_ID
    from nasolve.cif_native_monomers import POLICY_ID as MONOMER_POLICY
    root=tmp_path/'execution';b=root/'bundle';b.mkdir(parents=True);plan=root/'plan';plan.mkdir()
    for name in ('model.pdb','a.cif','b.cif','policy.phil'):(b/name).write_text('SYNTHETIC '+name)
    for i,name in enumerate(('a.cif','b.cif')):shutil.copyfile(b/name,plan/f'{i}.cif')
    (plan/'candidate.cif').write_text('SYNTHETIC GRAPH REPAIR')
    refs=lambda names:[dict(path=n) for n in names]
    value=dict(modeled_components=['AAA','BBB'],inputs=refs(['0.cif','1.cif']),final_dictionaries=refs(['candidate.cif','1.cif']),steps=[dict(component='AAA',dictionary_index=0,dictionaries_after=refs(['candidate.cif','1.cif']))])
    if bystander is not None:
        from tests.helpers import pdb_record
        value['modeled_components']=sorted([*value['modeled_components'],bystander])
        (b/'model.pdb').write_text(''.join(pdb_record('HETATM',i+1,'C1',code,'A',i+1,element='C')
            for i,code in enumerate(['AAA','BBB',bystander]))+'END\n')
    save(plan/'linear_torsion_bundle.json',value)
    consumer=dict(name='TEST',version='TEST',executable_sha256='1'*64)
    def prepared(p):
        p=Path(p);return dict(report=dict(components=['AAA','BBB'],consumer=consumer),model=p/'model.pdb',after_dictionaries=[p/'a.cif',p/'b.cif'],after_phils=[p/'policy.phil'],component_dictionaries={'AAA':p/'a.cif','BBB':p/'b.cif'})
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared);monkeypatch.setattr(m,'read_linear_torsion_bundle',lambda p:json.loads((p/'linear_torsion_bundle.json').read_bytes()))
    owner=PreparedRepairProcesses(root);work=root/'native/001/capture';work.mkdir(parents=True)
    (work/'native_worker.py').write_text('import time;time.sleep(10)' if kind=='TIMED_OUT' else 'raise SystemExit(3)')
    command=[sys.executable,'native_worker.py','native_spec.json']
    try:owner.runner('native-001')(command,cwd=work,log_path=work/'native.log',environment=dict(os.environ),timeout_seconds=.1 if kind=='TIMED_OUT' else 3)
    except subprocess.TimeoutExpired:assert kind=='TIMED_OUT'
    owner.finish('RAISED');state=inspect_prepared_repair_processes(root);finished=state['phases']['native-001']['finished'];rows=[]
    for i,(role,p) in enumerate([('model',b/'model.pdb'),('dictionary',plan/'candidate.cif'),('dictionary',plan/'1.cif'),('phil',b/'policy.phil')]):
        target=work/f'{i}{p.suffix}';shutil.copyfile(p,target);rows.append(dict(artifact(target,work),role=role,input_index=i))
    spec=dict(policy_id=NATIVE_POLICY_ID,model=rows[0]['path'],dictionaries=[p['path'] for p in rows[1:3]],phil_files=[rows[3]['path']],phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True,energy_inventory=True,full_monomer_inventory=True)
    save(work/'native_spec.json',spec)
    record=dict(status='FAILED',execution=dict(status=kind,returncode=finished['returncode'],timeout_seconds=.1 if kind=='TIMED_OUT' else 3),phenix_version='TEST',executable_sha256='1'*64,full_monomer_inventory_policy=MONOMER_POLICY,inputs=rows,outputs=[],command=command)
    record['outputs']=[artifact(p,work) for p in sorted(work.rglob('*')) if p.is_file()]
    receipt=work/'native_receipt.json';save(receipt,record)
    def capture(path,model):
        q=json.loads(path.read_bytes());return q,None if kind=='TIMED_OUT' else dict(status='FAILED',error='Synthetic native refusal',automatic_adoption=False,scientific_approval='NOT_RUN',optimization='NOT_RUN',model_editing='NOT_RUN',readyset_retry='NOT_RUN'),{path:path.read_bytes()}
    monkeypatch.setattr(m,'_capture_timeout',capture);monkeypatch.setattr(m,'_capture',capture)
    return m,root,receipt


@pytest.mark.parametrize('kind',['TIMED_OUT','FAILED'])
def test_optional_failure_binds_actual_stopped_owner_and_exact_plan(tmp_path,monkeypatch,kind):
    m,root,receipt=failure_case(tmp_path,monkeypatch,kind)
    q=m.inspect_prepared_native_failure(root,'native-001')
    assert q['failure_kind']==('NATIVE_TIMEOUT' if kind=='TIMED_OUT' else 'REPORTED_NATIVE_FAILURE')
    assert q['fallback_authorized'] is False and q['retry_authorized'] is False
    assert q['new_native_calls']==0 and q['stopped_verified'] is True
    before={p.relative_to(root):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
    moved=root.rename(tmp_path/'moved')
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Reader executed'))
    assert m.inspect_prepared_native_failure(moved,'native-001')==q
    assert all(((moved/p).read_bytes(),(moved/p).stat().st_mtime_ns)==v for p,v in before.items())


@pytest.mark.parametrize('defect',['baseline','initial','stage','receipt-state','returncode','dispatcher','input-order','plan-input','unlisted','unknown-stop','wrong-command'])
def test_failure_claims_cannot_replace_exact_negative_evidence(tmp_path,monkeypatch,defect):
    m,root,receipt=failure_case(tmp_path,monkeypatch);q=json.loads(receipt.read_bytes());phase='native-001'
    if defect in {'baseline','initial','stage'}:phase={'baseline':'native-baseline','initial':'native-000','stage':'native-002'}[defect]
    elif defect=='receipt-state':q['execution']['status']='COMPLETED'
    elif defect=='returncode':q['execution']['returncode']=3
    elif defect=='dispatcher':q['executable_sha256']='2'*64
    elif defect=='input-order':q['inputs'][1:3]=reversed(q['inputs'][1:3])
    elif defect=='plan-input':(root/'plan/0.cif').write_text('OTHER')
    elif defect=='unlisted':(receipt.parent/'unlisted').write_text('UNDECLARED')
    elif defect=='unknown-stop':(root/'ownership/phases/native-001/finished.json').unlink()
    elif defect=='wrong-command':q['command']=['different','worker.py']
    save(receipt,q)
    with pytest.raises(ValueError):m.inspect_prepared_native_failure(root,phase)


@pytest.mark.parametrize('field,value',[('error',''),('error',None),('model_editing','RUN'),
    ('optimization','RUN'),('scientific_approval','APPROVED'),('automatic_adoption',True),('readyset_retry','RUN')])
def test_reported_failure_cannot_hide_contradictory_claims(tmp_path,monkeypatch,field,value):
    m,root,receipt=failure_case(tmp_path,monkeypatch,'FAILED');capture=m._capture
    def altered(*a,**k):
        record,native,snapshots=capture(*a,**k);native[field]=value;return record,native,snapshots
    monkeypatch.setattr(m,'_capture',altered)
    with pytest.raises(ValueError):m.inspect_prepared_native_failure(root,'native-001')


def test_malformed_native_report_is_a_value_error_not_an_attribute_crash(tmp_path):
    from nasolve.cif_attachment_native import _capture
    _,path=capture_fixture(tmp_path);record=json.loads(path.read_bytes())
    record.update(status='FAILED',native_validation=[]);record['execution']=dict(status='FAILED',returncode=1)
    save(path.parent/'native_validation.json',[])
    record['outputs']=[artifact(p,path.parent) for p in sorted(path.parent.rglob('*')) if p.is_file() and p!=path];save(path,record)
    with pytest.raises(ValueError):_capture(path,(path.parent/record['inputs'][0]['path']).read_bytes())



def test_valid_reported_unsupported_worker_is_distinct_from_timeout(tmp_path,monkeypatch):
    m,root,receipt=failure_case(tmp_path,monkeypatch,'FAILED');capture=m._capture
    def unsupported(*a,**k):
        record,native,snapshots=capture(*a,**k);record['status']='UNSUPPORTED';native['status']='UNSUPPORTED'
        return record,native,snapshots
    monkeypatch.setattr(m,'_capture',unsupported)
    assert m.inspect_prepared_native_failure(root,'native-001')['failure_kind']=='REPORTED_NATIVE_UNSUPPORTED'


@pytest.mark.parametrize('bystander',['DG','Z81'])
def test_optional_failure_accepts_the_full_modeled_plan_without_claiming_bystander_chemistry(tmp_path,monkeypatch,bystander):
    m,root,receipt=failure_case(tmp_path,monkeypatch,bystander=bystander)
    before={p.relative_to(root):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
    result=m.inspect_prepared_native_failure(root,'native-001')
    assert result['failure_kind']=='NATIVE_TIMEOUT' and result['fallback_authorized'] is False
    assert all(((root/p).read_bytes(),(root/p).stat().st_mtime_ns)==v for p,v in before.items())
