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


@pytest.mark.parametrize('generate',[False,True])
def test_observed_builder_is_captured_when_only_imported_by_routing_module(tmp_path,monkeypatch,generate):
    """The installed ReadySet layout reaches builder through a non-ReadySet module."""
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch,'builder' if generate else 'noop')
    site=installation.root/'lib/python3.11/site-packages'
    ready=site/'elbow/command_line/ready_set.py'
    ready.write_text(ready.read_text().replace('from elbow.command_line import builder\n','').replace('builder.run()','elbow_on_pdb_file.call_builder()'))
    route=site/'elbow/scripts/elbow_on_pdb_file.py'
    route.write_text(route.read_text()+'\nfrom elbow.command_line import builder\ndef call_builder():\n    return builder.run()\n')
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    assert r['status']==('REVIEW' if generate else 'READYSET_CACHED_INPUT_PASS')
    assert r['trace']['builder_calls']==int(generate)
    proof=r['source_evidence']
    assert proof['explicit_observer_sources']==['lib/python3.11/site-packages/elbow/command_line/builder.py']
    row=next(v for v in proof['sources'] if v['path'].endswith('/elbow/command_line/builder.py'))
    assert (tmp_path/'control/source_evidence'/row['snapshot']['path']).read_bytes()==(site/'elbow/command_line/builder.py').read_bytes()


@pytest.mark.parametrize('defect',['missing','escaped','oversized','changed_after_capture'])
def test_explicit_observer_sources_keep_existing_proof_guards(tmp_path,monkeypatch,defect):
    import nasolve.cif_postmr_readyset as api
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    site=installation.root/'lib/python3.11/site-packages';ready=site/'elbow/command_line/ready_set.py'
    ready.write_text(ready.read_text().replace('from elbow.command_line import builder\n',''))
    builder=site/'elbow/command_line/builder.py'
    if defect=='missing':builder.unlink()
    elif defect=='escaped':
        outside=tmp_path/'outside.py';outside.write_bytes(builder.read_bytes());builder.unlink();builder.symlink_to(outside)
    elif defect=='oversized':builder.write_bytes(b'#'+b'x'*api.MAX_SOURCE_BYTES)
    else:
        original=api._capture_consumption_sources
        def capture(*args):
            result=original(*args);builder.write_bytes(b'# CHANGED AFTER CAPTURE\n');return result
        monkeypatch.setattr(api,'_capture_consumption_sources',capture)
    with pytest.raises((ValueError,OSError)):
        api.audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    assert not (tmp_path/'control/readyset/consumption_result.json').exists()


def test_import_time_child_records_literal_command_and_callers_without_environment(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    ready=installation.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
    command=[str(sys.executable),'-c','pass','argument with spaces']
    ready.write_text(ready.read_text().replace("import sys\n", "import sys,os,subprocess\nsubprocess.run("+repr(command)+",cwd=str(Path.cwd()),env=dict(os.environ,PRIVATE_OBSERVER_TEST='DO_NOT_CAPTURE_ENVIRONMENT'))\n"))
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    assert r['status']=='REVIEW' and r['checks']['readyset_completed']
    assert r['trace']['builder_calls']==0 and r['trace']['subprocess_calls']==1
    event=next(v for v in r['trace']['events'] if v['kind']=='subprocess')
    observed=event['process']
    assert observed['args']==command and observed['shell'] is False and observed['executable'] is None
    assert observed['cwd']==str(tmp_path/'control/readyset') and observed['parameters_complete']
    assert any(v['source']==str(ready) and v['function']=='<module>' for v in observed['callers'])
    assert observed['environment']=='NOT_CAPTURED' and 'DO_NOT_CAPTURE_ENVIRONMENT' not in json.dumps(r['trace'])
    assert r['trace']['argument_overrides']=='NONE'


def test_shell_child_keeps_command_and_executable_distinct_and_still_requires_review(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    ready=installation.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
    ready.write_text(ready.read_text().replace("print('No unknown residues')", "import subprocess; subprocess.run(':',shell=True,executable='/bin/sh'); print('No unknown residues')"))
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    observed=next(v['process'] for v in r['trace']['events'] if v['kind']=='subprocess')
    assert observed['args']==':' and observed['executable']=='/bin/sh' and observed['shell'] is True
    assert observed['parameters_complete'] and r['checks']['no_unclassified_subprocess_calls'] is False and r['status']=='REVIEW'


@pytest.mark.parametrize('large',['string','items'])
def test_large_child_command_is_bounded_without_changing_native_arguments(tmp_path,monkeypatch,large):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    ready=installation.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
    arguments=[sys.executable,'-c','pass',*(['x'*9000] if large=='string' else ['x']*90)]
    ready.write_text(ready.read_text().replace("print('No unknown residues')", "import subprocess; subprocess.run("+repr(arguments)+"); print('No unknown residues')"))
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    observed=next(v['process'] for v in r['trace']['events'] if v['kind']=='subprocess')
    assert r['checks']['readyset_completed'] and r['status']=='REVIEW'
    assert observed['parameters_complete'] is False and observed['truncated']
    assert len(observed['args'])<=64 and len(json.dumps(observed['args']))<10000


def test_observer_does_not_coerce_custom_child_argument_objects(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    ready=installation.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
    definition="class Argument:\n    def __repr__(self):raise AssertionError('OBSERVER_MUST_NOT_CALL_REPR')\n    def __str__(self):raise AssertionError('OBSERVER_MUST_NOT_CALL_STR')\n    def __fspath__(self):return 'native argument'\n"
    ready.write_text(ready.read_text().replace('def run(args):',definition+'def run(args):').replace("print('No unknown residues')", "import subprocess; subprocess.run([sys.executable,'-c','pass',Argument()]); print('No unknown residues')"))
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    observed=next(v['process'] for v in r['trace']['events'] if v['kind']=='subprocess')
    assert r['checks']['readyset_completed'] and r['status']=='REVIEW'
    assert observed['args'][-1]=={'unsupported_type':'Argument'} and observed['parameters_complete'] is False


def test_byte_child_arguments_are_recorded_losslessly_without_decoding(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    ready=installation.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
    command=[str(sys.executable).encode(),b'-c',b'pass',b'non_utf8_\xff']
    ready.write_text(ready.read_text().replace("print('No unknown residues')", "import subprocess; subprocess.run("+repr(command)+"); print('No unknown residues')"))
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    observed=next(v['process'] for v in r['trace']['events'] if v['kind']=='subprocess')
    assert r['checks']['readyset_completed'] and r['status']=='REVIEW' and observed['parameters_complete']
    assert observed['args']==[{'encoding':'hex','value':v.hex()} for v in command]


def test_deep_child_callers_are_bounded_and_marked_separately(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    s,c,model,installation,consumer=setup(tmp_path,monkeypatch)
    ready=installation.root/'lib/python3.11/site-packages/elbow/command_line/ready_set.py'
    helper="def child(depth):\n    if depth:return child(depth-1)\n    import subprocess\n    return subprocess.run([sys.executable,'-c','pass'])\n"
    ready.write_text(ready.read_text().replace('def run(args):',helper+'def run(args):').replace("print('No unknown residues')", "child(40); print('No unknown residues')"))
    r=audit_readyset_consumption(s,c,model,'Q17',installation,consumer,tmp_path/'control')
    observed=next(v['process'] for v in r['trace']['events'] if v['kind']=='subprocess')
    assert r['checks']['readyset_completed'] and r['status']=='REVIEW' and observed['parameters_complete']
    assert len(observed['callers'])==16 and observed['callers_truncated'] is True
