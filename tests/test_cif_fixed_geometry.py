"""Generic fixed-definition trial guards; installed Phenix is not available."""
from copy import deepcopy
import math
import pytest
from tests.test_cif_fragment_restoration import fixture


@pytest.mark.parametrize(('reason','error','iterations','criterion','expected'),[
    ('max_iterations',None,500,True,'NOT_CONVERGED_LIMIT'),
    ('traditional_convergence_test',None,500,True,'NOT_CONVERGED_LIMIT'),
    ('traditional_convergence_test','rounding error',8,True,'NOT_CONVERGED_ERROR'),
    ('traditional_convergence_test',None,8,False,'NOT_CONVERGED'),
    ('traditional_convergence_test',None,8,True,'NATIVE_CRITERION_MET'),
    ('unreported',None,8,True,'NOT_ASSESSED'),
])
def test_exit_zero_or_target_drop_cannot_replace_stopping_evidence(reason,error,iterations,criterion,expected):
    from nasolve.cif_fixed_geometry import classify_stopping
    r=classify_stopping({'reason':reason,'error':error,'iterations':iterations,'max_iterations':500,'native_criterion_met':criterion})
    assert r==expected


def test_full_precision_trial_writes_only_new_coordinate_fields(tmp_path):
    from nasolve.cif_fixed_geometry import write_geometry_candidate, review_fixed_coordinates
    _,model,_,native,_=fixture(tmp_path)
    model.write_text('CRYST1   50.000   51.000   52.000  90.00  90.00  90.00 P 1           1\n'+model.read_text())
    original=model.read_bytes();points=deepcopy(native['geometry']['sites_cart_exact']);points[-1][0]+=.123456789
    target=tmp_path/'new.pdb';r=write_geometry_candidate(model,target,native,points)
    assert model.read_bytes()==original and r['metadata_and_headers_preserved'] and r['atom_count']==14
    for before,after in zip(original.splitlines(),target.read_bytes().splitlines()):
        if before.startswith((b'ATOM  ',b'HETATM')):assert before[:30]+before[54:]==after[:30]+after[54:]
        else:assert before==after
    assert r['roundtrip_max_distance']<=math.sqrt(3)*.0005+1e-10
    assert r['displacement']['max']==pytest.approx(.123456789)
    report=review_fixed_coordinates(native,points)
    assert report['coordinate_source']=='FIXED_MANAGER_FULL_PRECISION'
    assert native['geometry']['sites_cart_exact']!=points


@pytest.mark.parametrize('defect',['nonfinite','count','overflow','baseline_changed','existing'])
def test_serialization_refuses_correspondence_and_output_defects(tmp_path,defect):
    from nasolve.cif_fixed_geometry import write_geometry_candidate
    _,model,_,native,_=fixture(tmp_path);points=deepcopy(native['geometry']['sites_cart_exact']);output=tmp_path/'candidate.pdb'
    if defect=='nonfinite':points[0][0]=float('nan')
    if defect=='count':points.pop()
    if defect=='overflow':points[0][0]=100000.
    if defect=='baseline_changed':model.write_text(model.read_text().replace('  10.000','  11.000',1))
    if defect=='existing':output.write_text('PRESERVE')
    with pytest.raises((ValueError,FileExistsError)):write_geometry_candidate(model,output,native,points)
    assert output.read_text()=='PRESERVE' if defect=='existing' else not output.exists()


_FAKE_ARRAYS='''
import math
class Double(list):
    def deep_copy(self):return Double(self)
    def size(self):return len(self)
    def norm(self):return math.sqrt(sum(v*v for v in self))
class Vec(list):
    def __init__(self,values):
        if isinstance(values,Double):values=[values[i:i+3] for i in range(0,len(values),3)]
        super().__init__(tuple(v) for v in values)
    def deep_copy(self):return Vec(self)
    def as_double(self):return Double(v for p in self for v in p)
    def norms(self):return [math.sqrt(sum(v*v for v in p)) for p in self]
'''


def worker_fixture(directory,native,mode):
    import json
    from pathlib import Path
    from nasolve.cif_fixed_geometry import _GEOMETRY_WORKER
    for name in ['cctbx','cctbx/array_family','cctbx/geometry_restraints','scitbx']:
        path=directory/name;path.mkdir(parents=True,exist_ok=True);(path/'__init__.py').write_text('')
    (directory/'fake_arrays.py').write_text(_FAKE_ARRAYS)
    (directory/'cctbx/array_family/flex.py').write_text('from fake_arrays import Vec as vec3_double\n')
    (directory/'cctbx/geometry_restraints/flags.py').write_text('class flags:\n def __init__(self,default=False):self.bond=default;self.nonbonded=default\n')
    for name in ['cctbx/geometry_restraints/manager.py','cctbx/geometry_restraints/energies.py','scitbx_lbfgs_ext.py','cctbx_geometry_restraints_ext.py']:
        (directory/name).write_text('# EXPLICIT FAKE; no installed-native claim\n')
    (directory/'scitbx/lbfgs.py').write_text('''
from types import SimpleNamespace as NS
from pathlib import Path
class termination_parameters:
    def __init__(self,**kwargs):self.__dict__.update(kwargs)
def traditional_convergence_test(size,epsilon):return lambda x,g:MODE=='converged'
def run(target_evaluator,termination_params,log):
    Path('fake_optimizer_called').write_text('EXPLICIT_FAKE')
    e=target_evaluator;e.compute_functional_and_gradients()
    e.x[:]=[v*.99 for v in e.x];e.compute_functional_and_gradients()
    n=termination_params.max_iterations if MODE=='limit' else 2
    m=NS(iter=lambda:n,nfun=lambda:3,error='rounding errors' if MODE=='rounding' else None)
    e.callback_after_step(m)
    if MODE!='rounding':log.write('lbfgs minimizer stop: '+('max_iterations' if MODE=='limit' else 'traditional_convergence_test')+'\\n')
    return m
'''.replace("MODE",repr(mode)))
    (directory/'expected_inventory.json').write_text(json.dumps(native))
    bootstrap='''
import json
from pathlib import Path
from types import SimpleNamespace as NS
from fake_arrays import Vec
report=json.loads(Path('expected_inventory.json').read_text())
if MODE=='mismatch':report['atoms'][0]['atom_id']='CHANGED'
if MODE=='target':report['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['type']='CHANGED'
sites=Vec(report['geometry']['sites_cart_exact'])
class Geo:
    site_symmetry_table=NS(special_position_indices=lambda:[0] if MODE=='special' else [])
    crystal_symmetry=NS(unit_cell=lambda:NS(parameters=lambda:(50.,51.,52.,90.,90.,90.)),space_group_info=lambda:'P 1')
    angle_proxies=[];dihedral_proxies=[];const_dihedral_proxies=[];chirality_proxies=[];planarity_proxies=[];parallelity_proxies=[]
    def pair_proxies(self,sites_cart):return NS(bond_proxies=NS(simple=[],asu=[]))
    def energies_sites(self,sites_cart,flags,compute_gradients,normalization):
        assert flags.bond and flags.nonbonded and compute_gradients and normalization is False
        target=sum(v*v for p in sites_cart for v in p)
        return NS(target=target,gradients=Vec([[2*v for v in p] for p in sites_cart]),bond_residual_sum=target,n_bond_proxies=1)
geo=Geo()
raise SystemExit(0)
'''.replace('MODE',repr(mode))
    (directory/'native_worker.py').write_text(bootstrap)
    (directory/'geometry_worker.py').write_text(_GEOMETRY_WORKER)
    spec={'policy_id':'cif-fixed-native-geometry-trial-v1','native_spec':'native_spec.json','expected_inventory':'expected_inventory.json',
          'max_iterations':5,'max_calls':100,'gradient_epsilon':1e-5}
    (directory/'geometry_spec.json').write_text(json.dumps(spec))
    return directory


@pytest.mark.parametrize('mode',['limit','converged','rounding','mismatch','target','special'])
def test_standalone_worker_records_actual_stops_and_refuses_changed_manager(tmp_path,mode):
    import json,os,subprocess,sys
    _,_,_,native,_=fixture(tmp_path);native['installed_api_sources']=[]
    directory=worker_fixture(tmp_path/'worker',native,mode)
    result=subprocess.run([sys.executable,'-B','geometry_worker.py','geometry_spec.json'],cwd=directory,
        env={**os.environ,'PYTHONPATH':str(directory)},capture_output=True,text=True)
    report=json.loads((directory/'geometry_result.json').read_text())
    if mode in {'mismatch','target','special'}:
        assert result.returncode==2 and report['status']=='FAILED'
        assert not (directory/'fake_optimizer_called').exists()
    else:
        assert result.returncode==0,(result.stdout,result.stderr)
        assert report['status']=='REVIEW' and report['captured_inventory_matches']
        assert report['initial']['target']>report['final']['target']
        assert report['constraint_signature_before']==report['constraint_signature_after']
        assert len(report['final_sites_cart'])==14 and report['normalization'] is False
        assert report['stopping']['iterations']==(5 if mode=='limit' else 2)
        from nasolve.cif_fixed_geometry import classify_stopping
        assert classify_stopping(report['stopping'])=={'limit':'NOT_CONVERGED_LIMIT','converged':'NATIVE_CRITERION_MET','rounding':'NOT_CONVERGED_ERROR'}[mode]
        assert len(report['installed_optimizer_sources'])==6


@pytest.mark.parametrize('mode',['limit','mismatch','changed_input','timeout'])
def test_native_trial_driver_preserves_inputs_and_reports_failures(tmp_path,monkeypatch,mode):
    import json,os,sys
    from pathlib import Path
    import nasolve.cif_fixed_geometry as m
    protected=tmp_path/'protected';protected.mkdir()
    _,model,_,native,_=fixture(protected);native['installed_api_sources']=[]
    dictionary=protected/'dictionary.cif';dictionary.write_text('EXPLICIT_FAKE')
    seed=worker_fixture(tmp_path/'fake',native,'mismatch' if mode=='mismatch' else 'limit')
    bootstrap=(seed/'native_worker.py').read_text()
    if mode=='changed_input':bootstrap+='\n'  # mutate original in the worker before successful exit
    bootstrap=bootstrap.replace('raise SystemExit(0)',
        (f'Path({str(model)!r}).write_text("CHANGED")\n' if mode=='changed_input' else '')+'raise SystemExit(0)')
    monkeypatch.setattr(m,'_NATIVE_WORKER',bootstrap)
    if mode=='timeout':monkeypatch.setattr(m,'_GEOMETRY_WORKER','import time\ntime.sleep(30)\n')
    original=model.read_bytes()
    report=m.run_fixed_geometry(model,[dictionary],[],native,tmp_path/'output',Path(sys.executable),
        environment={**os.environ,'PYTHONPATH':str(seed)},phenix_version='EXPLICIT_FAKE',max_iterations=5,timeout_seconds=1 if mode=='timeout' else 30)
    if mode=='limit':
        assert report['status']=='REVIEW' and report['convergence']=='NOT_CONVERGED_LIMIT'
        assert report['source_preserved'] and report['frozen_inputs_preserved']
    else:
        assert report['status']=='FAILED'
        if mode=='timeout':assert report['execution']['status']=='TIMED_OUT'
        if mode=='changed_input':assert not report['source_preserved']
    if mode!='changed_input':assert model.read_bytes()==original
    work=Path(report['native_directory'])
    assert json.loads((work/'geometry_receipt.json').read_text())==report
    assert (work/'geometry.log').is_file() and (work/'inputs/000_model.pdb').read_bytes()==original
