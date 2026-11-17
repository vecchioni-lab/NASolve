"""End discovery follows declared chemical order, never coordinate numbering."""
from dataclasses import replace

import pytest

from nasolve.topostitch_discovery import BackboneStrand, discover_logical_end_assignments


def strands():
    return [BackboneStrand('long',('A:1','A:2','A:3','A:4'),'chemical','unknown'),
            BackboneStrand('short',('B:2','B:3'),'unknown','chemical')]


PAIRS=[('A:3','B:3'),('A:4','B:2')]


def discover(routes=None,pairs=None,**options):
    return discover_logical_end_assignments(strands() if routes is None else routes,
        PAIRS if pairs is None else pairs,copy_id='copy_1',pairing_inventory_complete=True,**options)


def test_finds_5prime_overhang_with_ordered_anchor_and_inner_pair():
    assignments,report=discover()
    end,=assignments
    assert end.overhang_sites==('A:1','A:2')
    assert end.terminal_pair==('A:3','B:3')
    assert end.inner_pair==('A:4','B:2')
    assert end.polarity=='5prime'
    assert report['topology_source']=='caller_declared_strands_and_duplex_core_pairs'
    assert report['runtime_authority'] is False
    assert report['coverage_complete'] is False  # inward boundary remains unknown


def test_3prime_overhang_uses_chemical_order_not_traversal_order():
    routes=[BackboneStrand('long',('A:4','A:3','A:2','A:1'),'unknown','chemical'),
            BackboneStrand('short',('B:3','B:2'),'chemical','unknown')]
    assignments,_=discover(routes)
    end,=assignments
    assert end.overhang_sites==('A:2','A:1')
    assert end.polarity=='3prime'
    assert end.terminal_pair==('A:3','B:3')


def test_pair_input_order_does_not_change_end_identity_or_roles():
    a,report=discover()
    b,reordered=discover(list(reversed(strands())), [('B:2','A:4'),('B:3','A:3')])
    assert a==b
    assert report==reordered


def test_internal_gap_is_not_a_terminal_overhang():
    routes=[replace(strands()[0],sites=('A:0','A:1','A:2','A:3','A:4')),
            strands()[1],BackboneStrand('extra',('C:1',),'chemical','chemical')]
    assignments,report=discover(routes,PAIRS+[('A:0','C:1')])
    assert not assignments
    assert any(b['status']=='INTERNAL_UNPAIRED_INTERVAL' for b in report['boundaries'])


@pytest.mark.parametrize('boundary',['unknown','representation'])
def test_serialization_or_unknown_boundary_cannot_assert_a_chemical_end(boundary):
    routes=[replace(strands()[0],five_prime_boundary=boundary),strands()[1]]
    assignments,report=discover(routes)
    assert not assignments
    assert any(b['status']=='UNRESOLVED_BOUNDARY' for b in report['boundaries'])


def test_protected_junction_stops_discovery_at_anchor():
    assignments,report=discover(protected_sites=('A:3',))
    assert not assignments
    assert any(b['status']=='PROTECTED_JUNCTION' for b in report['boundaries'])


def test_two_unpaired_tails_are_not_guessed_into_one_sticky_end():
    routes=[strands()[0],replace(strands()[1],sites=('B:2','B:3','B:4'))]
    assignments,report=discover(routes)
    assert not assignments
    assert any(b['status']=='TWO_UNPAIRED_TAILS' for b in report['boundaries'])


def test_no_single_strand_overhang_does_not_create_a_repair_request():
    routes=[replace(strands()[0],sites=('A:3','A:4')),strands()[1]]
    assignments,report=discover(routes)
    assert not assignments
    assert any(b['status']=='NO_SINGLE_STRAND_OVERHANG' for b in report['boundaries'])


def test_overhang_length_budget_is_not_silently_truncated():
    assignments,report=discover(max_overhang_length=1)
    assert not assignments
    assert any(b['status']=='OVERHANG_LENGTH_LIMIT' for b in report['boundaries'])


def test_one_base_pair_cannot_supply_an_oriented_duplex_end():
    assignments,report=discover(pairs=[PAIRS[0]])
    assert not assignments
    assert report['isolated_pairs']==[['A:3','B:3']]
    assert report['coverage_complete'] is False


def test_conflicting_pair_or_strand_topology_is_rejected():
    with pytest.raises(ValueError,match='partner'):
        discover(pairs=PAIRS+[('A:3','A:1')])
    with pytest.raises(ValueError,match='multiple strands'):
        discover(strands()+[BackboneStrand('duplicate',('A:1',),'chemical','chemical')])
    with pytest.raises(ValueError,match='unknown'):
        discover(pairs=PAIRS+[('X:1','X:2')])


def test_adjacent_paired_sites_are_not_their_own_inner_step():
    routes=[BackboneStrand('one',('A:1','A:2','A:3','A:4'),'chemical','chemical')]
    assignments,report=discover(routes,[('A:3','A:4')])
    assert not assignments
    assert report['isolated_pairs']==[['A:3','A:4']]


def test_partial_pairing_inventory_cannot_turn_missing_evidence_into_an_overhang():
    assignments,report=discover_logical_end_assignments(strands(),PAIRS,copy_id='copy_1')
    assert not assignments
    assert report['coverage_complete'] is False
    assert any(b['status']=='PAIRING_COVERAGE_UNKNOWN' for b in report['boundaries'])


def test_discovery_cli_feeds_registration_and_preserves_unknown_boundaries(tmp_path,capsys):
    import hashlib,json
    from dataclasses import asdict
    from nasolve.topostitch_inspect import main
    from .test_topostitch_registration import inputs
    model,registration,_=inputs(tmp_path,rename=True)
    reg=tmp_path/'reg.json';reg.write_text(json.dumps(registration))
    manifest=tmp_path/'discovery.json'
    routes=strands()+[BackboneStrand('long2',('C:1','C:2','C:3','C:4'),'chemical','unknown'),
                      BackboneStrand('short2',('D:2','D:3'),'unknown','chemical')]
    value={'schema_version':1,'kind':'topostitch-end-discovery-input',
           'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
           'registration_sha256':hashlib.sha256(reg.read_bytes()).hexdigest(),
           'copy_id':'copy_1','strands':[asdict(s) for s in routes],
           'duplex_pairs':PAIRS+[('C:3','D:3'),('C:4','D:2')],
           'pairing_inventory_complete':True}
    manifest.write_text(json.dumps(value))
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    args=[str(model),str(manifest),'--registration',str(reg),'--radius','15','--pairings','--windows']
    assert main(args)==0
    report=json.loads(capsys.readouterr().out)
    assert len(report['ends'])==2
    assert all(e['status']=='INSUFFICIENT_PAIRED_CONTEXT' for e in report['editable_windows']['ends'])
    assert report['pairing_alternatives']['scheme_count']==2
    assert report['workflow']['proposal_state']=='INCOMPLETE_ASSESSMENT'
    assert len(report['registration_assessment']['discovery_assessment']['logical_assignments'])==2
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    value.pop('pairing_inventory_complete')
    manifest.write_text(json.dumps(value))
    assert main(args)==0
    report=json.loads(capsys.readouterr().out)
    assert report['ends']==[]
    assert report['workflow']['proposal_state']=='INCOMPLETE_ASSESSMENT'


def test_discovery_report_is_json_normalized_and_detached():
    import json
    _,report=discover()
    assert json.loads(json.dumps(report,allow_nan=False))==report


def long_core(protected=()):
    routes=[BackboneStrand('a',tuple(f'A:{i}' for i in range(1,9)),'chemical','unknown'),
            BackboneStrand('b',tuple(f'B:{i}' for i in range(1,7)),'unknown','chemical')]
    pairs=[(f'A:{i}',f'B:{9-i}') for i in range(3,9)]
    return discover_logical_end_assignments(routes,pairs,copy_id='copy_1',
        protected_sites=protected,pairing_inventory_complete=True)[1]


def test_windows_expand_by_whole_pairs_and_preserve_two_inner_anchors():
    from nasolve.topostitch_discovery import plan_editable_windows
    report=plan_editable_windows(long_core(),max_base_pairs=5,fixed_anchor_pairs=2)
    end,=report['ends']
    assert [v['base_pair_count'] for v in end['windows']]==[3,4,5]
    last=end['windows'][-1]
    assert last['fixed_pairs']==[['A:6','B:3'],['A:7','B:2']]
    assert last['movable_pairs']==[['A:3','B:6'],['A:4','B:5'],['A:5','B:4']]
    assert last['overhang_sites']==['A:1','A:2']
    assert end['stop_reason']=='PAIR_COUNT_LIMIT'
    assert report['selected_window'] is None
    assert report['geometry_feasibility_evaluated'] is False


def test_window_expansion_stops_before_protected_junction():
    from nasolve.topostitch_discovery import plan_editable_windows
    end,=plan_editable_windows(long_core(('A:7',)),max_base_pairs=8)['ends']
    assert end['stop_reason']=='PROTECTED_JUNCTION'
    assert max(w['base_pair_count'] for w in end['windows'])==4
    assert all('A:7' not in w['movable_sites'] for w in end['windows'])


def test_window_requires_movable_context_and_rejects_stale_discovery():
    from nasolve.topostitch_discovery import plan_editable_windows
    _,discovery=discover()
    end,=plan_editable_windows(discovery,max_base_pairs=5)['ends']
    assert end['status']=='INSUFFICIENT_PAIRED_CONTEXT'
    assert end['windows']==[]
    discovery['logical_assignments'][0]['polarity']='3prime'
    with pytest.raises(ValueError,match='discovery'):
        plan_editable_windows(discovery,max_base_pairs=5)


def test_declared_free_end_is_retained_but_never_gets_a_movement_window():
    from nasolve.topostitch_discovery import plan_editable_windows
    report=long_core()
    values=report['inputs']
    assignments,report=discover_logical_end_assignments(
        [BackboneStrand(**s) for s in values['strands']],values['duplex_pairs'],
        copy_id='copy_1',pairing_inventory_complete=True,do_not_connect_sites=('A:1',))
    assert assignments[0].state=='free'
    end,=plan_editable_windows(report,max_base_pairs=6)['ends']
    assert end['status']=='EXCLUDED_END_STATE'
    assert end['windows']==[]


def test_window_planner_accepts_earlier_discovery_report_without_free_site_extension():
    import hashlib,json
    from nasolve.topostitch_discovery import plan_editable_windows
    report=long_core()
    report['inputs'].pop('do_not_connect_sites')
    report.pop('unmatched_do_not_connect_sites')
    report['input_sha256']=hashlib.sha256(json.dumps(report['inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    end,=plan_editable_windows(report,max_base_pairs=5)['ends']
    assert [w['base_pair_count'] for w in end['windows']]==[3,4,5]
