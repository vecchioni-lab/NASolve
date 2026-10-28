"""Synthetic legacy-PHIL import; example chemistry is deliberately not a library."""
import json
import pytest

from nasolve.metal.phil_import import inspect_restraints, import_recipe
from nasolve.metal.recipe import Recipe, RecipeError


def sample():
    return b'''# Synthetic numerical control, not chemical guidance.
refinement.geometry_restraints.edits {
  ion = chain X and resid 900
  left = chain A and resid 12 and name S1
  right = chain B and resid 4 and name N3
  bond {
    action = *add
    atom_selection_1 = $ion
    atom_selection_2 = $left
    symmetry_operation = None
    distance_ideal = 2.3
    sigma = 0.04
    slack = None
  }
  bond {
    action = add
    atom_selection_1 = $ion
    atom_selection_2 = $right
    distance_ideal = 2.3
    sigma = 0.04
  }
  angle {
    action = *add
    atom_selection_1 = $ion
    atom_selection_2 = $left
    atom_selection_3 = $right
    angle_ideal = 0
    sigma = 3
  }
}
'''


def mapping():
    return {'s1':dict(id='m1',kind='metal',element='Hg'),
            's2':dict(id='d1',kind='donor',residue_slot='first',role='O2'),
            's3':dict(id='d2',kind='donor',residue_slot='second',role='N3')}


def test_import_preserves_order_vertex_targets_and_exact_source():
    draft=inspect_restraints(sample())
    assert len(draft['selectors'])==3
    assert draft['selectors'][0]['selection']=='chain X and resid 900'
    angle=draft['restraints'][-1]
    assert angle['selectors']==['s1','s2','s3'] and angle['target']==0
    recipe=import_recipe(sample(),mapping(),recipe_id='bridge',name='Synthetic bridge')
    doc=recipe.to_dict()
    assert doc['restraints'][-1]['nodes']==['m1','d1','d2']
    assert doc['restraints'][-1]['target']==0
    assert doc['restraints'][0]['sigma']==.04
    assert doc['extensions']['phil_import']['source_text'].encode()==sample()
    assert Recipe.from_json(recipe.to_json()).sha256==recipe.sha256
    assert inspect_restraints(doc['extensions']['phil_import']['source_text'].encode())==draft


@pytest.mark.parametrize('old,new',[
 (b'action = *add',b'action = delete'),
 (b'symmetry_operation = None',b'symmetry_operation = x+1,y,z'),
 (b'slack = None',b'slack = 0.2'),
 (b'sigma = 0.04',b'sigma = 0'),
 (b'angle_ideal = 0',b'angle_ideal = 181'),
 (b'distance_ideal = 2.3',b'distance_ideal = nan'),
 (b'distance_ideal = 2.3',b'distance_ideal = -1'),
 (b'atom_selection_1 = $ion',b'atom_selection_1 = $unknown'),
 (b'ion = chain X and resid 900',b'ion = $ion'),
 (b'slack = None',b'weight = 3'),
 (b'bond {',b'plane {'),
 (b'  ion =',b'  nproc = 8\n  ion ='),
 (b'  ion =',b'  include file = other.phil\n  ion ='),
 (b'sigma = 0.04',b'sigma = 0.04\n    sigma = 0.05'),
 (b'atom_selection_2 = $left',b'atom_selection_2 = $ion'),
 (b'atom_selection_2 = $left',b'atom_selection_2 = "$ion and name HG"'),
])
def test_unsupported_or_ambiguous_semantics_fail_closed(old,new):
    with pytest.raises(RecipeError):inspect_restraints(sample().replace(old,new,1))


@pytest.mark.parametrize('edit',['missing','extra','duplicate','not_node'])
def test_explicit_complete_logical_mapping_required(edit):
    nodes=mapping()
    if edit=='missing':nodes.pop('s2')
    if edit=='extra':nodes['s4']=dict(id='extra',kind='atom')
    if edit=='duplicate':nodes['s2']=nodes['s1']
    if edit=='not_node':nodes['s2']='d1'
    with pytest.raises(RecipeError):import_recipe(sample(),nodes,recipe_id='x',name='x')


def test_export_uses_new_exact_inventory_not_legacy_residue_selector(tmp_path):
    from tests.test_metal_materialize import control
    from nasolve.metal.materialize import build_hypothesis, verify_hypothesis
    from nasolve.metal.export import export_restraints
    context,_,placement=control(tmp_path)
    recipe=import_recipe(sample(),mapping(),recipe_id='bridge',name='Synthetic bridge')
    placement['recipe_sha256']=recipe.sha256
    out=build_hypothesis(context,recipe,placement)
    preview=json.loads((context.run/out['files']['preview']['relative_path']).read_text())
    native=export_restraints(preview)
    assert 'chain X' not in native and 'resid 900' not in native
    assert 'chain M and resid 1 and resname HG and name HG' in native
    assert preview['restraints'][-1]['measured']==0
    assert preview['restraints'][-1]['node_ids']==['m1','d1','d2']
    # Native export can be imported again without reordering the vertex.
    again=inspect_restraints(native.encode())
    assert again['restraints'][-1]['selectors']==['s1','s2','s3']
    assert verify_hypothesis(context.run,'Metal/hypothesis_001')==out
    # Imported source is captured, not an operational host path.
    import shutil
    moved=tmp_path/'moved';context.run.parent.parent.rename(moved)
    assert verify_hypothesis(moved/'AutoMR/run_001','Metal/hypothesis_001')==out


def test_cluster_links_do_not_imply_planarity_or_angles():
    raw=b'refinement.geometry_restraints.edits {\n'
    for a,b in [(1,2),(1,3),(1,4),(2,3),(2,4),(3,4)]:
        raw+=f'''bond {{
 action = add
 atom_selection_1 = chain X and resid {a}
 atom_selection_2 = chain X and resid {b}
 distance_ideal = 3.1
 sigma = 0.08
}}
'''.encode()
    raw+=b'}\n'
    draft=inspect_restraints(raw)
    assert len(draft['selectors'])==4 and len(draft['restraints'])==6
    assert {r['kind'] for r in draft['restraints']}=={'distance'}


def test_cli_inspects_and_imports_offline_without_overwrite(tmp_path,monkeypatch,capsys):
    from nasolve.cli import build_parser
    from nasolve.metal.cli import execute
    import nasolve.metal.cli as cli
    monkeypatch.setattr(cli,'discover_phenix',lambda *a,**kw:pytest.fail('Offline import'))
    source=tmp_path/'legacy.txt';source.write_bytes(sample())
    nodes=tmp_path/'mapping.json';nodes.write_text(json.dumps(mapping()))
    output=tmp_path/'recipe.json'
    args=build_parser().parse_args(['metal','import-restraints',str(source),'--json'])
    assert execute(args)==0
    assert json.loads(capsys.readouterr().out)['kind']=='metal-restraint-import'
    args=build_parser().parse_args(['metal','import-restraints',str(source),'--mapping',str(nodes),
        '--id','bridge','--name','Synthetic bridge','--output',str(output)])
    assert execute(args)==0
    saved=output.read_bytes();assert Recipe.from_json(saved.decode()).to_dict()['id']=='bridge'
    assert execute(args)==2 and output.read_bytes()==saved
