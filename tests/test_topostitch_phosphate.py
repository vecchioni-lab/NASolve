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


@pytest.mark.parametrize('mode', ['complete', 'preflight_only', 'failed_preflight', 'changed_plan'])
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
    if mode in ('complete','preflight_only'):
        result=job.run_registered_phosphate_refinement(path,out,phenix='unused',preflight_only=mode=='preflight_only')
        if mode=='preflight_only':
            assert phases==['preflight'] and result['status']=='PREFLIGHT_COMPLETE_REQUIRES_REVIEW'
            assert 'candidate' not in result and not (out/'fit').exists()
            return
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


def phased_request(tmp_path):
    from nasolve.topostitch_recipe import model_atom_rows
    path, spec = request(tmp_path)
    raw = (pdb_record('ATOM',1,'P','DA','B',1,x=1,y=2,z=3,element='P') +
           pdb_record('HETATM',2,'HG','HG','M',1,x=4,y=5,z=6,element='HG')).encode()
    (tmp_path/'model').write_bytes(raw)
    spec['inputs']['model']['sha256'] = sha256(raw).hexdigest()
    spec['diffraction'] = dict(target='mlhl',phase_labels=['HLA','HLB','HLC','HLD'],
        fixed_scattering_groups=[dict(selection='element P',f_prime=.1,f_double_prime=0),
                                 dict(selection='element Hg',f_prime=-8.,f_double_prime=0)])
    scattering=dict(schema_version=1,kind='topostitch-fixed-scattering',model_sha256=sha256(raw).hexdigest(),
        atoms=[dict(identity=r,f_prime=v,f_double_prime=0)
               for r,v in zip(model_atom_rows(raw),(.1,-8.))])
    for name,data in [('phases',b'phase-mtz'),('scattering',json.dumps(scattering).encode())]:
        (tmp_path/name).write_bytes(data)
        spec['inputs'][name]=dict(path=name,sha256=sha256(data).hexdigest())
    path.write_text(json.dumps(spec))
    return path,spec,scattering


def test_explicit_phased_intake_preserves_legacy_and_relocates_every_pin(tmp_path):
    old=tmp_path/'old';old.mkdir();path,spec,scattering=phased_request(old)
    new=tmp_path/'moved';old.rename(new)
    value,files,snapshots=job._request(new/path.name)
    assert value==spec and set(files)==set(spec['inputs'])|{'restraint_0'}
    assert all(p.is_relative_to(new) for p in files.values())
    assert json.loads(snapshots[files['scattering']])==scattering
    (new/'phases').write_bytes(b'drift')
    with pytest.raises(ValueError,match='checksum'):job._request(new/path.name)


@pytest.mark.parametrize('change', ['target','quartet','duplicate_label','missing_phase',
    'missing_scattering','nan_fp','nonzero_fdp','bool_fp','multiline_selection','unexpected_field'])
def test_phased_request_rejects_incomplete_or_unsafe_policy_before_output(tmp_path,change):
    path,spec,_=phased_request(tmp_path);d=spec['diffraction']
    if change=='target':d['target']='ml'
    if change=='quartet':d['phase_labels'].pop()
    if change=='duplicate_label':d['phase_labels'][-1]=d['phase_labels'][0]
    if change=='missing_phase':spec['inputs'].pop('phases')
    if change=='missing_scattering':spec['inputs'].pop('scattering')
    if change=='nan_fp':d['fixed_scattering_groups'][0]['f_prime']=float('nan')
    if change=='nonzero_fdp':d['fixed_scattering_groups'][0]['f_double_prime']=1
    if change=='bool_fp':d['fixed_scattering_groups'][0]['f_prime']=True
    if change=='multiline_selection':d['fixed_scattering_groups'][0]['selection']='all\nmain.nproc=8'
    if change=='unexpected_field':d['infer_phases']=True
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError):job._request(path)


@pytest.mark.parametrize('change',['source','missing','reorder','identity','nonzero_fdp','nan'])
def test_atom_keyed_scattering_requires_the_whole_exact_parent(tmp_path,change):
    path,spec,packet=phased_request(tmp_path)
    if change=='source':packet['model_sha256']='0'*64
    if change=='missing':packet['atoms'].pop()
    if change=='reorder':packet['atoms'].reverse()
    if change=='identity':packet['atoms'][1]['identity']['residue_number']=2
    if change=='nonzero_fdp':packet['atoms'][1]['f_double_prime']=.1
    if change=='nan':packet['atoms'][1]['f_prime']=float('nan')
    raw=json.dumps(packet).encode();(tmp_path/'scattering').write_bytes(raw)
    spec['inputs']['scattering']['sha256']=sha256(raw).hexdigest();path.write_text(json.dumps(spec))
    with pytest.raises(ValueError):job._request(path)


def phased_states():
    reference=dict(hl=[[[1,0,0],[2,0,0]],[[1.,2.,3.,4.],[5.,6.,7.,8.]]],
        flags=[[[1,0,0],[2,0,0]],[False,True]],
        scattering=[dict(identity={'label':'ligand'},f_prime=-8.,f_double_prime=0.)])
    native=dict(**deepcopy(reference),target='mlhl',anomalous=False,use_experimental_phases=True,
                strategy=['individual_sites'],refining_scattering=False)
    return reference,native


@pytest.mark.parametrize('change',['ML','disabled','anomalous','strategy','group_refine','HL','HL_index',
    'HL_duplicate','HL_missing','HL_nan','free','fp','fdp','atom','missing_atom'])
def test_effective_phased_native_state_cannot_hide_drift_behind_declared_policy(change):
    from nasolve.topostitch_phased import compare_native_state
    reference,state=phased_states()
    if change=='ML':state['target']='ml'
    if change=='disabled':state['use_experimental_phases']=False
    if change=='anomalous':state['anomalous']=True
    if change=='strategy':state['strategy'].append('group_anomalous')
    if change=='group_refine':state['refining_scattering']=True
    if change=='HL':state['hl'][1][0][0]+=.001
    if change=='HL_index':state['hl'][0][0]=[3,0,0]
    if change=='HL_duplicate':state['hl'][0][0]=[2,0,0]
    if change=='HL_missing':state['hl'][0].pop();state['hl'][1].pop()
    if change=='HL_nan':state['hl'][1][0][0]=float('nan')
    if change=='free':state['flags'][1].reverse()
    if change=='fp':state['scattering'][0]['f_prime']+=.01
    if change=='fdp':state['scattering'][0]['f_double_prime']=1.
    if change=='atom':state['scattering'][0]['identity']['label']='other'
    if change=='missing_atom':state['scattering'].clear()
    with pytest.raises(ValueError):compare_native_state(reference,state)


def test_phase_coefficients_and_original_flags_are_compared_by_index():
    from nasolve.topostitch_phased import compare_native_state
    reference,state=phased_states()
    for key in ('hl','flags'):
        state[key][0].reverse();state[key][1].reverse()
    result=compare_native_state(reference,state)
    assert result['source_hl_exact'] and result['source_flags_exact'] and result['fixed_scattering_exact']
    assert result['phase_count']==2 and result['atom_count']==1


def test_phase_policy_does_not_inject_phases_as_restraints_or_refine_scattering(tmp_path):
    from nasolve.topostitch_phased import policy_text
    _,spec,_=phased_request(tmp_path)
    policy=policy_text(spec['diffraction'],'../inputs/phases.mtz')
    assert 'target = mlhl' in policy and 'use_experimental_phases = True' in policy
    assert policy.count('refine = None')==2
    assert 'experimental_phases' in policy and 'find_automatically = False' in policy
    assert 'group_anomalous' not in policy.split('refine {',1)[1]


@pytest.mark.parametrize('change', ['none','overlap','uncovered','empty','extra_group','group_refine',
    'group_value','fm_value','source_value','scattering_species','scatterer_identity','phase_change','source_amplitude','native_cell','native_source'])
def test_initialized_guard_checks_both_managers_and_group_coverage(tmp_path,monkeypatch,change):
    from types import SimpleNamespace as N
    from nasolve.topostitch_phased import NativePhasedGuard
    from nasolve import topostitch_native_recipe
    _,spec,packet=phased_request(tmp_path)
    guard=object.__new__(NativePhasedGuard)
    guard.spec=spec['diffraction'];guard.scattering=packet;guard.source=(tmp_path/'model').read_bytes()
    guard._native_sources={};guard._native_hashes={}
    rows=[a['identity'] for a in packet['atoms']]
    monkeypatch.setattr(topostitch_native_recipe,'native_atom_identities',lambda h:rows)
    cell=[100.,100.,80.,90.,90.,120.]
    crystal=N(space_group=lambda:'R3',unit_cell=lambda:N(parameters=lambda:cell))
    guard.crystal=crystal
    obs=observations();indices=[r[0] for r in obs]
    guard.observations=deepcopy(obs)
    hl=[[1.,2.,3.,4.],[5.,6.,7.,8.]]
    guard.reference=dict(hl=[indices,deepcopy(hl)],flags=[indices,[False,True]],scattering=packet['atoms'])
    class Atom:
        def __init__(self,label):self.label=label
        def id_str(self):return self.label
    atoms=[Atom('P'),Atom('Hg')]
    def scatters():return [N(label='P',fp=.1,fdp=0,scattering_type='P'),N(label='Hg',fp=-8.,fdp=0,scattering_type='Hg')]
    sc,fs=scatters(),scatters()
    live_cell=list(cell)
    xs=N(scatterers=lambda:sc,space_group=lambda:'R3',unit_cell=lambda:N(parameters=lambda:live_cell))
    fx=N(scatterers=lambda:fs,space_group=lambda:'R3',unit_cell=crystal.unit_cell)
    masks={'element P':[True,False],'element Hg':[False,True]}
    groups=[N(selection_string=g['selection'],iselection=[i],f_prime=g['f_prime'],f_double_prime=0,
              refine_f_prime=False,refine_f_double_prime=False) for i,g in enumerate(guard.spec['fixed_scattering_groups'])]
    model=N(get_hierarchy=lambda:N(atoms=lambda:atoms),get_xray_structure=lambda:xs,
            selection=lambda s:masks[s],get_anomalous_scatterer_groups=lambda:groups)
    fo=N(indices=lambda:indices,data=lambda:[r[1] for r in obs],sigmas=lambda:[r[2] for r in obs],anomalous_flag=lambda:False)
    flags=N(indices=lambda:indices,data=lambda:[False,True])
    fm=N(xray_structure=fx,target_name='mlhl',hl_coeffs=lambda:N(indices=lambda:indices,data=lambda:hl),
         f_obs=lambda:fo,r_free_flags=lambda:flags)
    params=N(main=N(use_experimental_phases=True),refine=N(strategy=['individual_sites']))
    if change=='overlap':masks['element Hg']=[True,True];groups[1].iselection=[0,1]
    if change=='uncovered':masks['element Hg']=[True,False];groups[1].iselection=[0];groups[1].f_prime=.1;guard.spec['fixed_scattering_groups'][1]['f_prime']=.1
    if change=='empty':masks['element Hg']=[False,False];groups[1].iselection=[]
    if change=='extra_group':groups.append(groups[0])
    if change=='group_refine':groups[1].refine_f_prime=True
    if change=='group_value':groups[1].f_prime=0
    if change=='fm_value':fs[1].fp=0
    if change=='source_value':sc[1].fp=fs[1].fp=0
    if change=='scattering_species':fs[1].scattering_type='Hg2+'
    if change=='scatterer_identity':fs[1].label='other'
    if change=='phase_change':hl[0][0]+=.01
    if change=='source_amplitude':obs[0][1]+=1
    if change=='native_cell':live_cell[0]+=.01
    if change=='native_source':
        source=tmp_path/'native.py';source.write_text('before')
        guard._native_sources={'native':source};guard._native_hashes={'native':sha256(source.read_bytes()).hexdigest()}
        source.write_text('after')
    if change=='none':
        state,audit=guard.observe(model,fm,params)
        assert state['target']=='mlhl' and audit['source_observations']['observations_exact']
    else:
        with pytest.raises(ValueError):guard.observe(model,fm,params)


@pytest.mark.parametrize('change',['none','ML','absent_HL','different_HL','different_flags','different_data','different_manager','ADP','phase_order'])
def test_actual_coordinate_target_is_checked_not_only_its_manager_name(monkeypatch,change):
    from types import SimpleNamespace as N
    from nasolve.topostitch_phased import NativePhasedGuard
    guard=object.__new__(NativePhasedGuard);reference,_=phased_states();guard.reference=reference
    guard.observations=observations();indices=reference['hl'][0];coeffs=deepcopy(reference['hl'][1]);flags=[False,True]
    phase_indices=deepcopy(indices)
    fo=N(indices=lambda:indices,data=lambda:[r[1] for r in guard.observations],sigmas=lambda:[1.,1.])
    phases=N(indices=lambda:phase_indices,data=lambda:coeffs)
    core=N(spacialization='hl',experimental_phases=phases,f_obs=fo,
           r_free_flags=N(indices=lambda:indices,data=lambda:flags))
    fm=N(target_name='mlhl');functor=N(manager=fm,core=core)
    minimizer=N(fmodels=N(fmodel_xray=lambda:fm,target_functor_xray=functor),model=object(),refine_xyz=True,refine_adp=False)
    calls=[];monkeypatch.setattr(guard,'observe',lambda *args:calls.append(args)or('snapshot','audit'))
    if change=='ML':core.spacialization='f'
    if change=='absent_HL':core.experimental_phases=None
    if change=='different_HL':coeffs[0][0]+=.01
    if change=='different_flags':flags.reverse()
    if change=='different_data':fo.data=lambda:[9.,11.]
    if change=='different_manager':functor.manager=object()
    if change=='ADP':minimizer.refine_adp=True
    if change=='phase_order':phase_indices.reverse();coeffs.reverse()
    if change=='none':
        assert guard.observe_target(minimizer,None)==('snapshot','audit') and len(calls)==1
    else:
        with pytest.raises(ValueError):guard.observe_target(minimizer,None)
        assert calls==[]



def test_explicit_phased_roundoff_keeps_legacy_exact_and_each_tensor_in_own_frame():
    import math
    before=states();after=deepcopy(before);frame=hex_frame();other=deepcopy(frame)
    other['cell'][0]=math.nextafter(frame['cell'][0],math.inf)
    other['orthogonalization_matrix'][0]=math.nextafter(frame['orthogonalization_matrix'][0],math.inf)
    for state in (before,after):
        for a in state.values():a['u_star']=[v*1e-5 for v in a['u_star']]
    with pytest.raises(ValueError,match='frame changed'):
        job._verify_return(before,after,{'moving'},observations(),observations(),initial_frame=frame,final_frame=other)
    result=job._verify_return(before,after,{'moving'},observations(),observations(),
        initial_frame=frame,final_frame=other,allow_native_frame_roundoff=True)
    audit=result['adp_audit'];assert not audit['native_frame_exact']
    assert audit['native_frame_roundoff']['each_tensor_uses_own_frame']
    assert 0<audit['max_cartesian_difference_angstrom_squared']<1e-12


@pytest.mark.parametrize('change',['cell','angle','matrix','space_group','tensor','charge','species'])
def test_native_roundoff_permission_does_not_allow_crystal_or_chemical_changes(change):
    import math
    before=states();after=deepcopy(before);frame=hex_frame();other=deepcopy(frame)
    for state in (before,after):
        for a in state.values():a.update(charge='',scattering_type='P')
    if change=='cell':other['cell'][0]=math.nextafter(frame['cell'][0]+1e-10,math.inf)
    if change=='angle':other['cell'][5]=math.nextafter(frame['cell'][5]+1e-10,math.inf)
    if change=='matrix':other['orthogonalization_matrix'][0]=math.nextafter(frame['orthogonalization_matrix'][0]+1e-10,math.inf)
    if change=='space_group':other['space_group']='P 1'
    if change=='tensor':after['moving']['u_star'][4]+=1e-10
    if change=='charge':after['moving']['charge']='1+'
    if change=='species':after['moving']['scattering_type']='P5+'
    with pytest.raises(ValueError):
        job._verify_return(before,after,{'moving'},observations(),observations(),
            initial_frame=frame,final_frame=other,allow_native_frame_roundoff=True)


def test_native_phased_policy_omits_defaults_without_changing_live_groups(tmp_path):
    phil = pytest.importorskip('iotbx.phil')
    refinement = pytest.importorskip('phenix.refinement')
    from nasolve.topostitch_phased import policy_text
    _, spec, _ = phased_request(tmp_path)
    spec['diffraction']['fixed_scattering_groups'][0].update(
        selection="element P and not (segid 'test')", f_prime=.1427225023508072)
    master = refinement.master_params()
    legacy = master.extract().refinement
    actual = master.fetch(source=phil.parse(policy_text(
        spec['diffraction'], '../inputs/phases.mtz'))).extract().refinement
    # The unmodified native default remains enabled for non-phased callers.
    assert legacy.output.write_def_file is True
    assert actual.output.write_def_file is False
    assert actual.main.target == 'mlhl' and actual.main.use_experimental_phases
    groups = [g for g in actual.refine.anomalous_scatterers.group if g.selection]
    assert len(groups) == len(spec['diffraction']['fixed_scattering_groups'])
    for expected, group in zip(spec['diffraction']['fixed_scattering_groups'], groups):
        assert group.selection == expected['selection']
        assert group.f_prime == expected['f_prime']
        assert group.f_double_prime == expected['f_double_prime']
        assert group.refine == []
