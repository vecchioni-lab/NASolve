"""Registered original-runtime composition; scientific owners have separate tests.

Here the runtime resolver and native scientific owner are stubbed explicitly.
The real newly constructed FT runtime and compact archive are checked separately.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,shutil,tempfile
from unittest.mock import patch
import pytest
pytest.importorskip('gemmi')
from .test_cif_complete_request import case
from .test_cif_postmr_request import entry_case
from .test_registered_preparation_native import native_case


def runtime_case(entry_case,monkeypatch):
    args,rows,calls=native_case(entry_case,monkeypatch)
    from nasolve import cif_runtime_bundle as bundle,cif_component_runtime as component
    root=args['inputs'].parent/'runtime';root.mkdir()
    paths=[]
    for i,p in enumerate([args['inputs']/'model.pdb',*args['dictionaries'],*args['supplementary_phils']]):
        copied=root/str(i);copied.write_bytes(p.read_bytes());paths.append(copied)
    manifest=dict(policy_id=component.ORIGINAL_POLICY_ID,decision=dict(selected='verified_prepared_bundle'),
        source_selection=dict(candidate_receipt='evidence/candidate/native_receipt.json'),
        unavailable_native_checks=[dict(check='formal-charge',status='UNSUPPORTED')])
    mp=root/'runtime_bundle.json';mp.write_text(json.dumps(manifest))
    saved={p:p.read_bytes() for p in root.iterdir()}
    def verify(path,value):
        if path.read_bytes()!=saved[path] or any(p.read_bytes()!=v for p,v in saved.items()):raise ValueError('Changed runtime')
    def resolve(path):
        verify(mp,manifest)
        return dict(model=paths[0],dictionaries=paths[1:3],phils=paths[3:],manifest=deepcopy(manifest),manifest_path=mp)
    views=[]
    @contextmanager
    def evidence(path,value,*,subtree=None):
        assert path==root and subtree=='candidate'
        with tempfile.TemporaryDirectory() as name:
            view=Path(name).resolve();views.append(view);p=view/'evidence/candidate/native_receipt.json';p.parent.mkdir(parents=True);p.write_bytes(args['native_receipt'].read_bytes());yield view
    monkeypatch.setattr(bundle,'resolve_runtime_bundle',resolve)
    monkeypatch.setattr(component,'verify_component_runtime_resources',verify)
    monkeypatch.setattr(component,'component_runtime_evidence',evidence)
    return {k:args[k] for k in ('inputs','components','reference')},root,manifest,mp,paths,calls,views,args


def test_original_runtime_reads_declared_capture_and_releases_view(entry_case,monkeypatch):
    from nasolve.cif_registered_preparation_native import review_registered_original_runtime
    args,root,manifest,mp,paths,calls,views,old=runtime_case(entry_case,monkeypatch)
    with patch('subprocess.Popen',side_effect=AssertionError('No native launch')):
        value=review_registered_original_runtime(**args,runtime=root)
    assert value['status']=='REGISTERED_ORIGINAL_RUNTIME_FOR_REVIEW'
    assert value['unavailable_native_checks']==manifest['unavailable_native_checks']
    assert value['native_input_review']['ordinary_admission'] is False
    assert value['native_input_review']['construction_provenance']=='NOT_ASSESSED'
    assert value['candidate_receipt']['anchor']=='runtime_evidence'
    assert value['candidate_receipt']['path']=='evidence/candidate/native_receipt.json'
    assert value['runtime']['sha256']==sha256(mp.read_bytes()).hexdigest()
    assert len(calls)==1 and len(views)==1 and not views[0].exists()
    assert str(root) not in json.dumps(value) and str(views[0]) not in json.dumps(value)


@pytest.mark.parametrize('defect',['policy','selection','model','receipt-role'])
def test_unqualified_runtime_role_refuses_before_native(entry_case,monkeypatch,defect):
    from nasolve.cif_registered_preparation_native import review_registered_original_runtime
    args,root,m,mp,paths,calls,views,old=runtime_case(entry_case,monkeypatch)
    # Keep fixture resolver identity coherent; only the adapter's chosen scope changes.
    from nasolve import cif_runtime_bundle
    resolve=cif_runtime_bundle.resolve_runtime_bundle
    def changed(path):
        value=resolve(path)
        if defect=='policy':value['manifest']['policy_id']='readyset'
        if defect=='selection':value['manifest']['decision']['selected']='readyset_checked_model'
        if defect=='receipt-role':value['manifest']['source_selection']['candidate_receipt']='../outside'
        if defect=='model':
            other=root/'changed-model';other.write_bytes(paths[0].read_bytes()+b'\n');value['model']=other
        return value
    monkeypatch.setattr(cif_runtime_bundle,'resolve_runtime_bundle',changed)
    with pytest.raises(ValueError):review_registered_original_runtime(**args,runtime=root)
    assert not calls


@pytest.mark.parametrize('member',['manifest','dictionary','registered'])
def test_changes_during_original_runtime_read_refuse(entry_case,monkeypatch,member):
    from nasolve.cif_registered_preparation_native import review_registered_original_runtime
    from nasolve import cif_prepared_backbone
    args,root,m,mp,paths,calls,views,old=runtime_case(entry_case,monkeypatch);original=cif_prepared_backbone._native_candidate
    target={'manifest':mp,'dictionary':paths[1],'registered':args['inputs']/'registered_backbone/continuations.json'}[member]
    def changed(*a):
        result=original(*a);target.write_bytes(target.read_bytes()+b'\n');return result
    monkeypatch.setattr(cif_prepared_backbone,'_native_candidate',changed)
    with pytest.raises(ValueError):review_registered_original_runtime(**args,runtime=root)
    assert all(not p.exists() for p in views)


def test_runtime_qualification_failure_cannot_be_bypassed(entry_case,monkeypatch):
    from nasolve.cif_registered_preparation_native import review_registered_original_runtime
    args,root,m,mp,paths,calls,views,old=runtime_case(entry_case,monkeypatch)
    def refuse(*a):raise ValueError('Source runtime is unqualified')
    monkeypatch.setattr('nasolve.cif_runtime_bundle.resolve_runtime_bundle',refuse)
    with pytest.raises(ValueError,match='unqualified'):review_registered_original_runtime(**args,runtime=root)
    assert not calls and not views
