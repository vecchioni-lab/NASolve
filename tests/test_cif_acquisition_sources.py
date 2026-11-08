"""Source selection freezes authority, not a native usability verdict."""
from pathlib import Path
import shutil
from unittest.mock import patch
import pytest


def dictionary(code, bonds="C1 C2"):
    return f"data_comp_{code}\n_chem_comp.id {code}\nloop_\n_chem_comp_bond.comp_id\n_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n{code} {bonds}\n#\n"


@pytest.fixture
def sources(tmp_path,monkeypatch):
    from nasolve import curated_ligands as ligands
    from nasolve import cif_acquisition_sources as m
    monkeypatch.setattr(ligands,'_registered_record',lambda code: {'Ligand code':code})
    data=tmp_path/'data';(data/'ligands').mkdir(parents=True)
    (data/'ligands/DE.cif').write_text(dictionary('DE','C4 S4'))
    (data/'ligands/ZZZ.cif').write_text(dictionary('ZZZ'))
    sdk=tmp_path/'phenix';ready=sdk/'bin/phenix.ready_set';ready.parent.mkdir(parents=True);ready.write_text('never execute')
    ccd=sdk/'lib/python3.12/site-packages/chem_data/chemical_components/y/data_YYY.cif';ccd.parent.mkdir(parents=True);ccd.write_text(dictionary('YYY'))
    return m,data,ready,ccd,tmp_path/'selection'


def inventory(root):
    return {str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}


def test_selection_preserves_precedence_and_relocates_without_discovery(sources,monkeypatch):
    m,data,ready,ccd,out=sources
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')):
        report=m.freeze_acquisition_sources(['ZZZ','YYY','DE'],out,data_root=data,ready_set_executable=ready)
    assert report['components']==['DE','YYY','ZZZ'] and report['native_validation']=='NOT_RUN'
    before=inventory(out);out=out.rename(out.with_name('relocated'));shutil.rmtree(data);shutil.rmtree(ready.parent.parent)
    monkeypatch.setattr(m,'ligand_source',lambda *a,**k:(_ for _ in ()).throw(AssertionError('No rediscovery')))
    result=m.read_acquisition_sources(out)
    assert {c:v['source_authority'] for c,v in result['sources'].items()}==dict(DE='CURATED',YYY='NATIVE',ZZZ='EXPLICIT')
    assert result['report']==report and inventory(out)==before


def test_missing_curated_never_uses_installed_fallback(sources):
    m,data,ready,ccd,out=sources;(data/'ligands/DE.cif').unlink()
    fallback=ccd.parent.parent/'d/data_DE.cif';fallback.parent.mkdir();fallback.write_text(dictionary('DE','C4 S4'))
    with pytest.raises(FileNotFoundError):m.freeze_acquisition_sources(['DE'],out,data_root=data,ready_set_executable=ready)
    assert not out.exists()


@pytest.mark.parametrize('codes',[[],['DE','DE'],['../DE'],['de'],['A1AAZ'],'DE',list(range(17))])
def test_invalid_component_set_refuses_before_discovery(sources,monkeypatch,codes):
    m,data,ready,ccd,out=sources
    monkeypatch.setattr(m,'ligand_source',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Invalid codes reached discovery')))
    with pytest.raises(ValueError):m.freeze_acquisition_sources(codes,out,data_root=data,ready_set_executable=ready)
    assert not out.exists()


@pytest.mark.parametrize('defect',['identity','curated_bond','ambiguous_ccd','unregistered'])
def test_bad_source_batch_never_publishes(sources,monkeypatch,defect):
    m,data,ready,ccd,out=sources
    if defect=='identity':(data/'ligands/ZZZ.cif').write_text(dictionary('XXX'))
    elif defect=='curated_bond':(data/'ligands/DE.cif').write_text(dictionary('DE','N3 S4'))
    elif defect=='ambiguous_ccd':
        other=Path(str(ccd).replace('python3.12','python3.11'));other.parent.mkdir(parents=True);other.write_bytes(ccd.read_bytes())
    else:
        import nasolve.curated_ligands as ligands
        def reject(code):raise ValueError('Unregistered')
        monkeypatch.setattr(ligands,'_registered_record',reject)
    with pytest.raises((ValueError,FileNotFoundError)):m.freeze_acquisition_sources(['DE','ZZZ','YYY'],out,data_root=data,ready_set_executable=ready)
    assert not out.exists()


@pytest.mark.parametrize('defect',['bytes','precedence'])
def test_changed_earlier_selection_is_not_mixed_into_batch(sources,monkeypatch,defect):
    m,data,ready,ccd,out=sources;select=m.ligand_source
    def changed(code,*a,**k):
        result=select(code,*a,**k)
        if code=='ZZZ':
            if defect=='bytes':(data/'ligands/DE.cif').write_text(dictionary('DE','C4 S4')+'# changed\n')
            else:(data/'ligands/YYY.cif').write_bytes(ccd.read_bytes())
        return result
    monkeypatch.setattr(m,'ligand_source',changed)
    with pytest.raises(ValueError,match='selection changed'):m.freeze_acquisition_sources(['DE','YYY','ZZZ'],out,data_root=data,ready_set_executable=ready)
    assert not out.exists()


def test_interrupted_copy_is_preserved_and_never_resumed_in_place(sources,monkeypatch):
    m,data,ready,ccd,out=sources;reference=m._reference
    def interrupted(root,code):raise KeyboardInterrupt('copy interrupted')
    monkeypatch.setattr(m,'_reference',interrupted)
    with pytest.raises(KeyboardInterrupt):m.freeze_acquisition_sources(['DE','ZZZ'],out,data_root=data,ready_set_executable=ready)
    before=inventory(out);assert before and not (out/'source_selection.json').exists()
    monkeypatch.setattr(m,'_reference',reference)
    with pytest.raises(FileExistsError):m.freeze_acquisition_sources(['DE','ZZZ'],out,data_root=data,ready_set_executable=ready)
    assert inventory(out)==before
    from nasolve.campaigns import CampaignError
    with pytest.raises((CampaignError,ValueError)):m.read_acquisition_sources(out)
    m.freeze_acquisition_sources(['DE','ZZZ'],out.with_name('fresh'),data_root=data,ready_set_executable=ready)
    assert inventory(out)==before


@pytest.mark.parametrize('defect',['bytes','authority','path','order','extra_claim','native','boolean','schema_boolean','extra_file','extra_directory','record_temporary','symlink'])
def test_strict_readback_rejects_changed_evidence_and_claims(sources,defect):
    from nasolve.campaign_records import write_record
    m,data,ready,ccd,out=sources;r=m.freeze_acquisition_sources(['DE','YYY','ZZZ'],out,data_root=data,ready_set_executable=ready)
    if defect=='bytes':(out/'sources/DE.cif').write_text(dictionary('DE','C4 S4')+'# changed\n')
    elif defect=='authority':r['sources']['DE'].update(source_authority='NATIVE',source_kind='installed-phenix-ccd')
    elif defect=='path':r['sources']['DE']['artifact']['path']='../data/ligands/DE.cif'
    elif defect=='order':r['components'].reverse()
    elif defect=='extra_claim':r['approved']=True
    elif defect=='native':r['native_validation']='PASS'
    elif defect=='boolean':r['automatic_adoption']=0
    elif defect=='schema_boolean':r['schema_version']=True
    elif defect=='extra_file':(out/'sources/unknown').write_text('extra')
    elif defect=='extra_directory':(out/'sources/unknown').mkdir()
    elif defect=='record_temporary':(out/'.record-unbound').write_text('extra')
    else:
        (out/'sources/DE.cif').unlink();(out/'sources/DE.cif').symlink_to(data/'ligands/DE.cif')
    write_record(out/'source_selection.json',r,replace=True)
    with pytest.raises((ValueError,OSError)):m.read_acquisition_sources(out)


def test_readback_detects_source_change_during_validation(sources,monkeypatch):
    m,data,ready,ccd,out=sources;m.freeze_acquisition_sources(['DE','YYY'],out,data_root=data,ready_set_executable=ready)
    validate=m.validate_ligand_dictionary
    def changed(code,path):
        validate(code,path)
        if code=='YYY':(out/'sources/DE.cif').write_text(dictionary('DE','C4 S4')+'# changed during read\n')
    monkeypatch.setattr(m,'validate_ligand_dictionary',changed)
    with pytest.raises(ValueError):m.read_acquisition_sources(out)


@pytest.mark.parametrize('kind',['existing','symlink_parent'])
def test_unsafe_or_existing_output_does_not_discover(sources,monkeypatch,kind):
    m,data,ready,ccd,out=sources
    if kind=='existing':out.mkdir();(out/'mine').write_text('preserve')
    else:
        link=out.with_name('link');link.symlink_to(data,target_is_directory=True);out=link/'new'
    monkeypatch.setattr(m,'ligand_source',lambda *a,**k:(_ for _ in ()).throw(AssertionError('No discovery')))
    with pytest.raises((ValueError,FileExistsError)):m.freeze_acquisition_sources(['DE'],out,data_root=data)


def test_frozen_source_feeds_component_request_without_live_selection(tmp_path,monkeypatch):
    from nasolve import cif_acquisition_sources as m
    from nasolve import cif_acquisition_attempt as acquisition
    from nasolve import curated_ligands as ligands
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot
    from tests.test_cif_dictionary_sites import inputs
    args=inputs(tmp_path,terminal=False);saved=resolve_dictionary_snapshot(args['snapshot'])
    data=tmp_path/'ordinary';(data/'ligands').mkdir(parents=True);(data/'ligands/ZZZ.cif').write_bytes(saved['source'].read_bytes())
    monkeypatch.setattr(ligands,'_registered_record',lambda code: {'Ligand code':code})
    out=tmp_path/'selection';m.freeze_acquisition_sources(['ZZZ'],out,data_root=data);shutil.rmtree(data)
    def forbidden(*a,**k):raise AssertionError('Frozen cache hit rediscovered or launched')
    monkeypatch.setattr(m,'ligand_source',forbidden);monkeypatch.setattr(acquisition,'execute_candidate_qualification',forbidden);monkeypatch.setattr(acquisition,'generate_source_candidate_attempt',forbidden)
    selected=m.read_acquisition_sources(out)['sources']['ZZZ'];sdk=tmp_path/'unavailable-sdk'
    pin=dict(anchor='phenix_installation',path='api.py',sha256='1'*64,size=6)
    generation=dict(installation_root=sdk,python_executable=sdk/'python',elbow_executable=sdk/'elbow',api_sources=[pin],prior_sources=[pin],expected_dialect='CHEMICAL_COMPONENTS_CIF',phenix_version='TEST',environment={},bond_representation_policy=saved['manifest']['request']['recipe']['bond_representation_policy'])
    result=acquisition.acquire_dictionary_attempt(selected['source'],'ZZZ',tmp_path/'cache',tmp_path/'request',source_authority=selected['source_authority'],consumer=args['consumer'],generation=generation,retained_snapshot=args['snapshot'])
    assert result['acquisition']['status']=='PREPARED_AND_FROZEN'
    again=acquisition.acquire_dictionary_attempt(selected['source'],'ZZZ',tmp_path/'cache',tmp_path/'request',source_authority=selected['source_authority'],consumer=args['consumer'],generation=generation,retained_snapshot=args['snapshot'])
    assert again['acquisition']['status']=='REUSED' and again['attempt_number']==2
    assert acquisition.read_acquisition_result(tmp_path/'request',1)['source'].read_bytes()==saved['source'].read_bytes()
