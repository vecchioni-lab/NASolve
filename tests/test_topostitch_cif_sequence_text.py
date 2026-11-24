"""Deposited sequence text is evidence, never a new target or chain assignment."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from tests.test_topostitch_cif_polymer import fixture, observe


def text_audit(tables, components=()):
    from nasolve.topostitch_cif_polymer import _sequence_text
    return _sequence_text(tables, list(components))


def tables(codes=('DA','DC','DG','DT'), literal='(DA)(DC)(DG)(DT)', canonical='ACGT'):
    return {'_entity_poly.':[dict(entity_id='1',type='polydeoxyribonucleotide',
                pdbx_seq_one_letter_code=literal,pdbx_seq_one_letter_code_can=canonical)],
            '_entity_poly_seq.':[dict(entity_id='1',num=str(i),mon_id=c) for i,c in enumerate(codes,1)]}


def parent(code, value, block='model'):
    return dict(block=block, source_row=1, row=dict(id=code,mon_nstd_parent_comp_id=value))


def test_standard_literal_and_canonical_text_match():
    result=text_audit(tables());r=result[0]
    assert r['literal_status']==r['canonical_status']=='MATCH'
    assert r['literal_components']==['DA','DC','DG','DT']
    assert r['canonical_expected']=='ACGT'
    assert [p['sequence_position'] for p in r['positions']]==[1,2,3,4]


@pytest.mark.parametrize('field,value',[
    ('pdbx_seq_one_letter_code','(DA)(DC)(DG)'),
    ('pdbx_seq_one_letter_code','(DA)(DG)(DG)(DT)'),
    ('pdbx_seq_one_letter_code_can','AGGT'),
    ('pdbx_seq_one_letter_code_can','ACGTT'),
])
def test_wrong_text_is_not_accepted(field,value):
    t=tables();t['_entity_poly.'][0][field]=value;r=text_audit(t)[0]
    assert r['literal_status' if field.endswith('code') else 'canonical_status']=='CONFLICT'


def test_plain_dna_letters_do_not_silently_become_deoxy_components():
    r=text_audit(tables(codes=('DA','DC'),literal='AC',canonical='AC'))[0]
    assert r['literal_components']==['A','C']
    assert r['literal_status']=='CONFLICT' and r['canonical_status']=='MATCH'


def test_rna_and_hybrid_literal_tokens_use_same_parser():
    t=tables(codes=('A','U','DC','DG'),literal='A U\n(DC)(DG)',canonical='AUCG')
    t['_entity_poly.'][0]['type']='polydeoxyribonucleotide/polyribonucleotide hybrid'
    r=text_audit(t)[0];assert r['literal_status']==r['canonical_status']=='MATCH'


@pytest.mark.parametrize('value',[None,False,''])
def test_missing_text_retained_unavailable(value):
    r=text_audit(tables(literal=value,canonical=value))[0]
    assert r['literal_status']==r['canonical_status']=='UNAVAILABLE'


def test_modified_component_needs_parent_not_name_or_alias():
    t=tables(codes=('DA','A1C3T'),literal='(DA)(A1C3T)',canonical='AC')
    r=text_audit(t,[dict(block='model',source_row=1,row={'id':'A1C3T','name':'cytidine'})])[0]
    assert r['literal_status']=='MATCH' and r['canonical_status']=='UNAVAILABLE'
    assert r['positions'][1]['canonical_options']==[]
    assert r['canonical_expected'] is None


def test_explicit_parent_can_qualify_modified_canonical_letter():
    t=tables(codes=('DA','A1C3T'),literal='(DA)(A1C3T)',canonical='AC')
    r=text_audit(t,[parent('A1C3T','DC','component')])[0]
    assert r['literal_status']==r['canonical_status']=='MATCH'
    assert r['positions'][1]['parent_evidence'][0]['block']=='component'


def test_duplicate_consistent_parent_declarations_agree():
    r=text_audit(tables(('ATL',),'(ATL)','T'),[parent('ATL','DT'),parent('ATL','DT','component')])[0]
    assert r['canonical_status']=='MATCH'
    assert len(r['positions'][0]['parent_evidence'])==2


@pytest.mark.parametrize('parents',[
    [parent('ATL',None)], [parent('ATL','DA,DC')],
    [parent('ATL','DT'),parent('ATL','DC','component')],
    [parent('ATL','ANOTHER')],
])
def test_unknown_multiple_conflicting_or_nonstandard_parent_stays_unresolved(parents):
    r=text_audit(tables(('ATL','DA'),'(ATL)(DA)','TA'),parents)[0]
    assert r['literal_status']=='MATCH' and r['canonical_status']=='UNAVAILABLE'
    assert r['canonical_expected'] is None
    assert r['positions'][1]['canonical_options']==['A']


def test_explicit_no_parent_can_be_x_but_unknown_is_not_no_parent():
    t=tables(('ZZZ',),'(ZZZ)','X')
    assert text_audit(t,[parent('ZZZ',False)])[0]['canonical_status']=='MATCH'
    assert text_audit(t,[parent('ZZZ',None)])[0]['canonical_status']=='UNAVAILABLE'


def test_alternative_monomers_not_last_wins():
    t=tables(('DT',),'(DT)','T');t['_entity_poly_seq.'].append(dict(entity_id='1',num='1',mon_id='ATL'))
    r=text_audit(t,[parent('ATL','DT')])[0]
    assert r['positions'][0]['declared_components']==['ATL','DT']
    assert r['literal_status']==r['canonical_status']=='MATCH'
    assert r['has_alternative_monomers'] is True
    t['_entity_poly_seq.'][-1]['mon_id']='DA';r=text_audit(t)[0]
    assert r['literal_status']=='MATCH' and r['canonical_status']=='UNAVAILABLE'


@pytest.mark.parametrize('mutate',[
    lambda t:t['_entity_poly.'].append(deepcopy(t['_entity_poly.'][0])),
    lambda t:t['_entity_poly_seq.'].pop(1),
    lambda t:t['_entity_poly_seq.'].append(deepcopy(t['_entity_poly_seq.'][0])),
])
def test_invalid_declarations_block_text_approval(mutate):
    t=tables();mutate(t);r=text_audit(t)[0]
    assert r['literal_status']==r['canonical_status']=='UNAVAILABLE'


def test_unmodeled_sequence_position_not_dropped():
    # Sequence evidence has no coordinate filter: the fifth declared base stays.
    t=tables(('DA','DC','DG','DT','DA'),'(DA)(DC)(DG)(DT)(DA)','ACGTA')
    r=text_audit(t)[0];assert len(r['positions'])==5 and r['canonical_status']=='MATCH'


@pytest.mark.parametrize('literal',['(TOOLONGCODE)','(DA','(DA))','Z'])
def test_unsupported_or_malformed_literal_is_explicit(literal):
    r=text_audit(tables(literal=literal))[0]
    assert r['literal_status']=='UNAVAILABLE' and r['literal_reason']


def test_public_observer_binds_text_without_changing_existing_coverage(tmp_path):
    from nasolve.topostitch_cif_polymer import observe_relabel_cif_sequence_text
    packet,model,kwargs,owner=fixture(tmp_path)
    # fixture's genuine source binding and fake public Cedar owner stay shared.
    before={p:p.read_bytes() for p in [model,*packet.iterdir()] if p.is_file()}
    old=observe(packet,model,kwargs)
    r=observe_relabel_cif_sequence_text(packet,model,**kwargs)
    assert r['polymer_coverage_sha256']==old['report_sha256']
    assert r['original_model_sha256']==sha256(model.read_bytes()).hexdigest()
    assert r['coordinates_written'] is False and r['chemical_entities_assigned'] is False
    assert r['scientific_acceptance'] is False and r['runtime_authority'] is False
    assert r['sequence_text_status']=='PARTIAL'
    assert all(p.read_bytes()==data for p,data in before.items())
    assert observe(packet,model,kwargs)==old
    json.dumps(r,allow_nan=False)


def test_multi_parent_expansion_never_shifts_later_residue_comparison():
    # A one-position modified monomer can expand to several canonical letters.
    # Do not compare later DA against the second letter of that expansion.
    t=tables(('ZZZ','DA'),'(ZZZ)(DA)','ACA')
    r=text_audit(t,[parent('ZZZ','DA,DC')])[0]
    assert r['literal_status']=='MATCH'
    assert r['canonical_status']=='UNAVAILABLE' and r['canonical_expected'] is None
    assert r['positions'][1]['canonical_options']==['A']


@pytest.mark.parametrize('raw,expected',[("'.'",'UNAVAILABLE'),('"?"','UNAVAILABLE'),('.', 'MATCH'),('?', 'UNAVAILABLE')])
def test_quoted_null_lookalikes_remain_literals(raw,expected):
    import gemmi
    from nasolve.topostitch_cif_annotations import _rows
    block=gemmi.cif.read_string('data_test\n_chem_comp.id ZZZ\n_chem_comp.mon_nstd_parent_comp_id '+raw+'\n')[0]
    evidence=[dict(block='test',source_row=1,row=_rows(block,'_chem_comp.')[0])]
    r=text_audit(tables(('ZZZ',),'(ZZZ)','X'),evidence)[0]
    assert r['canonical_status']==expected


def test_sequence_text_refuses_source_change_after_coverage(tmp_path,monkeypatch):
    import nasolve.topostitch_cif_polymer as module
    packet,model,kwargs,owner=fixture(tmp_path)
    old=module.observe_relabel_cif_polymer
    def drift(*args,**kw):
        result=old(*args,**kw);model.write_bytes(model.read_bytes()+b'\n# changed\n');return result
    monkeypatch.setattr(module,'observe_relabel_cif_polymer',drift)
    with pytest.raises(ValueError,match='changed during sequence text'):
        module.observe_relabel_cif_sequence_text(packet,model,**kwargs)
