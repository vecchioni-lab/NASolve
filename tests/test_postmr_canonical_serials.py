"""A declared ordinary-base mutation joins serial repair, never OP3 authority."""
from dataclasses import replace
from hashlib import sha256
import shutil

import pytest

from nasolve.postmr import MutationAction, construct_postmr_model
from nasolve.postmr_context import prepare_construction_context
from nasolve.cif_postmr_construction import audit_construction_context
from tests.helpers import pdb_record
from tests.test_postmr_context import SCAFFOLD, atom_rows
from tests.test_postmr_identity_serials import globally_numbered

POLICY = 'postmr-declared-canonical-serial-context-v1'


def mixed(tmp_path):
    raw, initial, source, graph = globally_numbered(tmp_path)
    for path, code, shift, start in ((initial, 'DC', 0, 200), (raw, 'DA', 3, 1)):
        rows = ''.join(pdb_record('HETATM', i, name, code, 'R', 4,
            element='P' if name == 'P' else 'O' if name.startswith('O') else 'C',
            x=xyz[0]+100+shift, y=xyz[1], z=xyz[2])
            for i, (name, xyz) in enumerate(SCAFFOLD.items(), start))
        path.write_text(path.read_text().replace('END\n', rows+'END\n'))
    return raw, initial, source, (graph, MutationAction('R:4', 'DC', 'DA', 'coot-mutate-base'))


def prepare(inputs, output, *, policy=POLICY, **kwargs):
    raw, initial, source, actions = inputs
    return prepare_construction_context(raw, initial, actions, {'ZZZ': source},
        {'Z:9': initial}, output, serial_identity_policy='postmr-input-identity-serial-context-v1',
        canonical_serial_policy=policy, **kwargs)


def audit(inputs, result):
    raw, initial, source, actions = inputs
    return audit_construction_context(initial, raw, result['model'], actions,
        {'ZZZ': source}, result['receipt'], context_shadow=result['shadow'],
        parent_models={'Z:9': initial})


def test_mixed_canonical_scope_is_serial_only_with_independent_audit(tmp_path):
    inputs = mixed(tmp_path); snapshots = {p:p.read_bytes() for p in inputs[:3]}
    result = prepare(inputs, tmp_path/'context.pdb')
    receipt = result['receipt']
    assert receipt['status'] == 'CONTEXT_PREPARED'
    assert receipt['canonical_serial_scope'] == {'policy_id': POLICY, 'scope': 'SERIAL_FIELDS_ONLY',
        'mutations': [{'site': 'R:4', 'before': 'DC', 'after': 'DA'}]}
    assert {(r['site'], r['atom']) for r in receipt['removed_atoms']} == {('Z:9','OP3')}
    before, after, shadow = map(atom_rows, (inputs[0], result['model'], result['shadow']))
    for key, line in after.items():
        assert line[:6]+line[11:] == before[key][:6]+before[key][11:]
        if key[0] == 'R': assert shadow[key][:6]+shadow[key][11:] == before[key][:6]+before[key][11:]
    assert audit(inputs, result)['status'] == 'CONSTRUCTION_CONTEXT_DELTA_PASS'
    assert all(p.read_bytes() == data for p,data in snapshots.items())
    old = prepare(inputs, tmp_path/'old.pdb', policy=None)
    assert old['receipt']['status'] == 'RAW_CONTEXT_RETAINED'
    assert old['model'].read_bytes() == inputs[0].read_bytes()


@pytest.mark.parametrize('defect', ['before','after','method','duplicate','passthrough','unselected'])
def test_declared_mutation_cannot_hide_other_changes(tmp_path, defect):
    raw, initial, source, actions = mixed(tmp_path)
    if defect in {'before','after','method'}:
        actions = actions[:1]+(replace(actions[1], **{defect: {'before':'DT','after':'LDA','method':'none'}[defect]}),)
    elif defect == 'duplicate': actions += (actions[1],)
    elif defect == 'unselected': raw.write_text(raw.read_text().replace('  -0.530', '  -0.630'))
    result = prepare((raw,initial,source,actions), tmp_path/'context.pdb',
        passthrough_sites=('R:4',) if defect == 'passthrough' else ())
    assert result['receipt']['status'] == 'RAW_CONTEXT_RETAINED'
    assert result['model'].read_bytes() == raw.read_bytes()
    assert not result['receipt']['removed_atoms'] and not result['receipt']['serial_repairs']


@pytest.mark.parametrize('defect', ['missing','policy','scope','site','before','after','extra','shadow_xyz'])
def test_reader_reconstructs_scope_and_rejects_forgery(tmp_path, defect):
    inputs = mixed(tmp_path); result = prepare(inputs, tmp_path/'context.pdb')
    receipt = result['receipt']; scope = receipt['canonical_serial_scope']
    if defect == 'missing': receipt.pop('canonical_serial_scope')
    elif defect == 'policy': scope['policy_id'] = 'unknown'
    elif defect == 'scope': scope['scope'] = 'ALSO_CHEMISTRY'
    elif defect in {'site','before','after'}: scope['mutations'][0][defect] = 'unbound'
    elif defect == 'extra': scope['mutations'].append({'site':'Z:8','before':'DT','after':'DA'})
    else:
        p=result['shadow']; lines=p.read_text().splitlines(keepends=True)
        i=next(i for i,l in enumerate(lines) if l.startswith('HETATM') and l[21]=='R')
        lines[i]=lines[i][:30]+f'{900.:8.3f}'+lines[i][38:];p.write_text(''.join(lines))
        receipt['shadow_sha256']=sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError): audit(inputs, result)


def test_ordinary_mixed_construction_restores_both_backbones(tmp_path, monkeypatch):
    inputs=mixed(tmp_path); raw,initial,source,actions=inputs
    def coot(model, output, actions, executable, directory, environment, dictionaries, parents, **unused):
        shutil.copyfile(raw,output);shutil.copyfile(initial,parents['Z:9'])
        log=directory/'coot.log';log.write_text('synthetic mixed Coot output')
        return directory/'mutate.py',log
    monkeypatch.setattr('nasolve.postmr._run_coot',coot)
    result=construct_postmr_model(initial,actions,{'ZZZ':source},tmp_path/'built/model.pdb',coot_executable=tmp_path/'coot')
    assert result['context_receipt']['status']=='CONTEXT_PREPARED'
    assert result['coordinate_restoration']['Z:9']['status']=='GRAPH_FRAGMENT_RESTORED'
    assert result['context_receipt']['final_sanitizer_recheck']['checked']
    original,final=map(atom_rows,(initial,result['model']))
    for key,line in final.items():
        if key[0]=='R' or key[1]=='9' and key[-1] in SCAFFOLD:
            assert line[30:54]==original[key][30:54]
    assert ('Z','9',' ','OP3') not in final
    assert len({l[6:11] for l in final.values()})==len(final)

    def fail(*args,**kwargs): raise ValueError('deliberate final phosphate proof failure')
    monkeypatch.setattr('nasolve.postmr.sanitize_phosphates',fail)
    rollback=construct_postmr_model(initial,actions,{'ZZZ':source},tmp_path/'rollback/model.pdb',coot_executable=tmp_path/'coot')
    receipt=rollback['context_receipt']
    assert receipt['status']=='RAW_CONTEXT_RETAINED'
    assert 'canonical_serial_scope' not in receipt
    assert receipt['attempted_canonical_serial_scope']['policy_id']==POLICY
    checked=audit_construction_context(initial,rollback['raw_model'],rollback['restoration_input'],
        actions,{'ZZZ':source},receipt,context_shadow=rollback['context_shadow'],parent_models=rollback['parent_models'])
    assert checked['status']=='RAW_CONTEXT_RETAINED'


def test_mixed_scope_replays_after_original_anchor_removed(tmp_path):
    old=tmp_path/'old';old.mkdir();inputs=mixed(old)
    result=prepare(inputs,tmp_path/'first.pdb');audit(inputs,result)
    new=tmp_path/'new';shutil.copytree(old,new);shutil.rmtree(old)
    relocated=tuple(new/p.name for p in inputs[:3])+(inputs[3],)
    replay=prepare(relocated,tmp_path/'second.pdb');audit(relocated,replay)
    assert result['model'].read_bytes()==replay['model'].read_bytes()
    assert result['receipt']['canonical_serial_scope']==replay['receipt']['canonical_serial_scope']
