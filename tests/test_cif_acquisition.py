from pathlib import Path
from hashlib import sha256
import shutil
import pytest

ROOT=Path(__file__).parents[1]


def installation(tmp_path):
    exe=tmp_path/'phenix/bin/phenix.ready_set';exe.parent.mkdir(parents=True);exe.write_text('NEVER EXECUTE')
    for code in ['PDU','5PC']:
        path=exe.parent.parent/'lib/python3.11/site-packages/chem_data/chemical_components'/code[0].lower()/('data_'+code+'.cif')
        path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'tests/fixtures/public_ccd'/f'{code}.cif',path)
    return exe


def test_source_api_is_the_same_priority_path_used_by_ordinary_dictionary_lookup(tmp_path):
    from nasolve.curated_ligands import ligand_source,ligand_dictionary
    exe=installation(tmp_path)
    for code,authority in [('DP','CURATED'),('1AP','CURATED'),('DE','CURATED'),('PDU','NATIVE'),('5PC','NATIVE')]:
        row=ligand_source(code,ready_set_executable=exe)
        assert row.path==ligand_dictionary(code,ready_set_executable=exe)
        assert row.authority==authority and row.code==code


def test_missing_curated_source_never_uses_installed_or_cached_alternative(tmp_path):
    from nasolve.curated_ligands import ligand_source
    exe=installation(tmp_path)
    with pytest.raises(FileNotFoundError,match='Curated dictionary'):
        ligand_source('1AP',tmp_path/'missing',ready_set_executable=exe)


@pytest.mark.parametrize('defect',['none','another_component','duplicate_metadata','contradictory_atoms'])
def test_generic_identity_supports_native_loop_headers_without_ambiguous_definitions(tmp_path,defect):
    from nasolve.curated_ligands import validate_ligand_dictionary
    text=(ROOT/'src/nasolve/data/ligands/1AP.cif').read_text().replace('1AP','Q17')
    if defect=='another_component':text=text.replace('Q17','ALT')
    if defect=='duplicate_metadata':text+='\ndata_duplicate\n_chem_comp.id Q17\n'
    if defect=='contradictory_atoms':text+='\ndata_contradictory\n_chem_comp_atom.comp_id ALT\n'
    path=tmp_path/'dictionary.cif';path.write_text(text)
    if defect=='none':validate_ligand_dictionary('Q17',path)
    else:
        with pytest.raises(ValueError):validate_ligand_dictionary('Q17',path)


def test_explicit_local_source_precedes_installed_source(tmp_path):
    from nasolve.curated_ligands import ligand_source
    exe=installation(tmp_path);data=tmp_path/'data';(data/'ligands').mkdir(parents=True)
    source=data/'ligands/PDU.cif';shutil.copyfile(ROOT/'tests/fixtures/public_ccd/PDU.cif',source)
    result=ligand_source('PDU',data,ready_set_executable=exe)
    assert result.path==source and result.authority=='EXPLICIT'


def test_acquisition_controls_freeze_real_sources_and_compile_declared_pairs(tmp_path):
    from nasolve.cif_acquisition import audit_ordinary_acquisition
    exe=installation(tmp_path)
    result=audit_ordinary_acquisition(exe,tmp_path/'audit',pairs=[('PDU','DA'),('5PC','DG')])
    # Missing canonical sources remain explicit; no unrelated source is substituted.
    assert result['status']=='REVIEW'


def test_full_pair_plan_has_exact_eight_user_pairs_and_no_atl():
    from nasolve.cif_acquisition import REQUESTED_PAIRS
    assert REQUESTED_PAIRS==(('CGY','DX'),('1AP','DT'),('DZ','DP'),('IGU','IMC'),('PDU','DA'),('5PC','DG'),('5CM','S6G'),('DF','DA'))


def test_compiler_positive_source_freeze_and_relative_artifacts(tmp_path):
    from nasolve.cif_acquisition import audit_ordinary_acquisition
    exe=installation(tmp_path)
    # An explicitly artificial DA-labelled adenine-role graph is sufficient for
    # source/role wiring. This fixture is not native or chemical qualification.
    path=exe.parent.parent/'lib/python3.11/site-packages/chem_data/chemical_components/d/data_DA.cif'
    path.parent.mkdir(parents=True);path.write_text((ROOT/'src/nasolve/data/ligands/1AP.cif').read_text().replace('1AP','DA'))
    r=audit_ordinary_acquisition(exe,tmp_path/'audit',pairs=[('PDU','DA')])
    assert r['status']=='ORDINARY_ACQUISITION_CONTROLS_PASS'
    pair=r['declared_pairs'][0];assert pair['recipe']=='AT' and len(pair['stack_phils'])==2
    for ref in [pair['pair_phil'],*pair['stack_phils'],*(v['source'] for v in r['sources'].values())]:
        assert ref['anchor']=='acquisition_directory'
        data=(tmp_path/'audit'/ref['path']).read_bytes()
        assert len(data)==ref['size'] and sha256(data).hexdigest()==ref['sha256']
    assert r['native_execution']==r['production_adoption']=='NOT_RUN'
    assert r['requires_cif_review'] is False


@pytest.mark.parametrize('change',['none','source_bytes','authority','wrong_code','corrupt_snapshot'])
def test_ordinary_source_guard_never_adopts_same_code_repair(tmp_path,change):
    from tests.test_cif_dictionary_store import inputs
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary
    from nasolve.cif_acquisition import saved_repair_applicability
    s,c,m,q,o,request,p=inputs(tmp_path)
    resolve_qualified_dictionary(s,'Q17',tmp_path/'store',tmp_path/'snapshot',
        acquire=lambda:dict(candidate=c,qualification=q,provenance=p),**o)
    original=c.read_bytes();authority=o['source_authority'];code='Q17'
    if change=='source_bytes':s.write_text(s.read_text()+'# another authoritative source\n')
    if change=='authority':authority='CURATED'
    if change=='wrong_code':code='ALT'
    if change=='corrupt_snapshot':(tmp_path/'snapshot/entry/dictionary.cif').write_text('CORRUPT')
    if change in {'wrong_code','corrupt_snapshot'}:
        with pytest.raises(ValueError):saved_repair_applicability(s,code,authority,tmp_path/'snapshot',tmp_path/'store')
    else:
        r=saved_repair_applicability(s,code,authority,tmp_path/'snapshot',tmp_path/'store')
        assert r['source_and_authority_exact']==(change=='none')
        assert r['lookup_status']==('HIT' if change=='none' else 'MISS')
        assert r['candidate_selected'] is False and r['original_converged'] is False
        assert r['original_notes']==p['notes'] and c.read_bytes()==original


@pytest.mark.parametrize('pairs',[[('PDU','PDU')],[('PDU','../X')],[('PDU','DA')]*9,[]])
def test_scope_is_bounded_and_validated_before_output(tmp_path,pairs):
    from nasolve.cif_acquisition import audit_ordinary_acquisition
    with pytest.raises(ValueError):audit_ordinary_acquisition(tmp_path/'unused',tmp_path/'audit',pairs=pairs)
    assert not (tmp_path/'audit').exists()
