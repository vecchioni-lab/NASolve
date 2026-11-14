"""Frozen site orchestration; synthetic numerics are not native qualifications."""
from copy import deepcopy
from hashlib import sha256
import json
import shutil
from unittest.mock import patch

import pytest

from nasolve.cif_dictionary_store import resolve_qualified_dictionary
from tests.test_cif_linked_preparation import fixture
from tests.test_cif_terminal_preparation import resource_fixture
from tests.test_cif_preparation_qualification import qualification, POLICY


def inputs(tmp_path, *, terminal=True, explicit=True):
    from nasolve.cif_linked_preparation import component_values, _render
    from nasolve.cif_postmr_cache import _API, _ENERGY
    s,c,m,contexts=fixture(tmp_path)
    if not terminal:
        contexts=[r for r in contexts if r['site']!='B:1']
        m.write_text(''.join(line for line in m.read_text().splitlines(keepends=True)
            if not line.startswith(('ATOM  ','HETATM')) or line[21]!='B'))
    v=component_values(s,'ZZZ');v['_chem_comp.group']=['DNA'];s.write_text(_render(v,'ZZZ'))
    q=qualification(s,c,'ZZZ')
    recipe={'policy_id':'SYNTHETIC_REPAIR'}
    if explicit:recipe['bond_representation_policy']=POLICY
    else:
        from nasolve.cif_candidate_usability import reassess_complete_candidate
        q['policy_id']='cif-isolated-candidate-native-usability-v2'
        q['source_assessment']=reassess_complete_candidate(s,c,'ZZZ')
    consumer={'name':'Phenix/CCTBX','version':'fake-test','executable_sha256':'d'*64,
        **{field:[{'anchor':'phenix_installation','path':'lib/site-packages/'+name,
                    'sha256':sha256(name.encode()).hexdigest()} for name in names]
            for field,names in [('api_sources',_API),('energy_sources',_ENERGY)]}}
    resolve_qualified_dictionary(s,'ZZZ',tmp_path/'store',tmp_path/'snapshot',
        source_authority='EXPLICIT',recipe=recipe,generator={'name':'FAKE','version':'TEST'},
        consumer=consumer,acquire=lambda:dict(candidate=c,qualification=q,
            provenance={'converged':False,'stopping':'TEST','notes':['Synthetic fixture.']}))
    resource=None
    if terminal:
        resource,native=resource_fixture(tmp_path)
        native['api_sources']=[{'module':'mmtbx.monomer_library.server',
            'sha256':sha256(b'mmtbx/monomer_library/server.py').hexdigest()}]
        r=json.loads(resource.read_text());r['native_resources']=native;r['executable_sha256']=consumer['executable_sha256']
        p=resource.parent/'native_resources.json';p.write_text(json.dumps(native))
        r['outputs'][0].update(size=p.stat().st_size,sha256=sha256(p.read_bytes()).hexdigest())
        resource.write_text(json.dumps(r))
    return dict(snapshot=tmp_path/'snapshot',model=m,contexts=contexts,consumer=consumer,
        expected_links=[('A:1','A:2')],terminal_resource=resource)


@pytest.mark.parametrize('terminal',[False,True])
@pytest.mark.parametrize('explicit',[False,True])
def test_saved_policy_reaches_exact_sites_and_survives_source_removal(tmp_path,terminal,explicit):
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites, read_dictionary_sites
    args=inputs(tmp_path,terminal=terminal,explicit=explicit)
    result=prepare_dictionary_sites(output=tmp_path/'prepared',**args)
    assert result['status']=='PREPARED_REVIEW' and result['automatic_adoption'] is False
    assert result['bond_representation_policy']==(POLICY if explicit else None)
    assert result['expected_links']==[['A:1','A:2']]
    frozen={p.relative_to(tmp_path/'prepared'):(p.read_bytes(),p.stat().st_mtime_ns)
        for p in (tmp_path/'prepared').rglob('*') if p.is_file()}
    (tmp_path/'prepared').rename(tmp_path/'moved')
    for name in ['store','snapshot','inputs','resources']:
        if (tmp_path/name).exists():shutil.rmtree(tmp_path/name)
    with patch('subprocess.Popen',side_effect=AssertionError('Read must not execute native code')):
        read=read_dictionary_sites(tmp_path/'moved')
    assert read['report']==result and len(read['projections'])==(3 if terminal else 2)
    assert all(((tmp_path/'moved'/p).read_bytes(),(tmp_path/'moved'/p).stat().st_mtime_ns)==v for p,v in frozen.items())


@pytest.mark.parametrize('defect',['consumer','missing_resource','extra_resource','links_missing',
    'links_reversed','links_duplicate','missing_context','stale_qualification','resource_consumer'])
def test_bad_context_or_identity_never_publishes(tmp_path,defect):
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites
    args=inputs(tmp_path,terminal=defect!='extra_resource')
    if defect=='consumer':args['consumer']['version']='other'
    if defect=='missing_resource':args['terminal_resource']=None
    if defect=='extra_resource':args['terminal_resource']=resource_fixture(tmp_path)[0]
    if defect=='links_missing':args['expected_links']=[]
    if defect=='links_reversed':args['expected_links']=[('A:2','A:1')]
    if defect=='links_duplicate':args['expected_links']*=2
    if defect=='missing_context':args['contexts']=args['contexts'][:-1]
    if defect=='stale_qualification':
        (args['snapshot']/'entry/qualification.json').write_text('{}')
    if defect=='resource_consumer':
        r=json.loads(args['terminal_resource'].read_text());r['executable_sha256']='0'*64
        args['terminal_resource'].write_text(json.dumps(r))
    with pytest.raises((ValueError,KeyError)):
        prepare_dictionary_sites(output=tmp_path/'out',**args)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',['policy','consumer','contexts','links','false_claim','projection',
    'modified_phil','extra_file','rehashed_extra','symlink','stale_hash','integer_boolean','float_size'])
def test_readback_recomputes_claims_and_generated_files(tmp_path,defect):
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites, read_dictionary_sites
    args=inputs(tmp_path);out=tmp_path/'out';prepare_dictionary_sites(output=out,**args)
    receipt=out/'site_receipt.json';r=json.loads(receipt.read_text())
    if defect=='policy':r['bond_representation_policy']='invented'
    if defect=='consumer':r['consumer']['version']='new'
    if defect=='contexts':r['contexts'][0]['five_prime_state']='free_OH'
    if defect=='links':r['expected_links']=[]
    if defect=='false_claim':r['automatic_adoption']=True
    if defect=='integer_boolean':r['automatic_adoption']=0
    if defect=='float_size':r['files'][0]['size']=float(r['files'][0]['size'])
    if defect in {'extra_file','rehashed_extra'}:
        p=out/'junk.txt';p.write_text('unlisted')
        if defect=='rehashed_extra':
            from nasolve.cif_dictionary_sites import _files
            r['files']=_files(out)
    if defect=='symlink':
        p=out/'inputs/model.pdb';p.unlink();p.symlink_to(args['model'])
    if defect in {'projection','modified_phil','stale_hash'}:
        p=out/'prepared'/('projected_A_2.cif' if defect=='projection' else 'site_modifications.phil')
        p.write_bytes(p.read_bytes()+b'\n# tampered\n')
        if defect!='stale_hash':
            ref=next(v for v in r['files'] if v['path']==p.relative_to(out).as_posix())
            ref.update(sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
    receipt.write_text(json.dumps(r))
    with pytest.raises((ValueError,KeyError)):
        read_dictionary_sites(out)


def test_fresh_output_and_explicit_supplementary_order(tmp_path):
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites, read_dictionary_sites
    args=inputs(tmp_path);a=tmp_path/'a.cif';b=tmp_path/'b.cif';p=tmp_path/'restraints.phil'
    a.write_text('data_A');b.write_text('data_B');p.write_text('# explicit policy')
    args.update(supplementary_dictionaries=[b,a],supplementary_phils=[p])
    out=tmp_path/'out';prepare_dictionary_sites(output=out,**args)
    r=read_dictionary_sites(out)
    assert [v.read_bytes() for v in r['before_dictionaries'][1:]]==[b.read_bytes(),a.read_bytes()]
    assert [v.read_bytes() for v in r['after_phils'][:-1]]==[p.read_bytes()]
    with pytest.raises(FileExistsError):prepare_dictionary_sites(output=out,**args)


def captured(consumer, model, dictionaries, phils):
    return {'execution':{'status':'COMPLETED','returncode':0},
        'phenix_version':consumer['version'],'executable_sha256':consumer['executable_sha256'],
        'native_validation':{'installed_api_sources':[
            {'historical_path':'/previous/phenix/'+p['path'],'sha256':p['sha256']} for p in consumer['api_sources']],
            'energy_inventory':{'installed_sources':[
                {'historical_path':'/previous/phenix/'+p['path'],'sha256':p['sha256']} for p in consumer['energy_sources']]}},
        'inputs':[{'role':role,'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
            for role,p in [('model',model),*[('dictionary',p) for p in dictionaries],*[('phil',p) for p in phils]]]}


@pytest.mark.parametrize('defect',[None,'version','dispatcher','api_hash','energy_hash','duplicate_api',
    'incomplete_api','unsafe_pin','role','order','size','hash','omitted_input','extra_input','failed'])
def test_native_binding_requires_exact_order_bytes_and_implementation(tmp_path,defect):
    from nasolve.cif_dictionary_sites import _bind_capture
    args=inputs(tmp_path,terminal=False);consumer=args['consumer'];model=args['model']
    dictionary=tmp_path/'a.cif';dictionary.write_text('data_explicit')
    phil=tmp_path/'a.phil';phil.write_text('# explicit policy')
    record=captured(consumer,model,[dictionary],[phil])
    if defect=='version':record['phenix_version']='other'
    if defect=='dispatcher':record['executable_sha256']='0'*64
    if defect=='api_hash':record['native_validation']['installed_api_sources'][0]['sha256']='0'*64
    if defect=='energy_hash':record['native_validation']['energy_inventory']['installed_sources'][0]['sha256']='0'*64
    if defect=='duplicate_api':consumer['api_sources'][0]=deepcopy(consumer['api_sources'][1])
    if defect=='incomplete_api':consumer['api_sources'].pop()
    if defect=='unsafe_pin':consumer['api_sources'][0]['path']='../'+consumer['api_sources'][0]['path']
    if defect=='role':record['inputs'][1]['role']='phil'
    if defect=='order':record['inputs'][1:]=record['inputs'][1:][::-1]
    if defect=='size':record['inputs'][1]['size']+=1
    if defect=='hash':record['inputs'][1]['sha256']='0'*64
    if defect=='omitted_input':record['inputs'].pop()
    if defect=='extra_input':record['inputs'].append(deepcopy(record['inputs'][-1]))
    if defect=='failed':record['execution']['returncode']=1
    if defect is None:_bind_capture(record,consumer,model,[dictionary],[phil])
    else:
        with pytest.raises(ValueError):_bind_capture(record,consumer,model,[dictionary],[phil])


def test_frozen_snapshot_is_not_a_destination(tmp_path):
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites
    args=inputs(tmp_path,terminal=False)
    with pytest.raises(ValueError,match='inside the frozen snapshot'):
        prepare_dictionary_sites(output=args['snapshot']/'sites',**args)
    assert not (args['snapshot']/'sites').exists()


@pytest.mark.parametrize('defect',[None,'selected_target','selected_plane_weight','selected_chirality',
    'zero_chirality_weight','zero_volume','missing_proxy_family','wrong_count','wrong_label',
    'geometry_coordinate','duplicate_mapping','missing_mapping','wrong_modifier',
    'nonrepeat_energy','missing_energy','competing_policy','selected_element'])
def test_active_site_checks_include_selected_endpoints_and_manager_evidence(tmp_path,defect):
    from nasolve.cif_dictionary_sites import _site_native_checks
    from tests.test_cif_candidate_usability import native_case
    _,candidate,_,before=native_case(tmp_path)
    for n in [before]:
        n['geometry']['simple_bonds']=deepcopy(n['geometry']['proxy_details']['bond_simple'])
        n['geometry']['asu_bonds']=[]
        n['monomer_mappings']['rows'][0]['chem_mod_ids']={'status':'RECORDED','ids':[]}
    after=deepcopy(before);d=after['geometry']['proxy_details']
    if defect=='selected_target':d['angle'][0]['angle_ideal']+=1
    if defect=='selected_plane_weight':d['planarity'][0]['weights'][0]*=2
    if defect=='selected_chirality':d['chirality'][0]['volume_ideal']*=-1
    if defect=='zero_chirality_weight':d['chirality'][0]['weight']=0
    if defect=='zero_volume':d['chirality'][0]['volume_ideal']=0
    if defect=='missing_proxy_family':d.pop('parallelity')
    if defect=='wrong_count':after['geometry']['proxy_counts']['angle']+=1
    if defect=='wrong_label':d['angle'][0]['atoms'][0]='unbound'
    if defect=='geometry_coordinate':after['geometry']['sites_cart_exact'][0]=[999,999,999]
    if defect=='duplicate_mapping':after['monomer_mappings']['rows']*=2
    if defect=='missing_mapping':after['monomer_mappings']['rows']=[]
    if defect=='wrong_modifier':after['monomer_mappings']['rows'][0]['chem_mod_ids']['ids']=['wrong']
    if defect=='nonrepeat_energy':after['energy_inventory']['snapshots'][1]['target']+=1
    if defect=='missing_energy':after.pop('energy_inventory')
    if defect=='competing_policy':after['restraint_policy']['secondary_structure_enabled']=True
    if defect=='selected_element':after['atoms'][0]['element']='As'
    prepared={'report':{'contexts':[{'site':'A:1','incoming_site':None}]},
        'projections':{'A:1':(candidate,'Q17')},'preparation':{'sites':[{'site':'A:1','modification_id':None}]}}
    checks=_site_native_checks(before,after,prepared)
    assert all(r['status']=='PASS' for r in checks) is (defect is None),checks


@pytest.mark.parametrize('allowed',[False,True])
def test_baseline_may_lack_only_the_explicitly_deleted_source_atoms(tmp_path,allowed):
    from nasolve.cif_dictionary_sites import _site_native_checks
    from tests.test_cif_candidate_usability import native_case
    _,candidate,_,before=native_case(tmp_path)
    before['geometry']['simple_bonds']=deepcopy(before['geometry']['proxy_details']['bond_simple'])
    before['geometry']['asu_bonds']=[]
    before['monomer_mappings']['rows'][0]['chem_mod_ids']={'status':'RECORDED','ids':[]}
    after=deepcopy(before)
    before['monomer_mappings']['rows'][0]['missing_non_hydrogen_atoms']['atom_ids']=['OP3']
    prepared={'report':{'contexts':[{'site':'A:1','incoming_site':None}]},
        'projections':{'A:1':(candidate,'Q17')},'preparation':{'sites':[{
            'site':'A:1','modification_id':None,'deleted_atoms':['OP3'] if allowed else []}]}}
    checks=_site_native_checks(before,after,prepared)
    assert all(r['status']=='PASS' for r in checks) is allowed


@pytest.mark.parametrize('defect',[None,'target','weight','origin','symmetry','extra','second_plane'])
def test_cross_site_mechanics_preserve_named_parameters_and_both_planes(tmp_path,defect):
    from nasolve.cif_dictionary_sites import _cross_site_proxies
    from tests.test_cif_candidate_usability import native_case
    _,_,_,before=native_case(tmp_path)
    before['atoms'][-1]['identity']['resseq']='2'
    before['geometry']['proxy_details']['parallelity']=[{
        'i_seqs':[0,1,2],'atoms':[r['label'] for r in before['atoms'][:3]],
        'j_seqs':[2,3,4],'j_atoms':[r['label'] for r in before['atoms'][2:]],
        'target_angle_deg':0.,'weight':1.,'origin_id':2,'symmetry_operation':None}]
    after=deepcopy(before);r=after['geometry']['proxy_details']['parallelity'][0]
    if defect=='target':r['target_angle_deg']=1.
    if defect=='weight':r['weight']=2.
    if defect=='origin':r['origin_id']=3
    if defect=='symmetry':r['symmetry_operation']='x+1,y,z'
    if defect=='extra':after['geometry']['proxy_details']['parallelity'].append(deepcopy(r))
    if defect=='second_plane':r['j_seqs']=[0,3,4];r['j_atoms']=[after['atoms'][i]['label'] for i in r['j_seqs']]
    assert (_cross_site_proxies(before,'parallelity')==_cross_site_proxies(after,'parallelity')) is (defect is None)


@pytest.mark.parametrize('hand',['D','L'])
@pytest.mark.parametrize('sugar',['arabino_fluoro','ribo_fluoro','deoxy'])
def test_stored_site_transfer_preserves_source_centres_across_sugar_families(tmp_path,hand,sugar):
    """Synthetic orchestration/configuration checks, not live L-FDNA qualification."""
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites, read_dictionary_sites
    from nasolve.cif_linked_preparation import _render, hydrogen_neighbors, component_values
    from tests.test_cif_fana import molecule, numerical
    identity=tmp_path/'identity';identity.mkdir();shared=inputs(identity)
    v,_=molecule(hand=hand,ribo=sugar=='ribo_fluoro')
    if sugar=='deoxy':
        v['_chem_comp_atom.type_symbol'][v['_chem_comp_atom.atom_id'].index('F')]='H'
        v['_chem_comp_atom.pdbx_stereo_config'][v['_chem_comp_atom.atom_id'].index('C2')]='N'
    rename={n:n+"'" for n in ['C1','C2','C3','C4','C5','O3','O5']}
    rename.update(OR="O4'",P1='OP1',P2='OP2',P2H0='HOP2',OP3H0='HOP3',F='F29')
    for key,values in v.items():
        if key.endswith('.atom_id') or '.atom_id_' in key:
            v[key]=[rename.get(n,n) for n in values]
    code='X73' if hand=='D' else 'B82'
    v['_chem_comp.type']=['L-DNA LINKING' if hand=='L' else 'DNA LINKING'];v['_chem_comp.group']=['DNA']
    g=numerical(v)
    for values in (v,g):
        for key in values:
            if key.endswith('.comp_id') or key=='_chem_comp.id':values[key]=[code]*len(values[key])
    source=tmp_path/'source.cif';candidate=tmp_path/'candidate.cif'
    source.write_text(_render(v,code));candidate.write_text(_render(g,code))
    q=qualification(source,candidate,code)
    assert q['source_assessment']['candidate_status']=='CANDIDATE_REVIEW'
    resolve_qualified_dictionary(source,code,tmp_path/'store',tmp_path/'snapshot',
        source_authority='EXPLICIT',recipe={'policy_id':'SYNTHETIC_TRANSFER','bond_representation_policy':POLICY},
        generator={'name':'FAKE','version':'TEST'},consumer=shared['consumer'],
        acquire=lambda:dict(candidate=candidate,qualification=q,
            provenance={'converged':None,'stopping':'SYNTHETIC','notes':['No native qualification claimed by this fixture.']}))
    atoms=list(zip(g['_chem_comp_atom.atom_id'],g['_chem_comp_atom.type_symbol']))
    xyz=list(zip(*[[float(x) for x in g['_chem_comp_atom.'+axis]] for axis in 'xyz']))
    lines=[]
    for resid in [1,2,3]:
        for (name,element),(x,y,z) in zip(atoms,xyz):
            if element=='H' or name=='OP3' or resid==1 and name in {'P','OP1','OP2'}:continue
            lines.append(f"HETATM{len(lines)+1:5d} {name:>4s} {code:>3s} A{resid:4d}    "
                f"{x+10*resid:8.3f}{y:8.3f}{z:8.3f}{1.:6.2f}{20.:6.2f}          {element:>2s}\n")
    model=tmp_path/'model.pdb';model.write_text(''.join(lines)+'END\n')
    contexts=[{'site':'A:'+str(i),'incoming_site':'A:'+str(i-1) if i>1 else None,
        'outgoing_site':'A:'+str(i+1) if i<3 else None,'five_prime_state':'linked' if i>1 else 'free_OH',
        'three_prime_state':'linked' if i<3 else 'free_OH'} for i in [1,2,3]]
    result=prepare_dictionary_sites(tmp_path/'snapshot',model,contexts,tmp_path/'out',
        consumer=shared['consumer'],expected_links=[('A:1','A:2'),('A:2','A:3')],
        terminal_resource=shared['terminal_resource'])
    read=read_dictionary_sites(tmp_path/'out');prep=read['preparation']
    assert prep['source_type']==v['_chem_comp.type'][0]
    assert len(prep['preparation_qualification']['source_configuration']['terms'])==(3 if sugar=='deoxy' else 4)
    for site in prep['sites']:
        checks=site['source_configuration_projection']
        assert len(checks)==(3 if sugar=='deoxy' else 4) and all(c['status']=='RETAINED_SOURCE_NEIGHBORS' for c in checks)
        path,component=read['projections'][site['site']];values=component_values(path,component)
        assert 'OP3' not in values['_chem_comp_atom.atom_id']
        original={n:tuple(float(g['_chem_comp_atom.'+axis][i]) for axis in 'xyz')
            for i,n in enumerate(g['_chem_comp_atom.atom_id'])}
        for i,name in enumerate(values['_chem_comp_atom.atom_id']):
            if name in original:
                assert tuple(float(values['_chem_comp_atom.'+axis][i]) for axis in 'xyz')==original[name]
        assert {k:val for k,val in values.items() if k.startswith('_chem_comp_chir.')} == {
            k:val for k,val in g.items() if k.startswith('_chem_comp_chir.')}
        if site['site']!='A:1':assert hydrogen_neighbors(values,'OP2')==['HOP2']
    assert result['automatic_adoption'] is False and result['native_validation']=='NOT_RUN'


@pytest.mark.parametrize('defect',[None,'contradiction','other_unsupported','native_review',
    'definition_review','no_native_checks','no_definition_checks'])
def test_continuation_keeps_review_visible_and_requires_both_check_layers(defect):
    from nasolve.cif_dictionary_sites import _diagnostic_continuation
    qualification={'status':'REVIEW','checks':[
        {'check':'effective-site-formal-charges:A:1','status':'UNSUPPORTED','contradictions':[]},
        {'check':'exact-definition','status':'PASS'}]}
    native=[{'check':'exact-active-angles','status':'PASS'}]
    if defect=='contradiction':qualification['checks'][0]['contradictions']=[{'atom':'P'}]
    if defect=='other_unsupported':qualification['checks'][0]['check']='unknown-source-state'
    if defect=='native_review':native[0]['status']='REVIEW'
    if defect=='definition_review':qualification['checks'][1]['status']='REVIEW'
    if defect=='no_native_checks':native=[]
    if defect=='no_definition_checks':qualification['checks']=[]
    result=_diagnostic_continuation(qualification,native)
    assert result['allowed'] is (defect is None)
    assert result['scope']=='SEPARATE_DIAGNOSTIC_PHASE_ONLY' and result['automatic_adoption'] is False
    assert qualification['status']=='REVIEW'


@pytest.mark.parametrize('defect',[None,'incoming_sulfur','outgoing_arsenic'])
def test_native_port_names_cannot_authorize_wrong_elements(defect):
    from nasolve.cif_dictionary_sites import _port_elements
    rows=[('1',"O3'",'O'),('2','P','P'),('2',"O3'",'O'),('3','P','P')]
    native={'atoms':[{'identity':{'chain_id':'A','resseq':site,'icode':''},'atom_id':name,'element':element}
        for site,name,element in rows]}
    if defect=='incoming_sulfur':native['atoms'][0]['element']='S'
    if defect=='outgoing_arsenic':native['atoms'][-1]['element']='As'
    assert _port_elements(native,{'site':'A:2','incoming_site':'A:1','outgoing_site':'A:3'}) is (defect is None)
