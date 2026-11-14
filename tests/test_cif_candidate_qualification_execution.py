"""Synthetic native transport exercises orchestration; actual SDK evidence is separate."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from tests.test_cif_candidate_usability import native_case
from tests.test_cif_repair_process import inventory


@pytest.fixture
def case(tmp_path, monkeypatch):
    from nasolve import cif_candidate_qualification_execution as m
    from nasolve.cif_postmr_cache import _API, _ENERGY
    from nasolve.cif_native_validation import inspect_native_bundle
    s,c,model,native=native_case(tmp_path)
    consumer=dict(name='Phenix/CCTBX',version='SYNTHETIC',executable_sha256=sha256(Path(sys.executable).read_bytes()).hexdigest())
    for field,rows in [('api_sources',_API),('energy_sources',_ENERGY)]:
        consumer[field]=[dict(anchor='phenix_installation',path='lib/python/site-packages/'+name,sha256='a'*64) for name in rows]
    native.update(automatic_adoption=False,scientific_approval='NOT_RUN',model_editing='NOT_RUN',optimization='NOT_RUN',readyset_retry='NOT_RUN',
        dictionary_loading=[dict(status='RECORDED',input='inputs/001_dictionary.cif')],phil_adaptations=[dict(input='inputs/002_phil.phil')],
        installed_api_sources=[dict(historical_path='/synthetic/'+r['path'],sha256=r['sha256']) for r in consumer['api_sources']])
    native['geometry'].update(simple_bonds=[],asu_bonds=[])
    native['energy_inventory']['installed_sources']=[dict(historical_path='/synthetic/'+r['path'],sha256=r['sha256']) for r in consumer['energy_sources']]
    sdkroot=tmp_path/'sdk';sdkroot.mkdir();sdk=SimpleNamespace(root=sdkroot,version='SYNTHETIC',executables={'phenix.python':Path(sys.executable),'phenix.ready_set':sdkroot/'ready'},environment=dict(os.environ))
    calls=[]
    def capture(*args,**kwargs):
        calls.append(kwargs['timeout_seconds']);runner=kwargs['_process_runner'];data=deepcopy(native)
        def synthetic(command,**options):
            script="from pathlib import Path;Path('native_validation.json').write_text("+repr(json.dumps(data))+")"
            return runner([sys.executable,'-c',script],**options)
        return inspect_native_bundle(*args,**dict(kwargs,_process_runner=synthetic))
    monkeypatch.setattr(m,'verify_current_consumer',lambda *a:True)
    monkeypatch.setattr(m,'inspect_native_bundle',capture)
    args=(s,c,'Q17',consumer,sdk,tmp_path/'qualification')
    return m,args,calls,native


def test_both_seeds_qualified_and_non_mutating_readback(case):
    m,args,calls,native=case;report=m.execute_candidate_qualification(*args,native_timeout_seconds=5,total_timeout_seconds=20)
    assert len(calls)==2 and report['qualification']['native_usable'] and report['same_covalent_proxies']
    before=inventory(args[-1]);assert m.read_candidate_qualification(args[-1])==report
    assert inventory(args[-1])==before and not report['automatic_adoption']


@pytest.mark.parametrize('options',[{'native_timeout_seconds':True},{'total_timeout_seconds':0},{'total_timeout_seconds':None}])
def test_invalid_limits_fail_without_output(case,options):
    m,args,calls,native=case
    with pytest.raises(ValueError):m.execute_candidate_qualification(*args,**options)
    assert not args[-1].exists() and not calls


@pytest.mark.parametrize('boundary',['preflight','preparation','first_native','second_native','derivation','publication'])
def test_one_allowance_withholds_late_work(case,monkeypatch,boundary):
    m,args,calls,native=case;clock=[0.];monkeypatch.setattr(m,'monotonic',lambda:clock[0])
    verify=m.verify_current_consumer;build=m.write_component_control_model;capture=m.inspect_native_bundle;derive=m._derive;inv=m._inventory
    if boundary=='preflight':
        def check(*a):clock[0]=21.;return True
        monkeypatch.setattr(m,'verify_current_consumer',check)
    elif boundary=='preparation':
        def model(*a):result=build(*a);clock[0]=21.;return result
        monkeypatch.setattr(m,'write_component_control_model',model)
    elif boundary in {'first_native','second_native'}:
        def run(*a,**k):
            result=capture(*a,**k)
            if len(calls)==(1 if boundary=='first_native' else 2):clock[0]=21.
            return result
        monkeypatch.setattr(m,'inspect_native_bundle',run)
    elif boundary=='derivation':
        def late(*a):result=derive(*a);clock[0]=21.;return result
        monkeypatch.setattr(m,'_derive',late)
    else:
        def late(*a):result=inv(*a);clock[0]=21.;return result
        monkeypatch.setattr(m,'_inventory',late)
    with pytest.raises(m.CandidateQualificationBudgetExceeded):m.execute_candidate_qualification(*args,total_timeout_seconds=20)
    assert not (args[-1]/m.REPORT).exists()
    assert len(calls)=={'preflight':0,'preparation':0,'first_native':1,'second_native':2,'derivation':2,'publication':2}[boundary]
    if boundary=='preflight':assert not args[-1].exists()
    else:
        from nasolve.cif_candidate_qualification import inspect_candidate_qualification_processes
        assert inspect_candidate_qualification_processes(args[-1])['state']=='STOPPED'


def test_next_job_receives_only_whole_seconds_remaining(case,monkeypatch):
    m,args,calls,native=case;clock=[0.];monkeypatch.setattr(m,'monotonic',lambda:clock[0]);capture=m.inspect_native_bundle
    def run(*a,**k):
        result=capture(*a,**k);clock[0]+=3.2;return result
    monkeypatch.setattr(m,'inspect_native_bundle',run)
    m.execute_candidate_qualification(*args,native_timeout_seconds=90,total_timeout_seconds=10)
    assert calls==[10,6]


@pytest.mark.parametrize('seed',[0,1])
def test_each_seed_must_be_independently_usable(case,monkeypatch,seed):
    m,args,calls,native=case;capture=m.inspect_native_bundle
    def run(*a,**k):
        if len(calls)==seed:native['geometry']['proxy_details']['bond_simple'][0]['distance_ideal']=9.
        return capture(*a,**k)
    monkeypatch.setattr(m,'inspect_native_bundle',run)
    with pytest.raises(ValueError,match='not natively usable'):m.execute_candidate_qualification(*args)
    assert not (args[-1]/m.REPORT).exists()


def test_two_usable_seeds_with_different_proxy_identity_are_refused(case,monkeypatch):
    m,args,calls,native=case;capture=m.inspect_native_bundle
    def run(*a,**k):
        if len(calls)==1:native['geometry']['proxy_details']['bond_simple'][0]['origin_id']=7
        return capture(*a,**k)
    monkeypatch.setattr(m,'inspect_native_bundle',run)
    with pytest.raises(ValueError,match='signatures differ'):m.execute_candidate_qualification(*args)
    assert not (args[-1]/m.REPORT).exists()


@pytest.mark.parametrize('change',['source','candidate','consumer','frozen_model','frozen_policy'])
def test_changed_inputs_or_consumer_prevent_success(case,monkeypatch,change):
    m,args,calls,native=case;capture=m.inspect_native_bundle
    def run(*a,**k):
        result=capture(*a,**k)
        if len(calls)==2:
            if change in {'source','candidate'}:args[0 if change=='source' else 1].write_bytes(b'changed')
            elif change=='consumer':monkeypatch.setattr(m,'verify_current_consumer',lambda *a:False)
            else:
                path=args[-1]/'inputs'/('models/source.pdb' if change=='frozen_model' else 'isolated.phil');path.write_bytes(b'changed')
        return result
    monkeypatch.setattr(m,'inspect_native_bundle',run)
    with pytest.raises(ValueError):m.execute_candidate_qualification(*args)
    assert not (args[-1]/m.REPORT).exists()


@pytest.mark.parametrize('failure',['interrupt','timeout','publication'])
def test_native_failure_preserves_partial_evidence_without_success(case,monkeypatch,failure):
    m,args,calls,native=case;capture=m.inspect_native_bundle
    if failure=='publication':
        def save(*a,**k):raise OSError('final publication failed')
        monkeypatch.setattr(m,'write_record',save)
    else:
        def run(*a,**k):
            if failure=='interrupt':raise KeyboardInterrupt('operator interruption')
            # A real owned worker must be killed and its partial output retained.
            work=args[-1]/'native/000/partial';work.mkdir(parents=True)
            k['_process_runner']([sys.executable,'-c',"import time;from pathlib import Path;Path('partial').write_text('keep');time.sleep(30)"],cwd=work,log_path=work/'native.log',environment=dict(os.environ),timeout_seconds=.2)
        monkeypatch.setattr(m,'inspect_native_bundle',run)
    error=KeyboardInterrupt if failure=='interrupt' else subprocess.TimeoutExpired if failure=='timeout' else OSError
    with pytest.raises(error):m.execute_candidate_qualification(*args)
    assert not (args[-1]/m.REPORT).exists()
    from nasolve.cif_candidate_qualification import inspect_candidate_qualification_processes
    state=inspect_candidate_qualification_processes(args[-1]);assert state['state']=='STOPPED' and not state['retry_authorized']
    if failure=='timeout':assert (args[-1]/'native/000/partial/partial').read_text()=='keep'


def resign(m,root,edit):
    from nasolve.campaign_records import read_record,write_record
    report=read_record(root/m.REPORT);edit(report)
    report['outputs']=m._inventory(root);write_record(root/m.REPORT,report,replace=True)


@pytest.mark.parametrize('defect',['claim','seed_claim','one_seed','swapped_seeds','other_consumer','timeout','extra_claim','model_seed','capture_spec','input_dictionary','worker','native_proxy','job_binding'])
def test_reader_rederives_even_after_outer_report_is_resigned(case,defect):
    m,args,calls,native=case;report=m.execute_candidate_qualification(*args);root=args[-1]
    def edit(r):
        if defect=='claim':r['qualification']['checks']['exact_active_bonds']=False
        elif defect=='seed_claim':r['seed_qualifications'][1]['native_usable']=False
        elif defect=='one_seed':r['native_receipts']=r['native_receipts'][:1]
        elif defect=='swapped_seeds':r['native_receipts'].reverse()
        elif defect=='timeout':r['elapsed_seconds']=180
        elif defect=='extra_claim':r['refinement_approved']=True
    if defect in {'other_consumer','model_seed'}:
        path=root/'inputs'/('protocol.json' if defect=='other_consumer' else 'models/source.pdb')
        if defect=='other_consumer':v=json.loads(path.read_bytes());v['consumer']['version']='different';path.write_text(json.dumps(v))
        else:path.write_text(path.read_text().replace('   0.000','   2.000'))
    elif defect in {'capture_spec','input_dictionary','worker','native_proxy'}:
        capture=root/report['native_receipts'][0]['path'];folder=capture.parent
        filename={'capture_spec':'native_spec.json','input_dictionary':'inputs/001_dictionary.cif','worker':'native_worker.py','native_proxy':'native_validation.json'}[defect]
        path=folder/filename;path.write_bytes(path.read_bytes()+b'changed')
    elif defect=='job_binding':
        from nasolve.campaign_records import read_record,write_record
        path=root/'ownership/phases/native-000/job.json';v=read_record(path);v['qualification_sha256']='0'*64;write_record(path,v,replace=True)
    resign(m,root,edit)
    with pytest.raises((ValueError,RuntimeError)):m.read_candidate_qualification(root)


def test_readback_relocates_without_sdk_execution_or_original_inputs(case,monkeypatch):
    import shutil
    m,args,calls,native=case;report=m.execute_candidate_qualification(*args);original=args[-1];moved=original.with_name('relocated');original.rename(moved)
    args[0].unlink();args[1].unlink();shutil.rmtree(args[4].root)
    def forbidden(*a,**k):raise AssertionError('Readback must not launch or write')
    monkeypatch.setattr(subprocess,'Popen',forbidden);monkeypatch.setattr(m,'write_record',forbidden);monkeypatch.setattr(m,'verify_current_consumer',forbidden)
    before=inventory(moved);assert m.read_candidate_qualification(moved)==report
    assert inventory(moved)==before and not original.exists()


def test_callback_returns_unchanged_store_qualification_and_is_lazy(case,monkeypatch):
    m,args,calls,native=case;source,candidate,code,consumer,sdk,out=args
    callback=m.make_candidate_qualifier(sdk,code,native_timeout_seconds=5,total_timeout_seconds=20)
    assert not calls and not out.exists()
    result=callback(source,candidate,consumer,out)
    report=m.read_candidate_qualification(out);assert result==report['seed_qualifications'][0]
    assert result['policy_id']=='cif-isolated-candidate-native-usability-v2' and result['scope']=='ISOLATED_COMPONENT_ONLY'


def test_existing_output_is_never_reused(case):
    m,args,calls,native=case;m.execute_candidate_qualification(*args);before=inventory(args[-1])
    with pytest.raises(FileExistsError):m.execute_candidate_qualification(*args)
    assert inventory(args[-1])==before and len(calls)==2


def test_explicit_representation_permission_reaches_every_scientific_check(case,monkeypatch):
    m,args,calls,native=case;seen=[];assess=m.reassess_complete_candidate;qualify=m.qualify_candidate_native
    def a(*a,**k):seen.append(k['bond_representation_policy']);return assess(*a)
    def q(*a,**k):seen.append(k['bond_representation_policy']);return qualify(*a)
    monkeypatch.setattr(m,'reassess_complete_candidate',a);monkeypatch.setattr(m,'qualify_candidate_native',q)
    m.execute_candidate_qualification(*args,bond_representation_policy='TEST_EXPLICIT_PERMISSION')
    m.read_candidate_qualification(args[-1]);assert seen==['TEST_EXPLICIT_PERMISSION']*5



def test_callback_feeds_existing_store_and_cache_hit_runs_nothing(case):
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary, resolve_dictionary_snapshot
    m,args,calls,native=case;s,c,code,consumer,sdk,out=args
    callback=m.make_candidate_qualifier(sdk,code)
    options=dict(source_authority='EXPLICIT',recipe={'policy_id':'TEST_NUMERICS'},generator={'name':'SYNTHETIC','version':'TEST'},consumer=consumer)
    def acquire():return dict(candidate=c,qualification=callback(s,c,consumer,out),provenance={'converged':None,'stopping':'NOT_REPORTED','notes':['Synthetic transport only.']})
    store=out.with_name('store');first=out.with_name('first');second=out.with_name('second')
    result=resolve_qualified_dictionary(s,code,store,first,acquire=acquire,**options)
    def forbidden():raise AssertionError('Cache hit invoked qualification')
    hit=resolve_qualified_dictionary(s,code,store,second,acquire=forbidden,**options)
    assert hit['entry_id']==result['entry_id'] and hit['status']=='REUSED' and len(calls)==2
    assert resolve_dictionary_snapshot(second)['qualification']==m.read_candidate_qualification(out)['qualification']


def test_outer_shrink_reaches_second_seed_and_elapsed_stays_local(case,monkeypatch):
    m,args,calls,native=case;clock=[0.];cap=[8.];monkeypatch.setattr(m,'monotonic',lambda:clock[0]);capture=m.inspect_native_bundle
    def run(*a,**k):r=capture(*a,**k);clock[0]+=1;cap[0]=3.;return r
    monkeypatch.setattr(m,'inspect_native_bundle',run)
    r=m.execute_candidate_qualification(*args,total_timeout_seconds=30,_remaining_seconds=lambda:cap[0])
    assert calls==[8,3] and r['elapsed_seconds']==2
    assert m.read_candidate_qualification(args[-1])==r


def test_outer_expiry_after_first_seed_withholds_second_and_receipt(case,monkeypatch):
    m,args,calls,native=case;cap=[8.];capture=m.inspect_native_bundle
    def run(*a,**k):r=capture(*a,**k);cap[0]=0.;return r
    monkeypatch.setattr(m,'inspect_native_bundle',run)
    with pytest.raises(TimeoutError):m.execute_candidate_qualification(*args,_remaining_seconds=lambda:cap[0])
    assert len(calls)==1 and not (args[-1]/m.REPORT).exists()
    from nasolve.cif_candidate_qualification import inspect_candidate_qualification_processes
    assert inspect_candidate_qualification_processes(args[-1])['state']=='STOPPED'


@pytest.mark.parametrize('seed', [0, 1])
@pytest.mark.parametrize('wrong_owner', [False, True])
def test_failed_native_seed_is_not_misreported_as_lost_ownership(case, monkeypatch, seed, wrong_owner):
    m, args, calls, native = case
    from nasolve.cif_native_validation import inspect_native_bundle
    from nasolve.cif_candidate_qualification import inspect_candidate_qualification_processes
    inputs = [p.read_bytes() for p in args[:2]]
    def capture(*a, **k):
        failing = len(calls) == seed; calls.append(k['timeout_seconds'])
        data = deepcopy(native)
        if failing: data.update(status='FAILED', error='Synthetic native interpretation refusal')
        runner = k['_process_runner']
        def synthetic(command, **options):
            script = "from pathlib import Path;Path('native_validation.json').write_text(" + repr(json.dumps(data)) + ");raise SystemExit(" + str(2 if failing else 0) + ")"
            return runner([sys.executable, '-c', script], **options)
        return inspect_native_bundle(*a, **dict(k, _process_runner=synthetic))
    monkeypatch.setattr(m, 'inspect_native_bundle', capture)
    if wrong_owner:
        derive = m._derive
        def other_owner(root, refs, state):
            state = deepcopy(state)
            state['phases']['native-000']['job']['cwd']['path'] = 'another-native-directory'
            return derive(root, refs, state)
        monkeypatch.setattr(m, '_derive', other_owner)
    match = 'ownership' if wrong_owner else 'Native qualification failed for ' + ('source' if seed == 0 else 'candidate') + ' seed'
    with pytest.raises(ValueError, match=match) as caught:
        m.execute_candidate_qualification(*args)
    if not wrong_owner:
        assert 'FAILED, return code 2' in str(caught.value)
        assert 'native_receipt.json' in str(caught.value) and str(args[-1]) in str(caught.value)
        assert 'ownership' not in str(caught.value).lower()
    assert len(calls) == 2 and [p.read_bytes() for p in args[:2]] == inputs
    assert not (args[-1]/m.REPORT).exists()
    state = inspect_candidate_qualification_processes(args[-1])
    assert state['state'] == 'STOPPED' and state['finished']['outcome'] == 'RAISED'
    assert state['retry_authorized'] is False
    for row in state['phases'].values():
        assert row['state'] == 'STOPPED'
        assert (args[-1]/row['job']['cwd']['path']/'native_receipt.json').is_file()
