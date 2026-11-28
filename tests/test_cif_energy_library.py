"""Installed library provenance is distinct from chemical target approval."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch
import pytest
from tests.test_cif_phenix_configuration import sdk_at,configure
from tests.test_cif_linear_bond_reference import energy_inputs


def case(tmp_path):
    sdk,site=sdk_at(tmp_path/'sdk')
    p=site/'iotbx/cif/__init__.py';p.parent.mkdir(parents=True);p.write_text('# synthetic native parser\n')
    source,_,library,_=energy_inputs(tmp_path)
    target=site/'chem_data/geostd/ener_lib.cif';target.parent.mkdir(parents=True);target.write_bytes(library.read_bytes())
    return sdk,configure(sdk).consumer,source,target


def fake_runner(library,mode='pass'):
    def run(command,*,cwd,log_path,environment,timeout_seconds):
        from nasolve import cif_energy_library as m
        log_path.write_text('SYNTHETIC installed-library execution\n')
        if mode=='interrupt':raise KeyboardInterrupt()
        if mode in {'timeout','unknown_timeout'}:
            exc=subprocess.TimeoutExpired(command,timeout_seconds)
            if mode=='timeout':exc.returncode=-15;exc.stopped_verified=True
            raise exc
        if mode=='failed':return 2
        spec=json.loads((cwd/'spec.json').read_text());root=Path(command[-1]);data=library.read_bytes()
        (cwd/'energy-library.cif').write_bytes(data)
        result=dict(spec_sha256=sha256((cwd/'spec.json').read_bytes()).hexdigest(),
            modules=spec['modules'],modules_after=spec['modules'],lookup=m.LOOKUP,
            resource=dict(anchor='phenix_installation',path=library.relative_to(root).as_posix(),sha256=sha256(data).hexdigest(),size=len(data)),
            parsed_tables_sha256=m._tables_digest(cwd/'energy-library.cif'))
        if mode=='changed_sdk':(root/spec['modules'][0]['path']).write_text('# changed while native process ran\n')
        (cwd/'native-result.json').write_text(json.dumps(result));return 0
    return run


def rebind(root):
    from nasolve import cif_energy_library as m
    report=json.loads((root/m.REPORT).read_text());report['outputs']=m._inventory(root)
    (root/m.REPORT).write_text(json.dumps(report))


def test_native_library_and_reference_replay_after_original_sdk_removed(tmp_path):
    from nasolve import cif_energy_library as m
    from nasolve.cif_linear_bond_reference import energy_library_linear_reference
    sdk,consumer,source,library=case(tmp_path);out=tmp_path/'out';r=energy_library_linear_reference(source,source,'Q17',library)
    report=m.capture_energy_library(sdk,consumer,out,_process_runner=fake_runner(library))
    assert report['status']=='SELECTED_NATIVE_ENERGY_LIBRARY_CAPTURED'
    assert not report['automatic_adoption'] and report['chemical_approval']=='NOT_ASSESSED'
    assert 'keep-this-live-only' not in (out/m.REPORT).read_text()+(out/'spec.json').read_text()
    q=m.qualify_energy_reference(source,source,'Q17',r,out,consumer=consumer)
    assert q['reference_authority']=='EXACT_ROWS_FROM_SELECTED_NATIVE_LIBRARY'
    assert q['supported_bonds']==[['L','X']] and len(q['unsupported_bonds'])==2
    moved=out.rename(tmp_path/'moved');shutil.rmtree(sdk.root);library=tmp_path/'energy.cif';library.unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('No SDK execution on read')):
        assert m.read_energy_library(moved)==report
        assert m.qualify_energy_reference(source,source,'Q17',r,moved,consumer=consumer)==q


@pytest.mark.parametrize('mode',['failed','timeout'])
def test_known_native_failure_stays_review_and_cannot_authorize_reference(tmp_path,mode):
    from nasolve import cif_energy_library as m
    sdk,consumer,source,library=case(tmp_path);out=tmp_path/'out'
    r=m.capture_energy_library(sdk,consumer,out,_process_runner=fake_runner(library,mode))
    assert r['status']=='REVIEW' and r['new_native_calls']==1
    with pytest.raises(ValueError):m.qualify_energy_reference(source,source,'Q17',{},out,consumer=consumer)
    moved=out.rename(tmp_path/'moved');shutil.rmtree(sdk.root)
    assert m.read_energy_library(moved)==r


@pytest.mark.parametrize('mode',['interrupt','unknown_timeout','changed_sdk'])
def test_uncertain_cleanup_or_changed_sdk_cannot_seal_evidence(tmp_path,mode):
    from nasolve import cif_energy_library as m
    from nasolve.campaign_process import CampaignProcessError
    sdk,consumer,source,library=case(tmp_path);out=tmp_path/'out'
    expected={'interrupt':KeyboardInterrupt,'unknown_timeout':CampaignProcessError,'changed_sdk':ValueError}[mode]
    with pytest.raises(expected):m.capture_energy_library(sdk,consumer,out,_process_runner=fake_runner(library,mode))
    assert (out/'spec.json').is_file() and not (out/m.REPORT).exists()


@pytest.mark.parametrize('defect',['table','module','path','lookup','spec','worker','extra','approval','count','elapsed'])
def test_rehashed_changed_library_evidence_is_refused(tmp_path,defect):
    from nasolve import cif_energy_library as m
    sdk,consumer,source,library=case(tmp_path);out=tmp_path/'out'
    m.capture_energy_library(sdk,consumer,out,_process_runner=fake_runner(library))
    result=out/'native-result.json';data=json.loads(result.read_text());report=out/m.REPORT;r=json.loads(report.read_text())
    if defect=='table':data['parsed_tables_sha256']='0'*64
    if defect=='module':data['modules_after'][0]['sha256']='0'*64
    if defect=='path':data['resource']['path']='../outside/ener_lib.cif'
    if defect=='lookup':data['lookup']='guessed_by_basename'
    if defect=='spec':data['spec_sha256']='0'*64
    if defect=='worker':(out/'worker.py').write_text('print("untrusted")\n')
    if defect=='extra':(out/'unexpected.cif').write_text('data_unknown\n')
    if defect=='approval':r['automatic_adoption']=True
    if defect=='count':r['new_native_calls']=0
    if defect=='elapsed':r['execution']['elapsed_seconds']=float('nan')
    result.write_text(json.dumps(data));report.write_text(json.dumps(r));rebind(out)
    with pytest.raises(ValueError):m.read_energy_library(out)


@pytest.mark.parametrize('defect',['reference_target','reference_hash','consumer','source'])
def test_reference_must_reproduce_exact_selected_library_and_source(tmp_path,defect):
    from nasolve import cif_energy_library as m
    from nasolve.cif_linear_bond_reference import energy_library_linear_reference
    sdk,consumer,source,library=case(tmp_path);out=tmp_path/'out';r=energy_library_linear_reference(source,source,'Q17',library)
    m.capture_energy_library(sdk,consumer,out,_process_runner=fake_runner(library))
    if defect=='reference_target':next(x for x in r['bonds'] if x['status']=='SUPPORTED')['equilibrium_angstrom']=1.5
    if defect=='reference_hash':r['provider']['library_sha256']='0'*64
    if defect=='consumer':consumer['version']='another'
    if defect=='source':source.write_text(source.read_text().replace('Q17','OTHER'))
    with pytest.raises(ValueError):m.qualify_energy_reference(source,source,'Q17',r,out,consumer=consumer)


def test_preflight_refuses_changed_consumer_and_reusing_output(tmp_path):
    from nasolve import cif_energy_library as m
    sdk,consumer,source,library=case(tmp_path);out=tmp_path/'out';bad=deepcopy(consumer);bad['executable_sha256']='0'*64
    with pytest.raises(ValueError):m.capture_energy_library(sdk,bad,out,_process_runner=fake_runner(library))
    assert not out.exists()
    m.capture_energy_library(sdk,consumer,out,_process_runner=fake_runner(library));frozen={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(ValueError):m.capture_energy_library(sdk,consumer,out,_process_runner=fake_runner(library))
    assert {p.name:p.read_bytes() for p in out.iterdir()}==frozen


@pytest.mark.parametrize('wrong_consumer',[False,True])
def test_bond_attribution_requires_the_same_complete_native_consumer(tmp_path,wrong_consumer):
    from nasolve import cif_energy_library as m
    from nasolve import cif_captured_bond_attribution as bond
    from tests.test_cif_captured_bond_attribution import fixture,fake_runner as bond_runner
    from tests.test_cif_attachment_native import rebind as bind_capture
    native=tmp_path/'native';native.mkdir();sdk,consumer,source,library=case(native)
    saved=tmp_path/'library';m.capture_energy_library(sdk,consumer,saved,_process_runner=fake_runner(library))
    # Separate graph fixture uses an MMFF reference; it may never borrow this
    # authentic library capture merely because the producer matches.
    base=tmp_path/'bond';base.mkdir();args,tool,refs=fixture(base)
    receipts=args[3:5]
    for receipt in receipts:
        record=json.loads(receipt.read_text());record['phenix_version']=sdk.version;record['executable_sha256']=consumer['executable_sha256']
        record['native_validation']['installed_api_sources']=[dict(module=r['path'].split('/site-packages/')[1].removesuffix('.py').replace('/','.'),historical_path='/historical/'+r['path'],sha256=r['sha256']) for r in consumer['api_sources']]
        record['native_validation']['energy_inventory']['installed_sources']=[dict(module='cctbx.geometry_restraints.'+r['path'].split('/')[-1].removesuffix('.py'),historical_path='/historical/'+r['path'],sha256=r['sha256']) for r in consumer['energy_sources']]
        receipt.write_text(json.dumps(record));bind_capture(receipt)
    tool.version=sdk.version;tool.executables=sdk.executables
    attribution=tmp_path/'attribution';bond.audit_captured_bond_attribution(*args,tool,attribution,bonds=[['Y','R']],_process_runner=bond_runner(refs))
    if wrong_consumer:consumer['version']='another'
    with pytest.raises(ValueError,match='consumer|reference'):
        m.qualify_bond_attribution_reference(attribution,saved,consumer=consumer)


@pytest.mark.parametrize('mode',['outside','oversized'])
def test_maintained_worker_bounds_native_resolver_result_before_parsing(tmp_path,mode):
    import sys
    from nasolve import cif_energy_library as m
    sdk,consumer,source,library=case(tmp_path)
    if mode=='outside':target=tmp_path/'outside.cif';target.write_bytes(library.read_bytes())
    else:target=library;target.write_bytes(b'x'*(m.MAX_SOURCE_BYTES+1))
    site=library.parents[2];marker=tmp_path/'parser_was_called'
    server=site/'mmtbx/monomer_library/server.py'
    server.write_text('from pathlib import Path\n'
        +'def find_mon_lib_file(relative_path_components):\n    return '+repr(str(target))+'\n'
        +'def mon_lib_ener_lib_cif(path):\n    Path('+repr(str(marker))+').write_text("called")\n    raise AssertionError("Must refuse before parsing")\n')
    consumer=configure(sdk).consumer
    def run(command,*,cwd,log_path,environment,timeout_seconds):
        with log_path.open('w') as log:
            return subprocess.run([sys.executable,*command[1:]],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=10).returncode
    out=tmp_path/'out';result=m.capture_energy_library(sdk,consumer,out,_process_runner=run)
    assert result['status']=='REVIEW' and not marker.exists()
    expected='Unselected numerical library' if mode=='outside' else 'Oversized or nonregular numerical library'
    assert expected in (out/'native.log').read_text()
