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
