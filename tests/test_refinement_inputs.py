"""Refinement must consume the full-model guard without rewriting its source."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from nasolve.autorefine import AutoRefineError,execute_autorefine
from nasolve.checkpoints import read_registry,resolve_checkpoint,inherited_paths
from nasolve.cif_native_monomers import FULL_MODEL_PHIL
from tests.test_autorefine import make_refine_run,make_refine,make_mtz_dump
from tests.test_cif_postmr_publication import snapshot


def inputs(tmp_path):
    run=make_refine_run(tmp_path,autosol=False)
    policy=run/'PostMR/Restraints/native_interpretation.phil';policy.write_text(FULL_MODEL_PHIL)
    p=run/'report.json';r=json.loads(p.read_text());r['postmr']['restraints'].append(str(policy));p.write_text(json.dumps(r))
    tools=tmp_path/'tools';tools.mkdir()
    return run,policy,make_refine(tools),make_mtz_dump(tools,anomalous=False)


def test_refinement_consumes_wrapped_policy_preserves_original_and_lineage(tmp_path):
    import subprocess
    run,policy,refine,dump=inputs(tmp_path);before=snapshot(run/'PostMR');original=subprocess.run
    def consume(command,*a,**k):
        if str(command[0])==str(refine):
            for item in command[1:]:
                p=Path(item)
                if p.is_file():
                    assert p.read_bytes()!=FULL_MODEL_PHIL.encode(), 'phenix.refine rejects bare interpreter policy'
        return original(command,*a,**k)
    with patch('subprocess.run',consume):
        result=execute_autorefine(run,refine,dump,phenix_version='2.2.1-6174')
    assert not json.loads(result.report_path.read_text())['preflight_failed']
    assert snapshot(run/'PostMR')==before
    _,registry=read_registry(run);child=resolve_checkpoint(registry,result.checkpoint_id)
    assert inherited_paths(child,run)['restraints'][1]==policy
    receipt=child['outputs']['refinement_inputs'];assert receipt['anchor']=='run'
    record=json.loads((run/receipt['relative_path']).read_text());row=record['adaptations'][0]
    assert row['index']==1
    execution=run/row['execution']['relative_path']
    assert execution.read_bytes()==b'refinement {\n'+FULL_MODEL_PHIL.encode()+b'}\n'
    args=json.loads((result.round_directory/'received_args.json').read_text())
    assert str(execution) in args and str(policy) not in args


def completed(tmp_path):
    run,policy,refine,dump=inputs(tmp_path)
    result=execute_autorefine(run,refine,dump,phenix_version='2.2.1-6174')
    _,registry=read_registry(run);child=resolve_checkpoint(registry,result.checkpoint_id)
    receipt=run/child['outputs']['refinement_inputs']['relative_path']
    record=json.loads(receipt.read_text())
    return run,policy,result,registry,child,receipt,record


def test_execution_policy_reads_after_dataset_move_without_original_or_native(tmp_path):
    run,policy,result,registry,child,receipt,record=completed(tmp_path)
    old=run.parents[1];moved=tmp_path/'relocated';old.rename(moved)
    assert not old.exists()
    with patch('subprocess.Popen',side_effect=AssertionError('read-only')):
        new=moved/'AutoMR/run_001';_,saved=read_registry(new)
        inherited=inherited_paths(resolve_checkpoint(saved,result.checkpoint_id),new)
    assert inherited['restraints'][1]==new/policy.relative_to(run)


@pytest.mark.parametrize('defect',['source','copy','rehash-copy','index','source-reference','symlink','receipt','size'])
def test_checkpoint_reader_refuses_changed_or_relabelled_execution_evidence(tmp_path,defect):
    from nasolve.campaign_records import write_record
    from nasolve.checkpoints import CheckpointError,_file_reference
    run,policy,result,registry,child,receipt,record=completed(tmp_path)
    execution=run/record['adaptations'][0]['execution']['relative_path']
    if defect=='source':policy.write_text(FULL_MODEL_PHIL.replace('False','True'))
    elif defect in {'copy','rehash-copy'}:
        execution.write_text(execution.read_text().replace('False','True'))
        if defect=='rehash-copy':record['adaptations'][0]['execution']=_file_reference(execution,run)
    elif defect=='size':record['adaptations'][0]['execution']['size']+=1
    elif defect=='index':record['adaptations'][0]['index']=0
    elif defect=='source-reference':record['adaptations'][0]['source']=child['restraints'][0]
    elif defect=='symlink':
        external=tmp_path/'copy.phil';execution.rename(external);execution.symlink_to(external)
    else:receipt.write_text('{}')
    if defect in {'rehash-copy','index','source-reference','size'}:
        write_record(receipt,record,replace=True)
        child['outputs']['refinement_inputs']=_file_reference(receipt,run)
        (run/'AutoRefine/checkpoints.json').write_text(json.dumps(registry))
    with patch('subprocess.Popen',side_effect=AssertionError('read-only')):
        with pytest.raises(CheckpointError):read_registry(run)


@pytest.mark.parametrize('content',[FULL_MODEL_PHIL.replace('False','True'),
    'refinement {\n'+FULL_MODEL_PHIL+'}\n',FULL_MODEL_PHIL+'# not the exact generated input\n'])
def test_unknown_or_already_qualified_text_is_not_rewritten(tmp_path,content):
    from nasolve.checkpoints import _file_reference
    from nasolve.refinement_inputs import prepare_refinement_inputs
    run,policy,_,_=inputs(tmp_path);policy.write_text(content);before=snapshot(run)
    paths,record=prepare_refinement_inputs(run,[_file_reference(policy,run)],checkpoint='refine-001')
    assert paths==[policy] and record is None and snapshot(run)==before


def test_policy_change_during_native_work_preserves_round_without_adoption(tmp_path):
    import subprocess
    run,policy,refine,dump=inputs(tmp_path);original=subprocess.run
    def consume(command,*a,**k):
        result=original(command,*a,**k)
        if str(command[0])==str(refine) and '--dry_run' not in command:
            copy=next((run/'AutoRefine/round_001/refinement_inputs').glob('*.phil'))
            copy.write_text(copy.read_text().replace('False','True'))
        return result
    with patch('subprocess.run',consume):
        with pytest.raises(AutoRefineError,match='changed after it was frozen'):
            execute_autorefine(run,refine,dump,phenix_version='2.2.1-6174')
    assert (run/'AutoRefine/round_001/refined_001.pdb').is_file()
    assert len(json.loads((run/'AutoRefine/checkpoints.json').read_text())['checkpoints'])==1
    assert policy.read_text()==FULL_MODEL_PHIL


def test_policy_change_during_preflight_prevents_refinement_launch(tmp_path):
    import subprocess
    run,policy,refine,dump=inputs(tmp_path);original=subprocess.run
    def consume(command,*a,**k):
        if str(command[0])==str(refine):
            assert '--dry_run' in command, 'No refinement launch after changed preflight input'
            result=original(command,*a,**k)
            copy=next((run/'AutoRefine/round_001/refinement_inputs').glob('*.phil'))
            copy.write_text(copy.read_text().replace('False','True'))
            return result
        return original(command,*a,**k)
    with patch('subprocess.run',consume):
        with pytest.raises(AutoRefineError,match='changed after it was frozen'):
            execute_autorefine(run,refine,dump,phenix_version='2.2.1-6174')
    assert len(json.loads((run/'AutoRefine/checkpoints.json').read_text())['checkpoints'])==1
