"""Synthetic, source-preserving metal hypothesis materialization controls."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import os

import pytest

from nasolve.metal import AtomKey, Recipe, RecipeError
from nasolve.metal.context import load_run_context, read_pdb
from nasolve.metal.materialize import build_hypothesis, verify_hypothesis


def atom(serial, name, component, chain, resid, xyz, symbol, q=1, b=20):
    return (f'HETATM{serial:5d} {name:>4s} {component:>3s} {chain}{resid:4d}    '
            f'{xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}{q:6.2f}{b:6.2f}          {symbol:>2s}  \n')


def control(tmp_path, *, metals=('Hg',), restrained=True, explicit_model=False):
    run=tmp_path/'dataset/AutoMR/run_001';run.mkdir(parents=True)
    raw=atom(1,'S1','DF','A',12,(0,0,0),'S',.7,31)+atom(2,'N3','DT','B',4,(4,0,0),'N')+atom(3,'I','IU','B',8,(10,0,0),'I',.8,40)
    if explicit_model:raw='MODEL        7\n'+raw+'ENDMDL\n'
    raw='CRYST1   40.000   40.000   40.000  90.00  90.00  90.00 P 1\n'+raw+'END\n'
    (run/'model.pdb').write_text(raw)
    observations=run.parent.parent/'observations.mtz';observations.write_bytes(b'synthetic')
    report={'workflow':'automr','frame':{'name':'W'},'inputs':{'reflections':str(observations),'reflections_sha256':hashlib.sha256(observations.read_bytes()).hexdigest()},'postmr':{'status':'POSTMR_READY','prepared_model':str(run/'model.pdb'),'prepared_sha256':hashlib.sha256(raw.encode()).hexdigest()}}
    (run/'report.json').write_text(json.dumps(report))
    context=load_run_context(run,records=[{'Ligand code':'DF','O2':'S2'},{'Ligand code':'DT','N3':'N3'}])
    doc={'kind':'metal-restraint-recipe','schema_version':1,'id':'synthetic','revision':1,'name':'Synthetic placement',
         'nodes':[{'id':'d1','kind':'donor','residue_slot':'first','role':'O2'},{'id':'d2','kind':'donor','residue_slot':'second','role':'N3'}]+[{'id':f'm{i}','kind':'metal','element':symbol} for i,symbol in enumerate(metals,1)],
         'sets':[{'id':'s','name':'Test','enabled':True}],
         'restraints':[{'id':'r','kind':'distance','nodes':['d1','m1'],'set_id':'s','enabled':True,'target':2.0,'sigma':.1,'unit':'angstrom','source':{'kind':'user','note':'Numerical control'}}] if restrained else []}
    recipe=Recipe(doc)
    placement={'kind':'metal-placement-plan','schema_version':1,'context_id':context.to_dict()['context_id'],'recipe_sha256':recipe.sha256,'atoms':{},'sites':[]}
    for i,symbol in enumerate(metals,1):
        placement['sites'].append({'node_id':f'm{i}','key':AtomKey(model_id='7' if explicit_model else '1',chain_id='M',residue_id=str(i),component_id=symbol.upper(),atom_name=symbol.upper()).to_dict(),
                                  'xyz':[2.,float(i-1)*3,0.],'occupancy':.6,'b_iso':25.,'formal_charge':None,'source_note':'Explicit synthetic coordinates'})
    return context,recipe,placement


def test_materialization_adds_only_declared_sites_and_retains_lineage(tmp_path):
    context,recipe,placement=control(tmp_path,metals=('Au','Ag'))
    original=(context.run/'model.pdb').read_bytes()
    result=build_hypothesis(context,recipe,placement)
    path=context.run/result['files']['model']['relative_path']
    assert (context.run/'model.pdb').read_bytes()==original
    assert result['parent']['context_id']==placement['context_id']
    assert result['native_ready'] is False and result['status']=='BUILT_REVIEW'
    imported=read_pdb(path)
    assert [a.element for a in imported.snapshot.atoms]==['S','N','I','Au','Ag']
    assert imported.to_dict()['atomic_state'][:3]==context.imported.to_dict()['atomic_state']
    assert 'END\n'==path.read_text().splitlines(keepends=True)[-1]
    assert not (context.run/'AutoRefine').exists()
    assert verify_hypothesis(context.run,path.parent)==result


def test_explicit_model_and_independent_numbered_hypotheses(tmp_path):
    context,recipe,placement=control(tmp_path,explicit_model=True)
    first=build_hypothesis(context,recipe,placement)
    second=build_hypothesis(context,recipe,placement)
    assert first['hypothesis_id']!=second['hypothesis_id']
    assert 'hypothesis_001/' in first['files']['model']['relative_path']
    assert 'hypothesis_002/' in second['files']['model']['relative_path']
    path=context.run/first['files']['model']['relative_path']
    assert path.read_text().index('HG')<path.read_text().index('ENDMDL')
    assert read_pdb(path).snapshot.atoms[-1].key.model_id=='7'


def test_bare_ter_records_from_readyset_are_preserved(tmp_path):
    context,recipe,placement=control(tmp_path)
    path=context.run/'model.pdb';raw=path.read_text().replace('END\n','TER\nEND\n');path.write_text(raw)
    report=json.loads((context.run/'report.json').read_text());report['postmr']['prepared_sha256']=hashlib.sha256(raw.encode()).hexdigest()
    (context.run/'report.json').write_text(json.dumps(report))
    context=load_run_context(context.run,records=context.roles.records());placement['context_id']=context.to_dict()['context_id']
    result=build_hypothesis(context,recipe,placement)
    assert 'TER\n' in (context.run/result['files']['model']['relative_path']).read_text()


def test_floating_metal_has_explicit_unrestrained_status(tmp_path):
    context,recipe,placement=control(tmp_path,restrained=False)
    result=build_hypothesis(context,recipe,placement)
    assert result['unrestrained_metal_nodes']==['m1']
    assert verify_hypothesis(context.run,context.run/result['files']['model']['relative_path'].rsplit('/',1)[0])==result


@pytest.mark.parametrize('problem',['context','recipe','duplicate','missing','unknown','collision','coordinate_width','nan','occupancy_precision','negative_b','formal_charge','alternate','symmetry','component','model'])
def test_invalid_placement_allocates_nothing(tmp_path,problem):
    context,recipe,placement=control(tmp_path)
    site=placement['sites'][0]
    if problem=='context':placement['context_id']='a'*64
    elif problem=='recipe':placement['recipe_sha256']='b'*64
    elif problem=='duplicate':placement['sites'].append(copy.deepcopy(site))
    elif problem=='missing':placement['sites']=[]
    elif problem=='unknown':site['node_id']='unknown'
    elif problem=='collision':site['key'].update(chain_id='A',residue_id='12')
    elif problem=='coordinate_width':site['xyz'][0]=10000
    elif problem=='nan':site['xyz'][0]=float('nan')
    elif problem=='occupancy_precision':site['occupancy']=.004
    elif problem=='negative_b':site['b_iso']=-1
    elif problem=='formal_charge':site['formal_charge']=True
    elif problem=='alternate':site['key']['altloc']='A'
    elif problem=='symmetry':site['key']['symmetry']='-x,y,z'
    elif problem=='component':site['key']['component_id']='AU'
    else:site['key']['model_id']='2'
    with pytest.raises(RecipeError):build_hypothesis(context,recipe,placement)
    assert not (context.run/'Metal').exists()


def test_pdb_rounding_and_charge_are_explicit_and_preview_uses_readback(tmp_path):
    context,recipe,placement=control(tmp_path)
    placement['sites'][0].update(xyz=[2.0004,0.,0.],formal_charge=2,occupancy=0.)
    result=build_hypothesis(context,recipe,placement)
    assert result['sites'][0]['xyz']==[2.,0.,0.]
    assert result['sites'][0]['coordinate_rounding_A'][0]==pytest.approx(-.0004)
    model=context.run/result['files']['model']['relative_path']
    assert next(l for l in model.read_text().splitlines() if l.startswith('HETATM') and l[17:20].strip()=='HG')[78:80]=='2+'
    preview=json.loads((context.run/result['files']['preview']['relative_path']).read_text())
    assert preview['restraints'][0]['measured']==2.
    assert result['sites'][0]['occupancy']==0.


def test_anisou_and_source_records_survive_verbatim(tmp_path):
    context,recipe,placement=control(tmp_path)
    path=context.run/'model.pdb';raw=path.read_text();line=raw.splitlines(keepends=True)[1]
    anisou='ANISOU'+line[6:28]+''.join(f'{v:7d}' for v in [1000,2000,3000,100,200,300])+line[70:]
    raw=raw.replace(line,line+anisou)
    path.write_text(raw)
    report=json.loads((context.run/'report.json').read_text());report['postmr']['prepared_sha256']=hashlib.sha256(raw.encode()).hexdigest()
    (context.run/'report.json').write_text(json.dumps(report))
    context=load_run_context(context.run,records=context.roles.records());placement['context_id']=context.to_dict()['context_id']
    result=build_hypothesis(context,recipe,placement)
    derived=(context.run/result['files']['model']['relative_path']).read_text()
    retained=''.join(l for l in derived.splitlines(keepends=True) if not (l.startswith('HETATM') and l[21]=='M'))
    assert retained==raw
    assert read_pdb(context.run/result['files']['model']['relative_path']).to_dict()['atomic_state'][0]['anisou']==[1000,2000,3000,100,200,300]


@pytest.mark.parametrize('target',['model','restraints','placement','context','metadata','metadata_type','rehashed_model'])
def test_saved_hypothesis_tampering_is_rejected(tmp_path,target):
    context,recipe,placement=control(tmp_path)
    result=build_hypothesis(context,recipe,placement)
    directory=(context.run/result['files']['model']['relative_path']).parent
    if target in {'metadata','metadata_type'}:
        if target=='metadata':result['sites'][0]['occupancy']=.3
        else:result['native_ready']=0
        (directory/'manifest.json').write_text(json.dumps(result))
    else:
        key='model' if target=='rehashed_model' else target
        path=context.run/result['files'][key]['relative_path']
        with path.open('a') as f:f.write('\n')
        if target=='rehashed_model':
            from nasolve.metal.recipe import digest
            result['files'][key]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            result['files'][key]['size']=path.stat().st_size
            result.pop('hypothesis_id');result['hypothesis_id']=digest(result)
            (directory/'manifest.json').write_text(json.dumps(result))
    with pytest.raises(RecipeError):verify_hypothesis(context.run,directory)


def test_report_progress_is_frozen_but_observation_changes_are_rejected(tmp_path):
    context,recipe,placement=control(tmp_path)
    result=build_hypothesis(context,recipe,placement)
    directory=(context.run/result['files']['model']['relative_path']).parent
    with (context.run/'report.json').open('a') as f:f.write('\n')
    assert verify_hypothesis(context.run,directory)==result
    (context.run.parent.parent/'observations.mtz').write_bytes(b'changed')
    with pytest.raises(RecipeError,match='checksum'):verify_hypothesis(context.run,directory)


def test_failed_publication_keeps_failed_directory_and_does_not_reuse_number(tmp_path,monkeypatch):
    import nasolve.metal.materialize as module
    context,recipe,placement=control(tmp_path)
    original=module._sources;calls=[]
    def fail_second(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise RecipeError('Changed at publication')
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'_sources',fail_second)
    with pytest.raises(RecipeError,match='publication'):build_hypothesis(context,recipe,placement)
    failed=context.run/'Metal/hypothesis_001'
    assert (failed/'failure.json').exists() and not (failed/'manifest.json').exists()
    monkeypatch.setattr(module,'_sources',original)
    result=build_hypothesis(context,recipe,placement)
    assert 'hypothesis_002/' in result['files']['model']['relative_path']


def test_concurrent_builders_allocate_distinct_replayable_bundles(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    context,recipe,placement=control(tmp_path)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda _:build_hypothesis(context,recipe,placement),range(3)))
    assert len({r['hypothesis_id'] for r in results})==3
    for result in results:
        directory=(context.run/result['files']['model']['relative_path']).parent
        assert verify_hypothesis(context.run,directory)==result


def test_changed_parent_allocates_no_hypothesis(tmp_path):
    context,recipe,placement=control(tmp_path)
    with (context.run/'model.pdb').open('a') as handle:handle.write('REMARK changed\n')
    with pytest.raises(RecipeError,match='checksum'):build_hypothesis(context,recipe,placement)
    assert not (context.run/'Metal').exists()


def test_symlink_output_root_does_not_write_elsewhere(tmp_path):
    context,recipe,placement=control(tmp_path)
    elsewhere=tmp_path/'elsewhere';elsewhere.mkdir()
    (context.run/'Metal').symlink_to(elsewhere,target_is_directory=True)
    with pytest.raises(RecipeError,match='symlink'):build_hypothesis(context,recipe,placement)
    assert list(elsewhere.iterdir())==[]


def test_coincident_serialized_sites_are_rejected_before_publication(tmp_path):
    context,recipe,placement=control(tmp_path,metals=('Au','Ag'))
    placement['sites'][1]['xyz']=[2.0004,0,0]
    with pytest.raises(RecipeError,match='coincides'):build_hypothesis(context,recipe,placement)
    assert not (context.run/'Metal').exists()


def test_cli_build_and_verify_share_backend_and_preserve_current_selection(tmp_path,monkeypatch,capsys):
    from nasolve.cli import main
    import nasolve.metal.cli as cli
    context,recipe,placement=control(tmp_path)
    monkeypatch.setattr(cli,'load_run_context',lambda *args,**kwargs:context)
    recipe_path=tmp_path/'recipe.json';recipe_path.write_text(recipe.to_json())
    plan_path=tmp_path/'placement.json';plan_path.write_text(json.dumps(placement))
    assert main(['metal','build',str(context.run),'--recipe',str(recipe_path),'--placement',str(plan_path),'--json'])==0
    built=json.loads(capsys.readouterr().out)
    assert main(['metal','verify',str(context.run),'--hypothesis','Metal/hypothesis_001','--json'])==0
    assert json.loads(capsys.readouterr().out)==built
    assert not (context.run/'AutoRefine').exists()


def test_relocated_source_and_run_replay_without_original_or_live_roles(tmp_path):
    original=tmp_path/'original';context,recipe,placement=control(original)
    expected=build_hypothesis(context,recipe,placement)
    package=Path(__file__).resolve().parents[1]/'src/nasolve'
    shutil.copytree(package,original/'src/nasolve',ignore=shutil.ignore_patterns('__pycache__'))
    relocated=tmp_path/'relocated';shutil.move(original,relocated)
    assert not original.exists()
    script='''import json,sys
from pathlib import Path
import nasolve.metal.materialize as module
assert Path(module.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
run=Path(sys.argv[1])/'dataset/AutoMR/run_001'
print(json.dumps(module.verify_hypothesis(run, 'Metal/hypothesis_001')))
'''
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(relocated/'src'))
    check=subprocess.run([sys.executable,'-B','-c',script,str(relocated)],cwd=tmp_path,env=env,text=True,capture_output=True,timeout=30)
    assert check.returncode==0,check.stderr
    assert json.loads(check.stdout)==expected
