"""Environmental B is a declared branch assumption, never a post-hoc fdp rescale."""
import copy
import json
from pathlib import Path
import pytest
from nasolve.metal import RecipeError
from nasolve.metal.environment import calibrate_b
from nasolve.metal.context import parse_pdb
from tests.test_metal_materialize import atom


def inputs():
    raw = (atom(1,'N3','DA','A',12,(0,0,0),'N',b=170) +
           atom(2,'C2','DA','A',12,(1,0,0),'C',b=230) +
           atom(3,'O2','DT','B',4,(4,0,0),'O',b=300) +
           atom(4,'C2','DT','B',4,(5,0,0),'C',b=400) +
           atom(5,'C4','DT','B',4,(4,1,0),'C',b=350) +
           atom(7,"C1'",'DA','A',12,(0,-1,0),'C',b=999) +
           atom(8,'P','DT','B',4,(5,1,0),'P',b=1) +
           atom(6,'HG','HG','M',1,(2,0,0),'Hg',b=25)).encode()
    keys = [a.key.to_dict() for a in parse_pdb(raw).snapshot.atoms]
    sites = [dict(node_id='m1',key=keys[-1])]
    nodes = [dict(node_id=n,kind=k,atom=dict(key=keys[i])) for n,k,i in [('a','donor',0),('b','donor',2),('m1','metal',7)]]
    terms = [dict(kind='distance',enabled=True,status='resolved',node_ids=[n,'m1']) for n in ('a','b')]
    return raw,sites,dict(nodes=nodes,restraints=terms)


def test_high_b_residue_means_keep_base_mismatch_and_equal_residue_weight():
    raw, sites, preview = inputs()
    report, model = calibrate_b(raw,sites,preview,['m1'],'base-mean')
    row=report['sites'][0]
    assert row['base_means_A2']==[200,350]
    assert row['base_mean_spread_A2']==150
    assert row['applied_b_A2']==275  # Not the atom-count-weighted pooled mean.
    assert len(row['atoms'])==5 and row['policy']=='base-mean'
    before,after=parse_pdb(raw),parse_pdb(model)
    assert before.snapshot.atoms==after.snapshot.atoms
    assert before.to_dict()['atomic_state'][:-1]==after.to_dict()['atomic_state'][:-1]
    assert after.to_dict()['atomic_state'][-1]['b_iso']==275
    assert before.to_dict()['atomic_state'][-1]['b_iso']==25


def test_donor_mean_is_distinct_and_duplicate_edges_do_not_reweight_atoms():
    raw, sites, preview = inputs(); preview['restraints'] *= 2
    report,_=calibrate_b(raw,sites,preview,['m1'],'donor-mean')
    assert report['sites'][0]['applied_b_A2']==235
    assert len(report['sites'][0]['atoms'])==2


def test_missing_ligand_or_anisotropic_metal_requires_explicit_alternative():
    raw, sites, preview=inputs()
    with pytest.raises(RecipeError,match='ligand'):calibrate_b(raw,sites,dict(preview,restraints=[]),['m1'],'base-mean')
    lines=raw.decode().splitlines(keepends=True);line=lines[-1]
    anisou='ANISOU'+line[6:28]+''.join(f'{v:7d}' for v in [1000,2000,3000,0,0,0])+line[70:]
    with pytest.raises(RecipeError,match='anisotropic'):calibrate_b((''.join(lines)+anisou).encode(),sites,preview,['m1'],'donor-mean')
    report, model=calibrate_b(raw,sites,None,['m1'],'keep')
    assert model==raw and report['policy']=='keep'


def test_disabled_edges_and_wrong_atom_identity_cannot_supply_b():
    raw,sites,preview=inputs()
    for r in preview['restraints']:r['enabled']=False
    with pytest.raises(RecipeError):calibrate_b(raw,sites,preview,['m1'],'donor-mean')
    raw,sites,preview=inputs();preview['nodes'][0]['atom']['key']['altloc']='A'
    with pytest.raises(RecipeError):calibrate_b(raw,sites,preview,['m1'],'donor-mean')


def test_new_trial_b_calibration_replays_and_legacy_trial_stays_identical(tmp_path,monkeypatch):
    from tests.test_metal_fdp import fake_execution
    from nasolve.metal.fdp import run_fdp,verify_fdp
    module,context,g,native=fake_execution(tmp_path,monkeypatch)
    legacy=run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'])
    old_files={p:p.read_bytes() for p in (context.run/'Metal/fdp_001').iterdir()}
    new=run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'],metal_b_policy='donor-mean')
    result=json.loads((context.run/new['files']['result.json']['relative_path']).read_text())
    assert result['sites'][0]['b_iso']==31
    assert result['sites'][0]['b_calibration']['policy']=='donor-mean'
    assert verify_fdp(context.run,'Metal/fdp_001')==legacy
    assert verify_fdp(context.run,'Metal/fdp_002')==new
    assert all(p.read_bytes()==data for p,data in old_files.items())
    from nasolve.metal.fdp_compare import build_comparison
    with pytest.raises(RecipeError,match='same geometry'):build_comparison(context.run,['Metal/fdp_001','Metal/fdp_002'])


def test_occupancy_scan_reuses_calibrated_branch_b(tmp_path,monkeypatch):
    from tests.test_metal_fdp import fake_execution
    import nasolve.metal.fdp_scan as scan
    from nasolve.metal.fdp import run_fdp
    module,context,g,native=fake_execution(tmp_path,monkeypatch)
    run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'],metal_b_policy='donor-mean')
    scan.create_plan(context.run,'Metal/fdp_001',{'m1':[.4,.6]},max_trials=2)
    monkeypatch.setattr(scan,'_check_native',lambda *a,**kw:None)
    doc=scan.run_scan(context.run,'Metal/fdp_scan_plan_001',job_budget=1,native=native)
    report=json.loads((context.run/doc['files']['report']['relative_path']).read_text())
    assert all(s['b_iso']==31 for p in report['points'] for s in p['sites'])
    assert scan.verify_scan(context.run,'Metal/fdp_scan_001')==doc


def test_modified_base_graph_includes_substituents_excludes_sugar_and_phosphate():
    from nasolve.metal.chemistry import dictionaries,base_names,display_connections
    cif=b"""data_DF
loop_
_chem_comp_atom.comp_id
_chem_comp_atom.atom_id
_chem_comp_atom.type_symbol
DF C1' C
DF O4' O
DF C2' C
DF P P
DF N1 N
DF C2 C
DF S1 S
DF C7 C
loop_
_chem_comp_bond.atom_id_1
_chem_comp_bond.atom_id_2
C1' O4'
C1' C2'
C2' P
C1' N1
N1 C2
C2 S1
C2 C7
"""
    chemistry=dictionaries([('captured.cif',cif)])
    names,source=base_names('DF',chemistry)
    assert names=={'N1','C2','S1','C7'} and source['kind']=='captured_component_graph'
    with pytest.raises(RecipeError,match='unavailable'):base_names('unknown',{})
    conflicting=cif.replace(b'C2 S1',b'N1 S1')
    with pytest.raises(RecipeError,match='Conflicting'):dictionaries([('a.cif',cif),('b.cif',conflicting)])
    raw,sites,preview=inputs()
    atoms=[dict(a.to_dict()) for a in parse_pdb(raw).snapshot.atoms]
    links=display_connections(atoms,{})
    assert links and all(row['source']=='distance_display_only' for row in links)
    assert all(k['component_id']!='HG' for row in links for k in row['keys'])


def test_branch_preparation_replay_after_source_tree_removed(tmp_path,monkeypatch):
    import os,shutil,subprocess,sys
    from tests.test_metal_fdp import fake_execution
    from nasolve.metal.fdp import run_fdp
    source=tmp_path/'original'
    module,context,g,native=fake_execution(source,monkeypatch)
    doc=run_fdp(context.run,'Metal/geometry_001',native=native,fit_nodes=['m1'],metal_b_policy='donor-mean')
    shutil.copytree(Path(__file__).resolve().parents[1]/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    moved=tmp_path/'relocated';source.rename(moved);assert not source.exists()
    code="""import json,subprocess
from pathlib import Path
from nasolve.metal.fdp import verify_fdp
subprocess.run=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('No native replay'))
print(json.dumps(verify_fdp(Path('dataset/AutoMR/run_001'),'Metal/fdp_001')))
"""
    done=subprocess.run([sys.executable,'-B','-c',code],cwd=moved,env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
    assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)==doc
