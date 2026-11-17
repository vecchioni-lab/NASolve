"""Explicit metal recipes bind shared coverage declarations without role inference."""
from copy import deepcopy
import json
import pytest
from nasolve.metal import Recipe, RecipeError
from nasolve.metal.materialize import build_hypothesis
from nasolve.metal.native_terms import describe_native_terms
from tests.test_metal_materialize import control


def fixture(tmp_path, *, disabled=False, precise=False, explicit_model=False):
    context,recipe,plan=control(tmp_path, explicit_model=explicit_model)
    doc=recipe.to_dict();row=doc['restraints'][0]
    doc['restraints'] += [dict(row,id='r2',nodes=['m1','d2']),
        dict(row,id='a',kind='angle',nodes=['m1','d1','d2'],target=0.,sigma=2.,unit='degree')]
    if disabled:doc['restraints'][-1]['enabled']=False
    if precise:doc['restraints'][0].update(target=2.1234567890123456,sigma=.1234567890123456)
    recipe=Recipe(doc);plan['recipe_sha256']=recipe.sha256
    h=build_hypothesis(context,recipe,plan)
    p=json.loads((context.run/h['files']['preview']['relative_path']).read_text())
    native=[]
    for a in p['inputs']['model']['atoms']:
        k=a['key'];native.append(dict(identity=dict(chain=k['chain_id'],residue_number=int(k['residue_id']),
            insertion_code=k['insertion_code'],residue_code=k['component_id'],atom_name=k['atom_name'],altloc=k['altloc']),
            element=a['element'].upper(),model_id='',segment_id=''))
    return p,native


def test_preserves_zero_angle_vertex_and_complete_native_order(tmp_path):
    p,n=fixture(tmp_path);before=deepcopy((p,n));n.reverse();out=describe_native_terms(p,n)
    assert out['atom_labels']==[json.dumps(x['identity'],sort_keys=True,separators=(',',':'))for x in n]
    assert [r['kind']for r in out['requested']]==['bond','bond','angle']
    angle=out['requested'][2]
    assert [json.loads(a['atom'])['atom_name']for a in angle['atoms']]==['HG','S1','N3']
    assert angle['parameters']==dict(ideal=0.,weight=.25,slack=0.)
    assert out['requested'][0]['parameters']==dict(ideal=2.,weight=pytest.approx(100.),slack=0.,limit=-1.,top_out=False)
    assert all(a['translation']==['0','0','0']for r in out['requested']for a in r['atoms'])
    assert p==before[0] and list(reversed(n))==before[1]
    assert out['runtime_authority']is False and out['scientific_acceptance']is False


@pytest.mark.parametrize('change',['missing','duplicate','element','residue','segment','model','identity_fields'])
def test_rejects_incomplete_or_lossy_native_binding(tmp_path,change):
    p,n=fixture(tmp_path)
    if change=='missing':n.pop()
    elif change=='duplicate':n[-1]=deepcopy(n[0])
    elif change=='element':n[-1]['element']='AU'
    elif change=='residue':n[-1]['identity']['residue_number']=9
    elif change=='segment':n[-1]['segment_id']='ABCD'
    elif change=='model':n[-1]['model_id']='2'
    else:n[-1]['identity']['unknown']='field'
    with pytest.raises(RecipeError):describe_native_terms(p,n)


def test_preview_tampering_is_not_a_new_recipe(tmp_path):
    p,n=fixture(tmp_path);p['restraints'][2]['node_ids']=['d1','m1','d2']
    with pytest.raises(RecipeError):describe_native_terms(p,n)


def test_declaration_is_detached_from_caller(tmp_path):
    p,n=fixture(tmp_path);out=describe_native_terms(p,n);before=deepcopy(out)
    n[0]['identity']['atom_name']='changed';p['restraints'].clear()
    assert out==before


def test_disabled_terms_are_not_declared_or_inferred(tmp_path):
    p,n=fixture(tmp_path,disabled=True);out=describe_native_terms(p,n)
    assert [r['term_id']for r in out['requested']]==['r','r2']
    assert out['disabled_restraint_ids']==['a']


def test_targets_follow_existing_phil_precision(tmp_path):
    from nasolve.metal.export import export_restraints
    p,n=fixture(tmp_path,precise=True);out=describe_native_terms(p,n)
    assert 'distance_ideal = 2.12345678901' in export_restraints(p)
    assert 'sigma = 0.123456789012' in export_restraints(p)
    assert out['requested'][0]['parameters']['ideal']==2.12345678901
    assert out['requested'][0]['parameters']['weight']==pytest.approx(65.610001181605)


def test_explicit_model_is_not_silently_rebound_to_implicit_one(tmp_path):
    p,n=fixture(tmp_path,explicit_model=True)
    with pytest.raises(RecipeError,match='model'):describe_native_terms(p,n)
    for row in n:row['model_id']='7'
    assert describe_native_terms(p,n)['model_binding']==dict(source='7',native='7')
