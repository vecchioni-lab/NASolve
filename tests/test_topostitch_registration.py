"""Logical end roles must resolve through a verified registration, never labels."""
import copy
import hashlib
import json
from dataclasses import asdict

import pytest

from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import inspect_pdb
from nasolve.topostitch_coordinates import inspect_end_assignments
from nasolve.topostitch_registration import LogicalEndAssignment, resolve_registered_ends
from .test_construct_registration import target
from .test_topostitch_coordinates import two_end_fixture


def inputs(tmp_path, rename=False, missing=None, changed_target=None):
    text, assignments = two_end_fixture()
    names = {'A':'M','B':'N','C':'Q','D':'R'} if rename else {c:c for c in 'ABCD'}
    mapping, codes, lines = {}, {}, []
    for line in text.splitlines():
        if line.startswith('ATOM'):
            chain, number = line[21], int(line[22:26])
            logical = f'{chain}:{number}'
            new_number = number+100 if rename else number
            mapping[logical] = f'{names[chain]}:{new_number}'
            codes[logical] = line[17:20].strip()
            line=line[:21]+names[chain]+f'{new_number:4d}'+line[26:]
        lines.append(line)
    path=tmp_path/'model.pdb'; path.write_text('\n'.join(lines)+'\n')
    assessment=inspect_pdb(path, polymer_ligand_codes={'DA','DC','DG','DT'})
    if changed_target: codes[changed_target] = 'DA' if codes[changed_target] != 'DA' else 'DG'
    if missing: mapping.pop(missing)
    registry=build_construct_registration(assessment, target(*codes.items()), {'copy_1':mapping}, source='synthetic-explicit-map')
    def key(site): return f'{site.chain}:{site.residue_number}'
    logical=[LogicalEndAssignment(a.end_id,'copy_1',tuple(map(key,a.overhang_sites)),
        tuple(map(key,a.terminal_pair)),tuple(map(key,a.inner_pair)),a.polarity,a.state) for a in assignments]
    return path,registry,logical


def resolve(path,registry,logical):
    return resolve_registered_ends(path, logical, registry, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def test_registered_rename_and_renumber_preserve_end_geometry(tmp_path):
    path, registry, logical=inputs(tmp_path)
    before, proof=resolve(path,registry,logical)
    baseline=inspect_end_assignments(path,before,expected_sha256=proof['source_model_sha256'],max_distance_angstrom=15)
    path,registry,logical=inputs(tmp_path,rename=True)
    after, proof=resolve(path,registry,logical)
    actual=inspect_end_assignments(path,after,expected_sha256=proof['source_model_sha256'],max_distance_angstrom=15)
    assert after[0].overhang_sites[0].chain=='M'
    assert after[0].overhang_sites[0].residue_number==101
    assert actual['ends']==baseline['ends']
    assert proof['source_bytes_verified'] is True
    assert proof['runtime_authority'] is False
    assert proof['topology_inferred'] is False
    assert len(proof['registration_sha256'])==64
    assert str(tmp_path) not in json.dumps(proof)


def test_partial_mapping_preserves_unresolved_end_instead_of_guessing(tmp_path):
    path,registry,logical=inputs(tmp_path,missing='A:1')
    assignments, proof=resolve(path,registry,logical)
    assert [a.end_id for a in assignments]==['end2']
    assert proof['ends'][0]['assessment']=='UNRESOLVED'
    assert proof['ends'][0]['issues'][0]['code']=='MISSING_LOGICAL_MAPPING'
    assert proof['coverage_complete'] is False
    assert proof['ends'][1]['assessment']=='RESOLVED'


def test_pending_chemistry_change_is_not_assumed_to_have_happened(tmp_path):
    path,registry,logical=inputs(tmp_path,changed_target='A:1')
    assignments, proof=resolve(path,registry,logical)
    assert [a.end_id for a in assignments]==['end2']
    assert proof['ends'][0]['issues'][0]['code']=='TARGET_IDENTITY_MISMATCH'


def test_model_drift_and_registration_model_mismatch_fail(tmp_path):
    path,registry,logical=inputs(tmp_path)
    wrong=copy.deepcopy(registry); wrong['model']['sha256']='b'*64
    with pytest.raises(ValueError,match='checksum'):
        resolve(path,wrong,logical)
    with pytest.raises(ValueError,match='checksum'):
        resolve_registered_ends(path,logical,registry,expected_sha256='a'*64)


def test_unknown_copy_or_logical_site_is_an_input_error(tmp_path):
    path,registry,logical=inputs(tmp_path)
    row=asdict(logical[0]); row['copy_id']='unknown'
    with pytest.raises(ValueError,match='copy'):
        resolve(path,registry,[LogicalEndAssignment(**row)])
    row=asdict(logical[0]); row['overhang_sites']=('A:999','A:2')
    with pytest.raises(ValueError,match='logical site'):
        resolve(path,registry,[LogicalEndAssignment(**row)])


def test_declared_registered_identity_is_checked_against_actual_bytes(tmp_path):
    path,registry,logical=inputs(tmp_path)
    # Consistent-looking metadata can still lie about actual atom residue names.
    fake=copy.deepcopy(registry)
    row=next(r for r in fake['copies'][0]['mappings'] if r['logical_site']=='A:1')
    row['coordinate_residue_code']=row['target_residue_code']='DA'
    assignments,proof=resolve(path,fake,logical)
    assert [a.end_id for a in assignments]==['end2']
    assert proof['ends'][0]['issues'][0]['code']=='COORDINATE_IDENTITY_MISMATCH'


def test_logical_topology_fields_are_strict():
    with pytest.raises(ValueError):
        LogicalEndAssignment('e','copy_1',('A:1','A:1'),('A:2','B:2'),('A:3','B:1'),'5prime')
    with pytest.raises(ValueError):
        LogicalEndAssignment('e','copy_1',('A 1',),('A:2','B:2'),('A:3','B:1'),'5prime')


def test_multiple_copies_use_explicit_copy_identity(tmp_path):
    from dataclasses import replace
    path, registry, logical=inputs(tmp_path)
    original=path.read_text()
    extra=[]
    for line in original.splitlines():
        if line.startswith('ATOM'):
            line=line[:21]+dict(zip('ABCD','EFGH'))[line[21]]+line[22:]
            line=line[:30]+f'{float(line[30:38])+50:8.3f}'+line[38:]
            extra.append(line)
    path.write_text(original.replace('END\n','')+'TER\n'+'\n'.join(extra)+'\nEND\n')
    rows=registry['copies'][0]['mappings']
    reference=target(*[(r['logical_site'],r['target_residue_code']) for r in rows])
    maps={'copy_1':{r['logical_site']:r['coordinate_site'] for r in rows},
          'copy_2':{r['logical_site']:dict(zip('ABCD','EFGH'))[r['coordinate_site'][0]]+r['coordinate_site'][1:] for r in rows}}
    registry=build_construct_registration(inspect_pdb(path,polymer_ligand_codes={'DA','DC','DG','DT'}),reference,maps,source='two-copy-fixture')
    assignments, proof=resolve(path,registry,[replace(logical[0],copy_id='copy_2')])
    assert assignments[0].overhang_sites[0].chain=='E'
    assert proof['ends'][0]['copy_id']=='copy_2'
    assert proof['coverage_complete'] is True


def test_split_coordinate_chain_and_insertion_code_do_not_change_logical_order(tmp_path):
    path,registry,logical=inputs(tmp_path)
    text=[]
    for line in path.read_text().splitlines():
        if line.startswith('ATOM') and line[21:26]=='A   1':
            line=line[:21]+'Z'+line[22:26]+'X'+line[27:]
        text.append(line)
    path.write_text('\n'.join(text)+'\n')
    rows=registry['copies'][0]['mappings']
    reference=target(*[(r['logical_site'],r['target_residue_code']) for r in rows])
    mapping={r['logical_site']:('Z:1X' if r['logical_site']=='A:1' else r['coordinate_site']) for r in rows}
    registry=build_construct_registration(inspect_pdb(path,polymer_ligand_codes={'DA','DC','DG','DT'}),reference,{'copy_1':mapping},source='split-chain-fixture')
    assignments,proof=resolve(path,registry,logical)
    assert assignments[0].overhang_sites[0].chain=='Z'
    assert assignments[0].overhang_sites[0].insertion_code=='X'
    assert assignments[0].overhang_sites[1].chain=='A'
    assert proof['topology_inferred'] is False


def test_cli_registration_checksum_and_partial_coverage(tmp_path,capsys):
    from nasolve.topostitch_inspect import main
    path,registry,logical=inputs(tmp_path,missing='A:1')
    registration_path=tmp_path/'registration.json'
    registration_path.write_text(json.dumps(registry))
    manifest=tmp_path/'logical-ends.json'
    manifest.write_text(json.dumps({'schema_version':1,'kind':'topostitch-logical-end-assignments',
        'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'registration_sha256':hashlib.sha256(registration_path.read_bytes()).hexdigest(),
        'ends':[asdict(a) for a in logical]}))
    args=[str(path),str(manifest),'--registration',str(registration_path),'--radius','15','--pairings']
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    assert main(args)==0
    report=json.loads(capsys.readouterr().out)
    assert report['workflow']['proposal_state']=='INCOMPLETE_ASSESSMENT'
    assert len(report['registration_assessment']['ends'])==2
    assert len(report['ends'])==1
    assert report['pairing_alternatives']['scheme_count']==1
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    registration_path.write_text(registration_path.read_text()+'\n')
    with pytest.raises(SystemExit) as error: main(args)
    assert error.value.code==2
    captured=capsys.readouterr()
    assert captured.out=='' and 'Registration file checksum' in captured.err


def test_relocation_with_original_path_absent_keeps_mapping_receipt(tmp_path):
    from shutil import move
    original=tmp_path/'original'; original.mkdir()
    path,registry,logical=inputs(original,rename=True)
    before,proof=resolve(path,registry,logical)
    moved=tmp_path/'new-name.pdb'; move(path,moved); original.rmdir()
    after,receipt=resolve(moved,registry,logical)
    assert not original.exists()
    assert after==before and receipt==proof
