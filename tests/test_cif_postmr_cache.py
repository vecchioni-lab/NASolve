"""Ordinary preparation reuses only exact-source dictionaries on a verified consumer."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import pytest

API = ['iotbx/phil.py','mmtbx/command_line/pdb_interpretation.py',
       'mmtbx/monomer_library/server.py','mmtbx/monomer_library/pdb_interpretation.py',
       'cctbx/geometry_restraints/linking_class.py','cctbx/geometry_restraints/auto_linking_types.py',
       'mmtbx/secondary_structure/__init__.py','mmtbx/secondary_structure/nucleic_acids.py']
ENERGY = ['cctbx/geometry_restraints/'+n+'.py' for n in ['flags','energies','manager']]


def prepared(tmp_path,monkeypatch,*,consumer_change=None,recipe_change=None):
    from tests.test_cif_dictionary_store import inputs
    from nasolve.cif_dictionary_store import make_dictionary_request,publish_dictionary
    import nasolve.curated_ligands as ligands
    s,c,m,q,o,_,p=inputs(tmp_path)
    root=tmp_path/'phenix';exe=root/'bin/phenix.python';exe.parent.mkdir(parents=True);exe.write_bytes(b'FAKE; NEVER EXECUTED\n')
    ready=root/'bin/phenix.ready_set';ready.write_bytes(b'FAKE; NEVER EXECUTED\n')
    def refs(names):
        rows=[]
        for n in names:
            path=root/'lib/python3.11/site-packages'/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('FAKE '+n).encode())
            rows.append({'anchor':'phenix_installation','path':path.relative_to(root).as_posix(),'sha256':sha256(path.read_bytes()).hexdigest()})
        return rows
    consumer={'name':'Phenix/CCTBX','version':'TEST','executable_sha256':sha256(exe.read_bytes()).hexdigest(),
              'api_sources':refs(API),'energy_sources':refs(ENERGY),
              'evidence_scope':'CURRENT_DISPATCHER_AND_API_FINGERPRINTS; FIXED_ISOLATED_SOURCE_REQUALIFICATION',
              'energy_library_resource_files':'NOT_CAPTURED; CURRENT_SITE_NATIVE_CHECKS_REMAIN_REQUIRED'}
    installation=SimpleNamespace(root=root,version='TEST',executables={'phenix.python':exe,'phenix.ready_set':ready},environment={})
    o.update(recipe={'policy_id':'cif-source-native-complete-candidate-v1',
                     'source_metadata_policy':'cif-source-declared-dna-metadata-v1','single_block_steps':180},
             generator={'name':'Phenix eLBOW','version':'ORIGINAL_PRODUCER'},consumer=consumer)
    if recipe_change:recipe_change(o)
    if consumer_change:consumer_change(consumer)
    req=make_dictionary_request(s,'Q17',**{k:o[k] for k in ['source_authority','recipe','generator']})
    entry=publish_dictionary(tmp_path/'store',req,s,c,q,consumer=consumer,provenance=p)
    selected=ligands.LigandDictionarySource('Q17',s,'EXPLICIT','local-verified')
    monkeypatch.setattr(ligands,'ligand_source',lambda *a,**k:selected)
    monkeypatch.setattr(ligands,'validate_ligand_dictionary',lambda *a:None)
    return s,c,q,o,p,entry,installation,ready


def call(tmp_path,installation,ready,**kwargs):
    from nasolve.cif_postmr_cache import prepare_postmr_dictionaries
    return prepare_postmr_dictionaries(['Q17'],ready,tmp_path/'run',store_root=tmp_path/'store',installation=installation,**kwargs)


def test_exact_current_consumer_reuses_and_freezes_original_producer(tmp_path,monkeypatch):
    from nasolve.cif_postmr_cache import read_postmr_dictionaries
    s,c,q,o,p,entry,installation,ready=prepared(tmp_path,monkeypatch)
    before={path:path.read_bytes() for path in (tmp_path/'store').rglob('*') if path.is_file()}
    report=call(tmp_path,installation,ready)
    assert report['components']['Q17']['status']=='REUSED'
    result=read_postmr_dictionaries(tmp_path/'run')['Q17']
    assert result['source'].read_bytes()==s.read_bytes() and result['dictionary'].read_bytes()==c.read_bytes()
    assert result['numerics']['manifest']['request']['generator']==o['generator']
    assert result['numerics']['provenance']==p and result['report']['converged'] is False
    assert all(path.read_bytes()==data for path,data in before.items())
    assert report['requires_cif_review'] is False and report['dictionary_generation']=='NOT_RUN'
    shutil.rmtree(tmp_path/'store');shutil.rmtree(installation.root);s.unlink();c.unlink()
    (tmp_path/'run').rename(tmp_path/'relocated')
    assert read_postmr_dictionaries(tmp_path/'relocated')['Q17']['numerics']['provenance']==p


@pytest.mark.parametrize('change',['version','dispatcher','api','energy','missing_api','wrong_readyset','unknown_version','symlink_api'])
def test_changed_or_unverified_installation_uses_ordinary_source(tmp_path,monkeypatch,change):
    s,c,q,o,p,entry,installation,ready=prepared(tmp_path,monkeypatch)
    if change=='version':installation.version='UPGRADED'
    if change=='unknown_version':installation.version='unknown'
    if change=='dispatcher':installation.executables['phenix.python'].write_bytes(b'CHANGED')
    if change in {'api','energy','missing_api','symlink_api'}:
        ref=o['consumer']['energy_sources' if change=='energy' else 'api_sources'][0]
        path=installation.root/ref['path']
        if change=='missing_api':path.unlink()
        elif change=='symlink_api':
            outside=tmp_path/'outside.py';outside.write_bytes(path.read_bytes());path.unlink();path.symlink_to(outside)
        else:path.write_bytes(b'CHANGED')
    if change=='wrong_readyset':installation.executables['phenix.ready_set']=installation.root/'bin/other'
    report=call(tmp_path,installation,ready)
    row=report['components']['Q17']
    assert row['status']=='ORDINARY_SOURCE_FALLBACK' and row['requalification']=='REQUIRED_BEFORE_CACHE_USE'
    from nasolve.cif_postmr_cache import read_postmr_dictionaries
    result=read_postmr_dictionaries(tmp_path/'run')['Q17']
    assert result['dictionary'].read_bytes()==s.read_bytes() and result['numerics'] is None


@pytest.mark.parametrize('change',['source_bytes','authority','corrupt_dictionary','stale_policy','bad_recipe','bad_generator','incomplete_api','unsafe_api','wrong_api_scope'])
def test_ineligible_or_corrupt_cache_never_becomes_a_name_based_hit(tmp_path,monkeypatch,change):
    kwargs={}
    if change=='incomplete_api':kwargs['consumer_change']=lambda c:c['api_sources'].pop()
    if change=='unsafe_api':kwargs['consumer_change']=lambda c:c['api_sources'][0].update(path='../outside.py')
    if change=='wrong_api_scope':kwargs['consumer_change']=lambda c:c['api_sources'][0].update(path=c['api_sources'][1]['path'])
    if change=='bad_recipe':kwargs['recipe_change']=lambda o:o['recipe'].update(policy_id='OTHER_REPAIR')
    if change=='bad_generator':kwargs['recipe_change']=lambda o:o['generator'].update(name='OTHER_BACKEND')
    s,c,q,o,p,entry,installation,ready=prepared(tmp_path,monkeypatch,**kwargs)
    if change=='source_bytes':s.write_bytes(s.read_bytes()+b'\n# distinct source\n')
    if change=='authority':
        import nasolve.curated_ligands as ligands
        monkeypatch.setattr(ligands,'ligand_source',lambda *a,**k:ligands.LigandDictionarySource('Q17',s,'CURATED','curated'))
    if change=='corrupt_dictionary':(entry['directory']/'dictionary.cif').write_bytes(b'DAMAGED')
    if change=='stale_policy':
        import nasolve.cif_candidate_usability as usability
        monkeypatch.setattr(usability,'POLICY_ID','cif-isolated-candidate-native-usability-v99')
    report=call(tmp_path,installation,ready)
    assert report['components']['Q17']['status']=='ORDINARY_SOURCE_FALLBACK'
    assert report['requires_cif_review'] is False


def test_missing_curated_source_stops_before_cache_lookup(tmp_path):
    from nasolve.cif_postmr_cache import prepare_postmr_dictionaries
    with pytest.raises(FileNotFoundError,match='Curated dictionary'):
        prepare_postmr_dictionaries(['1AP'],tmp_path/'never_execute',tmp_path/'run',data_root=tmp_path/'missing',store_root=tmp_path/'store')
    assert not (tmp_path/'run').exists()


@pytest.mark.parametrize('defect',['source','dictionary','authority','absolute_path'])
def test_run_result_rejects_broken_operational_bindings(tmp_path,monkeypatch,defect):
    from nasolve.cif_postmr_cache import read_postmr_dictionaries
    s,c,q,o,p,entry,installation,ready=prepared(tmp_path,monkeypatch)
    call(tmp_path,installation,ready);path=tmp_path/'run/postmr_dictionaries.json';r=json.loads(path.read_text())
    row=r['components']['Q17']
    if defect=='source':(tmp_path/'run'/row['source']['path']).write_bytes(b'DAMAGED')
    if defect=='dictionary':(tmp_path/'run'/row['dictionary']['path']).write_bytes(b'DAMAGED')
    if defect=='authority':row['source_authority']='NATIVE'
    if defect=='absolute_path':row['dictionary']['path']=str(c.resolve())
    path.write_text(json.dumps(r))
    with pytest.raises((ValueError,KeyError)):read_postmr_dictionaries(tmp_path/'run')


def test_ordinary_postmr_passes_cached_numerics_to_readyset_and_preserves_source(tmp_path,monkeypatch):
    import nasolve.postmr as postmr
    import nasolve.cif_postmr_cache as cache
    from tests.test_postmr import postmr_model_text,make_data_root
    from tests.helpers import make_postmr_report,make_ready_set
    source=tmp_path/'source.pdb';source.write_text(postmr_model_text())
    run=tmp_path/'run';make_postmr_report(run,source)
    data=make_data_root(tmp_path);raw=(data/'ligands/DE.cif').read_bytes()
    calls=[];original=cache.prepare_postmr_dictionaries
    # The production call reads the same shared result; substitute a marked
    # numerical path only at its public result boundary in this glue test.
    actual_read=cache.read_postmr_dictionaries;injected={}
    def stage(*args,**kwargs):
        report=original(*args,**kwargs);folder=Path(args[2]);candidate=folder/'DE/fixture_numerics.cif'
        candidate.write_bytes(raw+b'# EXPLICIT_CACHE_INTEGRATION_FIXTURE\n');injected['folder']=folder;injected['candidate']=candidate;calls.append(args)
        return report
    def read(folder):
        loaded=actual_read(folder)
        if Path(folder)==injected.get('folder'):loaded['DE']['dictionary']=injected['candidate']
        return loaded
    monkeypatch.setattr(cache,'prepare_postmr_dictionaries',stage);monkeypatch.setattr(cache,'read_postmr_dictionaries',read)
    def builder(_model,_pairs,out):out.write_text('geometry_restraints.edits {}\n')
    result=postmr.prepare_postmr(run,make_ready_set(tmp_path),data_root=data,narestraints_builder=builder)
    assert result.status=='POSTMR_READY' and len(calls)==1
    assert (result.postmr_directory/'Restraints/source_dictionaries/DE.cif').read_bytes()==raw
    assert b'EXPLICIT_CACHE_INTEGRATION_FIXTURE' in (result.postmr_directory/'Restraints/DE.cif').read_bytes()
    assert b'EXPLICIT_CACHE_INTEGRATION_FIXTURE' in (result.postmr_directory/'Restraints/curated_ligands.cif').read_bytes()
    assert 'dictionary_reuse' in json.loads(result.report_path.read_text())['cif_doctor']


def test_discovery_is_lazy_and_receives_the_configured_executable(tmp_path,monkeypatch):
    from nasolve.cif_postmr_cache import prepare_postmr_dictionaries
    import nasolve.phenix_runtime as runtime
    s,c,q,o,p,entry,installation,ready=prepared(tmp_path,monkeypatch);calls=[]
    def discover(path,**kwargs):
        assert path==ready and kwargs['base_environment']=={'EXPLICIT':'SELECTED'}
        calls.append(path);return installation
    monkeypatch.setattr(runtime,'installation_from_candidate',discover)
    report=prepare_postmr_dictionaries(['Q17'],ready,tmp_path/'fresh',store_root=tmp_path/'store',environment={'EXPLICIT':'SELECTED'})
    assert report['components']['Q17']['status']=='REUSED' and calls==[ready]
    shutil.rmtree(tmp_path/'store')
    def forbidden(*a,**k):raise AssertionError('A cache miss must not start Phenix discovery')
    monkeypatch.setattr(runtime,'installation_from_candidate',forbidden)
    report=prepare_postmr_dictionaries(['Q17'],ready,tmp_path/'miss',store_root=tmp_path/'store')
    assert report['components']['Q17']['status']=='ORDINARY_SOURCE_FALLBACK'


def test_ordinary_postmr_keeps_its_normal_error_boundary_for_acquisition_failures(tmp_path,monkeypatch):
    import nasolve.postmr as postmr
    import nasolve.cif_postmr_cache as cache
    from tests.test_postmr import postmr_model_text,make_data_root
    from tests.helpers import make_postmr_report,make_ready_set
    source=tmp_path/'source.pdb';source.write_text(postmr_model_text());original=source.read_bytes()
    run=tmp_path/'run';make_postmr_report(run,source)
    def missing(*a,**k):raise FileNotFoundError('Curated dictionary disappeared before freezing')
    monkeypatch.setattr(cache,'prepare_postmr_dictionaries',missing)
    def builder(_model,_pairs,out):out.write_text('geometry_restraints.edits {}\n')
    with pytest.raises(postmr.PostMRPreparationError,match='Dictionary acquisition failed: Curated dictionary'):
        postmr.prepare_postmr(run,make_ready_set(tmp_path),data_root=make_data_root(tmp_path),narestraints_builder=builder)
    assert source.read_bytes()==original
