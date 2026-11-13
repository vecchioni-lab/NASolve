"""Owned plane support reuses saved native builds; fake SDKs test contracts."""
from hashlib import sha256
import json
from pathlib import Path
import pytest


def generated(tmp_path, monkeypatch, owned=True):
    from tests.test_cif_source_candidate import test_owned_complete_builder_keeps_output_even_without_convergence_or_success_exit
    test_owned_complete_builder_keeps_output_even_without_convergence_or_success_exit(tmp_path,monkeypatch,"multiple_planes",owned)
    request=tmp_path/"generation"
    directory=request/"attempts/attempt-0001/generation" if owned else request
    return request,directory


@pytest.mark.parametrize("owned",[False,True])
def test_completed_multiple_plane_receipt_replays_without_sdk(tmp_path,monkeypatch,owned):
    from nasolve.cif_source_representation import read_multiple_plane_candidate
    request,directory=generated(tmp_path,monkeypatch,owned)
    report=json.loads((directory/"source_candidate_receipt.json").read_text())
    old={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in request.rglob("*") if p.is_file()}
    assert read_multiple_plane_candidate(directory)==report
    assert report["stopping"]["status"]=="NOT_CONVERGED_REPORTED"
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in old.items())


def rebound(directory, change):
    """Change scalar evidence and rehash it, so replay must inspect semantics."""
    report=json.loads((directory/'source_candidate_receipt.json').read_text())
    change(report)
    for row in report['outputs']:
        path=directory/row['path'];row.update(sha256=sha256(path.read_bytes()).hexdigest(),size=path.stat().st_size)
    (directory/'source_candidate_receipt.json').write_text(json.dumps(report))


@pytest.mark.parametrize('defect',['choice','option','policy','worker','source','spec','charge_proof','reader_edge',
    'conversion','finished_charge','finished_edge','dispatch','execution','builder','stopping','extra_file'])
def test_replay_refuses_rehashed_contradictions(tmp_path,monkeypatch,defect):
    from nasolve.cif_source_representation import read_multiple_plane_candidate
    _,directory=generated(tmp_path,monkeypatch,False)
    def change(report):
        if defect=='choice':report['multiple_planes']=False
        elif defect=='option':report['multiple_planes_option']='--invented'
        elif defect=='policy':report['policy_id']='cif-source-native-complete-candidate-v1'
        elif defect=='worker':
            p=directory/'candidate_worker.py';p.write_text(p.read_text()+'\n# changed\n')
        elif defect=='source':
            p=directory/'source.cif';p.write_text(p.read_text()+'\n# changed\n')
        elif defect=='spec':
            p=directory/'candidate_spec.json';v=json.loads(p.read_text());v['arguments'].remove('--multiple_planes');p.write_text(json.dumps(v))
        elif defect=='execution':report['execution']['status']='FAILED'
        elif defect=='stopping':report['stopping']['status']='CONVERGED'
        elif defect=='extra_file':(directory/'hidden.txt').write_text('unexpected')
        else:
            result=report['result']
            if defect=='charge_proof':result['charge_control']['before']['atoms'][0]['native_atom_charge']=1
            elif defect=='reader_edge':result['reader']['bonds'][0]['native_order']=2
            elif defect=='conversion':result['builder']['before']['atoms'][0]['xyz'][0]+=1
            elif defect=='finished_charge':result['builder']['after']['atoms'][0]['native_atom_charge']=1
            elif defect=='finished_edge':result['builder']['after']['bonds'][0]['native_order']=2
            elif defect=='dispatch':result['reader']['dispatch_is_chemical_components']=False
            elif defect=='builder':result['builder']['status']='EXCEPTION'
            (directory/'candidate_result.json').write_text(json.dumps(result))
    rebound(directory,change)
    with pytest.raises(ValueError):read_multiple_plane_candidate(directory)


def test_combined_representation_and_multiple_planes_replays_without_weakening_either(tmp_path):
    from tests.test_cif_source_representation import fake_generation
    from nasolve.cif_source_representation import read_multiple_plane_candidate,read_representation_candidate
    directory,report=fake_generation(tmp_path,multiple_planes=True)
    assert read_multiple_plane_candidate(directory)==report
    with pytest.raises(ValueError,match='scope'):read_representation_candidate(directory)
    def change(report):report['representation_validation']['checks']['charge_evidence']=False
    rebound(directory,change)
    with pytest.raises(ValueError):read_multiple_plane_candidate(directory)


def plane_generation(tmp_path,mode="none", *, candidate_defect=None):
    from tests.test_cif_source_representation import fake_generation
    from tests.test_cif_plane_candidate import inputs
    from tests.test_cif_stereochemistry_audit import write
    def pair_factory(folder):
        s,d,p=inputs(folder,'Q17')
        # Complete synthetic native support; no scientific geometry claim.
        p['_chem_comp_atom.type_energy']=list(p['_chem_comp_atom.type_symbol'])
        for field in ('value_dist','value_dist_esd'):p['_chem_comp_bond.'+field]=list(d['_chem_comp_bond.'+field])
        a='_chem_comp_angle.'
        p.update({a+'comp_id':['Q17']*3,a+'atom_id_1':['O','O','N'],a+'atom_id_2':['C']*3,
            a+'atom_id_3':['N','R','R'],a+'value_angle':['120']*3,a+'value_angle_esd':['2']*3})
        write(folder/'dictionary.cif',d)
        if candidate_defect=='charge':p['_chem_comp_atom.charge'][0]='1'
        elif candidate_defect=='element':p['_chem_comp_atom.type_symbol'][0]='N'
        elif candidate_defect=='bond':p['_chem_comp_bond.value_order'][0]='SING'
        return write(folder/'source.cif',s),write(folder/'support.cif',p)
    directory,report=fake_generation(tmp_path,mode=mode,opt_in=False,multiple_planes=True,request_owned=True,
        ring_atoms=(),aromatic_count=0,pair_factory=pair_factory,source_name='original source CCD.cif')
    assert report['status']==('REJECTED' if candidate_defect is not None else 'FAILED' if mode in {'timeout','process_failure','partial_candidate_failure','partial_result_failure'} else 'CANDIDATE_REVIEW')
    return tmp_path/'inputs/original source CCD.cif',tmp_path/'inputs/dictionary.cif',directory.parents[2],directory


def test_owned_plane_candidate_uses_selected_attempt_and_existing_chemistry_gate(tmp_path):
    from nasolve.cif_plane_generation import prepare_owned_trigonal_plane_candidate
    from nasolve.cif_plane_candidate import prepare_trigonal_plane_candidate
    source,dictionary,request,directory=plane_generation(tmp_path)
    output=tmp_path/'owned.cif';control=tmp_path/'supplied.cif'
    report=prepare_owned_trigonal_plane_candidate(source,dictionary,'Q17',request,1,output)
    expected=prepare_trigonal_plane_candidate(source,dictionary,directory/'candidate.cif','Q17',control)
    assert output.read_bytes()==control.read_bytes()
    assert report['plane_candidate']==expected
    assert report['support_generation']['attempt_number']==1
    assert report['native_qualification']=='NOT_RUN' and not report['automatic_adoption']
    assert report['support_generation']['support']['anchor']=='request_directory'


@pytest.mark.parametrize('defect',['source','code','attempt','unsealed','changed_receipt','support_file'])
def test_owned_support_refuses_missing_or_mismatched_authority_before_output(tmp_path,defect):
    from nasolve.cif_plane_generation import prepare_owned_trigonal_plane_candidate
    source,dictionary,request,directory=plane_generation(tmp_path)
    code='Q17';number=1
    if defect=='source':source.write_text(source.read_text()+'\n# other source\n')
    elif defect=='code':code='ZZZ'
    elif defect=='attempt':number=2
    elif defect=='unsealed':(directory.parent/'finished.json').unlink()
    elif defect=='changed_receipt':
        p=directory/'source_candidate_receipt.json';p.write_text(p.read_text()+'\n')
    elif defect=='support_file':
        p=directory/'candidate.cif';p.write_text(p.read_text()+'\n')
    output=tmp_path/'new.cif'
    with pytest.raises(ValueError):prepare_owned_trigonal_plane_candidate(source,dictionary,code,request,number,output)
    assert not output.exists()


@pytest.mark.parametrize('field',['single_block_steps','timeout_seconds','expected_dialect','phenix_version','prior_sources'])
def test_owned_binding_checks_recipe_and_producer_beyond_seal_identity(tmp_path,monkeypatch,field):
    import nasolve.cif_plane_generation as module
    source,_,request,_=plane_generation(tmp_path)
    original=module.inspect_source_generation_request
    def changed(path):
        state=original(path);config=state['request']['configuration']
        if field=='single_block_steps':config['recipe'][field]+=1
        elif field=='timeout_seconds':config['recipe'][field]-=1  # Actual work must fit the cap; shorter work is permitted.
        elif field=='expected_dialect':config['recipe'][field]='MONOMER_LIBRARY_CIF'
        elif field=='phenix_version':config['generator'][field]='different'
        else:config['generator'][field][0]['sha256']='0'*64
        return state
    monkeypatch.setattr(module,'inspect_source_generation_request',changed)
    with pytest.raises(ValueError,match='recipe/producer'):module.read_owned_plane_support(source,'Q17',request,1)


def test_cold_owned_support_needs_no_original_or_sdk_and_does_not_write(tmp_path,monkeypatch):
    from nasolve.cif_plane_generation import read_owned_plane_support
    source,_,request,directory=plane_generation(tmp_path)
    expected=read_owned_plane_support(source,'Q17',request,1)
    relocated=request.rename(tmp_path/'relocated');assert not request.exists()
    source.unlink()
    original_open=Path.open
    import nasolve.cif_doctor
    maintained=Path(nasolve.cif_doctor.__file__).parent
    def guarded(path,*args,**kwargs):
        if Path(path).is_relative_to(relocated) or Path(path).is_relative_to(maintained):return original_open(path,*args,**kwargs)
        raise AssertionError('Original/SDK access attempted: '+str(path))
    def forbidden(*args,**kwargs):raise AssertionError('Native execution/process probe attempted')
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in relocated.rglob('*') if p.is_file()}
    with monkeypatch.context() as m:
        m.setattr(Path,'open',guarded)
        m.setattr('subprocess.Popen',forbidden)
        m.setattr('nasolve.cif_generation_process.process_alive',forbidden)
        m.setattr('nasolve.cif_generation_attempt.coordinator_alive',forbidden)
        actual=read_owned_plane_support(relocated/'inputs/source.cif','Q17',relocated,1)
    assert actual==expected
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())


def test_support_changed_after_candidate_is_preserved_and_refused(tmp_path,monkeypatch):
    import nasolve.cif_plane_generation as module
    source,dictionary,request,directory=plane_generation(tmp_path)
    prepare=module.prepare_trigonal_plane_candidate
    def changed(*args):
        result=prepare(*args)
        p=directory/'candidate.cif';p.write_text(p.read_text()+'\n')
        return result
    monkeypatch.setattr(module,'prepare_trigonal_plane_candidate',changed)
    output=tmp_path/'partial.cif'
    with pytest.raises(ValueError):module.prepare_owned_trigonal_plane_candidate(source,dictionary,'Q17',request,1,output)
    assert output.exists()


@pytest.mark.parametrize('remaining',[None,5.5])
def test_explicit_earlier_attempt_is_not_replaced_by_latest(tmp_path,remaining):
    import os
    from nasolve.cif_generation_attempt import generate_source_candidate_attempt,inspect_source_generation_request
    from nasolve.cif_plane_generation import read_owned_plane_support
    source,_,request,directory=plane_generation(tmp_path)
    first=read_owned_plane_support(source,'Q17',request,1)
    config=inspect_source_generation_request(request)['request']['configuration']
    spec=json.loads((directory/'candidate_spec.json').read_text());installation=Path(spec['installation_root'])
    gen=config['generator'];recipe=config['recipe']
    result=generate_source_candidate_attempt(installation,installation/gen['dispatchers']['python']['path'],
        installation/gen['dispatchers']['elbow']['path'],gen['api_sources'],source,'Q17',request,
        environment={**os.environ,'CANDIDATE_FIXTURE':str(tmp_path/'inputs/support.cif')},
        prior_sources=gen['prior_sources'],phenix_version=gen['phenix_version'],max_attempts=config['max_attempts'],
        **({'_remaining_seconds':lambda:remaining} if remaining is not None else {}),**recipe)
    assert result['attempt_number']==2
    assert result['generation']['execution']['timeout_seconds']==(recipe['timeout_seconds'] if remaining is None else remaining)
    assert read_owned_plane_support(source,'Q17',request,1)==first
    second=read_owned_plane_support(source,'Q17',request,2)
    assert second['attempt_number']==2 and second['attempt_sha256']!=first['attempt_sha256']
    assert second['support']['sha256']==first['support']['sha256']


@pytest.mark.parametrize('defect',['command','context','allowance','job_timeout','completion','bool_returncode'])
def test_selected_phase_must_match_completed_recipe(tmp_path,monkeypatch,defect):
    import nasolve.cif_plane_generation as module
    source,_,request,_=plane_generation(tmp_path)
    original=module.inspect_generation_process
    def changed(path,phase):
        state=original(path,phase)
        if phase=='candidate':
            if defect=='command':state['job']['argv_provenance'][-1]='different.json'
            elif defect=='context':state['job']['context']['single_block_steps']+=1
            elif defect=='allowance':state['job']['context']['total_timeout_seconds']+=1
            elif defect=='job_timeout':state['job']['timeout_seconds']=state['job']['context']['total_timeout_seconds']+1
            elif defect=='completion':state['finished']['status']='FAILED'
            else:state['finished']['returncode']=False
        return state
    monkeypatch.setattr(module,'inspect_generation_process',changed)
    with pytest.raises(ValueError,match='phase command/recipe/completion'):module.read_owned_plane_support(source,'Q17',request,1)


@pytest.mark.parametrize('number',[None,False,0,-1,1.0,'1'])
def test_selection_cannot_default_or_coerce_attempt_number(tmp_path,number):
    from nasolve.cif_plane_generation import read_owned_plane_support
    with pytest.raises(ValueError,match='explicit positive'):read_owned_plane_support(tmp_path/'missing','Q17',tmp_path/'missing',number)



@pytest.mark.parametrize('changed',['worker','extra_file','receipt'])
def test_completed_replay_refuses_evidence_changed_during_assessment(tmp_path,monkeypatch,changed):
    import nasolve.cif_source_representation as module
    _,directory=generated(tmp_path,monkeypatch,False)
    original=module._replay_exact_handoff
    def mutate(*args):
        result=original(*args)
        p=directory/({'worker':'candidate_worker.py','receipt':'source_candidate_receipt.json','extra_file':'new.txt'}[changed])
        p.write_text((p.read_text() if p.exists() else '')+'\n')
        return result
    monkeypatch.setattr(module,'_replay_exact_handoff',mutate)
    with pytest.raises(ValueError):module.read_multiple_plane_candidate(directory)


def test_changed_request_ceiling_cannot_borrow_a_completed_attempt(tmp_path):
    from nasolve.campaign_records import read_record,write_record
    from nasolve.cif_plane_generation import read_owned_plane_support
    source,_,request,_=plane_generation(tmp_path)
    header=read_record(request/'request.json')
    header['configuration']['recipe']['timeout_seconds']+=1
    write_record(request/'request.json',header,replace=True)
    with pytest.raises(ValueError,match='generation attempt intent'):
        read_owned_plane_support(source,'Q17',request,1)


@pytest.mark.parametrize('mode',['timeout','process_failure','partial_candidate_failure','partial_result_failure'])
def test_known_failed_plane_generation_replays_cold_without_becoming_support(tmp_path,monkeypatch,mode):
    import nasolve.cif_plane_generation as m
    source,_,request,directory=plane_generation(tmp_path,mode)
    value=m.inspect_owned_plane_generation_failure(source,'Q17',request,1)
    assert value['status']=='KNOWN_STOPPED_GENERATION_FAILURE'
    assert value['failure_kind']==('TIMED_OUT' if mode=='timeout' else 'FAILED')
    assert value['new_native_calls']==0 and not value['fallback_authorized'] and not value['retry_authorized']
    assert value['candidate_qualification']=='NOT_ASSESSED' and 'support' not in value
    with pytest.raises(ValueError):m.read_owned_plane_support(source,'Q17',request,1)
    moved=request.rename(tmp_path/'relocated');source.unlink()
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    def forbidden(*a,**k):raise AssertionError('Cold failure read must not execute or probe')
    with monkeypatch.context() as guard:
        guard.setattr('subprocess.Popen',forbidden)
        guard.setattr('nasolve.cif_generation_process.process_alive',forbidden)
        guard.setattr('nasolve.cif_generation_attempt.coordinator_alive',forbidden)
        assert m.inspect_owned_plane_generation_failure(moved/'inputs/source.cif','Q17',moved,1)==value
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())


@pytest.mark.parametrize('defect',['source','code','attempt','unsealed','worker','spec','claim','returncode','retained','extra'])
def test_negative_plane_generation_still_requires_bound_inputs_and_stopped_execution(tmp_path,defect):
    from nasolve.cif_plane_generation import inspect_owned_plane_generation_failure
    from nasolve.campaign_records import read_record,write_record
    source,_,request,directory=plane_generation(tmp_path,'process_failure');code='Q17';number=1
    if defect=='source':source.write_bytes(source.read_bytes()+b'changed')
    elif defect=='code':code='OTHER'
    elif defect=='attempt':number=True
    elif defect=='unsealed':(directory.parent/'finished.json').unlink()
    else:
        report=json.loads((directory/'source_candidate_receipt.json').read_text())
        if defect=='worker':(directory/'candidate_worker.py').write_text('different')
        elif defect=='spec':
            p=directory/'candidate_spec.json';v=json.loads(p.read_text());v['arguments'].remove('--multiple_planes');p.write_text(json.dumps(v))
        elif defect=='claim':report['execution']['status']='COMPLETED'
        elif defect=='returncode':report['execution']['returncode']=True
        elif defect=='retained':report['candidate_retained']=True
        elif defect=='extra':(directory/'unexpected.txt').write_text('extra')
        for ref in report['outputs']:
            p=directory/ref['path'];ref.update(size=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())
        p=directory/'source_candidate_receipt.json';p.write_text(json.dumps(report))
        finished=read_record(directory.parent/'finished.json')
        finished['candidate_receipt'].update(size=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())
        write_record(directory.parent/'finished.json',finished,replace=True)
    with pytest.raises(ValueError):inspect_owned_plane_generation_failure(source,code,request,number)


@pytest.mark.parametrize('defect',['context','command','completion','job_timeout','missing_identity','bool_returncode'])
def test_negative_generation_requires_exact_candidate_process_receipt(tmp_path,monkeypatch,defect):
    import nasolve.cif_plane_generation as m
    source,_,request,_=plane_generation(tmp_path,'process_failure')
    original=m.inspect_generation_process
    def changed(*a,**k):
        v=original(*a,**k)
        if a[1]=='candidate':
            if defect=='context':v['job']['context']['total_timeout_seconds']+=1
            elif defect=='command':v['job']['argv_provenance'][-1]='another.json'
            elif defect=='completion':v['finished']['status']='INTERRUPTED'
            elif defect=='job_timeout':v['job']['timeout_seconds']=100
            elif defect=='missing_identity':v.pop('identity')
            else:v['finished']['returncode']=True
        return v
    monkeypatch.setattr(m,'inspect_generation_process',changed)
    with pytest.raises(ValueError):m.inspect_owned_plane_generation_failure(source,'Q17',request,1)


def test_completed_support_is_not_classified_as_failed_generation(tmp_path):
    from nasolve.cif_plane_generation import inspect_owned_plane_generation_failure
    source,_,request,_=plane_generation(tmp_path)
    with pytest.raises(ValueError):inspect_owned_plane_generation_failure(source,'Q17',request,1)


@pytest.mark.parametrize('defect',['charge','element','bond'])
def test_completed_chemical_rejection_is_known_negative_not_support(tmp_path,monkeypatch,defect):
    from nasolve.cif_plane_generation import inspect_owned_plane_generation_failure,read_owned_plane_support
    source,_,request,work=plane_generation(tmp_path,candidate_defect=defect)
    report=json.loads((work/'source_candidate_receipt.json').read_text())
    assert report['execution']['status']=='COMPLETED' and report['execution']['returncode']==0
    assert report['result']['builder']['status']=='COMPLETED' and report['status']=='REJECTED'
    value=inspect_owned_plane_generation_failure(source,'Q17',request,1)
    assert value['status']=='KNOWN_STOPPED_GENERATION_FAILURE'
    assert value['policy_id']=='cif-owned-plane-generation-rejection-v1'
    assert value['failure_kind']=='REJECTED_CANDIDATE' and value['returncode']==0
    assert value['candidate_qualification']=='SOURCE_REJECTED'
    assert value['rejection_diagnostic']==report['diagnostic']
    assert value['new_native_calls']==0 and not value['fallback_authorized'] and not value['retry_authorized']
    assert 'support' not in value
    with pytest.raises(ValueError):read_owned_plane_support(source,'Q17',request,1)
    moved=request.rename(tmp_path/'relocated');source.unlink()
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    def forbidden(*a,**k):raise AssertionError('Cold rejection read must not execute/probe')
    with monkeypatch.context() as guard:
        guard.setattr('subprocess.Popen',forbidden)
        guard.setattr('nasolve.cif_generation_process.process_alive',forbidden)
        guard.setattr('nasolve.cif_generation_attempt.coordinator_alive',forbidden)
        assert inspect_owned_plane_generation_failure(moved/'inputs/source.cif','Q17',moved,1)==value
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())


@pytest.mark.parametrize('defect',['diagnostic','inspection','candidate','worker','spec','builder','dispatch','unsealed','missing_execution','execution_shape'])
def test_chemical_rejection_requires_exact_completed_evidence(tmp_path,defect):
    from nasolve.cif_plane_generation import inspect_owned_plane_generation_failure
    from nasolve.campaign_records import read_record,write_record
    source,_,request,work=plane_generation(tmp_path,candidate_defect='charge')
    def change(report):
        if defect=='missing_execution':report.pop('execution')
        elif defect=='execution_shape':report['execution']=None
        elif defect=='diagnostic':report['diagnostic']['summary']='invented'
        elif defect=='inspection':report['inspection']['status']='CANDIDATE_REVIEW'
        elif defect=='candidate':
            p=work/'candidate.cif';p.write_text(p.read_text().replace('Q17','ZZZ'))
            report['candidate'].update(size=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())
        elif defect=='worker':(work/'candidate_worker.py').write_text('different')
        elif defect=='spec':
            p=work/'candidate_spec.json';v=json.loads(p.read_text());v['arguments'].remove('--multiple_planes');p.write_text(json.dumps(v))
        elif defect in {'builder','dispatch'}:
            result=report['result']
            if defect=='builder':result['builder']['status']='EXCEPTION'
            else:result['reader']['dispatch_is_chemical_components']=False
            (work/'candidate_result.json').write_text(json.dumps(result))
    rebound(work,change)
    p=work/'source_candidate_receipt.json';seal=work.parent/'finished.json'
    finished=read_record(seal);finished['candidate_receipt'].update(size=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())
    write_record(seal,finished,replace=True)
    if defect=='unsealed':seal.unlink()
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in request.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):inspect_owned_plane_generation_failure(source,'Q17',request,1)
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())


@pytest.mark.parametrize('defect',['context','command','status','returncode','missing_identity'])
def test_rejected_generation_requires_matching_completed_process(tmp_path,monkeypatch,defect):
    import nasolve.cif_plane_generation as m
    source,_,request,_=plane_generation(tmp_path,candidate_defect='charge')
    original=m.inspect_generation_process
    def changed(*a,**k):
        value=original(*a,**k)
        if a[1]=='candidate':
            if defect=='context':value['job']['context']['total_timeout_seconds']+=1
            elif defect=='command':value['job']['argv_provenance'][-1]='other.json'
            elif defect=='status':value['finished']['status']='FAILED'
            elif defect=='returncode':value['finished']['returncode']=True
            else:value.pop('identity')
        return value
    monkeypatch.setattr(m,'inspect_generation_process',changed)
    with pytest.raises(ValueError):m.inspect_owned_plane_generation_failure(source,'Q17',request,1)
