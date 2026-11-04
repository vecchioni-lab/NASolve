"""Source-derived eligibility under explicit policies, never residue-name whitelists.

Native summaries below are synthetic contracts, not native scientific evidence.
Actual native qualification is exercised separately in the local C133 control.
"""
from hashlib import sha256
from unittest.mock import patch
import pytest
from .test_cif_fana import inputs, numerical
from .test_cif_stereochemistry_audit import write

POLICY='cif-source-declared-neutral-6-oxo-purine-aromatic-v1'


def qualification(source,candidate,code):
    from nasolve.cif_candidate_usability import reassess_complete_candidate
    from nasolve.cif_preparation_qualification import REQUIRED_NATIVE_CHECKS
    return {'schema_version':1,'policy_id':'cif-isolated-candidate-native-usability-v3',
        'status':'ISOLATED_NATIVE_USABILITY_PASS','native_usable':True,'component':code,
        'scope':'ISOLATED_COMPONENT_ONLY','candidate_sha256':sha256(candidate.read_bytes()).hexdigest(),
        'checks':{k:True for k in REQUIRED_NATIVE_CHECKS},
        'source_assessment':reassess_complete_candidate(source,candidate,code,bond_representation_policy=POLICY)}


def bind(source,candidate,code,q,policy=POLICY):
    from nasolve.cif_preparation_qualification import bind_preparation_qualification
    return bind_preparation_qualification(source,candidate,code,q,bond_representation_policy=policy)


def test_explicit_representation_reaches_linked_preparation(tmp_path):
    from .test_cif_linked_preparation import fixture
    from nasolve.cif_linked_preparation import prepare_linked_component
    s,c,m,contexts=fixture(tmp_path)
    # This fixture's graph needs no aromatic permission; selecting a policy must
    # not fabricate a chemical change or relax the source comparison.
    q={'policy_id':'cif-isolated-candidate-native-usability-v3','native_usable':True}
    with pytest.raises(ValueError):
        prepare_linked_component(s,c,m,contexts,tmp_path/'out',code='ZZZ',native_qualification=q,bond_representation_policy=POLICY)


@pytest.mark.parametrize('hand',['D','L'])
@pytest.mark.parametrize('sugar',['arabino_fluoro','ribo_fluoro','deoxy'])
@pytest.mark.parametrize('rename',[False,True])
def test_all_source_centres_are_checked_independent_of_family_or_names(tmp_path,hand,sugar,rename):
    s,book,v,n=inputs(tmp_path,hand=hand,ribo=sugar=='ribo_fluoro',rename=rename)
    if sugar=='deoxy':
        ids=v['_chem_comp_atom.atom_id'];v['_chem_comp_atom.type_symbol'][ids.index(n['F'])]='H'
        v['_chem_comp_atom.pdbx_stereo_config'][ids.index(n['C2'])]='N'
        write(s,v)
    c=write(tmp_path/'candidate.cif',numerical(v));q=qualification(s,c,'Z99')
    before=s.read_bytes(),c.read_bytes()
    with patch('subprocess.Popen',side_effect=AssertionError('read-only')):r=bind(s,c,'Z99',q)
    assert r['candidate_reassessment']['candidate_status']=='CANDIDATE_REVIEW'
    stereo=r['source_configuration']
    assert len(stereo['terms'])==(3 if sugar=='deoxy' else 4)
    assert all(x['handedness']=='PRESERVED' for x in stereo['terms'])
    assert r['source_configuration']['absolute_cip_assignment']=='NOT_RUN'
    assert r['linked_qualification']=='NOT_RUN' and not r['automatic_adoption']
    assert before==(s.read_bytes(),c.read_bytes())


@pytest.mark.parametrize('defect',['mirror','c2_inverted','flat','missing_coordinates','lost_f','f_to_o','charge','phosphate_h','stale_qualification'])
def test_general_guard_catches_chemistry_or_configuration_damage(tmp_path,defect):
    s,book,v,n=inputs(tmp_path,hand='L',rename=True);g=numerical(v);c=write(tmp_path/'candidate.cif',g);q=qualification(s,c,'Z99');a='_chem_comp_atom.';ids=g[a+'atom_id']
    if defect=='mirror':g[a+'z']=[str(-float(x)) for x in g[a+'z']]
    if defect=='c2_inverted':
        i,j=ids.index(n['F']),ids.index(n['C2H0'])
        for axis in 'xyz':g[a+axis][i],g[a+axis][j]=g[a+axis][j],g[a+axis][i]
    if defect=='flat':g[a+'z']=['0']*len(ids)
    if defect=='missing_coordinates':g.pop(a+'z')
    if defect=='lost_f':
        from nasolve.cif_linked_preparation import _prune
        g=_prune(g,{n['F']},outgoing=False)
    if defect=='f_to_o':g[a+'type_symbol'][ids.index(n['F'])]='O'
    if defect=='charge':g[a+'charge'][ids.index(n['P2'])]='-1'
    if defect=='phosphate_h':g[a+'type_symbol'][ids.index(n['P2H0'])]='C'
    if defect=='stale_qualification':g[a+'type_energy'][0]='CHANGED'
    write(c,g)
    if defect!='stale_qualification':q=qualification(s,c,'Z99')
    with pytest.raises(ValueError):bind(s,c,'Z99',q)


@pytest.mark.parametrize('defect',['unknown_policy','omitted_policy','other_policy','old_version','false_check','missing_check','extra_check','true_integer','source_hash','component','scope','status','stereo_summary','representation_summary','schema_boolean'])
def test_qualification_and_policy_cannot_be_relabelled(tmp_path,defect):
    s,b,v,n=inputs(tmp_path);c=write(tmp_path/'candidate.cif',numerical(v));q=qualification(s,c,'Z99');policy=POLICY
    if defect=='schema_boolean':q['schema_version']=True
    if defect=='unknown_policy':policy='allow-everything'
    if defect=='omitted_policy':policy=None
    if defect=='other_policy':policy='cif-source-declared-neutral-purine-aromatic-v1'
    if defect=='old_version':q['policy_id']='cif-isolated-candidate-native-usability-v2'
    if defect=='false_check':q['checks']['exact_active_bonds']=False
    if defect=='missing_check':q['checks'].pop('exact_active_bonds')
    if defect=='extra_check':q['checks']['invented']=True
    if defect=='true_integer':q['checks']['exact_active_bonds']=1
    if defect=='source_hash':q['source_assessment']['finished_stereo']['source_sha256']='0'*64
    if defect=='component':q['component']='OTHER'
    if defect=='scope':q['scope']='LINKED'
    if defect=='status':q['status']='REVIEW'
    if defect=='stereo_summary':q['source_assessment']['finished_stereo']['terms']=[]
    if defect=='representation_summary':q['source_assessment']['legacy_inspection']['bond_representation']['unresolved_bonds']=['hidden']
    with pytest.raises(ValueError):bind(s,c,'Z99',q,policy)


def test_residue_code_is_an_identity_not_a_chemical_whitelist(tmp_path):
    s,b,v,n=inputs(tmp_path,hand='L',rename=True)
    for k,values in v.items():
        if k.endswith('.comp_id') or k=='_chem_comp.id':v[k]=['X73']*len(values)
    s=write(s,v);g=numerical(v)
    for k,values in g.items():
        if k.endswith('.comp_id'):g[k]=['X73']*len(values)
    c=write(tmp_path/'candidate.cif',g);q=qualification(s,c,'X73')
    assert len(bind(s,c,'X73',q)['source_configuration']['terms'])==4


def test_qualified_terminal_bridge_preserves_declared_site_chemistry(tmp_path):
    from .test_cif_linked_preparation import fixture
    from .test_cif_terminal_preparation import resource_fixture
    from nasolve.cif_linked_preparation import prepare_linked_component
    from nasolve.cif_terminal_preparation import prepare_terminal_component
    s,c,m,contexts=fixture(tmp_path)
    from nasolve.cif_linked_preparation import component_values,_render
    v=component_values(s,'ZZZ');v['_chem_comp.group']=['DNA'];s.write_text(_render(v,'ZZZ'))
    q=qualification(s,c,'ZZZ')
    resource,_=resource_fixture(tmp_path)
    legacy=prepare_linked_component(s,c,m,contexts,tmp_path/'legacy',code='ZZZ')
    result=prepare_terminal_component(s,c,m,contexts,resource,tmp_path/'new',code='ZZZ',
        native_qualification=q,bond_representation_policy=POLICY)
    assert result['policy_id']=='cif-native-five-prime-hydroxyl-v2'
    assert result['linked_preparation_policy']=='cif-source-preserving-linked-sites-v3'
    assert result['preparation_qualification']['source_configuration']['terms']==[]
    sites={p['site']:p for p in result['sites']}
    old={p['site']:p for p in legacy['sites']}
    for site in ['A:2','A:1']:
        assert sites[site]['source_configuration_projection']==[]
        assert {k:v for k,v in sites[site].items() if k not in {'source_configuration_projection','source_port_qualification'}}==old[site]
    assert 'OP3' not in sites['A:2']['expected_atoms']
    assert sites['A:2']['retained_op2_hydrogens']==['keepH']
    assert 'OP3' in sites['A:1']['expected_atoms']
    assert not {'P','OP1','OP2','OP3'} & set(sites['B:1']['expected_atoms'])
    assert sites['B:1']['terminal_hydroxyl']['new_hydrogen_formal_charge']=='UNASSESSED'
    assert result['native_validation']=='NOT_RUN' and not result['automatic_adoption']


@pytest.mark.parametrize('source_type',['DNA LINKING','L-DNA LINKING','l-dna linking'])
def test_qualified_linked_source_type_preserves_hand_declaration(tmp_path,source_type):
    from .test_cif_linked_preparation import fixture
    from nasolve.cif_linked_preparation import prepare_linked_component,component_values,_render
    s,c,m,contexts=fixture(tmp_path)
    v=component_values(s,'ZZZ');v['_chem_comp.type']=[source_type];v['_chem_comp.group']=['DNA'];s.write_text(_render(v,'ZZZ'))
    q=qualification(s,c,'ZZZ')
    result=prepare_linked_component(s,c,m,contexts,tmp_path/'new',code='ZZZ',
        native_qualification=q,bond_representation_policy=POLICY)
    assert result['source_type']==source_type
    assert result['source_preserved'] and not result['automatic_adoption']


@pytest.mark.parametrize('kind,group',[('RNA LINKING','DNA'),('non-polymer','DNA'),
    ('L-DNA LINKING','RNA'),('L-DNA LINKING','other'),('?','DNA'),('L-DNA LINKING L-DNA LINKING','DNA')])
def test_explicit_bridge_does_not_guess_or_override_polymer_declarations(tmp_path,kind,group):
    from .test_cif_linked_preparation import fixture
    from nasolve.cif_linked_preparation import prepare_linked_component,component_values,_render
    s,c,m,contexts=fixture(tmp_path)
    v=component_values(s,'ZZZ');v['_chem_comp.type']=[kind];v['_chem_comp.group']=[group];s.write_text(_render(v,'ZZZ'))
    q=qualification(s,c,'ZZZ')
    with pytest.raises(ValueError):prepare_linked_component(s,c,m,contexts,tmp_path/'new',code='ZZZ',
        native_qualification=q,bond_representation_policy=POLICY)
    assert not (tmp_path/'new').exists()



def fixed_phosphate_source(tmp_path):
    """Synthetic declared centre: tests retention, not actual P stereochemistry."""
    from .test_cif_linked_preparation import fixture
    from nasolve.cif_linked_preparation import component_values,_render
    s,c,m,contexts=fixture(tmp_path);v=component_values(s,'ZZZ');v['_chem_comp.group']=['DNA']
    ids=v['_chem_comp_atom.atom_id'];positions={'OP1':(0,0,0),'OP2':(1,0,0),'OP3':(0,1,0),"O5'":(0,0,1)}
    for j,axis in enumerate('xyz'):v['_chem_comp_atom.'+axis]=[str(positions.get(n,(2+i,3+i,4+i))[j]) for i,n in enumerate(ids)]
    v['_chem_comp_atom.pdbx_stereo_config']=['R' if n=='P' else 'N' for n in ids]
    row={'comp_id':'ZZZ','id':'source_fixed','atom_id_centre':'P','atom_id_1':'OP1','atom_id_2':'OP2','atom_id_3':'OP3','volume_sign':'positive'}
    v.update({'_chem_comp_chir.'+k:[val] for k,val in row.items()})
    for p in (s,c):p.write_text(_render(v,'ZZZ'))
    return s,c,m,contexts


def test_link_operation_cannot_drop_a_retained_source_fixed_configuration(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    s,c,m,contexts=fixed_phosphate_source(tmp_path);q=qualification(s,c,'ZZZ')
    assert q['source_assessment']['finished_stereo']['terms'][0]['handedness']=='PRESERVED'
    with pytest.raises(ValueError,match='retained source'):
        prepare_linked_component(s,c,m,contexts,tmp_path/'new',code='ZZZ',
            native_qualification=q,bond_representation_policy=POLICY)
    assert not (tmp_path/'new').exists()


def test_explicit_group_removal_records_removed_source_centre(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    s,c,m,contexts=fixed_phosphate_source(tmp_path);q=qualification(s,c,'ZZZ')
    m.write_text(''.join(line for line in m.read_text().splitlines(keepends=True)
        if not line.startswith(('ATOM  ','HETATM')) or line[21]=='B'))
    result=prepare_linked_component(s,c,m,[r for r in contexts if r['site']=='B:1'],tmp_path/'new',code='ZZZ',
        native_qualification=q,bond_representation_policy=POLICY)
    checks=result['sites'][0]['source_configuration_projection']
    assert checks==[{'center':'P','status':'REMOVED_WITH_EXPLICIT_GROUP','ordered_neighbors':['OP1','OP2','OP3',"O5'"]}]



@pytest.mark.parametrize('defect',['leaving_fluorine','phosphate_sulfur','wrong_phosphorus',
    'outgoing_fluorine','charged_outgoing','charged_leaving','leaving_h_deuterium',
    'outgoing_double_bond','extra_outgoing_heavy','missing_o5_c5'])
def test_named_ports_must_have_the_declared_chemical_operation(tmp_path,defect):
    from .test_cif_linked_preparation import fixture
    from nasolve.cif_linked_preparation import prepare_linked_component,component_values,_render
    s,c,m,contexts=fixture(tmp_path);v=component_values(s,'ZZZ');v['_chem_comp.group']=['DNA']
    ids=v['_chem_comp_atom.atom_id'];a='_chem_comp_atom.';b='_chem_comp_bond.'
    changes={'leaving_fluorine':('OP3','F'),'phosphate_sulfur':('OP1','S'),
             'wrong_phosphorus':('P','As'),'outgoing_fluorine':("O3'",'F'),
             'leaving_h_deuterium':('leaveH','D')}
    if defect in changes:
        name,element=changes[defect];v[a+'type_symbol'][ids.index(name)]=element
    if defect=='charged_outgoing':v[a+'charge'][ids.index("O3'")]='-1'
    if defect=='charged_leaving':v[a+'charge'][ids.index('OP3')]='-1'
    pairs=list(zip(v[b+'atom_id_1'],v[b+'atom_id_2']))
    if defect=='outgoing_double_bond':v[b+'type'][pairs.index(("C3'","O3'"))]='double'
    if defect in {'extra_outgoing_heavy','missing_o5_c5'}:
        i=pairs.index(("O5'","C5'"));v[b+'atom_id_1'][i]="O3'" if defect=='extra_outgoing_heavy' else 'OP1'
        # This source graph intentionally differs; derive complete angle rows
        # for that graph so rejection must come from the operation contract.
        from itertools import combinations
        for k in list(v):
            if k.startswith('_chem_comp_angle.'):v.pop(k)
        neighbors={n:set() for n in ids}
        for x,y in zip(v[b+'atom_id_1'],v[b+'atom_id_2']):neighbors[x].add(y);neighbors[y].add(x)
        rows=[('ZZZ',x,center,y,'109.47','3.0') for center,ns in neighbors.items() for x,y in combinations(sorted(ns),2)]
        for i,k in enumerate(['comp_id','atom_id_1','atom_id_2','atom_id_3','value_angle','value_angle_esd']):v['_chem_comp_angle.'+k]=[r[i] for r in rows]
    for path in (s,c):path.write_text(_render(v,'ZZZ'))
    q=qualification(s,c,'ZZZ');assert q['source_assessment']['candidate_status']=='CANDIDATE_REVIEW'
    out=tmp_path/'new'
    if defect=='leaving_h_deuterium':
        r=prepare_linked_component(s,c,m,contexts,out,code='ZZZ',native_qualification=q,bond_representation_policy=POLICY)
        assert 'leaveH' in next(p for p in r['sites'] if p['site']=='A:2')['deleted_atoms']
    else:
        with pytest.raises(ValueError):prepare_linked_component(s,c,m,contexts,out,code='ZZZ',native_qualification=q,bond_representation_policy=POLICY)
        assert not out.exists()
