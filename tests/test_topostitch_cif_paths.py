"""A recut projects declared paths; it cannot infer chemistry or drop context."""
from hashlib import sha256
import json
import shutil

import pytest
gemmi = pytest.importorskip('gemmi')
from tests.test_topostitch_cif_source import fixture, edit


def labelled(tmp_path):
    root,path,kw=fixture(tmp_path)
    def label(doc):
        t=doc[0].get_mmcif_category('_atom_site.')
        t['label_asym_id']=list(t['auth_asym_id'])
        t['label_seq_id']=list(t['auth_seq_id'])
        t['label_entity_id']=list(t['auth_asym_id'])
        doc[0].set_mmcif_category('_atom_site.',t)
    kw['expected_model_sha256']=edit(path,label)
    return root,path,kw


def observe(root,path,kw):
    from nasolve.topostitch_cif_source import observe_relabel_cif_paths
    return observe_relabel_cif_paths(root,path,**kw)


def test_original_sites_and_every_declared_edge_survive_path_projection(tmp_path):
    root,path,kw=labelled(tmp_path);before={p:p.read_bytes()for p in [path,*root.iterdir()]}
    report=observe(root,path,kw)
    packet=json.loads((root/'preview.json').read_bytes())['observation']
    edges=packet['graph_relabeling']['periodic_graph']['edges']
    covalent={e['edge_id']for e in edges if e['kind']=='covalent_backbone'}
    encoded=[i for p in report['paths']for i in p['ordinary_edge_ids']]
    encoded += [e['edge_id']for e in report['boundary_edges']]
    assert len(encoded)==len(set(encoded)) and set(encoded)==covalent
    assert len(report['paths'])==6 and len(report['boundary_edges'])==2
    assert report['registered_atom_count']==report['original_atom_count']==84
    assert report['unregistered_original_atom_ids']==[]
    assert report['declared_routes']==packet['registered_graph']['declared_routes']
    sites={r['logical_site']:r for r in report['registered_original_sites']}
    assert sites['A:1']['declared_do_not_connect'] and sites['A:2']['declared_protected']
    assert any(r['original_label']['label_comp_id']=='LONG1'for r in sites.values())
    assert sorted(i for r in sites.values()for i in r['original_atom_ids'])==sorted(gemmi.cif.read_file(str(path))[0].get_mmcif_category('_atom_site.')['id'])
    assert not report['source_sequence_semantics_validated'] and not report['annotation_coverage_validated']
    assert not report['runtime_authority'] and not report['coordinate_or_chemical_changes']
    assert str(tmp_path)not in json.dumps(report)
    assert all(p.read_bytes()==b for p,b in before.items())


@pytest.mark.parametrize('defect',['missing_label','split_site','aliased_site'])
def test_ambiguous_or_incomplete_original_labels_refuse(tmp_path,defect):
    root,path,kw=labelled(tmp_path)
    def mutate(doc):
        t=doc[0].get_mmcif_category('_atom_site.')
        if defect=='missing_label':t['label_seq_id'][0]=None
        elif defect=='split_site':t['label_seq_id'][0]='999'
        else:
            first=t['auth_seq_id'][0]
            second=next((t['auth_asym_id'][i],t['auth_seq_id'][i])for i,c in enumerate(t['label_comp_id'])if c==t['label_comp_id'][0]and t['auth_seq_id'][i]!=first)
            for i,v in enumerate(t['auth_seq_id']):
                if (t['auth_asym_id'][i],v)==second:
                    for field in ('label_asym_id','label_seq_id','label_entity_id','label_comp_id'):
                        t[field][i]=t[field][0]
        doc[0].set_mmcif_category('_atom_site.',t)
    kw['expected_model_sha256']=edit(path,mutate)
    with pytest.raises(ValueError,match='original CIF site'):
        observe(root,path,kw)


def partial_labelled(tmp_path):
    from nasolve.topostitch_graph import build_registered_periodic_graph
    from nasolve.topostitch_recut_bundle import build_relabel_preview
    root,path,kw=labelled(tmp_path)
    d=json.loads((root/'discovery.json').read_text())
    d['strands']=[s for s in d['strands']if s['strand_id']!='D']
    d['duplex_pairs']=[pair for pair in d['duplex_pairs']if not any(s.startswith('D:')for s in pair)]
    from nasolve.construct_registration import build_construct_registration
    from nasolve.model_assessment import inspect_pdb
    from tests.test_construct_registration import target
    old=json.loads((root/'registration.json').read_text())
    rows=[r for r in old['copies'][0]['mappings']if not r['logical_site'].startswith('D:')]
    registration=build_construct_registration(
        inspect_pdb(root/'source.pdb',polymer_ligand_codes={'DA','DC','DG','DT'}),
        target(*[(r['logical_site'],r['target_residue_code'])for r in rows]),
        {'copy_1':{r['logical_site']:r['coordinate_site']for r in rows}},source='explicit partial scope')
    reg=tmp_path/'partial-registration.json';reg.write_text(json.dumps(registration))
    d['registration_sha256']=sha256(reg.read_bytes()).hexdigest()
    discovery=tmp_path/'partial-discovery.json';discovery.write_text(json.dumps(d))
    graph=build_registered_periodic_graph(root/'source.pdb',discovery,reg)
    request=json.loads((root/'proposal.json').read_text())
    request.update(registered_graph_sha256=graph['report_sha256'],node_images=[])
    proposal=tmp_path/'partial-proposal.json';proposal.write_text(json.dumps(request))
    partial=tmp_path/'partial-preview'
    build_relabel_preview(root/'source.pdb',discovery,registration_path=reg,proposal_path=proposal,output_directory=partial)
    kw['expected_receipt_sha256']=sha256((partial/'preview.json').read_bytes()).hexdigest()
    return partial,path,kw


def test_unregistered_context_is_retained_and_not_named_solvent(tmp_path):
    root,path,kw=partial_labelled(tmp_path)
    report=observe(root,path,kw)
    assert report['original_atom_count']==84 and report['registered_atom_count']==70
    assert len(report['unregistered_original_atom_ids'])==14
    ids=[i for r in report['registered_original_sites']for i in r['original_atom_ids']]+report['unregistered_original_atom_ids']
    assert len(ids)==len(set(ids))==84


def edge(i,a,b,op='x,y,z',kind='covalent_backbone'):
    return dict(edge_id=i,source=a,target=b,target_operator_xyz=op,kind=kind)


@pytest.mark.parametrize('edges',[
    [edge(1,1,2),edge(2,1,3)],
    [edge(1,1,3),edge(2,2,3)],
    [edge(1,1,2),edge(2,2,1)],
])
def test_branches_competing_partners_and_uncut_cycles_are_not_linearized(edges):
    from nasolve.topostitch_cif_source import _declared_paths
    with pytest.raises(ValueError,match='Branched|cycle'):
        _declared_paths([1,2,3],edges)


def test_nicks_isolated_nodes_and_periodic_cycles_stay_distinct():
    from nasolve.topostitch_cif_source import _declared_paths
    edges=[edge(1,1,2),edge(2,2,1,'x+1,y,z'),edge(3,3,4),edge(4,2,3,kind='base_pairing')]
    paths,seams=_declared_paths([5,4,3,2,1],edges)
    assert [p['node_ids']for p in paths]==[[1,2],[3,4],[5]]
    assert [p['ordinary_edge_ids']for p in paths]==[[1],[3],[]]
    assert seams==[edges[1]]


def test_path_binding_relocates_and_detects_late_original_drift(tmp_path,monkeypatch):
    old=tmp_path/'old';old.mkdir();root,path,kw=labelled(old)
    expected=observe(root,path,kw)
    moved=tmp_path/'new';shutil.move(old,moved);assert not old.exists()
    root=moved/root.relative_to(old);path=moved/path.relative_to(old)
    assert observe(root,path,kw)==expected
    import nasolve.topostitch_cif_source as module
    original=module._declared_paths
    def drift(*args):
        result=original(*args);path.write_bytes(path.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'_declared_paths',drift)
    with pytest.raises(ValueError,match='changed during path'):
        observe(root,path,kw)


def test_different_components_cannot_alias_one_original_sequence_position(tmp_path):
    root,path,kw=labelled(tmp_path)
    def mutate(doc):
        t=doc[0].get_mmcif_category('_atom_site.')
        j=next(i for i,c in enumerate(t['label_comp_id'])if c!=t['label_comp_id'][0])
        key=t['auth_asym_id'][j],t['auth_seq_id'][j]
        for i in range(len(t['id'])):
            if (t['auth_asym_id'][i],t['auth_seq_id'][i])==key:
                for field in ('label_asym_id','label_seq_id','label_entity_id'):
                    t[field][i]=t[field][0]
        doc[0].set_mmcif_category('_atom_site.',t)
    kw['expected_model_sha256']=edit(path,mutate)
    with pytest.raises(ValueError,match='original CIF site'):
        observe(root,path,kw)


def test_missing_entity_on_unregistered_atom_cannot_hide_site_collision(tmp_path):
    root,path,kw=partial_labelled(tmp_path)
    def mutate(doc):
        t=doc[0].get_mmcif_category('_atom_site.')
        j=next(i for i,ch in enumerate(t['auth_asym_id'])if ch=='R')
        t['label_asym_id'][j]=t['label_asym_id'][0]
        t['label_seq_id'][j]=t['label_seq_id'][0]
        t['label_entity_id'][j]=None
        doc[0].set_mmcif_category('_atom_site.',t)
    kw['expected_model_sha256']=edit(path,mutate)
    with pytest.raises(ValueError,match='original CIF site'):
        observe(root,path,kw)
