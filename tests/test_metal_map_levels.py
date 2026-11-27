"""Display levels change only inspection, with exact-source cache checks."""
import copy
import pytest
from nasolve.metal.inspection import Inspections
from nasolve.metal.recipe import RecipeError,canonical
from nasolve.metal.context import _reference


def setup(tmp_path,monkeypatch):
    run=tmp_path/'dataset/AutoMR/run_001';run.mkdir(parents=True)
    model=run/'model.pdb';model.write_bytes(b'synthetic model')
    maps=[]
    for name in ['map-2mfo-dfc.mtz','map-mfo-dfc.mtz']:
        p=run/name;p.write_bytes(b'synthetic map '+name.encode());maps.append(dict(filename=name,source=_reference(p,run),stage='XYZ geometry'))
    scope=dict(dataset_id='d',structure_id='s',hypothesis_id='h');key=dict(atom_name='HG')
    scene=dict(scope,inspection=dict(id='g'),atoms=[dict(key=key,xyz=[1,2,3])],nodes=[])
    owner=Inspections();owner.profiles[canonical([scope,'g'])]=dict(run=run,scope=scope,model=_reference(model,run),maps=maps,dictionaries=[])
    calls=[]
    monkeypatch.setattr(owner,'_maps',lambda maps,centre:calls.append((copy.deepcopy(maps),centre)) or {'levels':{m['filename']:m['sigma'] for m in maps}})
    return owner,scene,calls,run


def test_requested_levels_get_distinct_cache_entries_and_defaults_stay_unchanged(tmp_path,monkeypatch):
    owner,scene,calls,run=setup(tmp_path,monkeypatch);before={p.name:p.read_bytes() for p in run.iterdir()}
    initial=owner.perform('maps',scene,None)
    assert initial['levels']=={'map-2mfo-dfc.mtz':1.,'map-mfo-dfc.mtz':3.}
    custom=owner.perform('maps',scene,None,sigma_levels={'mFo-DFc':1.5})
    assert custom['levels']=={'map-2mfo-dfc.mtz':1.,'map-mfo-dfc.mtz':1.5}
    assert owner.perform('maps',scene,None,sigma_levels={'mFo-DFc':1.5})==custom and len(calls)==2
    assert owner.perform('maps',scene,None)==initial and len(calls)==2
    assert {p.name:p.read_bytes() for p in run.iterdir()}==before
    (run/'map-mfo-dfc.mtz').write_bytes(b'changed')
    with pytest.raises(RecipeError):owner.perform('maps',scene,None,sigma_levels={'mFo-DFc':1.5})
    assert len(calls)==2


@pytest.mark.parametrize('levels',[[],{'Anomalous':2.},{'mFo-DFc':0},{'mFo-DFc':-1},{'mFo-DFc':True},{'mFo-DFc':'1.5'},{'mFo-DFc':float('nan')},{'mFo-DFc':float('inf')},{'mFo-DFc':10**400}])
def test_invalid_or_unavailable_levels_refuse_before_native_work(tmp_path,monkeypatch,levels):
    owner,scene,calls,_=setup(tmp_path,monkeypatch)
    with pytest.raises(RecipeError):owner.perform('maps',scene,None,sigma_levels=levels)
    assert calls==[] and owner.cache=={}


def test_same_display_levels_reach_isolated_coot_copy(tmp_path,monkeypatch):
    owner,scene,_,run=setup(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(owner,'_coot',lambda profile,model,maps,*rest:calls.append(maps) or {})
    owner.perform('coot',scene,None,sigma_levels={'mFo-DFc':1.5,'2mFo-DFc':.8})
    assert [m['sigma'] for m in calls[0]]==[.8,1.5]
    assert [m.get('sigma') for p in owner.profiles.values() for m in p['maps']]==[None,None]
