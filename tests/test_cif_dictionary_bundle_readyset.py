"""Exercise maintained ordinary helper control flow using explicit fake tools."""
from copy import deepcopy
from pathlib import Path
import json,shutil
from unittest.mock import patch
import pytest
from tests.test_cif_dictionary_bundle import fixture
from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle
from nasolve.cif_dictionary_bundle_readyset import readyset_endpoint_inputs,inspect_dictionary_bundle_readyset


def control(tmp_path,monkeypatch,behavior='noop'):
    from tests.test_cif_postmr_readyset import setup
    from nasolve.cif_postmr_readyset import audit_readyset_bundle_consumption
    fake=tmp_path/'fake';fake.mkdir();_,_,_,installation,consumer=setup(fake,monkeypatch,behavior)
    args=fixture(tmp_path,consumer=consumer)
    # Put synthetic phosphate atoms at nondegenerate tetrahedra so the ordinary
    # helper's real geometry guards run. This does not qualify the fake numerics.
    lines=[];d=.924
    offsets={'OP1':(d,d,d),'OP2':(d,-d,-d),'OP3':(-d,d,-d),"O5'":(-d,-d,d)}
    for line in args['model'].read_text().splitlines(keepends=True):
        if line.startswith(('ATOM  ','HETATM')):
            site=int(line[22:26]);name=line[12:16].strip();base=10.*(site-1);y=100. if line[21]=='B' else 0.
            delta=offsets.get(name,(0.,0.,0.))
            xyz=(base+delta[0],y+delta[1],delta[2])
            if name=="O3'":xyz=(base+10.-d,y+d,-d)
            line=line[:30]+''.join(f'{x:8.3f}' for x in xyz)+line[54:]
        lines.append(line)
    args['model'].write_text(''.join(lines))
    prepare_dictionary_bundle(output=tmp_path/'bundle',**args)
    b=read_dictionary_bundle(tmp_path/'bundle')
    monkeypatch.setattr('nasolve.cif_postmr_readyset.verify_current_consumer',lambda *a:True)
    audit_readyset_bundle_consumption(b['source'],b['dictionary'],b['model'],b['report']['components'],installation,
        b['report']['consumer'],tmp_path/'readyset',component_dictionaries=b['component_dictionaries'])
    for phase in ['before','after']:(tmp_path/phase).write_text('{}')
    return b,installation


def test_ordinary_per_component_inputs_replay_without_installation_or_originals(tmp_path,monkeypatch):
    b,installation=control(tmp_path,monkeypatch)
    expected=readyset_endpoint_inputs(tmp_path/'bundle',tmp_path/'readyset')
    assert len(expected['dictionaries'])==3 and len(expected['checks'])==8
    shutil.rmtree(installation.root)
    for name in ['first','second']:shutil.rmtree(tmp_path/name)
    (tmp_path/'model.pdb').unlink()
    (tmp_path/'bundle').rename(tmp_path/'moved_bundle');(tmp_path/'readyset').rename(tmp_path/'moved_readyset')
    with patch('subprocess.Popen',side_effect=AssertionError('Cold reader executes nothing')):
        result=readyset_endpoint_inputs(tmp_path/'moved_bundle',tmp_path/'moved_readyset')
    assert result['checks']==expected['checks']


@pytest.mark.parametrize('defect',['component','order','checks','trace','arguments','worker','input','effective','source','endpoint'])
def test_forged_success_cannot_replace_actual_evidence(tmp_path,monkeypatch,defect):
    b,_=control(tmp_path,monkeypatch);root=tmp_path/'readyset';p=root/'readyset_consumption.json';r=json.loads(p.read_text())
    if defect=='component':r['components'][0]='BAD'
    if defect=='order':r['ordinary_arguments'][-2:]=r['ordinary_arguments'][-2:][::-1]
    if defect=='checks':r['checks']['unchanged_heavy_sites']=1
    if defect=='trace':r['trace']['builder_calls']=1
    if defect=='arguments':r['ordinary_arguments'][2]='ready_set.actions.hydrogens=True'
    if defect=='worker':(root/'readyset/consumption_worker.py').write_text('print("fake")')
    if defect=='input':(root/r['component_inputs']['YYY']['path']).write_text('data_bad')
    if defect=='effective':(root/r['effective_dictionary']['path']).write_text('data_bad')
    if defect=='source':r['source_evidence']['sources'][0]['sha256']='0'*64
    if defect=='endpoint':r['readyset_model']['path']='../outside.pdb'
    p.write_text(json.dumps(r))
    with pytest.raises((ValueError,OSError,KeyError)):readyset_endpoint_inputs(tmp_path/'bundle',root)


@pytest.mark.parametrize('behavior',['fail','builder','template','bad_actions','child'])
def test_observed_failed_improvement_keeps_checked_start(tmp_path,monkeypatch,behavior):
    b,_=control(tmp_path,monkeypatch,behavior)
    # Starting scientific qualification is mocked here; real native controls
    # separately exercise both successful selection and atom-order fallback.
    monkeypatch.setattr('nasolve.cif_dictionary_bundle_readyset.inspect_dictionary_bundle_native',
        lambda *a:initial(True))
    r=inspect_dictionary_bundle_readyset(tmp_path/'bundle',tmp_path/'before',tmp_path/'after',tmp_path/'readyset')
    assert r['decision']['selected']=='verified_prepared_model' and r['endpoint_error']
    assert not r['automatic_adoption'] and not r['decision']['requires_cif_review']


def test_missing_final_native_evidence_keeps_start_and_unusable_start_selects_nothing(tmp_path,monkeypatch):
    b,_=control(tmp_path,monkeypatch)
    for usable in [True,False]:
        monkeypatch.setattr('nasolve.cif_dictionary_bundle_readyset.inspect_dictionary_bundle_native',
            lambda *a:initial(usable))
        r=inspect_dictionary_bundle_readyset(tmp_path/'bundle',tmp_path/'before',tmp_path/'after',tmp_path/'readyset')
        assert r['decision']['selected']==('verified_prepared_model' if usable else None)


def initial(usable):
    from hashlib import sha256
    digest=sha256(b'{}').hexdigest()
    return dict(diagnostic_continuation=dict(allowed=usable),baseline_receipt_sha256=digest,candidate_receipt_sha256=digest)


def test_malformed_saved_argument_type_keeps_verified_start(tmp_path,monkeypatch):
    control(tmp_path,monkeypatch)
    p=tmp_path/'readyset/readyset_consumption.json';r=json.loads(p.read_text())
    r['ordinary_arguments'][1]=42;p.write_text(json.dumps(r))
    monkeypatch.setattr('nasolve.cif_dictionary_bundle_readyset.inspect_dictionary_bundle_native',lambda *a:initial(True))
    review=inspect_dictionary_bundle_readyset(tmp_path/'bundle',tmp_path/'before',tmp_path/'after',tmp_path/'readyset')
    assert review['decision']['selected']=='verified_prepared_model'
    assert 'ReadySet model argument' in review['endpoint_error']
