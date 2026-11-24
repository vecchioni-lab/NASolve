"""Declared sequence positions survive a recut without inventing atoms or chains."""
from hashlib import sha256
import json
import shutil

import pytest
gemmi = pytest.importorskip('gemmi')
from tests.test_topostitch_cif_annotations import fixture as connection_fixture
from tests.test_topostitch_cif_source import edit


def fixture(tmp_path):
    root,model,kw,owner=connection_fixture(tmp_path)
    # A contract fake for loader/schema tests; actual-file qualification uses
    # the source-pinned Cedar implementation, not this synthetic observation.
    owner.write_text(owner.read_text()+'''\nfrom hashlib import sha256
from pathlib import Path
def inspect_deposition_links(model):
    return {'model': {'sha256':sha256(Path(model).read_bytes()).hexdigest(),
        'status':'REVIEW', 'sequence_tables_checked':['_entity_poly_seq.','_pdbx_poly_seq_scheme.'],
        'sequence_conflicts':[], 'unlabelled_polymer_atom_rows':0}}
''')
    kw['expected_deposition_owner_sha256']=sha256(owner.read_bytes()).hexdigest()
    kw.pop('expected_image_owner_sha256')
    def populate(doc):
        b=doc[0];atoms=b.get_mmcif_category('_atom_site.')
        old=sorted(set(zip(atoms['label_asym_id'],atoms['label_seq_id'])))
        numbering={}
        for chain in sorted({c for c,n in old}):
            for i,(_,n)in enumerate(sorted((x for x in old if x[0]==chain),key=lambda x:int(x[1])),1):
                numbering[chain,n]=str(i)
        atoms['label_seq_id']=[numbering[c,n]for c,n in zip(atoms['label_asym_id'],atoms['label_seq_id'])]
        b.set_mmcif_category('_atom_site.',atoms)
        chains=sorted(set(atoms['label_asym_id']))
        b.set_mmcif_category('_entity.',{'id':chains,'type':['polymer']*len(chains)})
        b.set_mmcif_category('_entity_poly.',{'entity_id':chains,'type':['polydeoxyribonucleotide']*len(chains),'nstd_linkage':['yes']*len(chains)})
        b.set_mmcif_category('_struct_asym.',{'id':chains,'entity_id':chains})
        sites=sorted(set(zip(atoms['label_asym_id'],atoms['label_seq_id'],atoms['label_comp_id'])))
        b.set_mmcif_category('_entity_poly_seq.',{'entity_id':[c for c,n,m in sites],'num':[n for c,n,m in sites],'mon_id':[m for c,n,m in sites],'hetero':['n']*len(sites)})
        b.set_mmcif_category('_pdbx_poly_seq_scheme.',{'asym_id':[c for c,n,m in sites],'entity_id':[c for c,n,m in sites],'seq_id':[n for c,n,m in sites],'mon_id':[m for c,n,m in sites],
            'auth_seq_num':['original-design-number']*len(sites)})
    kw['expected_model_sha256']=edit(model,populate)
    return root,model,kw,owner


def observe(root,model,kw):
    from nasolve.topostitch_cif_polymer import observe_relabel_cif_polymer
    return observe_relabel_cif_polymer(root,model,**kw)


def test_complete_original_polymer_sites_bind_to_declared_paths(tmp_path):
    root,model,kw,owner=fixture(tmp_path);before={p:p.read_bytes()for p in [model,owner,*root.iterdir()]}
    r=observe(root,model,kw)
    assert r['metadata_coverage_status']=='CONSISTENT_DECLARATIONS'
    assert r['original_atom_count']==r['polymer_atom_count']==84
    assert r['all_atoms_accounted_once'] and r['all_observed_polymer_atoms_registered']
    assert len(r['declared_positions'])==12 and len(r['observed_polymer_sites'])==12
    assert not r['unmodeled_positions'] and not r['unresolved_atoms'] and not r['issues']
    assert r['cedar_sequence_evidence']['source_inspection_status']=='REVIEW'
    assert any(s['original_components']==['LONG1']for s in r['observed_polymer_sites'])
    assert all(s['registered_node_ids'] and s['proposed_path_positions']for s in r['observed_polymer_sites'])
    assert all(row['nstd_linkage']=='yes'for row in r['original_tables']['_entity_poly.'])
    assert not r['coordinates_written'] and not r['runtime_authority'] and not r['author_numbering_semantics_validated']
    assert str(tmp_path)not in json.dumps(r)
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('category',['_entity.','_entity_poly.','_struct_asym.','_entity_poly_seq.','_pdbx_poly_seq_scheme.'])
def test_missing_table_stays_unavailable_not_empty_conflict_approval(tmp_path,category):
    root,model,kw,owner=fixture(tmp_path)
    kw['expected_model_sha256']=edit(model,lambda d:d[0].find_mmcif_category(category).erase())
    r=observe(root,model,kw)
    assert category in r['missing_tables'] and r['metadata_coverage_status']=='UNAVAILABLE'
    assert r['all_atoms_accounted_once'] and not r['source_semantics_approved']


@pytest.mark.parametrize('damage',['asym_entity','missing_entity','duplicate_entity','wrong_monomer','scheme_entity','duplicate_sequence','bad_number'])
def test_inconsistent_metadata_is_retained_for_review(tmp_path,damage):
    root,model,kw,owner=fixture(tmp_path)
    def mutate(d):
        category={'asym_entity':'_struct_asym.','missing_entity':'_entity.','duplicate_entity':'_entity.',
            'wrong_monomer':'_entity_poly_seq.','scheme_entity':'_pdbx_poly_seq_scheme.',
            'duplicate_sequence':'_entity_poly_seq.','bad_number':'_entity_poly_seq.'}[damage]
        t=d[0].get_mmcif_category(category)
        if damage in ('duplicate_entity','duplicate_sequence'):
            for v in t.values():v.append(v[0])
        elif damage=='missing_entity':
            for v in t.values():del v[0]
        elif damage=='wrong_monomer':t['mon_id'][0]='WRONG'
        elif damage=='bad_number':t['num'][0]='not-an-integer'
        else:t['entity_id'][0]='NO_SUCH_ENTITY'
        d[0].set_mmcif_category(category,t)
    kw['expected_model_sha256']=edit(model,mutate)
    if damage=='bad_number':
        with pytest.raises(ValueError):observe(root,model,kw)
        return
    r=observe(root,model,kw)
    assert r['metadata_coverage_status']=='REVIEW_REQUIRED' and r['issues']
    assert r['all_atoms_accounted_once']


def test_declared_unmodeled_positions_and_alternative_monomers_remain(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    def add(d):
        b=d[0];seq=b.get_mmcif_category('_entity_poly_seq.');scheme=b.get_mmcif_category('_pdbx_poly_seq_scheme.')
        chain=seq['entity_id'][0];last=max(int(n)for c,n in zip(seq['entity_id'],seq['num'])if c==chain)
        for table,row in ((seq,dict(entity_id=chain,num=str(last+1),mon_id='DG',hetero='n')),
            (scheme,dict(asym_id=chain,entity_id=chain,seq_id=str(last+1),mon_id='DG',auth_seq_num=None))):
            for key,values in table.items():values.append(row.get(key))
        # A second declared monomer at the same position is allowed microheterogeneity.
        alt={k:v[0]for k,v in seq.items()};alt['mon_id']='DG';alt['hetero']='y'
        seq['hetero'][0]='y'
        for k,v in seq.items():v.append(alt[k])
        alt={k:v[0]for k,v in scheme.items()};alt['mon_id']='DG'
        for k,v in scheme.items():v.append(alt[k])
        b.set_mmcif_category('_entity_poly_seq.',seq);b.set_mmcif_category('_pdbx_poly_seq_scheme.',scheme)
    kw['expected_model_sha256']=edit(model,add);r=observe(root,model,kw)
    assert r['metadata_coverage_status']=='CONSISTENT_DECLARATIONS'
    assert len(r['unmodeled_positions'])==1
    assert r['unmodeled_positions'][0]['declared_components']==['DG']
    assert not r['unmodeled_positions'][0]['original_atom_ids']
    assert any(len(p['declared_components'])==2 for p in r['declared_positions'])
    assert r['original_atom_count']==84


def test_scheme_omission_for_unmodeled_site_is_still_a_coverage_gap(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    def add(d):
        t=d[0].get_mmcif_category('_entity_poly_seq.')
        for k,v in t.items():v.append({'entity_id':t['entity_id'][0],'num':'99','mon_id':'DG','hetero':'n'}[k])
        d[0].set_mmcif_category('_entity_poly_seq.',t)
    kw['expected_model_sha256']=edit(model,add);r=observe(root,model,kw)
    assert r['unmodeled_positions'] and r['metadata_coverage_status']=='REVIEW_REQUIRED'


def test_cedar_sequence_evidence_requires_bound_source_and_available_result(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    text=owner.read_text().replace("'sequence_conflicts':[]", "'sequence_conflicts':[['1','M',1,'LONG1','_entity_poly_seq.']]")
    owner.write_text(text);kw['expected_deposition_owner_sha256']=sha256(owner.read_bytes()).hexdigest()
    assert observe(root,model,kw)['metadata_coverage_status']=='REVIEW_REQUIRED'
    owner.write_text(text.replace("sha256(Path(model).read_bytes()).hexdigest()", "'0'*64"));kw['expected_deposition_owner_sha256']=sha256(owner.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='Cedar.*source'):observe(root,model,kw)


def test_polymer_report_relocates_and_detects_late_source_drift(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,owner=fixture(old);expected=observe(root,model,kw)
    moved=tmp_path/'moved';shutil.move(old,moved);assert not old.exists()
    root=moved/root.relative_to(old);model=moved/model.relative_to(old);kw['cedar_source']=moved/kw['cedar_source'].relative_to(old)
    assert observe(root,model,kw)==expected
    import nasolve.topostitch_cif_polymer as module
    fn=module._coverage
    def drift(*args,**kwargs):
        result=fn(*args,**kwargs);model.write_bytes(model.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'_coverage',drift)
    with pytest.raises(ValueError,match='changed|bound original source'):observe(root,model,kw)


def test_atoms_with_conflicting_entity_are_not_called_unmodeled(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    def mutate(d):
        t=d[0].get_mmcif_category('_atom_site.')
        key=t['label_asym_id'][0],t['label_seq_id'][0]
        other=next(e for e in t['label_entity_id']if e!=t['label_entity_id'][0])
        for i in range(len(t['id'])):
            if (t['label_asym_id'][i],t['label_seq_id'][i])==key:t['label_entity_id'][i]=other
        d[0].set_mmcif_category('_atom_site.',t)
    kw['expected_model_sha256']=edit(model,mutate);r=observe(root,model,kw)
    assert not r['unmodeled_positions']
    assert any(p['coordinate_status']=='UNRESOLVED' and p['original_atom_ids']for p in r['declared_positions'])
    assert not r['all_observed_polymer_atoms_registered']


def test_one_entity_instantiated_twice_keeps_two_unmodeled_sites(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    def mutate(d):
        b=d[0];atoms=b.get_mmcif_category('_atom_site.')
        atoms['label_entity_id']=['N'if c=='R'else c for c in atoms['label_entity_id']]
        b.set_mmcif_category('_atom_site.',atoms)
        for category,key in (('_entity.','id'),('_entity_poly.','entity_id'),('_entity_poly_seq.','entity_id')):
            t=b.get_mmcif_category(category);indices=[i for i,v in enumerate(t[key])if v!='R']
            b.set_mmcif_category(category,{k:[v[i]for i in indices]for k,v in t.items()})
        for category in ('_struct_asym.','_pdbx_poly_seq_scheme.'):
            t=b.get_mmcif_category(category);t['entity_id']=['N'if e=='R'else e for e in t['entity_id']]
            b.set_mmcif_category(category,t)
        t=b.get_mmcif_category('_entity_poly_seq.')
        for k,v in t.items():v.append(dict(entity_id='N',num='3',mon_id='DG',hetero='n')[k])
        b.set_mmcif_category('_entity_poly_seq.',t)
        t=b.get_mmcif_category('_pdbx_poly_seq_scheme.')
        for chain in ('N','R'):
            for k,v in t.items():v.append(dict(asym_id=chain,entity_id='N',seq_id='3',mon_id='DG',auth_seq_num=None)[k])
        b.set_mmcif_category('_pdbx_poly_seq_scheme.',t)
    kw['expected_model_sha256']=edit(model,mutate);r=observe(root,model,kw)
    assert r['metadata_coverage_status']=='CONSISTENT_DECLARATIONS'
    assert {(p['label_asym_id'],p['label_entity_id'],p['label_seq_id'])for p in r['unmodeled_positions']}=={('N','N',3),('R','N',3)}


@pytest.mark.parametrize('unknown_position',[False,True])
def test_unregistered_polymer_coverage_never_disappears(tmp_path,unknown_position):
    from tests.test_topostitch_cif_paths import partial_labelled
    root,model,kw,owner=fixture(tmp_path)
    other=tmp_path/'partial';other.mkdir();partial,_,binding=partial_labelled(other)
    kw['expected_receipt_sha256']=binding['expected_receipt_sha256']
    if unknown_position:
        def mutate(d):
            t=d[0].get_mmcif_category('_atom_site.')
            for i,c in enumerate(t['label_asym_id']):
                if c=='R':t['label_seq_id'][i]=None
            d[0].set_mmcif_category('_atom_site.',t)
        kw['expected_model_sha256']=edit(model,mutate)
    r=observe(partial,model,kw)
    assert not r['all_observed_polymer_atoms_registered'] and r['all_atoms_accounted_once']
    if unknown_position:
        assert r['metadata_coverage_status']=='REVIEW_REQUIRED' and len(r['unresolved_atoms'])==14
        assert not r['unmodeled_positions']
        assert [p['coordinate_status']for p in r['declared_positions']if p['label_asym_id']=='R']==['UNRESOLVED','UNRESOLVED']
    else:
        assert r['metadata_coverage_status']=='CONSISTENT_DECLARATIONS'
        assert len(r['unregistered_polymer_atom_ids'])==14


def test_gapped_sequence_table_is_not_complete_sequence_metadata(tmp_path):
    root,model,kw,owner=fixture(tmp_path)
    def mutate(d):
        for category,key in (('_entity_poly_seq.','num'),('_pdbx_poly_seq_scheme.','seq_id')):
            t=d[0].get_mmcif_category(category)
            ownerkey='entity_id' if key=='num' else 'asym_id'
            row=dict((k,v[0])for k,v in t.items());row[key]='100';row['mon_id']='DG'
            for k,v in t.items():v.append(row[k])
            d[0].set_mmcif_category(category,t)
    kw['expected_model_sha256']=edit(model,mutate);r=observe(root,model,kw)
    assert r['metadata_coverage_status']=='REVIEW_REQUIRED'
    assert any('Noncontiguous' in i['reason']for i in r['issues'])


@pytest.mark.parametrize('entity,position,expected_status',[('W',None,'UNMODELED'),('M','1','UNMODELED'),('M','5','UNRESOLVED')])
def test_unlocated_atom_uncertainty_respects_known_entity_and_position(tmp_path,entity,position,expected_status):
    from nasolve.topostitch_cif_polymer import _coverage, CATEGORIES
    from nasolve.topostitch_cif_annotations import _rows
    root,model,kw,owner=fixture(tmp_path);b=gemmi.cif.read_file(str(model))[0]
    tables={cat:_rows(b,cat)for cat in CATEGORIES};atoms=_rows(b,'_atom_site.')
    tables['_entity.'].append(dict(id='W',type='water'))
    tables['_entity_poly_seq.'].append(dict(entity_id='M',num='5',mon_id='DG',hetero='n'))
    tables['_pdbx_poly_seq_scheme.'].append(dict(asym_id='M',entity_id='M',seq_id='5',mon_id='DG'))
    atoms.append(dict(id='unlocated',label_asym_id=None,label_entity_id=entity,label_seq_id=position,label_comp_id='HOH' if entity=='W' else 'DG'))
    r=_coverage(tables,atoms,[])
    p=next(p for p in r['declared_positions']if p['label_asym_id']=='M'and p['label_seq_id']==5)
    assert p['coordinate_status']==expected_status
    assert r['unresolved_atoms'] and r['issues'] and r['all_atoms_accounted_once']
