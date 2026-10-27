"""Synthetic run-bound integration controls; no unpublished coordinates."""
import json
import hashlib
from pathlib import Path
import shutil
import os
import subprocess
import sys

import pytest

from nasolve.metal.context import read_pdb, load_run_context
from nasolve.metal.scattering import observation_metadata
from nasolve.metal.export import export_restraints
from nasolve.metal import RecipeError
from nasolve.metal import Atom, AtomKey, ModelSnapshot, Recipe, preview
from nasolve.metal.export import atom_selection


def pdb_atom(serial, name, component, chain, residue, xyz, element, *, alt='', insertion='', q=1, b=20):
    return (f'HETATM{serial:5d} {name:>4s}{alt:1s}{component:>3s} {chain:1s}{residue:4d}{insertion:1s}   '
            f'{xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}{q:6.2f}{b:6.2f}          {element:>2s}  \n')


def test_pdb_import_retains_exact_identity_and_atomic_state(tmp_path):
    path = tmp_path / 'model.pdb'
    raw = pdb_atom(1, "C1'", 'DF', 'A', 12, (1, 2, 3), 'C', alt='A', insertion='B', q=.6, b=17)
    path.write_text(raw)
    imported = read_pdb(path, checkpoint_id='postmr')
    atom = imported.snapshot.atoms[0]
    assert atom.key.atom_name == "C1'"
    assert atom.key.altloc == 'A' and atom.key.insertion_code == 'B'
    assert imported.snapshot.source_sha256 == hashlib.sha256(raw.encode()).hexdigest()
    assert imported.to_dict()['atomic_state'][0]['occupancy'] == .6
    assert imported.to_dict()['atomic_state'][0]['b_iso'] == 17
    assert path.read_text() == raw


@pytest.mark.parametrize('mutation', ['duplicate', 'missing_element', 'bad_xyz', 'multiple_models'])
def test_pdb_import_rejects_silent_identity_or_numeric_loss(tmp_path, mutation):
    raw = pdb_atom(1, 'S1', 'DF', 'A', 12, (1, 2, 3), 'S')
    if mutation == 'duplicate': raw += raw
    elif mutation == 'missing_element': raw = raw[:76] + '    \n'
    elif mutation == 'bad_xyz': raw = raw[:30] + '     nan' + raw[38:]
    else: raw = 'MODEL        1\n' + raw + 'ENDMDL\nMODEL        2\n' + raw + 'ENDMDL\n'
    path = tmp_path / 'model.pdb'
    path.write_text(raw)
    with pytest.raises(RecipeError): read_pdb(path)


def mtz_dump(wavelength='1.234', duplicate=False):
    output = '''Space group from matrices: R 3 :H (No. 146)
Resolution range: 50 3.5
Crystal 1:
  Name: HKL_base
  Dataset 1:
    Name: HKL_base
    Id: 0
    Wavelength: 9.999
    H 10 100.00% 0 5 H: index
Crystal 2:
  Name: data
  Dataset 1:
    Name: measured
    Id: 1
    Wavelength: LAMBDA
    F(+) 10 100.00% 1 5 G: amplitude
    SIGF(+) 10 100.00% 1 5 L: sigma
    F(-) 9 90.00% 1 5 G: amplitude
    SIGF(-) 9 90.00% 1 5 L: sigma
    FreeR_flag 10 100.00% 0 19 I: integer
'''.replace('LAMBDA', wavelength)
    if duplicate: output += output[output.index('Crystal 2:'):].replace('Id: 1', 'Id: 2')
    return output


def test_wavelength_belongs_to_observation_quartet_not_hkl_base():
    result = observation_metadata(mtz_dump())
    assert result['wavelength_A'] == 1.234
    assert result['dataset_id'] == 1
    assert result['anomalous_labels'] == ['F(+)', 'SIGF(+)', 'F(-)', 'SIGF(-)']
    assert result['free_r_label'] == 'FreeR_flag'


@pytest.mark.parametrize('output', [mtz_dump('nan'), mtz_dump('0'), mtz_dump('9.999'), mtz_dump(duplicate=True), mtz_dump().replace('F(-) 9', 'F(-) 0'), mtz_dump().replace('FreeR_flag', 'unknown')])
def test_ambiguous_or_incomplete_observation_metadata_is_rejected(output):
    with pytest.raises(RecipeError): observation_metadata(output)


def write_run(root):
    run = root / 'dataset' / 'AutoMR' / 'run_001'
    run.mkdir(parents=True)
    model = run / 'prepared.pdb'
    model.write_text(pdb_atom(1, 'S1', 'DF', 'A', 12, (0, 0, 0), 'S') + pdb_atom(2, 'N3', 'DT', 'B', 4, (4, 0, 0), 'N'))
    observations = run.parent.parent / 'observations.mtz'
    observations.write_bytes(b'synthetic observations')
    report = {'workflow': 'automr', 'frame': {'name': 'W'}, 'inputs': {'reflections': str(observations), 'reflections_sha256': hashlib.sha256(observations.read_bytes()).hexdigest()}, 'postmr': {'status': 'POSTMR_READY', 'prepared_model': str(model), 'prepared_sha256': hashlib.sha256(model.read_bytes()).hexdigest()}, 'post_mr_plan': {'allow_op3_sites': [], 'standard_pair': {'ligand_codes': ['DF', 'DT']}}}
    (run / 'report.json').write_text(json.dumps(report))
    return run


def test_context_uses_generated_pair_and_does_not_create_registry(tmp_path):
    run = write_run(tmp_path)
    result = load_run_context(run, records=[{'Ligand code': 'DF', 'O2': 'S2'}, {'Ligand code': 'DT', 'N3': 'N3'}])
    doc = result.to_dict()
    assert doc['residue_slots']['first']['component_id'] == 'DF'
    assert doc['residue_slots']['second']['chain_id'] == 'B'
    assert result.roles.resolve('DF', 'O2')[0] == 'S1'
    assert doc['fixed_f_prime'] is True and doc['native_ready'] is False
    assert not (run / 'AutoRefine').exists()
    assert doc['sources']['model']['anchor'] == 'run'


def test_context_relocation_uses_declared_anchors_and_keeps_identity(tmp_path):
    original = tmp_path / 'original'
    run = write_run(original)
    records = [{'Ligand code': 'DF', 'O2': 'S2'}, {'Ligand code': 'DT', 'N3': 'N3'}]
    before = load_run_context(run, records=records).to_dict()
    relocated = tmp_path / 'relocated'
    shutil.copytree(original, relocated)
    shutil.rmtree(original)
    after = load_run_context(relocated / 'dataset/AutoMR/run_001', records=records).to_dict()
    assert before == after


def test_model_checksum_change_is_not_accepted(tmp_path):
    run = write_run(tmp_path)
    with (run / 'prepared.pdb').open('a') as handle: handle.write('REMARK changed\n')
    with pytest.raises(RecipeError, match='checksum'):
        load_run_context(run, records=[])


def test_export_requires_resolved_preview():
    with pytest.raises(RecipeError): export_restraints({'status': 'draft'})


def concrete_preview():
    keys = [AtomKey(model_id='1', chain_id='A', residue_id='12', component_id='DF', atom_name="C1'"),
            AtomKey(model_id='1', chain_id='M', residue_id='1', component_id='HG', atom_name='HG'),
            AtomKey(model_id='1', chain_id='B', residue_id='4', component_id='DT', atom_name='N3')]
    atoms = [Atom(key, symbol, xyz) for key, symbol, xyz in zip(keys, ['C', 'Hg', 'N'], [(0,0,0), (2,0,0), (2,2,0)])]
    doc = {'kind':'metal-restraint-recipe', 'schema_version':1, 'id':'test', 'name':'Synthetic export', 'revision':1,
           'nodes':[{'id':name, 'kind':'atom'} for name in ['a','m','b']],
           'sets':[{'id':'main', 'name':'Synthetic', 'enabled':True}],
           'restraints':[{'id':'distance', 'set_id':'main', 'kind':'distance', 'nodes':['a','m'], 'target':2.0, 'sigma':.1, 'unit':'angstrom', 'enabled':True, 'source':{'kind':'user', 'note':'Synthetic control'}},
                         {'id':'angle', 'set_id':'main', 'kind':'angle', 'nodes':['a','m','b'], 'target':90.0, 'sigma':3.0, 'unit':'degree', 'enabled':True, 'source':{'kind':'user', 'note':'Synthetic control'}}]}
    return preview(Recipe(doc), model=ModelSnapshot(tuple(atoms), 'a'*64), residue_slots={}, atom_bindings=dict(zip(['a','m','b'], keys)))


def test_export_preserves_requested_distances_angles_and_prime_names():
    text = export_restraints(concrete_preview())
    assert 'refinement.geometry_restraints.edits {' in text
    assert 'distance_ideal = 2' in text and 'angle_ideal = 90' in text
    assert 'sigma = 0.1' in text and 'sigma = 3' in text
    assert "name C1'" in text
    assert "altloc ' '" in text and "segid '    '" in text
    assert 'model ' not in text


@pytest.mark.parametrize('section', ['target', 'identity', 'fingerprint'])
def test_export_replays_instead_of_trusting_modified_preview(section):
    result = concrete_preview()
    if section == 'target': result['restraints'][0]['target'] = 10
    elif section == 'identity': result['nodes'][0]['atom']['key']['chain_id'] = 'Z'
    else: result['input_sha256'] = 'b'*64
    with pytest.raises(RecipeError): export_restraints(result)


@pytest.mark.parametrize('name', ['*', 'N?', 'C[12]', 'N3 and all', '"N3"', "'N3"])
def test_selector_refuses_wildcards_or_expression_characters(name):
    key = AtomKey(model_id='1', chain_id='A', residue_id='12', component_id='DF', atom_name=name)
    with pytest.raises(RecipeError): atom_selection(key)


def test_non_w_frame_has_no_implicit_standard_site_mapping(tmp_path):
    run = write_run(tmp_path)
    report = json.loads((run/'report.json').read_text()); report['frame'] = {'name':'other'}
    (run/'report.json').write_text(json.dumps(report))
    with pytest.raises(RecipeError, match='W/5W6W'): load_run_context(run, records=[])


def test_requested_checkpoint_is_explicit_not_latest(tmp_path):
    run = write_run(tmp_path)
    with pytest.raises(RecipeError, match='Unknown checkpoint'):
        load_run_context(run, checkpoint='refine-999', records=[])


def test_w_alternate_pair_is_reported_instead_of_collapsed(tmp_path):
    run = write_run(tmp_path)
    model=run/'prepared.pdb'; model.write_text(model.read_text()+pdb_atom(3,'S1','DF','A',12,(0,0,0),'S',alt='A'))
    report=json.loads((run/'report.json').read_text());report['postmr']['prepared_sha256']=hashlib.sha256(model.read_bytes()).hexdigest()
    (run/'report.json').write_text(json.dumps(report))
    with pytest.raises(RecipeError, match='ambiguous'): load_run_context(run, records=[])


def test_cli_rejects_existing_output_before_native_work(tmp_path, capsys):
    from nasolve.cli import main
    output=tmp_path/'existing.json';output.write_text('keep')
    assert main(['metal','inspect',str(tmp_path/'not-a-run'),'--output',str(output)]) == 2
    assert output.read_text() == 'keep'
    assert 'new files' in capsys.readouterr().err


def test_cli_preview_binds_to_source_and_keeps_original_model(tmp_path, monkeypatch, capsys):
    import nasolve.metal.cli as cli
    from nasolve.cli import main
    run=write_run(tmp_path)
    records=[{'Ligand code':'DF','O2':'S2'}, {'Ligand code':'DT','N3':'N3'}]
    context=load_run_context(run, records=records)
    monkeypatch.setattr(cli,'load_run_context',lambda *args,**kwargs: context)
    result=concrete_preview();doc=result['inputs']['recipe']
    doc['nodes']=[{'id':'a','kind':'donor','residue_slot':'first','role':'O2'},
                  {'id':'m','kind':'donor','residue_slot':'second','role':'N3'}]
    doc['restraints']=doc['restraints'][:1]
    recipe=tmp_path/'recipe.json';recipe.write_text(json.dumps(doc))
    output=tmp_path/'preview.json';phil=tmp_path/'proposal.phil'
    before=(run/'prepared.pdb').read_bytes()
    assert main(['metal','preview',str(run),'--recipe',str(recipe),'--output',str(output),'--export',str(phil)]) == 0
    assert json.loads(output.read_text())['restraints'][0]['measured'] == 4
    assert 'distance_ideal = 2' in phil.read_text()
    assert (run/'prepared.pdb').read_bytes() == before
    assert not (run/'AutoRefine').exists()


def test_reference_lookup_records_fixed_fprime_and_rejects_invalid_native_result(monkeypatch):
    import nasolve.metal.scattering as s
    monkeypatch.setattr(s, '_run', lambda *args: 'NASOLVE_SCATTERING='+json.dumps([{'element':'Hg','f_prime':-8.1,'f_double_prime':8.6,'table_sha256':'a'*64,'native_version':'synthetic'}])+'\n')
    result=s.reference_scattering(['Hg'],.92,executable='unused',version='synthetic')
    assert result[0]['f_prime_policy']=='fixed' and result[0]['refined'] is False
    assert result[0]['provider']=='cctbx-sasaki' and result[0]['wavelength_A']==.92
    monkeypatch.setattr(s,'_run',lambda *args:'NASOLVE_SCATTERING=[{"element":"Au","f_prime":0,"f_double_prime":1}]\n')
    with pytest.raises(RecipeError):s.reference_scattering(['Hg'],.92,executable='unused',version='synthetic')


def test_relocated_checkout_and_run_replay_after_original_is_gone(tmp_path):
    original=tmp_path/'original'
    run=write_run(original)
    records=[{'Ligand code':'DF','O2':'S2'}, {'Ligand code':'DT','N3':'N3'}]
    expected=load_run_context(run, records=records).to_dict()
    package=Path(__file__).resolve().parents[1]/'src/nasolve'
    shutil.copytree(package, original/'src/nasolve', ignore=shutil.ignore_patterns('__pycache__'))
    relocated=tmp_path/'relocated'
    shutil.move(original,relocated)
    assert not original.exists()
    script='''import json,sys
from pathlib import Path
import nasolve.metal.context as module
assert Path(module.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
records=[{'Ligand code':'DF','O2':'S2'},{'Ligand code':'DT','N3':'N3'}]
print(json.dumps(module.load_run_context(Path(sys.argv[1])/'dataset/AutoMR/run_001',records=records).to_dict()))
'''
    env=dict(os.environ,PYTHONPATH=str(relocated/'src'),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-B','-c',script,str(relocated)],cwd=tmp_path,env=env,text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)==expected
