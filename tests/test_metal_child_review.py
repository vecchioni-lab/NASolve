"""Read saved conditional fits without source parents or native execution."""
from pathlib import Path
from hashlib import sha256
import gzip,json,shutil
from unittest.mock import patch
import pytest
from nasolve.cli import main
from nasolve.metal import child_session as m
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_session import setup,run


def finished(tmp_path,monkeypatch):
    values,native=setup(tmp_path,monkeypatch);review=run(tmp_path,values,native)
    return values,review


def test_normal_read_after_relocation_without_originals_or_native(tmp_path,monkeypatch,capsys):
    values,review=finished(tmp_path,monkeypatch)
    session=tmp_path/'moved';(tmp_path/'session').rename(session)
    shutil.rmtree(values[0].run.parents[2]);shutil.rmtree(values[1]);shutil.rmtree(values[2])
    before={p:p.read_bytes() for p in session.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')),patch.object(m.child_inputs,'verify_child_inputs',side_effect=AssertionError('No original parent replay')):
        assert main(['metal','inspect-audited-fdp-child',str(session),'--review-id',review['record_sha256'],'--json'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['result']==review['result']
    assert result['recorded_free_r']['label']=='FreeR_flag' and result['recorded_free_r']['test_value']==0
    assert result['parent_context']['metal_b_policy']=='donor-mean'
    assert not result['fresh_parent_verification'] and not result['fresh_free_r_audit']
    assert not result['reuse_authorized'] and not result['retirement_authorized']
    assert result['result']['sites'][0]['b_iso']==260 and result['result']['sites'][0]['occupancy']==.6
    assert before=={p:p.read_bytes() for p in before}


@pytest.mark.parametrize('target',['review.json','free-r.json','attempt/native/fdp/job/final.pdb'])
def test_changed_saved_bytes_refuse(tmp_path,monkeypatch,target):
    _,review=finished(tmp_path,monkeypatch);session=tmp_path/'session'
    p=session/target;p.write_bytes(p.read_bytes()+b'changed')
    with pytest.raises((RecipeError,ValueError)):
        m.inspect_audited_child(session,review_id=review['record_sha256'])


def republish(session,review,proof=None):
    if proof:
        p=session/proof;review['files'][proof]['size']=p.stat().st_size;review['files'][proof]['sha256']=sha256(p.read_bytes()).hexdigest()
    return m.records.write_record(session/'review.json',review,replace=True)


@pytest.mark.parametrize('defect',['result','free-r','parent','request'])
def test_rehashed_inconsistent_scientific_claim_refuses(tmp_path,monkeypatch,defect):
    _,review=finished(tmp_path,monkeypatch);session=tmp_path/'session';proof=None
    if defect=='result':review['result']['sites'][0]['f_double_prime']+=1
    elif defect=='free-r':
        proof='free-r.json';v=m.records.read_record(session/proof);v['usable']=False;m.records.write_record(session/proof,v,replace=True)
    elif defect=='parent':review['parent_derivation_after']='0'*64
    else:
        proof='request.json';v=m.records.read_record(session/proof);v['run_relative']='another/AutoMR/run_001';m.records.write_record(session/proof,v,replace=True)
    changed=republish(session,review,proof)
    with pytest.raises(RecipeError):m.inspect_audited_child(session,review_id=changed['record_sha256'])


def test_resealed_native_B_change_still_fails_scientific_audit(tmp_path,monkeypatch):
    _,review=finished(tmp_path,monkeypatch);session=tmp_path/'session';attempt=session/'attempt'
    p=attempt/'native/fdp/job/native-result.json.gz';native=json.loads(gzip.decompress(p.read_bytes()));native['atoms'][-1]['b_iso']+=1
    p.write_bytes(gzip.compress(json.dumps(native).encode()))
    fresh=m.child_outputs._inventory(attempt,review['request_id'],m.child_outputs.DEFAULT_MAX_BYTES)
    seal=m.records.write_record(attempt/'outputs.json',fresh,replace=True)
    review['output_evidence_id']=seal['record_sha256'];changed=republish(session,review)
    with pytest.raises(RecipeError,match='Frozen native state changed'):
        m.inspect_audited_child(session,review_id=changed['record_sha256'])


def test_wrong_independent_pin_and_late_proof_change_refuse(tmp_path,monkeypatch):
    _,review=finished(tmp_path,monkeypatch);session=tmp_path/'session'
    with pytest.raises(RecipeError):m.inspect_audited_child(session,review_id='0'*64)
    original=m._audit_job
    def changed(*a,**k):
        result=original(*a,**k)
        p=session/'fresh-inputs.json';p.write_bytes(p.read_bytes()+b'changed')
        return result
    monkeypatch.setattr(m,'_audit_job',changed)
    with pytest.raises(RecipeError):m.inspect_audited_child(session,review_id=review['record_sha256'])


def test_native_audit_expansion_is_bounded(tmp_path,monkeypatch):
    _,review=finished(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'MAX_NATIVE_JSON_BYTES',16)
    with pytest.raises(RecipeError,match='Native audit JSON exceeds byte budget'):
        m.inspect_audited_child(tmp_path/'session',review_id=review['record_sha256'])
