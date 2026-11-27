"""Frozen registered input joins exact native evidence, without runtime authority.

The small native owner is mocked here; retained FT capture exercises it without
mocks in the recorded live qualification. No synthetic test is chemistry proof.
"""
from hashlib import sha256
from pathlib import Path
from copy import deepcopy
import shutil
from unittest.mock import patch

import pytest
pytest.importorskip('gemmi')

from .test_cif_complete_request import case
from .test_cif_postmr_request import entry_case
from .test_registered_preparation_request import registered_case
from .test_cif_repair_attempt import inventory


def native_case(entry, monkeypatch):
    from nasolve.cif_registered_preparation_input import capture_registered_backbone
    from nasolve import cif_prepared_backbone
    _,args,*_=registered_case(entry)
    model=args['model'];codes=['YYY','ZZZ']
    captured=capture_registered_backbone(model,codes,dict(args['registered_preparation'],report=args['report']))
    root=model.parent/'frozen';root.mkdir();(root/'model.pdb').write_bytes(model.read_bytes())
    for name,raw in captured['files'].items():
        p=root/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(raw)
    dictionaries=[model.parent/'first.cif',model.parent/'second.cif']
    phils=[model.parent/'first.phil',model.parent/'second.phil']
    for i,p in enumerate([*dictionaries,*phils]):p.write_text('distinct input '+str(i))
    receipt=model.parent/'receipt.json';receipt.write_text('native receipt fixture')
    rows=[dict(role=role,sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,
               anchor='native_directory',path=f'inputs/{i}')
          for i,(role,p) in enumerate([('model',root/'model.pdb'),*[('dictionary',p) for p in dictionaries],*[('phil',p) for p in phils]])]
    calls=[]
    def native(source,candidate,receipt_path,paths,observations,local,intent,components):
        assert source==candidate==root/'model.pdb'
        assert [r['registered_continuation']['continuation_id'] for r in observations]==[1,2]
        assert all(r['registered_continuation']['oxygen_operator_xyz']=='x-1,y,z' for r in observations)
        calls.append(components)
        return dict(status='NATIVE_INPUTS_VERIFIED_FOR_REVIEW',native_inputs=deepcopy(rows),
            candidate_model_sha256=sha256(candidate.read_bytes()).hexdigest(),
            native_receipt_sha256=sha256(receipt_path.read_bytes()).hexdigest(),
            registered_continuations=[dict(id=1),dict(id=2)])
    monkeypatch.setattr(cif_prepared_backbone,'_native_candidate',native)
    return dict(inputs=root,components=codes,reference=captured['reference'],native_receipt=receipt,
                dictionaries=dictionaries,supplementary_phils=phils),rows,calls


def test_registered_native_review_preserves_context_without_admission(entry_case,monkeypatch):
    from nasolve.cif_registered_preparation_native import review_registered_native_input
    args,rows,calls=native_case(entry_case,monkeypatch);before=inventory(args['inputs'].parent)
    with patch('subprocess.Popen',side_effect=AssertionError('Read-only native evidence')):
        value=review_registered_native_input(**args)
    assert value['status']=='REGISTERED_NATIVE_INPUTS_VERIFIED_FOR_REVIEW'
    assert value['registered_backbone']==args['reference']
    assert value['native']['native_inputs']==rows and len(calls)==1
    assert value['ordinary_admission'] is False and value['native_image_forces']=='NOT_ASSESSED'
    assert value['construction_provenance']=='NOT_ASSESSED' and value['refinement']=='NOT_RUN'
    assert inventory(args['inputs'].parent)==before


@pytest.mark.parametrize('defect',['dictionary','phil_order','missing','duplicate','role'])
def test_exact_native_inputs_cannot_be_changed(entry_case,monkeypatch,defect):
    from nasolve.cif_registered_preparation_native import review_registered_native_input
    args,rows,calls=native_case(entry_case,monkeypatch)
    if defect=='dictionary':args['dictionaries'][0].write_text('different chemical state')
    if defect=='phil_order':args['supplementary_phils'].reverse()
    if defect=='missing':args['dictionaries'].pop()
    if defect=='duplicate':args['dictionaries'].append(args['dictionaries'][0])
    if defect=='role':rows[1]['role']='phil'
    with pytest.raises(ValueError,match='[Ii]nputs|[Dd]istinct|[Dd]ictionar|[Nn]ative'):
        review_registered_native_input(**args)


def test_registered_role_change_is_checked_before_native_read(entry_case,monkeypatch):
    from nasolve.cif_registered_preparation_native import review_registered_native_input
    args,rows,calls=native_case(entry_case,monkeypatch)
    p=args['inputs']/'registered_backbone/continuations.json';p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError):review_registered_native_input(**args)
    assert calls==[]


def test_native_owner_refusal_is_not_relabelled_as_success(entry_case,monkeypatch):
    from nasolve.cif_registered_preparation_native import review_registered_native_input
    args,rows,calls=native_case(entry_case,monkeypatch)
    def refuse(*a):raise ValueError('Competing native image bond')
    monkeypatch.setattr('nasolve.cif_prepared_backbone._native_candidate',refuse)
    with pytest.raises(ValueError,match='Competing native image'):review_registered_native_input(**args)


@pytest.mark.parametrize('member',['dictionary','receipt','registered'])
def test_inputs_changing_during_native_read_refuse(entry_case,monkeypatch,member):
    from nasolve.cif_registered_preparation_native import review_registered_native_input
    from nasolve import cif_prepared_backbone
    args,rows,calls=native_case(entry_case,monkeypatch);original=cif_prepared_backbone._native_candidate
    path={'dictionary':args['dictionaries'][0],'receipt':args['native_receipt'],
          'registered':args['inputs']/'registered_backbone/continuations.json'}[member]
    def change(*a):
        result=original(*a);path.write_bytes(path.read_bytes()+b'\n');return result
    monkeypatch.setattr(cif_prepared_backbone,'_native_candidate',change)
    with pytest.raises(ValueError):review_registered_native_input(**args)
