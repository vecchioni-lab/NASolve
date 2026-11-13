"""Preview arithmetic, preservation and portable evidence; synthetic, not DNA qualification."""
import hashlib
import json
import math
import shutil

import pytest

from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import inspect_pdb
from nasolve.topostitch_discovery import plan_editable_windows
from nasolve.topostitch_inspect import load_registered_end_assignments
from nasolve.topostitch_preview import build_bend_preview, load_bend_preview
from .helpers import pdb_record
from .test_construct_registration import target


def digest(data):
    return hashlib.sha256(data).hexdigest()


def setup_preview(tmp_path, *, anisou=True, rotation=(0, 0, 1), translation=(0.1, 0, 0), extended=False):
    rows, codes, serial = [], {}, 1
    for chain, count, x, direction in [('A', 8, -5, -1), ('B', 6, 5, 1)]:
        for resid in range(1, count+1):
            z = (3-resid)*3 if chain == 'A' else (resid-6)*3
            code = 'DA' if chain == 'A' else 'DT'
            codes[f'{chain}:{resid}'] = code
            points = {name: (x+math.cos(i*math.pi/3), math.sin(i*math.pi/3), z)
                      for i,name in enumerate(('N1','C2','N3','C4','C5','C6'))}
            points.update({"C1'": (x,-2,z), 'P': (x,0,z-direction*.1),
                           "O3'": (x,0,z+direction*1.5), "C3'": (x+1,0,z+direction*.5),
                           "O5'": (x+.8,0,z-direction*.7)})
            if extended:
                points.update({"OP1":(x+1.2,.4,z-direction*.1),"OP2":(x-.4,1.2,z-direction*.1),
                               "C4'":(x+1.1,1.,z+direction*.2),"C5'":(x+1.4,.6,z-direction*1.1)})
            for name,p in points.items():
                row = pdb_record('ATOM',serial,name,code,chain,resid,x=p[0],y=p[1],z=p[2],element=name[0])
                rows.append(row)
                if anisou:
                    rows.append('ANISOU'+row[6:28]+''.join(f'{v:7d}' for v in (1000,2000,3000,100,50,-25))+row[70:])
                serial += 1
        rows.append('TER\n')
    model = tmp_path/'input.pdb'; model.write_text(''.join(rows)+'END\n')
    registration = build_construct_registration(inspect_pdb(model,polymer_ligand_codes=set(codes.values())),
        target(*codes.items()), {'copy_1': {s:s for s in codes}}, source='synthetic-preview')
    reg = tmp_path/'registration.json'; reg.write_text(json.dumps(registration))
    manifest = dict(schema_version=1,kind='topostitch-end-discovery-input',model_sha256=digest(model.read_bytes()),
        registration_sha256=digest(reg.read_bytes()),copy_id='copy_1',pairing_inventory_complete=True,
        strands=[dict(strand_id=c,sites=[f'{c}:{i}' for i in range(1,n+1)],
            five_prime_boundary='chemical' if c=='A' else 'unknown',
            three_prime_boundary='chemical' if c=='B' else 'unknown') for c,n in [('A',8),('B',6)]],
        duplex_pairs=[[f'A:{i}',f'B:{9-i}'] for i in range(3,9)])
    discovery = tmp_path/'discovery.json'; discovery.write_text(json.dumps(manifest))
    _,_,_,mapping=load_registered_end_assignments(model,discovery,reg)
    windows=plan_editable_windows(mapping['discovery_assessment'],max_base_pairs=6,fixed_anchor_pairs=2)
    window=windows['ends'][0]['windows'][-1]
    request=dict(schema_version=1,kind='topostitch-window-transform',model_sha256=manifest['model_sha256'],
        discovery_file_sha256=digest(discovery.read_bytes()),registration_file_sha256=digest(reg.read_bytes()),
        window_id=window['window_id'],max_window_pairs=6,fixed_anchor_pairs=2,
        rotation_vector_degrees=list(rotation),translation_angstrom=list(translation),
        max_atom_displacement_angstrom=30.,max_backbone_bond_change_angstrom=20.,max_backbone_angle_change_degrees=180.)
    trial=tmp_path/'trial.json'; trial.write_text(json.dumps(request))
    return model,discovery,reg,trial,window


def build(paths, out):
    return build_bend_preview(paths[0],paths[1],registration_path=paths[2],trial_path=paths[3],output_directory=out)


def coords(data):
    return {r[6:27]:tuple(float(r[a:b]) for a,b in ((30,38),(38,46),(46,54)))
            for r in data.decode().splitlines() if r.startswith('ATOM')}


def change_trial(paths, **changes):
    value=json.loads(paths[3].read_text()); value.update(changes); paths[3].write_text(json.dumps(value))


def test_preview_preserves_source_and_anchors_and_audits_rendered_coordinates(tmp_path):
    paths=setup_preview(tmp_path)
    original=paths[0].read_bytes()
    out=tmp_path/'preview'
    report=build(paths,out)
    candidate=(out/'candidate.pdb').read_bytes()
    assert paths[0].read_bytes()==original==(out/'source.pdb').read_bytes()
    assert candidate!=original
    fixed=set(paths[4]['fixed_sites'])
    for before,after in zip(original.decode().splitlines(),candidate.decode().splitlines()):
        if before.startswith(('ATOM','ANISOU')):
            logical=f'{before[21]}:{int(before[22:26])}'
            if logical in fixed: assert after==before
        else: assert after==before
    assert report['workflow']=={'execution_state':'CANDIDATE_BUILT','review_state':'UNREVIEWED','refinement_state':'NOT_ATTEMPTED'}
    assert report['geometry_validated'] is False
    assert report['runtime_authority'] is False
    assert report['backbone_audit']['links']
    assert report['backbone_audit']['limits_passed'] is True
    actual=max(math.dist(p,coords(candidate)[k]) for k,p in coords(original).items())
    assert report['max_atom_displacement_angstrom']==pytest.approx(actual)
    assert str(tmp_path) not in json.dumps(report)


def test_zero_transform_is_byte_identical_including_anisou(tmp_path):
    paths=setup_preview(tmp_path,rotation=(0,0,0),translation=(0,0,0))
    build(paths,tmp_path/'preview')
    assert (tmp_path/'preview/candidate.pdb').read_bytes()==paths[0].read_bytes()


def test_terminal_rigid_rotation_preserves_distances_and_rotates_anisou(tmp_path):
    paths=setup_preview(tmp_path,rotation=(0,0,90),translation=(0,0,0))
    build(paths,tmp_path/'preview')
    before=paths[0].read_bytes(); after=(tmp_path/'preview/candidate.pdb').read_bytes()
    old,new=coords(before),coords(after)
    terminal=[k for k in old if k[15]=='A' and int(k[16:20]) in (1,2,3)]
    assert len(terminal)==33
    assert math.dist(old[terminal[0]],old[terminal[-1]])==pytest.approx(math.dist(new[terminal[0]],new[terminal[-1]]),abs=.002)
    u=next(r for r in after.decode().splitlines() if r.startswith('ANISOU'))
    assert [int(u[a:a+7]) for a in (28,35,42,49,56,63)]==[2000,1000,3000,-100,25,50]


@pytest.mark.parametrize('field,value',[
    ('max_atom_displacement_angstrom',.001),('max_backbone_bond_change_angstrom',.000001),
    ('max_backbone_angle_change_degrees',.000001),('rotation_vector_degrees',[0,0,181]),
    ('translation_angstrom',[float('nan'),0,0]),('max_window_pairs',True),
    ('window_id','unknown'),('model_sha256','a'*64)])
def test_rejected_trials_write_nothing(tmp_path,field,value):
    paths=setup_preview(tmp_path); change_trial(paths,**{field:value})
    with pytest.raises(ValueError): build(paths,tmp_path/'preview')
    assert not (tmp_path/'preview').exists()


def test_existing_output_is_never_overwritten(tmp_path):
    paths=setup_preview(tmp_path); out=tmp_path/'preview'; out.mkdir(); (out/'mine').write_text('keep')
    with pytest.raises(FileExistsError): build(paths,out)
    assert (out/'mine').read_text()=='keep'


def test_preview_relocates_and_verifies_after_original_inputs_are_gone(tmp_path):
    source=tmp_path/'original'; source.mkdir(); paths=setup_preview(source)
    build(paths,source/'preview')
    moved=tmp_path/'relocated'; shutil.move(str(source/'preview'),moved); shutil.rmtree(source)
    report=load_bend_preview(moved)
    assert report['kind']=='topostitch-bend-preview'
    with (moved/'candidate.pdb').open('ab') as f: f.write(b'REMARK tampered\n')
    with pytest.raises(ValueError,match='artifact'): load_bend_preview(moved)


def rebind_source(paths, text):
    """Freeze a deliberately malformed variant as a new explicit test input."""
    paths[0].write_text(text)
    registration=json.loads(paths[2].read_text()); registration['model']['sha256']=digest(paths[0].read_bytes())
    paths[2].write_text(json.dumps(registration))
    discovery=json.loads(paths[1].read_text()); discovery.update(model_sha256=digest(paths[0].read_bytes()),
        registration_sha256=digest(paths[2].read_bytes()))
    paths[1].write_text(json.dumps(discovery))
    change_trial(paths,model_sha256=discovery['model_sha256'],discovery_file_sha256=digest(paths[1].read_bytes()),
        registration_file_sha256=digest(paths[2].read_bytes()))


@pytest.mark.parametrize('defect', ['missing_phosphate','bad_occupancy','duplicate_anisou','orphan_anisou','sigatm'])
def test_selected_unsupported_atom_records_fail_before_writing(tmp_path,defect):
    paths=setup_preview(tmp_path)
    rows=paths[0].read_text().splitlines(keepends=True)
    if defect=='missing_phosphate':
        rows=[r for r in rows if not (r.startswith(('ATOM','ANISOU')) and r[21]=='A' and int(r[22:26])==2 and r[12:16].strip()=='P')]
    elif defect=='bad_occupancy':
        i=next(i for i,r in enumerate(rows) if r.startswith('ATOM') and r[12:16].strip()=="O3'")
        rows[i]=rows[i][:54]+'  0.00'+rows[i][60:]
    elif defect=='duplicate_anisou':
        rows.insert(2,rows[1])
    elif defect=='orphan_anisou':
        rows[1]=rows[1][:6]+'99999'+rows[1][11:]
    else:
        rows.insert(2,'SIGATM'+rows[0][6:])
    rebind_source(paths,''.join(rows))
    with pytest.raises(ValueError): build(paths,tmp_path/'preview')
    assert not (tmp_path/'preview').exists()


def test_coordinate_width_overflow_is_not_written(tmp_path):
    paths=setup_preview(tmp_path)
    change_trial(paths,translation_angstrom=[100000,0,0],max_atom_displacement_angstrom=1000000.)
    with pytest.raises(ValueError,match='field width'): build(paths,tmp_path/'preview')
    assert not (tmp_path/'preview').exists()


@pytest.mark.parametrize('declaration', ['do_not_connect_sites','protected_sites'])
def test_free_and_protected_end_cannot_be_moved_by_old_window_id(tmp_path,declaration):
    paths=setup_preview(tmp_path)
    value=json.loads(paths[1].read_text()); value[declaration]=['A:3']
    paths[1].write_text(json.dumps(value))
    change_trial(paths,discovery_file_sha256=digest(paths[1].read_bytes()))
    with pytest.raises(ValueError,match='window'): build(paths,tmp_path/'preview')
    assert not (tmp_path/'preview').exists()


def test_receipt_tampering_is_detected_even_with_unchanged_artifacts(tmp_path):
    paths=setup_preview(tmp_path); out=tmp_path/'preview'; build(paths,out)
    receipt=json.loads((out/'preview.json').read_text()); receipt['geometry_validated']=True
    (out/'preview.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='reproduce'): load_bend_preview(out)


def test_candidate_tampering_cannot_be_hidden_by_updating_artifact_hash(tmp_path):
    paths=setup_preview(tmp_path); out=tmp_path/'preview'; build(paths,out)
    data=(out/'candidate.pdb').read_bytes()+b'REMARK added\n'; (out/'candidate.pdb').write_bytes(data)
    receipt=json.loads((out/'preview.json').read_text())
    receipt['artifacts']['candidate'].update(sha256=digest(data),size_bytes=len(data))
    (out/'preview.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='reproduce'): load_bend_preview(out)


def test_selected_rigid_residues_and_every_unselected_record_are_preserved(tmp_path):
    paths=setup_preview(tmp_path,rotation=(5,4,-3),translation=(.2,.3,-.4)); out=tmp_path/'preview'
    build(paths,out)
    before,after=coords(paths[0].read_bytes()),coords((out/'candidate.pdb').read_bytes())
    by_site={}
    for key in before: by_site.setdefault(key[15:],[]).append(key)
    for keys in by_site.values():
        for a,b in zip(keys,keys[1:]):
            assert abs(math.dist(before[a],before[b])-math.dist(after[a],after[b]))<.002
    moving=set(paths[4]['movable_sites'])
    original=paths[0].read_text().splitlines(); modified=(out/'candidate.pdb').read_text().splitlines()
    assert len(original)==len(modified)
    for a,b in zip(original,modified):
        if a.startswith(('ATOM','ANISOU')) and f'{a[21]}:{int(a[22:26])}' in moving:
            assert a[:28]==b[:28]
            assert a[70:]==b[70:]
            if a.startswith('ATOM'): assert a[54:]==b[54:]
        else: assert a==b


def test_cli_reports_a_new_preview_and_rejects_reuse(tmp_path,capsys):
    from nasolve.topostitch_preview import main
    paths=setup_preview(tmp_path)
    arguments=[str(paths[0]),str(paths[1]),'--registration',str(paths[2]),'--trial',str(paths[3]),'--out',str(tmp_path/'preview')]
    assert main(arguments)==0
    assert json.loads(capsys.readouterr().out)['workflow']['execution_state']=='CANDIDATE_BUILT'
    with pytest.raises(SystemExit) as exc: main(arguments)
    assert exc.value.code==2
    assert 'already exists' in capsys.readouterr().err


def test_extended_backbone_preview_is_explicit_and_replayable(tmp_path):
    paths=setup_preview(tmp_path,extended=True)
    change_trial(paths,schema_version=2,max_backbone_torsion_change_degrees=180.)
    report=build(paths,tmp_path/'extended')
    assert report['schema_version']==2
    assert report['backbone_audit']['policy']=='extended-junction-source-change-v2'
    assert all(len(r['angles_degrees'])==4 and len(r['torsions_degrees'])==3 for r in report['backbone_audit']['links'])
    assert load_bend_preview(tmp_path/'extended')==report


def test_extended_audit_detects_phosphate_rotation_missed_by_two_angles():
    from nasolve.topostitch_preview import _audit_links, TrialLimitError
    left={"O3'":(1.,1.,-1.),"C3'":(2.,1.,-1.),"C4'":(2.,2.,-2.)}
    right={'P':(0.,0.,0.),"O5'":(0.,0.,1.),'OP1':(1.,0.,0.),'OP2':(0.,1.,0.),"C5'":(1.,0.,1.5)}
    before={'a':left,'b':right}
    # Rotate the following residue around P--O5. The old O3-P length and two
    # watched angles are unchanged, but phosphate orientation changes.
    after={'a':left,'b':{k:(-p[1],p[0],p[2]) for k,p in right.items()}}
    legacy={'schema_version':1,'max_backbone_bond_change_angstrom':.001,'max_backbone_angle_change_degrees':.001}
    assert _audit_links([('a','b')],before,after,legacy)['max_angle_change_degrees']==pytest.approx(0)
    with pytest.raises(TrialLimitError,match='Extended backbone'):
        _audit_links([('a','b')],before,after,{**legacy,'schema_version':2,'max_backbone_torsion_change_degrees':180})


def test_circular_torsion_crossing_is_two_degrees_not_358():
    from nasolve.topostitch_preview import _dihedral,_circular_difference
    def points(degrees):
        angle=math.radians(degrees)
        return [(0.,1.,0.),(0.,0.,0.),(1.,0.,0.),(1.,math.cos(angle),math.sin(angle))]
    before=_dihedral(*points(179));after=_dihedral(*points(-179))
    assert before==pytest.approx(179) and after==pytest.approx(-179)
    assert _circular_difference(after,before)==pytest.approx(2)
    assert _circular_difference(before,after)==pytest.approx(-2)


def test_degenerate_torsion_is_not_assigned_an_arbitrary_angle():
    from nasolve.topostitch_preview import _dihedral
    with pytest.raises(ValueError,match='Degenerate'):
        _dihedral((0,0,0),(1,0,0),(2,0,0),(2,1,0))


def test_extended_torsion_limit_can_reject_with_unchanged_watched_angles():
    from nasolve.topostitch_preview import _audit_links,TrialLimitError
    left={"O3'":(1.,1.,-1.),"C3'":(2.,1.,-1.),"C4'":(2.,2.,-2.)}
    right={'P':(0.,0.,0.),"O5'":(0.,0.,1.),'OP1':(1.,0.,0.),'OP2':(0.,1.,0.),"C5'":(1.,0.,1.5)}
    changed={**right,"C5'":(0.,1.,1.5)}
    trial={'schema_version':2,'max_backbone_bond_change_angstrom':.001,'max_backbone_angle_change_degrees':.001,'max_backbone_torsion_change_degrees':1}
    with pytest.raises(TrialLimitError,match='torsion 90'):
        _audit_links([('a','b')],{'a':left,'b':right},{'a':left,'b':changed},trial)


def test_extended_preview_refuses_missing_atoms_before_creating_output(tmp_path):
    paths=setup_preview(tmp_path)
    change_trial(paths,schema_version=2,max_backbone_torsion_change_degrees=180.)
    with pytest.raises(ValueError,match='Missing extended backbone audit atom'):
        build(paths,tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()


@pytest.mark.parametrize('value',[0,181,True,float('nan')])
def test_extended_preview_requires_explicit_finite_circular_bound(tmp_path,value):
    paths=setup_preview(tmp_path,extended=True)
    change_trial(paths,schema_version=2,max_backbone_torsion_change_degrees=value)
    with pytest.raises(ValueError):build(paths,tmp_path/'rejected')
    assert not (tmp_path/'rejected').exists()


def test_extended_zero_trial_and_relocation_preserve_frozen_inputs(tmp_path):
    paths=setup_preview(tmp_path,extended=True,rotation=(0,0,0),translation=(0,0,0))
    change_trial(paths,schema_version=2,max_backbone_torsion_change_degrees=1.)
    original=paths[0].read_bytes();report=build(paths,tmp_path/'old')
    assert (tmp_path/'old/candidate.pdb').read_bytes()==original
    assert report['backbone_audit']['max_torsion_change_degrees']==0
    (tmp_path/'old').rename(tmp_path/'moved')
    for p in paths[:4]:p.unlink()
    assert load_bend_preview(tmp_path/'moved')==report
