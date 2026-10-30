"""A selected-coordinate trial must never optimize its frozen environment."""
from copy import deepcopy
import math
import pytest


def test_selected_space_reorders_only_explicit_atoms_and_projects_full_gradient():
    from nasolve.cif_selected_geometry import SelectedCoordinates
    p=[[0.,1.,2.],[3.,4.,5.],[6.,7.,8.]];before=deepcopy(p)
    s=SelectedCoordinates(p,[2,0]);x=s.pack(p);x[0]=60.
    assert s.unpack(x)==[[0.,1.,2.],[3.,4.,5.],[60.,7.,8.]]
    assert s.project(list(range(9)))==[6.,7.,8.,0.,1.,2.]
    p[1][0]=99.;assert s.unpack(x)[1]==before[1]
    with pytest.raises(ValueError):s.pack(p)


@pytest.mark.parametrize('indices',[[],[True],[1,1],[-1],[3],[.5],'0',[0,1,2]])
def test_requires_explicit_proper_subset(indices):
    from nasolve.cif_selected_geometry import SelectedCoordinates
    with pytest.raises(ValueError):SelectedCoordinates([[0.,0.,0.]]*3,indices)


@pytest.mark.parametrize('defect',['short','nan','bool','flank'])
def test_selection_vectors_cannot_hide_bad_values_or_flank_motion(defect):
    from nasolve.cif_selected_geometry import SelectedCoordinates
    p=[[0.,1.,2.],[3.,4.,5.]];s=SelectedCoordinates(p,[0])
    if defect=='flank':p[1][0]=99.;call=lambda:s.pack(p)
    else:
        x=[1.,2.,3.]
        if defect=='short':x.pop()
        if defect=='nan':x[0]=math.nan
        if defect=='bool':x[0]=True
        call=lambda:s.unpack(x)
    with pytest.raises(ValueError):call()


def test_generated_worker_keeps_default_fixed_worker_unchanged():
    from nasolve.cif_selected_geometry import selected_geometry_worker
    from nasolve.cif_fixed_geometry import _GEOMETRY_WORKER
    old=_GEOMETRY_WORKER;new=selected_geometry_worker();compile(new,'selected_worker.py','exec')
    assert _GEOMETRY_WORKER==old and 'SelectedCoordinates' not in old


def numerical_capture(points=None):
    from tests.test_cif_native_gradients import capture
    from nasolve.cif_gradient_audit import audit_gradients,FAMILIES
    from nasolve.cif_mixed_gradient import _manager_digest
    n=capture();points=deepcopy(points or n['geometry']['sites_cart_exact'])
    for i,a in enumerate(n['atoms']):a.update(xyz=points[i][:],atom_id=['C','N','O','P'][i],element=['C','N','O','P'][i],occupancy=1.)
    n['geometry']['sites_cart_exact']=points
    baselines={f:[] for f in FAMILIES}
    def evaluate(p,f):
        active=f in ('all','bond');g=[2.*x if active else 0. for xyz in p for x in xyz]
        r={'target':float(sum(x*x for xyz in p for x in xyz)) if active else 0.,'gradient':g,
           'proxy_counts':{'n_bond_proxies':1 if active else None,'n_nonbonded_proxies':0 if f in ('all','nonbonded') else None}}
        if p==points:baselines[f].append(deepcopy(r))
        return r
    e=evaluate(points,'all');baselines['all'].clear();e.update(gradient_norm=math.sqrt(sum(v*v for v in e['gradient'])),terms={'bond_residual_sum':e['target'],'nonbonded_residual_sum':0.})
    n['energy_inventory']['snapshots']=[deepcopy(e),deepcopy(e)]
    q=n['gradient_inventory'];q['manager_sha256']=_manager_digest(n)
    q['gradient_audit']=audit_gradients(evaluate,{'initial':points},[0,1],references={'initial':{k:e[k] for k in ('target','gradient_norm')}},max_calls=2000)
    q['baseline_evaluations']=baselines
    return n


def evidence():
    from nasolve.cif_selected_geometry import SelectedCoordinates,POLICY_ID
    from nasolve.cif_mixed_gradient import _manager_digest
    n=numerical_capture();points=deepcopy(n['geometry']['sites_cart_exact']);points[1][0]=.75
    endpoint=numerical_capture(points);a=n['energy_inventory']['snapshots'][0];b=endpoint['energy_inventory']['snapshots'][0]
    space=SelectedCoordinates(n['geometry']['sites_cart_exact'],[0,1]);x=space.pack(space.points);y=space.pack(points)
    spec={'schema_version':1,'policy_id':POLICY_ID,'moving_indices':[0,1],'max_iterations':1,'max_calls':20,'manager_sha256':_manager_digest(n)}
    sources=deepcopy(n['gradient_inventory']['installed_numeric_sources'])+[{'module':m,'historical_path':'/unavailable/'+m,'sha256':'c'*64} for m in ['scitbx.lbfgs','scitbx_lbfgs_ext']]
    pair={'target':b['target'],'gradient':b['gradient'],'proxy_counts':b['proxy_counts'],'pairs':[],
          'nonbonded_target':0.,'nonbonded_gradient':[0.]*12,'nonbonded_membership':[],
          'function_parameters':{'class':'prolsq_repulsion_function','c_rep':16.,'k_rep':1.,'irexp':1.,'rexp':4.}}
    r={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','normalization':False,'automatic_adoption':False,'scientific_approval':'NOT_RUN','refinement':'NOT_RUN',
       'moving_indices':[0,1],'manager_sha256':spec['manager_sha256'],'trace':[{'selected_coordinates':p[:],'snapshot':deepcopy(e)} for p,e in [(x,a),(x,a),(y,b),(y,b),(y,b),(y,b)]],
       'initial':deepcopy(a),'final':deepcopy(b),'serialized':deepcopy(b),'final_sites_cart':points,'full_precision_inventory':endpoint,
       'full_precision_inventory_origin':'FIXED_MANAGER_EVALUATION_NOT_REINTERPRETATION','constraint_signature_before':'b'*64,'constraint_signature_after':'b'*64,
       'optimizer_sources':sources,'optimizer_sources_after':deepcopy(sources),'evaluation_calls':6,
       'stopping':{'reason':'max_iterations','error':None,'iterations':1,'calls':2,'max_iterations':1,'native_criterion_met':False},
       'accepted_steps':[{'iteration':1,'native_calls':2,'trace_index':2}],
       'serialized_pair_inventory':{'schema_version':1,'policy_id':'cif-native-nonbonded-attribution-v1','status':'RECORDED','normalization':False,
           'symmetry_scope':'IDENTITY_ONLY','evaluation_calls':2,'pair_kernel_calls':2,'max_pair_kernel_calls':5000,'snapshots':[deepcopy(pair),deepcopy(pair)]}}
    return n,spec,r,'lbfgs minimizer stop: max_iterations\n'


def test_limit_and_energy_improvement_do_not_accept_a_geometry_candidate():
    from nasolve.cif_selected_geometry import review_selected_result
    n,s,r,log=evidence();before=deepcopy(r);q=review_selected_result(r,n,s,log)
    assert q['stopping_classification']=='NOT_CONVERGED_LIMIT' and q['final_target']<q['initial_target']
    assert q['endpoint_sampled_derivatives_pass'] and not q['automatic_adoption'] and not q['geometry_accepted'] and r==before


@pytest.mark.parametrize('defect',['schema','spec_schema','policy','approval','manager','selected','flank','budget','budget_bool','calls','trace_vector','trace_nan',
 'trace_gradient','trace_norm','trace_count','initial','final','serialized','repeat','endpoint_fields','endpoint_flags','endpoint_source','signature',
 'source_repeat','source_missing','stop_reason','stop_calls','stop_iterations','stop_bool','history_missing','history_index','pairs'])
def test_inconsistent_or_rebound_optimizer_evidence_refuses(defect):
    from nasolve.cif_selected_geometry import review_selected_result
    n,s,r,log=evidence()
    if defect=='schema':r['schema_version']=True
    if defect=='spec_schema':s['schema_version']=True
    if defect=='policy':r['policy_id']='wrong'
    if defect=='approval':r['automatic_adoption']=True
    if defect=='manager':s['manager_sha256']='d'*64
    if defect=='selected':s['moving_indices']=[0,2]
    if defect=='flank':r['final_sites_cart'][2][0]=9.
    if defect=='budget':s['max_calls']=5
    if defect=='budget_bool':s['max_calls']=True
    if defect=='calls':r['evaluation_calls']=5
    if defect=='trace_vector':r['trace'][1]['selected_coordinates'].pop()
    if defect=='trace_nan':r['trace'][1]['snapshot']['target']=math.nan
    if defect=='trace_gradient':r['trace'][1]['snapshot']['gradient'].pop()
    if defect=='trace_norm':r['trace'][1]['snapshot']['gradient_norm']=99.
    if defect=='trace_count':r['trace'][1]['snapshot']['proxy_counts']['n_bond_proxies']=True
    if defect=='initial':r['initial']['target']=1.
    if defect=='final':r['final']['target']=1.
    if defect=='serialized':r['trace'][-1]['selected_coordinates'][0]=.001
    if defect=='repeat':r['trace'][-2]['snapshot']['target']=1.
    if defect=='endpoint_fields':r['full_precision_inventory']['restraint_policy']['secondary_structure_enabled']=True
    if defect=='endpoint_flags':r['full_precision_inventory']['gradient_inventory']['gradient_audit']['cases']['initial']['sampled_gradients_consistent']=False
    if defect=='endpoint_source':r['full_precision_inventory']['gradient_inventory']['manager_sha256']='d'*64
    if defect=='signature':r['constraint_signature_after']='d'*64
    if defect=='source_repeat':r['optimizer_sources_after'][0]['sha256']='d'*64
    if defect=='source_missing':r['optimizer_sources'].pop()
    if defect=='stop_reason':r['stopping']['reason']='traditional_convergence_test'
    if defect=='stop_calls':r['stopping']['calls']+=1
    if defect=='stop_iterations':r['stopping']['iterations']+=1
    if defect=='stop_bool':r['stopping']['native_criterion_met']=1
    if defect=='history_missing':r['accepted_steps']=[]
    if defect=='history_index':r['accepted_steps'][0]['trace_index']=5
    if defect=='pairs':r['serialized_pair_inventory']['snapshots'][0]['target']+=1.
    with pytest.raises(ValueError):review_selected_result(r,n,s,log)


def model_file(path,native):
    lines=['REMARK synthetic selected-coordinate regression\n']
    for i,a in enumerate(native['atoms'],1):
        x,y,z=a['xyz'];lines.append(f"HETATM{i:5d} {a['atom_id']:>4} ZZZ Z   9    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {a['element']:>2}\n")
    path.write_text(''.join(lines));return path


def test_selected_serialization_preserves_noncanonical_fixed_records_and_identity_order(tmp_path):
    from nasolve.cif_selected_geometry import selected_model_bytes
    n,s,r,_=evidence();p=model_file(tmp_path/'start.pdb',n);lines=p.read_bytes().splitlines(keepends=True)
    # Noncanonical coordinate spacing and reversed PDB ordering must survive on fixed atoms.
    lines[3]=lines[3][:30]+b'   0.000'+lines[3][38:];p.write_bytes(lines[0]+b''.join(lines[:0:-1]));before=p.read_bytes()
    output=selected_model_bytes(p,n,r['final_sites_cart'],s['moving_indices'])
    for a,b in zip(before.splitlines(),output.splitlines()):
        if a[:6]!=b'HETATM' or a[12:16].strip() in [b'O',b'P']:assert a==b
        else:assert a[:30]+a[54:]==b[:30]+b[54:]
    assert p.read_bytes()==before


@pytest.mark.parametrize('mode',['timeout','failed','omitted'])
def test_driver_preserves_owned_failure_attempts_and_never_creates_candidate(tmp_path,monkeypatch,mode):
    import json,os,sys
    from pathlib import Path
    import nasolve.cif_selected_geometry as g
    n,_,_,_=evidence();source=tmp_path/'source';source.mkdir();model=model_file(source/'model.pdb',n)
    spec={'model':'model.pdb','dictionaries':[],'phil_files':[],'gradient_indices':[0,1]}
    (source/'native_spec.json').write_text(json.dumps(spec));(source/'native_worker.py').write_text('synthetic')
    receipt=source/'native_receipt.json';receipt.write_text(json.dumps({'native_validation':n}))
    frozen={p:p.read_bytes() for p in source.iterdir()}
    monkeypatch.setattr(g,'_start',lambda p:({},n,model,frozen))
    if mode=='timeout':worker='import time\ntime.sleep(30)\n'
    elif mode=='failed':worker='from pathlib import Path\nimport json,sys\nPath("selected_result.json").write_text(json.dumps({"status":"FAILED","error":"synthetic preserved failure"}))\nsys.exit(2)\n'
    else:worker='pass\n'
    monkeypatch.setattr(g,'selected_geometry_worker',lambda:worker)
    root=g.run_selected_geometry(receipt,tmp_path/'output',Path(sys.executable),environment=os.environ,phenix_version='synthetic',moving_indices=[0,1],timeout_seconds=1)
    q=json.loads((root/'receipt.json').read_text());assert q['status']=='FAILED' and not(root/'candidate.pdb').exists()
    assert all(p.read_bytes()==b for p,b in frozen.items()) and (root/'native.log').exists()
    if mode=='timeout':assert q['execution']['status']=='TIMED_OUT'
    else:assert 'error' in q


@pytest.mark.parametrize('defect',[None,'candidate','bootstrap','worker','helper','receipt','extra','symlink'])
def test_reader_relocates_and_rejects_rehashed_inconsistent_packages(tmp_path,monkeypatch,defect):
    import json,shutil
    from pathlib import Path
    import nasolve.cif_selected_geometry as g
    n,s,r,log=evidence();original=tmp_path/'original';original.mkdir()
    start=original/'start';start.mkdir();model_file(start/'model.pdb',n)
    ns={'model':'model.pdb','dictionaries':[],'phil_files':[],'gradient_indices':[0,1]}
    g._save(start/'native_spec.json',ns);g._save(start/'native_receipt.json',{'native_validation':n})
    bootstrap=original/'bootstrap';bootstrap.mkdir();shutil.copy2(start/'model.pdb',bootstrap/'model.pdb')
    g._save(bootstrap/'native_spec.json',{k:v for k,v in ns.items() if k!='gradient_indices'})
    g._save(bootstrap/'native_validation.json',n)
    (bootstrap/'native_worker.py').write_text(g.native_energy_worker(g._NATIVE_WORKER))
    (original/'selected_worker.py').write_text(g.selected_geometry_worker())
    (original/'gradient_helpers.py').write_text(g._gradient_helper_source())
    (original/'nonbonded_helpers.py').write_text(g._pair_helper_source())
    g._save(original/'selected_spec.json',s);g._save(original/'selected_result.json',r)
    (original/'minimizer.log').write_text(log)
    (original/'candidate.pdb').write_bytes(g.selected_model_bytes(start/'model.pdb',n,r['final_sites_cart'],s['moving_indices']))
    receipt={'schema_version':1,'policy_id':g.POLICY_ID,'status':'REVIEW','source_preserved':True,'automatic_adoption':False,
             'execution':{'status':'COMPLETED','returncode':0},'files':g._files(original)}
    g._save(original/'receipt.json',receipt)
    moved=original.rename(tmp_path/'moved');assert not original.exists()
    # Capture authenticity has its own tests; exercise this package reader with a synthetic bound manager.
    monkeypatch.setattr(g,'_start',lambda p:({},n,Path(p).parent/'model.pdb',{}))
    monkeypatch.setattr(g.subprocess,'Popen',lambda *a,**k:pytest.fail('Reader must not execute a process'))
    if defect=='candidate':(moved/'candidate.pdb').write_bytes((moved/'candidate.pdb').read_bytes()+b'REMARK altered\n')
    if defect=='bootstrap':(moved/'bootstrap/model.pdb').write_bytes(b'changed')
    if defect=='worker':(moved/'selected_worker.py').write_text('pass')
    if defect=='helper':(moved/'gradient_helpers.py').write_text('pass')
    if defect=='receipt':receipt['execution']['returncode']=True
    if defect=='extra':(moved/'unrecorded.txt').write_text('extra')
    if defect=='symlink':(moved/'link').symlink_to(moved/'candidate.pdb')
    if defect not in ('extra','symlink'):receipt['files']=g._files(moved)
    g._save(moved/'receipt.json',receipt)
    before={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    if defect:
        with pytest.raises(ValueError):g.read_selected_geometry(moved)
    else:
        q=g.read_selected_geometry(moved)
        assert q['fixed_coordinates_preserved'] and q['native_execution']=='NOT_RUN_BY_READER'
    assert before=={p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
