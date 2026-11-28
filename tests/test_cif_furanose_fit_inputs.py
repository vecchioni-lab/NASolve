"""A site-only fit must receive every interpretation control from the chosen native read."""
from copy import deepcopy

from unittest.mock import patch

import pytest
from tests.test_cif_furanose_fit_return import frozen


def test_fit_uses_the_native_consumed_definitions_without_rewriting_parameters(tmp_path):
    from nasolve.cif_furanose_fit import interpreted_geometry_phils

    rows = [{'role':'model','path':'inputs/model.pdb'},
            {'role':'dictionary','path':'inputs/component.cif'},
            {'role':'phil','path':'inputs/pairs.phil'},
            {'role':'phil','path':'inputs/site-modification.phil'}]
    paths = ('geometry_restraints.edits.bond.sigma', 'pdb_interpretation.apply_cif_modification.data_mod')
    adaptations = [dict(input=row['path'],canonical=f'canonical_{i:03d}.phil',
        policy='refinement-root-to-interpreter-v1',definitions_preserved=1,
        field_mapping=[dict(source='refinement.'+field,interpreter=field,value_tokens=[value])])
        for i,(row,field,value) in enumerate(zip(rows[2:],paths,('0.20','MOD1')))]
    report = dict(status='REVIEW',unused_definitions=[],phil_adaptations=adaptations)
    first, second = b'geometry_restraints.edits.bond.sigma = 0.20\n', b'pdb_interpretation.apply_cif_modification.data_mod = MOD1\n'
    snapshots = {tmp_path/'canonical_000.phil':first, tmp_path/'canonical_001.phil':second}
    def read(native, files=snapshots):
        return interpreted_geometry_phils(tmp_path, {'inputs':rows}, native, files)
    assert read(report) == ((first,second),2)
    for change in ('missing','reordered','redirected','unused','lost field','foreign control','unbound bytes'):
        altered=deepcopy(report)
        fs=dict(snapshots)
        maps=altered['phil_adaptations']
        if change=='missing': maps.pop()
        elif change=='reordered': maps.reverse()
        elif change=='redirected': maps[0]['canonical']='../other.phil'
        elif change=='unused': altered['unused_definitions']=['geometry_restraints.edits.bond.sigma']
        elif change=='lost field': maps[0]['field_mapping'].clear()
        elif change=='foreign control':
            maps[0]['field_mapping'][0].update(source='refinement.selection', interpreter='selection')
        elif change=='unbound bytes': fs.pop(tmp_path/'canonical_000.phil')
        with pytest.raises(ValueError):
            read(altered,fs)


def test_numbered_sugar_fit_can_retry_after_a_stopped_failure_and_reopen_without_phenix(tmp_path, frozen, monkeypatch):
    from hashlib import sha256
    from types import SimpleNamespace
    import os
    from nasolve import cif_furanose_fit_attempt as fit
    from nasolve.cif_furanose_fit import FuranoseFitInputs

    run=tmp_path/'run'
    run.mkdir()
    dispatch=tmp_path/'sdk/bin/phenix.geometry_minimization'
    dispatch.parent.mkdir(parents=True)
    dispatch.write_text("#!/bin/sh\nset -eu\nif [ \"$SIMULATE_FAILURE\" = yes ]; then exit 12; fi\n"
                        "cp \"$1\" relaxed.pdb\nprintf 'Bond | User supplied | restraints: 1\\n' > relaxed.geo\n")
    dispatch.chmod(0o700)
    sdk=SimpleNamespace(root=tmp_path/'sdk',executables={'phenix.ready_set':tmp_path/'readyset'},
                        environment=dict(os.environ,SIMULATE_FAILURE='yes'))
    plan=FuranoseFitInputs(frozen,'A:2','UY1',(frozen/'model.pdb').read_bytes(),
        (b'data_fixture\n',),(b'geometry_restraints.edits.bond.sigma = 0.2\n',), b'selection = all\n',
        '1'*64,'2'*64,1,(('bond',1),),{'version':'fixture'})
    monkeypatch.setattr(fit,'read_furanose_fit_inputs',lambda *a,**k: plan)
    monkeypatch.setattr(fit,'verify_current_consumer',lambda *a: True)
    def contacts(model,geometry,sites,*,minimum_overlap):
        return dict(status='OBSERVED',model_sha256=sha256(model.read_bytes()).hexdigest(),
                    geometry_sha256=sha256(geometry.read_bytes()).hexdigest(),
                    overlap_screen=dict(minimum_overlap_A=minimum_overlap,contacts=[]))
    monkeypatch.setattr(fit,'read_refined_contacts',contacts)
    def discover():
        return sdk
    def offline():
        pytest.fail('Reopening a saved fit attempted to discover Phenix')
    with pytest.raises(ValueError,match='exact preceding'):
        fit.fit_checked_sugar(run,offline,attempt_number=1,after_fit=0)
    with pytest.raises(ValueError,match='Phenix geometry fit failed'):
        fit.fit_checked_sugar(run,discover,attempt_number=1)
    parent=run/'PostMR/SugarFit/preparation-0001'
    failed=parent/'fit-0001'
    assert (failed/'ownership/finished.json').is_file() and not (failed/'candidate.pdb').exists()
    with pytest.raises(ValueError,match='incomplete'):
        fit.fit_checked_sugar(run,offline,attempt_number=1)
    with pytest.raises(ValueError,match='exact preceding'):
        fit.fit_checked_sugar(run,offline,attempt_number=1,after_fit=0)
    sdk.environment['SIMULATE_FAILURE']='no'
    result=fit.fit_checked_sugar(run,discover,attempt_number=1,after_fit=1)
    assert result.number==2 and result.model.read_bytes()==plan.model
    assert result.observations['checkpoint_published'] is False and result.observations['user_restraints']=={'bond':1}
    assert (failed/'reservation.json').is_file() and not (run/'AutoRefine').exists()
    moved=run.rename(tmp_path/'relocated')
    with patch('subprocess.Popen',side_effect=AssertionError('Cold read launched a process')):
        again=fit.read_checked_sugar_fit(moved,attempt_number=1,fit_number=2)
        assert again.observations==result.observations
        assert fit.fit_checked_sugar(moved,offline,attempt_number=1).model==again.model
        with pytest.raises(ValueError,match='already available'):
            fit.fit_checked_sugar(moved,offline,attempt_number=1,after_fit=2)
        from nasolve.campaign_records import read_record, write_record
        reservation = again.report.parent/'reservation.json'
        original = reservation.read_bytes()
        data = read_record(reservation)
        data.pop('record_sha256')
        data['number'] = 1
        reservation.unlink()
        write_record(reservation,data)
        with pytest.raises(ValueError, match='reservation differs'):
            fit.read_checked_sugar_fit(moved,attempt_number=1,fit_number=2)
        reservation.write_bytes(original)
        again.model.write_bytes(again.model.read_bytes()+b'REMARK changed\n')
        with pytest.raises(ValueError,match='changed'):
            fit.read_checked_sugar_fit(moved,attempt_number=1,fit_number=2)


def test_local_sugar_fit_does_not_replace_a_live_or_unknown_attempt(tmp_path,monkeypatch):
    from nasolve import cif_furanose_fit_attempt as fit
    from nasolve.campaign_records import write_record
    previous=tmp_path/'fit-0001'
    previous.mkdir()
    from nasolve.campaign_process import current_process_identity
    write_record(previous/'reservation.json',dict(number=1,preparation_result_sha256='3'*64,coordinator=current_process_identity()))
    monkeypatch.setattr(fit,'_inspect_owned_processes',lambda *a: dict(state='NOT_RECORDED',activity=None))
    for living in (True,None):
        monkeypatch.setattr(fit,'coordinator_alive',lambda ident: living)
        with pytest.raises(ValueError,match='proof its processes stopped'):
            fit._next_fit(tmp_path,1,'3'*64)
    monkeypatch.setattr(fit,'coordinator_alive',lambda ident: False)
    with pytest.raises(ValueError,match='reservation differs'):
        fit._next_fit(tmp_path,1,'4'*64)
    assert fit._next_fit(tmp_path,1,'3'*64)==(2,True)
    (previous/'ownership/phases').mkdir(parents=True)
    with pytest.raises(ValueError,match='proof its processes stopped'):
        fit._next_fit(tmp_path,1,'3'*64)


def test_sugar_cli_read_uses_the_named_attempt_and_fit_without_discovering_tools(tmp_path,monkeypatch,capsys):
    from types import SimpleNamespace
    from nasolve import cli, cif_furanose_fit_attempt
    def read(run,*,attempt_number,fit_number):
        assert run==tmp_path and (attempt_number,fit_number)==(3,2)
        return SimpleNamespace(number=2,model=tmp_path/'candidate.pdb',report=tmp_path/'result.json',
                               observations=dict(site='A:2',component='UY1'))
    monkeypatch.setattr(cif_furanose_fit_attempt,'read_checked_sugar_fit',read)
    with patch.object(cli,'discover_phenix',side_effect=AssertionError('Read attempted Phenix discovery')):
        assert cli.main(['cif-doctor','fit-sugar',str(tmp_path),'--attempt','3','--read-fit','2'])==0
    assert 'Geometry-only fit 2 for A:2 UY1' in capsys.readouterr().out
