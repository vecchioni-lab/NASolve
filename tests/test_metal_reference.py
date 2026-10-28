"""Human models are geometric reference snapshots, never stored-fdp authority."""
import copy
import hashlib
import json
from pathlib import Path
import pytest

from nasolve.metal import RecipeError
from nasolve.metal.context import parse_pdb
from nasolve.metal.geometry import prepare_geometry
from nasolve.metal.materialize import build_hypothesis, _json_bytes
from nasolve.metal.reference import inspect_reference, compare_reference, verify_reference_comparison
from tests.test_metal_materialize import control, atom


def setup(tmp_path, *, angle=False):
    context, recipe, placement = control(tmp_path)
    if angle:
        from nasolve.metal import Recipe
        data = recipe.to_dict()
        data['restraints'].append(dict(id='a', kind='angle', nodes=['d1','m1','d2'], set_id='s',
                                      enabled=True, target=180., sigma=10., unit='degree', source={'kind':'user','note':'Synthetic angle control'}))
        recipe = Recipe(data); placement['recipe_sha256'] = recipe.sha256
    hypothesis = build_hypothesis(context, recipe, placement)
    geometry = prepare_geometry(context.run, Path(hypothesis['files']['model']['relative_path']).parent)
    model = (context.run/geometry['files']['model']['relative_path']).read_bytes()
    parsed = parse_pdb(model)
    lines = ['REMARK 3 UNTRUSTED f_double_prime = 999.0\n']
    mapping = {}
    preview = json.loads((context.run/geometry['files']['preview']['relative_path']).read_text())
    nodes = {tuple(sorted(n['atom']['key'].items())): n['node_id'] for n in preview['nodes'] if n['atom']}
    for i,(a,s) in enumerate(zip(parsed.snapshot.atoms,parsed.to_dict()['atomic_state']),1):
        x,y,z = a.xyz
        line = atom(i,a.key.atom_name,a.key.component_id,a.key.chain_id,int(a.key.residue_id),(-y+11,x-7,z+4),a.element,s['occupancy'],s['b_iso'])
        lines.append(line)
        if tuple(sorted(a.key.to_dict().items())) in nodes:
            mapping[nodes[tuple(sorted(a.key.to_dict().items()))]] = a.key.to_dict()
    # An extra reference scatterer must stay visible even though no candidate node maps to it.
    lines.append(atom(len(parsed.snapshot.atoms)+1,'AG','AG','Z',9,(20,20,20),'Ag',.4,77))
    reference = tmp_path/'human.pdb';reference.write_text(''.join(lines)+'END\n')
    plan = dict(kind='metal-reference-map',schema_version=1,geometry_id=geometry['geometry_id'],
                reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
                elements=['Hg','Ag','I'],nodes=mapping,note='Explicit synthetic reference mapping')
    return context, geometry, reference, plan


def test_rigid_frame_change_preserves_internal_geometry_and_exposes_extra_atoms(tmp_path):
    context,g,reference,plan = setup(tmp_path)
    before = reference.read_bytes()
    doc = compare_reference(context.run,'Metal/geometry_001',reference,plan)
    result = json.loads((context.run/doc['files']['report']['relative_path']).read_text())
    assert result['status']=='REFERENCE_COMPARISON_REVIEW'
    assert result['stored_anomalous_parameters']=='UNTRUSTED_IGNORED'
    assert result['automatic_checkpoint_selection'] is False
    assert all(abs(r['candidate_minus_reference'])<1e-10 for r in result['pair_distances'])
    assert all(row['cartesian_displacement_A'] is None for row in result['nodes'])
    assert any(a['element']=='Ag' for a in result['unmapped_reference_atoms_of_interest'])
    assert reference.read_bytes()==before
    assert verify_reference_comparison(context.run,'Metal/reference_comparison_001')==doc


def report(run, doc):
    return json.loads((run/doc['files']['report']['relative_path']).read_text())


def update_reference(path, plan, transform):
    path.write_text(transform(path.read_text()))
    plan['reference_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()


def test_inventory_preserves_recorded_anisou_charge_exact_labels_and_warnings():
    line = atom(1,'Hg','HG','Z',9,(1,2,3),'Hg',1.2,-2).rstrip('\n')
    line = line[:16]+'A'+line[17:26]+'B'+line[27:72]+'SEG1'+line[76:78]+'2+\n'
    values=[1000,2000,3000,100,-200,300]
    anisou='ANISOU'+line[6:28]+''.join(f'{v:7d}' for v in values)+line[70:]
    raw=('MODEL        7\nREMARK fdp = 999\n'+line+anisou+'ENDMDL\nEND\n').encode()
    data=inspect_reference(raw,elements=['Hg'])
    row=data['atoms_of_interest'][0]
    assert row['anisou_pdb']==values and row['reported_b_A2']==-2
    assert row['occupancy']==1.2 and row['pdb_charge_field']=='2+'
    assert row['key']['model_id']=='7' and row['key']['atom_name']=='Hg'
    assert row['key']['altloc']=='A' and row['key']['insertion_code']=='B' and row['key']['segment_id']=='SEG1'
    assert data['warnings']=={'occupancies_outside_zero_to_one':1,'negative_reported_b':1}
    assert data['stored_anomalous_parameters']=='UNTRUSTED_IGNORED'
    assert 'f_double_prime' not in row


def test_geometry_and_state_differences_leave_targets_and_source_unchanged(tmp_path):
    context,g,reference,plan=setup(tmp_path,angle=True)
    def change(raw):
        lines=raw.splitlines(keepends=True)
        for i,line in enumerate(lines):
            if line.startswith('HETATM') and line[21]=='M':
                lines[i]=line[:30]+f'{12.:8.3f}'+line[38:54]+f'{.3:6.2f}{55.:6.2f}'+line[66:]
        return ''.join(lines)
    update_reference(reference,plan,change)
    data=report(context.run,compare_reference(context.run,'Metal/geometry_001',reference,plan))
    metal=next(r for r in data['nodes'] if r['node_id']=='m1')
    assert metal['candidate_minus_reference_occupancy']==pytest.approx(.3)
    assert metal['candidate_minus_reference_reported_b_A2']==-30
    assert any(abs(r['candidate_minus_reference'])>.1 for r in data['pair_distances'])
    angle=next(r for r in data['recipe_geometry'] if r['kind']=='angle')
    assert angle['reference']<180 and angle['recipe_target']==180
    assert (context.run/g['files']['model']['relative_path']).read_bytes()!=reference.read_bytes()


def test_partial_mapping_and_element_mismatch_remain_explicit(tmp_path):
    context,g,reference,plan=setup(tmp_path)
    extra=next(a for a in inspect_reference(reference.read_bytes(),elements=['Ag'])['atoms_of_interest'])
    plan['nodes']={'m1':extra['key']}
    data=report(context.run,compare_reference(context.run,'Metal/geometry_001',reference,plan))
    assert data['nodes'][0]['element_agrees'] is False
    assert data['unmapped_candidate_nodes']==['d1','d2']
    assert data['recipe_geometry'][0]['candidate'] is None
    assert data['recipe_geometry'][0]['issues']==['unmapped_node']
    assert any(a['element']=='Hg' for a in data['unmapped_reference_atoms_of_interest'])


@pytest.mark.parametrize('problem',['sha','geometry','unknown','missing_atom','case','symmetry','duplicate',
                                     'empty','no_metal','elements','duplicate_elements','extra_field','schema_type'])
def test_invalid_mapping_allocates_no_comparison(tmp_path,problem):
    context,g,reference,plan=setup(tmp_path)
    if problem=='sha':plan['reference_sha256']='a'*64
    elif problem=='geometry':plan['geometry_id']='b'*64
    elif problem=='unknown':plan['nodes']['absent']=plan['nodes']['m1']
    elif problem=='missing_atom':plan['nodes']['m1']['residue_id']='99'
    elif problem=='case':plan['nodes']['m1']['atom_name']='Hg'
    elif problem=='symmetry':plan['nodes']['m1']['symmetry']='-x,y,z'
    elif problem=='duplicate':plan['nodes']['d1']=copy.deepcopy(plan['nodes']['m1'])
    elif problem=='empty':plan['nodes']={}
    elif problem=='no_metal':plan['nodes'].pop('m1')
    elif problem=='elements':plan['elements']=['Ag']
    elif problem=='duplicate_elements':plan['elements']=['Hg','Hg']
    elif problem=='extra_field':plan['unknown']=True
    else:plan['schema_version']=True
    with pytest.raises(RecipeError):compare_reference(context.run,'Metal/geometry_001',reference,plan)
    assert not list((context.run/'Metal').glob('reference_comparison_*'))


@pytest.mark.parametrize('target',['reference','mapping','report','policy','extra_file','symlink','parent'])
def test_rehashed_tampering_is_rejected_by_replay(tmp_path,target):
    from nasolve.metal.recipe import digest
    context,g,reference,plan=setup(tmp_path)
    doc=compare_reference(context.run,'Metal/geometry_001',reference,plan)
    directory=context.run/'Metal/reference_comparison_001'
    if target in {'reference','mapping','report'}:
        path=context.run/doc['files'][target]['relative_path']
        if target=='reference':path.write_bytes(path.read_bytes()+b'REMARK changed\n')
        else:
            data=json.loads(path.read_text())
            if target=='mapping':data['note']='Changed map'
            else:data['nodes'][0]['candidate_minus_reference_occupancy']=42
            path.write_bytes(_json_bytes(data))
        doc['files'][target]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        doc['files'][target]['size']=path.stat().st_size
    elif target=='policy':doc['native_ready']=True
    elif target=='extra_file':(directory/'extra.txt').write_text('unexpected')
    elif target=='symlink':
        (directory/'reference.pdb').unlink();(directory/'reference.pdb').symlink_to(reference)
    else:
        path=context.run/doc['parent']['relative_path'];path.write_bytes(path.read_bytes()+b'\n')
    doc.pop('comparison_id');doc['comparison_id']=digest(doc)
    (directory/'manifest.json').write_bytes(_json_bytes(doc))
    with pytest.raises(RecipeError):verify_reference_comparison(context.run,directory)


def test_original_reference_can_disappear_and_prior_comparison_stays_immutable(tmp_path):
    context,g,reference,plan=setup(tmp_path)
    first=compare_reference(context.run,'Metal/geometry_001',reference,plan)
    root=context.run/'Metal/reference_comparison_001'
    before={p.name:p.read_bytes() for p in root.iterdir()}
    second=compare_reference(context.run,'Metal/geometry_001',reference,plan)
    assert first['comparison_id']!=second['comparison_id']
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}
    reference.unlink()
    assert verify_reference_comparison(context.run,root)==first


def test_capture_failure_preserves_failed_number_and_next_attempt(tmp_path,monkeypatch):
    import nasolve.metal.reference as module
    context,g,reference,plan=setup(tmp_path)
    original=module._allocate
    def changed(run):
        directory=original(run);reference.write_bytes(reference.read_bytes()+b'REMARK changed\n');return directory
    monkeypatch.setattr(module,'_allocate',changed)
    with pytest.raises(RecipeError,match='changed during capture'):
        compare_reference(context.run,'Metal/geometry_001',reference,plan)
    assert (context.run/'Metal/reference_comparison_001/failure.json').is_file()
    with pytest.raises(RecipeError):verify_reference_comparison(context.run,'Metal/reference_comparison_001')
    monkeypatch.setattr(module,'_allocate',original)
    plan['reference_sha256']=hashlib.sha256(reference.read_bytes()).hexdigest()
    second=compare_reference(context.run,'Metal/geometry_001',reference,plan)
    assert 'reference_comparison_002' in second['files']['report']['relative_path']


def test_source_removed_relocation_uses_captured_reference_and_fresh_source(tmp_path):
    import os,shutil,subprocess,sys
    original=tmp_path/'original';original.mkdir()
    context,g,reference,plan=setup(original)
    doc=compare_reference(context.run,'Metal/geometry_001',reference,plan)
    source=Path(__file__).resolve().parents[1]/'src'
    shutil.copytree(source,original/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    reference.unlink()
    moved=tmp_path/'moved';original.rename(moved)
    assert not original.exists()
    code="""import sys,subprocess
from pathlib import Path
import nasolve.metal.reference as m
assert Path(m.__file__).is_relative_to(Path(sys.argv[1]))
def forbidden(*a,**kw):raise AssertionError('No native process allowed')
subprocess.run=forbidden
print(m.verify_reference_comparison(sys.argv[2],'Metal/reference_comparison_001')['comparison_id'])
"""
    done=subprocess.run([sys.executable,'-B','-c',code,str(moved/'src'),str(moved/'dataset/AutoMR/run_001')],
                        cwd=moved,env=dict(os.environ,PYTHONPATH=str(moved/'src'),PYTHONDONTWRITEBYTECODE='1'),
                        capture_output=True,text=True,timeout=30)
    assert done.returncode==0,done.stderr
    assert done.stdout.strip()==doc['comparison_id']


def test_cli_inventory_capture_replay_and_output_guard_without_native(tmp_path,monkeypatch,capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    import nasolve.metal.cli as module
    context,g,reference,plan=setup(tmp_path)
    monkeypatch.setattr(module,'discover_phenix',lambda *a,**kw:pytest.fail('No native discovery'))
    parser=build_parser()
    assert execute(parser.parse_args(['metal','inspect-reference',str(reference),'--element','Hg','--json']))==0
    assert json.loads(capsys.readouterr().out)['stored_anomalous_parameters']=='UNTRUSTED_IGNORED'
    mapping=tmp_path/'map.json';mapping.write_bytes(_json_bytes(plan))
    args=['metal','compare-reference',str(context.run),'--geometry','Metal/geometry_001','--reference',str(reference),'--mapping',str(mapping)]
    assert execute(parser.parse_args(args+['--output',str(mapping)]))==2
    capsys.readouterr()
    assert not list((context.run/'Metal').glob('reference_comparison_*'))
    assert execute(parser.parse_args(args))==0
    assert 'no alignment' in capsys.readouterr().out
    assert execute(parser.parse_args(['metal','verify-reference-comparison',str(context.run),'--comparison','Metal/reference_comparison_001','--json']))==0
    assert json.loads(capsys.readouterr().out)['status']=='REFERENCE_COMPARISON_REVIEW'


@pytest.mark.parametrize('payload',[[],None,True,{}])
def test_malformed_manifest_has_controlled_failure(tmp_path,payload):
    context,g,reference,plan=setup(tmp_path)
    compare_reference(context.run,'Metal/geometry_001',reference,plan)
    (context.run/'Metal/reference_comparison_001/manifest.json').write_bytes(_json_bytes(payload))
    with pytest.raises(RecipeError):verify_reference_comparison(context.run,'Metal/reference_comparison_001')
