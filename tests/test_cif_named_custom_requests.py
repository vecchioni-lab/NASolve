"""Display labels cannot hide changed ordered, indexed explicit restraints."""
from copy import deepcopy
import pytest
from tests.test_cif_named_proxy_comparison import native_pair

KINDS=['bond','angle','dihedral','planarity','parallelity']


def pair(kind='parallelity'):
    proxy='bond_simple' if kind=='bond' else kind
    a,b=native_pair(proxy)
    for n in (a,b):
        row=n['geometry']['proxy_details'][proxy][0]
        row.update(kind=kind,action='add',selections=['explicit selection '+str(i) for i in range(1 if kind=='planarity' else 3 if kind=='angle' else 4 if kind=='dihedral' else 2)])
        row.pop('origin_id',None)
        if kind=='dihedral':row['alt_angle_ideals']=[]
        n['geometry']['custom_proxy_requests']=[row]
    for atom in b['atoms']:atom['i_seq']-=20
    row=b['geometry']['custom_proxy_requests'][0]
    for k in ('i_seqs','j_seqs'):
        if k in row:row[k]=[i-20 for i in row[k]]
    for n,align in ((a,'right'),(b,'left')):
        for atom in n['atoms']:
            field=atom['atom_id'].rjust(4) if align=='right' else atom['atom_id'].ljust(4)
            atom['atom_name_field']=field;atom['label']='pdb="'+field+'  DG X  17 "'
        by_index={atom['i_seq']:atom for atom in n['atoms']}
        row=n['geometry']['custom_proxy_requests'][0]
        for key,labels in [('i_seqs','atoms'),('j_seqs','j_atoms')]:
            if key in row:row[labels]=[by_index[i]['label'] for i in row[key]]
    return a,b


def matches(a,b):
    from nasolve.cif_terminal_qualification import ordered_custom_requests_match
    return ordered_custom_requests_match(a,b)


@pytest.mark.parametrize('kind',KINDS)
def test_only_bound_display_padding_can_change(kind):
    a,b=pair(kind);snapshot=deepcopy((a,b))
    assert matches(a,b)
    assert (a,b)==snapshot


@pytest.mark.parametrize('defect',['target','weight','element','residue','atom_name','selection','action','symmetry','endpoint_order','second_plane_order','row_order','multiplicity','index','extra_parameter'])
def test_every_non_display_difference_remains_visible(defect):
    a,b=pair();row=b['geometry']['custom_proxy_requests'][0]
    if defect=='target':row['target_angle_deg']=1.
    elif defect=='weight':row['weight']+=1.
    elif defect=='element':b['atoms'][0]['element']='N'
    elif defect=='residue':b['atoms'][0]['identity']['resname']='DA'
    elif defect=='atom_name':
        atom=b['atoms'][0];atom['atom_id']='N1';atom['atom_name_field']='N1  ';atom['label']='pdb="N1  '+atom['label'][9:];row['j_atoms'][-1]=atom['label']
    elif defect=='selection':row['selections'][0]+=' '
    elif defect=='action':row['action']='delete'
    elif defect=='symmetry':row['symmetry_operation']='-x,y,z'
    elif defect=='extra_parameter':row['new_parameter']=1.
    elif defect in {'endpoint_order','second_plane_order'}:
        k,l=('i_seqs','atoms') if defect=='endpoint_order' else ('j_seqs','j_atoms');row[k].reverse();row[l].reverse()
    elif defect=='multiplicity':b['geometry']['custom_proxy_requests'].append(deepcopy(row))
    elif defect=='row_order':
        for n in (a,b):
            q=deepcopy(n['geometry']['custom_proxy_requests'][0]);q['weight']+=1.;n['geometry']['custom_proxy_requests'].append(q)
        b['geometry']['custom_proxy_requests'].reverse()
    elif defect=='index':
        for atom in b['atoms']:atom['i_seq']+=100
        for k in ('i_seqs','j_seqs'):row[k]=[i+100 for i in row[k]]
    assert not matches(a,b)


@pytest.mark.parametrize('defect',['duplicate_index','duplicate_identity','missing_identity','null_identity','blank_name','missing_element','blank_label','first_label','second_label','missing_second_labels','missing_second_indices','unknown_index','bool_index','repeat_first','repeat_second','overlap','short_first','short_second','missing_rows','missing_selections','blank_selection','nonfinite_target','missing_action'])
def test_malformed_or_ambiguous_evidence_refuses(defect):
    _,b=pair();row=b['geometry']['custom_proxy_requests'][0]
    if defect=='duplicate_index':b['atoms'].append(deepcopy(b['atoms'][0]))
    elif defect=='duplicate_identity':
        atom=deepcopy(b['atoms'][0]);atom['i_seq']=99;b['atoms'].append(atom)
    elif defect=='missing_identity':del b['atoms'][0]['identity']['altloc']
    elif defect=='null_identity':b['atoms'][0]['identity']['altloc']=None
    elif defect=='blank_name':b['atoms'][0]['atom_id']=' '
    elif defect=='missing_element':del b['atoms'][0]['element']
    elif defect=='blank_label':b['atoms'][0]['label']=' '
    elif defect=='first_label':row['atoms'][0]='wrong'
    elif defect=='second_label':row['j_atoms'][0]='wrong'
    elif defect=='missing_second_labels':del row['j_atoms']
    elif defect=='missing_second_indices':del row['j_seqs']
    elif defect=='unknown_index':row['j_seqs'][0]=99
    elif defect=='bool_index':row['i_seqs'][0]=True
    elif defect in {'repeat_first','repeat_second','short_first','short_second'}:
        k,l=('i_seqs','atoms') if defect.endswith('first') else ('j_seqs','j_atoms')
        if defect.startswith('short'):row[k].pop();row[l].pop()
        else:row[k][0]=row[k][1];row[l][0]=row[l][1]
    elif defect=='overlap':row['j_seqs'][0]=row['i_seqs'][0];row['j_atoms'][0]=row['atoms'][0]
    elif defect=='missing_rows':b['geometry']['custom_proxy_requests']=None
    elif defect=='missing_selections':del row['selections']
    elif defect=='blank_selection':row['selections'][0]=' '
    elif defect=='nonfinite_target':row['target_angle_deg']=float('nan')
    elif defect=='missing_action':del row['action']
    with pytest.raises((ValueError,KeyError,TypeError)):matches(b,b)


def test_v3_is_opt_in_and_v2_does_not_change(tmp_path):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_postmr_cached_model import qualify_cached_model_roundtrip
    _,a,model,_,_=case(tmp_path);a['installed_api_sources']=[]
    row=deepcopy(a['geometry']['proxy_details']['bond_simple'][0]);row.update(kind='bond',action='add',selections=['first','second'])
    a['geometry']['custom_proxy_requests']=[row];b=deepcopy(a)
    for n,align in ((a,'right'),(b,'left')):
        for atom in n['atoms']:
            field=atom['atom_id'].rjust(4) if align=='right' else atom['atom_id'].ljust(4)
            atom['atom_name_field']=field
            ident=atom['identity'];atom['label']='pdb="'+field+' '+ident['resname'].rjust(3)+' '+ident['chain_id']+ident['resseq'].rjust(4)+' "'
        for rows in [*n['geometry']['proxy_details'].values(),n['geometry']['custom_proxy_requests']]:
            for q in rows:q['atoms']=[n['atoms'][i]['label'] for i in q['i_seqs']]
    legacy=qualify_cached_model_roundtrip(a,b,model,model)
    assert legacy['policy_id']=='cif-postmr-cached-model-readback-v2' and legacy['status']=='REVIEW'
    q=qualify_cached_model_roundtrip(a,b,model,model,explicit_request_policy='cif-native-ordered-named-custom-requests-v1')
    assert q['policy_id']=='cif-postmr-cached-model-readback-v3' and q['mechanics_checks_pass'] is True
    assert qualify_cached_model_roundtrip(a,b,model,model)==legacy
    for atom in b['atoms']:atom['label']='padded:'+atom['label']
    for rows in [*b['geometry']['proxy_details'].values(),b['geometry']['custom_proxy_requests']]:
        for row in rows:row['atoms']=[b['atoms'][i]['label'] for i in row['i_seqs']]
    rejected=qualify_cached_model_roundtrip(a,b,model,model,explicit_request_policy='cif-native-ordered-named-custom-requests-v1')
    assert rejected['status']=='REVIEW' and rejected['checks']['exact_explicit_requests'] is False
    with pytest.raises(ValueError):qualify_cached_model_roundtrip(a,b,model,model,explicit_request_policy='unknown')


def rebind_labels(native):
    atoms={a['i_seq']:a for a in native['atoms']}
    for row in native['geometry']['custom_proxy_requests']:
        for key,labels in [('i_seqs','atoms'),('j_seqs','j_atoms')]:
            if key in row:row[labels]=[atoms[i]['label'] for i in row[key]]


@pytest.mark.parametrize('plane',['first','second'])
@pytest.mark.parametrize('change',['arbitrary','prefix','suffix','same_length_suffix','missing_field','unrecognized'])
def test_only_verified_name_padding_is_exempt_even_when_labels_are_rebound(plane,change):
    a,b=pair();assert matches(a,b)
    atom=next(v for v in b['atoms'] if v['i_seq']==(0 if plane=='first' else 3))
    if change=='arbitrary':atom['label']='arbitrary same-capture label'
    elif change=='prefix':atom['label']='padded:'+atom['label']
    elif change=='suffix':atom['label']+=' extra'
    elif change=='same_length_suffix':atom['label']=atom['label'][:-3]+'8 "'
    elif change=='missing_field':del atom['atom_name_field']
    elif change=='unrecognized':atom['label']=atom['label'].replace('pdb=','other=')
    rebind_labels(b)
    assert not matches(a,b)


@pytest.mark.parametrize('optional',['missing_both','missing_one','unrecognized_equal'])
def test_exact_raw_labels_remain_usable_without_supported_optional_format(optional):
    a,_=pair();b=deepcopy(a)
    if optional=='unrecognized_equal':
        for n in (a,b):
            for atom in n['atoms']:atom['label']='opaque:'+atom['label']
            rebind_labels(n)
    else:
        for n in ((a,b) if optional=='missing_both' else (a,)):
            for atom in n['atoms']:del atom['atom_name_field']
    assert matches(a,b)


@pytest.mark.parametrize('plane',['first','second'])
@pytest.mark.parametrize('defect',['contradicts_label','contradicts_identity','wrong_length','wrong_type'])
def test_supplied_name_field_must_agree_with_raw_label_and_structured_identity(plane,defect):
    a,b=pair();atom=next(v for v in b['atoms'] if v['i_seq']==(0 if plane=='first' else 3))
    if defect=='contradicts_label':atom['atom_name_field']=' N9 '
    elif defect=='contradicts_identity':atom['atom_id']='N9'
    elif defect=='wrong_length':atom['atom_name_field']='C'
    else:atom['atom_name_field']=123
    with pytest.raises(ValueError,match='atom-name field'):matches(a,b)


def test_large_request_inventory_builds_each_atom_index_once():
    class CountedAtoms(list):
        traversals=0
        def __iter__(self):
            self.traversals+=1
            return super().__iter__()
    a,b=pair()
    for native in (a,b):
        native['geometry']['custom_proxy_requests']*=200
        native['atoms']=CountedAtoms(native['atoms'])
    assert matches(a,b)
    assert a['atoms'].traversals==b['atoms'].traversals==1


@pytest.mark.parametrize('padding', ['\t', '\u00a0'])
def test_only_literal_pdb_spaces_can_pad_an_atom_name(padding):
    before, after = pair()
    atom = after['atoms'][0]
    field = atom['atom_name_field'].replace(' ', padding, 1)
    assert field != atom['atom_name_field']
    atom['atom_name_field'] = field
    atom['label'] = atom['label'][:5] + field + atom['label'][9:]
    rebind_labels(after)
    with pytest.raises(ValueError, match='atom-name field'):
        matches(before, after)


@pytest.mark.parametrize('part', ['chain_id', 'element'])
def test_non_pdb_whitespace_in_structured_identity_is_significant(part):
    before, after = pair()
    atom = after['atoms'][0]
    table = atom if part == 'element' else atom['identity']
    table[part] += '\t'
    assert not matches(before, after)
