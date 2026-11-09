"""Exact acquired components feed the existing site/bundle preparer."""
from copy import deepcopy
from pathlib import Path
import shutil
from unittest.mock import patch
import pytest
from nasolve.campaigns import CampaignError


@pytest.fixture
def case(tmp_path,monkeypatch):
    from nasolve import cif_acquisition_preparation as m
    from nasolve import curated_ligands as ligands
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources,read_acquisition_sources
    from nasolve.cif_acquisition_attempt import acquire_dictionary_attempt
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    from tests.test_cif_dictionary_bundle import fixture
    ordinary=fixture(tmp_path);data=tmp_path/'data';(data/'ligands').mkdir(parents=True)
    monkeypatch.setattr(ligands,'_registered_record',lambda code: {'Ligand code':code})
    saved={}
    for item in ordinary['components']:
        value=resolve_dictionary_snapshot(item['snapshot']);code=value['manifest']['request']['component'];saved[code]=(item,value)
        (data/'ligands'/f'{code}.cif').write_bytes(value['source'].read_bytes())
    selection=tmp_path/'sources';freeze_acquisition_sources(list(saved),selection,data_root=data)
    sources=read_acquisition_sources(selection)['sources'];components=[]
    for code,(item,value) in saved.items():
        sdk=tmp_path/'missing-sdk';pin=dict(anchor='phenix_installation',path='api.py',sha256='1'*64,size=6)
        generation=dict(installation_root=sdk,python_executable=sdk/'python',elbow_executable=sdk/'elbow',api_sources=[pin],prior_sources=[pin],expected_dialect='CHEMICAL_COMPONENTS_CIF',phenix_version='TEST',environment={},bond_representation_policy=value['manifest']['request']['recipe']['bond_representation_policy'])
        request=tmp_path/('request-'+code)
        acquire_dictionary_attempt(sources[code]['source'],code,tmp_path/('cache-'+code),request,source_authority=sources[code]['source_authority'],consumer=ordinary['consumer'],generation=generation,retained_snapshot=item['snapshot'])
        components.append(dict(code=code,request_directory=request,attempt_number=1,contexts=item['contexts']))
    return m,dict(source_selection=selection,components=components,model=ordinary['model'],consumer=ordinary['consumer'],expected_links=ordinary['expected_links'],native_context=ordinary['native_context']),tmp_path/'prepared'


def inventory(root):
    return {str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}


def test_exact_acquisitions_prepare_existing_bundle_and_replay_cold(case):
    from nasolve.cif_dictionary_bundle import read_dictionary_bundle
    m,args,out=case
    with patch('subprocess.Popen',side_effect=AssertionError('Preparation must not run native jobs')):
        report=m.prepare_acquired_dictionary_bundle(output=out,**args)
    assert report['status']=='PREPARED_REVIEW' and report['automatic_adoption'] is False
    loaded=m.read_acquired_dictionary_bundle(out);assert loaded['bundle']['report']['components']==['YYY','ZZZ']
    assert read_dictionary_bundle(loaded['bundle_directory'])['report']==loaded['bundle']['report']
    before=inventory(out);out=out.rename(out.with_name('relocated'))
    for item in args['components']:shutil.rmtree(item['request_directory'])
    shutil.rmtree(args['source_selection']);args['model'].unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Replay must not run native jobs')):
        assert m.read_acquired_dictionary_bundle(out)['report']==report
    assert inventory(out)==before


@pytest.mark.parametrize('defect',['attempt','coverage','duplicate','consumer','source'])
def test_wrong_acquisition_binding_never_publishes(case,defect):
    m,args,out=case;args=deepcopy(args)
    if defect=='attempt':args['components'][0]['attempt_number']=2
    elif defect=='coverage':args['components'].pop()
    elif defect=='duplicate':args['components'][1]=deepcopy(args['components'][0])
    elif defect=='consumer':args['consumer']['version']='OTHER'
    else:(args['source_selection']/'sources/ZZZ.cif').write_text('changed')
    with pytest.raises(ValueError):m.prepare_acquired_dictionary_bundle(output=out,**args)
    assert not out.exists()


@pytest.mark.parametrize('defect',['site','link','context'])
def test_existing_site_guards_keep_frozen_inputs_but_withhold_completion(case,defect):
    m,args,out=case;args=deepcopy(args)
    if defect=='site':args['components'][0]['contexts'].pop()
    elif defect=='link':args['expected_links'].pop()
    else:args['native_context']['monomer_inventory']='selected_only'
    with pytest.raises(ValueError):m.prepare_acquired_dictionary_bundle(output=out,**args)
    assert not (out/'acquisition_preparation.json').exists()
    assert all(item['request_directory'].exists() for item in args['components'])


@pytest.mark.parametrize('boundary',['copy','prepare','seal'])
def test_interruption_preserves_partial_work_and_requires_fresh_output(case,monkeypatch,boundary):
    m,args,out=case
    if boundary=='copy':
        original=m._freeze
        def stop(root,files,dirs):original(root,files,dirs);raise KeyboardInterrupt('copy boundary')
        monkeypatch.setattr(m,'_freeze',stop)
    elif boundary=='prepare':
        original=m.prepare_dictionary_bundle
        def stop(*a,**k):original(*a,**k);raise KeyboardInterrupt('prepare boundary')
        monkeypatch.setattr(m,'prepare_dictionary_bundle',stop)
    else:
        original=m.write_record
        def stop(path,value,**kwargs):
            if path.name=='acquisition_preparation.json':raise KeyboardInterrupt('completion boundary')
            return original(path,value,**kwargs)
        monkeypatch.setattr(m,'write_record',stop)
    with pytest.raises(KeyboardInterrupt):m.prepare_acquired_dictionary_bundle(output=out,**args)
    before=inventory(out);assert before and not (out/'acquisition_preparation.json').exists()
    with pytest.raises(FileExistsError):m.prepare_acquired_dictionary_bundle(output=out,**args)
    assert inventory(out)==before
    with pytest.raises((ValueError,OSError,CampaignError)):m.read_acquired_dictionary_bundle(out)


@pytest.mark.parametrize('defect',['model','source','attempt','claim','boolean','extra','empty_directory','snapshot','contexts'])
def test_readback_refuses_tampered_preparation(case,defect):
    from nasolve.campaign_records import read_record,write_record
    m,args,out=case;m.prepare_acquired_dictionary_bundle(output=out,**args)
    if defect=='model':(out/'bundle/inputs/model.pdb').write_text('changed')
    elif defect=='source':(out/'inputs/sources/sources/ZZZ.cif').write_text('changed')
    elif defect=='snapshot':(out/'bundle/components/ZZZ/snapshot/entry/dictionary.cif').write_text('changed')
    elif defect=='extra':(out/'unexpected').write_text('unbound')
    elif defect=='empty_directory':(out/'unexpected').mkdir()
    elif defect=='contexts':
        p=out/'preparation_intent.json';r=read_record(p);r['controls']['sites']['ZZZ']['contexts'].reverse();write_record(p,r,replace=True)
    else:
        p=out/'acquisition_preparation.json';r=read_record(p)
        if defect=='attempt':r['selected_attempts']['ZZZ']['attempt_number']=2
        elif defect=='boolean':r['automatic_adoption']=0
        else:r['scientific_qualification']='PASS'
        write_record(p,r,replace=True)
    with pytest.raises((ValueError,OSError,CampaignError)):m.read_acquired_dictionary_bundle(out)


def test_shared_phils_are_frozen_in_order(case,tmp_path):
    m,args,out=case;first=tmp_path/'one.phil';second=tmp_path/'two.phil';first.write_text('# first\n');second.write_text('# second\n')
    m.prepare_acquired_dictionary_bundle(output=out,supplementary_phils=[second,first],**args)
    read=m.read_acquired_dictionary_bundle(out);assert [p.read_text() for p in read['bundle']['before_phils'][:2]]==['# second\n','# first\n']
    first.unlink();second.unlink();assert m.read_acquired_dictionary_bundle(out)['report']['status']=='PREPARED_REVIEW'


def test_empty_historical_directories_are_preserved(case):
    m,args,out=case
    # A persistent request can contain an empty interrupted next attempt. It is
    # not selected, resumed or silently deleted from the frozen readback evidence.
    request=args['components'][0]['request_directory'];(request/'attempts/attempt-0002').mkdir()
    m.prepare_acquired_dictionary_bundle(output=out,**args)
    code=args['components'][0]['code'];assert (out/'inputs/acquisitions'/code/'attempts/attempt-0002').is_dir()
    assert m.read_acquired_dictionary_bundle(out)['report']['selected_attempts'][code]['attempt_number']==1


def test_source_change_during_preparation_keeps_output_unfinished(case,monkeypatch):
    m,args,out=case;original=m.prepare_dictionary_bundle
    def changed(*a,**k):
        value=original(*a,**k);args['model'].write_bytes(args['model'].read_bytes()+b'REMARK changed\n');return value
    monkeypatch.setattr(m,'prepare_dictionary_bundle',changed)
    with pytest.raises(ValueError,match='source changed'):m.prepare_acquired_dictionary_bundle(output=out,**args)
    assert (out/'bundle').is_dir() and not (out/'acquisition_preparation.json').exists()


def test_single_acquisition_keeps_exact_attempt_and_site_bindings(case,tmp_path):
    from tests.test_cif_dictionary_bundle import select_single_component
    m,args,out=case;args=select_single_component(args,tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('Preparation must not execute')):
        report=m.prepare_acquired_dictionary_bundle(output=out,**args)
    loaded=m.read_acquired_dictionary_bundle(out)
    assert set(report['selected_attempts'])=={'ZZZ'} and report['selected_attempts']['ZZZ']['attempt_number']==1
    assert loaded['bundle']['report']['site_owners']=={'A:1':'ZZZ','A:2':'ZZZ'}
    before=inventory(out);out=out.rename(tmp_path/'relocated');shutil.rmtree(args['components'][0]['request_directory']);shutil.rmtree(args['source_selection']);args['model'].unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Replay must not execute')):
        assert m.read_acquired_dictionary_bundle(out)['report']==report
    assert inventory(out)==before
