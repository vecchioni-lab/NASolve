"""Visible recut fragments retain source identity and only declared oligo mappings."""
from hashlib import sha256
import json
import shutil
from pathlib import Path

import pytest
from tests.test_topostitch_cif_polymer import fixture
from tests.test_topostitch_cif_source import edit
from tests.test_construct_registration import target
from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import inspect_pdb, literal_polymer_identity_inventory


def observe(root,model,kw,**extra):
    from nasolve.topostitch_cif_fragments import observe_relabel_cif_fragments
    return observe_relabel_cif_fragments(root,model,**kw,**extra)


def oligo_file(root,folder,*,missing=False,extra=False,different=False,lexical_order=False,target_path=None):
    a=inspect_pdb(root/'source.pdb',polymer_ligand_codes={'DA','DC','DG','DT'})
    codes=literal_polymer_identity_inventory(a)
    saved=json.loads((root/'preview.json').read_text())['observation']['registered_graph']
    coordinates={n['logical_site']:n['mapping']['coordinate_site'] for n in saved['nodes']}
    ordered=(list(codes) if lexical_order else
             [coordinates[site] for route in saved['declared_routes'] for site in route['sites']])
    sites=[(f'oligo:{i}',codes[s])for i,s in enumerate(ordered,1)]
    if different:sites[0]=(sites[0][0],'DA'if sites[0][1]!='DA'else'DG')
    if extra:sites.append(('oligo:extra','DA'))
    mapping={f'oligo:{i}':s for i,s in enumerate(ordered,1)if not missing or i>1}
    declared=target(*sites);declared['reference']={'id':'explicit-oligo-fixture','version':'1','content_sha256':'b'*64}
    if target_path is not None:target_path.write_text(json.dumps(declared))
    reg=build_construct_registration(a,declared,{'declared-copy':mapping},source='Explicit synthetic oligo assignment; not inferred')
    path=folder/'oligo.json';path.write_text(json.dumps(reg));return path


def binding(path):return dict(oligo_registration_path=path,expected_oligo_registration_sha256=sha256(path.read_bytes()).hexdigest())


def all_sites(r):return [s for f in r['fragments']for s in f['sites']]


def test_asu_registration_does_not_prove_full_oligo_identity(tmp_path):
    root,model,kw,owner=fixture(tmp_path);before={p:p.read_bytes()for p in [model,owner,*root.iterdir()]}
    r=observe(root,model,kw);sites=all_sites(r)
    assert len(sites)==r['registered_site_count']==12
    assert r['oligo_mapping_status']=='SOURCE_LINEAGE_ONLY'
    assert all(s['oligo_assignment'] is None for s in sites)
    assert all(s['registered_copy_id'] and s['registered_logical_site'] and s['original_atom_ids'] for s in sites)
    assert len({a for s in sites for a in s['original_atom_ids']})==84
    assert r['all_registered_nodes_projected_once'] and r['all_declared_backbone_edges_retained']
    assert not r['physical_nick_inferred'] and not r['assembly_transformed'] and not r['tls_transformed']
    assert not r['writer_authorized'] and not r['scientific_acceptance']
    assert all(p.read_bytes()==data for p,data in before.items())


def test_explicit_oligo_registration_composes_without_renaming_source(tmp_path):
    root,model,kw,_=fixture(tmp_path);path=oligo_file(root,tmp_path)
    r=observe(root,model,kw,**binding(path));sites=all_sites(r)
    assert r['oligo_mapping_status']=='DECLARED_REGISTRATION_ONLY'
    assert {s['declared_mapping']['copy_id']for s in sites}=={'declared-copy'}
    assert sorted(s['declared_mapping']['target_strand_position']for s in sites)==list(range(1,13))
    assert all(s['declared_mapping']['strand_id']=='oligo'for s in sites)
    assert any(s['original_label']['label_comp_id']=='LONG1'for s in sites)
    assert all(s['original_author_sites']for s in sites)
    assert not r['physical_copy_placement_validated']
    assert r['oligo_registration']['unmapped_logical_sites_by_copy']=={'declared-copy':[]}


def test_missing_target_sites_are_not_missing_coordinates(tmp_path):
    root,model,kw,_=fixture(tmp_path);path=oligo_file(root,tmp_path,extra=True)
    r=observe(root,model,kw,**binding(path))
    assert r['oligo_mapping_status']=='DECLARED_REGISTRATION_ONLY'
    assert r['oligo_registration']['unmapped_logical_sites_by_copy']=={'declared-copy':['oligo:extra']}
    assert not r['source_positions_without_fragment']
    assert r['oligo_registration']['copies'][0]['status']=='PARTIAL'


def test_partial_or_identity_mismatched_mapping_stays_review(tmp_path):
    root,model,kw,_=fixture(tmp_path);path=oligo_file(root,tmp_path,missing=True,different=True)
    r=observe(root,model,kw,**binding(path))
    assert r['oligo_mapping_status']=='DECLARED_MAPPING_REVIEW_REQUIRED'
    assert len(r['registered_nodes_without_declared_mapping'])==1
    assert len(all_sites(r))==12


def test_target_difference_is_retained_not_used_to_mutate(tmp_path):
    root,model,kw,_=fixture(tmp_path);path=oligo_file(root,tmp_path,different=True)
    r=observe(root,model,kw,**binding(path))
    assert r['oligo_mapping_status']=='DECLARED_MAPPING_REVIEW_REQUIRED'
    assert len(r['target_identity_conflicts'])==1
    assert not r['coordinates_written']


@pytest.mark.parametrize('problem',['missing_hash','missing_path','wrong_hash','wrong_model','wrong_code','duplicate_key'])
def test_bad_explicit_binding_refused(tmp_path,problem):
    root,model,kw,_=fixture(tmp_path);path=oligo_file(root,tmp_path);args=binding(path)
    if problem=='missing_hash':args.pop('expected_oligo_registration_sha256')
    elif problem=='missing_path':args.pop('oligo_registration_path')
    elif problem=='wrong_hash':args['expected_oligo_registration_sha256']='0'*64
    else:
        reg=json.loads(path.read_text())
        if problem=='wrong_model':reg['model']['sha256']='0'*64
        elif problem=='wrong_code':
            row=reg['copies'][0]['mappings'][0];row['coordinate_residue_code']=row['target_residue_code']='ZZZ'
        path.write_text(json.dumps(reg))
        if problem=='duplicate_key':path.write_text(path.read_text().replace('"schema_version": 1','"schema_version": 1, "schema_version": 1',1))
        args=binding(path)
    with pytest.raises((ValueError,RuntimeError)):
        observe(root,model,kw,**args)


def test_unmodeled_source_position_is_not_assigned_to_a_fragment(tmp_path):
    root,model,kw,_=fixture(tmp_path)
    def add(doc):
        for cat,number in [('_entity_poly_seq.','num'),('_pdbx_poly_seq_scheme.','seq_id')]:
            table=doc[0].get_mmcif_category(cat);index=0;eid=table['entity_id'][index]
            last=max(int(n)for e,n in zip(table['entity_id'],table[number])if e==eid)
            for key,values in table.items():values.append(str(last+1)if key==number else 'DG'if key=='mon_id'else values[index])
            doc[0].set_mmcif_category(cat,table)
    kw['expected_model_sha256']=edit(model,add)
    r=observe(root,model,kw)
    assert len(r['source_positions_without_fragment'])==1
    assert r['source_positions_without_fragment'][0]['coordinate_status']=='UNMODELED'
    assert len(all_sites(r))==12


def test_source_and_proposed_images_remain_attached_to_every_edge(tmp_path):
    root,model,kw,_=fixture(tmp_path);r=observe(root,model,kw)
    preview=json.loads((root/'preview.json').read_text())['observation']
    original={e['edge_id']:e for e in preview['registered_graph']['periodic_graph']['edges']if e['kind']=='covalent_backbone'}
    after={e['edge_id']:e for e in preview['graph_relabeling']['periodic_graph']['edges']if e['kind']=='covalent_backbone'}
    assert {e['edge_id']for e in r['backbone_edges']}==set(original)
    for row in r['backbone_edges']:
        assert row['original_target_operator_xyz']==original[row['edge_id']]['target_operator_xyz']
        assert row['representative_target_operator_xyz']==after[row['edge_id']]['target_operator_xyz']
        assert row['source_node_id']and row['target_node_id']
    assert all(s['representative_operator_xyz']for s in all_sites(r))


def test_relocation_preserves_observation_and_late_oligo_drift_refused(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old);path=oligo_file(root,old)
    original=observe(root,model,kw,**binding(path));relative=[p.relative_to(old)for p in (root,model,path,kw['cedar_source'])]
    new=tmp_path/'moved';shutil.move(old,new);root,model,path,cedar=[new/p for p in relative];kw['cedar_source']=cedar
    assert not old.exists();assert observe(root,model,kw,**binding(path))==original
    assert str(old)not in json.dumps(original)
    import nasolve.topostitch_cif_fragments as module
    before=module.observe_relabel_cif_polymer
    def drift(*args,**kwargs):
        result=before(*args,**kwargs);path.write_text(path.read_text()+'\n');return result
    monkeypatch.setattr(module,'observe_relabel_cif_polymer',drift)
    with pytest.raises(ValueError,match='changed'):
        observe(root,model,kw,**binding(path))


def test_coordinate_sort_order_is_not_declared_sequence_order(tmp_path):
    root,model,kw,_=fixture(tmp_path);path=oligo_file(root,tmp_path,lexical_order=True)
    r=observe(root,model,kw,**binding(path))
    assert r['oligo_mapping_status']=='DECLARED_MAPPING_REVIEW_REQUIRED'
    assert len(r['sequence_adjacency_review_edge_ids'])==2
    assert not r['physical_nick_inferred']


@pytest.mark.parametrize('reserialize',[False,True])
def test_reusing_asu_registration_is_not_an_oligo_declaration(tmp_path,reserialize):
    root,model,kw,_=fixture(tmp_path);path=tmp_path/'asu-again.json'
    data=(root/'registration.json').read_bytes()
    if reserialize:data=json.dumps(json.loads(data),sort_keys=True,indent=4).encode()
    path.write_bytes(data);r=observe(root,model,kw,**binding(path))
    assert r['oligo_mapping_status']=='SOURCE_TARGET_REUSED'
    assert all(s['oligo_assignment'] is None for s in all_sites(r))
    assert all(s['declared_mapping'] is not None for s in all_sites(r))


# W262 binds the existing logical target itself, not only a reference label.
def target_binding(path):
    return dict(oligo_target_path=path, expected_oligo_target_sha256=sha256(path.read_bytes()).hexdigest())


def test_target_document_rebuilds_registration_and_retains_unmapped_codes(tmp_path):
    root,model,kw,_=fixture(tmp_path);design=tmp_path/'target.json'
    path=oligo_file(root,tmp_path,extra=True,target_path=design)
    before=observe(root,model,kw,**binding(path))
    r=observe(root,model,kw,**binding(path),**target_binding(design))
    assert before['oligo_mapping_status']=='DECLARED_REGISTRATION_ONLY'
    assert r['oligo_mapping_status']=='TARGET_DOCUMENT_BOUND'
    assert r['explicit_target_document_verified']
    assert r['oligo_registration']['target_document_sha256']==sha256(design.read_bytes()).hexdigest()
    assert r['oligo_registration']['target_document_sites'][-1]=={'site':'oligo:extra','residue_code':'DA'}
    assert r['oligo_registration']['unmapped_logical_sites_by_copy']=={'declared-copy':['oligo:extra']}
    assert all(s['oligo_assignment']==s['declared_mapping'] for s in all_sites(r))
    assert not r['physical_copy_placement_validated'] and not r['physical_nick_inferred']
    assert not r['oligo_registration']['target_reference_content_loaded']
    assert not r['writer_authorized'] and not r['coordinates_written']
    assert r['polymer_coverage_sha256']==before['polymer_coverage_sha256']


@pytest.mark.parametrize('damage',['missing_hash','missing_path','wrong_hash','no_registration','mapped_code','reference','duplicate_key'])
def test_target_document_binding_rejects_inconsistent_evidence(tmp_path,damage):
    root,model,kw,_=fixture(tmp_path);design=tmp_path/'target.json'
    path=oligo_file(root,tmp_path,target_path=design);args=dict(**binding(path),**target_binding(design))
    if damage=='missing_hash':args.pop('expected_oligo_target_sha256')
    elif damage=='missing_path':args.pop('oligo_target_path')
    elif damage=='wrong_hash':args['expected_oligo_target_sha256']='0'*64
    elif damage=='no_registration':args=target_binding(design)
    else:
        data=json.loads(design.read_text())
        if damage=='mapped_code':data['sites'][0]['residue_code']='ZZZ'
        elif damage=='reference':data['reference']['content_sha256']='c'*64
        design.write_text(json.dumps(data))
        if damage=='duplicate_key':design.write_text(design.read_text().replace('"schema_version": 1','"schema_version": 1, "schema_version": 1',1))
        args.update(target_binding(design))
    with pytest.raises((ValueError,RuntimeError)):
        observe(root,model,kw,**args)


def test_bound_target_does_not_hide_missing_mapping_or_identity_conflict(tmp_path):
    root,model,kw,_=fixture(tmp_path);design=tmp_path/'target.json'
    path=oligo_file(root,tmp_path,missing=True,target_path=design)
    r=observe(root,model,kw,**binding(path),**target_binding(design))
    assert r['explicit_target_document_verified']
    assert r['oligo_mapping_status']=='DECLARED_MAPPING_REVIEW_REQUIRED'
    assert len(r['registered_nodes_without_declared_mapping'])==1
    path=oligo_file(root,tmp_path,different=True,target_path=design)
    r=observe(root,model,kw,**binding(path),**target_binding(design))
    assert r['explicit_target_document_verified'] and len(r['target_identity_conflicts'])==1
    assert r['oligo_registration']['target_document_status']=='LOADED_REGISTRATION_MATCH'
    assert r['oligo_registration']['target_reference_status']=='NOT_LOADED'
    assert r['oligo_mapping_status']=='DECLARED_MAPPING_REVIEW_REQUIRED'
    assert not r['coordinates_written']


def test_actual_asu_target_document_remains_neutral(tmp_path):
    root,model,kw,_=fixture(tmp_path);reg=json.loads((root/'registration.json').read_text())
    codes={m['logical_site']:m['target_residue_code'] for c in reg['copies']for m in c['mappings']}
    doc=target(*[(s,codes[s]) for s in reg['target']['sites']]);doc['reference']=reg['target']['reference']
    design=tmp_path/'asu-target.json';design.write_text(json.dumps(doc))
    r=observe(root,model,kw,**binding(root/'registration.json'),**target_binding(design))
    assert r['explicit_target_document_verified']
    assert r['oligo_mapping_status']=='SOURCE_TARGET_REUSED'
    assert all(s['oligo_assignment'] is None for s in all_sites(r))


def test_target_binding_relocation_and_late_change(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,model,kw,_=fixture(old);design=old/'target.json'
    path=oligo_file(root,old,target_path=design)
    original=observe(root,model,kw,**binding(path),**target_binding(design))
    rel=[p.relative_to(old)for p in (root,model,path,design,kw['cedar_source'])]
    new=tmp_path/'relocated';shutil.move(old,new);root,model,path,design,cedar=[new/p for p in rel];kw['cedar_source']=cedar
    assert not old.exists()
    assert observe(root,model,kw,**binding(path),**target_binding(design))==original
    import nasolve.topostitch_cif_fragments as module
    before=module.observe_relabel_cif_polymer
    def drift(*args,**kwargs):
        result=before(*args,**kwargs);design.write_text(design.read_text()+' ');return result
    monkeypatch.setattr(module,'observe_relabel_cif_polymer',drift)
    with pytest.raises(ValueError,match='changed'):
        observe(root,model,kw,**binding(path),**target_binding(design))
