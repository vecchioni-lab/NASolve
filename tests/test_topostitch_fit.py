"""Bounded placement is an unapproved proposal, with no hidden pairing search."""
import hashlib
import json
import math

import pytest

pytest.importorskip('scipy')

from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import inspect_pdb
from nasolve.topostitch_contacts import inspect_end_contacts
from nasolve.topostitch_discovery import plan_editable_windows
from nasolve.topostitch_inspect import load_registered_end_assignments
from nasolve.topostitch_fit import fit_end_placement
from .helpers import pdb_record
from .test_construct_registration import target
from .test_topostitch_preview import setup_preview, digest


def fit_inputs(tmp_path, *, periodic=False, move_target=False, target_z_shift=0, target_x_shift=-.2, extended=False):
    model,discovery,reg,_,_=setup_preview(tmp_path,anisou=False,extended=extended)
    first=[r for r in model.read_text().splitlines() if r.startswith('ATOM')]
    second=[]
    for r in first:
        xyz=[float(r[a:a+8]) for a in (30,38,46)]
        xyz=(-xyz[0]-8+target_x_shift+(40 if periodic else 0),xyz[1],12-xyz[2]+target_z_shift)
        r=r[:6]+f'{int(r[6:11])+1000:5d}'+r[11:17]+(' DT' if r[17:20].strip()=='DA' else ' DA')+r[20:21]+{'A':'C','B':'D'}[r[21]]+r[22:30]+''.join(f'{v:8.3f}' for v in xyz)+r[54:]
        second.append(r)
    rows=[]; codes={}; serial=3000
    for r in first+second:
        rows.append(r+'\n'); logical=f'{r[21]}:{int(r[22:26])}'; codes[logical]=r[17:20].strip()
        if r[12:16].strip()=='C6':
            x,y,z=[float(r[a:a+8]) for a in (30,38,46)]
            name='N6' if codes[logical]=='DA' else 'O4'
            rows.append(pdb_record('ATOM',serial,name,codes[logical],r[21],int(r[22:26]),x=x+1,y=y+.5,z=z,element=name[0])); serial+=1
    header='CRYST1   40.000   40.000   40.000  90.00  90.00  90.00 P 1           1\n' if periodic else ''
    model.write_text(header+''.join(rows)+'END\n')
    registry=build_construct_registration(inspect_pdb(model,polymer_ligand_codes={'DA','DT'}),target(*codes.items()),
        {'copy_1':{s:s for s in codes}},source='synthetic-fit')
    reg.write_text(json.dumps(registry))
    value=json.loads(discovery.read_text()); value.update(model_sha256=digest(model.read_bytes()),registration_sha256=digest(reg.read_bytes()))
    originals=list(value['strands']); pairs=list(value['duplex_pairs'])
    for route in originals:
        value['strands'].append({**route,'strand_id':{'A':'C','B':'D'}[route['strand_id']],
            'sites':[{'A':'C','B':'D'}[s[0]]+s[1:] for s in route['sites']]})
    value['duplex_pairs'] += [[{'A':'C','B':'D'}[s[0]]+s[1:] for s in p] for p in pairs]
    discovery.write_text(json.dumps(value))
    sha,assignments,_,mapping=load_registered_end_assignments(model,discovery,reg)
    observations=inspect_end_contacts(model,assignments,expected_sha256=sha,max_distance_angstrom=20,periodic=periodic)
    screen=observations['periodic_screening' if periodic else 'screening']
    edge=next(c for c in screen['candidates'] if c['ends'][0]!=c['ends'][1])
    chosen=edge['ends'][1 if move_target else 0]
    windows=plan_editable_windows(mapping['discovery_assessment'],max_base_pairs=6,fixed_anchor_pairs=2)
    window=next(e['windows'][-1] for e in windows['ends'] if e['end_id']==chosen)
    request=dict(schema_version=1,kind='topostitch-placement-request',model_sha256=sha,
        discovery_file_sha256=digest(discovery.read_bytes()),registration_file_sha256=digest(reg.read_bytes()),
        reference_catalog_sha256=observations['contact_assessment']['library']['effective_catalog_sha256'],
        search=dict(periodic=periodic,radius_angstrom=20.,max_pairs=1000,max_image_tests=100000),
        candidate=dict(ends=edge['ends'],target_image_operator=edge.get('target_image',{}).get('operator_xyz')),
        window=dict(window_id=window['window_id'],max_base_pairs=6,fixed_anchor_pairs=2),
        motion_bounds=dict(rotation_degrees=[10.,10.,10.],translation_angstrom=[4.,4.,4.]),
        objective=dict(backbone_distance_scale_angstrom=.5,backbone_angle_scale_degrees=20.,
            plane_offset_scale_angstrom=.5,plane_normal_scale_degrees=10.,motion_weight=.01),
        limits=dict(max_atom_displacement_angstrom=20.,max_backbone_bond_change_angstrom=5.,max_backbone_angle_change_degrees=90.),
        max_residual_evaluations=3000)
    if extended:
        request['schema_version']=2
        request['objective']['backbone_torsion_scale_degrees']=10.
        request['limits']['max_backbone_torsion_change_degrees']=90.
    path=tmp_path/'fit.json'; path.write_text(json.dumps(request))
    return model,discovery,reg,path


def fit(paths):
    return fit_end_placement(paths[0],paths[1],registration_path=paths[2],request_path=paths[3])


def change(paths, **changes):
    request=json.loads(paths[3].read_text()); request.update(changes); paths[3].write_text(json.dumps(request))


@pytest.mark.parametrize('move_target',[False,True])
def test_fit_improves_named_pair_without_editing_source_or_approving(tmp_path,move_target):
    paths=fit_inputs(tmp_path,move_target=move_target)
    before={p:p.read_bytes() for p in tmp_path.iterdir()}
    result=fit(paths)
    assert result['status']=='TRANSFORM_FOR_REVIEW'
    assert result['serialized_after']['pair_target_sum_squares'] < result['before']['pair_target_sum_squares']
    assert result['trial']['kind']=='topostitch-window-transform'
    assert result['geometry_validated'] is False and result['runtime_authority'] is False
    assert result['solver']['residual_calls']<=3000
    assert result['solver']['residual_calls']>result['solver']['nfev']
    assert {p:p.read_bytes() for p in tmp_path.iterdir()}==before
    assert str(tmp_path) not in json.dumps(result)


def test_budget_counts_jacobian_calls_and_returns_no_partial_transform(tmp_path):
    paths=fit_inputs(tmp_path); change(paths,max_residual_evaluations=2)
    result=fit(paths)
    assert result['status']=='BUDGET_EXHAUSTED'
    assert result['solver']['residual_calls']==2
    assert result['trial'] is None


def test_post_serialization_limits_can_reject_an_improving_fit(tmp_path):
    paths=fit_inputs(tmp_path)
    change(paths,limits=dict(max_atom_displacement_angstrom=.001,max_backbone_bond_change_angstrom=5.,max_backbone_angle_change_degrees=90.))
    result=fit(paths)
    assert result['status']=='TRIAL_LIMIT_REJECTED' and result['trial'] is None


@pytest.mark.parametrize('key,value',[('model_sha256','a'*64),('reference_catalog_sha256','b'*64),
    ('max_residual_evaluations',True),('max_residual_evaluations',0)])
def test_stale_inputs_and_invalid_budgets_are_errors(tmp_path,key,value):
    paths=fit_inputs(tmp_path); change(paths,**{key:value})
    with pytest.raises(ValueError): fit(paths)


def test_periodic_translation_and_identity_frame_give_equivalent_fit(tmp_path):
    pytest.importorskip('gemmi')
    first=tmp_path/'first'; second=tmp_path/'second'; first.mkdir(); second.mkdir()
    a=fit(fit_inputs(first)); b=fit(fit_inputs(second,periodic=True))
    assert a['status']==b['status']=='TRANSFORM_FOR_REVIEW'
    assert a['serialized_after']['pair_target_sum_squares']==pytest.approx(b['serialized_after']['pair_target_sum_squares'],rel=1e-5)
    assert b['selected_candidate']['target_image']['operator_xyz']!='x,y,z'


def test_zero_residual_control_returns_noop(tmp_path,monkeypatch):
    import copy
    import nasolve.topostitch_contacts as contacts
    paths=fit_inputs(tmp_path,target_z_shift=-3)
    digest_value,assignments,_,_=load_registered_end_assignments(paths[0],paths[1],paths[2])
    observation=contacts.inspect_end_contacts(paths[0],assignments,expected_sha256=digest_value,max_distance_angstrom=20)
    library=copy.deepcopy(observation['contact_assessment']['library'])
    # Synthetic known-answer target: the starting coordinates themselves.
    pair=observation['contact_assessment']['candidates'][0]['residue_pairs'][0]
    for kind in ('bonds','angles'):
        for row,measured in zip(library['effective_catalog']['recipes']['AT'][kind],pair[kind]):
            row[-2]=measured['observed']
    library['effective_catalog_sha256']=hashlib.sha256(json.dumps(library['effective_catalog'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    monkeypatch.setattr(contacts,'_canonical_catalog',lambda:library)
    change(paths,reference_catalog_sha256=library['effective_catalog_sha256'])
    result=fit(paths)
    assert result['before']['pair_target_sum_squares']<1e-20
    assert result['status']=='NO_PAIR_TARGET_IMPROVEMENT'
    assert result['trial'] is None


def test_suggested_trial_reproduces_the_scored_candidate(tmp_path):
    from nasolve.topostitch_preview import build_bend_preview, load_bend_preview
    paths=fit_inputs(tmp_path)
    result=fit(paths)
    trial=tmp_path/'suggested.json'; trial.write_text(json.dumps(result['trial']))
    preview=build_bend_preview(paths[0],paths[1],registration_path=paths[2],trial_path=trial,output_directory=tmp_path/'candidate')
    assert preview['candidate_model_sha256']==result['candidate_model_sha256']
    assert load_bend_preview(tmp_path/'candidate')==preview


def test_invalid_or_changed_pairing_is_not_replaced_by_a_nearby_one(tmp_path):
    paths=fit_inputs(tmp_path)
    request=json.loads(paths[3].read_text())
    change(paths,candidate=dict(ends=list(reversed(request['candidate']['ends'])),target_image_operator=None))
    with pytest.raises(ValueError,match='absent'): fit(paths)


def test_optional_dependency_error_is_explicit(tmp_path,monkeypatch):
    import builtins
    import nasolve.topostitch_fit as module
    original=builtins.__import__
    def blocked(name,*args,**kwargs):
        if name=='scipy.optimize': raise ImportError('test missing optional dependency')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',blocked)
    with pytest.raises(RuntimeError,match='topology-fit'): module._scipy()


def test_fit_cli_is_json_only_and_does_not_write_models(tmp_path,capsys):
    from nasolve.topostitch_fit import main
    paths=fit_inputs(tmp_path); change(paths,max_residual_evaluations=2)
    files=set(tmp_path.iterdir())
    assert main([str(paths[0]),str(paths[1]),'--registration',str(paths[2]),'--request',str(paths[3])])==0
    assert json.loads(capsys.readouterr().out)['status']=='BUDGET_EXHAUSTED'
    assert set(tmp_path.iterdir())==files


def test_opposite_plane_offsets_can_request_opposite_motion(tmp_path):
    positive=tmp_path/'positive'; negative=tmp_path/'negative'; positive.mkdir(); negative.mkdir()
    a=fit(fit_inputs(positive,target_z_shift=0))
    b=fit(fit_inputs(negative,target_z_shift=-6))
    assert a['status']==b['status']=='TRANSFORM_FOR_REVIEW'
    assert a['trial']['translation_angstrom'][2]*b['trial']['translation_angstrom'][2]<0


def test_invalid_motion_scale_and_self_pair_are_rejected(tmp_path):
    paths=fit_inputs(tmp_path)
    original=json.loads(paths[3].read_text())
    for change_set in [
        {'motion_bounds':{'rotation_degrees':[200,1,1],'translation_angstrom':[1,1,1]}},
        {'objective':{**original['objective'],'plane_normal_scale_degrees':180}},
        {'candidate':{'ends':[original['candidate']['ends'][0]]*2,'target_image_operator':None}}]:
        paths[3].write_text(json.dumps({**original,**change_set}))
        with pytest.raises(ValueError): fit(paths)


def test_screw_image_fit_uses_asu_motion_before_target_image(tmp_path):
    gemmi=pytest.importorskip('gemmi')
    base=tmp_path/'base'; screw=tmp_path/'screw'; base.mkdir(); screw.mkdir()
    expected=fit(fit_inputs(base,move_target=True))
    paths=fit_inputs(screw,move_target=True)
    wanted=gemmi.Op('y,-x,z+1/4'); inverse=wanted.inverse(); cell=gemmi.UnitCell(40,40,40,90,90,90)
    lines=['CRYST1   40.000   40.000   40.000  90.00  90.00  90.00 P 43          1\n']
    for row in paths[0].read_text().splitlines(keepends=True):
        if row.startswith('ATOM') and row[21] in 'CD':
            point=gemmi.Position(*(float(row[a:a+8]) for a in (30,38,46)))
            xyz=cell.orthogonalize(gemmi.Fractional(*inverse.apply_to_xyz(list(cell.fractionalize(point)))))
            row=row[:30]+''.join(f'{v:8.3f}' for v in xyz)+row[54:]
        lines.append(row)
    paths[0].write_text(''.join(lines))
    registry=json.loads(paths[2].read_text()); registry['model']['sha256']=digest(paths[0].read_bytes())
    paths[2].write_text(json.dumps(registry))
    manifest=json.loads(paths[1].read_text()); manifest.update(model_sha256=digest(paths[0].read_bytes()),registration_sha256=digest(paths[2].read_bytes()))
    paths[1].write_text(json.dumps(manifest))
    request=json.loads(paths[3].read_text())
    _,assignments,_,_=load_registered_end_assignments(paths[0],paths[1],paths[2])
    first=next(a for a in assignments if a.end_id==request['candidate']['ends'][0])
    operator=wanted if first.overhang_sites[0].chain=='A' else inverse
    request.update(model_sha256=manifest['model_sha256'],discovery_file_sha256=digest(paths[1].read_bytes()),
        registration_file_sha256=digest(paths[2].read_bytes()),search={**request['search'],'periodic':True},
        candidate={**request['candidate'],'target_image_operator':operator.triplet()})
    paths[3].write_text(json.dumps(request))
    actual=fit(paths)
    assert actual['status']==expected['status']=='TRANSFORM_FOR_REVIEW'
    assert actual['serialized_after']['pair_target_sum_squares']==pytest.approx(expected['serialized_after']['pair_target_sum_squares'],rel=1e-5)


def test_periodic_fit_defers_partial_occupancy_before_solver(tmp_path,monkeypatch):
    pytest.importorskip('gemmi')
    paths=fit_inputs(tmp_path,periodic=True)
    model,discovery,reg,request_path=paths
    model.write_text(model.read_text().replace('  1.00','  0.50',1))
    codes={f'{r[21]}:{int(r[22:26])}':r[17:20].strip() for r in model.read_text().splitlines() if r.startswith('ATOM')}
    registry=build_construct_registration(inspect_pdb(model,polymer_ligand_codes={'DA','DT'}),target(*codes.items()),
        {'copy_1':{s:s for s in codes}},source='synthetic-fit')
    reg.write_text(json.dumps(registry))
    value=json.loads(discovery.read_text());value.update(model_sha256=digest(model.read_bytes()),registration_sha256=digest(reg.read_bytes()));discovery.write_text(json.dumps(value))
    change(paths,model_sha256=digest(model.read_bytes()),discovery_file_sha256=digest(discovery.read_bytes()),registration_file_sha256=digest(reg.read_bytes()))
    def forbidden(*args,**kwargs):raise AssertionError('Ambiguous image must not reach the solver')
    monkeypatch.setattr('nasolve.topostitch_fit._scipy',lambda:forbidden)
    result=fit(paths)
    assert result['status']=='IMAGE_IDENTITY_REVIEW_REQUIRED'
    assert result['trial'] is None and result['solver']['residual_calls']==0
    assert result['selected_image_identity']['assessment']=='COINCIDENCE_OR_OCCUPANCY_REVIEW'


def test_periodic_fit_defers_coincident_distinct_atoms(tmp_path,monkeypatch):
    pytest.importorskip('gemmi')
    # Preserve the original synthetic corner case: A:1 N1 coincides exactly
    # with the selected C:1 N1 image even though their source labels differ.
    paths=fit_inputs(tmp_path,periodic=True,target_x_shift=0)
    def forbidden(*args,**kwargs):raise AssertionError('Coincident source identities must not reach the solver')
    monkeypatch.setattr('nasolve.topostitch_fit._scipy',lambda:forbidden)
    result=fit(paths)
    assert result['status']=='IMAGE_IDENTITY_REVIEW_REQUIRED'
    assert result['trial'] is None and result['solver']['residual_calls']==0
    audit=result['selected_image_identity']
    assert audit['selected_atom_sets_disjoint'] is False
    assert audit['selected_image_overlaps'][0]['relation']=='DISTINCT_SOURCE_ATOMS_COINCIDE'


def test_extended_fit_scores_and_materializes_the_same_torsion_audit(tmp_path):
    from nasolve.topostitch_preview import build_bend_preview,load_bend_preview
    paths=fit_inputs(tmp_path,extended=True)
    report=fit(paths)
    assert report['schema_version']==2 and report['status']=='TRANSFORM_FOR_REVIEW'
    assert report['trial']['schema_version']==2
    assert report['preview_audit']['backbone_audit']['max_torsion_change_degrees']<=90.
    assert all(len(r['angles_degrees'])==4 for r in report['preview_audit']['backbone_audit']['links'])
    trial=tmp_path/'extended-trial.json';trial.write_text(json.dumps(report['trial']))
    preview=build_bend_preview(paths[0],paths[1],registration_path=paths[2],trial_path=trial,output_directory=tmp_path/'extended-preview')
    assert preview['candidate_model_sha256']==report['candidate_model_sha256']
    assert preview['backbone_audit']==report['preview_audit']['backbone_audit']
    assert load_bend_preview(tmp_path/'extended-preview')==preview


def test_extended_fit_cannot_silently_drop_new_terms_or_limits(tmp_path):
    paths=fit_inputs(tmp_path,extended=True)
    original=json.loads(paths[3].read_text())
    for section,key in [('objective','backbone_torsion_scale_degrees'),('limits','max_backbone_torsion_change_degrees')]:
        missing=json.loads(json.dumps(original));missing[section].pop(key);paths[3].write_text(json.dumps(missing))
        with pytest.raises(ValueError,match='Expected object fields'):fit(paths)
    paths[3].write_text(json.dumps({**original,'schema_version':1}))
    with pytest.raises(ValueError,match='Expected object fields'):fit(paths)
