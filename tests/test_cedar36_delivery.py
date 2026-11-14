"""A failed portable preflight is preserved without claiming native execution."""
from copy import deepcopy
from hashlib import sha256
import json,zipfile
import pytest
from tests.test_cedar35_delivery import stereo_return
from tests.test_cif_geometry_review_probe import write_capsule


def failed_source_dialect_return(tmp_path,monkeypatch):
    m,old=stereo_return(tmp_path,monkeypatch)
    parent=json.loads(old['probe_receipt.json'])
    parent.update(graph_preparations={},component_controls={'PDU':{'policy_status':'PASS'}},
        source_plan={'recovery_codes':['DP'],'blocked':[]},prior_rotation_evidence_recomputed={'directions_passed':96})
    for code in ['DP','PDU']:
        data=('EXPLICIT_FAKE_GRAPH35_'+code).encode();digest=sha256(data).hexdigest()
        old['graph_preview/'+code+'/source.cif']=data
        parent['graph_preparations'][code]={'graph_source_sha256':digest,'source_preserved':True}
    old['component_controls/PDU_control.json']=json.dumps(parent['component_controls']['PDU']).encode()
    old['component_controls/sources/PDU.cif']=b'EXPLICIT_FAKE_PUBLIC_SOURCE'
    old['numerical_recovery_plan.json']=json.dumps(parent['source_plan']).encode()
    old['probe_receipt.json']=json.dumps(parent).encode()
    for n in sorted(n for n in old if n.startswith('padding/'))[:len(old)-1320]:del old[n]
    p=tmp_path/'old.zip';write_capsule(p,old)
    with zipfile.ZipFile(p) as z:e={'inputs/review/'+n:z.read(n) for n in z.namelist()}
    keys=['graph_preparations','component_controls','source_plan','prior_rotation_evidence_recomputed']
    r={k:deepcopy(parent[k]) for k in keys}
    r.update(build={'fixture':'EXPLICIT_FAKE_C35_BUILD'},delivery_prefix='35_Cedar',
        kind='cif-source-graph-numerical-recovery-probe',status='REVIEW',analysis_completed=False,
        requested_action='SOURCE_DIALECT_READER_AUDIT',error='Output parent cannot traverse a symlink',
        automatic_adoption=False,policy_authority='NARestraints',consumer_preparations={},
        original_archive_preserved=True,frozen_inputs_preserved=True,prerequisite_mechanics_replayed=True,
        prior_archive={'sha256':m.CEDAR34_SHA256,'verified_payloads':1320})
    r.update({k:'NOT_RUN' for k in ['native_execution','dictionary_generation','model_editing','model_optimization',
        'native_proxy_validation','linked_site_validation','policy_recompilation','refinement','installed_phenix_edits',
        'readyset_retry','scientific_approval']})
    m.CEDAR35_BUILD_SHA256=sha256(json.dumps(r['build'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    for name in ['graph_preview/DP/source.cif','graph_preview/PDU/source.cif','component_controls/PDU_control.json',
                 'component_controls/sources/PDU.cif','numerical_recovery_plan.json']:e[name]=old[name]
    e['probe_receipt.json']=json.dumps(r).encode()
    return m,e


@pytest.mark.parametrize('defect',['none','build','phase','completed','error','adoption','prior','consumer',
                                  'extra_output','graph','graph_receipt','control','plan','rotation'])
def test_failed_preflight_gate_preserves_scope_graphs_and_nested_native_evidence(tmp_path,monkeypatch,defect):
    m,e=failed_source_dialect_return(tmp_path,monkeypatch);r=json.loads(e['probe_receipt.json'])
    if defect=='build':r['build']['fixture']='CHANGED'
    if defect=='phase':r['native_execution']='SOURCE_READER_DIALECT_CONTROLS'
    if defect=='completed':r['analysis_completed']=True
    if defect=='error':r['error']='UNRELATED_FAILURE'
    if defect=='adoption':r['automatic_adoption']=True
    if defect=='prior':e['inputs/review/padding/001.txt']=b'CHANGED'
    if defect=='consumer':r['consumer_preparations']={'DP':{'status':'COMPLETED'}}
    if defect=='extra_output':e['native_source_reader/result.json']=b'{}'
    if defect=='graph':e['graph_preview/DP/source.cif']=b'CHANGED'
    if defect=='graph_receipt':r['graph_preparations']['DP']['graph_source_sha256']='0'*64
    if defect=='control':e['component_controls/sources/PDU.cif']=b'CHANGED'
    if defect=='plan':r['source_plan']['recovery_codes']=['PDU']
    if defect=='rotation':r['prior_rotation_evidence_recomputed']['directions_passed']=0
    e['probe_receipt.json']=json.dumps(r).encode();p=tmp_path/'review.zip';write_capsule(p,e)
    if defect=='none':
        result=m._read_capsule(p,sha256(p.read_bytes()).hexdigest())
        assert m._source_view(result[0])[1]=='inputs/review/'*6
        reader,prefix=m._source_reader_evidence(result[0])
        assert json.loads(reader['probe_receipt.json'])['delivery_prefix']=='34_Cedar'
        assert prefix=='inputs/review/'
    else:
        with pytest.raises((ValueError,KeyError)):m._read_capsule(p,sha256(p.read_bytes()).hexdigest())
