"""Identity-only repair of Coot-wide serial changes; no native tool in fixtures."""
from hashlib import sha256
import shutil

import pytest

from nasolve.postmr_context import prepare_construction_context
from nasolve.cif_postmr_construction import audit_construction_context
from tests.test_postmr_context import fixture, atom_rows

POLICY = 'postmr-input-identity-serial-context-v1'


def globally_numbered(tmp_path):
    raw, parent, source, action = fixture(tmp_path)
    for path in (raw, parent):
        path.write_text(''.join(line for line in path.read_text().splitlines(keepends=True)
                                if not line.startswith('CONECT')))
    raw.write_text(''.join(line[:6]+f'{int(line[6:11])+5:5d}'+line[11:]
                          if line.startswith('HETATM') and line[22:26].strip()!='9'
                          else line for line in raw.read_text().splitlines(keepends=True)))
    return raw, parent, source, action


def prepare(inputs, out, **kwargs):
    raw, parent, source, action = inputs
    return prepare_construction_context(raw, parent, (action,), {'ZZZ': source},
        {'Z:9': parent}, out, serial_identity_policy=POLICY, **kwargs)


def audit(inputs, result):
    raw, parent, source, action = inputs
    return audit_construction_context(parent, raw, result['model'], (action,),
        {'ZZZ': source}, result['receipt'], context_shadow=result['shadow'],
        parent_models={'Z:9': parent})


def test_global_serial_repair_proves_only_identity_fields_and_internal_op3(tmp_path):
    inputs=globally_numbered(tmp_path)
    before={p:p.read_bytes() for p in inputs[:3]}
    result=prepare(inputs,tmp_path/'context.pdb')
    assert result['receipt']['status']=='CONTEXT_PREPARED'
    assert result['receipt']['serial_authority']['policy_id']==POLICY
    assert any(row['site']=='Z:8' for row in result['receipt']['serial_repairs'])
    old,new=map(atom_rows,(inputs[0],result['model']))
    assert len(old)-len(new)==1
    for key,line in new.items():
        assert line[:6]+line[11:]==old[key][:6]+old[key][11:]
    assert all(p.read_bytes()==data for p,data in before.items())
    checked=audit(inputs,result)
    assert checked['status']=='CONSTRUCTION_CONTEXT_DELTA_PASS'
    assert checked['unselected_records_preserved'] is False
    assert checked['unselected_nonserial_fields_preserved'] is True
    assert checked['inherited_connections_rebound'] is False


def test_historical_default_refuses_global_serials_without_new_policy(tmp_path):
    raw,parent,source,action=globally_numbered(tmp_path)
    result=prepare_construction_context(raw,parent,(action,),{'ZZZ':source},
        {'Z:9':parent},tmp_path/'context.pdb')
    assert result['receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert result['model'].read_bytes()==raw.read_bytes()


@pytest.mark.parametrize('defect',['conect','anisou','sigatm','siguij','model',
    'endmdl','duplicate_reference','duplicate_identity','coordinate','occupancy',
    'bfactor','charge','record_type','duplicate_ter','invalid_ter','invalid_serial'])
def test_unsafe_global_serial_context_preserves_complete_raw(tmp_path,defect):
    inputs=globally_numbered(tmp_path);raw,parent,*_=inputs
    lines=raw.read_text().splitlines(keepends=True)
    index=next(i for i,l in enumerate(lines) if l.startswith('HETATM') and l[22:26].strip()=='8')
    line=lines[index]
    additions={'conect':'CONECT    1    2\n','anisou':'ANISOU'+line[6:],
               'sigatm':'SIGATM'+line[6:],'siguij':'SIGUIJ'+line[6:],
               'model':'MODEL        1\n','endmdl':'ENDMDL\n',
               'duplicate_ter':'TER       3\nTER       3\n','invalid_ter':'TER   ?????\n'}
    if defect in additions:lines.insert(0,additions[defect])
    elif defect=='duplicate_reference':parent.write_text(parent.read_text().replace('HETATM   10','HETATM    1'))
    elif defect=='duplicate_identity':lines.append(line)
    elif defect=='coordinate':lines[index]=line[:30]+f'{91.:8.3f}'+line[38:]
    elif defect=='occupancy':lines[index]=line[:54]+'  0.50'+line[60:]
    elif defect=='bfactor':lines[index]=line[:60]+' 12.00'+line[66:]
    elif defect=='charge':lines[index]=line[:78]+'1+\n'
    elif defect=='record_type':lines[index]='ATOM  '+line[6:]
    elif defect=='invalid_serial':lines[index]=line[:6]+'    0'+line[11:]
    raw.write_text(''.join(lines))
    before=raw.read_bytes();result=prepare(inputs,tmp_path/'context.pdb')
    assert result['receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert result['model'].read_bytes()==before
    assert not result['receipt']['removed_atoms'] and not result['receipt']['serial_repairs']


def test_ter_numbers_are_reserved_without_editing_record(tmp_path):
    inputs=globally_numbered(tmp_path)
    for path in inputs[:2]:path.write_text(path.read_text().replace('END\n','TER       3\nEND\n'))
    result=prepare(inputs,tmp_path/'context.pdb')
    assert result['receipt']['status']=='CONTEXT_PREPARED'
    assert result['receipt']['serial_authority']['reserved_ter_serials']==[3]
    assert 3 not in [int(l[6:11]) for l in atom_rows(result['shadow']).values()]
    assert 'TER       3\n' in result['model'].read_text()
    audit(inputs,result)


@pytest.mark.parametrize('defect',['policy','count','reserved','delta','noncanonical','metadata','reference'])
def test_independent_audit_rejects_forged_identity_authority(tmp_path,defect):
    inputs=globally_numbered(tmp_path);result=prepare(inputs,tmp_path/'context.pdb')
    assert result['receipt']['status']=='CONTEXT_PREPARED'
    receipt=result['receipt'];authority=receipt['serial_authority']
    if defect=='policy':authority['policy_id']='unknown'
    elif defect=='count':authority['unselected_atom_count']+=1
    elif defect=='reserved':authority['reserved_ter_serials']=[999]
    elif defect=='delta':receipt['serial_repairs'].pop()
    elif defect=='reference':
        p=inputs[1];p.write_text(p.read_text().replace('  -0.530','  -0.630'))
        receipt['reference_model_sha256']=sha256(p.read_bytes()).hexdigest()
    else:
        # Forge both shadow/model and all corresponding hashes/serial deltas.
        for p in (result['model'],result['shadow']):
            lines=p.read_text().splitlines(keepends=True)
            i=next(i for i,l in enumerate(lines) if l.startswith('HETATM') and l[22:26].strip()=='8')
            l=lines[i]
            lines[i]=l[:6]+'  777'+l[11:] if defect=='noncanonical' else l[:60]+' 91.00'+l[66:]
            p.write_text(''.join(lines))
        for row in receipt['serial_repairs']:
            if row['site']=='Z:8' and row['atom']=="O3'":row['new_serial']=777
        receipt['shadow_sha256']=sha256(result['shadow'].read_bytes()).hexdigest()
        receipt['restoration_input_sha256']=sha256(result['model'].read_bytes()).hexdigest()
    with pytest.raises(ValueError):audit(inputs,result)


def test_ordinary_path_uses_new_authority_and_rolls_back_failed_final_proof(tmp_path,monkeypatch):
    from nasolve.postmr import construct_postmr_model
    inputs=globally_numbered(tmp_path);raw,parent,source,action=inputs
    def coot(model,output,actions,executable,directory,environment,dictionaries,parents,**unused):
        shutil.copyfile(raw,output);shutil.copyfile(parent,parents['Z:9'])
        log=directory/'coot.log';log.write_text('synthetic Coot output')
        return directory/'mutate.py',log
    monkeypatch.setattr('nasolve.postmr._run_coot',coot)
    result=construct_postmr_model(parent,(action,),{'ZZZ':source},tmp_path/'ok/model.pdb',coot_executable=tmp_path/'coot')
    assert result['coordinate_restoration']['Z:9']['status']=='GRAPH_FRAGMENT_RESTORED'
    assert result['context_receipt']['serial_authority']['policy_id']==POLICY
    def fail(*args,**kwargs):raise ValueError('deliberately failed final proof')
    monkeypatch.setattr('nasolve.postmr.sanitize_phosphates',fail)
    rollback=construct_postmr_model(parent,(action,),{'ZZZ':source},tmp_path/'rollback/model.pdb',coot_executable=tmp_path/'coot')
    assert rollback['context_receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert rollback['model'].read_bytes()==raw.read_bytes()
    assert not rollback['context_receipt']['serial_repairs']
    assert rollback['context_receipt']['attempted_serial_repairs']


def test_cold_relocated_inputs_reproduce_context_after_old_anchor_removed(tmp_path):
    old=tmp_path/'old';old.mkdir();inputs=globally_numbered(old)
    first=prepare(inputs,tmp_path/'first/context.pdb');audit(inputs,first)
    relocated=tmp_path/'new';shutil.copytree(old,relocated);shutil.rmtree(old)
    new=tuple(relocated/p.name for p in inputs[:3])+(inputs[3],)
    second=prepare(new,tmp_path/'second/context.pdb');audit(new,second)
    assert first['model'].read_bytes()==second['model'].read_bytes()
    # Sanitizer reports include provenance paths; operational identity authority
    # and exact file bindings are anchor-independent.
    for field in ('serial_authority','serial_repairs','removed_atoms','shadow_sha256','restoration_input_sha256'):
        assert first['receipt'][field]==second['receipt'][field]


def test_final_audit_binds_explicit_terminal_intent_without_inferring_consent(tmp_path,monkeypatch):
    from nasolve.postmr import construct_postmr_model
    from nasolve.cif_postmr_construction import audit_postmr_construction
    from tests.helpers import pdb_record
    from tests.test_postmr_context import SCAFFOLD
    inputs=globally_numbered(tmp_path);raw,parent,source,action=inputs
    terminal=''.join(pdb_record('HETATM',i,name,'DT','W',1,
        element='P' if name=='P' else 'O' if name.startswith('O') else 'C',
        x=xyz[0]+100,y=xyz[1]+100,z=xyz[2]+100)
        for i,(name,xyz) in enumerate({**SCAFFOLD,'OP3':(-.5,-.9,-1.2)}.items(),500))
    for path in (raw,parent):path.write_text(path.read_text().replace('END\n',terminal+'END\n'))
    def coot(model,output,actions,executable,directory,environment,dictionaries,parents,**unused):
        shutil.copyfile(raw,output);shutil.copyfile(parent,parents['Z:9'])
        log=directory/'coot.log';log.write_text('synthetic Coot output')
        return directory/'mutate.py',log
    monkeypatch.setattr('nasolve.postmr._run_coot',coot)
    result=construct_postmr_model(parent,(action,),{'ZZZ':source},tmp_path/'ok/model.pdb',
        coot_executable=tmp_path/'coot',allow_op3_sites=('W:1',))
    assert result['context_receipt']['status']=='CONTEXT_PREPARED'
    args=(parent,result['raw_model'],result['model'],(action,),{'ZZZ':source},
          result['parent_models'],result['coordinate_restoration'])
    kwargs=dict(restoration_input=result['restoration_input'],context_receipt=result['context_receipt'],
                context_shadow=result['context_shadow'])
    checked=audit_postmr_construction(*args,**kwargs,allow_op3_sites=('W:1',))
    assert checked['status']=='CONSTRUCTION_CONTROLS_PASS'
    assert checked['context_audit']['final_phosphate_audit']['allow_op3_sites']==['W:1']
    assert checked['unselected_raw_records_preserved'] is False
    assert ('W','1',' ','OP3') in atom_rows(result['model'])
    with pytest.raises(ValueError,match='intent'):
        audit_postmr_construction(*args,**kwargs)
    result['context_receipt']['allow_op3_sites']=[]
    with pytest.raises(ValueError,match='intent'):
        audit_postmr_construction(*args,**kwargs,allow_op3_sites=('W:1',))
