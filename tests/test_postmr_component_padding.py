"""Coot may pad the same residue name differently, never change its identity."""
import shutil
import pytest
from nasolve.postmr_context import prepare_construction_context
from tests.test_postmr_identity_serials import globally_numbered, audit, POLICY as LEGACY

POLICY='postmr-input-identity-component-padding-v1'


def padded_case(tmp_path):
    raw,parent,source,action=globally_numbered(tmp_path)
    lines=parent.read_text().splitlines(keepends=True)
    parent.write_text(''.join(line[:17]+line[17:20].strip().ljust(3)+line[20:]
        if line.startswith(('ATOM  ','HETATM')) and line[22:26].strip()!='9' else line for line in lines))
    return raw,parent,source,action


def prepare(inputs,output,policy=POLICY):
    raw,parent,source,action=inputs
    return prepare_construction_context(raw,parent,(action,),{'ZZZ':source},{'Z:9':parent},output,serial_identity_policy=policy)


def test_padding_is_an_explicit_narrow_identity_proof_and_raw_fields_stay_exact(tmp_path):
    inputs=padded_case(tmp_path);before={p:p.read_bytes() for p in inputs[:3]}
    result=prepare(inputs,tmp_path/'context.pdb');receipt=result['receipt']
    assert receipt['status']=='CONTEXT_PREPARED'
    proof=receipt['serial_authority'];assert proof['policy_id']==POLICY
    assert proof['component_padding_difference_count']>0
    assert proof['unselected_component_names_preserved'] is True
    assert proof['unselected_other_nonserial_fields_preserved'] is True
    assert 'unselected_nonserial_fields_preserved' not in proof
    checked=audit(inputs,result);assert checked['status']=='CONSTRUCTION_CONTEXT_DELTA_PASS'
    assert all(p.read_bytes()==b for p,b in before.items())
    old=prepare(inputs,tmp_path/'legacy.pdb',LEGACY)
    assert old['receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert old['model'].read_bytes()==inputs[0].read_bytes()


def test_byte_exact_cases_keep_old_proof_bytes_even_with_padding_capability(tmp_path):
    inputs=globally_numbered(tmp_path)
    old=prepare(inputs,tmp_path/'old/context.pdb',LEGACY);new=prepare(inputs,tmp_path/'new/context.pdb')
    assert old['receipt']['serial_authority']==new['receipt']['serial_authority']
    assert old['model'].read_bytes()==new['model'].read_bytes()
    audit(inputs,new)


@pytest.mark.parametrize('defect',['code','atom_name','occupancy','B','charge','element','record_type'])
def test_padding_permission_never_hides_other_input_changes(tmp_path,defect):
    inputs=padded_case(tmp_path);raw=inputs[0];lines=raw.read_text().splitlines(keepends=True)
    i=next(i for i,l in enumerate(lines) if l.startswith('HETATM') and l[22:26].strip()=='8');l=lines[i]
    if defect=='code':l=l[:17]+' DA'+l[20:]
    elif defect=='atom_name':l=l[:12]+"O3' "+l[16:]
    elif defect=='occupancy':l=l[:54]+'  0.50'+l[60:]
    elif defect=='B':l=l[:60]+' 91.00'+l[66:]
    elif defect=='charge':l=l[:78]+'1+\n'
    elif defect=='element':l=l[:76]+' N'+l[78:]
    else:l='ATOM  '+l[6:]
    lines[i]=l;raw.write_text(''.join(lines));before=raw.read_bytes()
    result=prepare(inputs,tmp_path/'context.pdb')
    assert result['receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert result['model'].read_bytes()==before


@pytest.mark.parametrize('defect',['count','old_policy','drop','other_metadata'])
def test_independent_reader_rejects_forged_padding_authority(tmp_path,defect):
    inputs=padded_case(tmp_path);result=prepare(inputs,tmp_path/'context.pdb');r=result['receipt']['serial_authority']
    if defect=='count':r['component_padding_difference_count']+=1
    elif defect=='old_policy':r['policy_id']=LEGACY
    elif defect=='drop':r.pop('unselected_component_names_preserved')
    else:
        from hashlib import sha256
        p=inputs[1];p.write_text(p.read_text().replace(' 20.00',' 21.00'))
        result['receipt']['reference_model_sha256']=sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError):audit(inputs,result)


def test_ordinary_constructor_uses_padding_proof_without_changing_scaffold_rule(tmp_path,monkeypatch):
    from nasolve.postmr import construct_postmr_model
    inputs=padded_case(tmp_path);raw,parent,source,action=inputs
    def coot(model,output,actions,executable,directory,environment,dictionaries,parents,**unused):
        shutil.copyfile(raw,output);shutil.copyfile(parent,parents['Z:9'])
        log=directory/'coot.log';log.write_text('controlled output');return directory/'mutate.py',log
    monkeypatch.setattr('nasolve.postmr._run_coot',coot)
    result=construct_postmr_model(parent,(action,),{'ZZZ':source},tmp_path/'out/model.pdb',coot_executable=tmp_path/'coot')
    assert result['context_receipt']['serial_authority']['policy_id']==POLICY
    assert result['coordinate_restoration']['Z:9']['status']=='GRAPH_FRAGMENT_RESTORED'


def test_padding_proof_replays_after_relocation_without_original_paths(tmp_path):
    from unittest.mock import patch
    old=tmp_path/'old';old.mkdir();inputs=padded_case(old)
    first=prepare(inputs,tmp_path/'first/context.pdb');audit(inputs,first)
    moved=tmp_path/'moved';shutil.copytree(old,moved);shutil.rmtree(old)
    relocated=tuple(moved/p.name for p in inputs[:3])+(inputs[3],)
    with patch('subprocess.Popen',side_effect=AssertionError('Context replay must not execute')):
        second=prepare(relocated,tmp_path/'second/context.pdb');audit(relocated,second)
    assert first['model'].read_bytes()==second['model'].read_bytes()
    for field in ('serial_authority','serial_repairs','removed_atoms','shadow_sha256','restoration_input_sha256'):
        assert first['receipt'][field]==second['receipt'][field]
