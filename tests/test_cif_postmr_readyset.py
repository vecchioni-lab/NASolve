"""Observed CLI transport exercises real control flow with explicit fake tools."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import sys
from types import SimpleNamespace
import pytest


def setup(tmp_path, monkeypatch, behavior='noop'):
    from tests.test_cif_postmr_cache import prepared
    s,c,q,o,p,entry,installation,ready=prepared(tmp_path,monkeypatch)
    site=installation.root/'lib/python3.11/site-packages'
    ready.write_text('"$LIBTBX_PREFIX/lib/python3.11/site-packages/elbow/command_line/ready_set.py"\n')
    for name in ['elbow/__init__.py','elbow/command_line/__init__.py','elbow/scripts/__init__.py']:
        path=site/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('')
    (site/'elbow/command_line/builder.py').write_text('def run():\n    return None\n')
    (site/'elbow/scripts/elbow_on_pdb_file.py').write_text('def get_elbow_molecule_from_chemical_components():\n    return None\n')
    body={
        'noop':"print('No unknown residues')",
        'builder':"builder.run(); print('No unknown residues')",
        'template':"elbow_on_pdb_file.get_elbow_molecule_from_chemical_components(); print('No unknown residues')",
        'fail':"raise ValueError('EXPLICIT FAKE READYSET FAILURE')",
        'timeout':"import time; time.sleep(3)",
        'truncated':"[builder.run() for _ in range(150)]; print('No unknown residues')",
        'bad_actions':"params.ready_set.actions.hydrogens=True; print('No unknown residues')",
        'mutate':"Path(args[0]).write_text('CHANGED'); print('No unknown residues')",
        'child':"import subprocess; subprocess.run([sys.executable,'-c','pass']); print('No unknown residues')",
    }[behavior]
    text='''from pathlib import Path
from types import SimpleNamespace as S
from elbow.command_line import builder
from elbow.scripts import elbow_on_pdb_file
import sys
def run(args):
    params=S(ready_set=S(actions=S(hydrogens=False,ligands=True,optimise_ligand_geometry=False,optimise_final_geometry_of_hydrogens=False)))
    BODY
    return ([],params)
if __name__=='__main__':
    args=sys.argv[1:];del sys.argv[1:];run(args)
'''.replace('BODY',body)
    (site/'elbow/command_line/ready_set.py').write_text(text)
    exe=installation.executables['phenix.python']
    exe.write_text('#!/bin/sh\nexec "'+sys.executable+'" "$@"\n');exe.chmod(0o755)
    from hashlib import sha256
    o['consumer']['executable_sha256']=sha256(exe.read_bytes()).hexdigest()
    model=tmp_path/'full.pdb'
    model.write_text('HETATM    1  C1  Q17 A   1       0.000   0.000   0.000  1.00 20.00           C\nHETATM    2  H1  Q17 A   1       0.000   0.000   1.000  1.00 20.00           H\nEND\n')
    return s,c,model,installation,o['consumer']


def call(tmp_path,monkeypatch,behavior='noop',**kwargs):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch,behavior)
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control',**kwargs)
    return r,(s,c,model,installation,consumer)


def test_real_ordinary_helper_observed_noop_and_portable_output(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import read_readyset_consumption
    r,inputs=call(tmp_path,monkeypatch)
    assert r['status']=='READYSET_CACHED_INPUT_PASS'
    assert r['ordinary_arguments'][2:5]==['ready_set.actions.hydrogens=False','ready_set.actions.ligands=True','ready_set.actions.optimise_ligand_geometry=False']
    assert r['trace']['builder_calls']==r['trace']['template_calls']==0
    assert r['trace']['argument_overrides']=='NONE' and not r['trace']['truncated']
    assert r['checks']['unchanged_heavy_sites'] and r['checks']['effective_numerics_exact']
    assert r['readyset_output_mode']=='successful-noop'
    assert r['requires_cif_review'] is False
    assert r['invocation']=='SELECTED_LITERAL_READYSET_ENTRYPOINT_WITH_ORDINARY_ARGUMENTS'
    assert r['dispatcher_execution']=='NOT_RUN; SELECTED_PHENIX_PYTHON_OBSERVER_TRANSPORT'
    for path in inputs[:3]:path.unlink()
    shutil.rmtree(inputs[3].root)
    (tmp_path/'control').rename(tmp_path/'relocated')
    loaded=read_readyset_consumption(tmp_path/'relocated')
    assert loaded['report']==r and loaded['dictionary'].is_file()


@pytest.mark.parametrize('behavior',['builder','template','fail','timeout','truncated','bad_actions','child'])
def test_observed_generation_incomplete_or_changed_policy_is_not_pass(tmp_path,monkeypatch,behavior):
    r,inputs=call(tmp_path,monkeypatch,behavior,timeout_seconds=.2 if behavior=='timeout' else 10)
    assert r['status']=='REVIEW'
    assert r['verified_input_retained'] is True and inputs[1].is_file()
    if behavior=='builder':assert r['trace']['builder_calls']==1
    if behavior=='template':assert r['trace']['template_calls']==1
    if behavior=='truncated':assert r['trace']['truncated']
    if behavior=='timeout':assert r['execution']['status']=='TIMED_OUT'
    if behavior=='child':assert r['trace']['subprocess_calls']>=1


def test_frozen_input_mutation_is_detected(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='changed'):
        call(tmp_path,monkeypatch,'mutate')


@pytest.mark.parametrize('timeout',[0,-1,181,float('inf'),True])
def test_timeout_bounds(tmp_path,monkeypatch,timeout):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    with pytest.raises(ValueError):audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control',timeout_seconds=timeout)


def test_inspection_prepares_only_inputs_without_installation(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    shutil.rmtree(installation.root)
    r=audit_readyset_consumption(s,c,model,'Q17',None,consumer,tmp_path/'control')
    assert r['status']=='PREPARED_ONLY' and r['execution']['status']=='NOT_RUN'
    assert not (tmp_path/'control/readyset').exists()


@pytest.mark.parametrize('defect',['source','dictionary','model','traversal','symlink'])
def test_reader_requires_hash_bound_local_copies(tmp_path,monkeypatch,defect):
    from nasolve.cif_postmr_readyset import read_readyset_consumption
    r,_=call(tmp_path,monkeypatch)
    root=tmp_path/'control';ref=r['inputs'][defect if defect in {'source','dictionary','model'} else 'dictionary']
    if defect=='traversal':
        r['inputs']['dictionary']['path']='../elsewhere.cif'
        (root/'readyset_consumption.json').write_text(json.dumps(r))
    elif defect=='symlink':
        path=root/ref['path'];other=tmp_path/'other';other.write_bytes(path.read_bytes());path.unlink();path.symlink_to(other)
    else:(root/ref['path']).write_bytes(b'CORRUPTED')
    with pytest.raises(ValueError):read_readyset_consumption(root)


def test_existing_parameterized_precedence_preserves_cache_against_changed_readyset_copy(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import effective_cached_input
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    generated=tmp_path/'generated.cif';generated.write_bytes(c.read_bytes().replace(b'1.5',b'1.9')+b'\n# EXPLICIT FAKE GENERATED\n')
    out=tmp_path/'effective';out.mkdir()
    selected,checks=effective_cached_input(c,generated,out)
    assert checks['effective_numerics_exact'] and checks['single_effective_dictionary']
    assert selected.read_bytes()==c.read_bytes() and generated.read_bytes()!=c.read_bytes()
