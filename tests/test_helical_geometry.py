from dataclasses import replace
from hashlib import sha256
import json
import math
import subprocess
import sys

import pytest

from nasolve.helical_geometry import HelicalSite, DeclaredPair, PairedRegion, inspect_phosphate_spans
from .helpers import pdb_record


def atom(chain, number, xyz, *, name='P', code='DA', alt='', insertion='', occupancy=1):
    line = pdb_record('ATOM', 1, name, code, chain, number, x=xyz[0], y=xyz[1], z=xyz[2], occupancy=occupancy)
    return line[:16]+alt.ljust(1)+line[17:26]+insertion.ljust(1)+line[27:]


def region():
    return PairedRegion('test-edge', (
        DeclaredPair('pair-1', HelicalSite('A', 1, 'DA'), HelicalSite('B', 9, 'IMC'), role='flank'),
        DeclaredPair('pair-2', HelicalSite('A', 2, 'DC'), HelicalSite('B', 8, 'DG'), break_before=True),
    ))


def coordinates(transform=lambda xyz: xyz):
    return ''.join(atom(chain, n, transform(xyz), code=code) for chain,n,xyz,code in [
        ('A',1,(1,2,3),'DA'), ('B',9,(4,6,3),'IMC'),
        ('A',2,(0,0,7),'DC'), ('B',8,(0,12,7),'DG')])


def inspect(tmp_path, text=None, declaration=None, **kwargs):
    path=tmp_path/'input.pdb';path.write_text(coordinates() if text is None else text)
    pin=sha256(path.read_bytes()).hexdigest()
    result=inspect_phosphate_spans(path, declaration or region(), expected_model_sha256=pin, **kwargs)
    assert sha256(path.read_bytes()).hexdigest()==pin
    return result


def test_bound_ordered_regions_and_distinct_width_quantities(tmp_path):
    report=inspect(tmp_path, include_half_span=True)
    assert [r['distance_angstrom'] for r in report['pairs']]==[5,12]
    assert [r['half_span_angstrom'] for r in report['pairs']]==[2.5,6]
    assert report['coverage']=={'declared_pairs':2,'measured_pairs':2,'unavailable_pairs':0}
    assert report['region']['pairs'][0]['strand_ii']['component']=='IMC'
    assert report['region']['pairs'][0]['role']=='flank'
    assert report['region']['pairs'][1]['break_before'] is True
    assert report['axis_radii']['status']=='NOT_MEASURED'
    assert report['simple_step_twist']['status']=='NOT_MEASURED'
    assert report['runtime_authority'] is False
    assert report['pairing_validated'] is False
    assert report['source']['anchor']=='model_directory'
    assert str(tmp_path) not in json.dumps(report)
    assert json.loads(json.dumps(report,allow_nan=False))==report


def test_rigid_movement_and_pair_order_do_not_change_spans(tmp_path):
    a=inspect(tmp_path)
    b=inspect(tmp_path, coordinates(lambda xyz:(-xyz[1]+7,xyz[0]-9,xyz[2]+17)))
    swapped=replace(region(), pairs=tuple(replace(p,strand_i=p.strand_ii,strand_ii=p.strand_i) for p in region().pairs))
    c=inspect(tmp_path,declaration=swapped)
    for result in (b,c):
        assert [r['distance_angstrom'] for r in result['pairs']]==[5,12]
    assert 'half_span_angstrom' not in a['pairs'][0]
    assert a['source']['sha256']!=b['source']['sha256']
    assert a['region_sha256']!=c['region_sha256']


def test_single_pair_displacement_is_local(tmp_path):
    text=coordinates().replace('   4.000   6.000   3.000','   4.000  10.000   3.000')
    r=inspect(tmp_path,text)
    assert r['pairs'][0]['distance_angstrom']==pytest.approx(math.sqrt(73))
    assert r['pairs'][1]['distance_angstrom']==12


@pytest.mark.parametrize('fault,reason', [
    ('absent','MISSING_RESIDUE'),('no_p','MISSING_PHOSPHATE'),
    ('duplicate','AMBIGUOUS_PHOSPHATE'),('zero_q','UNUSABLE_OCCUPANCY'),
    ('component','COMPONENT_MISMATCH'),('alt','ALTERNATE_CONFORMER_REQUIRED'),
    ('ter','AMBIGUOUS_RESIDUE'),
])
def test_missing_or_ambiguous_phosphate_is_local_not_zero(tmp_path,fault,reason):
    lines=coordinates().splitlines(keepends=True)
    if fault=='absent':lines.pop(1)
    if fault=='no_p':lines[1]=lines[1][:12]+" C1'"+lines[1][16:]
    if fault=='duplicate':lines.insert(1,lines[1])
    if fault=='zero_q':lines[1]=lines[1][:54]+'  0.00'+lines[1][60:]
    if fault=='component':lines[1]=lines[1][:17]+' DT'+lines[1][20:]
    if fault=='alt':lines[1]=lines[1][:16]+'A'+lines[1][17:]
    if fault=='ter':lines.extend(['TER\n',lines[1]])
    r=inspect(tmp_path,''.join(lines),include_half_span=True)
    first,second=r['pairs']
    assert first['distance_angstrom'] is None and first['half_span_angstrom'] is None
    assert first['phosphates'][1]['reason']==reason
    assert first['phosphates'][0]['status']=='AVAILABLE'
    assert second['distance_angstrom']==12
    assert r['coverage']['measured_pairs']==1


def test_explicit_altloc_and_insertion_choose_exact_atom(tmp_path):
    a=HelicalSite('A',-2,'DA',insertion_code='J',altloc='B')
    b=HelicalSite('',3,'DT')
    declaration=PairedRegion('alt', (DeclaredPair('p',a,b),))
    text=atom('A',-2,(50,0,0),alt='A',insertion='J')+atom('A',-2,(3,0,0),alt='B',insertion='J')+atom('',3,(0,0,0),code='DT')
    r=inspect(tmp_path,text,declaration)
    assert r['pairs'][0]['distance_angstrom']==3
    assert r['pairs'][0]['phosphates'][0]['actual_altloc']=='B'
    absent=replace(declaration,pairs=(replace(declaration.pairs[0],strand_i=replace(a,altloc='C')),))
    assert inspect(tmp_path,text,absent)['pairs'][0]['phosphates'][0]['reason']=='MISSING_CONFORMER'


def test_shared_phosphate_of_explicit_conformer(tmp_path):
    a=HelicalSite('A',1,'DA',altloc='B')
    declaration=PairedRegion('alt', (DeclaredPair('p',a,HelicalSite('B',1,'DT')),))
    text=atom('A',1,(3,0,0))+atom('A',1,(4,0,0),name="C1'",alt='B')+atom('B',1,(0,0,0),code='DT')
    assert inspect(tmp_path,text,declaration)['pairs'][0]['distance_angstrom']==3


@pytest.mark.parametrize('factory', [
 lambda:HelicalSite('A',True,'DA'),lambda:HelicalSite('A',1,'DA',operator_xyz='x+1,y,z'),
 lambda:HelicalSite('A',1,'DA',altloc='AB'),lambda:HelicalSite('A',1,'bad name'),
 lambda:PairedRegion('x',region().pairs,model_index=1),lambda:PairedRegion('x',()),
 lambda:PairedRegion('x',(region().pairs[0],region().pairs[0])),
 lambda:DeclaredPair('p',HelicalSite('A',1,'DA'),HelicalSite('A',1,'DA')),
 lambda:replace(region().pairs[0],break_before=1),lambda:replace(region().pairs[0],role='unknown'),
])
def test_invalid_assignment_and_unsupported_images_refuse(factory):
    with pytest.raises((ValueError,TypeError)):factory()


def test_same_physical_site_cannot_masquerade_as_two_components():
    with pytest.raises(ValueError):
        DeclaredPair('p',HelicalSite('A',1,'DA'),HelicalSite('A',1,'DT'))


def test_missing_pair_is_not_bridged_or_reordered(tmp_path):
    r=inspect(tmp_path,coordinates().replace('IMC B   9','IMC B  10'))
    assert [p['pair_id'] for p in r['pairs']]==['pair-1','pair-2']
    assert r['pairs'][0]['distance_angstrom'] is None
    assert r['pairs'][1]['distance_angstrom']==12


def test_pin_and_multi_model_refuse(tmp_path):
    p=tmp_path/'input.pdb';p.write_text(coordinates())
    with pytest.raises(ValueError,match='hash'):inspect_phosphate_spans(p,region(),expected_model_sha256='0'*64)
    p.write_text('MODEL        1\n'+coordinates()+'ENDMDL\nMODEL        2\n'+coordinates()+'ENDMDL\n')
    with pytest.raises(ValueError,match='Multiple'):inspect_phosphate_spans(p,region(),expected_model_sha256=sha256(p.read_bytes()).hexdigest())


def test_original_path_gone_relocation_and_cli(tmp_path):
    old=tmp_path/'old';old.mkdir();p=old/'model.pdb';p.write_text(coordinates())
    pin=sha256(p.read_bytes()).hexdigest();expected=inspect_phosphate_spans(p,region(),expected_model_sha256=pin)
    from dataclasses import asdict
    (old/'region.json').write_text(json.dumps(asdict(region())))
    new=tmp_path/'new';old.rename(new);assert not old.exists()
    assert inspect_phosphate_spans(new/'model.pdb',region(),expected_model_sha256=pin)==expected
    cp=subprocess.run([sys.executable,'-B','-m','nasolve.helical_geometry','--model',str(new/'model.pdb'),'--region',str(new/'region.json'),'--sha256',pin],capture_output=True,text=True,check=True)
    assert json.loads(cp.stdout)==expected


def test_model_change_during_read_refuses(tmp_path,monkeypatch):
    import nasolve.helical_geometry as module
    p=tmp_path/'input.pdb';p.write_text(coordinates());pin=sha256(p.read_bytes()).hexdigest()
    reader=module._read_atoms
    def mutate(payload):
        p.write_text(coordinates()+'REMARK changed\n')
        return reader(payload)
    monkeypatch.setattr(module,'_read_atoms',mutate)
    with pytest.raises(ValueError,match='changed during'):
        inspect_phosphate_spans(p,region(),expected_model_sha256=pin)


def test_region_rejects_reused_residue_with_different_logical_label():
    p=region().pairs[0]
    with pytest.raises(ValueError,match='multiple declared pairs'):
        PairedRegion('overlap',(p,replace(p,pair_id='different')))


def test_partial_missing_region_preserves_breaks_and_coverage(tmp_path):
    text=coordinates().replace(' DC A   2',' DC C   2')
    r=inspect(tmp_path,text)
    assert r['pairs'][0]['distance_angstrom']==5
    assert r['pairs'][1]['break_before'] is True
    assert r['pairs'][1]['distance_angstrom'] is None
    assert r['coverage']['unavailable_pairs']==1


def test_zero_span_is_observed_not_accepted(tmp_path):
    text=coordinates().replace('   4.000   6.000   3.000','   1.000   2.000   3.000')
    r=inspect(tmp_path,text)
    assert r['pairs'][0]['status']=='MEASURED' and r['pairs'][0]['distance_angstrom']==0
    assert r['pairing_validated'] is False


@pytest.mark.parametrize('pin',['',None,'A'*64,'x'*64])
def test_invalid_hash_not_accepted(tmp_path,pin):
    with pytest.raises(ValueError,match='hash'):
        inspect_phosphate_spans(tmp_path/'absent',region(),expected_model_sha256=pin)
