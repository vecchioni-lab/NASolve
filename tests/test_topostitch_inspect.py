import hashlib
import json
from dataclasses import asdict

import pytest

from nasolve.topostitch_inspect import load_end_assignments, main
from .test_topostitch_coordinates import two_end_fixture
from .test_topostitch_periodic import cryst1


def inputs(tmp_path):
    text,assignments=two_end_fixture()
    model=tmp_path/'model.pdb';model.write_text(cryst1((30,30,30,90,90,90))+text)
    manifest=tmp_path/'ends.json'
    value={'schema_version':1,'kind':'topostitch-end-assignments',
           'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
           'ends':[asdict(e) for e in assignments]}
    manifest.write_text(json.dumps(value))
    return model,manifest,value


def test_nonperiodic_command_prints_verified_report_without_writes(tmp_path,capsys):
    model,manifest,_=inputs(tmp_path)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert main([str(model),str(manifest),'--radius','15'])==0
    output=json.loads(capsys.readouterr().out)
    assert output['kind']=='topostitch-coordinate-end-report'
    assert output['source_bytes_verified'] is True
    assert len(output['screening']['candidates'])==1
    assert output['changes']==[]
    assert output['assignment_file_sha256']==hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_periodic_command_uses_same_backend(tmp_path,capsys):
    pytest.importorskip('gemmi')
    model,manifest,_=inputs(tmp_path)
    assert main([str(model),str(manifest),'--radius','15','--periodic'])==0
    output=json.loads(capsys.readouterr().out)
    assert output['kind']=='topostitch-periodic-coordinate-report'
    assert output['periodic_screening']['candidates']
    assert output['workflow']['execution_state']=='NOT_ATTEMPTED'


@pytest.mark.parametrize('change',[
    lambda v:v.update(schema_version=True),lambda v:v.update(schema_version=2),
    lambda v:v.update(kind='recipe'),lambda v:v.update(runtime_authority=True),
    lambda v:v.update(model_sha256='bad'),lambda v:v.update(ends='A'),
    lambda v:v['ends'][0].update(unrecognized=1),
    lambda v:v['ends'][0]['overhang_sites'][0].update(typo='A'),
    lambda v:v['ends'][0].update(terminal_pair=[]),
])
def test_invalid_manifest_fails_without_stdout(tmp_path,capsys,change):
    model,manifest,value=inputs(tmp_path)
    change(value);manifest.write_text(json.dumps(value))
    with pytest.raises(SystemExit) as exc:
        main([str(model),str(manifest),'--radius','15'])
    assert exc.value.code==2
    captured=capsys.readouterr()
    assert captured.out=='' and captured.err


def test_duplicate_json_keys_are_not_silently_overridden(tmp_path):
    _,manifest,_=inputs(tmp_path)
    manifest.write_text('{"schema_version": 1, "schema_version": 2}')
    with pytest.raises(ValueError,match='Duplicate'):
        load_end_assignments(manifest)


def test_model_drift_is_refused_by_manifest_hash(tmp_path,capsys):
    model,manifest,_=inputs(tmp_path)
    model.write_text(model.read_text()+'REMARK changed\n')
    with pytest.raises(SystemExit):main([str(model),str(manifest),'--radius','15'])
    captured=capsys.readouterr()
    assert captured.out=='' and 'checksum' in captured.err


def test_missing_file_is_a_clean_cli_error(tmp_path,capsys):
    with pytest.raises(SystemExit) as exc:
        main([str(tmp_path/'m.pdb'),str(tmp_path/'missing.json'),'--radius','15'])
    assert exc.value.code==2
    assert capsys.readouterr().out==''


def test_no_mutating_actions_are_accepted(capsys):
    with pytest.raises(SystemExit) as exc:
        main(['x.pdb','ends.json','--radius','15','--apply'])
    assert exc.value.code==2
    assert 'unrecognized arguments' in capsys.readouterr().err


def test_invalid_image_budget_is_rejected_even_without_periodic_mode(tmp_path,capsys):
    model,manifest,_=inputs(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main([str(model),str(manifest),'--radius','15','--max-image-tests','0'])
    assert exc.value.code==2
    assert capsys.readouterr().out==''


def test_periodic_budget_failure_emits_no_partial_json(tmp_path,capsys):
    pytest.importorskip('gemmi')
    model,manifest,_=inputs(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main([str(model),str(manifest),'--radius','45','--periodic','--max-image-tests','1'])
    assert exc.value.code==2
    captured=capsys.readouterr()
    assert captured.out=='' and 'budget' in captured.err


def test_selected_atom_image_audit_is_opt_in_and_read_only(tmp_path,capsys):
    pytest.importorskip('gemmi')
    model,manifest,_=inputs(tmp_path)
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert main([str(model),str(manifest),'--radius','15','--periodic','--audit-image','0'])==0
    output=json.loads(capsys.readouterr().out)
    audit=output['selected_image_identity']
    assert audit['candidate_index']==0
    assert audit['kind']=='topostitch-selected-image-identity'
    assert audit['source_bytes_verified'] is True
    assert audit['runtime_authority'] is False
    assert output['periodic_screening']['candidates'][0]['image_distinctness_validated'] is False
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}
