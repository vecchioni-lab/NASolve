"""The live reuse control uses real cache APIs and never invokes a generator."""
from pathlib import Path
import pytest

from tests.test_cif_dictionary_store import inputs


@pytest.mark.parametrize('warm',[False,True])
def test_reuse_trial_survives_cold_and_warm_store_and_preserves_qualified_input(tmp_path,warm):
    from nasolve.cif_dictionary_store import publish_dictionary
    from nasolve.cif_dictionary_reuse import exercise_dictionary_reuse
    s,c,m,q,o,request,p=inputs(tmp_path)
    if warm:publish_dictionary(tmp_path/'store',request,s,c,q,consumer=o['consumer'],provenance=p)
    before=s.read_bytes(),c.read_bytes()
    resources={'Q17':{'source':s,'numerical':c,'qualification':q,'provenance':p,**o}}
    r=exercise_dictionary_reuse(resources,tmp_path/'store',tmp_path/'trial')
    assert r['status']=='QUALIFIED_DICTIONARY_REUSE_PASS' and r['new_native_calls']==0
    assert r['source_inputs_preserved'] and r['dictionary_generation']==r['model_optimization']=='NOT_RUN'
    assert all(r['cases']['Q17']['checks'].values())
    assert r['cases']['Q17']['first']['status']==('REUSED' if warm else 'PREPARED_AND_FROZEN')
    assert r['cases']['Q17']['repeat']['status']=='REUSED'
    assert r['cases']['Q17']['repeat']['converged'] is False
    assert (s.read_bytes(),c.read_bytes())==before and not r['requires_cif_review']


def test_unavailable_cache_is_a_reported_optional_layer_not_lost_input(tmp_path,monkeypatch):
    import nasolve.cif_dictionary_store as cache
    from nasolve.cif_dictionary_reuse import exercise_dictionary_reuse
    s,c,m,q,o,request,p=inputs(tmp_path)
    monkeypatch.setattr(cache,'publish_dictionary',lambda *a,**k:(_ for _ in ()).throw(PermissionError('TEST read-only')))
    r=exercise_dictionary_reuse({'Q17':{'source':s,'numerical':c,'qualification':q,'provenance':p,**o}},tmp_path/'store',tmp_path/'trial')
    assert r['status']=='REVIEW' and r['source_inputs_preserved'] and r['cases']['Q17']['first']['persistent_store']=='UNAVAILABLE'
