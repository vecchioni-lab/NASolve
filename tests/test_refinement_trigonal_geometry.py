"""Source-selected shape and actual plane membership remain distinct reports."""
from copy import deepcopy
from hashlib import sha256
from unittest.mock import patch
import pytest
from tests.test_cif_plane_geometry import fixture
from nasolve.cif_construction_provenance import _pdb_inventory
from nasolve.cif_refinement_sites import validate_snapshot, unavailable


def observed(tmp_path, *, rename=False, height=.7, plane=True):
    source, dictionary, code, model = fixture(tmp_path,code='XYZ',rename=rename,height=height)
    atoms=[]
    for key,row in _pdb_inventory(model).items():
        chain,resseq,icode,altloc,name=key;i=len(atoms)
        atoms.append(dict(i_seq=i,atom_id=name,label=str(i),identity=dict(model_id='',chain_id=chain,resseq=resseq,icode=icode,altloc=altloc,resname=code),element=row['element'],xyz=list(row['xyz']),occupancy=1.))
    sites=[dict(site='A:1',component=code),dict(site='A:2',component=code)]
    planes=[dict(i_seqs=list(range(start,start+4)),atoms=[str(i)for i in range(start,start+4)],weights=[2500.]*4,origin_id=0)for start in (0,4)]if plane else[]
    kinds=('bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity')
    details={k:planes if k=='planarity'else[]for k in kinds}
    observation=dict(policy_id='native-refinement-selected-sites-v1',status='OBSERVED',sites=sites,scope='ACTUAL_NATIVE_MANAGER_INTRA_SITE_HEAVY_ATOMS',coordinate_precision='FULL_NATIVE',model_state_sha256='a'*64,full_atom_count=len(atoms),atoms=atoms,monomer_mappings=dict(rows=[dict(site=s['site'],metadata=dict(effective_definition=dict(bonds=[])))for s in sites]),geometry=dict(proxy_details=details,full_proxy_counts={k:len(v)for k,v in details.items()}),definition_binding='EXACT_OBSERVED_SUMMARY_OBJECT',scientific_approval='NOT_RUN')
    validate_snapshot(observation,sites,[a['label']for a in atoms])
    return {'A:1':(source,code),'A:2':(source,code)},observation,model


def review(projections, observation):
    from nasolve.cif_plane_geometry import _observed_trigonal_geometry
    return _observed_trigonal_geometry(projections,observation)


@pytest.mark.parametrize('rename',[False,True])
def test_native_shape_is_measured_even_when_plane_is_present(tmp_path,rename):
    projections,obs,model=observed(tmp_path,rename=rename);frozen=deepcopy(obs)
    before={p:(p.read_bytes(),p.stat().st_mtime_ns)for p,_ in projections.values()}
    with patch('subprocess.Popen',side_effect=AssertionError('No native evaluation')):
        result=review(projections,obs)
    assert result['coordinate_precision']=='FULL_NATIVE' and len(result['measurements'])==2
    for row in result['measurements']:
        assert row['coverage']=='CAPTURED_INTRA_SITE_PLANE_PRESENT'
        assert len(row['covering_plane_indices'])==1
        assert row['geometry']['absolute_normalized_volume']>.4
        assert max(v['absolute_out_of_plane_degrees']for v in row['geometry']['bond_elevations'])>30
    assert result['status']=='REVIEW'and result['scientific_approval']=='NOT_RUN'
    assert not result['automatic_adoption']and result['native_residuals']=='NOT_EVALUATED'
    assert obs==frozen and all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())


def test_missing_plane_does_not_imply_bent_geometry_or_missing_alternative_restraints(tmp_path):
    projections,obs,_=observed(tmp_path,height=0.,plane=False);result=review(projections,obs)
    assert not result['native_planes']
    for row in result['measurements']:
        assert row['coverage']=='NO_CAPTURED_INTRA_SITE_PLANE'
        assert row['geometry']['absolute_normalized_volume']==0
        assert row['geometry']['status']=='DESCRIPTIVE'
    assert result['status']=='REVIEW'


def test_native_precision_is_not_replaced_by_rounded_model_coordinates(tmp_path):
    projections,obs,_=observed(tmp_path,height=0.)
    obs['atoms'][3]['xyz'][2]=.000123456789
    r=review(projections,obs)
    assert r['measurements'][0]['geometry']['absolute_normalized_volume']>0
    assert r['measurements'][1]['geometry']['absolute_normalized_volume']==0


@pytest.mark.parametrize('defect',['component','element','duplicate_atom','plane_weights','scope'])
def test_source_or_observed_plane_mismatch_is_not_measured_as_valid(tmp_path,defect):
    projections,obs,_=observed(tmp_path)
    if defect=='component':obs['atoms'][0]['identity']['resname']='OTH'
    elif defect=='element':obs['atoms'][0]['element']='P'
    elif defect=='duplicate_atom':obs['atoms'].append(deepcopy(obs['atoms'][0]))
    elif defect=='plane_weights':obs['geometry']['proxy_details']['planarity'][0]['weights']=[2500.]
    else:obs['sites'][0]['component']='OTH'
    with pytest.raises(ValueError):review(projections,obs)


def test_missing_local_atom_and_degenerate_reference_remain_explicit(tmp_path):
    projections,obs,_=observed(tmp_path,height=0.,plane=False)
    obs['atoms']=[a for a in obs['atoms']if a['i_seq']!=3]
    rows=review(projections,obs)['measurements']
    assert rows[0]['geometry']['status']=='UNAVAILABLE'and rows[0]['geometry']['missing_atoms']==['R']
    assert rows[1]['geometry']['status']=='DESCRIPTIVE'
    # Restore the missing atom in a fresh observation and create a collinear pair.
    projections,obs,_=observed(tmp_path,height=0.,plane=False)
    obs['atoms'][2]['xyz']=[4.,0.,0.]
    assert review(projections,obs)['measurements'][0]['geometry']['status']=='DEGENERATE'


def test_unavailable_observation_and_unsupported_source_remain_unassessed(tmp_path):
    projections,obs,_=observed(tmp_path)
    r=review(projections,unavailable(obs['sites'],'No final observation'))
    assert r['status']=='UNASSESSED'and not r['measurements']
    from tests.test_cif_plane_coverage import values,write
    v=values('XYZ');v['_chem_comp_atom.charge'][0]='1'
    source=write(tmp_path,v,'source.cif')
    r=review(projections,obs)
    assert r['status']=='UNASSESSED'and not r['measurements']
    assert all(r['unassessed_carbon_centres'].values())


def test_exact_owner_read_relocates_and_keeps_historical_triple_report(tmp_path,monkeypatch):
    from tests.test_refinement_parallelity import completed
    from nasolve.refinement_parallelity import read_execution_trigonal_geometry,read_execution_chemistry
    run,result,_,child,_,_=completed(tmp_path,monkeypatch,chemistry='bent')
    args=dict(checkpoint=child['id'],parent=child['parent'])
    old=run.parents[1];moved=tmp_path/'moved';old.rename(moved);run=moved/run.relative_to(old)
    model=run/child['model']['relative_path'];before={p:(p.read_bytes(),p.stat().st_mtime_ns)for p in run.rglob('*')if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('Cold owner read')):
        r=read_execution_trigonal_geometry(run,child['outputs']['parallelity_execution'],model=model,**args)
        assert read_execution_chemistry(run,child['outputs']['parallelity_execution'],model=model,**args)==result.statistics['chemical_geometry']
    assert r['status']=='UNASSESSED'and r['model_sha256']==sha256(model.read_bytes()).hexdigest()
    assert not old.exists()and all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())
    wrong=tmp_path/'other.pdb';wrong.write_bytes(model.read_bytes()+b'REMARK changed\n')
    with pytest.raises(ValueError,match='differs from the checkpoint model'):
        read_execution_trigonal_geometry(run,child['outputs']['parallelity_execution'],model=wrong,**args)


def test_zero_member_weight_is_reported_separately_from_plane_presence(tmp_path):
    projections,obs,_=observed(tmp_path)
    obs['geometry']['proxy_details']['planarity'][0]['weights'][0]=0.
    result=review(projections,obs);first,second=result['measurements']
    assert first['covering_plane_indices']==[0]and not first['positively_weighted_covering_plane_indices']
    assert second['positively_weighted_covering_plane_indices']==[1]
    assert result['native_planes'][0]['weights'][0]==0.


@pytest.mark.parametrize('chemistry',[None,'unavailable'])
def test_owner_cannot_invent_missing_native_scope(tmp_path,monkeypatch,chemistry):
    from tests.test_refinement_parallelity import completed
    from nasolve.refinement_parallelity import read_execution_trigonal_geometry
    run,result,_,child,_,_=completed(tmp_path,monkeypatch,chemistry=chemistry)
    with patch('subprocess.Popen',side_effect=AssertionError('No new capture')):
        r=read_execution_trigonal_geometry(run,child['outputs']['parallelity_execution'],checkpoint=child['id'],parent=child['parent'],model=result.model_path)
    if chemistry is None:assert r is None
    else:assert r['status']=='UNASSESSED'and not r['measurements']and r['reason']


def test_projection_change_during_read_is_refused(tmp_path,monkeypatch):
    import nasolve.cif_plane_geometry as geometry
    projections,obs,_=observed(tmp_path);original=geometry.audit_trigonal_plane_coverage
    def changed(source,dictionary,code):
        result=original(source,dictionary,code)
        source.write_text(source.read_text()+'# changed\n')
        return result
    monkeypatch.setattr(geometry,'audit_trigonal_plane_coverage',changed)
    with pytest.raises(ValueError,match='projection changed'):
        review(projections,obs)
