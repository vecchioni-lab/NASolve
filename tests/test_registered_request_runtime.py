"""Request/runtime composition, with existing scientific readers stubbed.

Real frozen construction, source replay and native evidence are exercised by the
separate installed FT qualification. These cases discriminate binding failures.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
from unittest.mock import patch

import pytest


@pytest.fixture
def bound(tmp_path, monkeypatch):
    from nasolve import cif_complete_request as request_owner
    from nasolve import cif_runtime_bundle, cif_component_runtime
    from nasolve import cif_dictionary_bundle, cif_dictionary_sites
    from nasolve import cif_registered_preparation_native, cif_acquisition_sources
    root=tmp_path/'request'; inputs=root/'inputs'; inputs.mkdir(parents=True)
    (inputs/'model.pdb').write_text('exact model'); (inputs/'phils').mkdir()
    phils=[]
    for i in range(2):
        p=inputs/'phils'/f'{i:03}.phil'; p.write_text(f'geometry {i}'); phils.append(p)
    source=inputs/'source.cif'; source.write_text('declared chemistry')
    runtime=tmp_path/'runtime'; runtime.mkdir(); bundle=runtime/'evidence/bundle'; bundle.mkdir(parents=True)
    (bundle/'model.pdb').write_bytes((inputs/'model.pdb').read_bytes())
    for i,p in enumerate(phils): (bundle/f'{i}.phil').write_bytes(p.read_bytes())
    saved_source=bundle/'source.cif'; saved_source.write_bytes(source.read_bytes())
    dictionary_request=dict(component='XYZ',source_authority='CURATED',recipe={'policy':'source-preserving'},generator={'version':'1'})
    config=dict(registered_backbone={'policy':'registered'},construction_inputs={'path':'inputs/construction'},
        explicit_na_policy={'path':'inputs/explicit_na'},components={'XYZ':dict(dictionary_request=dictionary_request)},
        controls=dict(consumer={'version':'1'},native_context={'policy':'context'},expected_links=[['A:1','A:2']],
            supplementary_phils=['phils/000.phil','phils/001.phil'],
            sites={'XYZ':dict(contexts=[{'site':'A:2'}],phosphate_atom_policy=None,retained=None,terminal_resource=None)}))
    request=dict(configuration=config,record_sha256='request-record')
    request_path=root/'request.json'; request_path.write_text(json.dumps(request))
    state=dict(state='RECORDED',availability='BLOCKED',attempts=[],request=request)
    manifest=dict(policy_id=cif_component_runtime.ORIGINAL_POLICY_ID,source_selection={'bundle':'evidence/bundle'},decision={'selected':'verified_prepared_bundle'})
    mp=runtime/'runtime_bundle.json';mp.write_text(json.dumps(manifest))
    report=dict(components=['XYZ'],consumer=config['controls']['consumer'],native_context=config['controls']['native_context'],
        expected_links=config['controls']['expected_links'],supplementary_phils=['0.phil','1.phil'])
    site=dict(report=dict(contexts=[{'site':'A:2'}],terminal_resource=None),
        snapshot=dict(source=saved_source,manifest=dict(request=deepcopy(dictionary_request),consumer=config['controls']['consumer']),entry_id='selected-entry'))
    calls=[]
    def inspect(path):
        assert path==root; calls.append('request'); return deepcopy(state)
    def resolve(path):
        assert path==runtime; calls.append('resolve');return dict(manifest_path=mp,manifest=deepcopy(manifest))
    def native(*args,**kwargs):
        calls.append('native');return dict(runtime=dict(anchor='runtime_directory',path=mp.name,sha256=sha256(mp.read_bytes()).hexdigest()),ordinary_admission=False)
    @contextmanager
    def evidence(path,value,*,subtree):
        assert path==runtime and subtree=='bundle';calls.append('open');yield runtime;calls.append('close')
    monkeypatch.setattr(request_owner,'inspect_dictionary_request',inspect)
    monkeypatch.setattr(cif_runtime_bundle,'resolve_runtime_bundle',resolve)
    monkeypatch.setattr(cif_registered_preparation_native,'_review_original_selection',native,raising=False)
    monkeypatch.setattr(cif_component_runtime,'component_runtime_evidence',evidence)
    monkeypatch.setattr(cif_component_runtime,'verify_component_runtime_resources',lambda *a:calls.append('verify'))
    monkeypatch.setattr(cif_dictionary_bundle,'read_dictionary_bundle',lambda p:dict(report=deepcopy(report),model=bundle/'model.pdb'))
    monkeypatch.setattr(cif_dictionary_sites,'read_dictionary_sites',lambda p:deepcopy(site))
    monkeypatch.setattr(cif_acquisition_sources,'read_acquisition_sources',lambda p:dict(sources={'XYZ':dict(source=source)}))
    return root,runtime,state,report,site,calls,bundle


def test_original_runtime_binds_frozen_construction_without_execution(bound):
    from nasolve.cif_registered_request_review import review_registered_request_runtime
    root,runtime,state,report,site,calls,bundle=bound
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        result=review_registered_request_runtime(root,runtime=runtime)
    assert result['status']=='REGISTERED_REQUEST_RUNTIME_BOUND_FOR_REVIEW'
    assert result['construction_inputs']==state['request']['configuration']['construction_inputs']
    assert result['request']['anchor']=='dictionary_request_directory'
    assert result['entries']=={'XYZ':'selected-entry'}
    assert result['ordinary_admission'] is False and result['execution_ancestry']=='SEPARATE_DIAGNOSTIC'
    assert calls==['request','resolve','native','open','close','verify','request']
    assert str(root) not in json.dumps(result) and str(runtime) not in json.dumps(result)


@pytest.mark.parametrize('defect',['source','recipe','consumer','model','phils','context','phosphate','components','links'])
def test_independently_valid_but_different_bundle_refuses(bound,defect):
    from nasolve.cif_registered_request_review import review_registered_request_runtime
    root,runtime,state,r,s,calls,b=bound
    if defect=='source':s['snapshot']['source'].write_text('different source chemistry')
    if defect=='recipe':s['snapshot']['manifest']['request']['recipe']['policy']='different'
    if defect=='consumer':s['snapshot']['manifest']['consumer']={'version':'2'}
    if defect=='model':(b/'model.pdb').write_text('other coordinates')
    if defect=='phils':r['supplementary_phils'].reverse()
    if defect=='context':s['report']['contexts']=[{'site':'B:2'}]
    if defect=='phosphate':s['report']['phosphate_atom_policy']='another policy'
    if defect=='components':r['components']=['ABC']
    if defect=='links':r['expected_links']=[['B:1','B:2']]
    with pytest.raises(ValueError):review_registered_request_runtime(root,runtime=runtime)


@pytest.mark.parametrize('defect',['construction','compiler','registered','retained','terminal','furanose','planes','controls','attempt'])
def test_missing_ancestry_or_unqualified_scope_refuses_before_runtime(bound,defect):
    from nasolve.cif_registered_request_review import review_registered_request_runtime
    root,runtime,state,r,s,calls,b=bound;c=state['request']['configuration'];site=c['controls']['sites']['XYZ']
    if defect=='construction':c.pop('construction_inputs')
    if defect=='compiler':c.pop('explicit_na_policy')
    if defect=='registered':c.pop('registered_backbone')
    if defect=='retained':site['retained']='retained/XYZ'
    if defect=='terminal':site['terminal_resource']='terminal'
    if defect=='furanose':site['furanose_reaction']={}
    if defect=='planes':c['plane_support']={}
    if defect=='controls':c['controls']['interpretation_controls']={}
    if defect=='attempt':state['attempts']=[{'number':1}]
    with pytest.raises(ValueError):review_registered_request_runtime(root,runtime=runtime)
    assert calls==['request']


def test_request_mutating_during_evidence_review_refuses(bound,monkeypatch):
    from nasolve.cif_registered_request_review import review_registered_request_runtime
    root,runtime,state,r,s,calls,b=bound
    def mutate(*args):
        p=root/'request.json';p.write_bytes(p.read_bytes()+b'\n')
    monkeypatch.setattr('nasolve.cif_component_runtime.verify_component_runtime_resources',mutate)
    with pytest.raises(ValueError,match='changed'):review_registered_request_runtime(root,runtime=runtime)


def test_request_owner_refusal_propagates(bound,monkeypatch):
    from nasolve.cif_registered_request_review import review_registered_request_runtime
    root,runtime,state,r,s,calls,b=bound
    def refuse(*args):raise ValueError('Construction producer mismatches')
    monkeypatch.setattr('nasolve.cif_complete_request.inspect_dictionary_request',refuse)
    with pytest.raises(ValueError,match='producer'):review_registered_request_runtime(root,runtime=runtime)
    assert not calls
