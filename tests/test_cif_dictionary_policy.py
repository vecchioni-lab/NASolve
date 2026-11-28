"""Explicit representation contracts survive storage without promoting linked use.

Native inventories here are synthetic fixtures, not new Phenix qualifications.
"""
from copy import deepcopy
from hashlib import sha256
import json
import shutil
from unittest.mock import patch

import pytest

from nasolve.cif_candidate_usability import qualify_candidate_native, reassess_complete_candidate
from nasolve.cif_dictionary_store import (
    make_dictionary_request, publish_dictionary, lookup_dictionary,
    resolve_qualified_dictionary, resolve_dictionary_snapshot,
)
from nasolve.cif_purine_representation import POLICY_ID, OXO_POLICY_ID
from tests.test_cif_candidate_usability import native_case
from tests.test_cif_dictionary_store import inputs as legacy_inputs
from tests.test_cif_stereochemistry_audit import write


def inputs(tmp_path, policy=OXO_POLICY_ID):
    if policy == OXO_POLICY_ID:
        from tests.test_cif_oxo_purine_representation import pair
    else:
        from tests.test_cif_purine_representation import pair
    v, g = pair()
    for values in (v, g):
        for i, axis in enumerate('xyz'):
            values['_chem_comp_atom.'+axis] = [str((n+1)*(i+1)/10)
                for n in range(len(values['_chem_comp_atom.atom_id']))]
    s, c, m, native = native_case(tmp_path, g)
    write(s, v)
    q = qualify_candidate_native(s, c, m, 'Q17', native, bond_representation_policy=policy)
    assert q['native_usable'], q['checks']
    assert reassess_complete_candidate(s, c, 'Q17')['candidate_status'] == 'REJECTED'
    options = dict(source_authority='EXPLICIT', recipe={'policy_id':'TEST_REPAIR',
        'bond_representation_policy':policy}, generator={'name':'FAKE', 'version':'TEST'},
        consumer={'name':'FAKE', 'version':'TEST'})
    request = make_dictionary_request(s, 'Q17', **{k:v for k,v in options.items() if k != 'consumer'})
    provenance = {'converged':False, 'stopping':'ITERATION_LIMIT', 'notes':['Synthetic native evidence only.']}
    return s, c, m, native, q, options, request, provenance


@pytest.mark.parametrize('policy', [POLICY_ID, OXO_POLICY_ID])
def test_explicit_policy_publication_reuse_and_cold_relocation(tmp_path, policy):
    s,c,m,n,q,o,request,p = inputs(tmp_path, policy)
    a = resolve_qualified_dictionary(s, 'Q17', tmp_path/'store', tmp_path/'first',
        acquire=lambda:dict(candidate=c, qualification=q, provenance=p), **o)
    def forbidden(*args): raise AssertionError('Reuse must not regenerate or run native code')
    with patch('subprocess.Popen', side_effect=forbidden):
        b = resolve_qualified_dictionary(s, 'Q17', tmp_path/'store', tmp_path/'second',
            acquire=forbidden, requalify=forbidden, **o)
    assert a['status'] == 'PREPARED_AND_FROZEN' and b['status'] == 'REUSED'
    assert a['entry_id'] == b['entry_id'] and b['converged'] is False
    expected = c.read_bytes()
    for folder in ('store','first','source','candidate','models'): shutil.rmtree(tmp_path/folder)
    (tmp_path/'second').rename(tmp_path/'moved')
    with patch('subprocess.Popen', side_effect=forbidden):
        saved = resolve_dictionary_snapshot(tmp_path/'moved')
    assert saved['dictionary'].read_bytes() == expected and saved['provenance'] == p
    assert saved['manifest']['request'] == request
    assert saved['report']['linked_context'] == 'REQUALIFY_FOR_CURRENT_SITE'
    assert saved['report']['production_adoption'] == 'NOT_RUN'


@pytest.mark.parametrize('defect', ['missing_policy','wrong_policy','v2','future_version',
    'source_hash','assessment_policy','representation','missing_check','extra_check',
    'integer_check','schema_boolean'])
def test_explicit_qualification_cannot_be_relabelled_or_weakened(tmp_path, defect):
    s,c,m,n,q,o,request,p = inputs(tmp_path)
    if defect == 'missing_policy': request['recipe'].pop('bond_representation_policy')
    if defect == 'wrong_policy': request['recipe']['bond_representation_policy'] = POLICY_ID
    if defect == 'v2': q['policy_id'] = 'cif-isolated-candidate-native-usability-v2'
    if defect == 'future_version': q['policy_id'] = 'cif-isolated-candidate-native-usability-v99'
    if defect == 'source_hash': q['source_assessment']['finished_stereo']['source_sha256'] = '0'*64
    if defect == 'assessment_policy': q['source_assessment']['policy_id'] = 'invented'
    if defect == 'representation': q['source_assessment']['legacy_inspection']['bond_representation']['policy_id'] = POLICY_ID
    if defect == 'missing_check': q['checks'].pop('exact_active_bonds')
    if defect == 'extra_check': q['checks']['invented'] = True
    if defect == 'integer_check': q['checks']['exact_active_bonds'] = 1
    if defect == 'schema_boolean': q['schema_version'] = True
    with pytest.raises(ValueError):
        publish_dictionary(tmp_path/'store', request, s, c, q, consumer=o['consumer'], provenance=p)
    assert not (tmp_path/'store').exists()


@pytest.mark.parametrize('policy', [None, '', 'allow-everything', 1, {}, []])
def test_invalid_explicit_recipe_policy_is_rejected_before_writes(tmp_path, policy):
    s,c,m,q,o,request,p = legacy_inputs(tmp_path)
    o['recipe']['bond_representation_policy'] = policy
    with pytest.raises(ValueError):
        resolve_qualified_dictionary(s, 'Q17', tmp_path/'store', tmp_path/'run', **o)
    assert not (tmp_path/'store').exists() and not (tmp_path/'run').exists()


def test_default_request_bytes_and_old_entry_identity_are_unchanged(tmp_path):
    from nasolve.cif_dictionary_store import _bytes, _payload
    s,c,m,q,o,request,p = legacy_inputs(tmp_path)
    assert 'bond_representation_policy' not in request['recipe']
    manifest, data = _payload(request, s, c, q, o['consumer'], p)
    entry = publish_dictionary(tmp_path/'store', request, s, c, q, consumer=o['consumer'], provenance=p)
    assert entry['entry_id'] == sha256(_bytes(manifest)).hexdigest()
    assert lookup_dictionary(tmp_path/'store', request, o['consumer'])['status'] == 'HIT'
    explicit = deepcopy(request); explicit['recipe']['bond_representation_policy'] = OXO_POLICY_ID
    assert lookup_dictionary(tmp_path/'store', explicit, o['consumer'])['status'] == 'MISS'


def test_unknown_or_unbound_future_evidence_is_not_a_requalification_candidate(tmp_path):
    from nasolve.cif_dictionary_store import _bytes
    s,c,m,q,o,request,p = legacy_inputs(tmp_path)
    entry = publish_dictionary(tmp_path/'store', request, s, c, q, consumer=o['consumer'], provenance=p)
    directory = entry['directory']; manifest = deepcopy(entry['manifest'])
    q['policy_id'] = 'cif-isolated-candidate-native-usability-v99'
    raw = _bytes(q); (directory/'qualification.json').write_bytes(raw)
    manifest['artifacts']['qualification'].update(sha256=sha256(raw).hexdigest(), size=len(raw))
    manifest['native_qualification_policy'] = q['policy_id']
    raw = _bytes(manifest); (directory/'manifest.json').write_bytes(raw)
    directory.rename(directory.parent/sha256(raw).hexdigest())
    result = lookup_dictionary(tmp_path/'store', request, o['consumer'])
    assert result['status'] == 'MISS' and result['notes']


@pytest.mark.parametrize('wrong_evidence', [False, True])
def test_consumer_upgrade_requalifies_same_bytes_under_same_policy(tmp_path, wrong_evidence):
    s,c,m,n,q,o,request,p = inputs(tmp_path)
    entry = publish_dictionary(tmp_path/'store', request, s, c, q, consumer=o['consumer'], provenance=p)
    before = {f:f.read_bytes() for f in entry['directory'].iterdir()}
    o['consumer']['version'] = 'NEW'; o['generator']['version'] = 'NEW'
    assert lookup_dictionary(tmp_path/'store', request, o['consumer'])['status'] == 'REQUALIFICATION_REQUIRED'
    calls = []
    def requalify(source, candidate, consumer):
        calls.append(consumer['version'])
        return qualify_candidate_native(source, candidate, m, 'Q17', n,
            bond_representation_policy=POLICY_ID if wrong_evidence else OXO_POLICY_ID)
    def forbidden(): raise AssertionError('Do not regenerate saved numerics')
    if wrong_evidence:
        with pytest.raises(ValueError):
            resolve_qualified_dictionary(s, 'Q17', tmp_path/'store', tmp_path/'run',
                acquire=forbidden, requalify=requalify, **o)
        assert not (tmp_path/'run').exists()
    else:
        r = resolve_qualified_dictionary(s, 'Q17', tmp_path/'store', tmp_path/'run',
            acquire=forbidden, requalify=requalify, **o)
        assert r['status'] == 'REQUALIFIED_AND_FROZEN'
        saved = resolve_dictionary_snapshot(tmp_path/'run')
        assert saved['manifest']['request']['generator']['version'] == 'TEST'
        assert saved['dictionary'].read_bytes() == c.read_bytes()
    assert calls == ['NEW'] and all(f.read_bytes() == data for f,data in before.items())


@pytest.mark.parametrize('policy', [POLICY_ID, OXO_POLICY_ID])
def test_source_projection_requires_fresh_qualification_then_survives_relocation(tmp_path, monkeypatch, policy):
    from nasolve.cif_source_reuse import resolve_ordinary_dictionary, read_ordinary_dictionary
    import nasolve.curated_ligands as ligands
    s,c,m,n,q,o,request,p = inputs(tmp_path, policy)
    resolve_qualified_dictionary(s, 'Q17', tmp_path/'old_store', tmp_path/'saved',
        acquire=lambda:dict(candidate=c, qualification=q, provenance=p), **o)
    selected = tmp_path/'ordinary.cif'; selected.write_bytes(s.read_bytes()+b'\n# new source provenance\n')
    source = ligands.LigandDictionarySource('Q17', selected, 'CURATED', 'curated')
    monkeypatch.setattr(ligands, 'ligand_source', lambda *a,**k:source)
    monkeypatch.setattr(ligands, 'validate_ligand_dictionary', lambda *a:None)
    calls = []
    def qualify(a,b,consumer):
        calls.append(consumer)
        return qualify_candidate_native(a,b,m,'Q17',n,bond_representation_policy=policy)
    options = {k:v for k,v in o.items() if k != 'source_authority'}
    r = resolve_ordinary_dictionary('Q17', tmp_path/'never_execute', tmp_path/'new_store', tmp_path/'run',
        saved_snapshot=tmp_path/'saved', qualify=qualify, **options)
    assert r['status'] == 'SOURCE_REQUALIFIED_AND_FROZEN' and len(calls) == 1
    assert r['projection']['status'] == 'SOURCE_PROJECTION_PASS'
    expected = c.read_bytes()
    for folder in ('old_store','new_store','saved','source','candidate','models'): shutil.rmtree(tmp_path/folder)
    selected.unlink(); (tmp_path/'run').rename(tmp_path/'relocated')
    with patch('subprocess.Popen', side_effect=AssertionError('Cold read must not run native code')):
        saved = read_ordinary_dictionary(tmp_path/'relocated')
    assert saved['dictionary'].read_bytes() == expected
    assert saved['numerics']['provenance']['converged'] is False


def test_explicit_entries_do_not_automatically_enter_postmr(tmp_path, monkeypatch):
    from nasolve.cif_postmr_cache import prepare_postmr_dictionaries
    import nasolve.curated_ligands as ligands
    s,c,m,n,q,o,request,p = inputs(tmp_path)
    o['recipe'].update(policy_id='cif-source-native-complete-candidate-v1',
        source_metadata_policy='cif-source-declared-dna-metadata-v1')
    o['generator']['name'] = 'Phenix eLBOW'
    request = make_dictionary_request(s, 'Q17', **{k:v for k,v in o.items() if k != 'consumer'})
    publish_dictionary(tmp_path/'store', request, s, c, q, consumer=o['consumer'], provenance=p)
    selected = ligands.LigandDictionarySource('Q17', s, 'EXPLICIT', 'local-verified')
    monkeypatch.setattr(ligands, 'ligand_source', lambda *a,**k:selected)
    monkeypatch.setattr(ligands, 'validate_ligand_dictionary', lambda *a:None)
    with patch('nasolve.phenix_runtime.installation_from_candidate', side_effect=AssertionError('No automatic promotion')):
        result = prepare_postmr_dictionaries(['Q17'], tmp_path/'never_execute', tmp_path/'postmr', store_root=tmp_path/'store')
    row = result['components']['Q17']
    assert row['status'] == 'ORDINARY_SOURCE_FALLBACK'
    assert any('current-site' in note for note in row['notes'])
    assert (tmp_path/'postmr/Q17/source.cif').read_bytes() == s.read_bytes()


@pytest.mark.parametrize('defect', ['different_policy', 'stale_source_evidence', 'missing_adapter'])
def test_explicit_source_projection_failure_retains_ordinary_source(tmp_path, monkeypatch, defect):
    from nasolve.cif_source_reuse import resolve_ordinary_dictionary, read_ordinary_dictionary
    import nasolve.curated_ligands as ligands
    s,c,m,n,q,o,request,p = inputs(tmp_path)
    resolve_qualified_dictionary(s, 'Q17', tmp_path/'old_store', tmp_path/'saved',
        acquire=lambda:dict(candidate=c, qualification=q, provenance=p), **o)
    selected = tmp_path/'ordinary.cif'; selected.write_bytes(s.read_bytes()+b'\n# selected source\n')
    source = ligands.LigandDictionarySource('Q17', selected, 'CURATED', 'curated')
    monkeypatch.setattr(ligands, 'ligand_source', lambda *a,**k:source)
    monkeypatch.setattr(ligands, 'validate_ligand_dictionary', lambda *a:None)
    calls = []
    def qualify(*args): calls.append(True); return deepcopy(q)
    if defect == 'different_policy': o['recipe']['bond_representation_policy'] = POLICY_ID
    options = {k:v for k,v in o.items() if k != 'source_authority'}
    result = resolve_ordinary_dictionary('Q17', tmp_path/'never_execute', tmp_path/'new_store', tmp_path/'run',
        saved_snapshot=tmp_path/'saved', qualify=None if defect == 'missing_adapter' else qualify, **options)
    assert result['status'] == 'ORDINARY_SOURCE_FALLBACK'
    assert calls == ([True] if defect == 'stale_source_evidence' else [])
    assert not (tmp_path/'run/numerics').exists() and not (tmp_path/'new_store').exists()
    assert read_ordinary_dictionary(tmp_path/'run')['dictionary'].read_bytes() == selected.read_bytes()
