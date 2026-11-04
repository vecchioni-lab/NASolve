"""One molecule per ReadySet file; caches retain exact parsed numerical values."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,shutil
import pytest
from tests.test_cif_postmr_cached_model import bundle


def installed_registry_fixture(tmp_path,monkeypatch):
    s,c,m,p,consumer=bundle(tmp_path,monkeypatch)
    site=p.root/'lib/python3.11/site-packages';folder=site/'elbow/utilities';folder.mkdir()
    (folder/'__init__.py').write_text('')
    (folder/'ready_set_utils.py').write_text('''from pathlib import Path
import re
def get_user_defined_restraints(filenames):
    result={}
    for filename in filenames:
        ids=set(re.findall(r'(?m)^(Q[0-9][0-9])\\s',Path(filename).read_text()))
        if len(ids)!=1:continue
        result[next(iter(ids))]=Path(filename).read_text()
    return result
''')
    ready=site/'elbow/command_line/ready_set.py';text=ready.read_text()
    text='from elbow.utilities.ready_set_utils import get_user_defined_restraints\n'+text
    text=text.replace("    print('No unknown residues')", "    registered=get_user_defined_restraints([a.split('=',1)[1] for a in args if a.startswith('ready_set.input.cif_file_name=')])\n    for code in ['Q17','Q18']:\n        if code not in registered:builder.run()\n    print('No unknown residues')")
    ready.write_text(text)
    return s,c,m,p,consumer,{'Q17':tmp_path/'candidate/c.cif','Q18':tmp_path/'candidate2.cif'}


def test_individual_files_avoid_combined_container_builder_fallback(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_bundle_consumption,read_readyset_consumption
    s,c,m,p,consumer,paths=installed_registry_fixture(tmp_path,monkeypatch)
    legacy=audit_readyset_bundle_consumption(s,c,m,['Q17','Q18'],p,consumer,tmp_path/'legacy')
    assert legacy['status']=='REVIEW' and legacy['trace']['builder_calls']==2
    fixed=audit_readyset_bundle_consumption(s,c,m,['Q17','Q18'],p,consumer,tmp_path/'fixed',component_dictionaries=paths)
    assert fixed['status']=='READYSET_CACHED_INPUT_PASS' and fixed['trace']['builder_calls']==0
    assert len([a for a in fixed['ordinary_arguments'] if a.startswith('ready_set.input.cif_file_name=')])==2
    assert fixed['checks']['effective_numerics_exact'] and fixed['checks']['unchanged_heavy_sites']
    assert fixed['input_representation']=='ONE_PARAMETERIZED_COMPONENT_PER_PHIL_ARGUMENT'
    for code,ref in fixed['component_inputs'].items():assert (tmp_path/'fixed'/ref['path']).read_bytes()==paths[code].read_bytes()
    shutil.rmtree(p.root);[v.unlink() for v in paths.values()]
    (tmp_path/'fixed').rename(tmp_path/'relocated')
    assert read_readyset_consumption(tmp_path/'relocated')['dictionary'].read_bytes()==c.read_bytes()


@pytest.mark.parametrize('defect',['missing','overlap','unparameterized','changed_numerics','wrong_code'])
def test_individual_inputs_cannot_change_or_omit_a_component(tmp_path,monkeypatch,defect):
    from nasolve.cif_postmr_readyset import audit_readyset_bundle_consumption
    s,c,m,p,consumer,paths=installed_registry_fixture(tmp_path,monkeypatch)
    if defect=='missing':paths.pop('Q18')
    if defect=='overlap':paths['Q18']=c
    if defect=='unparameterized':
        from nasolve.cif_stereochemistry_audit import _values
        from nasolve.cif_linked_preparation import _render
        v=_values(paths['Q17'],'Q17');v.pop('_chem_comp_atom.type_energy')
        graph=tmp_path/'graph.cif';graph.write_text(_render(v,'Q17'));paths['Q17']=graph
    if defect=='changed_numerics':paths['Q18'].write_bytes(paths['Q18'].read_bytes().replace(b'1.5',b'1.9'))
    if defect=='wrong_code':paths['Q17']=paths['Q18']
    with pytest.raises(ValueError):audit_readyset_bundle_consumption(s,c,m,['Q17','Q18'],p,consumer,tmp_path/'out',component_dictionaries=paths)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',['none','unrecorded','digest','anchor','cif','traversal'])
def test_v1_reader_skips_only_explicit_matching_opaque_metadata(tmp_path,defect):
    from nasolve.cif_postmr_cached_model import read_cached_model
    LEGACY_POLICY_ID='cif-postmr-cached-model-readback-v1'
    nested={'anchor':'postmr_readyset_directory','path':'readyset/Q17.pickle','sha256':'a'*64,'size':17}
    ref={**nested,'anchor':'cached_model_directory','path':'readyset_consumption/'+nested['path']}
    report={'policy_id':LEGACY_POLICY_ID,'requires_cif_review':False,'outputs':[ref],
        'readyset':{'excluded_serialized_outputs':[nested]}}
    if defect=='unrecorded':report['readyset']['excluded_serialized_outputs']=[]
    if defect=='digest':nested['sha256']='b'*64
    if defect=='anchor':nested['anchor']='WRONG'
    if defect=='cif':nested['path']='readyset/Q17.cif';ref['path']='readyset_consumption/readyset/Q17.cif'
    if defect=='traversal':nested['path']='../Q17.pickle';ref['path']='readyset_consumption/../Q17.pickle'
    (tmp_path/'cached_model.json').write_text(json.dumps(report));before=(tmp_path/'cached_model.json').read_bytes()
    if defect=='none':assert read_cached_model(tmp_path)==report
    else:
        with pytest.raises((ValueError,FileNotFoundError)):read_cached_model(tmp_path)
    assert (tmp_path/'cached_model.json').read_bytes()==before


@pytest.mark.parametrize('field',['determinant','eigenvalues'])
def test_cached_legacy_derived_notes_allow_only_machine_roundoff(field):
    from nasolve.cif_postmr_cached_model import cached_preparation_replays
    value=0.4023329552414226
    a={'legacy_inspection':{'numerical_issues':[{'measurements':{field:value if field=='determinant' else [value]}}]}}
    b=deepcopy(a);b['legacy_inspection']['numerical_issues'][0]['measurements'][field]=value+1e-16 if field=='determinant' else [value+1e-16]
    assert cached_preparation_replays(a,b)
    b['legacy_inspection']['numerical_issues'][0]['measurements'][field]=value+1e-6 if field=='determinant' else [value+1e-6]
    assert not cached_preparation_replays(a,b)


@pytest.mark.parametrize('field',['target','weight','coordinate','sha256','status','rule','determinant'])
def test_cached_replay_does_not_relax_nonmeasurement_fields(field):
    from nasolve.cif_postmr_cached_model import cached_preparation_replays
    assert not cached_preparation_replays({field:0.4},{field:0.4+1e-16})
    assert not cached_preparation_replays({'numerical_issues':[{field:0.4}]},{'numerical_issues':[{field:0.4+1e-16}]})


@pytest.mark.parametrize('a,b',[(float('inf'),float('inf')),(float('nan'),float('nan')),(0.4,float('nan')),(0.4,0)])
def test_cached_derived_notes_reject_nonfinite_and_changed_types(a,b):
    from nasolve.cif_postmr_cached_model import cached_preparation_replays
    def note(v):return {'numerical_issues':[{'measurements':{'determinant':v}}]}
    assert not cached_preparation_replays(note(a),note(b))
