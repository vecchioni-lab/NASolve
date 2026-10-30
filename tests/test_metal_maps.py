"""Maps must describe the completed native endpoint, not a reloaded model."""
import copy
import gzip
import hashlib
import json
import pytest
from nasolve.metal import map_diagnostics as maps
from tests.test_metal_xyz import prepared,evidence,fake_execution


def capture_fixture(plan,native,directory=None):
    work=[r[0] for r in native['reflection_after']['rows'] if not r[3]]
    atoms={json.dumps(a['key'],sort_keys=True):a for a in native['atoms']}
    rows=[]
    for name,filename,label in maps.MAPS:
        raw=(name+' synthetic coefficients').encode()
        if directory is not None:(directory/filename).write_bytes(raw)
        sites=[]
        for site in plan['sites']:
            a=atoms[json.dumps(site['key'],sort_keys=True)]
            sites.append(dict(node_id=site['node_id'],key=a['key'],xyz=a['xyz'],center_sigma=1.,sphere_min_sigma=-2.,sphere_max_sigma=3.,sphere_mean_sigma=.5,samples=123))
        rows.append(dict(type=name,filename=filename,label=label,sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),coefficient_indices=work,coefficient_count=len(work),max_abs_coefficient=10.,readback_max_complex_error=1e-7,grid=[12,12,12],sites=sites))
    return dict(protocol=maps.PROTOCOL,policy=maps.request(),endpoint_sha256=maps.endpoint_digest(native),active_state_before='a'*64,active_state_after='a'*64,implementation_sha256='b'*64,native_source_hashes={k:'c'*64 for k in ('map_tools','miller','mtz')},maps=rows)


def enabled(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    new=xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],capture_maps=True)
    n=evidence(new,raw);n['map_diagnostics']=capture_fixture(new,n)
    return xyz,c,new,raw,n


def test_opt_in_preserves_legacy_plan_parameters_and_acceptance(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    assert xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],capture_maps=False)==p
    new=xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],capture_maps=True)
    assert xyz.parameters(new,[])==xyz.parameters(p,[])
    assert new['map_capture']==maps.request() and new['options']['capture_maps'] is True
    assert 'map_capture' not in p
    n=evidence(new,raw);n['map_diagnostics']=capture_fixture(new,n)
    r=xyz.audit_result(new,raw,n,raw)
    assert r['map_diagnostics']['source']=='completed_native_xyz'
    assert r['scientific_acceptance']=='NOT_ASSESSED' and not r['automatic_checkpoint_selection']


@pytest.mark.parametrize('change',['missing','unexpected','endpoint','state','free','duplicate','site','coordinate','nonfinite','range','path','policy','source','mtz_error','grid','count'])
def test_bad_map_capture_is_rejected(tmp_path,change):
    xyz,c,p,raw,n=enabled(tmp_path);e=n['map_diagnostics'];m=e['maps'][0]
    if change=='missing':n.pop('map_diagnostics')
    if change=='unexpected':p.pop('map_capture');p['options'].pop('capture_maps')
    if change=='endpoint':e['endpoint_sha256']='d'*64
    if change=='state':e['active_state_after']='e'*64
    if change=='free':m['coefficient_indices'].append(next(r[0] for r in n['reflection_after']['rows'] if r[3]));m['coefficient_count']+=1
    if change=='duplicate':m['coefficient_indices']*=2;m['coefficient_count']*=2
    if change=='site':m['sites'][0]['node_id']='other'
    if change=='coordinate':m['sites'][0]['xyz']=list(m['sites'][0]['xyz']);m['sites'][0]['xyz'][0]+=.1
    if change=='nonfinite':m['sites'][0]['center_sigma']=float('nan')
    if change=='range':m['sites'][0]['sphere_mean_sigma']=10.
    if change=='path':m['filename']='../outside.mtz'
    if change=='policy':e['policy']['fill_missing']=True
    if change=='source':e['native_source_hashes']['miller']='invalid'
    if change=='mtz_error':m['readback_max_complex_error']=1.
    if change=='grid':m['grid']=[0,12,12]
    if change=='count':m['coefficient_count']+=1
    with pytest.raises(ValueError):xyz.audit_result(p,raw,n,raw)


@pytest.mark.parametrize('rw,rf,work,order',[(.299,.31,True,True),(.3,.31,False,True),(.2,.19,True,False),(.2,.2,True,False),(.343,.93,False,True)])
def test_fit_context_mirrors_existing_numerical_conditions_without_accepting(rw,rf,work,order):
    out=maps.fit_context(rw,rf)
    assert out['r_work_less_than_0_30'] is work
    assert out['r_work_less_than_r_free'] is order
    assert out['numerical_conditions_met'] is (work and order)
    assert out['scientific_acceptance']=='NOT_ASSESSED'
    assert out['r_free_minus_r_work']==pytest.approx(rf-rw)
    assert out['r_free_upper_limit'] is None
    from nasolve.refine_doctor import _candidate
    doctor=_candidate('numeric-test','source',{'r_work':rw,'r_free':rf},usable=True,accepted=True)
    assert out['numerical_conditions_met']==doctor['strict_success']


@pytest.mark.parametrize('value',[1,None,'true',[],{}])
def test_map_switch_requires_bool(tmp_path,value):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    with pytest.raises(ValueError):xyz.make_plan(raw,h['sites'],p['metadata'],p['references'],p['phases'],capture_maps=value)


def test_bundle_maps_relocate_and_rehashed_file_tampering_fails(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    from pathlib import Path
    from nasolve.metal.context import _reference
    from nasolve.metal.recipe import digest
    from nasolve.metal.materialize import _json_bytes
    old=tmp_path/'old';xyz,c,h,ref,n=fake_execution(old,monkeypatch);fake=xyz._native
    def enriched(directory,native,timeout):
        e=fake(directory,native,timeout);p=json.loads((directory/'plan.json').read_text())
        e['map_diagnostics']=capture_fixture(p,e,directory)
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()));return e
    monkeypatch.setattr(xyz,'_native',enriched)
    doc=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=n,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'],capture_maps=True)
    assert xyz.verify_xyz(c.run,'Metal/xyz_001')==doc
    assert all(filename in doc['files'] for _,filename,_ in maps.MAPS)
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',old/'src',ignore=shutil.ignore_patterns('__pycache__'))
    moved=tmp_path/'moved';old.rename(moved);run=moved/'dataset/AutoMR/run_001';d=run/'Metal/xyz_001'
    script="from nasolve.metal.xyz import verify_xyz;import sys;print(verify_xyz(sys.argv[1],'Metal/xyz_001')['trial_id'])"
    result=subprocess.run([sys.executable,'-B','-c',script,str(run)],cwd=moved,env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,check=True)
    assert result.stdout.strip()==doc['trial_id'] and not old.exists()
    filename=maps.MAPS[0][1];(d/filename).write_bytes(b'changed map')
    doc['files'][filename]=_reference(d/filename,run);doc.pop('trial_id');doc['trial_id']=digest(doc);(d/'manifest.json').write_bytes(_json_bytes(doc))
    with pytest.raises(ValueError):xyz.verify_xyz(run,d)


def test_declared_column_labels_are_checked_and_old_captures_remain_readable(tmp_path):
    xyz,c,p,raw,n=enabled(tmp_path)
    assert xyz.audit_result(p,raw,n,raw)['map_diagnostics']
    for row in n['map_diagnostics']['maps']:row['column_labels']=[row['label'],'PHI'+row['label']]
    assert xyz.audit_result(p,raw,n,raw)['map_diagnostics']['maps'][0]['column_labels']==['TWOFOFC','PHITWOFOFC']
    n['map_diagnostics']['maps'][0]['column_labels']=['ANOM','PHANOM']
    with pytest.raises(ValueError):xyz.audit_result(p,raw,n,raw)


def test_active_state_hash_covers_scale_coordinate_phase_and_flag_changes():
    from types import SimpleNamespace as S
    atom=S(label='site',scattering_type='Ag',site=[.1,.2,.3],occupancy=1.,u_iso=2.,u_star=[-1.]*6,fp=-.5,fdp=0.,flags=S(use_u_iso=lambda:True,use_u_aniso=lambda:False))
    data=dict(obs=[10.],calc=[3+4j],hl=[(1.,2.,3.,4.)],mask=[.3],free=[False])
    def array(key):return S(indices=lambda:[(1,0,0)],data=lambda:data[key],sigmas=lambda:[1.])
    x=S(scatterers=lambda:[atom],unit_cell=lambda:S(parameters=lambda:(10.,10.,10.,90.,90.,90.)),space_group_info=lambda:'P 1')
    f=S(xray_structure=x,f_obs=lambda:array('obs'),f_model=lambda:array('calc'),hl_coeffs=lambda:array('hl'),r_free_flags=lambda:array('free'),k_isotropic=lambda:[1.],k_anisotropic=lambda:[1.],k_masks=lambda:[data['mask']],r_work=lambda:.2,r_free=lambda:.3)
    before=maps._active_state(f);assert maps._active_state(f)==before
    for field,value in [('obs',[11.]),('calc',[4+4j]),('hl',[(2.,2.,3.,4.)]),('mask',[.4]),('free',[True])]:
        original=data[field];data[field]=value;assert maps._active_state(f)!=before;data[field]=original
    atom.site[0]+=.001;assert maps._active_state(f)!=before


def test_declared_map_wavelength_must_match_dataset(tmp_path):
    xyz,c,p,raw,n=enabled(tmp_path)
    n['map_diagnostics']['wavelength_A']=p['metadata']['wavelength_A']
    assert xyz.audit_result(p,raw,n,raw)['map_diagnostics']['wavelength_A']==p['metadata']['wavelength_A']
    n['map_diagnostics']['wavelength_A']+=.1
    with pytest.raises(ValueError):xyz.audit_result(p,raw,n,raw)
