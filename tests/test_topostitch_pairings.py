"""Independent combinatorial checks for bounded one-partner alternatives."""
import copy
import itertools

import pytest

from nasolve.topostitch import DuplexEnd, propose_connections
from nasolve.topostitch_periodic import propose_periodic_connections
from nasolve.topostitch_pairings import describe_pairing_alternatives


HASH = 'a'*64


def screen(rows):
    ends = [DuplexEnd(name, seq, '5prime', tuple(xyz)) for name, seq, xyz in rows]
    return propose_connections(ends, source_model_sha256=HASH, max_distance_angstrom=3)


def selections(report):
    return {tuple(sorted(i for part in combination for i in part['candidate_indices']))
            for combination in itertools.product(*(c['alternatives'] for c in report['components']))}


def test_competing_edges_cannot_reuse_an_end_and_no_connection_survives():
    source = screen([('a','GA',(0,0,0)),('b','TC',(1,0,0)),('c','TC',(2,0,0))])
    result = describe_pairing_alternatives(source)
    assert selections(result) == {(), (0,), (1,)}
    assert result['scheme_count'] == 3
    assert result['selected_scheme'] is None
    assert result['geometry_validated'] is False
    assert result['runtime_authority'] is False
    assert result['components'][0]['alternatives'][0]['unmatched_ends'] == ['a','b','c']


def test_all_matchings_equal_independent_brute_force_not_only_maximal_ones():
    rows = [('a','AT',(0,0,0)), ('b','AT',(1,0,0)), ('c','AT',(2,0,0)), ('d','AT',(3,0,0))]
    source = screen(rows)
    expected = set()
    for count in range(len(source['candidates'])+1):
        for subset in itertools.combinations(range(len(source['candidates'])), count):
            ends = [e for i in subset for e in source['candidates'][i]['ends']]
            if len(set(ends)) == len(ends): expected.add(subset)
    result = describe_pairing_alternatives(source)
    assert selections(result) == expected
    assert result['scheme_count'] == len(expected)


def test_independent_pairs_are_factorized_instead_of_exponential_materialization():
    source = screen([(f'{i:03}-{side}', seq, (10*i+offset,0,0))
                     for i in range(40) for side,seq,offset in [('a','GA',0),('b','TC',1)]])
    result = describe_pairing_alternatives(source, max_alternatives_per_component=2)
    assert len(result['components']) == 40
    assert result['scheme_count'] == 2**40
    assert sum(len(c['alternatives']) for c in result['components']) == 80


def test_involutive_self_image_consumes_one_end_and_translation_is_deferred():
    pytest.importorskip('gemmi')
    source = propose_periodic_connections([DuplexEnd('a','AT','5prime',(1,2,3))],
        source_model_sha256=HASH, cell_parameters=(10,10,10,90,90,90),space_group='P 2',
        max_distance_angstrom=10.1)
    result = describe_pairing_alternatives(source)
    deferred = {r['candidate_index'] for r in result['deferred_candidates']}
    assert deferred
    expected = {i for i,c in enumerate(source['candidates']) if c['self_image_inverse_is_same_operator']}
    assert {i for s in selections(result) for i in s} == expected
    assert deferred == set(range(len(source['candidates'])))-expected
    assert all(len(s) <= 1 for s in selections(result))
    assert result['physical_orbit_capacity_validated'] is False


def test_budget_exhaustion_is_an_error_not_a_unique_partial_answer():
    source = screen([('a','AT',(0,0,0)),('b','AT',(1,0,0)),('c','AT',(2,0,0)),('d','AT',(3,0,0))])
    with pytest.raises(ValueError, match='budget'):
        describe_pairing_alternatives(source, max_alternatives_per_component=2)
    with pytest.raises(ValueError, match='budget'):
        describe_pairing_alternatives(source, max_search_states=1)


def test_empty_inventory_has_exactly_one_no_connection_scheme():
    result = describe_pairing_alternatives(screen([]))
    assert result['scheme_count'] == 1
    assert result['components'] == []


def test_fingerprint_drift_and_invalid_candidate_are_rejected():
    source = screen([('a','GA',(0,0,0)),('b','TC',(1,0,0))])
    changed = copy.deepcopy(source)
    changed['inputs']['ends'][0]['state'] = 'free'
    with pytest.raises(ValueError, match='fingerprint'):
        describe_pairing_alternatives(changed)
    changed = copy.deepcopy(source)
    changed['candidates'][0]['ends'][1] = 'unknown'
    with pytest.raises(ValueError, match='candidate'):
        describe_pairing_alternatives(changed)


def test_no_mutation_and_deterministic_result():
    source = screen([('a','GA',(0,0,0)),('b','TC',(1,0,0))])
    before = copy.deepcopy(source)
    result = describe_pairing_alternatives(source)
    assert source == before
    assert result == describe_pairing_alternatives(source)
    assert len(result['candidate_report_sha256']) == 64


@pytest.mark.parametrize('options', [{'max_alternatives_per_component': True}, {'max_search_states': 0}])
def test_invalid_budgets_are_rejected(options):
    with pytest.raises(ValueError): describe_pairing_alternatives(screen([]), **options)


def test_multiple_periodic_images_are_alternatives_not_multiple_partners():
    pytest.importorskip('gemmi')
    source = propose_periodic_connections([
        DuplexEnd('a','GA','5prime',(0,0,0)), DuplexEnd('b','TC','5prime',(5,0,0))],
        source_model_sha256=HASH, cell_parameters=(10,10,10,90,90,90),space_group='P 1',
        max_distance_angstrom=5.1)
    assert len(source['candidates']) == 2
    result = describe_pairing_alternatives(source)
    assert selections(result) == {(), (0,), (1,)}


def test_self_image_and_external_pair_cannot_both_consume_one_end():
    pytest.importorskip('gemmi')
    source = propose_periodic_connections([
        DuplexEnd('a','AT','5prime',(1,0,0)), DuplexEnd('b','AT','5prime',(2,0,0))],
        source_model_sha256=HASH, cell_parameters=(10,10,10,90,90,90),space_group='P 2',
        max_distance_angstrom=4.1)
    result = describe_pairing_alternatives(source)
    assert any(c['ends'][0] == c['ends'][1] for c in source['candidates'])
    assert any(c['ends'][0] != c['ends'][1] for c in source['candidates'])
    for selected in selections(result):
        used = [name for i in selected for name in set(source['candidates'][i]['ends'])]
        assert len(used) == len(set(used))


def test_pairings_cli_composes_with_contacts_and_budget_failure_has_no_stdout(tmp_path, capsys):
    from dataclasses import asdict
    import hashlib
    import json
    from nasolve.topostitch_inspect import main
    from .test_topostitch_contacts import contact_fixture
    text, assignments = contact_fixture()
    model=tmp_path/'model.pdb'; model.write_text(text)
    manifest=tmp_path/'ends.json'
    manifest.write_text(json.dumps({'schema_version':1,'kind':'topostitch-end-assignments',
        'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),'ends':[asdict(a) for a in assignments]}))
    args=[str(model),str(manifest),'--radius','15','--contacts','--pairings']
    assert main(args) == 0
    report=json.loads(capsys.readouterr().out)
    assert report['contact_assessment']['candidates']
    assert report['pairing_alternatives']['scheme_count'] == 2
    assert report['changes'] == []
    with pytest.raises(SystemExit) as error:
        main(args+['--max-alternatives','1'])
    assert error.value.code == 2
    captured=capsys.readouterr()
    assert not captured.out and 'budget' in captured.err


def test_reciprocal_operator_drift_is_rejected():
    pytest.importorskip('gemmi')
    source = propose_periodic_connections([
        DuplexEnd('a','GA','5prime',(0,0,0)), DuplexEnd('b','TC','5prime',(9,0,0))],
        source_model_sha256=HASH, cell_parameters=(10,10,10,90,90,90),space_group='P 1',
        max_distance_angstrom=2)
    source['candidates'][0]['reciprocal_image']['operator_xyz'] = 'x,y,z'
    with pytest.raises(ValueError, match='reciprocal'):
        describe_pairing_alternatives(source)
