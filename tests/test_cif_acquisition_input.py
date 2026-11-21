"""Prepared generation keeps the existing acquisition owner and original authority."""
import shutil
import pytest
from tests.test_cif_acquisition_attempt import setup
from tests.test_cif_candidate_qualification_execution import case
POLICY='cif-source-reader-preparation-v1'

def test_owned_acquisition_relocation_and_read_only_original_binding(setup, monkeypatch):
    m,args,options,calls,generated=setup
    options['generation']['source_input_policy']=POLICY
    result=m.acquire_dictionary_attempt(*args,**options)
    assert result['acquisition']['status']=='PREPARED_AND_FROZEN'
    old=args[-1];moved=old.with_name('relocated');old.rename(moved)
    args[0].unlink();shutil.rmtree(options['phenix'].root);shutil.rmtree(args[2])
    from tests.test_cif_repair_process import inventory
    before=inventory(moved)
    monkeypatch.setattr(m,'write_record',lambda *a,**k:pytest.fail('read must not mutate'))
    import subprocess
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('read must not launch'))
    saved=m.read_acquisition_result(moved,1)
    assert saved['manifest']['request']['recipe']['source_input_policy']==POLICY
    assert inventory(moved)==before and not old.exists()


def test_interrupted_generation_keeps_projection_and_resumes_in_fresh_attempt(setup, monkeypatch):
    m,args,options,calls,generated=setup
    options['generation']['source_input_policy']=POLICY
    import nasolve.cif_generation_attempt as generation
    original=generation.generate_source_candidate
    def interrupted(*a,**k):
        original(*a,**k)
        raise KeyboardInterrupt('synthetic interruption after native return')
    monkeypatch.setattr(generation,'generate_source_candidate',interrupted)
    with pytest.raises(KeyboardInterrupt):m.acquire_dictionary_attempt(*args,**options)
    from tests.test_cif_repair_process import inventory
    before=inventory(args[-1]/'attempts/attempt-0001')
    child_before=inventory(args[-1]/'generation/attempts/attempt-0001')
    assert m.inspect_acquisition_request(args[-1])['attempts'][0]['state']=='STOPPED'
    monkeypatch.setattr(generation,'generate_source_candidate',original)
    result=m.acquire_dictionary_attempt(*args,**options)
    assert result['attempt_number']==2 and len(generated)==2
    assert inventory(args[-1]/'attempts/attempt-0001')==before
    assert inventory(args[-1]/'generation/attempts/attempt-0001')==child_before
    assert m.read_acquisition_result(args[-1],2)['report']['status']=='PREPARED_AND_FROZEN'
