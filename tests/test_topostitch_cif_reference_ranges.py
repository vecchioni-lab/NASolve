"""Sequence reference membership survives ASU splits without inventing DB offsets."""
from hashlib import sha256
import json
import shutil

import pytest
from tests.test_topostitch_cif_polymer import fixture as polymer_fixture
from tests.test_topostitch_cif_source import edit


def fixture(tmp_path):
    root,model,kw,owner=polymer_fixture(tmp_path)
    def add(doc):
        block=doc[0]
        atoms=block.get_mmcif_category('_atom_site.')
        atoms['pdbx_PDB_ins_code']=[False]*len(atoms['id'])
        block.set_mmcif_category('_atom_site.',atoms)
        author={(c,n):(a,r,i) for c,n,a,r,i in zip(atoms['label_asym_id'],atoms['label_seq_id'],
            atoms['auth_asym_id'],atoms['auth_seq_id'],atoms['pdbx_PDB_ins_code'])}
        scheme=block.get_mmcif_category('_pdbx_poly_seq_scheme.')
        scheme['auth_seq_num']=[author[c,n][1]for c,n in zip(scheme['asym_id'],scheme['seq_id'])]
        scheme['pdb_seq_num']=scheme['auth_seq_num'][:]
        scheme['pdb_strand_id']=[author[c,n][0]for c,n in zip(scheme['asym_id'],scheme['seq_id'])]
        scheme['pdb_ins_code']=[author[c,n][2]for c,n in zip(scheme['asym_id'],scheme['seq_id'])]
        block.set_mmcif_category('_pdbx_poly_seq_scheme.',scheme)
        block.set_mmcif_category('_struct_ref.',{'id':['ref-A'],'entity_id':['M'],'db_name':['EXTERNAL'],'db_code':['example']})
        row=dict(align_id='alignment-A',ref_id='ref-A',pdbx_strand_id='M',seq_align_beg='1',seq_align_end='4',
            pdbx_auth_seq_align_beg=author['M','1'][1],pdbx_auth_seq_align_end=author['M','4'][1],
            pdbx_seq_align_beg_ins_code=None,pdbx_seq_align_end_ins_code=None,
            db_align_beg='101',db_align_end='104',details='External endpoint range only; alignment correspondence not supplied')
        block.set_mmcif_category('_struct_ref_seq.',{k:[v]for k,v in row.items()})
        block.set_mmcif_category('_struct_ref_seq_dif.',dict(align_id=['alignment-A'],seq_num=['2'],mon_id=['DG'],details=['retain discrepancy']))
        block.set_mmcif_category('_pdbx_struct_ref_seq_depositor_info.',dict(ref_id=['ref-A'],entity_id=['M'],seq_align_begin=[None],seq_align_end=[None]))
    kw['expected_model_sha256']=edit(model,add)
    return root,model,kw,owner


def observe(root,model,kw):
    from nasolve.topostitch_cif_fragments import observe_relabel_cif_reference_ranges
    return observe_relabel_cif_reference_ranges(root,model,**kw)


def change(model,kw,category,fn):
    def mutate(doc):
        table=doc[0].get_mmcif_category(category);fn(table);doc[0].set_mmcif_category(category,table)
    kw['expected_model_sha256']=edit(model,mutate)


def test_reference_range_projects_across_real_preview_split(tmp_path):
    root,model,kw,owner=fixture(tmp_path);before={p:p.read_bytes()for p in [model,owner,*root.iterdir()]}
    r=observe(root,model,kw);row=r['alignments'][0]
    assert row['status']=='SOURCE_RANGE_PROJECTED'
    assert row['source_entity_id']=='M' and row['source_asym_id']=='M'
    assert [s['source_seq_id']for s in row['positions']]==[1,2,3,4]
    assert len(row['segments'])>1
    assert all(s['original_align_id']=='alignment-A' and s['original_ref_id']=='ref-A'for s in row['segments'])
    assert sum(len(s['positions'])for s in row['segments'])==4
    assert row['author_range_status']=='CONSISTENT_UNINSERTED_FORWARD_RANGE'
    assert row['raw_fields']['db_align_beg']=='101'
    assert row['discrepancy_rows'][0]['details']=='retain discrepancy'
    assert r['unprojected_reference_tables']['_pdbx_struct_ref_seq_depositor_info.'][0]['seq_align_begin'] is None
    assert all(s['output_db_align_beg'] is None and s['output_db_align_end'] is None for s in row['segments'])
    assert not r['database_positions_inferred'] and not r['writer_authorized']
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('problem',['reverse_range','bad_endpoint','missing_ref','duplicate_ref','duplicate_alignment','ambiguous_strand','wrong_author','insertion_endpoint'])
def test_ambiguous_reference_ranges_stay_explicit(tmp_path,problem):
    root,model,kw,_=fixture(tmp_path)
    category='_struct_ref_seq.'
    def mutate(t):
        if problem=='reverse_range':t['seq_align_beg'][0]='4';t['seq_align_end'][0]='1'
        elif problem=='bad_endpoint':t['seq_align_end'][0]='999'
        elif problem=='missing_ref':t['ref_id'][0]='absent'
        elif problem=='ambiguous_strand':t['pdbx_strand_id'][0]='M,Q'
        elif problem=='wrong_author':t['pdbx_auth_seq_align_end'][0]='777'
        elif problem=='insertion_endpoint':t['pdbx_seq_align_beg_ins_code'][0]='A'
        else:
            for v in t.values():v.append(v[0])
    if problem=='duplicate_ref':category='_struct_ref.'
    change(model,kw,category,mutate)
    if problem=='missing_ref':
        # Existing Gemmi/source owner refuses this dangling FK before projection.
        with pytest.raises(ValueError,match='serialized coordinate model'):
            observe(root,model,kw)
        return
    r=observe(root,model,kw)
    assert all(row['status']=='REVIEW_REQUIRED' and row['issues']for row in r['alignments'])
    assert r['original_tables']['_struct_ref_seq_dif.'][0]['align_id']=='alignment-A'
    if problem=='duplicate_alignment':assert len(r['unresolved_discrepancy_rows'])==1
    assert not r['output_alignment_rows_written']


def test_reverse_scheme_numbering_is_not_sorted_into_an_alignment(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def reverse(t):
        selected=[i for i,c in enumerate(t['asym_id'])if c=='M']
        for field in ('auth_seq_num','pdb_seq_num'):
            vals=[t[field][i]for i in selected][::-1]
            for i,v in zip(selected,vals):t[field][i]=v
    change(model,kw,'_pdbx_poly_seq_scheme.',reverse)
    row=observe(root,model,kw)['alignments'][0]
    assert row['status']=='REVIEW_REQUIRED'
    assert any('author' in issue.lower()for issue in row['issues'])
    assert [p['source_seq_id']for p in row['positions']]==[1,2,3,4]


def test_unmodeled_range_position_is_retained_without_fragment_assignment(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def add(doc):
        b=doc[0]
        for cat,number in [('_entity_poly_seq.','num'),('_pdbx_poly_seq_scheme.','seq_id')]:
            t=b.get_mmcif_category(cat)
            for k,v in t.items():v.append('5'if k==number else 'DG'if k=='mon_id'else '105'if k in ('auth_seq_num','pdb_seq_num')else v[0])
            b.set_mmcif_category(cat,t)
        t=b.get_mmcif_category('_struct_ref_seq.');t['seq_align_end'][0]='5';t['pdbx_auth_seq_align_end'][0]='105';b.set_mmcif_category('_struct_ref_seq.',t)
    kw['expected_model_sha256']=edit(model,add)
    row=observe(root,model,kw)['alignments'][0]
    assert row['status']=='REVIEW_REQUIRED'
    assert row['positions'][-1]['coordinate_status']=='UNMODELED'
    assert row['positions'][-1]['fragment_position'] is None
    assert sum(len(s['positions'])for s in row['segments'])==4


def test_missing_alignment_is_unavailable_and_orphan_discrepancy_survives(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    kw['expected_model_sha256']=edit(model,lambda d:d[0].find_mmcif_category('_struct_ref_seq.').erase())
    r=observe(root,model,kw)
    assert r['status']=='UNAVAILABLE' and not r['alignments']
    assert len(r['unresolved_discrepancy_rows'])==1
    assert r['original_tables']['_struct_ref.'][0]['id']=='ref-A'


def test_reference_range_relocation_and_source_drift(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old)
    report=observe(root,model,kw)
    rel=[p.relative_to(old)for p in (root,model,kw['cedar_source'])]
    new=tmp_path/'moved';shutil.move(old,new);root,model,cedar=[new/p for p in rel];kw['cedar_source']=cedar
    assert not old.exists() and observe(root,model,kw)==report
    assert str(old)not in json.dumps(report)
    import nasolve.topostitch_cif_fragments as module
    before=module.observe_relabel_cif_fragments
    def drift(*args,**kwargs):
        result=before(*args,**kwargs);model.write_bytes(model.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'observe_relabel_cif_fragments',drift)
    with pytest.raises(ValueError,match='changed'):
        observe(root,model,kw)


def test_unknown_insertion_is_not_assumed_absent(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def unknown(doc):
        for cat,field in [('_atom_site.','pdbx_PDB_ins_code'),('_pdbx_poly_seq_scheme.','pdb_ins_code')]:
            t=doc[0].get_mmcif_category(cat);t[field]=[None]*len(t[field]);doc[0].set_mmcif_category(cat,t)
    kw['expected_model_sha256']=edit(model,unknown)
    row=observe(root,model,kw)['alignments'][0]
    assert row['status']=='REVIEW_REQUIRED'
    assert any('insertion' in issue for issue in row['issues'])
    assert len(row['positions'])==4
    assert all(p['coordinate_status']=='OBSERVED' and p['fragment_position'] is not None for p in row['positions'])


def test_explicit_scheme_resolves_unreported_atom_insertion_without_rewriting(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    change(model,kw,'_atom_site.',lambda t:t.update(pdbx_PDB_ins_code=[None]*len(t['id'])))
    row=observe(root,model,kw)['alignments'][0]
    assert row['status']=='SOURCE_RANGE_PROJECTED'
    assert all(p['original_author_sites'][0]['pdbx_PDB_ins_code'] is None for p in row['positions'])
    assert all(p['original_author_scheme_rows'][0]['pdb_ins_code'] is False for p in row['positions'])
