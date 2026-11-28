"""Returned missing-mononer evidence must not become a qualified native case."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
import pytest


def template():
    p=Path(__file__).resolve().parents[1]/'scripts/cif_numerical_recovery_probe_template.py'
    spec=importlib.util.spec_from_file_location('cedar39_template',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


@pytest.mark.parametrize('label',['installed_lookup','saved_candidate'])
@pytest.mark.parametrize('defect',['none','worker','source','roles','scope','adoption','secondary_structure','receipt','invented_pass','membership','directory'])
def test_captured_native_boundary_retains_failed_lookup_and_saved_candidate_reviews(tmp_path,label,defect):
    m=template();pre='triple_controls/native/PDU/'+label+'/FAKE';members={
        'triple_controls/models/PDU/source_seed.pdb':b'FAKE FIXED SEED',
        'triple_controls/policies/PDU/isolated_component.phil':b'FAKE SS DISABLED'}
    report={'fixture':'EXPLICIT_FAKE_NATIVE_REPORT','status':'REVIEW' if label=='saved_candidate' else 'FAILED',
        'restraint_policy':{'secondary_structure_enabled':False}}
    rr={'status':report['status'],'native_validation':report,'source_preserved':True,'frozen_inputs_preserved':True,
        'automatic_adoption':False,'execution':{'status':'COMPLETED' if label=='saved_candidate' else 'FAILED','returncode':0 if label=='saved_candidate' else 2},
        'dictionary_source_policy':'EXPLICIT_DICTIONARIES' if label=='saved_candidate' else 'INSTALLED_LIBRARY_ONLY',
        'error':'Number of atoms with unknown nonbonded energy type symbols: 38',
        'inputs':[],'outputs':[],**{k:'NOT_RUN' for k in ['optimization','model_editing','readyset_retry','scientific_approval']}}
    def artifact(name,data,role=None):
        members[pre+'/'+name]=data;r={'anchor':'native_directory','path':name,'sha256':sha256(data).hexdigest(),'size':len(data)}
        if role:r['role']=role;rr['inputs'].append(r)
        else:rr['outputs'].append(r)
    artifact('inputs/model.pdb',members['triple_controls/models/PDU/source_seed.pdb'],'model')
    artifact('inputs/policy.phil',members['triple_controls/policies/PDU/isolated_component.phil'],'phil')
    if label=='saved_candidate':
        data=b'FAKE SAVED DICTIONARY';m.CEDAR33_PDU_CANDIDATE_SHA256=sha256(data).hexdigest();artifact('inputs/candidate.cif',data,'dictionary')
    worker=b'raise RuntimeError("CAPTURED WORKER MUST NOT RUN")\n';m.CEDAR38_NATIVE_WORKER_SHA256=sha256(worker).hexdigest()
    artifact('native_worker.py',worker);artifact('native_validation.json',json.dumps(report).encode())
    screen={'status':'REVIEW','target_screen':'PASS','coordinate_screen':'PASS','linear_axis_torsions':[{'fixture':'FAKE'}]*6} if label=='saved_candidate' else {'status':'NOT_RUN'}
    row={'directory':{'anchor':'triple_control_directory','path':pre.removeprefix('triple_controls/')},'interpretation':rr,'triple_screen':screen}
    if defect=='worker':members[pre+'/native_worker.py']=b'CHANGED'
    if defect=='source':
        r=rr['inputs'][0];data=b'ALTERED SEED';members[pre+'/'+r['path']]=data;r.update(size=len(data),sha256=sha256(data).hexdigest())
    if defect=='roles':rr['inputs'][0]['role']='dictionary'
    if defect=='scope':rr['optimization']='COMPLETED'
    if defect=='adoption':rr['automatic_adoption']=True
    if defect=='secondary_structure':report['restraint_policy']['secondary_structure_enabled']=True
    if defect=='invented_pass':rr['status']='PASS'
    if defect=='membership':screen['status']='PASS'
    if defect=='directory':row['directory']['path']='../outside'
    members[pre+'/native_validation.json']=json.dumps(report).encode()
    # Keep the explicit output checksum consistent when changing metadata;
    # semantic gates must still reject the changed scope/result.
    for r in rr['outputs']:
        if r['path']=='native_validation.json':r.update(size=len(members[pre+'/'+r['path']]),sha256=sha256(members[pre+'/'+r['path']]).hexdigest())
    members[pre+'/native_receipt.json']=json.dumps(rr).encode()
    if defect=='receipt':members[pre+'/native_receipt.json']=b'{}'
    if defect=='none':m._check_captured_triple_case(members,'PDU',label,row)
    else:
        with pytest.raises((ValueError,KeyError)):m._check_captured_triple_case(members,'PDU',label,row)


def test_numeric_replay_tolerance_does_not_hide_state_or_material_target_changes():
    m=template();a={'target':180.,'count':1,'adopt':False}
    assert m._evidence_equal(a,{**a,'target':180.+1e-10})
    for changed in [{'target':179.9},{'count':2},{'count':1.0},{'adopt':0},{'target':float('nan')}]:
        assert not m._evidence_equal(a,{**a,**changed})
