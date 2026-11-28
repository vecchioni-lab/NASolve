"""Exact-source older recipes retain their identity at the acquisition boundary."""
from copy import deepcopy
import shutil

import pytest

from tests.test_cif_generation_acquisition import case
from tests.test_cif_generation_attempt import inventory


@pytest.fixture
def retained(case):
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary
    module,args,kwargs,calls,c,q=case
    root=args[0].parent
    options=dict(source_authority=kwargs['source_authority'],
        recipe={'policy_id':'OLDER_COMPLETE_NUMERICS'},
        generator={'name':'OLD_BUILDER','version':'OLD_VERSION'},consumer=kwargs['consumer'])
    provenance={'converged':None,'stopping':'NOT_REPORTED','notes':['Original producer limitation.'],
                'diagnostic':{'error':'Original post-write diagnostic'}}
    snapshot=root/'retained'
    resolve_qualified_dictionary(args[0],args[1],root/'old-store',snapshot,**options,
        acquire=lambda:dict(candidate=c,qualification=q,provenance=provenance))
    kwargs['retained_snapshot']=snapshot
    return case,snapshot,options,provenance


def test_exact_source_older_recipe_reuses_before_generation_without_relabelling(retained):
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot,lookup_dictionary,make_dictionary_request
    (module,args,kwargs,calls,*_),snapshot,options,provenance=retained
    old=resolve_dictionary_snapshot(snapshot);before=inventory(snapshot)
    kwargs['qualify']=None
    shutil.rmtree(kwargs['generation']['installation_root'])
    result=module.resolve_generated_dictionary(*args,**kwargs)
    saved=resolve_dictionary_snapshot(args[3])
    assert result['entry_id']==old['entry_id'] and calls==[] and inventory(snapshot)==before
    assert saved['manifest']['request']==old['manifest']['request'] and saved['provenance']==provenance
    new=make_dictionary_request(args[0],args[1],source_authority=kwargs['source_authority'],
                                **module.generation_dictionary_options(kwargs['generation']))
    assert lookup_dictionary(args[2],new,kwargs['consumer'])['status']=='MISS'
    assert not args[4].exists() and not args[5].exists()


def test_stale_retained_candidate_is_requalified_with_original_recipe_and_producer(retained):
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    (module,args,kwargs,calls,*_),snapshot,options,provenance=retained
    before=inventory(snapshot);kwargs['consumer']={**kwargs['consumer'],'version':'NEW'}
    result=module.resolve_generated_dictionary(*args,**kwargs)
    saved=resolve_dictionary_snapshot(args[3])
    assert calls==['qualify'] and inventory(snapshot)==before and not args[4].exists()
    assert saved['manifest']['request']['recipe']==options['recipe']
    assert saved['manifest']['request']['generator']==options['generator']
    assert saved['manifest']['consumer']==kwargs['consumer'] and saved['provenance']==provenance


def test_stale_retained_candidate_without_qualifier_is_read_only(retained):
    (module,args,kwargs,calls,*_),snapshot,*_=retained
    kwargs['consumer']={**kwargs['consumer'],'version':'NEW'};kwargs['qualify']=None
    before=inventory(args[0].parent)
    result=module.resolve_generated_dictionary(*args,**kwargs)
    assert result['status']=='REQUALIFICATION_REQUIRED' and calls==[]
    assert inventory(args[0].parent)==before


@pytest.mark.parametrize('defect',['source_bytes','charge','stereo','authority','policy','corrupt_dictionary','corrupt_qualification','snapshot_symlink','parent_symlink'])
def test_incompatible_retained_candidate_refuses_without_generation_or_writes(retained,defect):
    from tests.test_cif_stereochemistry_audit import write
    from nasolve.cif_stereochemistry_audit import _values
    (module,args,kwargs,calls,*_),snapshot,*_=retained
    if defect=='source_bytes':args[0].write_bytes(args[0].read_bytes()+b'\n# other exact source\n')
    elif defect in {'charge','stereo'}:
        v=_values(args[0],args[1]);v['_chem_comp_atom.charge' if defect=='charge' else '_chem_comp_atom.pdbx_stereo_config'][0]='1' if defect=='charge' else 'S';write(args[0],v)
    elif defect=='authority':kwargs['source_authority']='CURATED'
    elif defect=='policy':kwargs['generation']['bond_representation_policy']='cif-source-declared-neutral-purine-aromatic-v1'
    elif defect.startswith('corrupt_'):(snapshot/'entry'/('dictionary.cif' if defect=='corrupt_dictionary' else 'qualification.json')).write_text('corrupt')
    else:
        link=snapshot.with_name('link')
        link.symlink_to(snapshot if defect=='snapshot_symlink' else snapshot.parent,target_is_directory=True)
        kwargs['retained_snapshot']=link if defect=='snapshot_symlink' else link/snapshot.name
    before=inventory(args[0].parent)
    with pytest.raises((ValueError,OSError)):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==[] and inventory(args[0].parent)==before


@pytest.mark.parametrize('defect',['unusable','missing_check','raise','mutate_candidate','mutate_source','mutate_consumer','mutate_saved'])
def test_failed_retained_qualification_preserves_failure_and_never_generates(retained,defect):
    (module,args,kwargs,calls,c,q),snapshot,*_=retained
    kwargs['consumer']={**kwargs['consumer'],'version':'NEW'}
    source=args[0].read_bytes();candidate=(snapshot/'entry/dictionary.cif').read_bytes()
    def qualify(a,b,consumer,out):
        result=deepcopy(q)
        if defect=='unusable':result['native_usable']=False
        elif defect=='missing_check':result['checks'].pop(next(iter(result['checks'])))
        elif defect=='raise':raise RuntimeError('failed native evidence')
        elif defect=='mutate_candidate':b.write_text('damaged')
        elif defect=='mutate_source':a.write_text('damaged')
        elif defect=='mutate_consumer':consumer['version']='WRONG'
        else:(snapshot/'entry/provenance.json').write_text('damaged')
        return result
    kwargs['qualify']=qualify
    with pytest.raises((ValueError,RuntimeError)):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==[] and not args[4].exists() and not args[3].exists() and not args[2].exists()
    assert args[0].read_bytes()==source and (snapshot/'entry/dictionary.cif').read_bytes()==candidate
    assert (args[5]/'inputs/dictionary.cif').is_file()


def test_current_generation_recipe_cache_has_precedence_over_unused_retained_path(case):
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    module,args,kwargs,calls,*_=case
    first=module.resolve_generated_dictionary(*args,**kwargs)
    kwargs['retained_snapshot']=args[0].parent/'does-not-exist'
    second=args[3].with_name('second')
    result=module.resolve_generated_dictionary(*args[:3],second,args[4],args[5].with_name('unused'),**kwargs)
    assert result['entry_id']==first['entry_id'] and calls==['generate','qualify']


def test_retained_fallback_does_not_mutate_or_retry_an_exhausted_generation(retained):
    (module,args,kwargs,calls,*_),snapshot,*_=retained
    fallback=kwargs.pop('retained_snapshot');qualify=kwargs['qualify'];kwargs['generation']['max_attempts']=1
    kwargs['qualify']=lambda *a:(_ for _ in ()).throw(ValueError('failed qualification'))
    with pytest.raises(ValueError):module.resolve_generated_dictionary(*args,**kwargs)
    before=inventory(args[4]);kwargs.update(retained_snapshot=fallback,qualify=qualify)
    result=module.resolve_generated_dictionary(*args[:5],args[5].with_name('fallback-qualification'),**kwargs)
    assert calls==['generate'] and inventory(args[4])==before and result['converged'] is None


@pytest.mark.parametrize('index',[2,3,4,5])
def test_retained_snapshot_cannot_overlap_mutating_scopes(retained,index):
    (module,args,kwargs,calls,*_),snapshot,*_=retained;args=list(args)
    args[index]=snapshot/'nested'
    before=inventory(snapshot)
    with pytest.raises(ValueError,match='separate'):module.resolve_generated_dictionary(*args,**kwargs)
    assert calls==[] and inventory(snapshot)==before


def test_frozen_fallback_is_independent_of_previous_snapshot_and_cache(retained,tmp_path):
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    (module,args,kwargs,calls,*_),snapshot,*_=retained
    module.resolve_generated_dictionary(*args,**kwargs)
    destination=tmp_path/'relocated';shutil.copytree(args[3],destination);before=inventory(destination)
    for p in (snapshot,args[2],args[3],kwargs['generation']['installation_root']):shutil.rmtree(p)
    args[0].unlink()
    assert resolve_dictionary_snapshot(destination)['qualification']['native_usable'] is True
    assert inventory(destination)==before


@pytest.mark.parametrize('has_qualifier',[False,True])
def test_old_native_policy_requires_requalification_even_with_same_consumer(retained,has_qualifier):
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot,_payload,_freeze
    (module,args,kwargs,calls,c,q),snapshot,options,provenance=retained
    saved=resolve_dictionary_snapshot(snapshot);legacy=deepcopy(q)
    legacy['policy_id']='cif-isolated-candidate-native-usability-v1'
    manifest,data=_payload(saved['manifest']['request'],args[0],c,legacy,kwargs['consumer'],provenance,
                           allow_stale_qualification=True)
    old=snapshot.with_name('old-policy')
    _freeze(old,manifest,data,origin='REUSED',persistent_store='AVAILABLE',notes=[])
    kwargs['retained_snapshot']=old
    if not has_qualifier:kwargs['qualify']=None
    before=inventory(old);result=module.resolve_generated_dictionary(*args,**kwargs)
    assert inventory(old)==before and not args[4].exists()
    if has_qualifier:
        assert calls==['qualify'] and resolve_dictionary_snapshot(args[3])['qualification_current']
    else:assert result['status']=='REQUALIFICATION_REQUIRED' and calls==[] and not args[3].exists()


@pytest.mark.parametrize('policy',['cif-source-declared-neutral-purine-aromatic-v1',
                                 'cif-source-declared-neutral-6-oxo-purine-aromatic-v1'])
def test_explicit_representation_qualified_snapshot_keeps_original_permission(case,tmp_path,policy):
    from tests.test_cif_dictionary_policy import inputs as policy_inputs
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot,resolve_qualified_dictionary
    module,args,kwargs,calls,*_=case
    folder=tmp_path/'policy-input';folder.mkdir()
    s,c,m,n,q,options,request,provenance=policy_inputs(folder,policy)
    args[0].write_bytes(s.read_bytes());snapshot=tmp_path/'policy-snapshot'
    options['source_authority']=kwargs['source_authority'];options['consumer']=kwargs['consumer']
    resolve_qualified_dictionary(s,'Q17',folder/'store',snapshot,**options,
        acquire=lambda:dict(candidate=c,qualification=q,provenance=provenance))
    kwargs['generation']['bond_representation_policy']=policy
    kwargs['retained_snapshot']=snapshot;kwargs['consumer']={**kwargs['consumer'],'version':'NEW'}
    kwargs['qualify']=lambda *a:deepcopy(q)
    module.resolve_generated_dictionary(*args,**kwargs)
    saved=resolve_dictionary_snapshot(args[3])
    assert saved['manifest']['request']['recipe']==options['recipe']
    assert saved['qualification']['policy_id']=='cif-isolated-candidate-native-usability-v3'
    assert calls==[] and not args[4].exists()


def test_original_recipe_cache_qualifies_before_explicit_retained_import(retained):
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary,resolve_dictionary_snapshot
    (module,args,kwargs,calls,c,q),snapshot,options,provenance=retained
    kwargs['consumer']={**kwargs['consumer'],'version':'NEW'}
    # A prior qualification of the original recipe for this consumer already
    # exists in the current store; do not rerun native work for the older snapshot.
    result=resolve_qualified_dictionary(args[0],args[1],args[2],args[3].with_name('already-qualified'),
        **{**options,'consumer':kwargs['consumer']},
        acquire=lambda:dict(candidate=c,qualification=q,provenance=provenance))
    kwargs['qualify']=lambda *a:pytest.fail('Original recipe already qualified')
    final=module.resolve_generated_dictionary(*args,**kwargs)
    assert final['status']=='REUSED' and final['entry_id']==result['entry_id'] and calls==[]
    assert not args[4].exists() and not args[5].exists()
