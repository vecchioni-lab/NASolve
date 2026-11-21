"""The ordinary audited child must invoke all scientific gates, not just exit 0."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json,os,shutil,sys
from unittest.mock import patch
import pytest
from nasolve.cli import main
from nasolve.metal import child_session as m
from nasolve.metal.recipe import RecipeError,canonical
from tests.test_metal_child_inputs import prepared_case
from tests.test_metal_fdp import native_result


def setup(tmp_path,monkeypatch,defect=None):
    values=prepared_case(tmp_path,monkeypatch);c,archive,prepared,request=values
    plan=json.loads((prepared/'plan.json').read_text());raw=(prepared/'input.pdb').read_bytes()
    evidence=native_result(plan,raw)
    if defect=='B':evidence['atoms'][-1]['b_iso']+=1
    executable=tmp_path/'synthetic-phenix-python'
    program='#!'+sys.executable+'\n'+'''from pathlib import Path
import gzip,json,sys
'''+f"evidence={evidence!r}\n"+'''
Path('native-result.json.gz').write_bytes(gzip.compress(json.dumps(evidence).encode()))
Path('final.pdb').write_bytes(Path('input.pdb').read_bytes())
Path('effective-final.phil').write_text('Synthetic policy for session lifecycle test\n')
'''.replace("test\n'","test\\n'")
    if defect=='serialized':program+="p=Path('final.pdb');p.write_bytes(p.read_bytes().replace(b'260.00',b'261.00'))\n"
    if defect=='process':program+='sys.exit(7)\n'
    executable.write_text(program);executable.chmod(0o700)
    native=SimpleNamespace(version='2.2.1',root=tmp_path,executables={'phenix.python':executable,'phenix.mtz.dump':executable},environment=dict(os.environ))
    metadata=deepcopy(plan['metadata']);references=deepcopy(plan['references'])
    if defect=='metadata':metadata['wavelength_A']+=.1
    if defect=='reference':references[-1]['f_double_prime']+=1
    monkeypatch.setattr(m,'inspect_observations',lambda *a,**k:metadata)
    monkeypatch.setattr(m,'reference_scattering',lambda *a,**k:references)
    monkeypatch.setattr(m,'audit_free_r_flags',lambda *a,**k:SimpleNamespace(valid=defect!='free-r',status='VALID' if defect!='free-r' else 'INVALID',details={},warnings=()))
    return values,native


def run(tmp_path,values,native):
    return m.run_audited_child(values[2],values[1],values[3],request_id=values[3]['request_id'],
        run_relative='dataset/AutoMR/run_001',endpoint_relative='Metal/xyz_001',
        session_directory=tmp_path/'session',native=native,timeout_seconds=5)


def test_normal_cli_composes_derivation_native_audit_and_output_seal(tmp_path,monkeypatch,capsys):
    values,native=setup(tmp_path,monkeypatch)
    monkeypatch.setattr('nasolve.metal.cli.discover_phenix',lambda *a,**k:native)
    request=tmp_path/'request.json';request.write_text(json.dumps(values[3]))
    args=['metal','run-audited-fdp-child',str(values[2]),'--parent-archive',str(values[1]),
        '--request',str(request),'--request-id',values[3]['request_id'],'--run-relative','dataset/AutoMR/run_001',
        '--endpoint-relative','Metal/xyz_001','--session',str(tmp_path/'session'),'--timeout','5','--json']
    before={p:p.read_bytes() for folder in [values[1],values[2]] for p in folder.iterdir() if p.is_file()}
    assert main(args)==0
    result=json.loads(capsys.readouterr().out)
    assert result['status']=='FDP_REVIEW' and result['result']['freeze_audit']=='PASS'
    assert result['result']['sites'][0]['b_iso']==260 and result['result']['sites'][0]['occupancy']==.6
    assert result['scientific_acceptance']=='NOT_ASSESSED' and not result['retirement_authorized']
    assert result['fresh_free_r_audit'] and result['serialized_model_unchanged']
    assert result['parent_derivation_before']==result['parent_derivation_after']
    assert (tmp_path/'session/attempt/outputs.json').is_file()
    assert before=={p:p.read_bytes() for p in before}
    assert main(args)==2
    assert not (tmp_path/'session/failure.json').exists()


@pytest.mark.parametrize('defect',['metadata','reference','free-r','B','serialized','process'])
def test_scientific_or_process_failure_never_publishes_review(tmp_path,monkeypatch,defect):
    values,native=setup(tmp_path,monkeypatch,defect)
    with pytest.raises(RecipeError):run(tmp_path,values,native)
    assert (tmp_path/'session/failure.json').exists()
    assert not (tmp_path/'session/review.json').exists()
    if defect in {'metadata','reference','free-r'}:assert not (tmp_path/'session/attempt').exists()
    else:assert (tmp_path/'session/attempt/outcome.json').is_file()


def test_changed_parent_after_child_prevents_scientific_report(tmp_path,monkeypatch):
    values,native=setup(tmp_path,monkeypatch);original=m.child_process.run_child
    def changed(*a,**k):
        result=original(*a,**k)
        p=values[1]/'part-001.zip';p.write_bytes(p.read_bytes()+b'changed')
        return result
    monkeypatch.setattr(m.child_process,'run_child',changed)
    with pytest.raises(RecipeError):run(tmp_path,values,native)
    assert (tmp_path/'session/failure.json').is_file() and not (tmp_path/'session/review.json').exists()


def test_unverified_request_or_derivation_never_starts_native_inspection(tmp_path,monkeypatch):
    values,native=setup(tmp_path,monkeypatch)
    p=values[2]/'input.pdb';p.write_bytes(p.read_bytes()+b'changed')
    with patch.object(m,'inspect_observations',side_effect=AssertionError('No native inspection')):
        with pytest.raises(RecipeError):run(tmp_path,values,native)
    assert not (tmp_path/'session').exists()


def test_rehashed_preflight_change_after_child_cannot_publish(tmp_path,monkeypatch):
    values,native=setup(tmp_path,monkeypatch);original=m.child_process.run_child
    def changed(*a,**k):
        result=original(*a,**k)
        path=tmp_path/'session/fresh-inputs.json';record=m.records.read_record(path)
        record['observations']['wavelength_A']+=.1
        m.records.write_record(path,record,replace=True)
        return result
    monkeypatch.setattr(m.child_process,'run_child',changed)
    with pytest.raises(RecipeError,match='Session proof'):run(tmp_path,values,native)
    assert (tmp_path/'session/failure.json').is_file() and not (tmp_path/'session/review.json').exists()
