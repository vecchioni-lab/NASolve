"""Identity observations must not confuse centers, lattice images or labels."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from nasolve.topostitch_images import (
    _Budget, _orbit_contacts, _selected_overlap, inspect_periodic_image_identity,
)
from nasolve.topostitch_periodic import _crystal
from nasolve.topostitch_inspect import main
from .test_topostitch_inspect import inputs


CELL=(10,10,10,90,90,90)


def orbit(points,cell=CELL,group='P 1',tolerance=.01,budget=100_000):
    pytest.importorskip('gemmi')
    gemmi,unit,sg=_crystal(cell,group)
    return _orbit_contacts(points,unit,sg,gemmi,tolerance,_Budget(budget))


def overlap(points,left,right,operator,cell=CELL,group='P 1'):
    pytest.importorskip('gemmi')
    gemmi,unit,sg=_crystal(cell,group)
    return _selected_overlap(points,left,right,gemmi.Op(operator),unit,gemmi,.01,_Budget(100_000))


def test_self_stabilizer_uses_atoms_not_a_centroid():
    records=orbit([(0,2,0),(1,2,3),(-1,2,-3)],group='P 2')
    self_records=[r for r in records if r['source_atom_index']==r['target_atom_index']]
    assert len(self_records)==1
    assert self_records[0]['source_atom_index']==0
    assert self_records[0]['target_image']['operator_xyz']=='-x,y,-z'
    assert self_records[0]['relation']=='SELF_STABILIZER_OBSERVATION'
    # A center on the axis does not imply the off-axis atom is fixed. The two
    # off-axis source labels instead have a coordinate-orbit ambiguity.
    alias=[r for r in records if r['source_atom_index']==1 and r['target_atom_index']==2]
    assert len(alias)==1 and alias[0]['relation']=='DISTINCT_SOURCE_ORBITS_COINCIDE'


def test_screw_axis_has_no_spurious_fixed_atom():
    assert orbit([(0,0,0)],cell=(10,10,40,90,90,90),group='P 43')==[]
    records=orbit([(3,-2,10),(2,3,0)],cell=(10,10,40,90,90,90),group='P 43')
    record,=records
    assert record['target_image']['operator_xyz']=='y,-x,z+1/4'
    assert record['distance_angstrom']==pytest.approx(0,abs=1e-10)
    assert record['relation']=='DISTINCT_SOURCE_ORBITS_COINCIDE'


def test_centering_translation_is_an_atom_orbit_relation():
    records=orbit([(6,7,8),(1,2,3)],group='I 2 2 2')
    record,=records
    assert record['target_image']['operator_xyz']=='x+1/2,y+1/2,z+1/2'


def test_large_outside_cell_translation_is_retained_exactly():
    record,=orbit([(101,2,3),(-89,2,3)])
    assert record['target_image']['operator_xyz']=='x+19,y,z'
    assert record['target_image']['lattice_translation']==[19,0,0]
    assert overlap([(101,2,3),(-89,2,3)],[0],[1],'x,y,z')==[]
    selected,=overlap([(101,2,3),(-89,2,3)],[0],[1],'x+19,y,z')
    assert selected['relation']=='DISTINCT_SOURCE_ATOMS_COINCIDE'


def test_nonorthogonal_metric_and_boundary_tolerance():
    gemmi=pytest.importorskip('gemmi')
    cell=(10,11,12,80,75,20);unit=gemmi.UnitCell(*cell)
    shifted=tuple(unit.orthogonalize(gemmi.Fractional(2,-3,1)))
    p=(1.,2.,3.);q=tuple(p[i]-shifted[i]+(.004 if i==0 else 0) for i in range(3))
    record,=orbit([p,q],cell=cell)
    assert record['target_image']['lattice_translation']==[2,-3,1]
    assert record['distance_angstrom']==pytest.approx(.004)
    assert orbit([p,q],cell=cell,tolerance=.002)==[]


def test_distinct_selected_images_can_share_center():
    points=[(-1,0,0),(1,0,0),(0,-1,0),(0,1,0)]
    assert overlap(points,[0,1],[2,3],'x,y,z')==[]
    assert orbit(points)==[]
    checked=capacity(points,[0,1],[2,3],['a','b'],'x,y,z')
    assert checked['one_partner_in_selected_scope'] and not checked['geometry_validated']


def test_self_image_overlap_is_not_a_new_partner():
    record,=overlap([(0,2,0)],[0],[0],'-x,y,-z',group='P 2')
    assert record['relation']=='SAME_SOURCE_ATOM_IMAGE'
    assert overlap([(1,2,3)],[0],[0],'-x,y,-z',group='P 2')==[]


def test_bounded_orbit_work_fails_without_a_partial_result():
    with pytest.raises(ValueError,match='budget'):
        orbit([(0,2,0),(1,2,3)],group='P 2',budget=1)
    # Tiny cells require many lattice tests even for one atom.
    with pytest.raises(ValueError,match='budget'):
        orbit([(0,0,0)],cell=(.001,.001,.001,90,90,90),budget=100)


def test_coincidence_output_budget_is_not_silently_truncated(monkeypatch):
    monkeypatch.setattr('nasolve.topostitch_images._MAX_COINCIDENCES',1)
    with pytest.raises(ValueError,match='record budget'):
        orbit([(0,0,0),(0,0,0),(0,0,0)])


def inspect(model,manifest,**kwargs):
    from nasolve.topostitch_inspect import load_end_assignments
    digest,assignments,_=load_end_assignments(manifest)
    return inspect_periodic_image_identity(model,assignments,expected_sha256=digest,
        max_distance_angstrom=15,candidate_index=0,**kwargs)


def test_public_api_is_deterministic_and_relocatable(tmp_path):
    pytest.importorskip('gemmi')
    old=tmp_path/'old';old.mkdir();model,manifest,_=inputs(old)
    first=inspect(model,manifest)
    new=tmp_path/'new';shutil.move(old,new)
    second=inspect(new/model.name,new/manifest.name)
    assert first==second
    audit=first['selected_image_identity']
    assert audit['atom_tests']>0 and audit['atoms']
    assert audit['physical_identity_validated'] is False and audit['identities_merged'] is False
    assert str(tmp_path) not in json.dumps(first,allow_nan=False)


@pytest.mark.parametrize('kwargs',[
    {'coincidence_tolerance_angstrom':0},{'coincidence_tolerance_angstrom':.1},
    {'coincidence_tolerance_angstrom':float('nan')},{'coincidence_tolerance_angstrom':True},
    {'max_atom_tests':0},{'max_atom_tests':True},
])
def test_invalid_bounds_fail_before_source_access(tmp_path,kwargs):
    with pytest.raises(ValueError):
        inspect_periodic_image_identity(tmp_path/'missing',[],expected_sha256='a'*64,
            max_distance_angstrom=15,candidate_index=0,**kwargs)


@pytest.mark.parametrize('extra,message',[
    (['--audit-image','0'],'requires --periodic'),
    (['--periodic','--audit-image','-1'],'candidate_index'),
    (['--periodic','--audit-image','999'],'candidate_index'),
    (['--periodic','--audit-image','0','--max-atom-tests','1'],'budget'),
])
def test_cli_fails_without_partial_json(tmp_path,capsys,extra,message):
    pytest.importorskip('gemmi')
    model,manifest,_=inputs(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main([str(model),str(manifest),'--radius','15',*extra])
    assert exc.value.code==2
    captured=capsys.readouterr()
    assert captured.out=='' and message in captured.err


def test_image_audit_composes_with_contacts_and_pairings(tmp_path,capsys):
    pytest.importorskip('gemmi');pytest.importorskip('restraints')
    model,manifest,_=inputs(tmp_path)
    assert main([str(model),str(manifest),'--radius','15','--periodic','--contacts','--pairings','--audit-image','0'])==0
    report=json.loads(capsys.readouterr().out)
    assert report['selected_image_identity'] and report['contact_assessment'] and report['pairing_alternatives']
    assert report['selected_image_identity']['runtime_authority'] is False


def test_extra_atom_with_bad_occupancy_keeps_audit_unassessed(tmp_path,capsys):
    pytest.importorskip('gemmi')
    from .helpers import pdb_record
    model,manifest,value=inputs(tmp_path)
    model.write_text(model.read_text().replace('\n','\n'+pdb_record('ATOM',999,'P','DG','A',1,occupancy=float('nan')),1))
    value['model_sha256']=hashlib.sha256(model.read_bytes()).hexdigest();manifest.write_text(json.dumps(value))
    assert main([str(model),str(manifest),'--radius','15','--periodic','--audit-image','0'])==0
    audit=json.loads(capsys.readouterr().out)['selected_image_identity']
    assert audit['assessment']=='UNASSESSED'
    assert audit['issues'][0]['code']=='UNUSABLE_OCCUPANCY'
    assert audit['selected_atom_sets_disjoint'] is None


def test_near_coincidences_are_not_transitively_merged():
    records=orbit([(0,0,0),(.006,0,0),(.012,0,0)])
    assert [(r['source_atom_index'],r['target_atom_index']) for r in records]==[(0,1),(1,2)]


def test_partial_occupancy_keeps_distinct_coordinates_under_review(tmp_path):
    pytest.importorskip('gemmi')
    model,manifest,value=inputs(tmp_path)
    model.write_text(model.read_text().replace('  1.00','  0.50',1))
    value['model_sha256']=hashlib.sha256(model.read_bytes()).hexdigest();manifest.write_text(json.dumps(value))
    audit=inspect(model,manifest)['selected_image_identity']
    assert audit['assessment']=='COINCIDENCE_OR_OCCUPANCY_REVIEW'
    assert audit['physical_identity_validated'] is False
    assert audit['single_edge_capacity']['assessment']=='CAPACITY_REVIEW_REQUIRED'


def capacity(points,left,right,ends,operator,group='P 1'):
    from nasolve.topostitch_images import _single_edge_capacity
    from nasolve.topostitch_periodic import _image_record
    gemmi,unit,sg=_crystal(CELL,group)
    aliases=orbit(points,group=group);overlaps=overlap(points,left,right,operator,group=group)
    audit=dict(source_model_sha256='a'*64,inputs=dict(ends=ends,target_image=_image_record(gemmi.Op(operator),gemmi),
        coincidence_tolerance_angstrom=.01),end_atom_indices=dict(source=left,target=right),
        assessment='COINCIDENCE_OR_OCCUPANCY_REVIEW' if aliases or overlaps else 'SELECTED_COORDINATES_DISTINCT',
        orbit_contacts=aliases,selected_image_overlaps=overlaps)
    return _single_edge_capacity(audit,gemmi)


def test_single_periodic_edge_keeps_both_unwrapped_reciprocal_neighbors():
    r=capacity([(1.,2.,3.),(3.,4.,5.)],[0],[1],['a','b'],'x+2,y,z')
    assert r['assessment']=='ONE_PARTNER_IN_SELECTED_SCOPE'
    assert [(x['end_id'],x['partner_count'],x['neighbors'][0]['image']['operator_xyz']) for x in r['incidence']]==[
        ('a',1,'x+2,y,z'),('b',1,'x-2,y,z')]
    assert not r['global_assignment_validated'] and not r['full_molecular_identity_validated']
    assert not r['connection_accepted']


@pytest.mark.parametrize('operator,group,partners',[
    ('-x,y,-z','P 2',1),
    ('x+1,y,z','P 1',2),
    ('x+1/2,y+1/2,z','C 2',2),
    ('y,-x,z+1/4','P 43',2),
])
def test_generic_self_edge_counts_distinct_forward_and_inverse_images(operator,group,partners):
    r=capacity([(1.,2.,3.)],[0],[0],['a','a'],operator,group)
    assert r['incidence'][0]['partner_count']==partners
    assert r['one_partner_in_selected_scope']==(partners==1)
    assert r['assessment']==('ONE_PARTNER_IN_SELECTED_SCOPE' if partners==1 else 'MULTIPLE_PARTNERS_IN_SELECTED_SCOPE')


def test_centering_inverse_is_not_identified_modulo_the_cell():
    r=capacity([(1.,2.,3.)],[0],[0],['a','a'],'x+1/2,y+1/2,z','C 2')
    images=[n['image'] for n in r['incidence'][0]['neighbors']]
    assert images[0]['symmetry_operation']==images[1]['symmetry_operation']
    assert images[0]['lattice_translation']!=images[1]['lattice_translation']
    assert r['assessment']=='MULTIPLE_PARTNERS_IN_SELECTED_SCOPE'


def test_stabilizer_or_shared_source_labels_cannot_establish_capacity():
    special=capacity([(0.,2.,0.)],[0],[0],['a','a'],'-x,y,-z','P 2')
    assert special['assessment']=='CAPACITY_REVIEW_REQUIRED'
    shared=capacity([(1.,2.,3.)],[0],[0],['a','b'],'x+1,y,z')
    assert shared['assessment']=='CAPACITY_REVIEW_REQUIRED'
    assert 'DISTINCT_END_LABELS_SHARE_SOURCE_ATOMS' in shared['issues']
    identity=capacity([(1.,2.,3.)],[0],[0],['a','a'],'x,y,z')
    assert 'IDENTITY_SELF_EDGE' in identity['issues']


def test_public_image_audit_binds_capacity_without_connection_approval(tmp_path):
    pytest.importorskip('gemmi')
    model,manifest,_=inputs(tmp_path);audit=inspect(model,manifest)['selected_image_identity']
    report=audit.pop('single_edge_capacity')
    expected=hashlib.sha256(json.dumps(audit,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    assert report['coordinate_evidence_sha256']==expected
    assert report['source_model_sha256']==audit['source_model_sha256']
    assert report['target_image']==audit['inputs']['target_image']
    assert not report['connection_accepted'] and not report['runtime_authority']


def model_orbits(path, **kwargs):
    from nasolve.topostitch_images import inspect_model_orbit_identity
    return inspect_model_orbit_identity(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), **kwargs)


def model_orbit_fixture(tmp_path, *, occupancy=1., alternate=False, group='P 1'):
    from .helpers import pdb_record
    from .test_topostitch_periodic import cryst1
    rows = [pdb_record('ATOM', 17, "O3'", 'DA', 'A', 1, x=1, y=2, z=3),
            pdb_record('HETATM', 5, 'O', 'HOH', 'W', 9, x=11, y=2, z=3, occupancy=occupancy)]
    if alternate:
        rows[1] = rows[1][:16]+'A'+rows[1][17:]
    path=tmp_path/'model.pdb';path.write_text(cryst1(CELL, group)+''.join(rows)+'END\n')
    return path


def test_complete_model_orbits_include_water_and_preserve_source_record_order(tmp_path):
    pytest.importorskip('gemmi')
    path=model_orbit_fixture(tmp_path);before=path.read_bytes()
    report=model_orbits(path)
    assert [a['identity']['atom_name'] for a in report['atoms']] == ["O3'", 'O']
    assert [a['source_atom_index'] for a in report['atoms']] == [0, 1]
    assert report['atoms'][1]['record_type'] == 'HETATM'
    contact,=report['orbit_contacts']
    assert contact['target_image']['operator_xyz'] == 'x-1,y,z'
    assert contact['source_atom_index'] == 0 and contact['target_atom_index'] == 1
    assert report['assessment'] == 'MODEL_ORBIT_REVIEW'
    assert not report['identities_merged'] and not report['physical_identity_validated']
    assert not report['asu_cut_validated'] and report['changes'] == []
    assert path.read_bytes() == before
    assert str(tmp_path) not in json.dumps(report)


@pytest.mark.parametrize('occupancy,alternate,codes', [
    (.5, False, {'PARTIAL_OCCUPANCY'}), (0., False, {'UNUSABLE_OCCUPANCY'}),
    (float('nan'), False, {'UNUSABLE_OCCUPANCY'}), (1., True, {'ALTERNATE_CONFORMER'}),
])
def test_model_orbits_observe_coordinates_but_never_hide_occupancy_or_altloc_uncertainty(tmp_path, occupancy, alternate, codes):
    pytest.importorskip('gemmi')
    report=model_orbits(model_orbit_fixture(tmp_path, occupancy=occupancy, alternate=alternate))
    assert {r['code'] for r in report['issues']} == codes
    assert report['orbit_contacts'] and report['assessment'] == 'MODEL_ORBIT_REVIEW'
    assert len(report['atoms']) == 2
    json.dumps(report, allow_nan=False)


def test_model_orbits_distinguish_special_position_from_distinct_source_alias(tmp_path):
    pytest.importorskip('gemmi')
    from .helpers import pdb_record
    from .test_topostitch_periodic import cryst1
    path=tmp_path/'special.pdb';path.write_text(cryst1(CELL, 'P 2')+
        pdb_record('HETATM', 1, 'MG', 'MG', 'M', 1, x=0, y=2, z=0, element='MG'))
    report=model_orbits(path);contact,=report['orbit_contacts']
    assert contact['relation'] == 'SELF_STABILIZER_OBSERVATION'
    assert contact['source_atom_index'] == contact['target_atom_index'] == 0
    assert report['assessment'] == 'MODEL_ORBIT_REVIEW'


def test_complete_model_orbit_report_is_relocatable_and_keeps_absent_old_path(tmp_path):
    pytest.importorskip('gemmi')
    source=tmp_path/'original';source.mkdir();path=model_orbit_fixture(source)
    # Remove the translated coincidence while retaining both atom records.
    path.write_text(path.read_text().replace('  11.000','  12.000'))
    before=model_orbits(path);assert before['assessment']=='PRESENT_MODEL_COORDINATES_DISTINCT'
    moved=tmp_path/'moved';source.rename(moved);assert not source.exists()
    assert model_orbits(moved/'model.pdb') == before


def test_model_orbit_budget_and_source_hash_fail_without_partial_report(tmp_path):
    pytest.importorskip('gemmi')
    from nasolve.topostitch_images import inspect_model_orbit_identity
    path=model_orbit_fixture(tmp_path)
    with pytest.raises(ValueError, match='budget'):model_orbits(path,max_atom_tests=1)
    with pytest.raises(ValueError, match='checksum'):
        inspect_model_orbit_identity(path,expected_sha256='a'*64)


def test_model_orbits_preserve_ambiguous_ter_split_site_as_review(tmp_path):
    pytest.importorskip('gemmi')
    from .helpers import pdb_record
    from .test_topostitch_periodic import cryst1
    path=tmp_path/'split.pdb';path.write_text(cryst1(CELL)+
        pdb_record('ATOM',1,"C3'",'DA','A',1,x=1,y=2,z=3)+'TER\n'+
        pdb_record('ATOM',2,"O3'",'DA','A',1,x=2,y=3,z=4))
    report=model_orbits(path)
    assert [r['code'] for r in report['issues']] == ['AMBIGUOUS_COORDINATE_SITE']*2
    assert report['assessment']=='MODEL_ORBIT_REVIEW'


def test_model_orbits_recheck_source_bytes_before_returning(tmp_path, monkeypatch):
    pytest.importorskip('gemmi')
    import nasolve.topostitch_images as module
    path=model_orbit_fixture(tmp_path);original=module._orbit_contacts
    def change(*args):
        result=original(*args);path.write_bytes(path.read_bytes()+b'REMARK drift\n');return result
    monkeypatch.setattr(module,'_orbit_contacts',change)
    with pytest.raises(ValueError, match='changed during'):model_orbits(path)
