"""Generic native DNA/context validation with explicit synthetic evidence."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest


@pytest.mark.parametrize('seconds',[0,61,True,1.5])
def test_native_context_budget_is_checked_before_parent_or_output(tmp_path,seconds):
    from nasolve.cif_mixed_context import audit_mixed_context
    output=tmp_path/'absent'
    with pytest.raises(ValueError):audit_mixed_context(tmp_path/'missing',None,output,timeout_seconds=seconds)
    assert not output.exists()


def context_fixture(tmp_path,codes=('Q17',),*,group_bad=True):
    """Complete declared DNA graphs with two contexts and one unaffected code."""
    from tests.test_cif_postmr_construction import dictionary
    from nasolve.cif_linked_preparation import component_values,_render
    inputs=tmp_path/'inputs';inputs.mkdir()
    sources={};numerical={};rows=[];lines=[];sites={};edges=[]
    for number,code in enumerate((*codes,'V29')):
        source=inputs/(code+'_source.cif');dictionary(source,code,op3=True)
        values=component_values(source,code)
        values['_chem_comp.group']=['DNA']
        atom_ids=values['_chem_comp_atom.atom_id']
        for name,neighbor in [('HOP2','OP2'),('HOP3','OP3'),('ODDH',"O3'")]:
            atom_ids.append(name);values['_chem_comp_atom.comp_id'].append(code);values['_chem_comp_atom.type_symbol'].append('H')
            values['_chem_comp_bond.atom_id_1'].append(neighbor);values['_chem_comp_bond.atom_id_2'].append(name)
            values['_chem_comp_bond.value_order'].append('SING')
        values['_chem_comp_atom.charge']=['0']*len(atom_ids)
        source.write_text(_render(values,code));sources[code]=source
        generated=deepcopy(values)
        generated['_chem_comp.group']=['non-polymer' if code in codes and group_bad else 'DNA']
        generated['_chem_comp.type']=['ORIGINAL_EFFECTIVE_TYPE']
        generated['_chem_comp.number_atoms_all']=[str(len(atom_ids))]
        generated['_chem_comp.number_atoms_nh']=[str(sum(e!='H' for e in values['_chem_comp_atom.type_symbol']))]
        generated['_chem_comp_atom.type_energy']=['CUSTOM_O3' if n=="O3'" else e for n,e in zip(atom_ids,values['_chem_comp_atom.type_symbol'])]
        generated['_chem_comp_atom.charge'][atom_ids.index('OP2')]='-1'
        bonds=len(generated['_chem_comp_bond.atom_id_1'])
        generated['_chem_comp_bond.comp_id']=[code]*bonds
        generated['_chem_comp_bond.type']=['single']*bonds
        generated['_chem_comp_bond.value_dist']=['1.5']*bonds
        generated['_chem_comp_bond.value_dist_esd']=['0.02']*bonds
        provider=inputs/(code+'_numerical.cif');provider.write_text(_render(generated,code));numerical[code]=provider
        chain=chr(ord('A')+number)
        selected_sites=[(1,False),(2,True)] if code in codes else [(1,False)]
        for resid,incoming in selected_sites:
            site=f'{chain}:{resid}';sites[site]=code
            if incoming:edges.append([f'{chain}:1',site])
            for name,element in zip(atom_ids,values['_chem_comp_atom.type_symbol']):
                if element=='H' or incoming and name=='OP3':continue
                serial=len(lines)+1
                lines.append(f'HETATM{serial:5d} {name:>4} {code:>3} {chain}{resid:4d}    {float(serial):8.3f}{1.:8.3f}{2.:8.3f}  1.00 20.00          {element:>2}\n')
            rows.append({'site':site,'resname':code,'metadata':{'group':generated['_chem_comp.group'][0],
                'classification':{'status':'RECORDED','value':'DNA'},'atom_ids':list(atom_ids)},
                'missing_non_hydrogen_atoms':{'status':'RECORDED','atom_ids':['OP3'] if incoming else []},
                'missing_hydrogen_atoms':{'status':'RECORDED','atom_ids':['HOP2','HOP3','ODDH']},
                'unexpected_atoms':{'status':'RECORDED','atom_ids':[]},
                'chem_mod_ids':{'status':'RECORDED','ids':[]}})
    model=inputs/'model.pdb';model.write_text(''.join(lines)+'END\n')
    plan={'target_site_components':sites,'stack_edges':edges,'all_pairs':[]}
    atoms=[{'i_seq':i,'atom_id':line[12:16].strip(),'element':line[76:78].strip(),
        'xyz':[float(line[j:j+8]) for j in (30,38,46)],
        'label':':'.join([line[21],line[22:26].strip(),line[17:20].strip(),line[12:16].strip()]),
        'identity':{'model_id':'','chain_id':line[21],'resseq':line[22:26].strip(),'icode':'','altloc':'',
            'resname':line[17:20].strip()}} for i,line in enumerate(lines)]
    native={'status':'REVIEW','inventory_detail':'linked','atoms':atoms,'atom_count':len(atoms),
        'monomer_mappings':{'rows':rows}}
    return model,plan,sources,list(numerical.values()),deepcopy(native),native,numerical


@pytest.mark.parametrize('codes',[('Q17',),('X11','Y22')])
def test_context_selection_is_generic_and_uses_every_site_of_selected_codes(tmp_path,codes):
    from nasolve.cif_mixed_context import _select_context
    model,plan,sources,dictionaries,before,after,_=context_fixture(tmp_path,codes)
    selected=_select_context(model,plan,sources,dictionaries,before,after)
    assert selected['components']==list(codes)
    assert set(selected['contexts'])==set(codes)
    for number,code in enumerate(codes):
        chain=chr(ord('A')+number)
        contexts={v['site']:v for v in selected['contexts'][code]}
        assert set(contexts)=={f'{chain}:1',f'{chain}:2'}
        assert contexts[f'{chain}:1']['five_prime_state']=='phosphate'
        assert contexts[f'{chain}:2']['incoming_site']==f'{chain}:1'
        assert selected['site_reasons'][f'{chain}:1']=={'group':True,'missing_op3':False}
        assert selected['site_reasons'][f'{chain}:2']=={'group':True,'missing_op3':True}
        assert selected['source_eligibility'][code]['heavy_name_elements_bound']
        assert selected['source_eligibility'][code]['source_graph']['component']==code
    assert 'V29' not in selected['components']


def test_missing_op3_selects_context_even_when_group_already_dna(tmp_path):
    from nasolve.cif_mixed_context import _select_context
    model,plan,sources,dictionaries,before,after,_=context_fixture(tmp_path,group_bad=False)
    selected=_select_context(model,plan,sources,dictionaries,before,after)
    assert selected['components']==['Q17']
    assert selected['site_reasons']['A:2']=={'group':False,'missing_op3':True}


def test_preparation_preserves_terminal_op3_and_every_surviving_effective_parameter(tmp_path):
    from nasolve.cif_mixed_context import _select_context,_prepare_component
    from nasolve.cif_linked_preparation import component_values,atom_rows
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path)
    selection=_select_context(model,plan,sources,dictionaries,before,after)
    source,provider=sources['Q17'],numerical['Q17'];original=source.read_bytes(),provider.read_bytes(),model.read_bytes()
    out=tmp_path/'prepared'
    receipt=_prepare_component(source,provider,model,selection['contexts']['Q17'],out,code='Q17',normalize_group=True)
    base=component_values(out/receipt['outputs']['dictionary']['path'],'Q17')
    initial=component_values(provider,'Q17');expected=deepcopy(initial);expected['_chem_comp.group']=['DNA']
    assert base==expected
    assert base['_chem_comp.type']==['ORIGINAL_EFFECTIVE_TYPE']
    assert atom_rows(base)["O3'"]['type_energy']=='CUSTOM_O3'
    assert atom_rows(base)['OP2']['charge']=='-1'
    by_site={r['site']:r for r in receipt['sites']}
    assert by_site['A:1']['deleted_atoms']==[] and by_site['A:1']['modification_id'] is None
    assert by_site['A:2']['deleted_atoms']==['HOP3','OP3']
    assert 'HOP2' in by_site['A:2']['expected_atoms'] and 'ODDH' in by_site['A:2']['expected_atoms']
    assert by_site['A:2']['expected_energy_types']["O3'"]=='CUSTOM_O3'
    assert by_site['A:2']['expected_formal_charges']['OP2']=='-1'
    assert (source.read_bytes(),provider.read_bytes(),model.read_bytes())==original


def test_internal_op3_preparation_keeps_an_already_dna_header_exact(tmp_path):
    from nasolve.cif_mixed_context import _select_context,_prepare_component
    from nasolve.cif_linked_preparation import component_values
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path,group_bad=False)
    selection=_select_context(model,plan,sources,dictionaries,before,after)
    out=tmp_path/'prepared'
    receipt=_prepare_component(sources['Q17'],numerical['Q17'],model,selection['contexts']['Q17'],out,
        code='Q17',normalize_group=False)
    assert component_values(out/receipt['outputs']['dictionary']['path'],'Q17')==component_values(numerical['Q17'],'Q17')


def test_context_preserves_effective_bond_order_difference_without_rewriting_source_chemistry(tmp_path):
    from nasolve.cif_mixed_context import _select_context,_prepare_component
    from nasolve.cif_linked_preparation import component_values,_render
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path)
    provider=numerical['Q17'];values=component_values(provider,'Q17')
    pairs=list(zip(values['_chem_comp_bond.atom_id_1'],values['_chem_comp_bond.atom_id_2']))
    index=next(i for i,pair in enumerate(pairs) if set(pair)=={'NX','C2'})
    values['_chem_comp_bond.type'][index]='double';values['_chem_comp_bond.value_order'][index]='DOUB'
    provider.write_text(_render(values,'Q17'))
    selection=_select_context(model,plan,sources,dictionaries,before,after)
    out=tmp_path/'prepared';receipt=_prepare_component(sources['Q17'],provider,model,selection['contexts']['Q17'],
        out,code='Q17',normalize_group=True)
    prepared=component_values(out/receipt['outputs']['dictionary']['path'],'Q17')
    assert prepared['_chem_comp_bond.type']==values['_chem_comp_bond.type']
    assert prepared['_chem_comp_bond.value_order']==values['_chem_comp_bond.value_order']
    assert component_values(sources['Q17'],'Q17')['_chem_comp_bond.value_order'][index]=='SING'


def test_effective_extra_heavy_adjacency_is_not_a_header_or_op3_context_change(tmp_path):
    from nasolve.cif_mixed_context import _select_context
    from nasolve.cif_linked_preparation import component_values,_render
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path)
    provider=numerical['Q17'];values=component_values(provider,'Q17')
    additions={'comp_id':'Q17','atom_id_1':'QZ','atom_id_2':"C2'",'value_order':'SING',
        'type':'single','value_dist':'1.5','value_dist_esd':'0.02'}
    for field,value in additions.items():values['_chem_comp_bond.'+field].append(value)
    provider.write_text(_render(values,'Q17'))
    with pytest.raises(ValueError,match='heavy adjacency'):_select_context(model,plan,sources,dictionaries,before,after)


@pytest.mark.parametrize('defect',['classification','classification_absent','native_disagreement','missing_other',
    'unexpected','branch','source_bridge','source_rna','heavy_element','zero_bond','duplicate_provider','missing_plan_site'])
def test_selection_refuses_unproved_native_or_source_context(tmp_path,defect):
    from nasolve.cif_mixed_context import _select_context
    from nasolve.cif_linked_preparation import component_values,_render
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path)
    for native in [before,after]:
        row=native['monomer_mappings']['rows'][1]
        if defect=='classification':row['metadata']['classification']['value']='RNA'
        elif defect=='classification_absent':row['metadata']['classification']={'status':'NOT_RECORDED'}
        elif defect=='missing_other':row['missing_non_hydrogen_atoms']['atom_ids']=['OP3',"O4'"]
        elif defect=='unexpected':row['unexpected_atoms']['atom_ids']=['EXTRA']
    if defect=='native_disagreement':after['monomer_mappings']['rows'][1]['metadata']['group']='DNA'
    elif defect=='branch':plan['stack_edges'].append(['B:1','A:2'])
    elif defect=='missing_plan_site':del plan['target_site_components']['A:2']
    elif defect in {'source_bridge','source_rna'}:
        source=sources['Q17'];values=component_values(source,'Q17')
        if defect=='source_rna':values['_chem_comp.type']=['RNA LINKING']
        else:
            values['_chem_comp_bond.atom_id_1'].append('QZ');values['_chem_comp_bond.atom_id_2'].append("C2'")
            values['_chem_comp_bond.value_order'].append('SING')
        source.write_text(_render(values,'Q17'))
    elif defect in {'heavy_element','zero_bond'}:
        provider=numerical['Q17'];values=component_values(provider,'Q17')
        if defect=='heavy_element':values['_chem_comp_atom.type_symbol'][values['_chem_comp_atom.atom_id'].index('NX')]='C'
        else:values['_chem_comp_bond.value_dist'][0]='0'
        provider.write_text(_render(values,'Q17'))
    elif defect=='duplicate_provider':dictionaries.append(numerical['Q17'])
    with pytest.raises(ValueError):_select_context(model,plan,sources,dictionaries,before,after)


def test_op3_deletion_cannot_remove_an_oxygen_with_an_unrelated_heavy_neighbor(tmp_path):
    from nasolve.cif_mixed_context import _select_context,_prepare_component
    from nasolve.cif_linked_preparation import component_values,_render
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path)
    selection=_select_context(model,plan,sources,dictionaries,before,after)
    provider=numerical['Q17'];values=component_values(provider,'Q17')
    additions={'comp_id':'Q17','atom_id_1':'OP3','atom_id_2':'NX','value_order':'SING',
        'type':'single','value_dist':'1.5','value_dist_esd':'0.02'}
    for field,value in additions.items():values['_chem_comp_bond.'+field].append(value)
    provider.write_text(_render(values,'Q17'))
    with pytest.raises(ValueError):
        _prepare_component(sources['Q17'],provider,model,selection['contexts']['Q17'],tmp_path/'prepared',
            code='Q17',normalize_group=True)


def anchored_parent(tmp_path,monkeypatch,*,single_op3=False):
    """Mock only previously verified parent captures; real preparation stays live."""
    from nasolve.cif_mixed_linked_recovery import _ref,_resolve
    root=tmp_path/'linked_parent';root.mkdir()
    model,plan,sources,dictionaries,before,after,_=context_fixture(root)
    if single_op3:
        from nasolve.cif_linked_preparation import component_values,_prune,_render
        provider=dictionaries[0];values=component_values(provider,'Q17')
        provider.write_text(_render(_prune(values,{'HOP3'},outgoing=False),'Q17'))
    active=root/'inputs/active.phil';active.write_text('refinement {\n pdb_interpretation.secondary_structure {\n enabled = False\n }\n}\n')
    disabled=root/'inputs/disabled.phil';disabled.write_bytes(active.read_bytes())
    plan_path=root/'inputs/plan.json';plan_path.write_text(json.dumps(plan))
    parent={'status':'REVIEW','inputs':{'model':_ref(model,root),'active_policy':_ref(active,root),
        'disabled_policy':_ref(disabled,root),'plan':_ref(plan_path,root),
        'sources':{c:_ref(p,root) for c,p in sources.items()}},
        'bundle':{'effective_dictionaries':[_ref(p,root) for p in dictionaries],
            'native_dictionaries':[_ref(p,root) for p in dictionaries],
            'preparations':{},'site_projections':{},'context_phils':[],
            'preserved_source_findings':{'Q17':{'status':'REJECTED','note':'Inherited source/effective charge difference remains open.'}}},
        'explicit_fake_saved_captures':[{'native_validation':before},{'native_validation':after}]}
    (root/'mixed_linked_recovery.json').write_text(json.dumps(parent))
    def parent_inputs(path):
        path=Path(path);p=json.loads((path/'mixed_linked_recovery.json').read_bytes());refs=p['inputs']
        return (p,_resolve(path,refs['model']),_resolve(path,refs['active_policy']),_resolve(path,refs['disabled_policy']),
            json.loads(_resolve(path,refs['plan']).read_bytes()),{c:_resolve(path,r) for c,r in refs['sources'].items()},
            [_resolve(path,r) for r in p['bundle']['effective_dictionaries']],p['explicit_fake_saved_captures'])
    monkeypatch.setattr('nasolve.cif_mixed_context._parent_inputs',parent_inputs)
    return root,parent


def test_anchored_inspection_relocates_with_parent_and_preserves_source_findings(tmp_path,monkeypatch):
    from nasolve.cif_mixed_context import audit_mixed_context,read_mixed_context,PARENT_ANCHOR
    parent_root,parent=anchored_parent(tmp_path,monkeypatch)
    original={p:p.read_bytes() for p in parent_root.rglob('*') if p.is_file()}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('inspect-only started a process'))
    out=tmp_path/'context';report=audit_mixed_context(parent_root,None,out)
    assert report['status']=='PREPARED_ONLY' and report['targets']==['Q17'] and report['new_native_calls']==0
    assert report['inputs']['linked_parent_report']['anchor']==PARENT_ANCHOR
    assert report['bundle']['preserved_source_findings']==parent['bundle']['preserved_source_findings']
    assert report['source_state_repair']=='NOT_PERFORMED' and not report['automatic_adoption']
    assert all(p.read_bytes()==data for p,data in original.items())
    moved_parent=tmp_path/'relocated_parent';parent_root.rename(moved_parent)
    moved=tmp_path/'relocated_context';out.rename(moved)
    assert read_mixed_context(moved,linked_parent_directory=moved_parent)==report


@pytest.mark.parametrize('defect',['targets','count','decision','adoption','source_state','projection','projection_component',
    'parent_report','status','qualification','extra'])
def test_anchored_reader_rejects_forged_scope_selection_and_unbound_evidence(tmp_path,monkeypatch,defect):
    from nasolve.cif_mixed_context import audit_mixed_context,read_mixed_context,REPORT
    parent_root,_=anchored_parent(tmp_path,monkeypatch);out=tmp_path/'context'
    report=audit_mixed_context(parent_root,None,out)
    if defect=='targets':report['targets']=[]
    elif defect=='count':report['new_native_calls']=2
    elif defect=='decision':report['coordinate_decision']['native_usable']=True
    elif defect=='adoption':report['automatic_adoption']=True
    elif defect=='source_state':report['source_state_repair']='PERFORMED'
    elif defect=='projection_component':report['bundle']['site_projections']['A:2']['component']='V29'
    elif defect=='projection':
        from nasolve.cif_linked_preparation import component_values,_render
        from nasolve.cif_mixed_context import _ref
        ref=report['bundle']['site_projections']['A:2']['dictionary'];path=out/ref['path']
        values=component_values(path,'Q17');values['_chem_comp_bond.value_dist'][0]='1.7'
        path.write_text(_render(values,'Q17'))
        updated=_ref(path,out);report['bundle']['site_projections']['A:2']['dictionary']=updated
        report['outputs']=[updated if v['path']==ref['path'] else v for v in report['outputs']]
    elif defect=='parent_report':
        p=parent_root/'mixed_linked_recovery.json';p.write_bytes(p.read_bytes()+b'\n')
    elif defect=='status':report['status']='MIXED_CONTEXT_MECHANICS_PASS'
    elif defect=='qualification':
        q=out/'forged_qualification.json';q.write_text(json.dumps({'mechanics_checks_pass':True}))
        from nasolve.cif_mixed_context import _ref
        report['qualification']={'artifact':_ref(q,out)};report['outputs'].append(_ref(q,out))
    else:(out/'unbound.txt').write_text('EXTRA')
    (out/REPORT).write_text(json.dumps(report))
    with pytest.raises(ValueError):read_mixed_context(out,linked_parent_directory=parent_root)


@pytest.mark.parametrize('defect',['unchanged','reindex_padding','proxy','gradient','target',
    'coordinate','occupancy','element','term_cancellation','energy_count'])
def test_saved_parent_mechanical_equivalence_checks_exact_proxies_and_named_gradients(tmp_path,defect):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_mixed_context import _mechanical_equivalence
    before,after,_,_,_=case(tmp_path)
    from math import sqrt
    for native in [before,after]:
        native['installed_api_sources']=[{'module':'EXPLICIT_FAKE','sha256':'a'*64}]
        for atom in native['atoms']:
            atom['atom_name_field']=f'{atom["atom_id"]:>4}';atom['occupancy']=1.0
        for snapshot in native['energy_inventory']['snapshots']:
            snapshot['gradient']=[float(i)+.125 for i in range(3*native['atom_count'])]
            snapshot['gradient_norm']=sqrt(sum(v*v for v in snapshot['gradient']))
            snapshot['terms']={'bond_residual_sum':4.0,'angle_residual_sum':3.0}
            snapshot['proxy_counts']={'n_bond_proxies':len(native['geometry']['proxy_details']['bond_simple']),
                'n_angle_proxies':len(native['geometry']['proxy_details']['angle'])}
    if defect=='reindex_padding':
        pairs=[(a['i_seq'],a) for a in reversed(after['atoms'])];mapping={old:i for i,(old,a) in enumerate(pairs)}
        after['atoms']=[a for old,a in pairs]
        for i,(old,atom) in enumerate(pairs):
            atom['i_seq']=i;atom['element']=' '+atom['element']+' '
            atom['identity']={k:' '+v+' ' for k,v in atom['identity'].items()}
            atom['atom_name_field']=f'{atom["atom_id"]:<4}';atom['label']='padded '+atom['label']+' '
        by_index={a['i_seq']:a for a in after['atoms']}
        rows={id(row):row for data in after['geometry']['proxy_details'].values() for row in data}
        rows.update({id(row):row for key in ['simple_bonds','asu_bonds'] for row in after['geometry'][key]})
        for row in rows.values():
            row['i_seqs']=[mapping[i] for i in row['i_seqs']];row['atoms']=[by_index[i]['label'] for i in row['i_seqs']]
            if 'j_seqs' in row:
                row['j_seqs']=[mapping[i] for i in row['j_seqs']];row['j_atoms']=[by_index[i]['label'] for i in row['j_seqs']]
        after['geometry']['sites_cart_exact']=[a['xyz'] for a in after['atoms']]
        for snapshot in after['energy_inventory']['snapshots']:
            old_gradient=snapshot['gradient'];snapshot['gradient']=[v for old,a in pairs for v in old_gradient[3*old:3*old+3]]
    if defect=='proxy':after['geometry']['proxy_details']['bond_simple'][0]['weight']*=2
    elif defect=='gradient':
        from math import sqrt
        for snapshot in after['energy_inventory']['snapshots']:
            snapshot['gradient'][0]+=.1;snapshot['gradient_norm']=sqrt(sum(v*v for v in snapshot['gradient']))
    elif defect=='target':
        for snapshot in after['energy_inventory']['snapshots']:snapshot['target']+=1
    elif defect=='coordinate':after['atoms'][0]['xyz'][0]+=.01
    elif defect=='occupancy':after['atoms'][0]['occupancy']=.5
    elif defect=='element':after['atoms'][0]['element']='N'
    elif defect=='term_cancellation':
        for snapshot in after['energy_inventory']['snapshots']:
            snapshot['terms']['bond_residual_sum']+=1;snapshot['terms']['angle_residual_sum']-=1
    elif defect=='energy_count':
        for snapshot in after['energy_inventory']['snapshots']:snapshot['proxy_counts']['n_bond_proxies']+=1
    result=_mechanical_equivalence(before,after)
    assert result['mechanics_unchanged'] is (defect in {'unchanged','reindex_padding'})
    if defect=='proxy':assert not result['checks']['unchanged-native-proxies:bond_simple']
    elif defect in {'gradient','target'}:assert not result['checks']['same_full_targets_and_named_gradients']
    elif defect in {'coordinate','occupancy','element'}:assert not result['checks']['exact_named_native_atoms']
    elif defect=='term_cancellation':assert not result['checks']['same_energy_terms']
    elif defect=='energy_count':assert not result['checks']['same_energy_proxy_counts']


def test_mechanical_equivalence_refuses_an_unbound_literal_atom_name(tmp_path):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_mixed_context import _mechanical_equivalence
    before,after,_,_,_=case(tmp_path)
    for native in [before,after]:
        native['installed_api_sources']=[{'module':'EXPLICIT_FAKE','sha256':'a'*64}]
        for atom in native['atoms']:atom.update(atom_name_field=f'{atom["atom_id"]:>4}',occupancy=1.0)
    after['atoms'][0]['atom_name_field']='DIFF'
    with pytest.raises(ValueError,match='structured native atom'):_mechanical_equivalence(before,after)


def modification_values(names):
    values={'data_':'mod_NASCtest'}
    for field,data in {'mod_id':['NASCtest']*len(names),'function':['delete']*len(names),'atom_id':list(names),
        'new_atom_id':['.']*len(names),'new_type_symbol':['.']*len(names),
        'new_type_energy':['.']*len(names),'new_partial_charge':['.']*len(names)}.items():
        values['_chem_mod_atom.'+field]=data
    return values


@pytest.mark.parametrize('names',[['OP3'],['O\'P "3'],['OP3','HOP3']])
def test_c87_atom_modification_grammar_keeps_one_or_many_rows_in_an_explicit_loop(tmp_path,names):
    from nasolve.cif_mixed_context import _render_atom_modification
    from nasolve.ligand_profiles import _blocks
    values=modification_values(names);text=_render_atom_modification(values)
    path=tmp_path/'modification.cif';path.write_text(text)
    assert '\nloop_\n_chem_mod_atom.mod_id\n' in text
    assert _blocks(path)[0].values==values


def single_op3_fixture(tmp_path):
    from nasolve.cif_mixed_context import _select_context
    from nasolve.cif_linked_preparation import component_values,_prune,_render
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path)
    provider=numerical['Q17'];values=component_values(provider,'Q17')
    provider.write_text(_render(_prune(values,{'HOP3'},outgoing=False),'Q17'))
    selected=_select_context(model,plan,sources,dictionaries,before,after)
    return model,sources['Q17'],provider,selected['contexts']['Q17']


def test_c87_single_op3_preparation_uses_a_native_modification_loop(tmp_path):
    from nasolve.cif_mixed_context import _prepare_component
    from nasolve.ligand_profiles import _blocks
    model,source,provider,contexts=single_op3_fixture(tmp_path)
    out=tmp_path/'prepared';receipt=_prepare_component(source,provider,model,contexts,out,code='Q17',normalize_group=True)
    path=out/receipt['outputs']['modifications']['path'];text=path.read_text();blocks=_blocks(path)
    assert '\nloop_\n_chem_mod_atom.mod_id\n' in text
    assert len(blocks)==1 and blocks[0].values['_chem_mod_atom.atom_id']==['OP3']
    assert blocks[0].values['data_']=='mod_'+next(v['modification_id'] for v in receipt['sites'] if v['modification_id'])


def test_c87_explicit_legacy_policy_preserves_the_old_scalar_bytes(tmp_path):
    from nasolve.cif_mixed_context import _prepare_component,LEGACY_POLICY_ID,POLICY_ID
    from nasolve.ligand_profiles import _blocks,_emit
    model,source,provider,contexts=single_op3_fixture(tmp_path)
    legacy=tmp_path/'legacy';modern=tmp_path/'modern'
    a=_prepare_component(source,provider,model,contexts,legacy,code='Q17',normalize_group=True,policy_id=LEGACY_POLICY_ID)
    b=_prepare_component(source,provider,model,contexts,modern,code='Q17',normalize_group=True,policy_id=POLICY_ID)
    old=legacy/a['outputs']['modifications']['path'];new=modern/b['outputs']['modifications']['path']
    assert a['policy_id']==LEGACY_POLICY_ID and b['policy_id']==POLICY_ID
    assert old.read_text()==_emit(_blocks(old)[0].values)
    assert '\nloop_\n_chem_mod_atom.mod_id\n' not in old.read_text()
    assert '\nloop_\n_chem_mod_atom.mod_id\n' in new.read_text()
    assert _blocks(old)[0].values==_blocks(new)[0].values
    for key in ['dictionary','parameters']:
        assert (legacy/a['outputs'][key]['path']).read_bytes()==(modern/b['outputs'][key]['path']).read_bytes()


def test_c87_new_audit_defaults_to_loop_policy_and_reader_keeps_legacy_dispatch(tmp_path,monkeypatch):
    from nasolve.cif_mixed_context import (audit_mixed_context,read_mixed_context,_prepare_bundle,
        _ref,REPORT,POLICY_ID,LEGACY_POLICY_ID)
    parent_root,_=anchored_parent(tmp_path,monkeypatch,single_op3=True)
    from nasolve.cif_mixed_context import _parent_inputs
    out=tmp_path/'context';report=audit_mixed_context(parent_root,None,out)
    assert report['policy_id']==POLICY_ID and POLICY_ID!=LEGACY_POLICY_ID
    assert all(v['receipt']['policy_id']==POLICY_ID for v in report['bundle']['preparations'].values())
    preparation=report['bundle']['preparations']['Q17']
    mod=out/preparation['directory']['path']/preparation['receipt']['outputs']['modifications']['path']
    assert '\nloop_\n_chem_mod_atom.mod_id\n' in mod.read_text()
    # Changing only a stored version is insufficient: the version chooses an
    # immutable grammar and preparation receipt, both replayed by the reader.
    changed=deepcopy(report);changed['policy_id']=LEGACY_POLICY_ID
    (out/REPORT).write_text(json.dumps(changed))
    with pytest.raises(ValueError):read_mixed_context(out,linked_parent_directory=parent_root)
    (out/REPORT).write_text(json.dumps(report))
    # Build the historical output with its explicit policy and keep all parent
    # file references identical. This exercises actual v1 bundle generation,
    # rather than bypassing the maintained preparation during reader replay.
    parent,model,active,disabled,plan,sources,dictionaries,captures=_parent_inputs(parent_root)
    legacy=tmp_path/'legacy_materialization';legacy.mkdir()
    bundle=_prepare_bundle(legacy,parent_root,parent,model,plan,sources,dictionaries,captures,policy_id=LEGACY_POLICY_ID)
    for path in legacy.rglob('*'):
        if path.is_file():
            target=out/path.relative_to(legacy);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
    historical=deepcopy(report);historical['policy_id']=LEGACY_POLICY_ID;historical['bundle']=bundle
    historical['outputs']=[_ref(p,out) for p in sorted(out.rglob('*')) if p.is_file() and p!=out/REPORT]
    (out/REPORT).write_text(json.dumps(historical))
    assert read_mixed_context(out,linked_parent_directory=parent_root)==historical
    assert '\nloop_\n_chem_mod_atom.mod_id\n' not in mod.read_text()
    historical['policy_id']=POLICY_ID;(out/REPORT).write_text(json.dumps(historical))
    with pytest.raises(ValueError):read_mixed_context(out,linked_parent_directory=parent_root)


def test_c87_no_atom_modification_keeps_the_existing_noop_bytes_for_both_policies(tmp_path):
    from nasolve.cif_mixed_context import _prepare_component,POLICY_ID,LEGACY_POLICY_ID
    model,plan,sources,dictionaries,before,after,numerical=context_fixture(tmp_path)
    model.write_text(''.join(line for line in model.read_text().splitlines(keepends=True)
        if not (line.startswith('HETATM') and line[21]=='A' and line[22:26].strip()=='2')))
    contexts=[{'site':'A:1','incoming_site':None,'outgoing_site':None,
        'five_prime_state':'phosphate','three_prime_state':'free_OH'}]
    payloads=[]
    for number,policy in enumerate([LEGACY_POLICY_ID,POLICY_ID]):
        out=tmp_path/f'prepared_{number}'
        receipt=_prepare_component(sources['Q17'],numerical['Q17'],model,contexts,out,code='Q17',
            normalize_group=True,policy_id=policy)
        payloads.append((out/receipt['outputs']['modifications']['path']).read_bytes())
    assert payloads==[b'data_mod_context_sites\n# No atom modifications required.\n']*2
