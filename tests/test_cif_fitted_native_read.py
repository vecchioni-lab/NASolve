"""A fitted model needs at most one completed fixed-coordinate native read per publication."""
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_cli_defers_native_discovery_for_a_named_fit(tmp_path, monkeypatch):
    from nasolve import cli, cif_postmr_publication

    seen = []
    configure = object()
    monkeypatch.setattr(cli, 'load_config', lambda: configure)
    monkeypatch.setattr(cli, 'discover_phenix', lambda config, *, explicit: seen.append((config, explicit)) or 'chosen')
    def publish(run, *, attempt_number, sugar_fit, discover_phenix, after_native_read):
        assert run == tmp_path and attempt_number == 3 and sugar_fit == 2 and after_native_read == 1
        assert not seen and discover_phenix() == 'chosen'
        return {'message':'Model verified', 'readyset':{'status':'COMPLETED'}}, ()
    monkeypatch.setattr(cif_postmr_publication, 'publish_checked_preparation_with_notes', publish)
    assert cli.main(['cif-doctor','publish-preparation',str(tmp_path),'--attempt','3',
                     '--sugar-fit','2','--after-native-read','1']) == 0
    assert len(seen) == 1


def test_cli_reports_missing_phenix_without_dropping_the_fit(tmp_path, monkeypatch, capsys):
    from nasolve import cli, cif_postmr_publication
    from nasolve.phenix_runtime import PhenixDiscoveryError

    def missing(*args, **kwargs):
        raise PhenixDiscoveryError('Selected installation unavailable')
    monkeypatch.setattr(cli, 'discover_phenix', missing)
    monkeypatch.setattr(cif_postmr_publication, 'publish_checked_preparation_with_notes',
                        lambda run, **options: options['discover_phenix']())
    assert cli.main(['cif-doctor','publish-preparation',str(tmp_path),'--attempt','1','--sugar-fit','1']) == 2
    assert 'Selected installation unavailable' in capsys.readouterr().err


def test_compact_native_files_only_after_archived_bytes_match(tmp_path):
    from nasolve.cif_fitted_native_read import compact_verified_read
    from nasolve.campaign_records import read_record

    source = tmp_path/'native'
    source.mkdir()
    receipt = source/'native_receipt.json'
    selected = source/'geometry.txt'
    other = source/'operator-note.txt'
    for p in (receipt, selected, other):
        p.write_text(p.name)
    originals = {p:p.read_bytes() for p in (receipt,selected)}
    archive = tmp_path/'expanded/evidence'
    archived = {archive/p.name:data for p, data in originals.items()}
    info = {'anchor':'run','relative_path':'PostMR/FittedPreparationEvidence/preparation-0001/fit-0001.zip'}
    with pytest.raises(ValueError,match='copy differs'):
        compact_verified_read(receipt, originals, {**archived, archive/selected.name:b'changed'}, archive, info)
    assert all(p.read_bytes()==b for p,b in originals.items()) and not (source/'archived_read.json').exists()
    compact_verified_read(receipt, originals, archived, archive, info)
    assert not receipt.exists() and not selected.exists() and other.read_text()==other.name
    assert read_record(source/'archived_read.json')['archive']==info


def test_completed_native_read_reopens_and_failed_read_needs_a_fresh_owned_attempt(tmp_path, monkeypatch):
    from hashlib import sha256
    from sys import executable
    from nasolve import cif_fitted_native_read as native
    from nasolve.campaign_records import write_record

    run = tmp_path/'run'
    source = run/'PostMR/SugarFit/preparation-0002/fit-0001'
    source.mkdir(parents=True)
    model = source/'candidate.pdb'
    model.write_bytes(b'coordinate fixture\n')
    fit_record = source/'result.json'
    write_record(fit_record, {'site':'A:7'})
    fit = SimpleNamespace(number=1, model=model, report=fit_record)
    plan = SimpleNamespace(result_sha256='1'*64, native_receipt_sha256='2'*64, consumer={'version':'test'})
    inputs = run/'restraints'
    inputs.mkdir()
    cif = inputs/'A.cif'
    phil = inputs/'pairs.phil'
    cif.write_text('data_A\n')
    phil.write_text('geometry_restraints {}\n')
    checked = SimpleNamespace(attempt_number=2, dictionary_paths=(cif,), restraint_paths=(phil,))
    installation = SimpleNamespace(executables={'phenix.ready_set':Path(executable),'phenix.python':Path(executable)},
                                   version='test', environment=dict(os.environ))
    monkeypatch.setattr(native, 'verify_current_consumer', lambda *args:None)
    calls = []
    def read(model_path, dictionaries, out, exe, **kw):
        assert model_path == model and dictionaries == (cif,) and kw['phil_files'] == (phil,)
        assert kw['inventory_detail'] == 'linked' and kw['full_monomer_inventory'] and kw['policy_inventory']
        job = out/'cif-native-controlled'
        job.mkdir(parents=True)
        calls.append(job)
        command = [executable, '-c', 'print(12)']
        code = kw['_process_runner'](command, cwd=job, log_path=job/'native.log',
                                     environment=kw['environment'], timeout_seconds=kw['timeout_seconds'])
        (job/'native_receipt.json').write_text(json.dumps({'attempt':len(calls)}))
        return {'native_directory':str(job), 'status':'REVIEW', 'command':command, 'execution':{'returncode':code}}
    monkeypatch.setattr(native, 'inspect_native_bundle', read)
    def verify(p):
        data=p.read_bytes()
        if json.loads(data)['attempt']==1: raise ValueError('Unresolved chemistry in test')
        return {p:data,p.parent/'native.log':(p.parent/'native.log').read_bytes()}
    def offline():raise AssertionError('A saved reading discovered Phenix')
    args=(run,checked,plan,fit)
    with pytest.raises(ValueError,match='Unresolved chemistry'):
        native.acquire_fit_read(*args, discover=lambda:installation, after=None, verify=verify)
    with pytest.raises(ValueError,match='after-native-read 1'):
        native.acquire_fit_read(*args, discover=offline, after=None, verify=verify)
    receipt, selected = native.acquire_fit_read(*args, discover=lambda:installation, after=1, verify=verify)
    assert len(calls)==2 and receipt==calls[1]/'native_receipt.json'
    assert (calls[0]/'native_receipt.json').read_text()=='{"attempt": 1}'
    snapshots={p:sha256(b).hexdigest() for p,b in selected.items()}
    same, again = native.acquire_fit_read(*args, discover=offline, after=None, verify=verify)
    assert same==receipt and {p:sha256(b).hexdigest() for p,b in again.items()}==snapshots
    assert len(calls)==2
    with pytest.raises(ValueError,match='already available'):
        native.acquire_fit_read(*args, discover=offline, after=2, verify=verify)
