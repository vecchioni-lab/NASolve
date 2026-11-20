"""Recorded statistics are readable without claiming a new scientific audit."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
from unittest.mock import patch

import pytest
from tests.test_metal_compact import trials
from nasolve.metal.recipe import digest, RecipeError
from nasolve.metal.compact import encode
from nasolve import cif_runtime_evidence as owner


def packed(tmp_path,monkeypatch):
    from nasolve.metal.input_archive import pack_fdp_inputs,expanded_fdp_inputs
    run,selected=trials(tmp_path,monkeypatch)
    archive=tmp_path/'inputs.zip';receipt=pack_fdp_inputs(run,selected,archive)
    with expanded_fdp_inputs(archive,receipt['archive_sha256'],projection_id=receipt['projection_id']) as (_,p):
        projection=deepcopy(p)
    record=projection['records'][0]
    args=dict(projection_id=receipt['projection_id'],trial_id=record['trial_id'],
              expected_parent=projection['bases'][record['basis_id']]['parent'])
    return archive,receipt,args,projection,run


def test_recorded_result_survives_source_removal_without_new_audit(tmp_path,monkeypatch):
    from nasolve.metal.input_archive import inspect_recorded_fdp
    archive,receipt,args,projection,run=packed(tmp_path,monkeypatch)
    shutil.rmtree(run)
    before=archive.read_bytes()
    with patch('subprocess.Popen',side_effect=AssertionError('No native work')):
        result=inspect_recorded_fdp(archive,receipt['archive_sha256'],**args)
    assert result['record']==projection['records'][0]
    assert result['request']==projection['requests'][result['record']['input_id']]
    assert result['basis']['parent']==args['expected_parent']
    assert result['status']=='RECORDED_FDP_REVIEW'
    assert result['native_evidence_replayed'] is False
    assert result['current_parent_verified'] is False
    assert result['reuse_authorized'] is False and result['retirement_authorized'] is False
    assert result['scientific_acceptance']=='NOT_ASSESSED'
    assert archive.read_bytes()==before
    # Identical requests remain distinct attempts, not merged measurements.
    other=inspect_recorded_fdp(archive,receipt['archive_sha256'],**dict(args,trial_id=projection['records'][2]['trial_id']))
    assert other['record']['input_id']==result['record']['input_id']
    assert other['record']['record_id']!=result['record']['record_id']


@pytest.mark.parametrize('change',['parent-id','parent-file','trial','projection','archive','budget'])
def test_wrong_selection_or_budget_preserves_all_evidence(tmp_path,monkeypatch,change):
    from nasolve.metal.input_archive import inspect_recorded_fdp
    archive,receipt,args,_,run=packed(tmp_path,monkeypatch)
    before={p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    args=deepcopy(args);identity=receipt['archive_sha256']
    if change=='parent-id':args['expected_parent']['geometry_id']='0'*64
    elif change=='parent-file':args['expected_parent']['manifest']['sha256']='0'*64
    elif change=='trial':args['trial_id']='0'*64
    elif change=='projection':args['projection_id']='0'*64
    elif change=='archive':identity='0'*64
    else:args['max_input_bytes']=1
    with pytest.raises((RecipeError,ValueError)):
        inspect_recorded_fdp(archive,identity,**args)
    assert {p:p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('change',['failed-result','failed-sibling','record-id','basis-id',
    'request-basis','occupancy','orphan-basis','missing-replay','accepted-result'])
def test_resealed_inconsistent_or_partial_records_cannot_be_inspected(tmp_path,monkeypatch,change):
    from nasolve.metal.input_archive import inspect_recorded_fdp
    archive,receipt,args,p,run=packed(tmp_path,monkeypatch)
    with owner.expanded_runtime_evidence(archive,receipt['archive_sha256']) as view:
        stage=tmp_path/'stage';shutil.copytree(view/'evidence',stage)
    (stage/'projection.json').chmod(0o600)
    row=p['records'][1 if change=='failed-sibling' else 0]
    if change in {'failed-result','failed-sibling'}:row['result']['freeze_audit']='FAIL'
    elif change=='record-id':row['result']['r_work']=.001
    elif change=='basis-id':p['bases'][row['basis_id']]['native_version']='changed'
    elif change=='request-basis':row['basis_id']='0'*64
    elif change=='occupancy':row['occupancy_vector']['m1']=.2
    elif change=='orphan-basis':p['bases']['0'*64]={}
    elif change=='missing-replay':p['source_replay']='NOT_REPLAYED'
    elif change=='accepted-result':row['result']['scientific_acceptance']='ACCEPTED'
    if change!='record-id':
        row.pop('record_id');row['record_id']=digest(row)
    p.pop('projection_id');p['projection_id']=digest(p)
    (stage/'projection.json').write_bytes(encode(p))
    altered=tmp_path/'altered.zip';packed_ref=owner.pack_runtime_evidence(stage,altered)
    before=altered.read_bytes()
    with pytest.raises((ValueError,RecipeError)):
        inspect_recorded_fdp(altered,packed_ref['archive_sha256'],**dict(args,projection_id=p['projection_id']))
    assert altered.read_bytes()==before


def test_partial_archive_is_preserved(tmp_path):
    from nasolve.metal.input_archive import inspect_recorded_fdp
    path=tmp_path/'partial.zip';path.write_bytes(b'interrupted write')
    with pytest.raises((ValueError,RecipeError)):
        inspect_recorded_fdp(path,'0'*64,projection_id='0'*64,trial_id='0'*64,
                             expected_parent={'geometry_id':'0'*64,'manifest':dict(anchor='run',
                                 relative_path='Metal/geometry_001/manifest.json',sha256='0'*64,size=1)})
    assert path.read_bytes()==b'interrupted write'
