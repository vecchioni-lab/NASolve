"""Declared graph coverage consumes Cedar's public rows, not proximity guesses."""
from copy import deepcopy
from hashlib import sha256
import json
import shutil

import pytest
import gemmi
from tests.test_topostitch_cif_output import fixture as output_fixture, prepare
from tests.test_topostitch_cif_source import edit


def bind_steps(owner, kw, payload, *, drift=False):
    # Contract fake: no crystallographic decoder/geometry implementation here.
    # Real Cedar and actual 3LNA are separately replayed against W273 evidence.
    text = owner.read_text()
    if '# PUBLIC_STEPS_FAKE' in text:
        text = text.split('# PUBLIC_STEPS_FAKE')[0]
    text += '\n# PUBLIC_STEPS_FAKE\nimport copy\n_legacy_inspect = inspect_deposition_links\n_PAYLOAD = '+repr(payload)+"""
def inspect_deposition_links(model, *, include_ordinary_steps=False):
    if not include_ordinary_steps:
        return _legacy_inspect(model)
    result = copy.deepcopy(_PAYLOAD)
    result['model']['sha256'] = sha256(Path(model).read_bytes()).hexdigest()
"""
    if drift:
        text += "    Path(model).write_bytes(Path(model).read_bytes()+b'\\n')\n"
    text += '    return result\n'
    owner.write_text(text)
    kw['expected_deposition_owner_sha256'] = sha256(owner.read_bytes()).hexdigest()


def fixture(tmp_path):
    from nasolve.topostitch_cif_output import _SOURCE_KEYS
    from nasolve.topostitch_cif_source import observe_relabel_cif_paths
    root, original, kw, owner = output_fixture(tmp_path)
    data, _ = prepare(root, original, kw)
    output = tmp_path/'emitted.cif'; output.write_bytes(data)
    kw = {k:v for k,v in kw.items() if k in _SOURCE_KEYS or k in ('cedar_source','expected_deposition_owner_sha256')}
    source_kw = {k:v for k,v in kw.items() if k in _SOURCE_KEYS}
    paths = observe_relabel_cif_paths(root, original, **source_kw)
    sites = {r['node_id']: (r['original_label']['label_asym_id'], r['original_label']['label_seq_id'],
        r['original_label']['label_comp_id'], '') for r in paths['registered_original_sites']}
    graph = json.loads((root/'preview.json').read_text())['observation']['graph_relabeling']['periodic_graph']
    ordinary, explicit = [], []
    geometry = dict(model='1', distance_A=1.6, O3_P_OP1_deg=108., O3_P_OP2_deg=109., O3_P_O5prime_deg=104.)
    for edge in graph['edges']:
        if edge['kind'] != 'covalent_backbone': continue
        left, right = sites[edge['source']], sites[edge['target']]
        op = edge['target_operator_xyz']
        if left[0] == right[0] and int(right[1]) == int(left[1])+1 and op == 'x,y,z':
            ordinary.append(dict(status='MEASURED', O3_label=left, P_label=right, operator_on_P=op,
                label_asym_id=left[0], from_label_seq_id=int(left[1]), to_label_seq_id=int(right[1]), **geometry))
        else:
            explicit.append(dict(id='edge'+str(edge['edge_id']), O3_label=left, P_label=right,
                operator_on_P=op, observations=[dict(geometry)]))
    payload = dict(schema_version=1, status='CHECKED', model=dict(status='CHECKED',
        ordinary=dict(steps=ordinary, measured=len(ordinary)), declared=explicit, sequence_conflicts=[]))
    bind_steps(owner, kw, payload)
    return root, original, output, kw, owner, payload, sites


def observe(root, original, output, kw):
    from nasolve.topostitch_cif_output import observe_whole_asym_cif_backbone
    return observe_whole_asym_cif_backbone(root, original, output,
        expected_output_sha256=sha256(output.read_bytes()).hexdigest(), **kw)


def test_public_per_step_coverage_retains_graph_and_relocates(tmp_path):
    old=tmp_path/'old'; old.mkdir()
    root, original, output, kw, owner, _, _ = fixture(old)
    before={p:p.read_bytes() for p in [original,output,owner,*root.iterdir()]}
    r=observe(root,original,output,kw)
    assert r['complete_declared_backbone_coverage'] and r['status']=='COMPLETE'
    assert r['original_atom_count']==84 and not r['unexpected_registered_links']
    assert r == json.loads(json.dumps(r))
    assert not r['coordinates_or_scattering_verified'] and not r['geometry_accepted']
    assert not r['runtime_authority'] and str(old)not in json.dumps(r)
    assert all(p.read_bytes()==v for p,v in before.items())
    relative=[p.relative_to(old)for p in (root,original,output,kw['cedar_source'])]
    moved=tmp_path/'moved';shutil.move(old,moved)
    root,original,output,kw['cedar_source']=[moved/p for p in relative]
    assert not old.exists() and observe(root,original,output,kw)==r


@pytest.mark.parametrize('damage', ['missing','wrong_image','duplicate','unmeasured','sequence_gap'])
def test_missing_conflicting_and_ambiguous_links_cannot_pass(tmp_path,damage):
    root,original,output,kw,owner,payload,_=fixture(tmp_path)
    steps=payload['model']['ordinary']['steps']; row=steps[0]
    if damage=='missing':steps.pop(0)
    elif damage=='wrong_image':
        payload['model']['declared'].append(dict(id='wrong',O3_label=row['O3_label'],P_label=row['P_label'],
            operator_on_P='x+1,y,z',observations=[{k:row[k]for k in ('model','distance_A')}]))
    elif damage=='duplicate':steps.append(deepcopy(row))
    else:
        row.update(status='SEQUENCE_GAP'if damage=='sequence_gap'else'UNMEASURED',
            O3_label=None,P_label=None,distance_A=None)
        if damage=='sequence_gap':row['operator_on_P']=None
    bind_steps(owner,kw,payload)
    r=observe(root,original,output,kw)
    assert not r['complete_declared_backbone_coverage'] and r['status']=='REVIEW_REQUIRED'
    assert any(e['status']!='COVERED'for e in r['edges'])
    if damage=='sequence_gap':assert len(r['sequence_gaps'])==1
    if damage=='wrong_image':assert r['unexpected_registered_links']


@pytest.mark.parametrize('status', ['LONG','PARTIAL_ANGLES'])
def test_geometry_review_does_not_erase_known_topology(tmp_path,status):
    root,original,output,kw,owner,payload,_=fixture(tmp_path)
    row=payload['model']['ordinary']['steps'][0];row['status']=status
    if status=='LONG':row['distance_A']=4.5
    else:row['O3_P_OP1_deg']=None
    payload['status']=payload['model']['status']='REVIEW'
    bind_steps(owner,kw,payload)
    r=observe(root,original,output,kw)
    assert r['complete_declared_backbone_coverage'] and not r['geometry_accepted']
    assert r['cedar_observation']['status']=='REVIEW'


def test_implicit_adjacency_cannot_override_declared_nick(tmp_path):
    from nasolve.topostitch_cif_output import _backbone_coverage
    root,_,_,_,_,payload,sites=fixture(tmp_path)
    graph=json.loads((root/'preview.json').read_text())['observation']['graph_relabeling']['periodic_graph']
    edge=next(e for e in graph['edges'] if e['kind']=='covalent_backbone')
    graph['edges'].remove(edge)
    r=_backbone_coverage(graph,sites,{**payload['model'],'_coverage_model':'1'})
    assert all(e['status']=='COVERED'for e in r['edges'])
    assert not r['complete_declared_backbone_coverage'] and len(r['unexpected_registered_links'])==1


def test_unregistered_context_is_reported_without_inventing_graph_edges(tmp_path):
    from nasolve.topostitch_cif_output import _backbone_coverage
    root,_,_,_,_,payload,sites=fixture(tmp_path)
    graph=json.loads((root/'preview.json').read_text())['observation']['graph_relabeling']['periodic_graph']
    outside=deepcopy(payload['model']['ordinary']['steps'][0])
    outside['O3_label']=('OUT','1','DA','');outside['P_label']=('OUT','2','DT','')
    payload['model']['ordinary']['steps'].append(outside)
    r=_backbone_coverage(graph,sites,{**payload['model'],'_coverage_model':'1'})
    assert r['complete_declared_backbone_coverage'] and len(r['outside_registered_scope'])==1


def test_output_pin_label_change_and_late_race_are_refused(tmp_path):
    from nasolve.topostitch_cif_output import observe_whole_asym_cif_backbone
    root,original,output,kw,owner,payload,_=fixture(tmp_path)
    with pytest.raises(ValueError,match='output binding'):
        observe_whole_asym_cif_backbone(root,original,output,expected_output_sha256='0'*64,**kw)
    saved=output.read_bytes()
    def change(doc):
        t=doc[0].get_mmcif_category('_atom_site.');t['label_atom_id'][0]='WRONG';doc[0].set_mmcif_category('_atom_site.',t)
    edit(output,change)
    with pytest.raises(ValueError,match='source labels'):observe(root,original,output,kw)
    output.write_bytes(saved);bind_steps(owner,kw,payload,drift=True)
    with pytest.raises(ValueError,match='changed during'):observe(root,original,output,kw)


def test_old_reader_does_not_silently_supply_aggregate_coverage(tmp_path):
    root,original,output,kw,owner,_,_=fixture(tmp_path)
    owner.write_text(owner.read_text().split('# PUBLIC_STEPS_FAKE')[0])
    kw['expected_deposition_owner_sha256']=sha256(owner.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='public per-step'):observe(root,original,output,kw)
