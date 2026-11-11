"""Cartesian geometry reports use source connectivity, never named PDU atoms."""
from copy import deepcopy
import pytest
from tests.test_cif_plane_coverage import values,plane,write


def fixture(tmp_path,code='XYZ',height=0.,rename=False,missing=False,degenerate=False):
    source=values(code);dictionary=deepcopy(source);plane(dictionary,['C','O','N','R'])
    mapping={n:('X'+str(i) if rename else n) for i,n in enumerate(['C','O','N','R'])}
    for data in (source,dictionary):
        for key,col in data.items():
            if key.endswith('.atom_id') or '.atom_id_' in key:data[key]=[mapping[n] for n in col]
    s=write(tmp_path,source,'source.cif');d=write(tmp_path,dictionary,'dictionary.cif')
    xyz={'C':(0.,0.,0.),'O':(1.,0.,0.),'N':(-.5,1.,0.),'R':(-.5,-1.,height)}
    if degenerate:xyz['N']=(-1.,0.,0.)
    lines=[]
    for site in (1,2):
        for name,point in xyz.items():
            if missing and site==2 and name=='R':continue
            x,y,z=point;name2=mapping[name];element='C' if name in ('C','R') else name
            lines.append(f'HETATM{len(lines)+1:5d} {name2:>4} {code:>3} A{site:4d}    {x+5*site:8.3f}{y:8.3f}{z:8.3f}{1.:6.2f}{20.:6.2f}          {element:>2}\n')
    model=tmp_path/'model.pdb';model.write_text(''.join(lines)+'END\n')
    return s,d,code,model


def review(args):
    from nasolve.cif_plane_geometry import review_trigonal_model_geometry
    return review_trigonal_model_geometry(*args)


@pytest.mark.parametrize('code,rename',[('PDU',False),('XYZ',False),('ZZZ',True)])
def test_every_occurrence_uses_source_connectivity_and_reports_bent_geometry(tmp_path,code,rename):
    args=fixture(tmp_path,code,height=.7,rename=rename);before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in (args[0],args[1],args[3])}
    r=review(args)
    assert r['modeled_sites']==['A:1','A:2'] and len(r['measurements'])==2
    for row in r['measurements']:
        assert row['coverage']=='EXPLICIT_PLANE_PRESENT'
        assert row['geometry']['absolute_normalized_volume']>.4
        assert max(v['absolute_out_of_plane_degrees'] for v in row['geometry']['bond_elevations'])>30
        assert row['geometry']['angle_sum_degrees']<360
    assert not r['automatic_adoption'] and r['scientific_approval']=='NOT_RUN'
    assert r==review(args) and all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())


def test_planar_is_descriptive_and_missing_atoms_remain_visible(tmp_path):
    r=review(fixture(tmp_path,missing=True));a,b=r['measurements']
    assert a['geometry']['absolute_normalized_volume']==0
    assert a['geometry']['angle_sum_degrees']==pytest.approx(360)
    assert a['geometry']['status']=='DESCRIPTIVE'
    assert b['geometry']==dict(status='UNAVAILABLE',missing_atoms=['R'])
    assert r['status']=='REVIEW'


def test_collinear_shape_cannot_pass_by_having_zero_volume(tmp_path):
    r=review(fixture(tmp_path,degenerate=True));g=r['measurements'][0]['geometry']
    assert g['absolute_normalized_volume']==0 and g['status']=='DEGENERATE'
    assert any(v['absolute_out_of_plane_degrees'] is None for v in g['bond_elevations'])


@pytest.mark.parametrize('defect',['model_record','altloc','duplicate','element','nonfinite'])
def test_ambiguous_or_incompatible_model_is_refused(tmp_path,defect):
    args=fixture(tmp_path);p=args[3];lines=p.read_text().splitlines(keepends=True)
    if defect=='model_record':lines.insert(0,'MODEL        1\n')
    elif defect=='altloc':lines[0]=lines[0][:16]+'A'+lines[0][17:]
    elif defect=='duplicate':lines.insert(1,lines[0])
    elif defect=='element':lines[0]=lines[0][:76]+' N'+lines[0][78:]
    else:lines[0]=lines[0][:30]+'     nan'+lines[0][38:]
    p.write_text(''.join(lines))
    with pytest.raises(ValueError):review(args)


@pytest.mark.parametrize('state',['charged','chiral','saturated','absent'])
def test_no_planarity_assumption_for_unsupported_source_or_absent_model(tmp_path,state):
    args=list(fixture(tmp_path));v=values()
    if state=='charged':v['_chem_comp_atom.charge'][0]='1'
    elif state=='chiral':v['_chem_comp_atom.pdbx_stereo_config'][0]='R'
    elif state=='saturated':v['_chem_comp_bond.value_order']=['SING']*3
    else:args[3].write_text(args[3].read_text().replace('XYZ','OTH'))
    if state!='absent':
        args[0]=write(tmp_path,v,'source.cif');args[1]=write(tmp_path,v,'dictionary.cif')
    r=review(args);assert r['status']=='UNASSESSED' and not r['measurements']


def test_relocation_and_changed_inputs(tmp_path,monkeypatch):
    import nasolve.cif_plane_geometry as module
    old=tmp_path/'old';old.mkdir();args=fixture(old);expected=review(args)
    new=old.rename(tmp_path/'new');args=tuple(new/p.name if hasattr(p,'name') else p for p in args)
    assert not old.exists() and review(args)==expected
    original=module._pdb_inventory
    def changed(path):
        r=original(path);path.write_text(path.read_text()+'REMARK changed\n');return r
    monkeypatch.setattr(module,'_pdb_inventory',changed)
    with pytest.raises(ValueError,match='input changed'):review(args)


def test_supported_zero_padded_residue_numbers_keep_the_same_sites(tmp_path):
    args=fixture(tmp_path);expected=review(args);p=args[3]
    p.write_text(''.join(line[:22]+f'{int(line[22:26]):04d}'+line[26:] if line.startswith('HETATM') else line for line in p.read_text().splitlines(keepends=True)))
    result=review(args)
    assert result['modeled_sites']==expected['modeled_sites']
    assert result['measurements']==expected['measurements']


def test_analytic_elevation_and_rigid_frame_invariance():
    from math import sqrt
    from nasolve.cif_plane_geometry import _measure
    xyz={'C':[0.,0.,0.],'A':[1.,0.,0.],'B':[0.,1.,0.],'D':[-sqrt(3)/2,0.,.5]}
    base=_measure(xyz,'C',['A','B','D'])
    assert base['absolute_normalized_volume']==pytest.approx(.5)
    assert base['angle_sum_degrees']==pytest.approx(330.)
    assert base['bond_elevations'][-1]['absolute_out_of_plane_degrees']==pytest.approx(30.)
    for sign in (-1,1):
        transformed={n:[p[2]+2.,sign*p[0]-3.,p[1]+4.] for n,p in xyz.items()}
        result=_measure(transformed,'C',['A','B','D'])
        assert result['absolute_normalized_volume']==pytest.approx(base['absolute_normalized_volume'])
        assert [r['absolute_out_of_plane_degrees'] for r in result['bond_elevations']]==pytest.approx([r['absolute_out_of_plane_degrees'] for r in base['bond_elevations']])
