"""A registered native execution remains coordinate-only and unselected."""
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from nasolve import topostitch_phosphate as job
from tests.helpers import pdb_record


def request(tmp_path):
    names=('model','registration_model','data','registration','discovery','continuations','native_receipt','restraint')
    refs={}
    for name in names:
        p=tmp_path/name;p.write_text(name)
        refs[name]=dict(path=name,sha256=sha256(p.read_bytes()).hexdigest())
    value=dict(schema_version=1,kind='topostitch-phosphate-refinement',
        inputs={k:v for k,v in refs.items() if k!='restraint'},restraints=[refs['restraint']],
        continuation_id=1,cycles=1,iterations=20,max_displacement_angstrom=3.,wxc_scale=.5,
        data_labels='F,SIGF',free_label='FreeR_flag',test_flag_value=0)
    path=tmp_path/'request.json';path.write_text(json.dumps(value));return path,value


@pytest.mark.parametrize('key,value', [('cycles',0),('cycles',6),('iterations',True),('iterations',201),
    ('max_displacement_angstrom',float('nan')),('wxc_scale',0),('continuation_id',0),
    ('test_flag_value',False),('data_labels','F\nmain.nproc=8')])
def test_invalid_protocol_refuses_before_native_owner_or_output(tmp_path,monkeypatch,key,value):
    path,spec=request(tmp_path);spec[key]=value;path.write_text(json.dumps(spec))
    import nasolve.topostitch_captured_job as owners
    monkeypatch.setattr(owners,'_cedar',lambda *a,**k:pytest.fail('Native owner loaded'))
    out=tmp_path/'out'
    with pytest.raises(ValueError):job.run_registered_phosphate_refinement(path,out,phenix='missing')
    assert not out.exists()


def test_request_pins_every_file_and_resolves_relative_paths_after_relocation(tmp_path):
    old=tmp_path/'old';old.mkdir();path,spec=request(old)
    new=tmp_path/'new';old.rename(new)
    actual,files,snapshots=job._request(new/path.name)
    assert actual==spec and all(p.is_relative_to(new)for p in files.values())
    files['data'].write_text('changed observations')
    with pytest.raises(ValueError,match='checksum'):job._request(new/path.name)


def test_coordinate_export_keeps_original_records_and_explicit_cartesian_tensors():
    raw=(pdb_record('ATOM',1,'P','DA','A',1,x=1,y=2,z=3,element='P')+
         'ANISOU    1  P    DA A   1     1000   2000   3000    100    200    300       P  \n'+
         pdb_record('ATOM',2,"O3'",'DT','B',2,x=4,y=5,z=6,element='O')+'END\n').encode()
    points=[(1.123456,2,3),(4,5,6)]
    candidate,audit=job._masked_result(raw,points,[0],1)
    assert candidate.splitlines()[1:]==raw.splitlines()[1:]
    assert audit['movable_anisou_count']==1 and audit['noncoordinate_bytes_preserved']
    assert not audit['scientific_acceptance'] and not audit['adp_refinement']
    with pytest.raises(ValueError,match='Fixed'):job._masked_result(raw,[points[0],(4,5,7)],[0],1)
    with pytest.raises(ValueError,match='exceeds'):job._masked_result(raw,[(3,2,3),points[1]],[0],1)


def states():
    atom=dict(xyz=[1.,2.,3.],q=1.,u_star=[.1,.2,.3,0.,0.,0.],u_iso=-1.,use_u_iso=False,use_u_aniso=True,element='P')
    return {'moving':deepcopy(atom),'fixed':deepcopy(atom)}


def observations():return [[[1,0,0],10.,1.,False],[[2,0,0],11.,1.,True]]


@pytest.mark.parametrize('change', ['missing','fixed','occupancy','tensor','flag','amplitude','empty','nan'])
def test_return_rejects_loss_of_atoms_fixed_context_thermal_state_or_data(change):
    before=states();after=deepcopy(before);obs=observations();final=deepcopy(obs)
    if change=='missing':after.pop('fixed')
    elif change=='fixed':after['fixed']['xyz'][0]+=.1
    elif change=='occupancy':after['moving']['q']=.5
    elif change=='tensor':after['moving']['u_star'][0]+=.1
    elif change=='flag':final[0][-1]=True
    elif change=='amplitude':final[0][1]+=1
    elif change=='empty':before={};after={}
    elif change=='nan':after['moving']['xyz'][0]=float('nan')
    with pytest.raises(ValueError):job._verify_return(before,after,{'moving'},obs,final)


def test_return_accepts_only_declared_coordinate_motion_and_keeps_small_r_stats_irrelevant():
    before=states();after=deepcopy(before);after['moving']['xyz'][0]+=.5
    job._verify_return(before,after,{'moving'},observations(),observations())
    assert before==states()
    for flags in ([],[[[1,0,0],10.,1.,True]],[[[1,0,0],10.,1.,False]]):
        with pytest.raises(ValueError,match='work and Free-R'):job._verify_return(before,after,{'moving'},flags,flags)


def test_existing_fit_entry_dispatches_native_path_without_changing_geometric_default(monkeypatch):
    from nasolve.topostitch_fit import main
    calls=[];monkeypatch.setattr(job,'main',lambda args:calls.append(args)or 7)
    assert main(['native-phosphate','--request','frozen.json'])==7
    assert calls==[['--request','frozen.json']]


def test_native_common_amplitude_sigma_scale_preserves_data_but_partial_scaling_refuses():
    before=observations(); after=deepcopy(before)
    for row in after:
        row[1]*=123.45; row[2]*=123.45
    result=job._verify_return(states(),states(),{'moving'},before,after)
    assert result['indices_and_flags_exact'] and not result['observations_exact']
    assert result['amplitude_sigma_common_scale']==pytest.approx(123.45)
    after[0][2]/=123.45
    with pytest.raises(ValueError,match='common F/sigma scale'):
        job._verify_return(states(),states(),{'moving'},before,after)


def test_legacy_geometric_fit_dispatch_preserves_arguments(monkeypatch,capsys):
    from pathlib import Path
    from nasolve import topostitch_fit
    calls=[]
    def observe(*args,**kwargs):
        calls.append((args,kwargs));return {'status':'UNCHANGED_GEOMETRIC_ROUTE'}
    monkeypatch.setattr(topostitch_fit,'fit_end_placement',observe)
    assert topostitch_fit.main(['model.pdb','discovery.json','--registration','registration.json','--request','request.json'])==0
    assert calls==[((Path('model.pdb'),Path('discovery.json')),dict(registration_path=Path('registration.json'),request_path=Path('request.json')))]
    assert 'UNCHANGED_GEOMETRIC_ROUTE' in capsys.readouterr().out


@pytest.mark.parametrize('mode', ['complete', 'failed_preflight', 'changed_plan'])
def test_owned_execution_requires_qualified_preflight_and_unchanged_plan(tmp_path, monkeypatch, mode):
    from contextlib import contextmanager
    from types import SimpleNamespace
    import nasolve.topostitch_captured_job as owners
    path, spec = request(tmp_path)
    raw = ''.join(pdb_record('ATOM', i+1, name, 'DA', 'B', residue,
        x=i, y=0, z=0, element=name[0]) for i, (name, residue) in enumerate(
        [('P',1), ('OP1',1), ('OP2',1), ("O5'",1), ("C5'",1), ("O3'",7)])).encode()
    model = tmp_path/'model'; model.write_bytes(raw)
    spec['inputs']['model']['sha256'] = sha256(raw).hexdigest()
    path.write_text(json.dumps(spec))
    loaded = dict(
        cif_phosphate_continuation=SimpleNamespace(
            RegisteredContinuation=lambda *args: None,
            inspect_inherited_continuation=lambda *args, **kwargs: {'phosphate':['B:1'], 'o3':['B:7']}),
        cif_phosphate_restraints=SimpleNamespace(phosphate_bond_phil=lambda inspection: 'bond policy'),
        cif_phosphate_runtime=SimpleNamespace(), cif_refinement_runtime=SimpleNamespace())
    actual_import = job.importlib.import_module
    monkeypatch.setattr(job.importlib, 'import_module', lambda name:
        loaded[name.rsplit('.',1)[1]] if name.startswith('_test_phosphate_owner.') else actual_import(name))
    phases = []
    def run(command, *, cwd, on_process, **kwargs):
        phase = cwd.name; phases.append(phase); on_process({'pid':123})
        if mode == 'failed_preflight': return 2
        (cwd/'science.json').write_text(json.dumps({'status':'COMPLETE_REQUIRES_REVIEW'}))
        (cwd/'candidate.pdb').write_bytes(raw)
        if mode == 'changed_plan': (cwd.parent/'plan.json').write_text('{}')
        return 0
    native = tmp_path/'native.py'; native.write_text('# owned test runtime')
    cedar = dict(cif_attachment_native=SimpleNamespace(__package__='_test_phosphate_owner',
        __file__=str(native), _capture=lambda *args: (None, None, {tmp_path/'native_receipt':b'native_receipt'})),
        phenix_runtime=SimpleNamespace(installation_from_candidate=lambda path: SimpleNamespace(
            version='synthetic', executables={'phenix.python':tmp_path/'not-executed'}, environment={})),
        campaign_process=SimpleNamespace(run_owned_command=run, process_alive=lambda record:False))
    @contextmanager
    def selected_owner(*args): yield cedar
    monkeypatch.setattr(owners, '_cedar', selected_owner)
    out=tmp_path/'out'
    if mode == 'complete':
        result=job.run_registered_phosphate_refinement(path,out,phenix='unused')
        assert phases == ['preflight','fit'] and result['status'] == 'REFINED_FOR_REVIEW'
        assert result['candidate']['anchor'] == 'run'
        assert not result['scientific_acceptance'] and not result['checkpoint_created']
    else:
        with pytest.raises((RuntimeError,ValueError)):
            job.run_registered_phosphate_refinement(path,out,phenix='unused')
        assert phases == ['preflight'] and not (out/'fit').exists()
        result=json.loads((out/'result.json').read_text())
        assert result['status'] == ('FAILED_INPUT_DRIFT' if mode == 'changed_plan' else 'FAILED')
    assert model.read_bytes() == raw



def hex_frame():
    return dict(cell=[100.,100.,80.,90.,90.,120.], space_group='R 3:H',
        orthogonalization_matrix=[100.,-50.,0.,0.,50.*(3.**.5),0.,0.,0.,80.])


def test_reciprocal_roundoff_is_compared_in_six_physical_cartesian_components():
    import math
    before=states(); after=deepcopy(before)
    for row in after.values():
        row['u_star']=[math.nextafter(v, math.inf) for v in row['u_star']]
    frame=hex_frame()
    result=job._verify_return(before,after,{'moving'},observations(),observations(),
        initial_frame=frame,final_frame=deepcopy(frame))
    audit=result['adp_audit']
    assert audit['anisotropic_atoms_checked']==2 and audit['native_frame_exact']
    assert 0 < audit['max_cartesian_difference_angstrom_squared'] <= 1e-12
    with pytest.raises(ValueError):
        job._verify_return(before,after,{'moving'},observations(),observations())


@pytest.mark.parametrize('component',range(6))
def test_real_diagonal_or_offdiagonal_tensor_changes_refuse(component):
    before=states();after=deepcopy(before);after['fixed']['u_star'][component]+=1e-8
    with pytest.raises(ValueError,match='Cartesian anisotropic tensor'):
        job._verify_return(before,after,{'moving'},observations(),observations(),
            initial_frame=hex_frame(),final_frame=hex_frame())


@pytest.mark.parametrize('change',['cell','group','matrix','mode','isotropic','inactive_tensor','nonfinite'])
def test_cartesian_roundoff_policy_keeps_frame_mode_and_isotropic_state_strict(change):
    before=states();after=deepcopy(before);frame=hex_frame();other=deepcopy(frame)
    if change=='cell':other['cell'][0]+=.001
    elif change=='group':other['space_group']='P 1'
    elif change=='matrix':other['orthogonalization_matrix'][0]+=.001
    elif change=='mode':after['moving']['use_u_aniso']=False
    elif change in ('isotropic','inactive_tensor'):
        for state in (before,after):
            for row in state.values():row.update(use_u_aniso=False,use_u_iso=True,u_iso=.2,u_star=[-1.]*6)
        if change=='isotropic':after['moving']['u_iso']+=1e-14
        else:after['moving']['u_star'][0]+=1e-14
    elif change=='nonfinite':after['moving']['u_star'][4]=float('nan')
    with pytest.raises(ValueError):
        job._verify_return(before,after,{'moving'},observations(),observations(),
            initial_frame=frame,final_frame=other)


def test_six_component_conversion_retains_shear_and_physical_units():
    # Independent product for O=[[2,1,0],[0,3,0],[0,0,4]], U*=diag(1,2,3).
    assert job._cartesian_adp([1.,2.,3.,0.,0.,0.],[[2.,1.,0.],[0.,3.,0.],[0.,0.,4.]])==(6.,18.,48.,6.,0.,0.)
    with pytest.raises(ValueError,match='both native'):
        job._verify_return(states(),states(),{'moving'},observations(),observations(),initial_frame=hex_frame())
