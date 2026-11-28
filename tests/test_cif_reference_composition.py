"""Explicit source composition, preserving both authorities and no native targets."""
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from hashlib import sha256

import pytest
from Bio.PDB.MMCIF2Dict import MMCIF2Dict
from nasolve.ligand_profiles import _emit

A, B = '_chem_comp_atom.', '_chem_comp_bond.'


def inputs(tmp_path):
    template = tmp_path/'template.cif'
    template.write_bytes((Path(__file__).parent/'fixtures/chemical_reference_DT.cif').read_bytes())
    reference = tmp_path/'reference.cif'
    reference.write_bytes(files('nasolve').joinpath('data/chemical_references/DY.cif').read_bytes())
    return template, reference


def compose(template, reference, code='Q17'):
    from nasolve.cif_reference_composition import compose_dna_source
    return compose_dna_source(template, 'DT', reference, 'DY', component=code)


def test_compose_keeps_reference_base_and_template_backbone(tmp_path):
    from nasolve.cif_stereochemistry_audit import _values, _graph
    t, r = inputs(tmp_path); original = t.read_bytes(), r.read_bytes()
    payload, report = compose(t, r); out=tmp_path/'composed.cif'; out.write_bytes(payload)
    graph = _graph(_values(out,'Q17')); elements,bonds,charges,neighbors=graph
    assert len(elements)==38 and sum(e not in {'H','D'} for e in elements.values())==24
    assert {'P','OP1','OP2','OP3','HOP2','HOP3','N1T','N2T','C3T','N4T','C5T'}<=elements.keys()
    assert not {'O4','C7','H71','H72','H73'}&elements.keys()
    assert neighbors['OP2']=={'P','HOP2'} and neighbors['OP3']=={'P','HOP3'}
    assert bonds[('C4','N1T')]=='SINGLE'
    assert set(charges.values())=={0}
    assert MMCIF2Dict(str(out))['_chem_comp.formula']==['C11 H14 N5 O7 P']
    assert report['status']=='COMPOSED_SOURCE_REQUIRES_QUALIFICATION'
    assert report['model_editing']=='NOT_RUN' and report['native_qualification']=='NOT_RUN'
    assert report['source_pins']['backbone']['sha256']==sha256(original[0]).hexdigest()
    assert report['source_pins']['reference']['sha256']==sha256(original[1]).hexdigest()
    assert report['output_sha256']==sha256(payload).hexdigest()
    assert all(v['state']=='PRESERVED' for v in report['sugar_configuration'])
    assert original==(t.read_bytes(),r.read_bytes())
    assert not any(k.startswith(('_chem_comp_angle.','_chem_comp_tor.','_chem_comp_plane_atom.','_pdbx_chem_comp_descriptor.')) for k in MMCIF2Dict(str(out)))
    assert compose(t,r)==(payload,report)


@pytest.mark.parametrize('variant',['renamed_base','mirrored_both','reordered','deuterated_base','changed_template_protonation'])
def test_composition_uses_explicit_graphs_and_states(tmp_path,variant):
    t,r=inputs(tmp_path);tv,rv=MMCIF2Dict(str(t)),MMCIF2Dict(str(r))
    if variant=='renamed_base':
        mapping={n:'Z'+str(i) for i,n in enumerate(['N1','C2','O2','N3','C4','C5','C6','N1T','N2T','C3T','N4T','C5T','H1','H2','H3','H4'])}
        for k in list(rv):
            if k.startswith((A,B)) and k.split('.')[-1].startswith('atom_id'):rv[k]=[mapping.get(n,n) for n in rv[k]]
    if variant=='mirrored_both':
        tv['_chem_comp.type']=['L-DNA LINKING']
        for v in (tv,rv):
            v[A+'pdbx_stereo_config']=[{'R':'S','S':'R'}.get(s,s) for s in v[A+'pdbx_stereo_config']]
            for k in list(v):
                if k.startswith(A) and ('cartn_z' in k.lower()):v[k]=[str(-float(x)) for x in v[k]]
    if variant=='reordered':
        for v in (tv,rv):
            for k in v:
                if k.startswith((A,B)):v[k]=list(reversed(v[k]))
    if variant=='deuterated_base':rv[A+'type_symbol'][rv[A+'atom_id'].index('H3')]='D'
    if variant=='changed_template_protonation':
        from nasolve.cif_linked_preparation import _prune
        tv=_prune(tv,{'HOP2'},outgoing=False)
        tv[A+'charge'][tv[A+'atom_id'].index('OP2')]='-1';tv['_chem_comp.pdbx_formal_charge']=['-1']
    t.write_text(_emit(tv));r.write_text(_emit(rv));payload,report=compose(t,r,'X73')
    out=tmp_path/'out.cif';out.write_bytes(payload);v=MMCIF2Dict(str(out));ids=v[A+'atom_id']
    if variant=='renamed_base':assert 'N1T' not in ids and 'Z7' in ids
    if variant=='mirrored_both':assert v['_chem_comp.type']==['L-DNA LINKING']
    if variant=='deuterated_base':assert v[A+'type_symbol'][ids.index('H3')]=='D'
    if variant=='changed_template_protonation':
        assert 'HOP2' not in ids and v[A+'charge'][ids.index('OP2')]=='-1'
    assert report['component']=='X73'


@pytest.mark.parametrize('defect',['sugar_hand','mirrored_reference','missing_stereo','missing_charge','sugar_charge','sugar_branch',
    'reference_phosphate','wrong_reference_type','wrong_template_type','partial_coordinates','degenerate_frame',
    'base_stereo','bond_stereo','conflicting_aromatic','outside_collision','numerical_source','carbon_glycoside','wrong_OH','total_charge','sugar_isotope'])
def test_unqualified_compositions_refuse_without_writing(tmp_path,defect):
    t,r=inputs(tmp_path);tv,rv=MMCIF2Dict(str(t)),MMCIF2Dict(str(r));ids=rv[A+'atom_id']
    if defect=='sugar_hand':rv[A+'pdbx_stereo_config'][ids.index("C3'")]='R'
    if defect=='mirrored_reference':rv[A+'model_Cartn_z']=[str(-float(x)) for x in rv[A+'model_Cartn_z']]
    if defect=='missing_stereo':rv[A+'pdbx_stereo_config'][ids.index("C1'")]='?'
    if defect=='missing_charge':rv[A+'charge'][0]='?'
    if defect=='sugar_charge':rv[A+'charge'][ids.index("O5'")]='-1'
    if defect=='sugar_branch':rv[A+'type_symbol'][ids.index('H6')]='F'
    if defect=='reference_phosphate':rv=deepcopy(tv);rv['_chem_comp.type']=['non-polymer'];rv['_chem_comp.id']=['DY'];rv[A+'comp_id']=['DY']*len(rv[A+'atom_id']);rv[B+'comp_id']=['DY']*len(rv[B+'atom_id_1'])
    if defect=='wrong_reference_type':rv['_chem_comp.type']=['RNA LINKING']
    if defect=='wrong_template_type':tv['_chem_comp.type']=['RNA LINKING']
    if defect=='partial_coordinates':rv.pop(A+'model_Cartn_z')
    if defect=='degenerate_frame':
        for axis in 'xyz':rv[A+'model_Cartn_'+axis]=['0']*len(ids)
    if defect=='base_stereo':rv[A+'pdbx_stereo_config'][ids.index('C3T')]='R'
    if defect=='bond_stereo':rv[B+'pdbx_stereo_config']=['E']+['N']*(len(rv[B+'atom_id_1'])-1)
    if defect=='conflicting_aromatic':rv[B+'aromatic']=['N']*len(rv[B+'atom_id_1'])
    if defect=='outside_collision':
        for k in list(rv):
            if k.startswith((A,B)) and k.split('.')[-1].startswith('atom_id'):rv[k]=['P' if n=='C3T' else n for n in rv[k]]
    if defect=='numerical_source':rv[B+'value_dist']=['1.4']*len(rv[B+'atom_id_1'])
    if defect=='carbon_glycoside':rv[A+'type_symbol'][ids.index('N1')]='C'
    if defect=='total_charge':tv['_chem_comp.pdbx_formal_charge']=['1']
    if defect=='sugar_isotope':rv[A+'type_symbol'][ids.index('H6')]='D'
    if defect=='wrong_OH':rv[A+'type_symbol'][ids.index('H13')]='C'
    t.write_text(_emit(tv));r.write_text(_emit(rv));before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError):compose(t,r)
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_composed_source_enters_unchanged_five_ring_contract(tmp_path):
    from nasolve.cif_source_representation import generation_representation_contract
    from nasolve.cif_purine_representation import FIVE_RING_POLICY_ID
    t,r=inputs(tmp_path);payload,report=compose(t,r);p=tmp_path/'source.cif';p.write_bytes(payload)
    contract=generation_representation_contract(p,'Q17',FIVE_RING_POLICY_ID)
    assert len(contract['allowed_systems'])==1 and len(contract['allowed_systems'][0])==5
    assert report['bond_stereo_encoding']=='NO_E_Z_DECLARATIONS_PERMITTED; UNASSERTED_COLUMN_OMITTED'


def test_composed_source_reuses_connected_whole_atom_row_order(tmp_path):
    from nasolve.cif_stereochemistry_audit import _graph,_values
    t,r=inputs(tmp_path);payload,report=compose(t,r);p=tmp_path/'out.cif';p.write_bytes(payload)
    v=_values(p,'Q17');elements,_,_,neighbors=_graph(v);order=v[A+'atom_id'];seen=set();hydrogens=False
    for atom in order:
        if elements[atom] in {'H','D'}:hydrogens=True
        else:
            assert not hydrogens
            if seen:assert neighbors[atom]&seen
            seen.add(atom)
    assert report['atom_order']['output_order']==order
    assert report['atom_order']['policy_id']=='cif-connected-heavy-atom-order-v1'


def test_complete_retained_subgraphs_and_rigid_coordinates_survive(tmp_path):
    from math import dist
    from nasolve.cif_stereochemistry_audit import _values,_graph,_coordinates,_stereo
    t,r=inputs(tmp_path);payload,report=compose(t,r);out=tmp_path/'out.cif';out.write_bytes(payload)
    sources={role:(_values(p,code)) for role,p,code in [('backbone',t,'DT'),('reference',r,'DY')]}
    result=_values(out,'Q17');eg,bg,cg,ng=_graph(result);_,xyz=_coordinates(result,source=True)
    graphs={role:_graph(v) for role,v in sources.items()};coords={role:_coordinates(v,source=True)[1] for role,v in sources.items()}
    for atom,origin in report['atom_origins'].items():
        role=origin['role'];e,b,c,n=graphs[role]
        assert eg[atom]==e[atom] and cg[atom]==c[atom]
        assert _stereo(result)[atom]==_stereo(sources[role])[atom]
        if role=='backbone':assert dist(xyz[atom],coords[role][atom])<1e-11
        else:
            assert ng[atom]==n[atom]
    base=[n for n,origin in report['atom_origins'].items() if origin['role']=='reference']+["C1'"]
    assert max(abs(dist(xyz[a],xyz[b])-dist(coords['reference'][a],coords['reference'][b]))
               for i,a in enumerate(base) for b in base[i+1:])<1e-10
    for edge,order in bg.items():
        role='reference' if any(report['atom_origins'][n]['role']=='reference' for n in edge) else 'backbone'
        assert graphs[role][1][edge]==order


def test_composition_replays_after_original_paths_are_gone(tmp_path,monkeypatch):
    import subprocess
    original=tmp_path/'original';original.mkdir();t,r=inputs(original);first=compose(t,r)
    moved=tmp_path/'moved';original.rename(moved)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k: pytest.fail('Source composition must not execute external tools'))
    assert not original.exists()
    assert compose(moved/t.name,moved/r.name)==first
    assert '/Users/' not in str(first[1]) and str(original) not in str(first[1])
