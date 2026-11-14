"""Owned support intake/recovery; fake native generation is contract evidence only."""
import json
from unittest.mock import patch
import pytest
from tests.test_cif_plane_generation import plane_generation
from tests.test_cif_repair_attempt import setup, inventory


@pytest.fixture
def support(tmp_path, monkeypatch):
    from nasolve import cif_prepared_repair_execution as execution
    source,dictionary,request,_=plane_generation(tmp_path/'generator')
    bundle=tmp_path/'prepared';bundle.mkdir();(bundle/'source.cif').write_bytes(source.read_bytes())
    monkeypatch.setattr(execution,'read_dictionary_bundle',lambda p:dict(report=dict(components=['Q17'])))
    monkeypatch.setattr(execution,'resolve_dictionary_snapshot',lambda p:dict(source=p.parents[2]/'source.cif'))
    declarations={'Q17':dict(request_directory=request,attempt_number=1)}
    return execution,bundle,declarations


def test_owned_support_is_exact_bounded_and_relocatable(support,tmp_path):
    m,bundle,decl=support;source=decl['Q17']['request_directory'];before=inventory(source)
    record,files=m._plane_support_snapshot(bundle,decl)
    assert record['choices']=={'Q17':1} and record['policy_id']==m.PLANE_SUPPORT_POLICY
    assert all(record['files'][name]['size']==len(data) for name,data in files.items())
    moved=source.rename(tmp_path/'moved')
    decl['Q17']['request_directory']=moved
    with patch('subprocess.Popen',side_effect=AssertionError('Read must not execute')):
        assert m._plane_support_snapshot(bundle,decl)==(record,files)
    assert inventory(moved)==before


@pytest.mark.parametrize('defect',['component','attempt','extra','changed-source','changed-support','symlink','file-bound','byte-bound','unknown-work'])
def test_invalid_support_never_becomes_optional_chemistry(support,monkeypatch,defect):
    from nasolve import cif_component_runtime as frozen
    from nasolve import cif_generation_attempt as generation
    m,bundle,decl=support;request=decl['Q17']['request_directory']
    if defect=='component':decl['other']=decl.pop('Q17')
    elif defect=='attempt':decl['Q17']['attempt_number']=True
    elif defect=='extra':decl['Q17']['latest']=True
    elif defect=='changed-source':(bundle/'source.cif').write_text('different')
    elif defect=='changed-support':
        p=request/'attempts/attempt-0001/generation/candidate.cif';p.write_bytes(p.read_bytes()+b'changed')
    elif defect=='symlink':(request/'link').symlink_to(bundle/'source.cif')
    elif defect=='file-bound':monkeypatch.setattr(frozen,'MAX_FILES',1)
    elif defect=='byte-bound':monkeypatch.setattr(frozen,'MAX_BYTES',1)
    else:
        original=generation.inspect_source_generation_request
        def unknown(p):
            state=original(p);state['attempts'][-1].update(state='UNKNOWN',activity=None);return state
        monkeypatch.setattr(generation,'inspect_source_generation_request',unknown)
    before=inventory(request)
    with pytest.raises((ValueError,AssertionError)):m._plane_support_snapshot(bundle,decl)
    assert inventory(request)==before


def supported_request(setup,support,monkeypatch):
    m,args,options,calls=setup;execution,bundle,decl=support
    (args[0]/'source.cif').write_bytes((bundle/'source.cif').read_bytes())
    original=m.execute_prepared_dictionary_repair
    def execute(*a,**kw):
        value=original(*a,**kw)
        cfg,_=execution._plane_support_snapshot(a[0],kw['plane_support'])
        value['plane_support']=cfg
        (a[2]/'repair_execution.json').write_text(json.dumps(value))
        return value
    monkeypatch.setattr(m,'execute_prepared_dictionary_repair',execute)
    return m,args,dict(options,plane_support=decl),calls


def test_plane_choice_is_frozen_across_fresh_attempts_and_cold_reads(setup,support,monkeypatch,tmp_path):
    m,args,options,calls=supported_request(setup,support,monkeypatch)
    first=m.execute_prepared_dictionary_repair_attempt(*args,**options)
    saved=inventory(args[2]/'attempts/attempt-0001')
    second=m.execute_prepared_dictionary_repair_attempt(*args,**options)
    assert first['request_id']==second['request_id'] and first['attempt_id']!=second['attempt_id']
    assert inventory(args[2]/'attempts/attempt-0001')==saved
    moved=args[2].rename(tmp_path/'moved-request')
    source=options['plane_support']['Q17']['request_directory'];source.rename(tmp_path/'moved-original-support')
    with patch('subprocess.Popen',side_effect=AssertionError('No cold execution')):
        state=m.inspect_prepared_repair_request(moved)
    assert state['availability']=='EXHAUSTED' and all(a['state']=='STOPPED' for a in state['attempts'])
    assert state['request']['configuration']['plane_support']['choices']=={'Q17':1}


@pytest.mark.parametrize('defect',['drop-report','changed-report','changed-frozen','dropped-intent'])
def test_support_identity_cannot_be_dropped_or_changed(setup,support,monkeypatch,defect):
    from nasolve.campaign_records import read_record,write_record
    m,args,options,calls=supported_request(setup,support,monkeypatch)
    m.execute_prepared_dictionary_repair_attempt(*args,**options)
    report=args[2]/'attempts/attempt-0001/execution/repair_execution.json'
    if defect in {'drop-report','changed-report'}:
        value=json.loads(report.read_text())
        if defect=='drop-report':value.pop('plane_support')
        else:value['plane_support']['choices']['Q17']=2
        report.write_text(json.dumps(value))
    elif defect=='changed-frozen':
        p=args[2]/'inputs/plane-support/Q17/inputs/source.cif';p.write_bytes(p.read_bytes()+b'changed')
    else:
        p=args[2]/'request.json';record=read_record(p);record['configuration'].pop('plane_support');write_record(p,record,replace=True)
    before=inventory(args[2])
    with pytest.raises(ValueError):m.inspect_prepared_repair_request(args[2])
    assert inventory(args[2])==before and len(calls)==1


def test_plane_support_overlap_refuses_before_request_or_executor_writes(support,tmp_path):
    from types import SimpleNamespace
    from nasolve import cif_repair_attempt as attempt
    m,bundle,decl=support;request=decl['Q17']['request_directory'];before=inventory(request)
    sdk=SimpleNamespace(root=tmp_path/'sdk',executables={})
    with pytest.raises(ValueError,match='separate from plane support'):
        m.execute_prepared_dictionary_repair(bundle,sdk,request/'nested',plane_support=decl)
    with pytest.raises(ValueError,match='separate from plane support'):
        attempt.execute_prepared_dictionary_repair_attempt(bundle,sdk,request/'nested',plane_support=decl)
    assert inventory(request)==before


@pytest.mark.parametrize('defect',[None,'proposal','candidate','slot','source','code','number','reference','attempt','extra','schema'])
def test_failed_plane_candidate_rebuilds_exactly_before_any_fallback(support,tmp_path,monkeypatch,defect):
    from hashlib import sha256
    import shutil
    from nasolve import cif_prepared_repair_failure as failure
    from nasolve.cif_plane_generation import prepare_owned_trigonal_plane_candidate
    execution,bundle,decl=support
    root=tmp_path/'failed-plane';root.mkdir();bundle=bundle.rename(root/'bundle')
    generation=decl['Q17']['request_directory']
    shutil.copytree(generation,root/'plane-support/Q17')
    (root/'plan').mkdir();dictionary=root/'plan/0.cif'
    shutil.copyfile(tmp_path/'generator/inputs/dictionary.cif',dictionary)
    source=bundle/'source.cif'
    prepared=dict(report=dict(components=['Q17']),after_dictionaries=[dictionary],component_dictionaries={'Q17':dictionary})
    monkeypatch.setattr(failure,'resolve_dictionary_snapshot',lambda p:dict(source=p.parents[2]/'source.cif'))
    candidate=root/'plane-candidates/000.cif'
    proposal=prepare_owned_trigonal_plane_candidate(source,dictionary,'Q17',root/'plane-support/Q17',1,candidate)
    row=dict(schema_version=1,policy_id='cif-prepared-plane-stage-v1',component='Q17',dictionary_index=0,
        attempt_number=1,native_number=1,proposal=proposal,candidate=dict(anchor='repair_directory',
        path='plane-candidates/000.cif',size=candidate.stat().st_size,sha256=sha256(candidate.read_bytes()).hexdigest()))
    plan=dict(steps=[],final_dictionaries=[dict(path='0.cif')])
    if defect=='proposal':row['proposal']['candidate_sha256']='0'*64
    elif defect=='candidate':candidate.write_bytes(candidate.read_bytes()+b'changed')
    elif defect=='slot':row['dictionary_index']=True
    elif defect=='source':source.write_bytes(source.read_bytes()+b'changed')
    elif defect=='code':row['component']='OTHER'
    elif defect=='number':row['native_number']=2
    elif defect=='reference':row['candidate']['path']='../outside'
    elif defect=='attempt':row['attempt_number']=True
    elif defect=='schema':row['schema_version']=True
    (candidate.with_suffix('.json')).write_text(json.dumps(row))
    if defect=='extra':(root/'plane-candidates/001.json').write_text(json.dumps(row))
    before=inventory(root)
    with patch('subprocess.Popen',side_effect=AssertionError('Failure read must not execute')):
        if defect is None:
            paths,manifest=failure._plane_failure_dictionaries(root,prepared,plan,1)
            assert paths==[candidate] and manifest==candidate.with_suffix('.json')
        else:
            with pytest.raises(ValueError):failure._plane_failure_dictionaries(root,prepared,plan,1)
    assert inventory(root)==before


@pytest.mark.parametrize('bound',['MAX_FILES','MAX_BYTES'])
def test_combined_support_limit_stops_before_reading_more_components(tmp_path,monkeypatch,bound):
    from nasolve import cif_prepared_repair_execution as m
    from nasolve import cif_component_runtime as frozen
    from nasolve import cif_generation_attempt as generation
    codes=['Q17','R18','S19'];requests={c:tmp_path/c for c in codes}
    for p in requests.values():p.mkdir()
    monkeypatch.setattr(m,'read_dictionary_bundle',lambda p:dict(report=dict(components=codes)))
    monkeypatch.setattr(m,'resolve_dictionary_snapshot',lambda p:dict(source=tmp_path/'source'))
    monkeypatch.setattr(m,'read_owned_plane_support',lambda *a:None)
    monkeypatch.setattr(generation,'inspect_source_generation_request',lambda p:dict(attempts=[dict(state='STOPPED',activity=False)]))
    read=[]
    def tree(p):
        assert p.name!='S19','Combined limit must stop before loading a third support tree'
        read.append(p.name);return {'one':b'1'}
    monkeypatch.setattr(m,'_tree',tree);monkeypatch.setattr(frozen,bound,1)
    with pytest.raises(ValueError,match='Combined plane support exceeds'):
        m._plane_support_snapshot(tmp_path,{c:dict(request_directory=p,attempt_number=1) for c,p in requests.items()})
    assert set(read)=={'Q17','R18'}
