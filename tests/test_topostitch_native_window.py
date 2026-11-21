"""A native window reports observed support, never permission to deform."""
from hashlib import sha256
import json
from types import SimpleNamespace
import shutil
from unittest.mock import patch

import pytest
from nasolve import checkpoints

FAMILIES=('bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity')

@pytest.fixture
def window(tmp_path):
    run=tmp_path/'dataset/AutoMR/run_001';run.mkdir(parents=True)
    def write(p,value):
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(value if isinstance(value,bytes) else json.dumps(value).encode());return p
    lines=[]
    for i in range(6):
        lines.append(f'ATOM  {i+1:5d}  P    DA A{i+1:4d}    {i*2.:8.3f}{0.:8.3f}{0.:8.3f}{1.:6.2f}{20.:6.2f}           P  ')
    payload=('\n'.join(lines)+'\nEND\n').encode()
    model=write(run/'PostMR/model.pdb',payload);obs=write(run/'data.mtz',b'observed')
    parent=dict(id='postmr',kind='postmr',usable=True,model=checkpoints._file_reference(model,run),observations=checkpoints._file_reference(obs,run),phases=None,restraints=[])
    write(run/'report.json',dict(postmr={}))
    write(checkpoints.registry_path(run),dict(schema_version=2,current='postmr',checkpoints=[parent]))
    atoms=[dict(i_seq=i,label=f'atom-{i}',atom_id='P',identity=dict(model_id='',chain_id='A',resseq=str(i+1),icode='',resname='DA',altloc=''),element='P',xyz=[i*2.,0.,0.],occupancy=1.) for i in range(6)]
    def proxy(ids,**kw):return dict(i_seqs=ids,atoms=[atoms[i]['label'] for i in ids],weight=100.,**kw)
    details={k:[] for k in FAMILIES}
    details['bond_simple']=[proxy([0,1]),proxy([0,1]),proxy([1,2]),proxy([1,2]),proxy([2,3]),proxy([4,5])]
    details['parallelity']=[proxy([0,1,2],j_seqs=[3,4,5],j_atoms=[atoms[i]['label'] for i in [3,4,5]],target_angle_deg=0.)]
    native=dict(status='REVIEW',atoms=atoms,atom_count=6,geometry=dict(status='RECORDED',proxy_details=details,proxy_counts={k:len(v) for k,v in details.items()},proxy_count_status={k:'RECORDED' for k in FAMILIES if not k.startswith('bond_')},custom_proxy_requests=[]))
    capture=tmp_path/'capture';receipt=write(capture/'native_receipt.json',dict(status='REVIEW',phenix_version='synthetic-only',inputs=[dict(role='model',sha256=sha256(payload).hexdigest(),size=len(payload),input_index=0,path='inputs/model.pdb')]))
    captured=write(capture/'native_validation.json',native)
    state=dict(run=run,model=model,receipt=receipt,native=native,captured=captured)
    def prep_reader(path):return path,json.loads(checkpoints.registry_path(path).read_text()),None
    def capture_reader(path,model_bytes):
        assert model_bytes==state['model'].read_bytes()
        r=json.loads(path.read_text());n=json.loads(state['captured'].read_text())
        return r,n,{path:path.read_bytes(),state['captured']:state['captured'].read_bytes()}
    def atom_reader(n,payload):
        return [(f"A:{a['identity']['resseq']}",'DA','P') for a in n['atoms']],[a['label'] for a in n['atoms']]
    def identities(n):return {a['i_seq']:a for a in n['atoms']},{a['i_seq']:('A',a['identity']['resseq'],'DA','P') for a in n['atoms']}
    def endpoints(row,atoms,ids):
        indices=row['i_seqs']+row.get('j_seqs',[])
        assert row['atoms']==[atoms[i]['label'] for i in row['i_seqs']]
        return indices,dict(atoms=[ids[i] for i in row['i_seqs']],**(dict(j_atoms=[ids[i] for i in row['j_seqs']]) if 'j_seqs' in row else {}))
    state.update(preparation_reader=prep_reader,native_owners=(SimpleNamespace(_capture=capture_reader,_native_atoms=atom_reader),SimpleNamespace(_native_atom_identities=identities,_bound_proxy_endpoints=endpoints),SimpleNamespace(review_full_monomers=lambda n:dict(status='RECORDED',atom_count=len(n['atoms']),residue_count=6))))
    return state


def load(s,**kw):
    from nasolve.topostitch_preparation import inspect_checkpoint_native_window
    opts=dict(expected_checkpoint_id='postmr',expected_model_sha256=sha256(s['model'].read_bytes()).hexdigest(),native_receipt=s['receipt'],expected_native_receipt_sha256=sha256(s['receipt'].read_bytes()).hexdigest(),selected_indices=[1,2],preparation_reader=s['preparation_reader'],native_owners=s['native_owners'])
    return inspect_checkpoint_native_window(s['run'],**dict(opts,**kw))


def update(s):s['captured'].write_text(json.dumps(s['native']))


def test_partition_keeps_crossing_names_multiplicity_and_no_authority(window):
    before={p:p.read_bytes() for p in window['run'].rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No execution')):r=load(window)
    assert r['families']['bond_simple']['counts']==dict(selected=2,boundary=3,fixed=1,total=6)
    assert r['families']['parallelity']['counts']==dict(selected=0,boundary=1,fixed=0,total=1)
    assert len(r['boundary_terms'])==4
    assert r['boundary_terms'][0]['named_endpoints']==r['boundary_terms'][1]['named_endpoints']
    assert [t['ordinal'] for t in r['boundary_terms'][:2]]==[0,1]
    assert r['boundary_terms'][0]['named_endpoints']['atoms']==[['A','1','DA','P'],['A','2','DA','P']]
    assert r['window']['selected_input_indices']==[1,2] and r['window']['fixed_atom_count']==4
    assert r['source_intent']['inherited_restraint_file_count']==0
    assert r['source_intent']['interaction_absence']=='NOT_ESTABLISHED'
    assert not r['motion_admission'] and not r['chemical_admission'] and not r['scientific_acceptance']
    assert all(p.read_bytes()==v for p,v in before.items())
    assert str(window['run']) not in json.dumps(r) and str(window['receipt'].parent) not in json.dumps(r)


@pytest.mark.parametrize('indices',[[],[True],[1,1],[-1],[6],[2,1],[1.0],None])
def test_invalid_or_ambiguous_window_refuses(window,indices):
    with pytest.raises(ValueError,match='indices'):load(window,selected_indices=indices)


def test_reordered_native_atoms_still_bind_input_window(window):
    r=load(window);n=window['native'];n['atoms'].reverse()
    for i,a in enumerate(n['atoms']):a['i_seq']=i
    for rows in n['geometry']['proxy_details'].values():
        for row in rows:
            row['i_seqs']=[5-i for i in row['i_seqs']]
            if 'j_seqs' in row:row['j_seqs']=[5-i for i in row['j_seqs']]
    update(window);other=load(window)
    assert other['families']==r['families']
    assert other['window']['selected_native_indices']==[3,4]
    assert other['boundary_terms'][0]['named_endpoints']==r['boundary_terms'][0]['named_endpoints']


@pytest.mark.parametrize('fault',['receipt_pin','parent_pin','context_pin','count','missing_family','monomers','native_failure'])
def test_unbound_or_incomplete_evidence_refuses(window,fault):
    kw={}
    if fault=='receipt_pin':kw['expected_native_receipt_sha256']='0'*64
    elif fault=='parent_pin':kw['expected_model_sha256']='0'*64
    elif fault=='context_pin':kw['expected_context_sha256']='0'*64
    elif fault=='count':window['native']['geometry']['proxy_counts']['bond_simple']+=1;update(window)
    elif fault=='missing_family':window['native']['geometry']['proxy_details'].pop('angle');update(window)
    elif fault=='native_failure':window['native']['status']='FAILED';update(window)
    else:
        owners=list(window['native_owners']);owners[2]=SimpleNamespace(review_full_monomers=lambda n:(_ for _ in ()).throw(ValueError('missing monomers')));kw['native_owners']=owners
    with pytest.raises(ValueError):load(window,**kw)


def test_unavailable_family_is_not_reported_as_zero(window):
    g=window['native']['geometry'];g['proxy_details']['const_dihedral']=None;g['proxy_counts']['const_dihedral']=None;g['proxy_count_status']['const_dihedral']='UNSUPPORTED';update(window)
    r=load(window)
    assert r['families']['const_dihedral']==dict(status='UNAVAILABLE',counts=None)
    assert r['coverage']=='PARTIAL_NATIVE_FAMILIES'


@pytest.mark.parametrize('changed',['capture','model','report','registry'])
def test_drift_during_capture_read_refuses(window,changed):
    old=window['native_owners'][0]._capture
    def reader(p,b):
        value=old(p,b)
        path={'capture':window['captured'],'model':window['model'],'report':window['run']/'report.json','registry':checkpoints.registry_path(window['run'])}[changed]
        path.write_bytes(path.read_bytes()+b'\n');return value
    window['native_owners'][0]._capture=reader
    with pytest.raises(ValueError):load(window)


def test_inherited_restraint_must_be_in_capture_and_duplicates_are_not_collapsed(window):
    p=window['run']/'pair.phil';p.write_bytes(b'original intent')
    rp=checkpoints.registry_path(window['run']);r=json.loads(rp.read_text());r['checkpoints'][0]['restraints']=[checkpoints._file_reference(p,window['run'])]*2;rp.write_text(json.dumps(r))
    receipt=json.loads(window['receipt'].read_text());ref=dict(role='phil',sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,input_index=1,path='inputs/first.phil');receipt['inputs'].append(ref);window['receipt'].write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='inherited'):load(window)
    receipt['inputs'].append(dict(ref,input_index=2,path='inputs/second.phil'));window['receipt'].write_text(json.dumps(receipt))
    assert load(window)['source_intent']['inherited_restraint_file_count']==2


def test_relocation_preserves_report_after_original_paths_are_gone(window,tmp_path):
    before=load(window);old=window['run'];target=tmp_path/'relocated/AutoMR/run_001';target.parent.mkdir(parents=True);shutil.move(old,target)
    window['run']=target;window['model']=target/window['model'].relative_to(old)
    old_capture=window['receipt'].parent;new_capture=tmp_path/'moved-capture';shutil.move(old_capture,new_capture)
    window['receipt']=new_capture/window['receipt'].name;window['captured']=new_capture/window['captured'].name
    assert not old.exists() and not old_capture.exists() and load(window)==before


def test_default_missing_native_owners_is_explicit(window):
    from importlib.util import find_spec
    if find_spec('nasolve.cif_attachment_native') is not None:pytest.skip('Cedar native readers installed')
    with pytest.raises(RuntimeError,match='Cedar'):load(window,native_owners=None)


@pytest.fixture
def ordinary(window):
    s=window
    report=dict(post_mr_plan={'allow_op3_sites':[]},postmr={'prepared_sha256':sha256(s['model'].read_bytes()).hexdigest()})
    (s['run']/'report.json').write_text(json.dumps(report))
    calls=[]
    def derive(model,frozen,components):
        calls.append((model,frozen,components))
        return dict(schema_version=1,policy_id='cif-prepared-model-context-v1',
            model_sha256=sha256(model.read_bytes()).hexdigest(),components=components,
            intent={'post_mr_plan':frozen['post_mr_plan']},contexts={},expected_links=[],
            phosphate_audit={'synthetic_fixture':True},scientific_qualification='NOT_ASSESSED')
    s['ordinary_owner']=SimpleNamespace(POLICY_ID='cif-prepared-model-context-v1',derive_prepared_model_context=derive)
    s['ordinary_calls']=calls
    return s


def test_opted_source_context_is_derived_separately_from_checked_authority(ordinary):
    before=load(ordinary)
    r=load(ordinary,ordinary_model_context_owner=ordinary['ordinary_owner'])
    p=r['preparation'];d=p['derived_source_context']
    assert p['status']=='NO_CHECKED_PREPARATION'
    assert all(v['status']=='UNAVAILABLE' for v in p['availability'].values())
    assert d['status']=='DERIVED_ORDINARY_BACKBONE_CONTEXT'
    assert d['pair_or_stack_assignments']=='NOT_INFERRED'
    assert d['model_context']['components']==['DA']
    assert d['model_context']['model_sha256']==p['context']['source_model_sha256']
    assert p['context_sha256']!=before['preparation']['context_sha256']
    assert len(ordinary['ordinary_calls'])==2
    assert load(ordinary)==before
    assert not p['chemical_admission'] and not p['motion_admission']


@pytest.mark.parametrize('fault',['frozen_parent','noncanonical','owner_policy','returned_model','returned_components','claim_acceptance','missing_plan'])
def test_source_context_cannot_invent_or_promote_frozen_intent(ordinary,fault):
    s=ordinary;owner=s['ordinary_owner'];rp=s['run']/'report.json';report=json.loads(rp.read_text())
    if fault=='frozen_parent':report['postmr']['prepared_sha256']='0'*64
    elif fault=='missing_plan':report.pop('post_mr_plan')
    elif fault=='noncanonical':
        p=s['model'];p.write_bytes(p.read_bytes().replace(b' DA ',b'PDU '))
        cp=checkpoints.registry_path(s['run']);r=json.loads(cp.read_text());r['checkpoints'][0]['model']=checkpoints._file_reference(p,s['run']);cp.write_text(json.dumps(r));report['postmr']['prepared_sha256']=sha256(p.read_bytes()).hexdigest()
    elif fault=='owner_policy':owner.POLICY_ID='other'
    else:
        derive=owner.derive_prepared_model_context
        def changed(*args):
            r=derive(*args)
            if fault=='returned_model':r['model_sha256']='0'*64
            elif fault=='returned_components':r['components']=['DT']
            else:r['scientific_qualification']='APPROVED'
            return r
        owner.derive_prepared_model_context=changed
    rp.write_text(json.dumps(report))
    with pytest.raises(ValueError):load(s,ordinary_model_context_owner=owner)


def test_ordinary_context_rejects_a_previous_nonopted_context_pin(ordinary):
    old=load(ordinary)['preparation']['context_sha256']
    with pytest.raises(ValueError,match='context changed'):
        load(ordinary,ordinary_model_context_owner=ordinary['ordinary_owner'],expected_context_sha256=old)


def test_ordinary_derivation_propagates_auditor_refusal_without_fallback(ordinary):
    def refuse(*a):raise ValueError('unexplained phosphate contact')
    ordinary['ordinary_owner'].derive_prepared_model_context=refuse
    with pytest.raises(ValueError,match='unexplained phosphate'):
        load(ordinary,ordinary_model_context_owner=ordinary['ordinary_owner'])


def test_original_report_change_during_context_derivation_refuses(ordinary):
    old=ordinary['ordinary_owner'].derive_prepared_model_context
    def changed(*a):
        r=old(*a);p=ordinary['run']/'report.json';p.write_bytes(p.read_bytes()+b'\n');return r
    ordinary['ordinary_owner'].derive_prepared_model_context=changed
    with pytest.raises(ValueError,match='changed'):
        load(ordinary,ordinary_model_context_owner=ordinary['ordinary_owner'])
