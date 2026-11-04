"""Source rebinding never turns a component-name match into native approval."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import pytest

from tests.test_cif_dictionary_store import inputs


def prepared(tmp_path, monkeypatch):
    from nasolve.cif_dictionary_store import resolve_qualified_dictionary
    import nasolve.curated_ligands as ligands
    s,c,m,q,o,request,p=inputs(tmp_path)
    resolve_qualified_dictionary(s,'Q17',tmp_path/'old_store',tmp_path/'saved',
        acquire=lambda:dict(candidate=c,qualification=q,provenance=p),**o)
    source=tmp_path/'ordinary.cif';source.write_bytes(s.read_bytes()+b'\n# selected ordinary source\n')
    selected=ligands.LigandDictionarySource('Q17',source,'CURATED','curated')
    monkeypatch.setattr(ligands,'ligand_source',lambda *a,**k:selected)
    monkeypatch.setattr(ligands,'validate_ligand_dictionary',lambda *a:None)
    return s,c,m,q,o,p,source,selected


def call(tmp_path,o,**kwargs):
    from nasolve.cif_source_reuse import resolve_ordinary_dictionary
    return resolve_ordinary_dictionary('Q17',tmp_path/'never_execute',tmp_path/'new_store',tmp_path/'run',
        saved_snapshot=tmp_path/'saved',**{k:v for k,v in o.items() if k!='source_authority'},**kwargs)


def native_qualifier(source,candidate,consumer):
    from nasolve.cif_candidate_usability import qualify_candidate_native
    from tests.test_cif_candidate_usability import native_case
    # The explicit fake native fixture has the exact unchanged candidate; fresh
    # source assessment must still bind the new selected source, not patched q.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        # macOS temporary paths may use /var, a symlink to /private/var.
        # Supply the canonical owned path without relaxing production guards.
        s,c,m,native=native_case(Path(d).resolve())
        assert c.read_bytes()==candidate.read_bytes()
        return qualify_candidate_native(source,candidate,m,'Q17',native)


def test_verified_projection_requalifies_once_then_ordinary_request_reuses(tmp_path,monkeypatch):
    from nasolve.cif_source_reuse import read_ordinary_dictionary
    from nasolve.cif_dictionary_store import lookup_dictionary,make_dictionary_request
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch);calls=[]
    def qualify(*args):calls.append('native');return native_qualifier(*args)
    before=c.read_bytes();old_manifest=(tmp_path/'saved/entry/manifest.json').read_bytes()
    r=call(tmp_path,o,qualify=qualify)
    assert r['status']=='SOURCE_REQUALIFIED_AND_FROZEN' and r['decision']=='CONTINUE_WITH_NOTES'
    assert r['source']['authority']=='CURATED' and r['projection']['status']=='SOURCE_PROJECTION_PASS'
    assert all(r['projection']['checks'].values()) and calls==['native']
    e=read_ordinary_dictionary(tmp_path/'run')
    assert e['dictionary'].read_bytes()==before and e['numerics']['manifest']['request']['source_authority']=='CURATED'
    assert e['numerics']['provenance']['converged'] is False
    assert e['numerics']['provenance']['notes']==p['notes']
    assert e['numerics']['manifest']['request']['generator']==o['generator']
    assert (tmp_path/'saved/entry/manifest.json').read_bytes()==old_manifest
    (tmp_path/'run').rename(tmp_path/'first')
    def forbidden(*args):raise AssertionError('Repeat reuse must not requalify or generate')
    r=call(tmp_path,o,qualify=forbidden)
    assert r['status']=='REUSED' and calls==['native']
    request=make_dictionary_request(source,'Q17',source_authority='CURATED',recipe=o['recipe'],generator=o['generator'])
    assert lookup_dictionary(tmp_path/'new_store',request,o['consumer'])['status']=='HIT'


@pytest.mark.parametrize('change',['charge','order','atom_name','stereo','hydrogen','recipe','backend','source_hand'])
def test_chemical_or_policy_difference_never_calls_native_or_relabels_saved_entry(tmp_path,monkeypatch,change):
    from nasolve.cif_linked_preparation import component_values,_render
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch)
    values=component_values(source,'Q17')
    if change=='charge':values['_chem_comp_atom.charge'][1]='-1'
    if change=='order':
        values['_chem_comp_bond.type'][0]='double';values['_chem_comp_bond.value_order'][0]='DOUB'
    if change=='atom_name':values={k:[('OTHER' if x=='CTR' else x) for x in v] for k,v in values.items()}
    if change=='stereo':values['_chem_comp_atom.pdbx_stereo_config'][0]='S'
    if change=='hydrogen':values['_chem_comp_atom.type_symbol'][1]='H'
    if change=='source_hand':
        for key in values:
            if key.startswith('_chem_comp_atom.') and key.lower().endswith(('.x','_x','_x_ideal')):
                values[key]=[str(-float(x)) for x in values[key]]
    if change=='recipe':o['recipe']['sha256']='8'*64
    if change=='backend':o['generator']['name']='OTHER_BACKEND'
    source.write_text(_render(values,'Q17'))
    def forbidden(*args):raise AssertionError('Incompatible source must be excluded before native evaluation')
    result=call(tmp_path,o,qualify=forbidden)
    assert result['status']=='ORDINARY_SOURCE_FALLBACK' and result['requires_cif_review'] is False
    assert not (tmp_path/'new_store').exists()


@pytest.mark.parametrize('defect',['no_adapter','failed_check','wrong_source','exception','candidate_edit','source_edit','corrupt_snapshot'])
def test_native_failure_or_unbound_evidence_preserves_ordinary_source_fallback(tmp_path,monkeypatch,defect):
    from nasolve.cif_source_reuse import read_ordinary_dictionary
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch)
    def qualify(a,b,consumer):
        if defect=='exception':raise RuntimeError('bounded native readback failed')
        result=native_qualifier(a,b,consumer)
        if defect=='failed_check':result['checks']['exact_active_bonds']=False
        if defect=='wrong_source':result['source_assessment']['finished_stereo']['source_sha256']='0'*64
        if defect=='candidate_edit':b.write_bytes(b.read_bytes()+b'# unexpected edit\n')
        if defect=='source_edit':a.write_bytes(a.read_bytes()+b'# unexpected edit\n')
        return result
    if defect=='corrupt_snapshot':(tmp_path/'saved/entry/dictionary.cif').write_text('DAMAGED')
    before=source.read_bytes()
    result=call(tmp_path,o,qualify=None if defect=='no_adapter' else qualify)
    assert result['status']=='ORDINARY_SOURCE_FALLBACK' and not (tmp_path/'run/numerics').exists()
    assert source.read_bytes()==before
    e=read_ordinary_dictionary(tmp_path/'run');assert e['dictionary'].read_bytes()==before
    assert result['production_adoption']=='NOT_RUN' and result['requires_cif_review'] is False


def test_snapshot_survives_cache_source_and_prior_capsule_loss(tmp_path,monkeypatch):
    from nasolve.cif_source_reuse import read_ordinary_dictionary
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch)
    call(tmp_path,o,qualify=native_qualifier);expected=c.read_bytes()
    for d in ['saved','old_store','new_store']:shutil.rmtree(tmp_path/d)
    s.unlink();c.unlink();source.unlink();(tmp_path/'run').rename(tmp_path/'relocated')
    result=read_ordinary_dictionary(tmp_path/'relocated')
    assert result['dictionary'].read_bytes()==expected and result['numerics']['provenance']['converged'] is False


@pytest.mark.parametrize('defect',['source','projection','entry','selected','path','authority'])
def test_frozen_binding_rejects_tampering(tmp_path,monkeypatch,defect):
    from nasolve.cif_source_reuse import read_ordinary_dictionary
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch)
    call(tmp_path,o,qualify=native_qualifier)
    file=tmp_path/'run/ordinary_dictionary.json';r=json.loads(file.read_text())
    if defect=='source':(tmp_path/'run/source.cif').write_text('DAMAGED')
    if defect=='projection':r['projection']['checks']['bond_orders']=False
    if defect=='entry':(tmp_path/'run/numerics/entry/dictionary.cif').write_text('DAMAGED')
    if defect=='selected':r['selected']='ordinary_source'
    if defect=='path':r['source']['artifact']['path']='../ordinary.cif'
    if defect=='authority':r['source']['authority']='NATIVE'
    file.write_text(json.dumps(r))
    with pytest.raises((ValueError,KeyError)):read_ordinary_dictionary(tmp_path/'run')


def test_missing_curated_source_fails_before_any_cache_or_adapter(tmp_path):
    from nasolve.cif_source_reuse import resolve_ordinary_dictionary
    with pytest.raises(FileNotFoundError,match='Curated dictionary'):
        resolve_ordinary_dictionary('1AP',tmp_path/'none',tmp_path/'store',tmp_path/'run',
            data_root=tmp_path/'missing',recipe={},generator={},consumer={})
    assert not (tmp_path/'run').exists()


def test_consumer_upgrade_requalifies_current_source_without_regenerating(tmp_path,monkeypatch):
    from nasolve.cif_source_reuse import read_ordinary_dictionary
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch)
    call(tmp_path,o,qualify=native_qualifier);old=read_ordinary_dictionary(tmp_path/'run')
    (tmp_path/'run').rename(tmp_path/'before_upgrade')
    o['consumer']['version']='UPGRADED_TEST_CONSUMER';o['generator']['version']='UPGRADED_TEST_PRODUCER'
    r=call(tmp_path,o,qualify=native_qualifier);fresh=read_ordinary_dictionary(tmp_path/'run')
    assert r['native_adapter_calls']==1 and r['status']=='SOURCE_REQUALIFIED_AND_FROZEN'
    assert fresh['dictionary'].read_bytes()==old['dictionary'].read_bytes()
    assert fresh['numerics']['manifest']['consumer']['version']=='UPGRADED_TEST_CONSUMER'
    assert fresh['numerics']['manifest']['request']['generator']['version']=='TEST'


def test_optional_persistent_store_failure_retains_qualified_run_copy(tmp_path,monkeypatch):
    from nasolve.cif_source_reuse import read_ordinary_dictionary
    import nasolve.cif_dictionary_store as store
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch)
    def unavailable(*args,**kwargs):raise OSError('TEST: persistent store unavailable')
    monkeypatch.setattr(store,'publish_dictionary',unavailable)
    r=call(tmp_path,o,qualify=native_qualifier)
    e=read_ordinary_dictionary(tmp_path/'run')
    assert r['selected']=='qualified_dictionary' and e['dictionary'].read_bytes()==c.read_bytes()
    assert e['numerics']['report']['persistent_store']=='UNAVAILABLE'


@pytest.mark.parametrize('existing',['directory','parent_symlink'])
def test_output_collision_and_symlink_parent_are_rejected(tmp_path,monkeypatch,existing):
    s,c,m,q,o,p,source,selected=prepared(tmp_path,monkeypatch)
    if existing=='directory':(tmp_path/'run').mkdir()
    else:
        real=tmp_path/'real';real.mkdir();(tmp_path/'run').symlink_to(real,target_is_directory=True)
    with pytest.raises(ValueError):call(tmp_path,o,qualify=native_qualifier)
